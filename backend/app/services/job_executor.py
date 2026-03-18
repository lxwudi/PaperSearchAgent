from __future__ import annotations

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.mcp.gateway import MCPClientManager, ScientificPaperGateway
from app.models.search import SearchJob, SearchJobEvent
from app.services.llm_client import LLMClient
from app.services.workflow_runner import WorkflowRunner


class JobExecutor:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}
        self.mcp_manager = MCPClientManager()
        self.settings = get_settings()
        self.llm_client = LLMClient()
        self.startup_error: str | None = None

    async def startup(self) -> None:
        if self.settings.job_executor_mode == "inline":
            try:
                await asyncio.wait_for(self.mcp_manager.start(), timeout=self.settings.mcp_timeout_sec)
                self.startup_error = None
            except Exception as exc:  # noqa: BLE001
                self.startup_error = str(exc)

    async def shutdown(self) -> None:
        for task in self._tasks.values():
            if not task.done():
                task.cancel()
        self._tasks.clear()
        if self.settings.job_executor_mode == "inline":
            await self.mcp_manager.stop()

    def start_job(self, job_id: str) -> None:
        if self.settings.job_executor_mode != "inline":
            return
        existing = self._tasks.get(job_id)
        if existing and not existing.done():
            return

        task = asyncio.create_task(self._run_job(job_id))
        self._tasks[job_id] = task

    def cancel_job(self, job_id: str) -> bool:
        if self.settings.job_executor_mode != "inline":
            return False
        task = self._tasks.get(job_id)
        if not task or task.done():
            return False
        task.cancel()
        return True

    async def _run_job(self, job_id: str) -> None:
        async with SessionLocal() as db:
            job = await db.get(SearchJob, job_id)
            if not job:
                return

            job.status = "running"
            await db.commit()

            startup_warning: str | None = self.startup_error
            if not self.mcp_manager.started:
                try:
                    await asyncio.wait_for(
                        self.mcp_manager.start(),
                        timeout=self.settings.mcp_timeout_sec,
                    )
                    startup_warning = None
                except Exception as exc:  # noqa: BLE001
                    startup_warning = f"MCP startup failed: {exc}"
                    self.startup_error = startup_warning

            gateway = ScientificPaperGateway(self.mcp_manager, startup_warning=startup_warning)
            runner = WorkflowRunner(gateway, self.llm_client)
            try:
                await runner.run(db, job)
            except Exception as exc:  # noqa: BLE001
                await self._mark_failed(db, job_id, str(exc))

    async def _mark_failed(self, db: AsyncSession, job_id: str, reason: str) -> None:
        job = await db.get(SearchJob, job_id)
        if not job:
            return
        job.status = "failed"
        db.add(
            SearchJobEvent(
                job_id=job_id,
                event_type="workflow.failed",
                from_agent="system",
                to_agent=None,
                reason=reason,
                payload={"error": reason},
            )
        )
        await db.commit()


job_executor = JobExecutor()
