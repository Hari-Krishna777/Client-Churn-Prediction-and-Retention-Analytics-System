import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import jwt
import bcrypt
from fastapi import Depends, HTTPException, status, Header, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.config import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    MAX_UPLOAD_SIZE_BYTES
)
from app.database.connection import get_db
from app.database.models import User, Dataset, Customer
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer(auto_error=False)

# Dangerous binary signatures that should never appear at the start of a CSV file
MALICIOUS_BINARY_MAGIC = [
    b"MZ",                # DOS/Windows PE executable
    b"\x7fELF",           # Linux ELF executable
    b"\xca\xfe\xba\xbe",  # Java class / Mach-O fat binary
    b"\xce\xfa\xed\xfe",  # Mach-O binary
    b"\xcf\xfa\xed\xfe",  # Mach-O 64-bit binary
    b"PK\x03\x04",        # ZIP/JAR/DOCX archive (not raw CSV)
    b"\x1f\x8b",          # GZIP compressed archive
    b"\x25\x50\x44\x46",  # PDF document (%PDF)
]

DANGEROUS_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with salt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    if not hashed_password or not plain_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception as e:
        logger.warning("Password verification failed with exception: %s", type(e).__name__)
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Generate a signed JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "iat": now,
        "exp": expire
    })
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please authenticate again.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials: invalid token signature.",
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_current_user(
    token: Optional[str] = Query(default=None),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency for extracting and verifying the authenticated User principal.
    Every customer-data endpoint requires a valid bearer token.
    Supports either Authorization: Bearer <token> or ?token=<token> query parameter.
    """
    raw_token = auth.credentials if (auth and auth.credentials) else token
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(raw_token)
    user_id = payload.get("sub") or payload.get("user_id")
    if not user_id:
        username = payload.get("username")
        if username:
            user = UserRepository.get_by_username(db, username)
            if user:
                return user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing user identifier.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = UserRepository.get_by_id(db, str(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with token no longer exists.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account."
        )

    return user


def require_role(*allowed_roles: str):
    """Dependency factory enforcing role-based access control (RBAC)."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: role '{current_user.role}' lacks permission for this operation."
            )
        return current_user
    return role_checker


def verify_dataset_tenant_access(dataset: Dataset, current_user: User) -> None:
    """Enforce dataset-level tenant isolation: one user cannot access another user's dataset."""
    if current_user.role == "admin":
        return

    if dataset.user_id and str(dataset.user_id) != str(current_user.id):
        logger.warning(
            "Tenant isolation violation for dataset %s", dataset.id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not have permission to view or modify this dataset."
        )


def verify_customer_tenant_access(customer: Customer, current_user: User, db: Session) -> None:
    """Enforce customer record tenant isolation: one user cannot view another user's customer."""
    if current_user.role == "admin":
        return

    if customer.user_id and str(customer.user_id) != str(current_user.id):
        logger.warning("Tenant isolation violation for customer record")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not have permission to access this customer record.",
        )

    if customer.dataset_id:
        dataset = db.query(Dataset).filter(Dataset.id == customer.dataset_id).first()
        if dataset and dataset.user_id and str(dataset.user_id) != str(current_user.id):
            logger.warning(
                "Tenant isolation violation for customer record in dataset %s", dataset.id
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: you do not have permission to access customer records from another tenant."
            )


def validate_uploaded_csv(content: bytes, filename: str) -> None:
    """
    Validate uploaded file:
    1. Size limit enforcement
    2. Extension enforcement
    3. Binary / malicious executable signature rejection
    """
    # 1. Size check
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded file exceeds maximum allowed size of {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB."
        )

    # 2. Filename check
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format: uploaded file must have a .csv extension."
        )

    # 3. Executable / binary detection
    for magic in MALICIOUS_BINARY_MAGIC:
        if content.startswith(magic):
            logger.warning("Rejected malicious upload %s: matched binary signature %s", filename, magic)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file content: binary/executable files are strictly prohibited."
            )

    # CSV is a text format. Reject binary control bytes and non-UTF-8 payloads
    # before passing them to a data parser.
    if b"\x00" in content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file content: CSV must not contain NUL bytes.")
    try:
        content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file encoding: CSV must be UTF-8 encoded.",
        ) from exc


def sanitize_csv_cell_value(val: Any) -> Any:
    """Neutralize spreadsheet formula injection (=, +, -, @, \\t, \\r)."""
    if isinstance(val, str) and val.startswith(DANGEROUS_FORMULA_PREFIXES):
        # Prepend single quote to neutralize formula execution in Excel/Sheets
        return "'" + val
    return val
