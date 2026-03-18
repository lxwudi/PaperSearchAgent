from pydantic import BaseModel


class FavoriteDetailResponse(BaseModel):
    id: str
    team_id: str
    user_id: str
    result_id: str
    title: str
    authors: list[str]
    abstract: str | None
    year: int | None
    source: str | None
    url: str | None
    score: int
    metadata: dict
