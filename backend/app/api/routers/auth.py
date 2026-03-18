from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.auth import RefreshToken, User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
)
from app.services.jwt_service import JWTService
from app.services.password_service import hash_password, verify_password
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db_session)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already exists")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    await db.flush()

    access_token = JWTService.create_access_token(user.id)
    refresh_token = JWTService.create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, token=refresh_token, revoked=False))

    await db.commit()
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")

    access_token = JWTService.create_access_token(user.id)
    refresh_token = JWTService.create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, token=refresh_token, revoked=False))
    await db.commit()

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db_session)):
    token_row = await db.execute(select(RefreshToken).where(RefreshToken.token == payload.refresh_token))
    token_obj = token_row.scalar_one_or_none()
    if not token_obj or token_obj.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token")

    decoded = JWTService.decode_token(payload.refresh_token)
    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token type")

    user = await db.get(User, decoded.get("sub"))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid user")

    token_obj.revoked = True
    new_refresh = JWTService.create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, token=new_refresh, revoked=False))
    access_token = JWTService.create_access_token(user.id)
    await db.commit()

    return AuthResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
    )


@router.post("/logout")
async def logout(payload: RefreshRequest, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == payload.refresh_token))
    token_obj = result.scalar_one_or_none()
    if token_obj:
        token_obj.revoked = True
        await db.commit()
    return {"message": "logged out"}


@router.get("/me", response_model=MeResponse)
async def me(user: User = Depends(get_current_user)):
    return MeResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
    )
