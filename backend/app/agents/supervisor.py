from __future__ import annotations

from app.agents.state import WorkflowState


def route_next_agent(state: WorkflowState) -> tuple[str, str]:
    if state.iteration_count >= 12:
        return "FINISH", "hit max iterations"

    if not state.query_plan:
        return "query_planner", "no query plan"

    if not state.raw_papers:
        return "paper_search", "no raw papers"

    if not state.ranked_papers:
        return "evidence_scorer", "no ranked papers"

    if not state.summary_draft:
        return "summary_writer", "no summary draft"

    if not state.review_result:
        return "quality_reviewer", "no review result"

    if state.review_result.startswith("APPROVED"):
        return "FINISH", "review approved"

    return "summary_writer", "revision needed"
