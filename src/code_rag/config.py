from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "code_chunks"
    ollama_url: str = "http://localhost:11434"
    embedding_model: str = "mxbai-embed-large"
    embedding_dims: int = 1024
    embedding_batch_size: int = 32
    state_db_path: str = "/app/data/state.db"
    projects_base_path: str = "/data/projects"
    # 用戶本地的絕對路徑前綴（容器內無法 expanduser，必須是絕對路徑）
    projects_host_prefix: str = "/Users/chc/Development"
    chunk_max_chars: int = 800
    chunk_overlap_chars: int = 80

    def to_container_path(self, host_path: str) -> Path:
        """將用戶本地路徑轉換為容器內路徑。"""
        # 直接做字串替換，不依賴 expanduser（容器內 home 不同）
        host_prefix = self.projects_host_prefix.rstrip("/")
        if host_path.startswith(host_prefix):
            relative = host_path[len(host_prefix) :].lstrip("/")
            return Path(self.projects_base_path) / relative
        return Path(self.projects_base_path) / Path(host_path).name

    def to_host_path(self, container_path: str) -> str:
        """將容器內路徑還原為用戶本地路徑。"""
        base = self.projects_base_path.rstrip("/")
        if container_path.startswith(base):
            relative = container_path[len(base) :].lstrip("/")
            return str(Path(self.projects_host_prefix) / relative)
        return container_path

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
