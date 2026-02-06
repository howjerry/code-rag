# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Code-RAG is a local codebase RAG (Retrieval-Augmented Generation) system. It indexes source code into semantic chunks, generates embeddings via Ollama, stores them in Qdrant, and exposes a FastAPI search API.

## Development Commands

```bash
# Install dependencies (requires uv)
uv sync

# Run locally (requires Qdrant + Ollama running)
uv run uvicorn code_rag.main:app --host 0.0.0.0 --port 8100 --reload --reload-dir src

# Run with Docker Compose (starts Qdrant + API)
docker compose up -d

# Run tests
uv run pytest
uv run pytest tests/test_specific.py::test_name  # single test
```

## Architecture

**Data flow:** Scan files → Detect language → Chunk (tree-sitter or text) → Embed (Ollama) → Store (Qdrant)

### Key layers

- **API** (`src/code_rag/api/`): FastAPI endpoints — index triggers, search queries, project management. Routes under `/api/v1/`.
- **Indexer** (`src/code_rag/indexer/`): Orchestrated by `pipeline.py`. Scanner discovers files respecting .gitignore; chunker uses tree-sitter for 6 languages (Python, JS, TS, Go, C#, Rust) with text fallback; embedder calls Ollama `/api/embed`; hasher provides SHA256 for incremental indexing.
- **Storage** (`src/code_rag/storage/`): `qdrant.py` wraps vector operations (COSINE distance, 1024 dims). `state.py` is a SQLite DB tracking file hashes and indexing status for incremental updates.
- **Models** (`src/code_rag/models/`): Pydantic models for search results, index requests, and project metadata.

### Path translation

The app runs in Docker but indexes host filesystem paths. `config.py` provides `to_container_path()` / `to_host_path()` to convert between host paths (e.g., `/Users/.../Development/project`) and container mount paths (`/data/projects/project`).

### Indexing is incremental

Pipeline compares SHA256 hashes against `state.db` — unchanged files are skipped entirely. Deleted files are detected and removed from the index.

## External Services

- **Qdrant** (vector DB): ports 6335/6336 — included in docker-compose
- **Ollama** (embeddings): port 11434 — must be running externally, model `mxbai-embed-large`
- **API**: port 8100

## Configuration

- `src/code_rag/config.py`: Pydantic Settings, all configurable via environment variables
- `.env`: Set `PROJECTS_DIR` to your local projects root directory
