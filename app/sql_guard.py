from __future__ import annotations

import re
from typing import Any

import sqlglot
from sqlglot import exp

from .config import MAX_QUERY_ROWS

FORBIDDEN_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "REPLACE",
    "GRANT",
    "REVOKE",
    "VACUUM",
    "ATTACH",
    "DETACH",
    "CALL",
    "EXEC",
    "MERGE",
    "SET",
    "PRAGMA",
}

class SqlValidationError(ValueError):
    pass


def _clamp_limit(statement: exp.Expression) -> None:
    current_limit = statement.args.get("limit")
    if current_limit is None:
        statement.set("limit", exp.Limit(expression=exp.Literal.number(MAX_QUERY_ROWS)))
        return
    expression = current_limit.expression
    if not isinstance(expression, exp.Literal) or not expression.is_int:
        statement.set("limit", exp.Limit(expression=exp.Literal.number(MAX_QUERY_ROWS)))
        return
    if int(expression.this) > MAX_QUERY_ROWS:
        statement.set("limit", exp.Limit(expression=exp.Literal.number(MAX_QUERY_ROWS)))


def validate_sql(sql: str, schema: dict[str, Any]) -> str:
    stripped = sql.strip()
    if not stripped:
        raise SqlValidationError("Empty SQL is not allowed.")
    if "--" in stripped or "/*" in stripped or "*/" in stripped:
        raise SqlValidationError("SQL comments are not allowed.")
    if stripped.count(";") > 1 or (";" in stripped and not stripped.endswith(";")):
        raise SqlValidationError("Only a single statement is allowed.")

    upper_sql = stripped.upper()
    if any(re.search(rf"\b{keyword}\b", upper_sql) for keyword in FORBIDDEN_KEYWORDS):
        raise SqlValidationError("Only read-only analytics queries are allowed.")

    try:
        parsed = sqlglot.parse(stripped, dialect="sqlite")
    except Exception as exc:
        raise SqlValidationError("SQL could not be parsed safely.") from exc

    if len(parsed) != 1:
        raise SqlValidationError("Exactly one SQL statement is allowed.")

    statement = parsed[0]
    if not isinstance(statement, exp.Select):
        raise SqlValidationError("Only SELECT queries are allowed.")

    _clamp_limit(statement)
    return statement.sql(dialect="sqlite")
