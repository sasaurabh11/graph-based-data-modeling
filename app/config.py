from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


BASE_DIR = Path(__file__).resolve().parent.parent
_load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
MAX_QUERY_ROWS = 200
QUERY_TIMEOUT_SECONDS = 3
SQL_PROGRESS_STEP_LIMIT = 200_000
GRAPH_INITIAL_NODE_LIMIT = 36
GRAPH_MAX_NODES = 1600

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "").strip()
APP_HOST = os.getenv("APP_HOST", "127.0.0.1").strip() or "127.0.0.1"
APP_PORT = int(os.getenv("APP_PORT", "8000").strip() or "8000")
