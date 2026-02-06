from fastapi import APIRouter

from code_rag.api.index import router as index_router
from code_rag.api.search import router as search_router
from code_rag.api.projects import router as projects_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(index_router, tags=["index"])
api_router.include_router(search_router, tags=["search"])
api_router.include_router(projects_router, tags=["projects"])
