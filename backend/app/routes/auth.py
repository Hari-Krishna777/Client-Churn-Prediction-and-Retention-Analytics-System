import hashlib
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
from app.database.connection import get_db
from app.database.models import User, PasswordResetToken
from app.repositories.user_repository import UserRepository
from app.services.email_service import EmailService
from app.services.security_service import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_role,
)

router = APIRouter(prefix="/auth", tags=["Authentication & User Management"])


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class MessageResponse(BaseModel):
    message: str


class VerifyResetTokenResponse(BaseModel):
    valid: bool
    email: Optional[str] = None
    message: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    id: str
    username: str
    email: str
    role: str
    token: str  # Kept for backward compatibility with frontend


def _validate_registration(req: RegisterRequest) -> None:
    if len(req.username.strip()) < 3 or len(req.username) > 100:
        raise HTTPException(status_code=422, detail="Username must be between 3 and 100 characters.")
    if len(req.password) < 12:
        raise HTTPException(status_code=422, detail="Password must be at least 12 characters long.")


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, summary="Register new user account")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account with hashed password and return signed JWT."""
    _validate_registration(req)
    existing_username = UserRepository.get_by_username(db, req.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{req.username}' is already registered."
        )

    existing_email = db.query(User).filter(User.email == req.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{req.email}' is already in use."
        )

    hashed = hash_password(req.password)
    user = User(
        username=req.username,
        email=req.email,
        # Public registration cannot self-assign elevated privileges.
        role="analyst",
        hashed_password=hashed
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token_data = {
        "sub": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role
    }
    jwt_token = create_access_token(token_data)

    return TokenResponse(
        access_token=jwt_token,
        token_type="bearer",
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        token=jwt_token
    )


@router.post("/login", response_model=TokenResponse, summary="Authenticate user and issue signed JWT")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with username and password, producing a secure JWT token."""
    user = UserRepository.get_by_username(db, req.username)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.hashed_password or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = {
        "sub": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role
    }
    jwt_token = create_access_token(token_data)

    return TokenResponse(
        access_token=jwt_token,
        token_type="bearer",
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        token=jwt_token
    )


@router.get("/me", response_model=TokenResponse, summary="Get current authenticated user profile")
def get_me(current_user: User = Depends(get_current_user)):
    """Return identity and roles of the authenticated principal."""
    token_data = {
        "sub": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role
    }
    jwt_token = create_access_token(token_data)

    return TokenResponse(
        access_token=jwt_token,
        token_type="bearer",
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        token=jwt_token
    )


@router.get("/users", summary="List available users and roles (Admin/Analyst persona management)")
def list_users(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Retrieve registered users (administrators only)."""

    users = db.query(User).filter(User.is_active == True).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "created_at": u.created_at.isoformat() if u.created_at else None
        }
        for u in users
    ]


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Request a password reset link sent to user email"
)
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Generate a secure password reset token and send an email to the user.
    To prevent user enumeration, always returns a generic success message
    regardless of whether the email address was found in the database.
    """
    normalized_email = req.email.strip().lower()
    if "@" not in normalized_email or len(normalized_email) < 5 or "." not in normalized_email.split("@")[-1]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A valid email address is required."
        )

    user = db.query(User).filter(func.lower(User.email) == normalized_email).first()

    generic_response = MessageResponse(
        message="If an account with that email address exists, a password reset link has been sent to your email."
    )

    if not user or not user.is_active:
        return generic_response

    # Invalidate previous unused reset tokens for this user
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used == False
    ).update({"used": True})

    # Generate cryptographically secure token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)

    reset_token_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        used=False
    )
    db.add(reset_token_record)
    db.commit()

    # Dispatch email
    EmailService.send_password_reset_email(
        to_email=user.email,
        username=user.username,
        reset_token=raw_token
    )

    return generic_response


@router.get(
    "/verify-reset-token",
    response_model=VerifyResetTokenResponse,
    summary="Verify if a password reset token is valid and unexpired"
)
def verify_reset_token(token: str, db: Session = Depends(get_db)):
    """Check if the given reset token is valid and unexpired."""
    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token parameter is required."
        )

    token_hash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
    record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.used == False
    ).first()

    if not record:
        return VerifyResetTokenResponse(
            valid=False,
            message="This password reset link is invalid or has already been used."
        )

    now = datetime.now(timezone.utc)
    record_expires = record.expires_at.replace(tzinfo=timezone.utc) if record.expires_at.tzinfo is None else record.expires_at
    if now > record_expires:
        return VerifyResetTokenResponse(
            valid=False,
            message="This password reset link has expired. Please request a new one."
        )

    user = db.query(User).filter(User.id == record.user_id).first()
    if not user or not user.is_active:
        return VerifyResetTokenResponse(
            valid=False,
            message="The user account associated with this token is inactive or no longer exists."
        )

    # Mask email (e.g. j***@example.com)
    parts = user.email.split("@")
    if len(parts) == 2 and len(parts[0]) > 1:
        masked_email = f"{parts[0][0]}***@{parts[1]}"
    else:
        masked_email = user.email

    return VerifyResetTokenResponse(
        valid=True,
        email=masked_email,
        message="Token is valid."
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset user password using a valid reset token"
)
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset the user password with a valid, unexpired reset token."""
    if not req.token or not req.token.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token is required."
        )

    if len(req.new_password) < 12:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 12 characters long."
        )

    token_hash = hashlib.sha256(req.token.strip().encode("utf-8")).hexdigest()
    record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.used == False
    ).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used password reset link. Please request a new one."
        )

    now = datetime.now(timezone.utc)
    record_expires = record.expires_at.replace(tzinfo=timezone.utc) if record.expires_at.tzinfo is None else record.expires_at
    if now > record_expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link has expired. Please request a new one."
        )

    user = db.query(User).filter(User.id == record.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account associated with this token is invalid or deactivated."
        )

    # Update password and invalidate token
    user.hashed_password = hash_password(req.new_password)
    record.used = True
    db.commit()

    return MessageResponse(
        message="Your password has been successfully reset. You can now sign in with your new password."
    )
