import os

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.auth import User
from app.models.search import ExportJob, FavoritePaper, SearchJob, SearchJobEvent, SearchResult
from app.models.team import TeamMember
from app.schemas.search import (
    ExportCreateRequest,
    ExportResponse,
    FavoriteCreateRequest,
    FavoriteResponse,
    SearchEventResponse,
    SearchJobCreateRequest,
    SearchJobResponse,
    SearchResultResponse,
)
from app.services.export_service import build_csv, build_pdf
from app.services.job_executor import job_executor
from app.services.rbac import has_role

router = APIRouter(prefix="/search", tags=["search"])
settings = get_settings()


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


@router.post("/jobs", response_model=SearchJobResponse)
async def create_job(
    payload: SearchJobCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    await _require_team_role(db, payload.team_id, user.id, "editor")

    job = SearchJob(
        team_id=payload.team_id,
        created_by=user.id,
        query=payload.query,
        status="queued",
        iteration_count=0,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    job_executor.start_job(job.id)

    return SearchJobResponse(
        id=job.id,
        team_id=job.team_id,
        query=job.query,
        status=job.status,
        iteration_count=job.iteration_count,
        final_output=job.final_output,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/jobs/{job_id}", response_model=SearchJobResponse)
async def get_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    job = await db.get(SearchJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")

    await _require_team_role(db, job.team_id, user.id, "viewer")

    return SearchJobResponse(
        id=job.id,
        team_id=job.team_id,
        query=job.query,
        status=job.status,
        iteration_count=job.iteration_count,
        final_output=job.final_output,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/jobs/{job_id}/results", response_model=list[SearchResultResponse])
async def get_job_results(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    min_score: int = Query(default=0, ge=0, le=100),
):
    job = await db.get(SearchJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    await _require_team_role(db, job.team_id, user.id, "viewer")

    rows = await db.execute(
        select(SearchResult)
        .where(SearchResult.job_id == job_id, SearchResult.score >= min_score)
        .order_by(SearchResult.score.desc())
    )

    return [
        SearchResultResponse(
            id=r.id,
            title=r.title,
            authors=r.authors,
            abstract=r.abstract,
            year=r.year,
            source=r.source,
            url=r.url,
            score=r.score,
            metadata=r.metadata_json,
        )
        for r in rows.scalars().all()
    ]


@router.get("/jobs/{job_id}/events", response_model=list[SearchEventResponse])
async def get_job_events(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    job = await db.get(SearchJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    await _require_team_role(db, job.team_id, user.id, "viewer")

    rows = await db.execute(
        select(SearchJobEvent).where(SearchJobEvent.job_id == job_id).order_by(SearchJobEvent.created_at.asc())
    )
    return [
        SearchEventResponse(
            id=e.id,
            event_type=e.event_type,
            from_agent=e.from_agent,
            to_agent=e.to_agent,
            reason=e.reason,
            payload=e.payload,
            created_at=e.created_at,
        )
        for e in rows.scalars().all()
    ]


@router.post("/jobs/{job_id}/retry", response_model=SearchJobResponse)
async def retry_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    job = await db.get(SearchJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    await _require_team_role(db, job.team_id, user.id, "editor")

    job.status = "queued"
    await db.commit()
    await db.refresh(job)
    job_executor.start_job(job.id)

    return SearchJobResponse(
        id=job.id,
        team_id=job.team_id,
        query=job.query,
        status=job.status,
        iteration_count=job.iteration_count,
        final_output=job.final_output,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    job = await db.get(SearchJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    await _require_team_role(db, job.team_id, user.id, "editor")

    cancelled = job_executor.cancel_job(job_id)
    cancelled_queued = False
    if cancelled:
        job.status = "cancelled"
    elif settings.job_executor_mode != "inline" and job.status == "queued":
        job.status = "cancelled"
        cancelled_queued = True
    await db.commit()
    return {"message": "cancelled" if cancelled or cancelled_queued else "not running"}


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


@router.get("/favorites", response_model=list[FavoriteResponse])
async def list_favorites(
    team_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    await _require_team_role(db, team_id, user.id, "viewer")
    rows = await db.execute(
        select(FavoritePaper).where(FavoritePaper.team_id == team_id, FavoritePaper.user_id == user.id)
    )
    return [
        FavoriteResponse(id=f.id, team_id=f.team_id, user_id=f.user_id, result_id=f.result_id)
        for f in rows.scalars().all()
    ]


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


@router.post("/exports", response_model=ExportResponse)
async def create_export(
    payload: ExportCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    await _require_team_role(db, payload.team_id, user.id, "viewer")

    job = await db.get(SearchJob, payload.job_id)
    if not job or job.team_id != payload.team_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")

    rows = await db.execute(select(SearchResult).where(SearchResult.job_id == payload.job_id))
    results = rows.scalars().all()

    if payload.export_type == "csv":
        file_path = build_csv(payload.job_id, [
            {
                "title": r.title,
                "authors": r.authors,
                "year": r.year,
                "source": r.source,
                "url": r.url,
                "score": r.score,
            }
            for r in results
        ])
    else:
        file_path = build_pdf(payload.job_id, job.final_output or "")

    export = ExportJob(
        team_id=payload.team_id,
        requested_by=user.id,
        job_id=payload.job_id,
        export_type=payload.export_type,
        status="completed",
        file_path=file_path,
    )
    db.add(export)
    await db.commit()
    await db.refresh(export)

    return ExportResponse(
        id=export.id,
        team_id=export.team_id,
        job_id=export.job_id,
        export_type=export.export_type,
        status=export.status,
        file_path=export.file_path,
    )


@router.get("/exports", response_model=list[ExportResponse])
async def list_exports(
    team_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    await _require_team_role(db, team_id, user.id, "viewer")
    rows = await db.execute(
        select(ExportJob).where(ExportJob.team_id == team_id).order_by(ExportJob.created_at.desc())
    )
    return [
        ExportResponse(
            id=e.id,
            team_id=e.team_id,
            job_id=e.job_id,
            export_type=e.export_type,
            status=e.status,
            file_path=e.file_path,
        )
        for e in rows.scalars().all()
    ]


@router.get("/exports/{export_id}", response_model=ExportResponse)
async def get_export(
    export_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    export = await db.get(ExportJob, export_id)
    if not export:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="export not found")

    await _require_team_role(db, export.team_id, user.id, "viewer")

    return ExportResponse(
        id=export.id,
        team_id=export.team_id,
        job_id=export.job_id,
        export_type=export.export_type,
        status=export.status,
        file_path=export.file_path,
    )


@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    export = await db.get(ExportJob, export_id)
    if not export:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="export not found")
    await _require_team_role(db, export.team_id, user.id, "viewer")
    if not export.file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file missing")
    return FileResponse(export.file_path, filename=os.path.basename(export.file_path))
