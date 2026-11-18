from typing import Optional, List
from sqlalchemy.orm import Session
from app.database.models import User


class UserRepository:
    """CRUD operations for users and tenant isolation."""

    @staticmethod
    def get_by_id(db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def create(
        db: Session,
        username: str,
        email: str,
        role: str = "analyst"
    ) -> User:
        user = User(username=username, email=email, role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_or_create_default_user(db: Session) -> User:
        user = db.query(User).filter(User.username == "default_analyst").first()
        if not user:
            user = User(
                username="default_analyst",
                email="analyst@churniq.io",
                role="admin"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
