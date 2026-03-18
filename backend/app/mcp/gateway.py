from __future__ import annotations

import asyncio
import json
import re
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

from app.agents.state import WorkflowState
from app.core.config import get_settings

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except Exception:  # noqa: BLE001
    ClientSession = None  # type: ignore[assignment]
    StdioServerParameters = None  # type: ignore[assignment]
    stdio_client = None  # type: ignore[assignment]


EventHook = Callable[[str, dict], None | Any]


def _tool_to_dict(tool: Any) -> dict:
    if isinstance(tool, dict):
        return tool
    return {
        "name": getattr(tool, "name", ""),
        "description": getattr(tool, "description", ""),
        "input_schema": getattr(tool, "inputSchema", None),
    }


def _extract_json_blob(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _find_items(payload: Any) -> list[dict]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [p for p in payload if isinstance(p, dict)]
    if isinstance(payload, dict):
        for key in ("papers", "results", "items", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [p for p in value if isinstance(p, dict)]
    return []


def _normalize_paper(raw: dict) -> dict:
    return {
        "title": raw.get("title", ""),
        "authors": raw.get("authors", []),
        "abstract": raw.get("abstract"),
        "year": raw.get("year"),
        "source": raw.get("source"),
        "url": raw.get("url"),
        "metadata": raw.get("metadata", {}),
    }


_CLI_TITLE_RE = re.compile(r"^\s*(?:\W{0,2}\s*)?\d+\.\s+(.+?)\s*$")
_CLI_ID_RE = re.compile(r"^\s*ID:\s*(.+?)\s*$", re.IGNORECASE)
_CLI_AUTHORS_RE = re.compile(r"^\s*Authors:\s*(.+?)\s*$", re.IGNORECASE)
_CLI_DATE_RE = re.compile(r"^\s*Date:\s*(.+?)\s*$", re.IGNORECASE)
_CLI_PDF_RE = re.compile(r"^\s*PDF:\s*(https?://\S+)\s*$", re.IGNORECASE)


def _parse_cli_search_output(text: str, source: str) -> list[dict]:
    papers: list[dict] = []
    current: dict[str, Any] | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if current:
            id_match = _CLI_ID_RE.match(line)
            if id_match:
                current["metadata"]["paper_id"] = id_match.group(1).strip()
                continue

            authors_match = _CLI_AUTHORS_RE.match(line)
            if authors_match:
                names = [name.strip() for name in authors_match.group(1).split(",")]
                current["authors"] = [name for name in names if name]
                continue

            date_match = _CLI_DATE_RE.match(line)
            if date_match:
                date_text = date_match.group(1).strip()
                current["metadata"]["published_at"] = date_text
                if len(date_text) >= 4 and date_text[:4].isdigit():
                    current["year"] = int(date_text[:4])
                continue

            pdf_match = _CLI_PDF_RE.match(line)
            if pdf_match:
                current["url"] = pdf_match.group(1).strip()
                continue

        title_match = _CLI_TITLE_RE.match(line)
        if title_match:
            if current and current.get("title"):
                papers.append(current)
            current = {
                "title": title_match.group(1).strip(),
                "authors": [],
                "abstract": None,
                "year": None,
                "source": source,
                "url": None,
                "metadata": {"retrieval_mode": "cli_fallback"},
            }
            continue

    if current and current.get("title"):
        papers.append(current)

    return papers


class MCPClientManager:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._started = False
        self._session: ClientSession | None = None
        self._client_ctx = None
        self._tools: list[dict] = []

    async def start(self) -> None:
        if self._started:
            return
        if ClientSession is None or stdio_client is None or StdioServerParameters is None:
            raise RuntimeError("mcp client not available")
        args = shlex.split(self.settings.mcp_args)
        params = StdioServerParameters(command=self.settings.mcp_command, args=args)
        self._client_ctx = stdio_client(params)
        read, write = await self._client_ctx.__aenter__()
        self._session = ClientSession(read, write)
        await self._session.__aenter__()
        await self._session.initialize()
        tools_result = await self._session.list_tools()
        tools = getattr(tools_result, "tools", tools_result)
        self._tools = [_tool_to_dict(t) for t in tools]
        self._started = True

    async def stop(self) -> None:
        if self._session:
            await self._session.__aexit__(None, None, None)
        if self._client_ctx:
            await self._client_ctx.__aexit__(None, None, None)
        self._session = None
        self._client_ctx = None
        self._tools = []
        self._started = False

    @property
    def started(self) -> bool:
        return self._started

    @property
    def tools(self) -> list[dict]:
        return self._tools

    def select_search_tool(self) -> str | None:
        if self.settings.mcp_search_tool:
            return self.settings.mcp_search_tool
        for tool in self._tools:
            name = tool.get("name", "").lower()
            if "search" in name or "paper" in name or "literature" in name:
                return tool.get("name")
        return self._tools[0].get("name") if self._tools else None

    async def call_tool(self, name: str, args: dict) -> Any:
        if not self._session:
            raise RuntimeError("mcp session not started")
        return await self._session.call_tool(name, args)


class ScientificPaperGateway:
    def __init__(self, client_manager: MCPClientManager, startup_warning: str | None = None) -> None:
        self.client_manager = client_manager
        self.settings = get_settings()
        self.startup_warning = startup_warning
        self._cache: dict[str, tuple[float, list[dict]]] = {}

    async def _emit_event(self, event_hook: EventHook | None, event_type: str, payload: dict) -> None:
        if not event_hook:
            return
        maybe = event_hook(event_type, payload)
        if asyncio.iscoroutine(maybe):
            await maybe

    def _run_cli_search_sync(self, query: str) -> list[dict]:
        args = shlex.split(self.settings.mcp_args)
        command = [
            self.settings.mcp_command,
            *args,
            "search-papers",
            f"--source={self.settings.mcp_cli_source}",
            f"--query={query}",
            f"--field={self.settings.mcp_cli_field}",
            f"--count={self.settings.mcp_cli_count}",
        ]

        completed = subprocess.run(
            command,
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.settings.mcp_cli_timeout_sec,
            check=False,
        )
        output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()

        if completed.returncode != 0:
            details = output[:500] if output else "no output"
            raise RuntimeError(f"CLI search failed (exit={completed.returncode}): {details}")

        return _parse_cli_search_output(output, self.settings.mcp_cli_source)

    async def _search_via_cli(
        self,
        query: str,
        reason: str,
        event_hook: EventHook | None = None,
    ) -> list[dict]:
        if not self.settings.mcp_cli_fallback_enabled:
            return []

        await self._emit_event(
            event_hook,
            "tool.started",
            {"tool": "cli.search", "query": query, "reason": reason},
        )

        try:
            papers = await asyncio.to_thread(self._run_cli_search_sync, query)
        except Exception as exc:  # noqa: BLE001
            await self._emit_event(
                event_hook,
                "tool.failed",
                {"tool": "cli.search", "query": query, "error": str(exc), "reason": reason},
            )
            return []

        await self._emit_event(
            event_hook,
            "tool.completed",
            {
                "tool": "cli.search",
                "query": query,
                "count": len(papers),
                "source": self.settings.mcp_cli_source,
                "reason": reason,
            },
        )
        return papers

    async def search(self, query: str, event_hook: EventHook | None = None) -> list[dict]:
        now = time.monotonic()
        cached = self._cache.get(query)
        if cached and (now - cached[0]) < self.settings.mcp_cache_ttl_sec:
            return cached[1]

        await self._emit_event(event_hook, "tool.started", {"tool": "mcp.search", "query": query})

        if not self.client_manager.started:
            reason = self.startup_warning or "mcp session not started"
            await self._emit_event(
                event_hook,
                "tool.failed",
                {"tool": "mcp.search", "query": query, "error": reason},
            )
            fallback = await self._search_via_cli(query, reason=reason, event_hook=event_hook)
            self._cache[query] = (time.monotonic(), fallback)
            return fallback

        tool_name = self.client_manager.select_search_tool()
        if not tool_name:
            reason = "tool not found"
            await self._emit_event(
                event_hook,
                "tool.failed",
                {"tool": "mcp.search", "query": query, "error": reason},
            )
            fallback = await self._search_via_cli(query, reason=reason, event_hook=event_hook)
            self._cache[query] = (time.monotonic(), fallback)
            return fallback

        payloads = [
            {"query": query},
            {"q": query},
            {"keywords": query},
            {"text": query},
        ]

        result = None
        last_error: Exception | None = None
        for payload in payloads:
            try:
                result = await asyncio.wait_for(
                    self.client_manager.call_tool(tool_name, payload),
                    timeout=self.settings.mcp_timeout_sec,
                )
                last_error = None
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc

        if last_error:
            reason = str(last_error)
            await self._emit_event(
                event_hook,
                "tool.failed",
                {"tool": "mcp.search", "query": query, "error": reason},
            )
            fallback = await self._search_via_cli(query, reason=reason, event_hook=event_hook)
            self._cache[query] = (time.monotonic(), fallback)
            return fallback

        items: list[dict] = []
        content = getattr(result, "content", result)
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if "json" in item:
                        items.extend(_find_items(item["json"]))
                    elif "text" in item:
                        try:
                            items.extend(_find_items(_extract_json_blob(item["text"])))
                        except Exception:
                            continue
                    elif "data" in item:
                        items.extend(_find_items(item["data"]))
                elif hasattr(item, "text"):
                    try:
                        items.extend(_find_items(_extract_json_blob(item.text)))
                    except Exception:
                        continue
                elif hasattr(item, "json"):
                    items.extend(_find_items(item.json))
        elif isinstance(content, dict):
            items.extend(_find_items(content))

        normalized = [_normalize_paper(item) for item in items]
        if not normalized:
            fallback = await self._search_via_cli(
                query,
                reason="mcp returned no items",
                event_hook=event_hook,
            )
            self._cache[query] = (time.monotonic(), fallback)
            return fallback

        await self._emit_event(
            event_hook,
            "tool.completed",
            {"tool": "mcp.search", "query": query, "count": len(normalized), "tool_name": tool_name},
        )

        self._cache[query] = (time.monotonic(), normalized)
        return normalized


async def run_paper_search(
    state: WorkflowState,
    gateway: ScientificPaperGateway,
    event_hook: EventHook | None = None,
) -> tuple[WorkflowState, dict]:
    all_items: list[dict] = []
    for item in state.query_plan:
        query = item.get("query")
        if not query:
            continue
        results = await gateway.search(query, event_hook=event_hook)
        all_items.extend(results)

    seen = set()
    deduped = []
    for p in all_items:
        key = (p.get("title"), p.get("year"), p.get("source"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(p)

    state.raw_papers = deduped
    return state, {"raw_papers": deduped, "count": len(deduped)}
