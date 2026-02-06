import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from code_rag.config import settings
from code_rag.api.router import api_router
from code_rag.indexer.embedder import Embedder
from code_rag.storage.qdrant import QdrantStorage
from code_rag.storage.state import StateDB

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# 全域資源
_qdrant: QdrantStorage | None = None
_state_db: StateDB | None = None
_embedder: Embedder | None = None


def get_qdrant() -> QdrantStorage:
    assert _qdrant is not None
    return _qdrant


def get_state_db() -> StateDB:
    assert _state_db is not None
    return _state_db


def get_embedder() -> Embedder:
    assert _embedder is not None
    return _embedder


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _qdrant, _state_db, _embedder

    logger.info("Starting Code RAG API...")
    _qdrant = QdrantStorage()
    _qdrant.ensure_collection()
    logger.info("Qdrant connected: %s", settings.qdrant_url)

    _state_db = StateDB(settings.state_db_path)
    logger.info("State DB initialized: %s", settings.state_db_path)

    _embedder = Embedder()
    logger.info("Embedder initialized: %s @ %s", settings.embedding_model, settings.ollama_url)

    yield

    logger.info("Shutting down...")

    # 等待背景索引任務完成
    from code_rag.api.index import get_index_tasks
    tasks = get_index_tasks()
    if tasks:
        logger.info("Waiting for %d background index task(s) to finish...", len(tasks))
        await asyncio.gather(*tasks, return_exceptions=True)

    if _qdrant:
        _qdrant.client.close()
    if _embedder:
        _embedder.close()
    if _state_db:
        _state_db.close()


app = FastAPI(title="Code RAG", version="0.1.0", lifespan=lifespan)
app.include_router(api_router)


@app.get("/api/v1/health")
async def health():
    qdrant_ok = _qdrant.health_check() if _qdrant else False
    ollama_ok = _embedder.health_check() if _embedder else False
    return {
        "status": "ok" if (qdrant_ok and ollama_ok) else "degraded",
        "qdrant": "connected" if qdrant_ok else "disconnected",
        "ollama": "connected" if ollama_ok else "disconnected",
    }
