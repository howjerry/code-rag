FROM python:3.12-slim

WORKDIR /app

# 安裝系統依賴（tree-sitter 編譯需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安裝 uv（快速 Python 套件管理）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 複製依賴定義並安裝
COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

# 複製原始碼（開發時會被 volume mount 覆蓋）
COPY src/ ./src/
COPY config/ ./config/

EXPOSE 8100

# 開發模式：uvicorn --reload（搭配 volume mount 實現 hot reload）
CMD ["uv", "run", "uvicorn", "code_rag.main:app", \
     "--host", "0.0.0.0", "--port", "8100", "--reload", \
     "--reload-dir", "/app/src"]
