from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.models.auth import User
from app.models.search import FavoritePaper, SearchJob, SearchResult
from app.schemas.library import FavoriteDetailResponse
from app.schemas.search import FavoriteCreateRequest, FavoriteResponse, SearchJobResponse
from app.services.rbac import has_role
from app.models.team import TeamMember

router = APIRouter(prefix="/library", tags=["library"])


async def _require_team_role(
    db: AsyncSession,
    team_id: str,
    user_id: str,
    role: str,
) -> TeamMember:
    row = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )
    member = row.scalar_one_or_none()
    if not member or not has_role(role, member.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient permission")
    return member


@router.get("/history", response_model=list[SearchJobResponse])
async def list_history(
    team_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    await _require_team_role(db, team_id, user.id, "viewer")
    rows = await db.execute(
        select(SearchJob).where(SearchJob.team_id == team_id).order_by(SearchJob.created_at.desc())
    )
    return [
        SearchJobResponse(
            id=j.id,
            team_id=j.team_id,
            query=j.query,
            status=j.status,
            iteration_count=j.iteration_count,
            final_output=j.final_output,
            created_at=j.created_at,
            updated_at=j.updated_at,
        )
        for j in rows.scalars().all()
    ]


@router.post("/favorites", response_model=FavoriteResponse)
async def create_favorite(
    payload: FavoriteCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    await _require_team_role(db, payload.team_id, user.id, "viewer")

    row = await db.execute(
        select(FavoritePaper).where(
            FavoritePaper.team_id == payload.team_id,
            FavoritePaper.user_id == user.id,
            FavoritePaper.result_id == payload.result_id,
        )
    )
    existed = row.scalar_one_or_none()
    if existed:
        return FavoriteResponse(
            id=existed.id,
            team_id=existed.team_id,
            user_id=existed.user_id,
            result_id=existed.result_id,
        )

    favorite = FavoritePaper(team_id=payload.team_id, user_id=user.id, result_id=payload.result_id)
    db.add(favorite)
    await db.commit()
    await db.refresh(favorite)

    return FavoriteResponse(
        id=favorite.id,
        team_id=favorite.team_id,
        user_id=favorite.user_id,
        result_id=favorite.result_id,
    )


@router.get("/favorites", response_model=list[FavoriteDetailResponse])
async def list_favorites(
    team_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=200, ge=1, le=1000),
):
    await _require_team_role(db, team_id, user.id, "viewer")

    rows = await db.execute(
        select(FavoritePaper, SearchResult)
        .join(SearchResult, SearchResult.id == FavoritePaper.result_id)
        .where(FavoritePaper.team_id == team_id, FavoritePaper.user_id == user.id)
        .limit(limit)
    )
    results: list[FavoriteDetailResponse] = []
    for favorite, paper in rows.all():
        results.append(
            FavoriteDetailResponse(
                id=favorite.id,
                team_id=favorite.team_id,
                user_id=favorite.user_id,
                result_id=favorite.result_id,
                title=paper.title,
                authors=paper.authors,
                abstract=paper.abstract,
                year=paper.year,
                source=paper.source,
                url=paper.url,
                score=paper.score,
                metadata=paper.metadata_json,
            )
        )
    return results


@router.delete("/favorites/{favorite_id}")
async def remove_favorite(
    favorite_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    favorite = await db.get(FavoritePaper, favorite_id)
    if not favorite or favorite.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="favorite not found")

    await db.delete(favorite)
    await db.commit()
    return {"message": "deleted"}
