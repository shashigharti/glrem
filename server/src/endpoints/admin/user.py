from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from src.crud.auth import authenticate_user
from src.schemas.user import UserLogin
from src.database import get_db
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

router = APIRouter()


@router.post("/login")
def login(user_login: UserLogin, db: Session = Depends(get_db)):
    """Handle user login."""
    try:
        if not user_login.username or not user_login.password:
            raise HTTPException(
                status_code=400, detail="Username and password are required"
            )

        user = authenticate_user(db, user_login.username, user_login.password)

        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return {
            "message": "Authentication successful",
            "user_id": user.id,
            "username": user.username,
        }

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail="Database error occurred")

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {e}")

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )
