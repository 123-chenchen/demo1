from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.db.models import User
from app.schemas import (
    AuthMeRead,
    AuthUserRead,
    ForgotPasswordRequest,
    ForgotPasswordVerifyRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    OTPDeliveryResponse,
    RegisterRequest,
    RegisterVerifyRequest,
    RegisterVerifyResponse,
)
from app.services.auth import (
    AuthAuthenticationError,
    AuthConflictError,
    AuthDeliveryError,
    AuthForbiddenError,
    AuthNotFoundError,
    AuthValidationError,
    auth_service,
)

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.get("/me", response_model=AuthMeRead, response_model_by_alias=False)
def get_authenticated_user(
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    return {
        "email": current_user.email,
        "name": auth_service.build_name_from_email(current_user.email),
    }


@auth_router.post("/register/request", response_model=OTPDeliveryResponse, response_model_by_alias=False)
def request_registration_otp(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return auth_service.request_register(
            db,
            email=payload.email,
            password=payload.password,
        )
    except AuthValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AuthConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthDeliveryError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@auth_router.post(
    "/register/verify",
    response_model=RegisterVerifyResponse,
    response_model_by_alias=False,
    status_code=status.HTTP_201_CREATED,
)
def verify_registration_otp(
    payload: RegisterVerifyRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return auth_service.verify_register(
            db,
            email=payload.email,
            otp=payload.otp,
        )
    except AuthValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AuthConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@auth_router.post("/login", response_model=LoginResponse, response_model_by_alias=False)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return auth_service.login(
            db,
            email=payload.email,
            password=payload.password,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    except AuthAuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AuthForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except AuthConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@auth_router.post("/forgot-password/request", response_model=OTPDeliveryResponse, response_model_by_alias=False)
def request_forgot_password_otp(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return auth_service.request_forgot_password(
            db,
            email=payload.email,
        )
    except AuthValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AuthNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthDeliveryError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@auth_router.post("/forgot-password/verify", response_model=MessageResponse, response_model_by_alias=False)
def verify_forgot_password_otp(
    payload: ForgotPasswordVerifyRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return auth_service.verify_forgot_password(
            db,
            email=payload.email,
            otp=payload.otp,
            new_password=payload.new_password,
        )
    except AuthValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AuthNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
