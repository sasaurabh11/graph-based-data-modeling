from __future__ import annotations

from collections import defaultdict
from typing import Any

from .config import GRAPH_INITIAL_NODE_LIMIT, GRAPH_MAX_NODES
from .types import GraphEdge, GraphNode


def _node_id(kind: str, raw_id: str) -> str:
    return f"{kind}:{raw_id}"


def curated_sql() -> str:
    return """
    CREATE VIEW customers AS
    SELECT
      bp.customer AS customer_id,
      bp.businessPartner AS business_partner_id,
      bp.businessPartnerName AS customer_name,
      bp.businessPartnerCategory AS customer_category,
      bp.creationDate AS creation_date,
      bp.lastChangeDate AS last_change_date,
      bp.businessPartnerIsBlocked AS is_blocked,
      bpa.addressId AS address_id,
      bpa.cityName AS city_name,
      bpa.region AS region,
      bpa.country AS country,
      bpa.postalCode AS postal_code,
      bpa.streetName AS street_name
    FROM business_partners bp
    LEFT JOIN business_partner_addresses bpa
      ON bpa.businessPartner = bp.businessPartner;

    CREATE VIEW addresses AS
    SELECT
      addressId AS address_id,
      businessPartner AS business_partner_id,
      cityName AS city_name,
      region,
      country,
      postalCode AS postal_code,
      streetName AS street_name,
      addressTimeZone AS address_time_zone
    FROM business_partner_addresses;

    CREATE VIEW plants_curated AS
    SELECT
      plant AS plant_id,
      plantName AS plant_name,
      addressId AS address_id,
      salesOrganization AS sales_organization,
      distributionChannel AS distribution_channel,
      division,
      isMarkedForArchiving AS is_marked_for_archiving
    FROM plants;

    CREATE VIEW products_curated AS
    SELECT
      p.product AS product_id,
      COALESCE(pd.productDescription, p.productOldId, p.product) AS product_name,
      p.productType AS product_type,
      p.productGroup AS product_group,
      p.baseUnit AS base_unit,
      p.division,
      p.industrySector AS industry_sector,
      p.grossWeight AS gross_weight,
      p.netWeight AS net_weight,
      p.isMarkedForDeletion AS is_marked_for_deletion
    FROM products p
    LEFT JOIN product_descriptions pd
      ON pd.product = p.product AND pd.language = 'EN';

    CREATE VIEW product_plants_curated AS
    SELECT
      product || ':' || plant AS product_plant_id,
      product AS product_id,
      plant AS plant_id,
      profitCenter AS profit_center,
      mrpType AS mrp_type,
      availabilityCheckType AS availability_check_type
    FROM product_plants;

    CREATE VIEW sales_orders AS
    SELECT
      salesOrder AS sales_order_id,
      soldToParty AS customer_id,
      salesOrderType AS sales_order_type,
      salesOrganization AS sales_organization,
      distributionChannel AS distribution_channel,
      organizationDivision AS organization_division,
      creationDate AS creation_date,
      requestedDeliveryDate AS requested_delivery_date,
      totalNetAmount AS total_net_amount,
      transactionCurrency AS transaction_currency,
      overallDeliveryStatus AS overall_delivery_status,
      overallOrdReltdBillgStatus AS overall_billing_status,
      headerBillingBlockReason AS header_billing_block_reason,
      deliveryBlockReason AS delivery_block_reason,
      customerPaymentTerms AS customer_payment_terms
    FROM sales_order_headers;

    CREATE VIEW sales_order_items_curated AS
    SELECT
      salesOrder || ':' || CAST(CAST(salesOrderItem AS INTEGER) AS TEXT) AS sales_order_item_id,
      salesOrder AS sales_order_id,
      CAST(CAST(salesOrderItem AS INTEGER) AS TEXT) AS sales_order_item_number,
      material AS product_id,
      requestedQuantity AS requested_quantity,
      requestedQuantityUnit AS requested_quantity_unit,
      netAmount AS net_amount,
      transactionCurrency AS transaction_currency,
      materialGroup AS material_group,
      productionPlant AS production_plant,
      storageLocation AS storage_location,
      salesDocumentRjcnReason AS rejection_reason,
      itemBillingBlockReason AS item_billing_block_reason
    FROM sales_order_items;

    CREATE VIEW sales_order_schedule_lines_curated AS
    SELECT
      salesOrder || ':' || CAST(CAST(salesOrderItem AS INTEGER) AS TEXT) || ':' || scheduleLine AS schedule_line_id,
      salesOrder AS sales_order_id,
      CAST(CAST(salesOrderItem AS INTEGER) AS TEXT) AS sales_order_item_number,
      scheduleLine AS schedule_line_number,
      confirmedDeliveryDate AS confirmed_delivery_date,
      confdOrderQtyByMatlAvailCheck AS confirmed_quantity,
      orderQuantityUnit AS order_quantity_unit
    FROM sales_order_schedule_lines;

    CREATE VIEW deliveries AS
    SELECT
      deliveryDocument AS delivery_id,
      creationDate AS creation_date,
      actualGoodsMovementDate AS actual_goods_movement_date,
      overallGoodsMovementStatus AS overall_goods_movement_status,
      overallPickingStatus AS overall_picking_status,
      overallProofOfDeliveryStatus AS overall_proof_of_delivery_status,
      shippingPoint AS shipping_point,
      deliveryBlockReason AS delivery_block_reason,
      headerBillingBlockReason AS header_billing_block_reason
    FROM outbound_delivery_headers;

    CREATE VIEW delivery_items_curated AS
    SELECT
      deliveryDocument || ':' || CAST(CAST(deliveryDocumentItem AS INTEGER) AS TEXT) AS delivery_item_id,
      deliveryDocument AS delivery_id,
      CAST(CAST(deliveryDocumentItem AS INTEGER) AS TEXT) AS delivery_item_number,
      referenceSdDocument AS sales_order_id,
      CAST(CAST(referenceSdDocumentItem AS INTEGER) AS TEXT) AS sales_order_item_number,
      plant AS plant_id,
      storageLocation AS storage_location,
      actualDeliveryQuantity AS actual_delivery_quantity,
      deliveryQuantityUnit AS delivery_quantity_unit,
      itemBillingBlockReason AS item_billing_block_reason
    FROM outbound_delivery_items;

    CREATE VIEW billing_documents AS
    SELECT
      billingDocument AS billing_document_id,
      soldToParty AS customer_id,
      billingDocumentType AS billing_document_type,
      billingDocumentDate AS billing_document_date,
      creationDate AS creation_date,
      totalNetAmount AS total_net_amount,
      transactionCurrency AS transaction_currency,
      companyCode AS company_code,
      fiscalYear AS fiscal_year,
      accountingDocument AS accounting_document,
      billingDocumentIsCancelled AS is_cancelled,
      cancelledBillingDocument AS cancelled_billing_document_id
    FROM billing_document_headers;

    CREATE VIEW billing_document_items_curated AS
    SELECT
      billingDocument || ':' || CAST(CAST(billingDocumentItem AS INTEGER) AS TEXT) AS billing_document_item_id,
      billingDocument AS billing_document_id,
      CAST(CAST(billingDocumentItem AS INTEGER) AS TEXT) AS billing_document_item_number,
      material AS product_id,
      billingQuantity AS billing_quantity,
      billingQuantityUnit AS billing_quantity_unit,
      netAmount AS net_amount,
      transactionCurrency AS transaction_currency,
      referenceSdDocument AS delivery_id,
      CAST(CAST(referenceSdDocumentItem AS INTEGER) AS TEXT) AS delivery_item_number
    FROM billing_document_items;

    CREATE VIEW journal_entries AS
    SELECT
      accountingDocument AS journal_entry_id,
      companyCode AS company_code,
      fiscalYear AS fiscal_year,
      MIN(referenceDocument) AS reference_billing_document_id,
      MIN(customer) AS customer_id,
      MIN(postingDate) AS posting_date,
      MIN(documentDate) AS document_date,
      MIN(accountingDocumentType) AS accounting_document_type,
      MIN(clearingAccountingDocument) AS clearing_accounting_document,
      SUM(amountInCompanyCodeCurrency) AS amount_in_company_code_currency,
      MIN(companyCodeCurrency) AS company_code_currency
    FROM journal_entry_items_accounts_receivable
    GROUP BY accountingDocument, companyCode, fiscalYear;

    CREATE VIEW payments AS
    SELECT
      p.accountingDocument AS payment_id,
      p.companyCode AS company_code,
      p.fiscalYear AS fiscal_year,
      MIN(p.customer) AS customer_id,
      MIN(p.clearingAccountingDocument) AS clearing_accounting_document,
      MIN(COALESCE(b.billingDocument, j.referenceDocument)) AS billing_document_id,
      MIN(p.postingDate) AS posting_date,
      MIN(p.documentDate) AS document_date,
      SUM(p.amountInCompanyCodeCurrency) AS amount_in_company_code_currency,
      MIN(p.companyCodeCurrency) AS company_code_currency
    FROM payments_accounts_receivable p
    LEFT JOIN billing_document_headers b
      ON b.accountingDocument = p.clearingAccountingDocument
     AND b.soldToParty = p.customer
    LEFT JOIN journal_entry_items_accounts_receivable j
      ON j.accountingDocument = p.clearingAccountingDocument
     AND j.customer = p.customer
    GROUP BY p.accountingDocument, p.companyCode, p.fiscalYear;
    """


def curated_schema(connection) -> dict[str, Any]:
    table_names = [
        "customers",
        "addresses",
        "plants_curated",
        "products_curated",
        "product_plants_curated",
        "sales_orders",
        "sales_order_items_curated",
        "sales_order_schedule_lines_curated",
        "deliveries",
        "delivery_items_curated",
        "billing_documents",
        "billing_document_items_curated",
        "journal_entries",
        "payments",
    ]
    tables: dict[str, list[str]] = {}
    for name in table_names:
        cursor = connection.execute(f"SELECT * FROM {name} LIMIT 0")
        tables[name] = [column[0] for column in cursor.description]
    return {
        "tables": tables,
        "relationships": [
            "customers.customer_id -> sales_orders.customer_id",
            "sales_orders.sales_order_id -> sales_order_items_curated.sales_order_id",
            "sales_order_items_curated.(sales_order_id,sales_order_item_number) -> delivery_items_curated.(sales_order_id,sales_order_item_number)",
            "deliveries.delivery_id -> delivery_items_curated.delivery_id",
            "delivery_items_curated.(delivery_id,delivery_item_number) -> billing_document_items_curated.(delivery_id,delivery_item_number)",
            "billing_documents.billing_document_id -> billing_document_items_curated.billing_document_id",
            "billing_documents.accounting_document -> journal_entries.journal_entry_id",
            "billing_documents.billing_document_id -> payments.billing_document_id",
            "customers.customer_id -> billing_documents.customer_id",
            "customers.customer_id -> journal_entries.customer_id",
            "customers.customer_id -> payments.customer_id",
            "payments.clearing_accounting_document -> journal_entries.journal_entry_id",
            "products_curated.product_id -> sales_order_items_curated.product_id",
            "products_curated.product_id -> billing_document_items_curated.product_id",
            "products_curated.product_id -> product_plants_curated.product_id",
            "plants_curated.plant_id -> product_plants_curated.plant_id",
            "plants_curated.plant_id -> delivery_items_curated.plant_id",
            "customers.address_id -> addresses.address_id",
        ],
    }


def _build_examples(connection) -> list[str]:
    billing = connection.execute("SELECT billing_document_id FROM billing_documents ORDER BY total_net_amount DESC LIMIT 1").fetchone()
    customer = connection.execute("SELECT customer_id, customer_name FROM customers ORDER BY customer_name LIMIT 1").fetchone()
    plant = connection.execute("SELECT plant_id FROM plants_curated ORDER BY plant_id LIMIT 1").fetchone()
    examples = [
        "Which customers have placed the most sales orders?",
        "What is the total billing amount per customer?",
        "Which products appear most often in billing document items?",
        "How many deliveries were shipped from each plant?",
        "What is the total payment amount received per customer?",
        "List all sales orders that have a delivery block or billing block.",
    ]
    if billing:
        examples.append(f"Show all items for billing document {billing['billing_document_id']}.")
    if customer:
        examples.append(f"List all sales orders placed by customer {customer['customer_id']}.")
    if plant:
        examples.append(f"List all delivery items shipped from plant {plant['plant_id']}.")
    return examples[:6]


def build_graph(connection) -> dict[str, Any]:
    node_index: dict[str, GraphNode] = {}
    edge_index: dict[str, GraphEdge] = {}
    degree = defaultdict(int)

    def add_node(kind: str, raw_id: str | None, label: str, title: str, properties: dict[str, Any]) -> None:
        if not raw_id:
            return
        node_id = _node_id(kind, str(raw_id))
        node_index[node_id] = GraphNode(
            id=node_id,
            label=str(label or raw_id),
            kind=kind,
            title=title,
            properties=properties,
        )

    def add_edge(source_kind: str, source_id: str | None, target_kind: str, target_id: str | None, relation: str) -> None:
        if not source_id or not target_id:
            return
        source = _node_id(source_kind, str(source_id))
        target = _node_id(target_kind, str(target_id))
        if source not in node_index or target not in node_index:
            return
        edge_id = f"{source}|{relation}|{target}"
        edge_index[edge_id] = GraphEdge(id=edge_id, source=source, target=target, relation=relation)
        degree[source] += 1
        degree[target] += 1

    def build_initial_node_ids(nodes: list[GraphNode]) -> list[str]:
        nodes_by_id = {node.id: node for node in nodes}
        ordered_ids: list[str] = []
        seen: set[str] = set()

        def add_node_id(node_id: str | None) -> None:
            if not node_id or node_id in seen or node_id not in nodes_by_id:
                return
            ordered_ids.append(node_id)
            seen.add(node_id)

        exemplar = connection.execute(
            """
            SELECT
              bd.billing_document_id,
              bd.customer_id,
              c.address_id,
              bd.accounting_document AS journal_entry_id,
              p.payment_id,
              bi.billing_document_item_id,
              bi.product_id,
              bi.delivery_id,
              bi.delivery_item_number,
              di.delivery_item_id,
              di.plant_id,
              soi.sales_order_id,
              soi.sales_order_item_id
            FROM billing_documents bd
            LEFT JOIN customers c
              ON c.customer_id = bd.customer_id
            LEFT JOIN payments p
              ON p.billing_document_id = bd.billing_document_id
            LEFT JOIN billing_document_items_curated bi
              ON bi.billing_document_id = bd.billing_document_id
            LEFT JOIN delivery_items_curated di
              ON di.delivery_id = bi.delivery_id
             AND di.delivery_item_number = bi.delivery_item_number
            LEFT JOIN sales_order_items_curated soi
              ON soi.sales_order_id = di.sales_order_id
             AND soi.sales_order_item_number = di.sales_order_item_number
            WHERE bi.billing_document_item_id IS NOT NULL
              AND di.delivery_item_id IS NOT NULL
              AND soi.sales_order_item_id IS NOT NULL
            ORDER BY bd.billing_document_id
            LIMIT 1
            """
        ).fetchone()
        if exemplar:
            add_node_id(_node_id("customer", exemplar["customer_id"]))
            add_node_id(_node_id("address", exemplar["address_id"]))
            add_node_id(_node_id("sales_order", exemplar["sales_order_id"]))
            add_node_id(_node_id("sales_order_item", exemplar["sales_order_item_id"]))
            add_node_id(_node_id("delivery", exemplar["delivery_id"]))
            add_node_id(_node_id("delivery_item", exemplar["delivery_item_id"]))
            add_node_id(_node_id("billing_document", exemplar["billing_document_id"]))
            add_node_id(_node_id("billing_document_item", exemplar["billing_document_item_id"]))
            add_node_id(_node_id("journal_entry", exemplar["journal_entry_id"]))
            add_node_id(_node_id("payment", exemplar["payment_id"]))
            add_node_id(_node_id("product", exemplar["product_id"]))
            add_node_id(_node_id("plant", exemplar["plant_id"]))

        kind_limits = {
            "customer": 4,
            "sales_order": 4,
            "delivery": 4,
            "billing_document": 4,
            "payment": 4,
            "journal_entry": 4,
            "product": 4,
            "plant": 4,
            "address": 2,
            "sales_order_item": 2,
            "delivery_item": 2,
            "billing_document_item": 2,
        }
        kind_counts = {kind: 0 for kind in kind_limits}
        for node_id in ordered_ids:
            kind_counts[nodes_by_id[node_id].kind] += 1

        for node in nodes:
            limit = kind_limits.get(node.kind)
            if limit is None or kind_counts[node.kind] >= limit:
                continue
            add_node_id(node.id)
            kind_counts[node.kind] += 1
            if len(ordered_ids) >= GRAPH_INITIAL_NODE_LIMIT:
                break

        return ordered_ids[:GRAPH_INITIAL_NODE_LIMIT]

    node_specs = [
        ("customer", "customers", "customer_id", "customer_name", "Customer"),
        ("address", "addresses", "address_id", "city_name", "Address"),
        ("plant", "plants_curated", "plant_id", "plant_name", "Plant"),
        ("product", "products_curated", "product_id", "product_name", "Product"),
        ("sales_order", "sales_orders", "sales_order_id", "sales_order_id", "Sales Order"),
        ("sales_order_item", "sales_order_items_curated", "sales_order_item_id", "sales_order_item_id", "Sales Order Item"),
        ("delivery", "deliveries", "delivery_id", "delivery_id", "Delivery"),
        ("delivery_item", "delivery_items_curated", "delivery_item_id", "delivery_item_id", "Delivery Item"),
        ("billing_document", "billing_documents", "billing_document_id", "billing_document_id", "Billing Document"),
        ("billing_document_item", "billing_document_items_curated", "billing_document_item_id", "billing_document_item_id", "Billing Document Item"),
        ("journal_entry", "journal_entries", "journal_entry_id", "journal_entry_id", "Journal Entry"),
        ("payment", "payments", "payment_id", "payment_id", "Payment"),
    ]
    for kind, table, id_column, label_column, title in node_specs:
        for row in connection.execute(f"SELECT * FROM {table}"):
            payload = dict(row)
            add_node(kind, payload[id_column], payload.get(label_column) or payload[id_column], title, payload)

    for row in connection.execute("SELECT customer_id, address_id FROM customers WHERE address_id IS NOT NULL"):
        add_edge("customer", row["customer_id"], "address", row["address_id"], "HAS_ADDRESS")
    for row in connection.execute("SELECT sales_order_id, customer_id FROM sales_orders"):
        add_edge("customer", row["customer_id"], "sales_order", row["sales_order_id"], "PLACED_ORDER")
    for row in connection.execute("SELECT sales_order_id, sales_order_item_id, product_id FROM sales_order_items_curated"):
        add_edge("sales_order", row["sales_order_id"], "sales_order_item", row["sales_order_item_id"], "HAS_ITEM")
        add_edge("sales_order_item", row["sales_order_item_id"], "product", row["product_id"], "ORDERS_PRODUCT")
    for row in connection.execute("SELECT soi.sales_order_item_id, di.delivery_item_id FROM sales_order_items_curated soi JOIN delivery_items_curated di ON di.sales_order_id = soi.sales_order_id AND di.sales_order_item_number = soi.sales_order_item_number"):
        add_edge("sales_order_item", row["sales_order_item_id"], "delivery_item", row["delivery_item_id"], "FULFILLED_BY")
    for row in connection.execute("SELECT delivery_id, delivery_item_id, plant_id FROM delivery_items_curated"):
        add_edge("delivery", row["delivery_id"], "delivery_item", row["delivery_item_id"], "HAS_ITEM")
        add_edge("delivery_item", row["delivery_item_id"], "plant", row["plant_id"], "SHIPPED_FROM")
    for row in connection.execute("SELECT DISTINCT delivery_id, plant_id FROM delivery_items_curated WHERE plant_id IS NOT NULL"):
        add_edge("delivery", row["delivery_id"], "plant", row["plant_id"], "SHIPS_FROM_PLANT")
    for row in connection.execute("SELECT DISTINCT di.sales_order_id, di.delivery_id FROM delivery_items_curated di WHERE di.sales_order_id IS NOT NULL"):
        add_edge("sales_order", row["sales_order_id"], "delivery", row["delivery_id"], "FULFILLED_BY_DELIVERY")
    for row in connection.execute("SELECT billing_document_id, billing_document_item_id, product_id, delivery_id, delivery_item_number FROM billing_document_items_curated"):
        add_edge("billing_document", row["billing_document_id"], "billing_document_item", row["billing_document_item_id"], "HAS_ITEM")
        add_edge("billing_document_item", row["billing_document_item_id"], "product", row["product_id"], "BILLS_PRODUCT")
        add_edge("delivery_item", f"{row['delivery_id']}:{row['delivery_item_number']}" if row["delivery_id"] and row["delivery_item_number"] else None, "billing_document_item", row["billing_document_item_id"], "BILLED_AS")
    for row in connection.execute("SELECT billing_document_id, customer_id, accounting_document FROM billing_documents"):
        add_edge("customer", row["customer_id"], "billing_document", row["billing_document_id"], "BILLED_TO")
        add_edge("billing_document", row["billing_document_id"], "journal_entry", row["accounting_document"], "POSTED_TO")
    for row in connection.execute("SELECT DISTINCT b.billing_document_id, b.delivery_id FROM billing_document_items_curated b WHERE b.delivery_id IS NOT NULL"):
        add_edge("delivery", row["delivery_id"], "billing_document", row["billing_document_id"], "BILLED_BY")
    for row in connection.execute("SELECT journal_entry_id, customer_id FROM journal_entries"):
        add_edge("customer", row["customer_id"], "journal_entry", row["journal_entry_id"], "HAS_JOURNAL_ENTRY")
    for row in connection.execute("SELECT payment_id, customer_id, billing_document_id, clearing_accounting_document FROM payments"):
        add_edge("customer", row["customer_id"], "payment", row["payment_id"], "MADE_PAYMENT")
        add_edge("billing_document", row["billing_document_id"], "payment", row["payment_id"], "SETTLED_BY_PAYMENT")
        add_edge("journal_entry", row["clearing_accounting_document"], "payment", row["payment_id"], "CLEARED_BY_PAYMENT")
    for row in connection.execute("SELECT product_id, plant_id FROM product_plants_curated"):
        add_edge("product", row["product_id"], "plant", row["plant_id"], "AVAILABLE_AT_PLANT")

    for node in node_index.values():
        node.degree = degree.get(node.id, 0)

    nodes = sorted(node_index.values(), key=lambda item: (-item.degree, item.kind, item.label))
    if len(nodes) > GRAPH_MAX_NODES:
        keep = {node.id for node in nodes[:GRAPH_MAX_NODES]}
        nodes = [node for node in nodes if node.id in keep]
        edge_index = {
            edge_id: edge
            for edge_id, edge in edge_index.items()
            if edge.source in keep and edge.target in keep
        }

    return {
        "nodes": [node.__dict__ for node in nodes],
        "edges": [edge.__dict__ for edge in edge_index.values()],
        "initialNodeIds": build_initial_node_ids(nodes),
        "examples": _build_examples(connection),
    }
