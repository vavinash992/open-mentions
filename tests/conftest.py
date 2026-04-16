"""Pytest configuration for Open Mentions.

We use a file-based SQLite DB (`open_mentions.db`) in the repo root.
To keep tests deterministic, remove it once before test collection so
FastAPI startup can create a clean schema.
"""

from pathlib import Path


def pytest_configure():
    db_path = Path(__file__).parent.parent / "open_mentions.db"
    if db_path.exists():
        db_path.unlink()
