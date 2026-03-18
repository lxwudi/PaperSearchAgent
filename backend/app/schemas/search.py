from datetime import datetime
from pydantic import BaseModel, Field


class SearchJobCreateRequest(BaseModel):
    team_id: str
    query: str = Field(min_length=3, max_length=2000)


class SearchJobResponse(BaseModel):
    id: str
    team_id: str
    query: str
    status: str
    iteration_count: int
    final_output: str | None
    created_at: datetime
    updated_at: datetime


class SearchResultResponse(BaseModel):
    id: str
    title: str
    authors: list[str]
    abstract: str | None
    year: int | None
    source: str | None
    url: str | None
    score: int
    metadata: dict


class SearchEventResponse(BaseModel):
    id: str
    event_type: str
    from_agent: str | None
    to_agent: str | None
    reason: str | None
    payload: dict
    created_at: datetime


class FavoriteCreateRequest(BaseModel):
    team_id: str
    result_id: str


class FavoriteResponse(BaseModel):
    id: str
    team_id: str
    user_id: str
    result_id: str


class ExportCreateRequest(BaseModel):
    team_id: str
    job_id: str
    export_type: str = Field(pattern="^(pdf|csv)$")


class ExportResponse(BaseModel):
    id: str
    team_id: str
    job_id: str
    export_type: str
    status: str
    file_path: str | None
