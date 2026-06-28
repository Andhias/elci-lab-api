from fastapi import APIRouter, Query

from app.schemas.common import SearchResponse, SearchResult

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search(q: str = Query(default="")) -> SearchResponse:
    return SearchResponse(
        query=q,
        results=[
            SearchResult(
                type="error_code",
                id="demo-error-e23",
                title="Monarch - Error E23",
                summary="Door lock fault placeholder",
                match_type="Exact Match",
                confidence="high",
            ),
            SearchResult(
                type="procedure",
                id="demo-procedure-1",
                title="Otis Escalator Safety Chain",
                summary="Procedure placeholder",
                match_type="Partial Match",
                confidence="medium",
            ),
        ],
    )
