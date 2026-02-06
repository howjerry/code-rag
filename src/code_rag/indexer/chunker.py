"""AST-based code chunker using tree-sitter."""

import logging

import tree_sitter_python
import tree_sitter_javascript
import tree_sitter_typescript
import tree_sitter_go
import tree_sitter_c_sharp
import tree_sitter_rust
from tree_sitter import Language, Parser, Node

from code_rag.config import settings

logger = logging.getLogger(__name__)

# tree-sitter 語言映射
_LANGUAGES: dict[str, Language] = {}


def _get_language(lang: str) -> Language | None:
    if lang in _LANGUAGES:
        return _LANGUAGES[lang]

    lang_modules = {
        "python": tree_sitter_python,
        "javascript": tree_sitter_javascript,
        "typescript": tree_sitter_typescript,
        "go": tree_sitter_go,
        "c_sharp": tree_sitter_c_sharp,
        "rust": tree_sitter_rust,
    }

    module = lang_modules.get(lang)
    if module is None:
        return None

    try:
        language = Language(module.language())
        _LANGUAGES[lang] = language
        return language
    except Exception as e:
        logger.warning("Failed to load tree-sitter language '%s': %s", lang, e)
        return None


# 每個語言中代表語意單元的 node 類型
SEMANTIC_NODE_TYPES: dict[str, set[str]] = {
    "python": {
        "function_definition",
        "class_definition",
        "decorated_definition",
    },
    "javascript": {
        "function_declaration",
        "class_declaration",
        "method_definition",
        "arrow_function",
        "export_statement",
    },
    "typescript": {
        "function_declaration",
        "class_declaration",
        "method_definition",
        "arrow_function",
        "export_statement",
        "interface_declaration",
        "type_alias_declaration",
    },
    "go": {
        "function_declaration",
        "method_declaration",
        "type_declaration",
    },
    "c_sharp": {
        "method_declaration",
        "class_declaration",
        "interface_declaration",
        "struct_declaration",
        "enum_declaration",
        "namespace_declaration",
    },
    "rust": {
        "function_item",
        "impl_item",
        "struct_item",
        "enum_item",
        "trait_item",
        "mod_item",
    },
}


def _extract_name(node: Node) -> str | None:
    """從 AST node 提取名稱。"""
    for child in node.children:
        if child.type in ("identifier", "name", "type_identifier", "property_identifier"):
            return child.text.decode("utf-8") if child.text else None
    return None


_TYPE_MAP = {
    "function": "function", "method": "function", "arrow": "function",
    "class": "class", "interface": "interface", "trait": "interface",
    "struct": "struct", "enum": "enum", "type": "type",
    "impl": "impl", "mod": "module", "namespace": "module",
}


def _node_chunk_type(node_type: str) -> str:
    return next((v for k, v in _TYPE_MAP.items() if k in node_type), "code")


def _collect_semantic_nodes(node: Node, language: str) -> list[Node]:
    """遞迴收集語意節點。"""
    semantic_types = SEMANTIC_NODE_TYPES.get(language, set())
    results = []

    if node.type in semantic_types:
        results.append(node)
    else:
        for child in node.children:
            results.extend(_collect_semantic_nodes(child, language))

    return results


def chunk_code(
    source: str,
    language: str,
    file_path: str,
    project_name: str,
) -> list[dict]:
    """使用 tree-sitter 在語意邊界切分程式碼。"""
    lang_obj = _get_language(language)
    if lang_obj is None:
        return []

    parser = Parser(lang_obj)
    tree = parser.parse(source.encode("utf-8"))
    root = tree.root_node

    semantic_nodes = _collect_semantic_nodes(root, language)

    if not semantic_nodes:
        # 沒有語意節點，整個檔案作為一個 chunk
        if len(source) <= settings.chunk_max_chars:
            return [
                {
                    "content": source,
                    "file_path": file_path,
                    "project_name": project_name,
                    "language": language,
                    "chunk_index": 0,
                    "start_line": 1,
                    "end_line": source.count("\n") + 1,
                    "chunk_type": "code",
                    "name": None,
                }
            ]
        # 太大，fallback 到固定大小切分
        return split_lines(source, file_path, project_name, language, chunk_type="code")

    chunks = []
    lines = source.split("\n")
    last_end = 0  # 上一個 chunk 結束的行號（0-indexed）

    for node in sorted(semantic_nodes, key=lambda n: n.start_point[0]):
        node_start_line = node.start_point[0]
        node_end_line = node.end_point[0]

        # 收集 node 之前的「間隙」程式碼（imports, 全域變數等）
        if node_start_line > last_end:
            gap_text = "\n".join(lines[last_end:node_start_line]).strip()
            if gap_text and len(gap_text) > 20:
                chunks.append({
                    "content": gap_text,
                    "file_path": file_path,
                    "project_name": project_name,
                    "language": language,
                    "chunk_index": len(chunks),
                    "start_line": last_end + 1,
                    "end_line": node_start_line,
                    "chunk_type": "code",
                    "name": None,
                })

        # 語意節點本身
        node_text = node.text.decode("utf-8") if node.text else ""

        if len(node_text) <= settings.chunk_max_chars:
            chunks.append({
                "content": node_text,
                "file_path": file_path,
                "project_name": project_name,
                "language": language,
                "chunk_index": len(chunks),
                "start_line": node_start_line + 1,
                "end_line": node_end_line + 1,
                "chunk_type": _node_chunk_type(node.type),
                "name": _extract_name(node),
            })
        else:
            # 節點太大，按固定大小切分
            sub_chunks = split_lines(
                node_text,
                file_path=file_path,
                project_name=project_name,
                language=language,
                chunk_type=_node_chunk_type(node.type),
                name=_extract_name(node),
                base_line=node_start_line,
                start_index=len(chunks),
            )
            chunks.extend(sub_chunks)

        last_end = node_end_line + 1

    # 收集最後的間隙
    if last_end < len(lines):
        gap_text = "\n".join(lines[last_end:]).strip()
        if gap_text and len(gap_text) > 20:
            chunks.append({
                "content": gap_text,
                "file_path": file_path,
                "project_name": project_name,
                "language": language,
                "chunk_index": len(chunks),
                "start_line": last_end + 1,
                "end_line": len(lines),
                "chunk_type": "code",
                "name": None,
            })

    return chunks


def split_lines(
    source: str,
    file_path: str,
    project_name: str,
    language: str,
    *,
    chunk_type: str = "text",
    name: str | None = None,
    base_line: int = 0,
    start_index: int = 0,
) -> list[dict]:
    """將文字按固定大小在行邊界切分，帶 overlap。

    同時用於 tree-sitter 過大節點的子切分和非程式碼檔案的 fallback 切分。
    """
    max_chars = settings.chunk_max_chars
    overlap = settings.chunk_overlap_chars
    lines = source.split("\n") if isinstance(source, str) else source
    chunks: list[dict] = []
    current_lines: list[str] = []
    current_chars = 0
    start_line = 0

    for i, line in enumerate(lines):
        line_len = len(line) + 1  # +1 for newline
        if current_chars + line_len > max_chars and current_lines:
            chunk_text = "\n".join(current_lines)
            chunks.append({
                "content": chunk_text,
                "file_path": file_path,
                "project_name": project_name,
                "language": language,
                "chunk_index": start_index + len(chunks),
                "start_line": base_line + start_line + 1,
                "end_line": base_line + i,
                "chunk_type": chunk_type,
                "name": name,
            })
            # overlap：保留最後幾行
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
        chunk_text = "\n".join(current_lines)
        if chunk_text.strip():
            chunks.append({
                "content": chunk_text,
                "file_path": file_path,
                "project_name": project_name,
                "language": language,
                "chunk_index": start_index + len(chunks),
                "start_line": base_line + start_line + 1,
                "end_line": base_line + len(lines),
                "chunk_type": chunk_type,
                "name": name,
            })

    return chunks
