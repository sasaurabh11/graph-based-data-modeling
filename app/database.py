from __future__ import annotations

import sqlite3
from typing import Any

from .config import MAX_QUERY_ROWS, QUERY_TIMEOUT_SECONDS, SQL_PROGRESS_STEP_LIMIT
from .types import TableData


def _sanitize_identifier(value: str) -> str:
    return "".join(character if character.isalnum() or character == "_" else "_" for character in value)


def _convert_value(value: Any, declared_type: str) -> Any:
    if value is None:
        return None
    if declared_type == "INTEGER":
        try:
            return int(value)
        except Exception:
            return None
    if declared_type == "REAL":
        try:
            return float(value)
        except Exception:
            return None
    return str(value)


def build_sqlite_memory(tables: list[TableData]) -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:", timeout=QUERY_TIMEOUT_SECONDS, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    for table in tables:
        table_name = _sanitize_identifier(table.name)
        columns = [_sanitize_identifier(column) for column in table.columns if column]
        if not columns:
            continue
        column_sql = ", ".join(
            f'"{column}" {table.column_types.get(column, "TEXT")}'
            for column in columns
        )
        connection.execute(f'CREATE TABLE "{table_name}" ({column_sql})')
        placeholders = ", ".join("?" for _ in columns)
        quoted_columns = ", ".join(f'"{column}"' for column in columns)
        insert_sql = f'INSERT INTO "{table_name}" ({quoted_columns}) VALUES ({placeholders})'
        rows = []
        for row in table.rows:
            rows.append(
                [_convert_value(row.get(column), table.column_types.get(column, "TEXT")) for column in columns]
            )
        if rows:
            connection.executemany(insert_sql, rows)
    connection.commit()
    return connection


def execute_script(connection: sqlite3.Connection, script: str) -> None:
    connection.executescript(script)
    connection.commit()


def execute_readonly_query(connection: sqlite3.Connection, sql: str, params: list[Any]) -> list[dict[str, Any]]:
    remaining_steps = {"count": SQL_PROGRESS_STEP_LIMIT}

    def _progress_handler() -> int:
        remaining_steps["count"] -= 100
        return 1 if remaining_steps["count"] <= 0 else 0

    connection.set_progress_handler(_progress_handler, 100)
    try:
        cursor = connection.execute(sql, params)
        return [dict(row) for row in cursor.fetchmany(MAX_QUERY_ROWS)]
    finally:
        connection.set_progress_handler(None, 0)
