from typing import Any

from pydantic import BaseModel


class SearchResult(BaseModel):
    type: str
    id: str
    title: str
    summary: str
    match_type: str
    confidence: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


class GenericMessageResponse(BaseModel):
    message: str
    data: dict[str, Any] | None = None
