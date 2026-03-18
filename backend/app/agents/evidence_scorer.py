from __future__ import annotations

from app.agents.state import WorkflowState
from app.services.llm_client import LLMClient


SYSTEM_PROMPT = """
你是文献结果评分器。请输出 JSON：
{
  "ranked_papers": [
    {
      "title": "...",
      "authors": ["..."],
      "abstract": "...",
      "year": 2024,
      "source": "arXiv",
      "url": "https://...",
      "metadata": {"provider": "..."},
      "score": 1-100
    }
  ],
  "facets": {"arXiv": 3, "Nature": 2}
}
规则：
- ranked_papers 必须包含输入中的论文（可调整顺序），不要新增不存在的论文
- score 为 1-100 的整数
- 仅输出 JSON
""".strip()


async def run_evidence_scorer(
    state: WorkflowState, llm: LLMClient | None = None
) -> tuple[WorkflowState, dict]:
    if llm:
        payload, warning = await llm.generate_json(
            SYSTEM_PROMPT,
            f"论文列表（最多30条）：{state.raw_papers[:30]}",
        )
        if warning:
            state.warnings.append(warning)
        if isinstance(payload, dict) and isinstance(payload.get("ranked_papers"), list):
            ranked = payload["ranked_papers"]
            for paper in ranked:
                try:
                    paper["score"] = int(paper.get("score", 0))
                except (TypeError, ValueError):
                    paper["score"] = 1
            ranked.sort(key=lambda x: x.get("score", 0), reverse=True)
            state.ranked_papers = ranked
            state.facets = payload.get("facets", {})
            return state, {
                "ranked_count": len(ranked),
                "facets": state.facets,
                "llm_used": True,
            }

    ranked = []
    for idx, paper in enumerate(state.raw_papers):
        metadata = paper.get("metadata", {})
        relevance = metadata.get("relevance", 0.5)
        score = int(relevance * 100) - idx
        enriched = dict(paper)
        enriched["score"] = max(score, 1)
        ranked.append(enriched)

    ranked.sort(key=lambda x: x["score"], reverse=True)
    state.ranked_papers = ranked

    facets: dict[str, int] = {}
    for p in ranked:
        source = p.get("source") or "unknown"
        facets[source] = facets.get(source, 0) + 1
    state.facets = facets

    return state, {"ranked_count": len(ranked), "facets": facets, "llm_used": False}
