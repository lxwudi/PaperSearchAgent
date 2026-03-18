from datetime import datetime
from pydantic import BaseModel


class APIMessage(BaseModel):
    message: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class Pagination(BaseModel):
    page: int = 1
    page_size: int = 20


class EventPayload(BaseModel):
    event_type: str
    timestamp: datetime
    payload: dict
