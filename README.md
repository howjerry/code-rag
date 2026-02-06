# Code-RAG

Local codebase RAG system — indexes source code with tree-sitter semantic chunking, generates embeddings via Ollama, stores in Qdrant, and provides semantic search through a FastAPI API.

## Features

- **Semantic code chunking** — tree-sitter parsing for Python, JavaScript, TypeScript, Go, C#, Rust; text fallback for 30+ other languages
- **Incremental indexing** — SHA256 change detection skips unchanged files
- **Vector search** — cosine similarity search with optional project/language filtering
- **Project management** — index, search, and manage multiple codebases independently

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [Ollama](https://ollama.com/) running locally with the embedding model:
  ```bash
  ollama pull mxbai-embed-large
  ```

## Quick Start

1. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env — set PROJECTS_DIR to your projects root directory
   ```

2. Start services:
   ```bash
   docker compose up -d
   ```

3. Index a project:
   ```bash
   curl -X POST http://localhost:8100/api/v1/index \
     -H "Content-Type: application/json" \
     -d '{"project_name": "my-project", "path": "/Users/you/Development/my-project"}'
   ```

4. Search:
   ```bash
   curl "http://localhost:8100/api/v1/search?q=authentication+logic&project=my-project"
   ```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/index` | Trigger project indexing |
| GET | `/api/v1/index/{project}/status` | Check indexing progress |
| GET | `/api/v1/search?q=&project=&language=&limit=` | Semantic code search |
| GET | `/api/v1/projects` | List indexed projects |
| DELETE | `/api/v1/projects/{project}` | Remove project from index |
| GET | `/api/v1/health` | Health check (Qdrant + Ollama) |

## Local Development

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run uvicorn code_rag.main:app --host 0.0.0.0 --port 8100 --reload --reload-dir src
```

## Services & Ports

| Service | Port | Notes |
|---------|------|-------|
| API | 8100 | FastAPI |
| Qdrant HTTP | 6335 | Vector database |
| Qdrant gRPC | 6336 | Vector database |
| Ollama | 11434 | External, not included in docker-compose |
