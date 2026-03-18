from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "papersearch-agent"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = True

    database_url: str = "sqlite+aiosqlite:///./papersearch.db"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = "please-change-me"
    access_token_expire_minutes: int = 60
    refresh_token_expire_minutes: int = 60 * 24 * 7
    jwt_algorithm: str = "HS256"

    openai_api_key: str = ""
    default_model: str = "gpt-4o-mini"
    llm_fallback_mode: str = "graceful"
    llm_force_heuristic: bool = False

    max_iterations: int = 12
    max_tokens: int = 100000
    agent_timeout_sec: int = 120

    mcp_command: str = "npx"
    mcp_args: str = "-y @futurelab-studio/latest-science-mcp@latest"
    mcp_server_name: str = "scientific-papers"
    mcp_search_tool: str = ""
    mcp_timeout_sec: int = 30
    mcp_cache_ttl_sec: int = 300
    mcp_cli_fallback_enabled: bool = True
    mcp_cli_source: str = "arxiv"
    mcp_cli_field: str = "all"
    mcp_cli_count: int = 20
    mcp_cli_timeout_sec: int = 120

    job_executor_mode: str = "inline"
    worker_poll_interval: int = 3
    ws_poll_interval_sec: float = 1.0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
