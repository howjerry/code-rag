import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path


class StateDB:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_tables()

    def _init_tables(self):
        with self._lock:
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS file_hashes (
                    project_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    hash TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (project_name, file_path)
                );
                CREATE TABLE IF NOT EXISTS index_status (
                    project_name TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'pending',
                    total_files INTEGER DEFAULT 0,
                    processed_files INTEGER DEFAULT 0,
                    total_chunks INTEGER DEFAULT 0,
                    error TEXT,
                    started_at TEXT,
                    completed_at TEXT
                );
            """)
            self.conn.commit()

    def get_file_hash(self, project_name: str, file_path: str) -> str | None:
        with self._lock:
            row = self.conn.execute(
                "SELECT hash FROM file_hashes WHERE project_name = ? AND file_path = ?",
                (project_name, file_path),
            ).fetchone()
            return row["hash"] if row else None

    def set_file_hash(self, project_name: str, file_path: str, hash_val: str):
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO file_hashes (project_name, file_path, hash, updated_at) VALUES (?, ?, ?, ?)",
                (project_name, file_path, hash_val, now),
            )
            self.conn.commit()

    def get_all_file_paths(self, project_name: str) -> set[str]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT file_path FROM file_hashes WHERE project_name = ?",
                (project_name,),
            ).fetchall()
            return {row["file_path"] for row in rows}

    def remove_file(self, project_name: str, file_path: str):
        with self._lock:
            self.conn.execute(
                "DELETE FROM file_hashes WHERE project_name = ? AND file_path = ?",
                (project_name, file_path),
            )
            self.conn.commit()

    def remove_project(self, project_name: str):
        with self._lock:
            self.conn.execute(
                "DELETE FROM file_hashes WHERE project_name = ?", (project_name,)
            )
            self.conn.execute(
                "DELETE FROM index_status WHERE project_name = ?", (project_name,)
            )
            self.conn.commit()

    def set_index_status(
        self,
        project_name: str,
        status: str,
        total_files: int = 0,
        processed_files: int = 0,
        total_chunks: int = 0,
        error: str | None = None,
    ):
        now = datetime.now(timezone.utc).isoformat()
        started_at = now if status == "running" else None
        completed_at = now if status in ("completed", "failed") else None

        with self._lock:
            existing = self.conn.execute(
                "SELECT started_at FROM index_status WHERE project_name = ?",
                (project_name,),
            ).fetchone()

            if existing:
                updates = {
                    "status": status,
                    "total_files": total_files,
                    "processed_files": processed_files,
                    "total_chunks": total_chunks,
                    "error": error,
                }
                if started_at:
                    updates["started_at"] = started_at
                if completed_at:
                    updates["completed_at"] = completed_at
                set_clause = ", ".join(f"{k} = ?" for k in updates)
                self.conn.execute(
                    f"UPDATE index_status SET {set_clause} WHERE project_name = ?",
                    (*updates.values(), project_name),
                )
            else:
                self.conn.execute(
                    "INSERT INTO index_status (project_name, status, total_files, processed_files, total_chunks, error, started_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (project_name, status, total_files, processed_files, total_chunks, error, started_at, completed_at),
                )
            self.conn.commit()

    def get_index_status(self, project_name: str) -> dict | None:
        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM index_status WHERE project_name = ?", (project_name,)
            ).fetchone()
            return dict(row) if row else None

    def get_all_projects(self) -> list[dict]:
        with self._lock:
            rows = self.conn.execute("SELECT * FROM index_status").fetchall()
            return [dict(row) for row in rows]

    def close(self):
        self.conn.close()
