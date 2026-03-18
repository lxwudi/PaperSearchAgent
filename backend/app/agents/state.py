from dataclasses import dataclass, field


@dataclass
class WorkflowState:
    job_id: str
    query: str
    team_id: str
    user_id: str
    next_agent: str = "supervisor"
    iteration_count: int = 0
    status: str = "running"
    query_plan: list[dict] = field(default_factory=list)
    raw_papers: list[dict] = field(default_factory=list)
    ranked_papers: list[dict] = field(default_factory=list)
    facets: dict[str, int] = field(default_factory=dict)
    summary_draft: str | None = None
    review_result: str | None = None
    final_output: str | None = None
    warnings: list[str] = field(default_factory=list)
