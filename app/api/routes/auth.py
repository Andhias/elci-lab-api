from fastapi import APIRouter

from app.schemas.auth import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    return LoginResponse(
        access_token="demo-access-token",
        refresh_token="demo-refresh-token",
        user=UserOut(name=payload.identifier, role="admin"),
    )
