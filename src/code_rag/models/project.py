from pydantic import BaseModel


class Project(BaseModel):
    name: str
    path: str
    languages: list[str] = []
    file_count: int = 0
    chunk_count: int = 0
    indexed_at: str | None = None
