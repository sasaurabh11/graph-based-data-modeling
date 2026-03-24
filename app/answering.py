from __future__ import annotations

import json
import re
from typing import Any

from .gemini import GeminiError, generate_text

OUT_OF_SCOPE_MESSAGE = "This system answers only questions grounded in the provided business dataset."

CLEARLY_OUT_OF_SCOPE_TERMS = {
    "poem",
    "poetry",
    "joke",
    "story",
    "song",
    "recipe",
    "weather",
    "capital of",
    "movie",
    "sports score",
    "horoscope",
    "translate",
    "what is ai",
    "who is the president",
    "general knowledge",
}

DOMAIN_KEYWORDS = {
    "sales order",
    "order",
    "ordered",
    "delivery",
    "shipment",
    "ship",
    "billing",
    "billing document",
    "invoice",
    "billed",
    "receivable",
    "ar ",
    "journal",
    "accounting",
    "ledger",
    "payment",
    "clearing",
    "settlement",
    "customer",
    "business partner",
    "product",
    "sku",
    "material",
    "item",
    "line item",
    "plant",
    "address",
    "shipping",
    "sold-to",
    "sold to",
    "broken flow",
    "incomplete flow",
    "top products",
    "billing count",
}


def is_in_scope(question: str) -> bool:
    lowered = question.lower()
    has_domain_signal = any(keyword in lowered for keyword in DOMAIN_KEYWORDS) or bool(re.search(r"\b\d{6,12}\b", question))
    if has_domain_signal:
        return True
    if any(term in lowered for term in CLEARLY_OUT_OF_SCOPE_TERMS):
        return False
    return True


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\n", "", stripped)
        stripped = re.sub(r"\n```$", "", stripped)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Model did not return JSON.")
    return json.loads(stripped[start : end + 1])


def generate_sql(question: str, schema: dict[str, Any], examples: list[str]) -> tuple[str, str]:
    if not is_in_scope(question):
        raise ValueError(OUT_OF_SCOPE_MESSAGE)

    schema_lines = [f"{table}({', '.join(columns)})" for table, columns in schema["tables"].items()]
    prompt = f"""
You are generating read-only SQLite for a business dataset.

Rules:
- Return JSON only with keys: in_scope, sql, rationale.
- If the question is not about this dataset, return {{"in_scope": false, "sql": "", "rationale": "out_of_scope"}}.
- Output exactly one SQLite SELECT query.
- Never use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, PRAGMA, comments, or multiple statements.
- Use only these tables and columns:
{chr(10).join(schema_lines)}

Known relationships:
{chr(10).join(schema["relationships"])}

Critical SQL rules to avoid runtime errors:
- ALWAYS prefer single-table queries. Only JOIN when it is strictly necessary.
- When you do JOIN, ALWAYS prefix every column reference with its table alias (e.g. so.customer_id, not just customer_id). Never write a bare column name in any query that touches more than one table.
- Use short meaningful aliases (so, bd, di, soi, c, p, pc) not T1/T2/T3.
- Never reference a column that does not exist in the schema above.
- Aggregations: use COUNT(*), SUM(col), MIN(col) — always GROUP BY the non-aggregated columns.

Examples of safe patterns:
- Single table: SELECT customer_id, COUNT(*) AS cnt FROM sales_orders GROUP BY customer_id ORDER BY cnt DESC LIMIT 10
- Two tables: SELECT so.sales_order_id, so.customer_id, so.total_net_amount FROM sales_orders so JOIN billing_documents bd ON bd.customer_id = so.customer_id LIMIT 20
- Filter: SELECT billing_document_id, total_net_amount FROM billing_documents WHERE is_cancelled = 0 ORDER BY total_net_amount DESC LIMIT 10

Example user questions:
{chr(10).join(f"- {example}" for example in examples)}

User question:
{question}
""".strip()

    payload = _extract_json(generate_text(prompt, temperature=0.05))
    if not payload.get("in_scope"):
        raise ValueError(OUT_OF_SCOPE_MESSAGE)
    sql = str(payload.get("sql", "")).strip()
    rationale = str(payload.get("rationale", "")).strip()
    if not sql:
        raise ValueError("I could not produce a safe dataset-backed query for that question.")
    return sql, rationale


def summarize_answer(question: str, sql: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "I could not find evidence in the dataset for that question."
    prompt = f"""
Return JSON only with key: answer.

Answer the question using only the provided rows.
Be concise and grounded.
If the rows are partial evidence, say so.

Question:
{question}

SQL:
{sql}

Rows:
{json.dumps(rows[:20], ensure_ascii=True, indent=2)}
""".strip()
    try:
        payload = _extract_json(generate_text(prompt, temperature=0.2))
        answer = str(payload.get("answer", "")).strip()
        return answer or "I found dataset-backed results."
    except GeminiError:
        return f"I found {len(rows)} dataset-backed row(s)."
