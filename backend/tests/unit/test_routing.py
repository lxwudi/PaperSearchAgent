from app.agents.state import WorkflowState
from app.agents.supervisor import route_next_agent


def test_route_initial_state() -> None:
    state = WorkflowState(
        job_id="job",
        query="test query",
        team_id="team",
        user_id="user",
    )
    next_agent, reason = route_next_agent(state)
    assert next_agent == "query_planner"
    assert "query plan" in reason


def test_route_after_query_plan() -> None:
    state = WorkflowState(
        job_id="job",
        query="test query",
        team_id="team",
        user_id="user",
        query_plan=[{"query": "test query", "priority": 1}],
    )
    next_agent, reason = route_next_agent(state)
    assert next_agent == "paper_search"
    assert "raw papers" in reason


def test_route_after_approved() -> None:
    state = WorkflowState(
        job_id="job",
        query="test query",
        team_id="team",
        user_id="user",
        query_plan=[{"query": "test query", "priority": 1}],
        raw_papers=[{"title": "x"}],
        ranked_papers=[{"title": "x", "score": 10}],
        summary_draft="## 核心发现\n## 建议阅读路径",
        review_result="APPROVED: ok",
    )
    next_agent, reason = route_next_agent(state)
    assert next_agent == "FINISH"
    assert "approved" in reason
