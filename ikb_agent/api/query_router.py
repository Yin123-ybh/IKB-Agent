from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.deps import get_query_service
from ..models import QueryRequest, QueryResponse
from ..services import QueryService

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest, service: QueryService = Depends(get_query_service)) -> QueryResponse:
    return service.query(request)

