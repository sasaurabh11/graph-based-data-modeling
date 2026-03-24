from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from .types import TableData


def _flatten_value(prefix: str, value: Any, output: dict[str, Any]) -> None:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            child_prefix = f"{prefix}_{key}" if prefix else str(key)
            _flatten_value(child_prefix, nested_value, output)
        return
    if isinstance(value, list):
        output[prefix] = json.dumps(value, ensure_ascii=True)
        return
    output[prefix] = value


def _normalize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in row.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            continue
        _flatten_value(normalized_key, value, flattened)
    return {key: _normalize_value(value) for key, value in flattened.items()}


def _infer_column_type(values: list[Any]) -> str:
    non_null = [value for value in values if value is not None]
    if not non_null:
        return "TEXT"
    if all(isinstance(value, int) for value in non_null):
        return "INTEGER"
    if all(isinstance(value, (int, float)) for value in non_null):
        return "REAL"
    if all(isinstance(value, str) and value.lstrip("-").isdigit() for value in non_null):
        return "INTEGER"
    try:
        for value in non_null:
            if not isinstance(value, str):
                raise ValueError
            float(value)
        return "REAL"
    except Exception:
        return "TEXT"


def _build_table(name: str, rows: list[dict[str, Any]]) -> TableData:
    columns = sorted({key for row in rows for key in row.keys()})
    column_types = {column: _infer_column_type([row.get(column) for row in rows]) for column in columns}
    return TableData(name=name, rows=rows, columns=columns, column_types=column_types)


def load_json(path: Path) -> TableData:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        for candidate in ("rows", "data", path.stem):
            if isinstance(payload.get(candidate), list):
                payload = payload[candidate]
                break
    if not isinstance(payload, list):
        raise ValueError(f"Unsupported JSON payload in {path.name}")
    rows = [_normalize_row(row) for row in payload if isinstance(row, dict)]
    return _build_table(path.stem, rows)


def load_xlsx(path: Path) -> list[TableData]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    tables: list[TableData] = []
    for sheet in workbook.worksheets:
        values = list(sheet.values)
        if not values:
            continue
        headers = [str(value).strip() if value is not None else "" for value in values[0]]
        rows = []
        for raw_row in values[1:]:
            mapped = {
                header: _normalize_value(raw_row[index] if index < len(raw_row) else None)
                for index, header in enumerate(headers)
                if header
            }
            if any(value is not None for value in mapped.values()):
                rows.append(mapped)
        tables.append(_build_table(f"{path.stem}__{sheet.title}".lower(), rows))
    return tables


def _load_jsonl_folder(folder: Path) -> TableData:
    rows: list[dict[str, Any]] = []
    for path in sorted(folder.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                rows.append(_normalize_row(json.loads(line)))
    return _build_table(folder.name, rows)


def discover_tables(data_dir: Path) -> list[TableData]:
    tables: list[TableData] = []
    for path in sorted(data_dir.iterdir()):
        if path.name.startswith("."):
            continue
        if path.is_dir():
            tables.append(_load_jsonl_folder(path))
            continue
        suffix = path.suffix.lower()
        if suffix == ".json":
            tables.append(load_json(path))
        elif suffix in {".xlsx", ".xlsm"}:
            tables.extend(load_xlsx(path))
    return tables
