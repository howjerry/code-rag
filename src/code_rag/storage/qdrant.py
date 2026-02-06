import uuid
import logging

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from code_rag.config import settings

logger = logging.getLogger(__name__)


class QdrantStorage:
    def __init__(self):
        self.client = QdrantClient(url=settings.qdrant_url)
        self.collection = settings.qdrant_collection

    def ensure_collection(self):
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection not in collections:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=settings.embedding_dims,
                    distance=Distance.COSINE,
                ),
            )
            # 建立 payload 索引加速過濾
            for field, schema in [
                ("project_name", PayloadSchemaType.KEYWORD),
                ("language", PayloadSchemaType.KEYWORD),
                ("file_path", PayloadSchemaType.KEYWORD),
            ]:
                self.client.create_payload_index(
                    collection_name=self.collection,
                    field_name=field,
                    field_schema=schema,
                )
            logger.info("Created collection '%s' with payload indexes", self.collection)

    def make_point_id(self, project: str, file_path: str, chunk_index: int) -> str:
        key = f"{project}:{file_path}:{chunk_index}"
        return str(uuid.uuid5(uuid.NAMESPACE_URL, key))

    def upsert_chunks(
        self,
        chunks: list[dict],
        vectors: list[list[float]],
    ):
        points = []
        for chunk, vector in zip(chunks, vectors):
            point_id = self.make_point_id(
                chunk["project_name"], chunk["file_path"], chunk["chunk_index"]
            )
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=chunk,
                )
            )
        if points:
            # 分批 upsert，每批 100 個
            batch_size = 100
            for i in range(0, len(points), batch_size):
                self.client.upsert(
                    collection_name=self.collection,
                    points=points[i : i + batch_size],
                )

    def search(
        self,
        query_vector: list[float],
        limit: int = 10,
        project_name: str | None = None,
        language: str | None = None,
    ) -> list[dict]:
        conditions = []
        if project_name:
            conditions.append(
                FieldCondition(
                    key="project_name", match=MatchValue(value=project_name)
                )
            )
        if language:
            conditions.append(
                FieldCondition(key="language", match=MatchValue(value=language))
            )

        query_filter = Filter(must=conditions) if conditions else None

        results = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
        )
        return [
            {**point.payload, "score": point.score}
            for point in results.points
        ]

    def delete_by_file(self, project_name: str, file_path: str):
        self.client.delete(
            collection_name=self.collection,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="project_name", match=MatchValue(value=project_name)
                    ),
                    FieldCondition(
                        key="file_path", match=MatchValue(value=file_path)
                    ),
                ]
            ),
        )

    def delete_by_project(self, project_name: str):
        self.client.delete(
            collection_name=self.collection,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="project_name", match=MatchValue(value=project_name)
                    ),
                ]
            ),
        )

    def get_project_stats(self, project_name: str) -> dict:
        result = self.client.count(
            collection_name=self.collection,
            count_filter=Filter(
                must=[
                    FieldCondition(
                        key="project_name", match=MatchValue(value=project_name)
                    ),
                ]
            ),
            exact=True,
        )
        return {"chunk_count": result.count}

    def health_check(self) -> bool:
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False
