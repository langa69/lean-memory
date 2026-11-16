"""MCP stdio entry point; the host supplies the working directory or LEAN_MEMORY_DIR."""
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .store import Store

server = FastMCP("lean-memory")


def store() -> Store:
    return Store(Path(os.environ.get("LEAN_MEMORY_DIR", ".lean-memory")))


@server.tool()
def save_task(title: str, summary: str, task_id: str = "", status: str = "in_progress", expected_revision: int | None = None) -> dict:
    """Create or update a concise task checkpoint. For updates read the task and provide its ID and revision. Do not save secrets or private data unnecessarily."""
    return store().save(title, summary, task_id, status, expected_revision)


@server.tool()
def search_tasks(query: str, limit: int = 5) -> list[dict]:
    """Search task titles and checkpoints by keywords; returns brief metadata only. Choose the correct task before reading it."""
    return store().search(query, limit)


@server.tool()
def read_task(task_id: str) -> dict:
    """Read one task by its exact ID, including its current checkpoint and revision."""
    return store().read(task_id)


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
