from __future__ import annotations

import asyncio
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.search import SearchJob, SearchJobEvent
from app.ws.manager import ws_manager

router = APIRouter(tags=["ws"])
settings = get_settings()


async def _send_events(
    websocket: WebSocket,
    rows: list[SearchJobEvent],
    seen_ids: set[str],
) -> tuple[datetime | None, set[str]]:
    last_seen_at = None
    for event in rows:
        if event.id in seen_ids:
            continue
        payload = {
            "id": event.id,
            "event_type": event.event_type,
            "from_agent": event.from_agent,
            "to_agent": event.to_agent,
            "reason": event.reason,
            "payload": event.payload,
            "created_at": event.created_at.isoformat() if event.created_at else "",
            "job_id": event.job_id,
        }
        await websocket.send_json(payload)
        seen_ids.add(event.id)
        last_seen_at = event.created_at or last_seen_at
    return last_seen_at, seen_ids


@router.websocket("/ws/jobs/{job_id}")
async def job_events_ws(websocket: WebSocket, job_id: str):
    await ws_manager.connect_job(job_id, websocket)
    last_seen_at: datetime | None = None
    seen_ids: set[str] = set()
    try:
        async with SessionLocal() as db:
            rows = await db.execute(
                select(SearchJobEvent)
                .where(SearchJobEvent.job_id == job_id)
                .order_by(SearchJobEvent.created_at.asc())
                .limit(200)
            )
            last_seen_at, seen_ids = await _send_events(websocket, rows.scalars().all(), seen_ids)

        if settings.job_executor_mode == "inline":
            while True:
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                    if data == "ping":
                        await websocket.send_text("pong")
                except asyncio.TimeoutError:
                    continue

        while True:
            async with SessionLocal() as db:
                stmt = select(SearchJobEvent).where(SearchJobEvent.job_id == job_id)
                if last_seen_at:
                    stmt = stmt.where(SearchJobEvent.created_at >= last_seen_at)
                rows = await db.execute(stmt.order_by(SearchJobEvent.created_at.asc()))
                events = rows.scalars().all()
                last_seen_at, seen_ids = await _send_events(websocket, events, seen_ids)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=settings.ws_poll_interval_sec)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        ws_manager.disconnect_job(job_id, websocket)
    except Exception:  # noqa: BLE001
        ws_manager.disconnect_job(job_id, websocket)


@router.websocket("/ws/teams/{team_id}/streams")
async def team_events_ws(websocket: WebSocket, team_id: str):
    await ws_manager.connect_team(team_id, websocket)
    last_seen_at: datetime | None = None
    seen_ids: set[str] = set()
    try:
        async with SessionLocal() as db:
            rows = await db.execute(
                select(SearchJobEvent)
                .join(SearchJob, SearchJob.id == SearchJobEvent.job_id)
                .where(SearchJob.team_id == team_id)
                .order_by(SearchJobEvent.created_at.asc())
                .limit(200)
            )
            last_seen_at, seen_ids = await _send_events(websocket, rows.scalars().all(), seen_ids)

        if settings.job_executor_mode == "inline":
            while True:
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                    if data == "ping":
                        await websocket.send_text("pong")
                except asyncio.TimeoutError:
                    continue

        while True:
            async with SessionLocal() as db:
                stmt = (
                    select(SearchJobEvent)
                    .join(SearchJob, SearchJob.id == SearchJobEvent.job_id)
                    .where(SearchJob.team_id == team_id)
                )
                if last_seen_at:
                    stmt = stmt.where(SearchJobEvent.created_at >= last_seen_at)
                rows = await db.execute(stmt.order_by(SearchJobEvent.created_at.asc()))
                events = rows.scalars().all()
                last_seen_at, seen_ids = await _send_events(websocket, events, seen_ids)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=settings.ws_poll_interval_sec)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        ws_manager.disconnect_team(team_id, websocket)
    except Exception:  # noqa: BLE001
        ws_manager.disconnect_team(team_id, websocket)
