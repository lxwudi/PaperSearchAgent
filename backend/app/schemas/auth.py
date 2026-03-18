from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import TokenPair


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(TokenPair):
    user_id: str
    email: EmailStr
    display_name: str


class MeResponse(BaseModel):
    id: str
    email: EmailStr
    display_name: str
    is_active: bool
