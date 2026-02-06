EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".cs": "c_sharp",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".lua": "lua",
    ".r": "r",
    ".R": "r",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".sql": "sql",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".md": "markdown",
    ".rst": "rst",
    ".txt": "text",
    ".dockerfile": "dockerfile",
    ".tf": "terraform",
    ".proto": "protobuf",
    ".graphql": "graphql",
    ".gql": "graphql",
}

# tree-sitter 支援的語言
TREESITTER_LANGUAGES = {"python", "javascript", "typescript", "go", "c_sharp", "rust"}


def detect_language(file_path: str) -> str:
    from pathlib import Path

    p = Path(file_path)
    if p.name == "Dockerfile" or p.name.startswith("Dockerfile."):
        return "dockerfile"
    if p.name in ("Makefile", "GNUmakefile"):
        return "makefile"
    return EXTENSION_MAP.get(p.suffix.lower(), "unknown")


def supports_treesitter(language: str) -> bool:
    return language in TREESITTER_LANGUAGES
