from __future__ import annotations

import json
import re
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import get_settings


class LLMUnavailableError(RuntimeError):
    pass


@dataclass
class LLMCallResult:
    content: str
    warning: str | None = None


def _strip_code_fence(text: str) -> str:
    if "```" not in text:
        return text.strip()
    parts = re.split(r"```(?:json)?", text, maxsplit=2, flags=re.IGNORECASE)
    if len(parts) >= 2:
        candidate = parts[1]
        return candidate.replace("```", "").strip()
    return text.strip()


def _extract_json(text: str) -> dict | list:
    cleaned = _strip_code_fence(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(1))


class LLMClient:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.openai_api_key
        self.model = model if model is not None else settings.default_model
        self.fallback_mode = settings.llm_fallback_mode.lower()
        self.force_heuristic = settings.llm_force_heuristic
        self.timeout_sec = settings.agent_timeout_sec
        self._client: ChatOpenAI | None = None

    def available(self) -> bool:
        return bool(self.api_key) and not self.force_heuristic

    def _ensure_client(self) -> ChatOpenAI:
        if not self._client:
            self._client = ChatOpenAI(
                api_key=self.api_key,
                model=self.model,
                temperature=0.2,
                max_tokens=2000,
                timeout=self.timeout_sec,
            )
        return self._client

    async def generate_text(self, system_prompt: str, user_prompt: str) -> LLMCallResult:
        if not self.available():
            if self.fallback_mode == "hard_fail":
                raise LLMUnavailableError("LLM API key missing or heuristic-only mode enabled")
            return LLMCallResult("", warning="LLM not available, using heuristic fallback.")

        client = self._ensure_client()
        response = await client.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
        return LLMCallResult(response.content)

    async def generate_json(self, system_prompt: str, user_prompt: str) -> tuple[dict | list | None, str | None]:
        result = await self.generate_text(system_prompt, user_prompt)
        if result.warning:
            return None, result.warning
        try:
            payload = _extract_json(result.content)
            return payload, None
        except json.JSONDecodeError:
            if self.fallback_mode == "hard_fail":
                raise LLMUnavailableError("LLM response is not valid JSON")
            return None, "LLM response invalid, using heuristic fallback."
