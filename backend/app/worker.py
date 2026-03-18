from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.mcp.gateway import MCPClientManager, ScientificPaperGateway
from app.models.search import SearchJob, SearchJobEvent
from app.services.llm_client import LLMClient
from app.services.workflow_runner import WorkflowRunner


async def mark_failed(job_id: str, reason: str) -> None:
    async with SessionLocal() as db:
        job = await db.get(SearchJob, job_id)
        if not job:
            return
        job.status = "failed"
        db.add(
            SearchJobEvent(
                job_id=job_id,
                event_type="workflow.failed",
                from_agent="worker",
                to_agent=None,
                reason=reason,
                payload={"error": reason},
            )
        )
        await db.commit()


async def run_worker() -> None:
    settings = get_settings()
    mcp_manager = MCPClientManager()
    await mcp_manager.start()
    llm_client = LLMClient()
    runner = WorkflowRunner(ScientificPaperGateway(mcp_manager), llm_client)

    try:
        while True:
            async with SessionLocal() as db:
                row = await db.execute(
                    select(SearchJob)
                    .where(SearchJob.status == "queued")
                    .order_by(SearchJob.created_at.asc())
                    .limit(1)
                )
                job = row.scalar_one_or_none()
                if not job:
                    await asyncio.sleep(settings.worker_poll_interval)
                    continue

                job.status = "running"
                await db.commit()
                try:
                    await runner.run(db, job)
                except Exception as exc:  # noqa: BLE001
                    await mark_failed(job.id, str(exc))
            await asyncio.sleep(0)
    finally:
        await mcp_manager.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
