"""索引 pipeline：掃描 → 分塊 → 嵌入 → 寫入。"""

import logging
from pathlib import Path

from code_rag.config import settings
from code_rag.indexer.scanner import scan_files
from code_rag.indexer.chunker import chunk_code
from code_rag.indexer.text_chunker import chunk_text
from code_rag.indexer.embedder import Embedder
from code_rag.indexer.hasher import file_hash
from code_rag.storage.qdrant import QdrantStorage
from code_rag.storage.state import StateDB
from code_rag.utils.language import supports_treesitter

logger = logging.getLogger(__name__)


def run_index(
    project_name: str,
    project_path: str,
    qdrant: QdrantStorage,
    state_db: StateDB,
    embedder: Embedder,
):
    """執行完整的索引 pipeline。"""
    path = Path(project_path)
    if not path.exists():
        raise FileNotFoundError(f"Project path not found: {project_path}")

    qdrant.ensure_collection()

    # 掃描檔案
    files = scan_files(path)
    total_files = len(files)
    state_db.set_index_status(project_name, "running", total_files=total_files)

    # 取得已知的檔案清單（用於偵測刪除）
    known_files = state_db.get_all_file_paths(project_name)
    current_files = set()

    processed = 0
    total_chunks = 0

    for file_info in files:
        file_path = file_info["path"]
        relative_path = file_info["relative_path"]
        language = file_info["language"]
        current_files.add(relative_path)

        try:
            # 增量檢查：hash 沒變就跳過
            current_hash = file_hash(file_path)
            stored_hash = state_db.get_file_hash(project_name, relative_path)
            if stored_hash == current_hash:
                processed += 1
                continue

            # 讀取檔案內容
            source = Path(file_path).read_text(encoding="utf-8", errors="ignore")

            # 分塊
            if supports_treesitter(language):
                chunks = chunk_code(source, language, relative_path, project_name)
                if not chunks:
                    # tree-sitter 沒產出 chunks，fallback
                    chunks = chunk_text(source, relative_path, project_name, language)
            else:
                chunks = chunk_text(source, relative_path, project_name, language)

            if not chunks:
                processed += 1
                state_db.set_file_hash(project_name, relative_path, current_hash)
                continue

            # 嵌入（先完成嵌入，確認成功後才刪除舊資料）
            texts = [c["content"] for c in chunks]
            vectors = embedder.embed_batch(texts)

            # 刪除此檔案的舊向量，再寫入新的
            qdrant.delete_by_file(project_name, relative_path)
            qdrant.upsert_chunks(chunks, vectors)

            # 更新 hash
            state_db.set_file_hash(project_name, relative_path, current_hash)
            total_chunks += len(chunks)

        except Exception as e:
            logger.error("Error processing %s: %s", file_path, e)

        processed += 1
        if processed % 50 == 0:
            state_db.set_index_status(
                project_name, "running",
                total_files=total_files,
                processed_files=processed,
                total_chunks=total_chunks,
            )

    # 刪除已不存在的檔案對應的向量
    deleted_files = known_files - current_files
    for deleted_path in deleted_files:
        qdrant.delete_by_file(project_name, deleted_path)
        state_db.remove_file(project_name, deleted_path)
        logger.info("Removed deleted file from index: %s", deleted_path)

    # 最終統計
    stats = qdrant.get_project_stats(project_name)
    state_db.set_index_status(
        project_name, "completed",
        total_files=total_files,
        processed_files=processed,
        total_chunks=stats["chunk_count"],
    )
    logger.info(
        "Indexing complete for '%s': %d files, %d chunks",
        project_name, processed, stats["chunk_count"],
    )
