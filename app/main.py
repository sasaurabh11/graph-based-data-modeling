from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .answering import generate_sql, summarize_answer
from .bootstrap import bootstrap_data
from .database import execute_readonly_query
from .gemini import GeminiError
from .sql_guard import SqlValidationError, validate_sql

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"

app = FastAPI(title="Graph Based Data Modeling")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
if FRONTEND_ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS_DIR), name="assets")
runtime: dict = {}


class ChatRequest(BaseModel):
    question: str


@app.on_event("startup")
def startup() -> None:
    connection, graph, schema = bootstrap_data()
    runtime["connection"] = connection
    runtime["graph"] = graph
    runtime["schema"] = schema


@app.get("/")
def index() -> Response:
    index_path = FRONTEND_DIST_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse(
        "<html><body style='font-family:sans-serif;background:#020617;color:#e2e8f0;padding:24px'>"
        "<h1>Frontend not built</h1>"
        "<p>Run <code>npm run build</code> to build the Vite React frontend, or <code>npm run dev</code> for local frontend development.</p>"
        "</body></html>",
        status_code=503,
    )


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/meta")
def meta() -> dict:
    return {
        "examples": runtime["graph"].get("examples", []),
        "tables": list(runtime["schema"]["tables"].keys()),
    }


@app.get("/api/graph")
def graph() -> dict:
    return runtime["graph"]


@app.get("/api/graph/neighbors/{node_id:path}")
def neighbors(node_id: str) -> dict:
    graph_data = runtime["graph"]
    touching_edges = [edge for edge in graph_data["edges"] if edge["source"] == node_id or edge["target"] == node_id]
    neighbor_ids = {node_id}
    for edge in touching_edges:
        neighbor_ids.add(edge["source"])
        neighbor_ids.add(edge["target"])
    nodes = [node for node in graph_data["nodes"] if node["id"] in neighbor_ids]
    return {"nodes": nodes, "edges": touching_edges}


def _highlight_node_ids(rows: list[dict], graph: dict) -> list[str]:
    valid_ids = {node["id"] for node in graph["nodes"]}
    kind_map = {
        "customer_id": "customer",
        "address_id": "address",
        "plant_id": "plant",
        "product_id": "product",
        "sales_order_id": "sales_order",
        "sales_order_item_id": "sales_order_item",
        "delivery_id": "delivery",
        "delivery_item_id": "delivery_item",
        "billing_document_id": "billing_document",
        "reference_billing_document_id": "billing_document",
        "billing_document_item_id": "billing_document_item",
        "journal_entry_id": "journal_entry",
        "clearing_accounting_document": "journal_entry",
        "payment_id": "payment",
    }
    result: list[str] = []
    for row in rows[:20]:
        for column, kind in kind_map.items():
            value = row.get(column)
            if not value:
                continue
            node_id = f"{kind}:{value}"
            if node_id in valid_ids and node_id not in result:
                result.append(node_id)
    return result


@app.post("/api/chat")
def chat(payload: ChatRequest) -> dict:
    try:
        sql, rationale = generate_sql(payload.question, runtime["schema"], runtime["graph"].get("examples", []))
        safe_sql = validate_sql(sql, runtime["schema"])
        rows = execute_readonly_query(runtime["connection"], safe_sql, [])
        answer = summarize_answer(payload.question, safe_sql, rows)
        return {
            "question": payload.question,
            "intent": "gemini_sql",
            "rationale": rationale,
            "sql": safe_sql,
            "answer": answer,
            "evidence": rows[:20],
            "highlightNodeIds": _highlight_node_ids(rows, runtime["graph"]),
            "trace": [],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SqlValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GeminiError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(status_code=500, detail="The query failed safely. Please try a narrower business question.")
