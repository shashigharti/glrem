"""
Module for handling user password hashing and seeding the database with an admin user.

This module includes functionality to:
- Hash passwords using bcrypt
- Seed the database with a default 'admin' user if it does not already exist
- Handle database session creation and rollback in case of errors
"""

from datetime import datetime, timezone
from passlib.context import CryptContext
from src.models import User
from src.database import SessionLocal

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash the password using bcrypt."""
    return pwd_context.hash(password)


def seed_users():
    """Seeds the database with an 'admin' user if not already present."""

    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.username == "admin").first()

        if not existing_user:
            hashed_password = hash_password("admin123")
            new_user = User(
                username="admin",
                email="shashi.gharti@gmail.com",
                hashed_password=hashed_password,
                created_at=datetime.now(timezone.utc),
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            existing_user = new_user
        else:
            print("User 'admin' already exists. Skipping user creation.")

        db.commit()

        print("Seed data (users and tasks) inserted successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_users()
