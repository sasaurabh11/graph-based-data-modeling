from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TableData:
    name: str
    rows: list[dict[str, Any]]
    columns: list[str]
    column_types: dict[str, str]


@dataclass
class GraphNode:
    id: str
    label: str
    kind: str
    title: str
    properties: dict[str, Any]
    degree: int = 0


@dataclass
class GraphEdge:
    id: str
    source: str
    target: str
    relation: str
    properties: dict[str, Any] = field(default_factory=dict)
