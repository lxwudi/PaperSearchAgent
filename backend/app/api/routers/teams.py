from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.models.auth import User
from app.models.team import Team, TeamMember
from app.schemas.team import (
    TeamCreateRequest,
    TeamMemberAddRequest,
    TeamMemberResponse,
    TeamMemberRoleUpdateRequest,
    TeamResponse,
)
from app.services.rbac import has_role

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list[TeamResponse])
async def list_teams(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    member_rows = await db.execute(select(TeamMember).where(TeamMember.user_id == user.id))
    memberships = member_rows.scalars().all()
    if not memberships:
        return []

    ids = [m.team_id for m in memberships]
    teams = await db.execute(select(Team).where(Team.id.in_(ids)))
    return [
        TeamResponse(id=t.id, name=t.name, created_by=t.created_by)
        for t in teams.scalars().all()
    ]


@router.post("", response_model=TeamResponse)
async def create_team(
    payload: TeamCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    team = Team(name=payload.name, created_by=user.id)
    db.add(team)
    await db.flush()

    db.add(TeamMember(team_id=team.id, user_id=user.id, role="owner"))
    await db.commit()
    return TeamResponse(id=team.id, name=team.name, created_by=team.created_by)


@router.post("/{team_id}/members", response_model=TeamMemberResponse)
async def add_member(
    team_id: str,
    payload: TeamMemberAddRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    current_member = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user.id)
    )
    current = current_member.scalar_one_or_none()
    if not current or not has_role("admin", current.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient permission")

    target = await db.get(User, payload.user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    existing = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == payload.user_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="already member")

    member = TeamMember(team_id=team_id, user_id=payload.user_id, role=payload.role)
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return TeamMemberResponse(id=member.id, team_id=member.team_id, user_id=member.user_id, role=member.role)


@router.patch("/{team_id}/members/{user_id}", response_model=TeamMemberResponse)
async def update_member_role(
    team_id: str,
    user_id: str,
    payload: TeamMemberRoleUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    actor_row = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user.id)
    )
    actor = actor_row.scalar_one_or_none()
    if not actor or not has_role("admin", actor.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient permission")

    target_row = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )
    target = target_row.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="member not found")

    if target.role == "owner" and actor.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="cannot change owner role")

    target.role = payload.role
    await db.commit()
    return TeamMemberResponse(id=target.id, team_id=target.team_id, user_id=target.user_id, role=target.role)


@router.get("/{team_id}/members", response_model=list[TeamMemberResponse])
async def list_members(
    team_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=100, ge=1, le=500),
):
    member_row = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user.id)
    )
    if not member_row.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not team member")

    rows = await db.execute(select(TeamMember).where(TeamMember.team_id == team_id).limit(limit))
    return [
        TeamMemberResponse(id=m.id, team_id=m.team_id, user_id=m.user_id, role=m.role)
        for m in rows.scalars().all()
    ]
