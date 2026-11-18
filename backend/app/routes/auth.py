import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import User
from app.repositories.user_repository import UserRepository
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
