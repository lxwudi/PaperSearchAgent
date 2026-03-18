from __future__ import annotations

from app.agents.state import WorkflowState
from app.services.llm_client import LLMClient


SYSTEM_PROMPT = """
你是学术检索的 Query Planner。请输出 JSON 对象：
{
  "query_plan": [
    {
      "query": "...",
      "priority": 1,
      "filters": {
        "year_start": 2020,
        "year_end": 2025,
        "venues": ["arXiv", "Nature"],
        "keywords": ["multi-agent", "retrieval"]
      }
    }
  ]
}
规则：
- query_plan 最多 4 条
- priority 为 1-3
- filters 可选，没有就省略
- 仅输出 JSON，不要附加说明
""".strip()


async def run_query_planner(
    state: WorkflowState, llm: LLMClient | None = None
) -> tuple[WorkflowState, dict]:
    if llm:
        payload, warning = await llm.generate_json(
            SYSTEM_PROMPT,
            f"用户问题：{state.query}",
        )
        if warning:
            state.warnings.append(warning)
        if isinstance(payload, dict) and isinstance(payload.get("query_plan"), list):
            state.query_plan = payload["query_plan"]
            return state, {"query_plan": state.query_plan, "llm_used": True}

    terms = [t.strip() for t in state.query.split(" ") if t.strip()]
    plan = [{"query": " ".join(terms), "priority": 1}]
    if len(terms) > 2:
        plan.append({"query": " ".join(terms[:2]), "priority": 2})

    state.query_plan = plan
    return state, {"query_plan": plan, "llm_used": False}
