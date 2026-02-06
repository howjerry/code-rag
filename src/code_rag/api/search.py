import asyncio

from fastapi import APIRouter, Query

from code_rag.config import settings
from code_rag.models.search import SearchResult

router = APIRouter()


@router.get("/search", response_model=list[SearchResult])
async def search(
    q: str = Query(..., description="搜尋查詢"),
    project: str | None = Query(None, description="限定專案"),
    language: str | None = Query(None, description="限定語言"),
    limit: int = Query(10, ge=1, le=100, description="回傳數量"),
):
    """語意搜尋 codebase。"""
    from code_rag.main import get_qdrant, get_embedder

    embedder = get_embedder()
    qdrant = get_qdrant()

    query_vector = await asyncio.to_thread(embedder.embed_single, q)
    results = qdrant.search(
        query_vector=query_vector,
        limit=limit,
        project_name=project,
        language=language,
    )

    return [
        SearchResult(
            content=r["content"],
            file_path=settings.to_host_path(r["file_path"]),
            project_name=r["project_name"],
            language=r["language"],
            chunk_type=r.get("chunk_type", "code"),
            name=r.get("name"),
            start_line=r.get("start_line", 0),
            end_line=r.get("end_line", 0),
            score=r["score"],
        )
        for r in results
    ]
