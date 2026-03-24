from __future__ import annotations

import sqlite3

from .config import DATA_DIR
from .database import build_sqlite_memory, execute_script
from .graph_builder import build_graph, curated_schema, curated_sql
from .ingestion import discover_tables


def bootstrap_data() -> tuple[sqlite3.Connection, dict, dict]:
    tables = discover_tables(DATA_DIR)
    connection = build_sqlite_memory(tables)
    execute_script(connection, curated_sql())
    return connection, build_graph(connection), curated_schema(connection)
