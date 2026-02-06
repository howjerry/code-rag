import logging
from pathlib import Path

import pathspec

from code_rag.utils.filters import should_exclude_dir, should_exclude_file
from code_rag.utils.language import detect_language

logger = logging.getLogger(__name__)


def load_gitignore(project_path: Path) -> pathspec.PathSpec | None:
    gitignore = project_path / ".gitignore"
    if gitignore.exists():
        try:
            patterns = gitignore.read_text(encoding="utf-8", errors="ignore").splitlines()
            return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
        except Exception:
            logger.warning("Failed to parse .gitignore at %s", gitignore)
    return None


def scan_files(project_path: Path) -> list[dict]:
    """掃描專案目錄，回傳需要索引的檔案清單。"""
    gitignore_spec = load_gitignore(project_path)
    files = []

    for item in sorted(project_path.rglob("*")):
        # 跳過 symlinks（避免無限遞迴）
        if item.is_symlink():
            continue

        # 跳過排除的目錄
        if any(should_exclude_dir(part) for part in item.parts):
            continue

        if not item.is_file():
            continue

        # .gitignore 過濾
        rel_path = item.relative_to(project_path)
        if gitignore_spec and gitignore_spec.match_file(str(rel_path)):
            continue

        if should_exclude_file(item):
            continue

        language = detect_language(str(item))
        if language == "unknown":
            continue

        files.append({
            "path": str(item),
            "relative_path": str(rel_path),
            "language": language,
        })

    logger.info("Scanned %d files in %s", len(files), project_path)
    return files
