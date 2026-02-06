"""Ollama embedding 客戶端。"""

import logging

import httpx

from code_rag.config import settings

logger = logging.getLogger(__name__)


class Embedder:
    def __init__(self):
        self.url = f"{settings.ollama_url}/api/embed"
        self.model = settings.embedding_model
        self.batch_size = settings.embedding_batch_size
        self.client = httpx.Client(timeout=120.0)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批次嵌入文字，回傳向量清單。"""
        all_vectors = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            resp = self.client.post(
                self.url,
                json={"model": self.model, "input": batch},
            )
            resp.raise_for_status()
            data = resp.json()
            all_vectors.extend(data["embeddings"])
        return all_vectors

    def embed_single(self, text: str) -> list[float]:
        """嵌入單一文字。"""
        return self.embed_batch([text])[0]

    def health_check(self) -> bool:
        try:
            resp = self.client.get(settings.ollama_url)
            return resp.status_code == 200
        except Exception:
            return False

    def close(self):
        self.client.close()
