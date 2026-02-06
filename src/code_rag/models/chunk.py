from pydantic import BaseModel


class CodeChunk(BaseModel):
    content: str
    file_path: str
    project_name: str
    language: str
    chunk_index: int
    start_line: int
    end_line: int
    chunk_type: str = "code"  # code, function, class, method
    name: str | None = None  # 函式/類別名稱


class TextChunk(BaseModel):
    content: str
    file_path: str
    project_name: str
    language: str
    chunk_index: int
    start_line: int
    end_line: int
    chunk_type: str = "text"
