from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.evidence_scorer import run_evidence_scorer
from app.agents.query_planner import run_query_planner
from app.agents.quality_reviewer import run_quality_reviewer
from app.agents.state import WorkflowState
from app.agents.summary_writer import run_summary_writer
from app.agents.supervisor import route_next_agent
from app.core.config import get_settings
from app.mcp.gateway import ScientificPaperGateway, run_paper_search
from app.models.search import SearchJob, SearchJobEvent, SearchResult
from app.services.llm_client import LLMClient, LLMUnavailableError
from app.ws.manager import ws_manager


class WorkflowRunner:
    def __init__(self, gateway: ScientificPaperGateway, llm_client: LLMClient):
        self.gateway = gateway
        self.llm_client = llm_client
        self.settings = get_settings()

    async def _append_event(
        self,
        db: AsyncSession,
        team_id: str,
        job_id: str,
        event_type: str,
        from_agent: str | None,
        to_agent: str | None,
        reason: str | None,
        payload: dict,
    ) -> None:
        event = SearchJobEvent(
            job_id=job_id,
            event_type=event_type,
            from_agent=from_agent,
            to_agent=to_agent,
            reason=reason,
            payload=payload,
        )
        db.add(event)
        await db.flush()
        if self.settings.job_executor_mode == "inline":
            created_at = event.created_at or datetime.now(timezone.utc)
            payload_out = {
                "id": event.id,
                "event_type": event_type,
                "from_agent": from_agent,
                "to_agent": to_agent,
                "reason": reason,
                "payload": payload,
                "created_at": created_at.isoformat(),
                "job_id": job_id,
                "team_id": team_id,
            }
            await ws_manager.broadcast_job(job_id, payload_out)
            await ws_manager.broadcast_team(team_id, payload_out)

    async def run(self, db: AsyncSession, job: SearchJob) -> SearchJob:
        state = WorkflowState(
            job_id=job.id,
            query=job.query,
            team_id=job.team_id,
            user_id=job.created_by,
            iteration_count=job.iteration_count,
            status="running",
        )

        while state.iteration_count < self.settings.max_iterations:
            next_agent, reason = route_next_agent(state)
            await self._append_event(
                db,
                job.team_id,
                job.id,
                event_type="route.decision",
                from_agent="supervisor",
                to_agent=next_agent,
                reason=reason,
                payload={"iteration": state.iteration_count},
            )

            if next_agent == "FINISH":
                break

            await self._append_event(
                db,
                job.team_id,
                job.id,
                event_type="agent.started",
                from_agent=next_agent,
                to_agent=None,
                reason=None,
                payload={},
            )

            failed = False
            try:
                if next_agent == "query_planner":
                    state, payload = await asyncio.wait_for(
                        run_query_planner(state, self.llm_client), self.settings.agent_timeout_sec
                    )
                elif next_agent == "paper_search":
                    async def event_hook(event_type: str, pl: dict) -> None:
                        await self._append_event(
                            db,
                            job.team_id,
                            job.id,
                            event_type=event_type,
                            from_agent="paper_search",
                            to_agent=None,
                            reason=None,
                            payload=pl,
                        )

                    state, payload = await asyncio.wait_for(
                        run_paper_search(state, self.gateway, event_hook=event_hook),
                        self.settings.agent_timeout_sec,
                    )
                elif next_agent == "evidence_scorer":
                    state, payload = await asyncio.wait_for(
                        run_evidence_scorer(state, self.llm_client), self.settings.agent_timeout_sec
                    )
                elif next_agent == "summary_writer":
                    state, payload = await asyncio.wait_for(
                        run_summary_writer(state, self.llm_client), self.settings.agent_timeout_sec
                    )
                elif next_agent == "quality_reviewer":
                    state, payload = await asyncio.wait_for(
                        run_quality_reviewer(state, self.llm_client), self.settings.agent_timeout_sec
                    )
                else:
                    payload = {"warning": "unknown agent"}
            except LLMUnavailableError as exc:
                state.warnings.append(str(exc))
                payload = {"warning": str(exc)}
                state.status = "failed"
                failed = True

            await self._append_event(
                db,
                job.team_id,
                job.id,
                event_type="agent.completed",
                from_agent=next_agent,
                to_agent=None,
                reason=None,
                payload=payload,
            )

            state.iteration_count += 1

            if state.status == "completed" or failed:
                break

        if state.status != "completed" and not state.summary_draft:
            state.summary_draft = "未能完成检索流程，请稍后重试。"

        # 持久化 job
        job.iteration_count = state.iteration_count
        job.status = "completed" if state.status == "completed" else "failed"
        job.final_output = state.final_output or state.summary_draft

        # 覆盖旧结果
        old_rows = await db.execute(select(SearchResult).where(SearchResult.job_id == job.id))
        for row in old_rows.scalars().all():
            await db.delete(row)

        for paper in state.ranked_papers:
            db.add(
                SearchResult(
                    job_id=job.id,
                    title=paper.get("title", ""),
                    authors=paper.get("authors", []),
                    abstract=paper.get("abstract"),
                    year=paper.get("year"),
                    source=paper.get("source"),
                    url=paper.get("url"),
                    score=paper.get("score", 0),
                    metadata_json=paper.get("metadata", {}),
                )
            )

        await self._append_event(
            db,
            job.team_id,
            job.id,
            event_type="workflow.completed" if job.status == "completed" else "workflow.failed",
            from_agent="supervisor",
            to_agent=None,
            reason=job.status,
            payload={"iteration_count": state.iteration_count},
        )

        await db.commit()
        await db.refresh(job)
        return job
