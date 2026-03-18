from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

from app.core.config import get_settings

settings = get_settings()


class JWTService:
    @staticmethod
    def create_token(subject: str, expires_minutes: int, token_type: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
        payload = {"sub": subject, "exp": expire, "type": token_type}
        return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    def create_access_token(user_id: str) -> str:
        return JWTService.create_token(
            subject=user_id,
            expires_minutes=settings.access_token_expire_minutes,
            token_type="access",
        )

    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        return JWTService.create_token(
            subject=user_id,
            expires_minutes=settings.refresh_token_expire_minutes,
            token_type="refresh",
        )

    @staticmethod
    def decode_token(token: str) -> dict:
        try:
            return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        except JWTError as exc:
            raise ValueError("invalid token") from exc
