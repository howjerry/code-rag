from pydantic import BaseModel


class SearchResult(BaseModel):
    content: str
    file_path: str
    project_name: str
    language: str
    chunk_type: str
    name: str | None = None
    start_line: int
    end_line: int
    score: float


class IndexRequest(BaseModel):
    project_name: str
    path: str


class IndexStatus(BaseModel):
    project_name: str
    status: str  # pending, running, completed, failed
    total_files: int = 0
    processed_files: int = 0
    total_chunks: int = 0
    error: str | None = None
