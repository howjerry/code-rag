import asyncio
import logging
import threading
import traceback

from fastapi import APIRouter, HTTPException

from code_rag.config import settings
from code_rag.models.search import IndexRequest, IndexStatus
from code_rag.indexer.pipeline import run_index

logger = logging.getLogger(__name__)

router = APIRouter()

# 背景索引任務追蹤
_index_tasks: set[asyncio.Task] = set()
_index_lock = threading.Lock()


def get_index_tasks() -> set[asyncio.Task]:
    """取得所有背景索引任務（供 shutdown 使用）。"""
    return _index_tasks


@router.post("/index", response_model=IndexStatus)
async def trigger_index(req: IndexRequest):
    """觸發專案索引（背景執行）。"""
    from code_rag.main import get_qdrant, get_state_db, get_embedder

    state_db = get_state_db()
    qdrant = get_qdrant()
    embedder = get_embedder()

    # 路徑轉換
    container_path = str(settings.to_container_path(req.path))

    # 原子化檢查與設定狀態
    with _index_lock:
        status = state_db.get_index_status(req.project_name)
        if status and status["status"] == "running":
            raise HTTPException(400, f"Project '{req.project_name}' is already being indexed")
        state_db.set_index_status(req.project_name, "pending")

    # 背景執行索引
    async def _run():
        try:
            await asyncio.to_thread(
                run_index, req.project_name, container_path, qdrant, state_db, embedder
            )
        except Exception as e:
            logger.error("Index failed for '%s': %s\n%s", req.project_name, e, traceback.format_exc())
            state_db.set_index_status(req.project_name, "failed", error=str(e))

    task = asyncio.create_task(_run())
    _index_tasks.add(task)
    task.add_done_callback(_index_tasks.discard)

    return IndexStatus(project_name=req.project_name, status="pending")


@router.get("/index/{project_name}/status", response_model=IndexStatus)
async def get_index_status(project_name: str):
    """查詢索引進度。"""
    from code_rag.main import get_state_db

    state_db = get_state_db()
    status = state_db.get_index_status(project_name)
    if not status:
        raise HTTPException(404, f"Project '{project_name}' not found")
    return IndexStatus(
        project_name=project_name,
        status=status["status"],
        total_files=status["total_files"],
        processed_files=status["processed_files"],
        total_chunks=status["total_chunks"],
        error=status.get("error"),
    )
