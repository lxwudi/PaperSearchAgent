from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.auth import User
from app.models.team import TeamMember
from app.services.jwt_service import JWTService
from app.services.rbac import has_role

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing token")

    payload = JWTService.decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token type")

    user = await db.get(User, payload.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid user")
    return user


def team_role_guard(min_role: str):
    async def _guard(
        team_id: str,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session),
    ) -> TeamMember:
        stmt = select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user.id,
        )
        result = await db.execute(stmt)
        member = result.scalar_one_or_none()
        if not member or not has_role(min_role, member.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient permission")
        return member

    return _guard
