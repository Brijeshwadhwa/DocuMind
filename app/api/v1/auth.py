from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.user import UserRegister, UserLogin, UserResponse, Token
from app.services.auth_service import AuthService
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Registers a unique user email with a bcrypt-hashed password."
)
def register(
    payload: UserRegister,
    db: Session = Depends(get_db)
):
    service = AuthService(db)
    return service.register_user(payload)


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate and obtain JWT access token",
    description="Validates user credentials and returns a JWT bearer access token."
)
def login(
    payload: UserLogin,
    db: Session = Depends(get_db)
):
    service = AuthService(db)
    return service.authenticate_user(payload)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Returns the authenticated user details corresponding to the provided Bearer token."
)
def get_me(
    current_user: User = Depends(get_current_user)
):
    return UserResponse.model_validate(current_user)
