# AI Coding Session Log

This document summarizes how AI was used during the implementation of the take-home assignment, what architectural decisions were made, how those decisions evolved, and how verification was performed.

---

## Project

**Assignment:** Forward Deployed Engineer Task: Graph-Based Data Modeling and Query System

**Repository:** `/Users/saurabh/Documents/Graph-based-data-modeling`

**Primary AI workflow used:** iterative implementation, verification, review, and refinement with Codex

---

## Objectives

The implementation targeted the following non-negotiable requirements:

1. Load the provided fragmented business dataset
2. Convert it into an explicit graph model of entities and relationships
3. Visualize the graph in a frontend UI
4. Support natural-language questioning over the same dataset
5. Generate structured SQL dynamically
6. Keep answers grounded in the dataset
7. Apply backend query guardrails
8. Reject out-of-domain questions

---

## Working Style

The AI was used as an implementation and review assistant, not as a blind code generator.

The workflow was:

1. Inspect the repository and data shape first
2. Infer the real schema from the dataset instead of hardcoding assumptions
3. Build the smallest viable backend pipeline
4. Add graph construction and query safety before frontend polish
5. Replace template or placeholder data with the actual dataset
6. Re-review the application against the assignment requirements
7. Patch gaps found during review
8. Improve UX after core correctness was in place

---

## Architecture Decisions

### 1. Keep the system single-process and startup-loaded

**Decision**

Load all JSONL source data into an in-memory SQLite database at startup.

**Why**

- The dataset size is small enough for memory
- Setup stays simple
- Query latency is low
- The app remains reproducible on every restart

**Trade-off**

- No persistence between restarts
- Startup performs the full ingest

### 2. Use curated SQL views between raw data and the LLM

**Decision**

Load raw partitioned tables first, then define curated business views with normalized names and derived identifiers.

**Why**

- The raw dataset uses source-oriented field names
- Curated views make the graph model and LLM prompt more stable
- The business model becomes easier to reason about and test

**Trade-off**

- Adds a modeling layer that must be kept consistent with the source data

### 3. Build the graph from the same curated views used for query answering

**Decision**

Use the curated views as the shared source for both graph construction and SQL answering.

**Why**

- Prevents drift between UI and chat answers
- Keeps graph edges grounded in actual data relationships
- Makes highlighting answer paths straightforward

### 4. Use Gemini for SQL generation and summarization

**Decision**

Use Gemini to convert natural language to SQL and to summarize returned rows.

**Why**

- The assignment explicitly allows an LLM-powered interface
- Gemini is the chosen model provider for this project
- The model is only used after the data model and SQL execution path are controlled

### 5. Use React + Cytoscape.js for graph interaction

**Decision**

Move the frontend to a Vite React app and use Cytoscape.js for graph visualization.

**Why**

- Cytoscape is a practical fit for node-edge exploration
- React makes it easier to manage graph, chat, inspector, and UI state together

---

## Implementation Timeline

### Phase 1. Repository and dataset inspection

**AI contribution**

- Inspected repo contents and existing code
- Read the actual files under `data/`
- Identified real entities and join keys

**Result**

Confirmed the dataset contains real order-to-cash records:

- sales orders
- sales order items
- deliveries
- delivery items
- billing documents
- billing document items
- journal entry AR lines
- payments AR lines
- business partners
- addresses
- products
- plants

### Phase 2. Replace placeholder/demo data with real ingestion

**AI contribution**

- Removed template/demo dataset usage
- Switched the app to build from real JSONL folders
- Normalized nested fields and inferred SQLite column types

**Result**

The application now uses the provided dataset as the only source of truth.

### Phase 3. Build graph model and query pipeline

**AI contribution**

- Defined node and edge construction from curated views
- Added Gemini-based SQL generation
- Added query execution and answer grounding
- Added frontend graph rendering and inspector

**Result**

The application reached end-to-end functionality with:

- graph rendering
- chat interface
- dynamic SQL generation
- grounded evidence display

### Phase 4. Assignment review and gap analysis

**AI contribution**

Performed a structured review against the assignment and found concrete gaps.

**Important issues discovered**

1. The invoice-to-payment relationship was not modeled correctly
2. The in-scope question gate was too narrow and rejected valid business prompts
3. The initial graph view was technically correct but visually confusing

### Phase 5. Patch missing billing-to-payment functionality

**AI contribution**

Used the real data to trace the missing payment path:

`payments.clearingAccountingDocument -> billing_document_headers.accountingDocument`

and, where available:

`payments.clearingAccountingDocument -> journal_entry_items_accounts_receivable.accountingDocument -> referenceDocument`

**Result**

The graph now includes real payment linkage back to billing documents.

### Phase 6. Improve graph usability

**AI contribution**

- Changed the initial graph seeding to show a representative order-to-cash slice first
- Added color and shape differentiation by node type
- Added clearer labeling and edge highlighting
- Added node guidance and usage help
- Moved the selected-node inspector into a more useful UI location

**Result**

The graph became easier to interpret and less dominated by dense high-degree clusters.

### Phase 7. Simplify UI and interaction flow

**AI contribution**

- Simplified the top header
- Reworked the page layout to graph-left / chat-right
- Fixed chat ordering so answers no longer appear above the user message
- Added fixed-height chat behavior
- Added input-driven example suggestions only when the user is typing

### Phase 8. Relax backend SQL restrictions per user request

**AI contribution**

- Reduced SQL guard strictness to focus mainly on dangerous commands, comments, and multiple statements
- Preserved single-statement parsing and row-limit enforcement

**Important note**

This was a deliberate user-directed trade-off.

It improves flexibility, but it is less strict than the earlier parser-and-allowlist model and therefore weaker from a security-review perspective.

---

## Representative Decision Log

### Decision: use curated business views instead of querying raw tables directly

**Prompt/problem**

The raw dataset uses many source-specific field names and fragmented tables.

**Reasoning**

If the LLM sees only raw source tables, SQL generation becomes brittle and hard to validate. Curated views create a more stable business layer.

**Outcome**

Created a curated schema for customers, products, orders, deliveries, billing documents, journal entries, and payments.

### Decision: treat the graph as a primary data model, not only a visualization

**Prompt/problem**

The assignment explicitly requires graph-based modeling, not only relational joins.

**Reasoning**

A graph should exist independently as nodes and edges with real business relationships, so the UI is reflecting a data model rather than drawing join results ad hoc.

**Outcome**

Implemented `GraphNode` and `GraphEdge` generation from curated business views.

### Decision: rework the initial graph view

**Prompt/problem**

The first version of the graph surfaced highly connected clusters that were correct but hard to understand.

**Reasoning**

Users need to understand the business flow quickly. An exemplar chain is more helpful than a pure degree-based initial render.

**Outcome**

Initial graph now starts from a representative order-to-cash path and then fills remaining visible nodes more evenly.

### Decision: broaden the in-scope check

**Prompt/problem**

Valid prompts such as “top SKUs by billed count” could be rejected because they did not match a narrow keyword list.

**Reasoning**

The system should reject truly irrelevant prompts, but it should not block reasonable business phrasing too aggressively before model inference.

**Outcome**

Relaxed the pre-filter so in-domain phrasing is more likely to reach the model.

---

## How AI Helped

AI materially contributed in these areas:

- repository inspection and schema discovery
- mapping fragmented source tables into a coherent order-to-cash model
- identifying missing business relationships during review
- refining graph UX after functional correctness was in place
- generating and then validating implementation patches
- writing regression tests for important fixes

AI was not used as an unquestioned source of truth. Intermediate results were checked against:

- the real dataset
- runtime inspection queries
- unit and integration tests
- frontend build verification

---

## Verification and Debugging

### Backend verification

Repeated checks were used to validate:

- ingestion works from the real `data/` directory
- graph nodes and edges are populated
- payment rows link to billing documents
- safe SQL execution path still works
- dangerous SQL commands are rejected

### Frontend verification

The frontend was rebuilt after major UI iterations to confirm:

- React compilation passed
- Cytoscape integration still rendered
- layout changes did not break the app shell
- chat ordering and fixed-height behavior worked after refactoring

### Typical verification commands

```bash
python3 -m unittest discover -s tests -v
npm run build
```

---

## Final State Summary

At the end of the AI-assisted implementation, the project provides:

- real dataset ingestion from partitioned JSONL
- graph-based modeling of the business flow
- visual graph exploration in React + Cytoscape
- natural-language querying via Gemini
- dynamic SQL generation
- grounded evidence-backed answers
- configurable SQL guard behavior
- documented architecture and implementation rationale

---

## Reviewer Notes

This log is intended to demonstrate:

- architectural reasoning
- iteration discipline
- willingness to re-evaluate earlier decisions
- practical use of AI as a development accelerator
- verification after each meaningful change

The strongest signal from the session was not speed alone, but the repeated cycle of:

**inspect -> infer -> implement -> verify -> review -> refine**

