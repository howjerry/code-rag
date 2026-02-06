from pathlib import Path

# 總是排除的目錄
EXCLUDED_DIRS: set[str] = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    ".env",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "target",
    "bin",
    "obj",
    ".idea",
    ".vscode",
    ".vs",
    "vendor",
    "coverage",
    ".coverage",
    "htmlcov",
    ".terraform",
    ".docker",
}

# 總是排除的檔案模式
EXCLUDED_FILES: set[str] = {
    ".DS_Store",
    "Thumbs.db",
    ".gitkeep",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Cargo.lock",
    "go.sum",
    "composer.lock",
    "Gemfile.lock",
}

# 排除的副檔名（二進位、媒體等）
EXCLUDED_EXTENSIONS: set[str] = {
    ".pyc",
    ".pyo",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".o",
    ".a",
    ".class",
    ".jar",
    ".war",
    ".ear",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".ico",
    ".svg",
    ".webp",
    ".mp3",
    ".mp4",
    ".avi",
    ".mov",
    ".wav",
    ".flac",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".7z",
    ".rar",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    ".map",
    ".min.js",
    ".min.css",
    ".db",
    ".sqlite",
    ".sqlite3",
}

# 最大檔案大小（bytes）- 跳過超過 500KB 的檔案
MAX_FILE_SIZE = 500 * 1024


def should_exclude_dir(dir_name: str) -> bool:
    return dir_name in EXCLUDED_DIRS


def should_exclude_file(file_path: Path) -> bool:
    if file_path.name in EXCLUDED_FILES:
        return True
    if file_path.suffix.lower() in EXCLUDED_EXTENSIONS:
        return True
    if file_path.name.endswith(".min.js") or file_path.name.endswith(".min.css"):
        return True
    try:
        if file_path.stat().st_size > MAX_FILE_SIZE:
            return True
        if file_path.stat().st_size == 0:
            return True
    except OSError:
        return True
    return False
