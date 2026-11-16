"""Small local store. The caller supplies summaries; no conversation capture or AI calls."""
from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

MAX_SUMMARY = 12000
MAX_RESULTS = 10
TASK_ID = re.compile(r"^[a-f0-9]{12}$")


class Store:
    def __init__(self, directory: Path):
        directory = directory.expanduser().resolve()
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "memory.sqlite3"
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("""CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, summary TEXT NOT NULL,
                status TEXT NOT NULL, revision INTEGER NOT NULL, updated_at TEXT NOT NULL
            )""")
            db.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts USING fts5(
                id UNINDEXED, title, summary, tokenize='unicode61 remove_diacritics 2'
            )""")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def save(self, title: str, summary: str, task_id: str = "", status: str = "in_progress", expected_revision: int | None = None) -> dict:
        title, summary, task_id = title.strip(), summary.strip(), task_id.strip()
        if not title or len(title) > 160:
            raise ValueError("Title must contain 1 to 160 characters.")
        if not summary or len(summary) > MAX_SUMMARY:
            raise ValueError(f"Summary must contain 1 to {MAX_SUMMARY} characters.")
        if status not in ("in_progress", "blocked", "completed"):
            raise ValueError("Invalid status.")
        if task_id and not TASK_ID.fullmatch(task_id):
            raise ValueError("Invalid task ID.")
        if task_id and expected_revision is None:
            raise ValueError("Existing tasks require expected_revision to prevent accidental overwrites.")
        if not task_id and expected_revision is not None:
            raise ValueError("expected_revision applies only to an existing task.")
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if task_id:
                existing = db.execute("SELECT revision FROM tasks WHERE id=?", (task_id,)).fetchone()
                if existing is None:
                    raise ValueError("Task not found; create a new task without an ID.")
                if existing["revision"] != expected_revision:
                    raise ValueError("Revision conflict; read the current task and retry.")
                revision = existing["revision"] + 1
                db.execute("UPDATE tasks SET title=?, summary=?, status=?, revision=?, updated_at=? WHERE id=?",
                           (title, summary, status, revision, timestamp, task_id))
                db.execute("DELETE FROM tasks_fts WHERE id=?", (task_id,))
            else:
                task_id, revision = uuid4().hex[:12], 1
                db.execute("INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?)",
                           (task_id, title, summary, status, revision, timestamp))
            db.execute("INSERT INTO tasks_fts(id,title,summary) VALUES (?,?,?)", (task_id, title, summary))
        return {"id": task_id, "revision": revision, "updated_at": timestamp}

    def read(self, task_id: str) -> dict:
        if not TASK_ID.fullmatch(task_id):
            raise ValueError("Invalid task ID.")
        with self.connect() as db:
            row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise ValueError("Task not found.")
        return dict(row)

    def search(self, query: str, limit: int = 5) -> list[dict]:
        words = re.findall(r"[^\W_]+", query, flags=re.UNICODE)[:12]
        if not words:
            raise ValueError("Search needs at least one word.")
        if not 1 <= limit <= MAX_RESULTS:
            raise ValueError(f"Limit must be between 1 and {MAX_RESULTS}.")
        expression = " OR ".join('"' + word + '"' for word in words)
        with self.connect() as db:
            rows = db.execute("""SELECT t.id,t.title,t.status,t.revision,t.updated_at
                FROM tasks_fts f JOIN tasks t ON t.id=f.id WHERE tasks_fts MATCH ?
                ORDER BY bm25(tasks_fts), t.updated_at DESC LIMIT ?""", (expression, limit)).fetchall()
        return [dict(row) for row in rows]
