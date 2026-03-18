from __future__ import annotations

from app.agents.state import WorkflowState
from app.services.llm_client import LLMClient


SYSTEM_PROMPT = """
你是学术检索结果总结者。请输出中文 Markdown，必须包含以下标题：
# 文献检索总结
## 核心发现
## 建议阅读路径
## 研究空白与趋势
规则：
- 结合给定论文，不要编造不存在的论文
- 每个小节 3-6 条要点
- 仅输出 Markdown，不要附加说明
""".strip()


async def run_summary_writer(
    state: WorkflowState, llm: LLMClient | None = None
) -> tuple[WorkflowState, dict]:
    top = state.ranked_papers[:8]

    if llm:
        result = await llm.generate_text(
            SYSTEM_PROMPT,
            f"论文列表：{top}",
        )
        if result.warning:
            state.warnings.append(result.warning)
        if result.content:
            draft = result.content
            if state.warnings:
                warning_block = "\n".join([f"> 警告：{w}" for w in state.warnings])
                draft = f"{warning_block}\n\n{draft}"
            state.summary_draft = draft
            return state, {"summary_preview": draft[:500], "paper_count": len(top), "llm_used": True}

    lines = ["# 文献检索总结", "", "## 核心发现"]
    for idx, paper in enumerate(top, start=1):
        lines.append(
            f"{idx}. **{paper.get('title')}** ({paper.get('year')}) - {paper.get('source')}"
        )

    lines.append("")
    lines.append("## 建议阅读路径")
    for paper in top[:3]:
        lines.append(f"- {paper.get('title')} -> {paper.get('url')}")

    lines.append("")
    lines.append("## 研究空白与趋势")
    lines.append("- 需要更多跨学科评测与可重复性验证的研究。")
    lines.append("- 对高质量数据与评测基准的需求仍然明显。")
    lines.append("- 真实场景下的系统级实验仍相对不足。")

    draft = "\n".join(lines)
    if state.warnings:
        warning_block = "\n".join([f"> 警告：{w}" for w in state.warnings])
        draft = f"{warning_block}\n\n{draft}"
    state.summary_draft = draft
    return state, {"summary_preview": draft[:500], "paper_count": len(top), "llm_used": False}
