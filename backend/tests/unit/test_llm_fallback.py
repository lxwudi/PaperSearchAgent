import os

import pytest

from app.agents.query_planner import run_query_planner
from app.agents.state import WorkflowState
from app.core.config import get_settings
from app.services.llm_client import LLMClient, LLMUnavailableError


@pytest.mark.asyncio
async def test_llm_fallback_graceful() -> None:
    original_mode = os.environ.get("LLM_FALLBACK_MODE")
    original_key = os.environ.get("OPENAI_API_KEY")
    os.environ["LLM_FALLBACK_MODE"] = "graceful"
    os.environ["OPENAI_API_KEY"] = ""
    get_settings.cache_clear()
    try:
        llm = LLMClient()
        state = WorkflowState(
            job_id="job",
            query="test query",
            team_id="team",
            user_id="user",
        )
        state, payload = await run_query_planner(state, llm)
        assert payload["llm_used"] is False
        assert state.query_plan
        assert state.warnings
    finally:
        if original_mode is None:
            os.environ.pop("LLM_FALLBACK_MODE", None)
        else:
            os.environ["LLM_FALLBACK_MODE"] = original_mode
        if original_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = original_key
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_llm_fallback_hard_fail() -> None:
    original_mode = os.environ.get("LLM_FALLBACK_MODE")
    original_key = os.environ.get("OPENAI_API_KEY")
    os.environ["LLM_FALLBACK_MODE"] = "hard_fail"
    os.environ["OPENAI_API_KEY"] = ""
    get_settings.cache_clear()
    try:
        llm = LLMClient()
        state = WorkflowState(
            job_id="job",
            query="test query",
            team_id="team",
            user_id="user",
        )
        with pytest.raises(LLMUnavailableError):
            await run_query_planner(state, llm)
    finally:
        if original_mode is None:
            os.environ.pop("LLM_FALLBACK_MODE", None)
        else:
            os.environ["LLM_FALLBACK_MODE"] = original_mode
        if original_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = original_key
        get_settings.cache_clear()
