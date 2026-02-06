"""非程式碼檔案的 fallback chunker（固定大小 + overlap）。"""

from code_rag.config import settings


def chunk_text(
    source: str,
    file_path: str,
    project_name: str,
    language: str,
) -> list[dict]:
    """將文字按固定大小切分，在行邊界切分。"""
    max_chars = settings.chunk_max_chars
    overlap = settings.chunk_overlap_chars
    lines = source.split("\n")
    chunks = []
    current_lines: list[str] = []
    current_chars = 0
    start_line = 0

    for i, line in enumerate(lines):
        line_len = len(line) + 1
        if current_chars + line_len > max_chars and current_lines:
            chunk_text_str = "\n".join(current_lines)
            chunks.append({
                "content": chunk_text_str,
                "file_path": file_path,
                "project_name": project_name,
                "language": language,
                "chunk_index": len(chunks),
                "start_line": start_line + 1,
                "end_line": i,
                "chunk_type": "text",
                "name": None,
            })
            # overlap
            overlap_chars = 0
            overlap_start = len(current_lines)
            for j in range(len(current_lines) - 1, -1, -1):
                overlap_chars += len(current_lines[j]) + 1
                if overlap_chars >= overlap:
                    overlap_start = j
                    break
            current_lines = current_lines[overlap_start:]
            current_chars = sum(len(l) + 1 for l in current_lines)
            start_line = i - len(current_lines)

        current_lines.append(line)
        current_chars += line_len

    if current_lines:
        chunk_text_str = "\n".join(current_lines)
        if chunk_text_str.strip():
            chunks.append({
                "content": chunk_text_str,
                "file_path": file_path,
                "project_name": project_name,
                "language": language,
                "chunk_index": len(chunks),
                "start_line": start_line + 1,
                "end_line": len(lines),
                "chunk_type": "text",
                "name": None,
            })

    return chunks
