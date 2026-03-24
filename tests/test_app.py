from __future__ import annotations

import unittest

from app.answering import OUT_OF_SCOPE_MESSAGE, is_in_scope
from app.bootstrap import bootstrap_data
from app.database import execute_readonly_query
from app.sql_guard import SqlValidationError, validate_sql


class QuerySafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.connection, cls.graph, cls.schema = bootstrap_data()

    def test_rejects_destructive_sql(self) -> None:
        with self.assertRaises(SqlValidationError):
            validate_sql("DROP TABLE billing_documents", self.schema)

    def test_rejects_sql_comments(self) -> None:
        with self.assertRaises(SqlValidationError):
            validate_sql("SELECT 1 -- comment", self.schema)

    def test_accepts_select_and_adds_limit(self) -> None:
        sql = validate_sql("SELECT billing_document_id FROM billing_documents", self.schema)
        self.assertIn("LIMIT 200", sql)

    def test_out_of_scope_prompt(self) -> None:
        self.assertFalse(is_in_scope("Write me a poem about the moon"), OUT_OF_SCOPE_MESSAGE)

    def test_allows_valid_business_prompt_without_exact_keyword(self) -> None:
        self.assertTrue(is_in_scope("Show top SKUs by billed count for sold-to 320000083"))

    def test_real_table_query_executes(self) -> None:
        sql = validate_sql("SELECT sales_order_id, customer_id FROM sales_orders ORDER BY sales_order_id", self.schema)
        rows = execute_readonly_query(self.connection, sql, [])
        self.assertTrue(len(rows) > 0)
        self.assertIn("sales_order_id", rows[0])

    def test_graph_contains_real_entities(self) -> None:
        self.assertTrue(len(self.graph["nodes"]) > 0)
        self.assertTrue(any(node["kind"] == "billing_document" for node in self.graph["nodes"]))

    def test_payments_link_to_real_billing_documents(self) -> None:
        row = self.connection.execute(
            "SELECT COUNT(*) AS count FROM payments WHERE billing_document_id IS NOT NULL"
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertGreater(row["count"], 0)

    def test_graph_contains_billing_to_payment_edges(self) -> None:
        self.assertTrue(any(edge["relation"] == "SETTLED_BY_PAYMENT" for edge in self.graph["edges"]))


if __name__ == "__main__":
    unittest.main()
