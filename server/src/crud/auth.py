from sqlalchemy.orm import Session
from passlib.context import CryptContext
from src.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """Authenticate a user by username and password."""
    db_user = db.query(User).filter(User.username == username).first()
    if db_user and verify_password(password, db_user.hashed_password):
        return db_user
    return None
