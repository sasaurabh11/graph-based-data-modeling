# Order-to-Cash Graph Explorer

A full-stack business intelligence tool that ingests partitioned JSONL records, models them as a knowledge graph, and lets users explore the order-to-cash flow visually and through natural language queries powered by Gemini.

---

## Table of Contents

- [What It Does](#what-it-does)
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Architecture Decisions](#architecture-decisions)
- [Database Choice](#database-choice)
- [Data Pipeline](#data-pipeline)
- [Graph Model](#graph-model)
- [LLM Prompting Strategy](#llm-prompting-strategy)
- [Guardrails](#guardrails)
- [Running the App](#running-the-app)
- [Testing](#testing)
- [Configuration](#configuration)
- [AI Session Log](#ai-session-log)

---

## What It Does

1. Loads 19 partitioned JSONL datasets (customers, orders, deliveries, billing, payments, etc.) on startup
2. Creates an in-memory SQLite database with 14 curated analytics views
3. Builds a knowledge graph of 12 entity types and 17+ relationship types
4. Serves a React + Cytoscape.js frontend for interactive graph exploration
5. Accepts natural language questions, generates SQL via Gemini, validates it, executes it, and highlights the answer on the graph

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (React + Vite)                    │
│                                                                  │
│  ┌─────────────────────┐   ┌───────────────┐   ┌─────────────┐ │
│  │   GraphCanvas        │   │  ChatPanel    │   │  Inspector  │ │
│  │   (Cytoscape.js)     │   │  (NL → SQL)   │   │  Panel      │ │
│  └──────────┬──────────┘   └──────┬────────┘   └──────┬──────┘ │
└─────────────┼────────────────────┼──────────────────────┼───────┘
              │  GET /api/graph    │  POST /api/chat      │ click
              ▼                    ▼                       │
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                           │
│                                                                  │
│  /api/graph ──► graph_builder.py                                │
│  /api/chat  ──► answering.py ──► gemini.py ──► sql_guard.py    │
│                                          └──► database.py       │
│                                                                  │
│  Startup: bootstrap.py                                          │
│    1. ingestion.py   — load JSONL → TableData                   │
│    2. database.py    — TableData → in-memory SQLite             │
│    3. graph_builder.py — curated SQL views + graph nodes/edges  │
└─────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│               In-Memory SQLite (ephemeral)                       │
│   19 raw tables  →  14 curated views (only these exposed to LLM)│
└─────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
.
├── app/
│   ├── main.py            # FastAPI app, all API endpoints
│   ├── bootstrap.py       # Startup orchestration
│   ├── ingestion.py       # JSONL/JSON/XLSX → TableData
│   ├── database.py        # SQLite builder and query executor
│   ├── graph_builder.py   # Curated SQL views + graph construction
│   ├── answering.py       # Scope check, Gemini SQL generation, summarization
│   ├── gemini.py          # HTTP client for Google Generative Language API
│   ├── sql_guard.py       # Parser-based SQL validation (sqlglot)
│   ├── config.py          # Environment variable loading
│   └── types.py           # GraphNode, GraphEdge, TableData dataclasses
├── frontend/
│   ├── src/
│   │   ├── App.tsx                      # Root component, state management
│   │   ├── api.ts                       # Typed fetch wrappers
│   │   ├── types.ts                     # TypeScript interfaces
│   │   ├── styles.css                   # Global dark-theme styles
│   │   └── components/
│   │       ├── GraphCanvas.tsx          # Cytoscape.js graph renderer
│   │       ├── ChatPanel.tsx            # NL query interface
│   │       └── InspectorPanel.tsx       # Node metadata viewer
│   └── vite.config.mjs                 # Vite config, /api proxy
├── data/                  # 19 partitioned JSONL source folders
├── tests/
│   └── test_app.py        # Unit + integration tests
├── scripts/
│   └── run.sh             # Uvicorn startup script
├── requirements.txt
└── .env.example
```

---

## Architecture Decisions

### Single-process, startup-loaded design

All data is loaded once at server startup into an in-memory SQLite database. There is no persistent database, no migration system, and no background workers. This was a deliberate choice for the following reasons:

- **Reproducibility** — every restart produces a clean, deterministic database from the source JSONL files
- **Simplicity** — no database server to run, no connection pooling, no schema migrations
- **Safety** — since the database is rebuilt from read-only files on every start, there is no risk of LLM-generated SQL permanently mutating state
- **Speed** — the entire dataset fits in memory; queries execute in milliseconds without disk I/O

The trade-off is that the database is lost on restart. This is acceptable because the source of truth is always the JSONL files in `/data`.

### Separation between raw tables and curated views

Raw JSONL data is loaded as-is into 19 SQLite tables preserving original field names. A second layer of 14 SQL `CREATE VIEW` statements then defines the analytics-ready schema with:

- Consistent `snake_case` column names
- Composite surrogate keys (e.g. `salesOrder:salesOrderItem` → `sales_order_item_id`)
- Aggregations that collapse line-item tables into document-level views (journal entries, payments)
- `LEFT JOIN` enrichment (customers joined with their addresses, products joined with English descriptions)

**Only the 14 curated views are ever exposed to the LLM.** Raw tables are never referenced in the LLM prompt or reachable by generated SQL. This isolates the LLM from internal field names, schema volatility, and data quality issues in raw ingestion tables.

### Graph as a first-class data model

Rather than treating the graph as a UI feature, it is built as a structured data model (`GraphNode`, `GraphEdge`) from the same curated SQL views. This means:

- Graph edges reflect actual foreign key relationships in the data, not hardcoded display logic
- Node `degree` is computed from actual edge counts, so node size in the UI is data-driven
- The graph can be queried for neighbors independently of the SQL path (`/api/graph/neighbors/{node_id}`)
- Chat answer results highlight the relevant nodes by mapping result column names (`customer_id`, `billing_document_id`, etc.) back to graph node IDs

---

## Database Choice

**SQLite (in-memory)** was chosen over PostgreSQL, DuckDB, or a graph database for these reasons:

| Criterion | Decision |
|-----------|----------|
| Zero infrastructure | SQLite requires no server process, no Docker, no credentials |
| Read-only workload | All queries are analytics SELECTs; SQLite's write limitations are irrelevant |
| Dataset size | The full dataset fits in RAM; SQLite in-memory mode is fast enough |
| LLM SQL dialect | SQLite is the simplest, most widely understood SQL dialect — LLMs generate reliable SQLite |
| Validation tooling | `sqlglot` has first-class SQLite dialect support for parsing and validation |
| Portability | Any developer can clone and run with zero setup beyond `pip install` |

**Why not DuckDB?** DuckDB would offer faster analytics on larger datasets and better support for JSONL ingestion. The trade-off is a heavier dependency and a less familiar SQL dialect for the LLM. SQLite was sufficient for this dataset size.

**Why not a graph database (Neo4j, etc.)?** The graph model here is used for visualization and navigation, not for graph-traversal queries. All analytical questions are answered with SQL against the relational views. A graph database would add infrastructure complexity without improving the query experience for this use case.

---

## Data Pipeline

```
/data/{entity}/part-*.jsonl
        │
        ▼  ingestion.py
┌────────────────────────────────┐
│  _load_jsonl_folder()          │
│  • read line-delimited JSON    │
│  • flatten nested objects      │
│    (creationTime.hours         │
│     → creationTime_hours)      │
│  • normalize values            │
│    (bool → 0/1, "" → NULL)     │
│  • infer column types          │
│    (INTEGER / REAL / TEXT)     │
│  → TableData(name, rows,       │
│              columns,          │
│              column_types)     │
└────────────────────────────────┘
        │
        ▼  database.py
┌────────────────────────────────┐
│  build_sqlite_memory()         │
│  • CREATE TABLE per TableData  │
│  • typed INSERT for all rows   │
│  → sqlite3.Connection          │
│    (in-memory, :memory:)       │
└────────────────────────────────┘
        │
        ▼  graph_builder.py → curated_sql()
┌────────────────────────────────┐
│  execute_script()              │
│  • CREATE VIEW customers       │
│  • CREATE VIEW sales_orders    │
│  • ... 14 views total ...      │
│  • aggregations, joins,        │
│    composite keys              │
└────────────────────────────────┘
        │
        ▼  graph_builder.py → build_graph()
┌────────────────────────────────┐
│  SELECT from curated views     │
│  • build GraphNode per row     │
│  • build GraphEdge per FK      │
│  • compute degree per node     │
│  • pick initialNodeIds         │
│    (exemplar O2C chain first,  │
│     then top-degree fill)      │
└────────────────────────────────┘
```

---

## Graph Model

### Node types (12)

| Type | Source view | Label shown |
|------|------------|-------------|
| customer | customers | customer_name |
| address | addresses | city_name |
| plant | plants_curated | plant_name |
| product | products_curated | product_name |
| sales_order | sales_orders | sales_order_id |
| sales_order_item | sales_order_items_curated | sales_order_item_id |
| delivery | deliveries | delivery_id |
| delivery_item | delivery_items_curated | delivery_item_id |
| billing_document | billing_documents | billing_document_id |
| billing_document_item | billing_document_items_curated | billing_document_item_id |
| journal_entry | journal_entries | journal_entry_id |
| payment | payments | payment_id |

### Key relationships

```
customer ──PLACED_ORDER──► sales_order
customer ──HAS_ADDRESS──► address
customer ──BILLED_TO──► billing_document
customer ──MADE_PAYMENT──► payment
sales_order ──HAS_ITEM──► sales_order_item
sales_order_item ──ORDERS_PRODUCT──► product
sales_order_item ──FULFILLED_BY──► delivery_item
delivery ──HAS_ITEM──► delivery_item
delivery_item ──SHIPPED_FROM──► plant
billing_document ──HAS_ITEM──► billing_document_item
billing_document ──POSTED_TO──► journal_entry
billing_document ──SETTLED_BY_PAYMENT──► payment
product ──AVAILABLE_AT_PLANT──► plant
```

### Initial graph seeding

On load, the graph first renders a complete exemplar order-to-cash chain (one customer → order → delivery → invoice → journal entry → payment) by querying for a fully-linked record. It then fills remaining slots up to `GRAPH_INITIAL_NODE_LIMIT` (36) using the highest-degree nodes per entity type. This ensures the first render shows a meaningful, navigable business story rather than random nodes.

---

## LLM Prompting Strategy

All LLM interaction goes through `app/answering.py`. There are two separate Gemini calls per chat turn, each with a distinct role.

### Call 1 — SQL generation (temperature 0.05)

Low temperature is used here because SQL generation is a deterministic translation task. The prompt includes:

**Schema injection** — the full column list of every curated view is injected as `table(col1, col2, ...)` lines so the model knows exactly what columns exist. It cannot hallucinate column names that are not in this list.

**Relationship hints** — explicit foreign key relationships are listed (e.g. `customers.customer_id -> sales_orders.customer_id`) so the model knows how to JOIN correctly without guessing.

**SQL safety rules** — the prompt explicitly prohibits destructive keywords, comments, and multiple statements. It also instructs the model to always qualify column names with table aliases in JOINs to prevent ambiguous column errors at runtime.

**Output format** — the model is instructed to return a strict JSON object with three keys: `in_scope` (boolean), `sql` (string), and `rationale` (string). This avoids free-text parsing and makes failures explicit.

**Example questions** — a small set of example questions (generated from real IDs in the database at startup) is included to prime the model on the vocabulary and style of valid questions.

### Call 2 — Answer summarization (temperature 0.2)

Slightly higher temperature is used here for more natural language output. The prompt includes:

- The original user question
- The SQL that was executed
- Up to 20 result rows as JSON

The model is instructed to answer using **only the provided rows** — it cannot draw on external knowledge. If the rows are partial evidence, it must say so. This keeps answers grounded in the actual dataset.

### Why two calls instead of one?

Separating SQL generation from summarization means:

1. The SQL can be validated, logged, and shown to the user before any summarization happens
2. Summarization failures do not affect whether a valid answer was found
3. Each call can be tuned independently (stricter for SQL, looser for prose)

---

## Guardrails

The system has four independent layers of protection against unsafe or incorrect queries.

### Layer 1 — Scope check (pre-LLM, `answering.py`)

Before any Gemini call is made, the question is checked locally:

- A set of `CLEARLY_OUT_OF_SCOPE_TERMS` (poem, weather, translate, recipe, etc.) immediately rejects unrelated questions
- A set of `DOMAIN_KEYWORDS` (sales order, billing, delivery, payment, customer, etc.) confirms business relevance
- Questions that match neither list are allowed through with neutral intent

This prevents wasting Gemini API calls on questions that are obviously unrelated to the dataset.

### Layer 2 — LLM self-classification (in-prompt)

The SQL generation prompt instructs Gemini to return `"in_scope": false` if it determines the question cannot be answered from the dataset. If the model returns `in_scope: false`, the request is rejected with a clear message before any SQL is executed.

### Layer 3 — Parser-based SQL validation (`sql_guard.py`)

Every SQL string returned by Gemini is parsed by `sqlglot` before execution. The validator:

- **Rejects forbidden keywords** — `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `REPLACE`, `GRANT`, `REVOKE`, `VACUUM`, `ATTACH`, `DETACH`, `CALL`, `EXEC`, `MERGE`, `SET`, `PRAGMA`
- **Rejects SQL comments** — `--` and `/* */` which could be used to inject logic
- **Rejects multiple statements** — only a single `SELECT` is permitted per call
- **Enforces `LIMIT 200`** — any query without a limit or with a limit above 200 is clamped automatically
- **Requires a SELECT statement** — any non-SELECT parsed result is rejected

Validation uses the AST produced by `sqlglot`, not string matching, so it cannot be bypassed by case tricks or whitespace.

### Layer 4 — In-memory execution boundary (`database.py`)

The database itself is the final guardrail:

- **Ephemeral** — the SQLite database exists only in RAM and is rebuilt from read-only source files on every restart. Even if a destructive query somehow passed all prior layers, it would affect only the current process instance and would be gone on the next restart.
- **Progress handler** — a step counter limits execution to `SQL_PROGRESS_STEP_LIMIT` (200,000 steps) to prevent runaway queries from locking the server.
- **Query timeout** — the SQLite connection is opened with a `timeout` of `QUERY_TIMEOUT_SECONDS` (3 seconds).
- **Result cap** — `fetchmany(MAX_QUERY_ROWS)` ensures at most 200 rows are ever returned regardless of what the SQL produces.

### Summarization grounding

The summarization prompt explicitly instructs the model to answer using only the returned rows. This prevents the LLM from combining dataset evidence with external knowledge to produce answers that are not supported by the actual data.

---

## Running the App

### Prerequisites

- Python 3.10+
- Node.js 18+
- A Google Gemini API key

### Setup

```bash
# Install Python dependencies
pip3 install -r requirements.txt

# Install Node dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### Production mode

```bash
npm run build        # Build the React frontend into frontend/dist/
bash scripts/run.sh  # Start FastAPI, serves built frontend at http://127.0.0.1:8000
```

### Development mode (hot reload)

```bash
# Terminal 1 — backend
bash scripts/run.sh

# Terminal 2 — frontend with hot reload
npm run dev          # Vite dev server at http://127.0.0.1:5173
                     # /api requests are proxied to port 8000
```

---

## Testing

```bash
python3 -m unittest discover -s tests -v
```

| Test | What it verifies |
|------|-----------------|
| `test_rejects_destructive_sql` | SQL guard blocks DROP, DELETE, INSERT, etc. |
| `test_enforces_allowlisted_tables` | Only the 14 curated views are queryable |
| `test_accepts_select_and_adds_limit` | Valid SELECT queries get LIMIT 200 enforced |
| `test_out_of_scope_prompt` | Off-topic questions are rejected before hitting Gemini |
| `test_real_table_query_executes` | Full end-to-end query executes against real loaded data |
| `test_graph_contains_real_entities` | Knowledge graph is correctly built from the dataset |

---

## Configuration

---

## AI Session Log

The AI-assisted implementation log is available at:

- [`docs/ai-session-log.md`](./docs/ai-session-log.md)

All configuration is loaded from `.env` via `app/config.py`.

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | required | Google Generative Language API key |
| `GEMINI_MODEL` | required | Model name, e.g. `gemini-2.0-flash` |
| `APP_HOST` | `127.0.0.1` | Host for Uvicorn |
| `APP_PORT` | `8000` | Port for Uvicorn |
| `MAX_QUERY_ROWS` | `200` | Maximum rows returned per query |
| `QUERY_TIMEOUT_SECONDS` | `3` | SQLite connection timeout |
| `SQL_PROGRESS_STEP_LIMIT` | `200000` | Max SQLite execution steps |
| `GRAPH_INITIAL_NODE_LIMIT` | `36` | Nodes shown on first graph render |
| `GRAPH_MAX_NODES` | `1600` | Maximum total nodes in the graph |

`.env` is excluded from version control via `.gitignore`. Never commit API keys.
