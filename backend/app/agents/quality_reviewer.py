from __future__ import annotations

from app.agents.state import WorkflowState
from app.services.llm_client import LLMClient


SYSTEM_PROMPT = """
你是质量审查员。请输出 JSON：
{
  "review_result": "APPROVED" | "REVISION_NEEDED",
  "reason": "..."
}
规则：
- 如果摘要缺少关键标题，或引用论文过少，应返回 REVISION_NEEDED
- 仅输出 JSON
""".strip()


async def run_quality_reviewer(
    state: WorkflowState, llm: LLMClient | None = None
) -> tuple[WorkflowState, dict]:
    draft = state.summary_draft or ""

    if llm:
        payload, warning = await llm.generate_json(
            SYSTEM_PROMPT,
            f"摘要：{draft}\n\n论文数量：{len(state.ranked_papers)}",
        )
        if warning:
            state.warnings.append(warning)
        if isinstance(payload, dict) and "review_result" in payload:
            result = f"{payload['review_result']}: {payload.get('reason', '')}".strip()
            state.review_result = result
            if str(payload["review_result"]).startswith("APPROVED"):
                state.final_output = draft
                state.status = "completed"
            else:
                state.status = "running"
            return state, {"review_result": state.review_result, "llm_used": True}

    has_core_sections = "## 核心发现" in draft and "## 建议阅读路径" in draft
    has_items = len(state.ranked_papers) > 0

    if has_core_sections and has_items:
        result = "APPROVED: summary structure and evidence coverage are acceptable"
        state.review_result = result
        state.final_output = draft
        state.status = "completed"
    else:
        result = "REVISION_NEEDED: missing required sections or no ranked papers"
        state.review_result = result
        state.status = "running"

    return state, {"review_result": state.review_result, "llm_used": False}
