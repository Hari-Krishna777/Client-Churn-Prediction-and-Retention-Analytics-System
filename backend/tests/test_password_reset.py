import hashlib
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest
from fastapi import HTTPException

from app.database.connection import init_db, SessionLocal
from app.database.models import User, PasswordResetToken
from app.routes.auth import (
    register,
    login,
    forgot_password,
    verify_reset_token,
    reset_password,
    RegisterRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.services.security_service import verify_password


def test_password_reset_end_to_end():
    init_db()
    db = SessionLocal()

    suffix = uuid4().hex[:8]
    test_email = f"test_{suffix}@example.com"
    test_username = f"user_{suffix}"
    old_password = "OldPassword123!"
    new_password = "NewStrongPassword456!"

    try:
        # 1. Register a test user
        reg_result = register(
            RegisterRequest(username=test_username, email=test_email, password=old_password),
            db=db,
        )
        assert reg_result.username == test_username
        assert reg_result.email == test_email

        # 2. Request forgot password for an unknown email -> privacy safe (doesn't reveal user absence)
        unknown_res = forgot_password(
            ForgotPasswordRequest(email="nobody_unknown@example.com"),
            db=db,
        )
        assert "If an account with that email address exists" in unknown_res.message

        # 3. Request forgot password for registered user
        forgot_res = forgot_password(
            ForgotPasswordRequest(email=test_email),
            db=db,
        )
        assert "If an account with that email address exists" in forgot_res.message

        # Verify a token record was created in the database
        user = db.query(User).filter(User.email == test_email).first()
        assert user is not None
        token_record = (
            db.query(PasswordResetToken)
            .filter(PasswordResetToken.user_id == user.id, PasswordResetToken.used == False)
            .first()
        )
        assert token_record is not None
        expires_utc = (
            token_record.expires_at.replace(tzinfo=timezone.utc)
            if token_record.expires_at.tzinfo is None
            else token_record.expires_at
        )
        assert expires_utc > datetime.now(timezone.utc)

        # 4. Invalidate old tokens on subsequent request
        forgot_res2 = forgot_password(
            ForgotPasswordRequest(email=test_email),
            db=db,
        )
        assert "If an account with that email address exists" in forgot_res2.message
        # The previous token should now be marked used = True
        prev_token = (
            db.query(PasswordResetToken)
            .filter(PasswordResetToken.id == token_record.id)
            .first()
        )
        assert prev_token.used is True

        # 5. Create known raw token to test verification and password reset
        raw_token = f"raw_token_{suffix}"
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        manual_record = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            used=False,
        )
        db.add(manual_record)
        db.commit()

        # Verify invalid token
        invalid_verify = verify_reset_token(token="invalid_token_xyz", db=db)
        assert invalid_verify.valid is False

        # Verify valid token
        valid_verify = verify_reset_token(token=raw_token, db=db)
        assert valid_verify.valid is True
        assert valid_verify.email is not None
        assert "@example.com" in valid_verify.email

        # 6. Reset password with password shorter than 12 characters -> rejected with 422
        with pytest.raises(HTTPException) as exc_info:
            reset_password(ResetPasswordRequest(token=raw_token, new_password="short"), db=db)
        assert exc_info.value.status_code == 422

        # 7. Reset password with valid password -> success
        reset_res = reset_password(
            ResetPasswordRequest(token=raw_token, new_password=new_password),
            db=db,
        )
        assert "successfully reset" in reset_res.message

        # Token should now be marked used
        db.refresh(manual_record)
        assert manual_record.used is True

        # 8. Re-using the same token -> rejected with 400
        with pytest.raises(HTTPException) as exc_info:
            reset_password(
                ResetPasswordRequest(token=raw_token, new_password="AnotherPassword123!"),
                db=db,
            )
        assert exc_info.value.status_code == 400

        # 9. Verify user password was changed: old password fails, new password succeeds
        with pytest.raises(HTTPException) as exc_info:
            login(LoginRequest(username=test_username, password=old_password), db=db)
        assert exc_info.value.status_code == 401

        login_res = login(LoginRequest(username=test_username, password=new_password), db=db)
        assert login_res.access_token is not None
        assert login_res.username == test_username

        # 10. Expired token check
        expired_raw = f"expired_raw_{suffix}"
        expired_hash = hashlib.sha256(expired_raw.encode("utf-8")).hexdigest()
        past_expires = datetime.now(timezone.utc) - timedelta(minutes=15)
        expired_record = PasswordResetToken(
            user_id=user.id,
            token_hash=expired_hash,
            expires_at=past_expires,
            used=False,
        )
        db.add(expired_record)
        db.commit()

        expired_verify = verify_reset_token(token=expired_raw, db=db)
        assert expired_verify.valid is False
        assert "expired" in expired_verify.message.lower()

        with pytest.raises(HTTPException) as exc_info:
            reset_password(
                ResetPasswordRequest(token=expired_raw, new_password="ValidExpiredPassword123!"),
                db=db,
            )
        assert exc_info.value.status_code == 400
        assert "expired" in exc_info.value.detail.lower()

        # 11. Malformed email in forgot-password -> 422 Unprocessable Entity
        with pytest.raises(HTTPException) as exc_info:
            forgot_password(ForgotPasswordRequest(email="not-an-email"), db=db)
        assert exc_info.value.status_code == 422

        # 12. Empty token in reset-password -> 400 Bad Request
        with pytest.raises(HTTPException) as exc_info:
            reset_password(ResetPasswordRequest(token="   ", new_password=new_password), db=db)
        assert exc_info.value.status_code == 400

    finally:
        db.close()
