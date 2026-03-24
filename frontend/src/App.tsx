import { useCallback, useEffect, useMemo, useState } from "react";
import { askQuestion, getGraph, getMeta, getNeighbors } from "./api";
import { ChatPanel } from "./components/ChatPanel";
import { GraphCanvas } from "./components/GraphCanvas";
import { InspectorPanel } from "./components/InspectorPanel";
import type { GraphNode, GraphPayload } from "./types";

const GRAPH_LEGEND = [
  { kind: "customer", label: "Customer", color: "#ff6b6b", description: "Who buys the order." },
  { kind: "product", label: "Product", color: "#38bdf8", description: "What is sold or billed." },
  { kind: "plant", label: "Plant", color: "#10b981", description: "Where goods are available or shipped from." },
  { kind: "sales_order", label: "Sales Order", color: "#8b5cf6", description: "The commercial order header." },
  { kind: "delivery", label: "Delivery", color: "#22c55e", description: "The physical shipment document." },
  { kind: "billing_document", label: "Billing Document", color: "#fb7185", description: "The invoice or billing record." },
  { kind: "journal_entry", label: "Journal Entry", color: "#60a5fa", description: "The accounting posting." },
  { kind: "payment", label: "Payment", color: "#14b8a6", description: "The receivable settlement record." },
];

const GRAPH_ACTIONS = [
  "Click a node to inspect its metadata.",
  "Use “Expand related nodes” in the inspector to reveal the next step in the business flow.",
  "Ask a question in chat to highlight matching entities on the graph.",
  "Use Reset to return to the starting order-to-cash sample.",
];

export function App() {
  const [graph, setGraph] = useState<GraphPayload | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [highlightedNodeIds, setHighlightedNodeIds] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [examples, setExamples] = useState<string[]>([]);
  const [expandedNodeIds, setExpandedNodeIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    void Promise.all([getGraph(), getMeta()])
      .then(([graphPayload, metaPayload]) => {
        setGraph(graphPayload);
        setExamples(metaPayload.examples);
      })
      .catch((nextError: Error) => {
        setError(nextError.message);
      });
  }, []);

  const selectedNodeId = selectedNode?.id ?? null;

  const handleExpandNode = useCallback(async (node: GraphNode) => {
    if (!graph || expandedNodeIds.has(node.id)) return;
    const neighborPayload = await getNeighbors(node.id);
    const nextNodeMap = new Map(graph.nodes.map((item) => [item.id, item]));
    neighborPayload.nodes.forEach((item) => nextNodeMap.set(item.id, item));

    const nextEdgeMap = new Map(graph.edges.map((item) => [item.id, item]));
    neighborPayload.edges.forEach((item) => nextEdgeMap.set(item.id, item));

    setGraph({
      ...graph,
      nodes: [...nextNodeMap.values()],
      edges: [...nextEdgeMap.values()],
      initialNodeIds: [...new Set([...graph.initialNodeIds, ...neighborPayload.nodes.map((item) => item.id)])],
    });
    setExpandedNodeIds((prev) => new Set(prev).add(node.id));
  }, [expandedNodeIds, graph]);

  const nodeById = useMemo(() => new Map((graph?.nodes ?? []).map((node) => [node.id, node])), [graph]);
  const kindCounts = useMemo(() => {
    const counts = new Map<string, number>();
    graph?.nodes.forEach((node) => counts.set(node.kind, (counts.get(node.kind) ?? 0) + 1));
    return counts;
  }, [graph]);

  const handleAsk = useCallback(async (question: string) => {
    const payload = await askQuestion(question);
    setGraph((current) => (
      current
        ? {
            ...current,
            initialNodeIds: [...new Set([...current.initialNodeIds, ...payload.highlightNodeIds])],
          }
        : current
    ));
    setHighlightedNodeIds(payload.highlightNodeIds);
    const nextSelectedId = payload.highlightNodeIds[0];
    if (nextSelectedId) {
      const nextNode = nodeById.get(nextSelectedId);
      if (nextNode) {
        setSelectedNode(nextNode);
      }
    }
    return payload;
  }, [nodeById]);

  if (error) {
    return <main className="app-shell error-shell">{error}</main>;
  }

  if (!graph) {
    return <main className="app-shell loading-shell">Loading graph and schema...</main>;
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <h1>Order-to-Cash Graph Explorer</h1>
        <p>Explore the business flow from customer and sales order through delivery, billing, journal entry, and payment.</p>
      </header>

      <section className="workspace-layout">
        <div className="graph-column">
          <section className="panel graph-panel">
            <div className="panel-heading panel-heading-row">
              <div>
                <h2>Graph</h2>
                <p>Start with a billing document, sales order, or customer and follow the linked records through the flow.</p>
              </div>
              <button
                className="ghost-button"
                onClick={() => {
                  setSelectedNode(null);
                  setHighlightedNodeIds([]);
                  setExpandedNodeIds(new Set());
                  void getGraph().then(setGraph).catch((nextError: Error) => setError(nextError.message));
                }}
              >
                Reset
              </button>
            </div>
            <GraphCanvas
              nodes={graph.nodes}
              edges={graph.edges}
              initialNodeIds={graph.initialNodeIds}
              highlightedNodeIds={highlightedNodeIds}
              selectedNodeId={selectedNodeId}
              onSelectNode={setSelectedNode}
            />
          </section>
        </div>

        <aside className="chat-column">
          <ChatPanel
            examples={examples}
            onAsk={handleAsk}
          />
          <InspectorPanel node={selectedNode} onExpandNode={(node) => void handleExpandNode(node)} />
        </aside>
      </section>

      <section className="info-section">
        <section className="info-grid">
          <section className="panel">
            <div className="panel-heading">
              <h2>Node Types</h2>
              <p>Each color represents a different business entity in the order-to-cash process.</p>
            </div>
            <div className="legend-grid">
              {GRAPH_LEGEND.map((item) => (
                <div key={item.kind} className="legend-item">
                  <span className="legend-swatch" style={{ backgroundColor: item.color }} />
                  <div>
                    <strong>{item.label}</strong>
                    <span>{item.description}</span>
                    <small>{kindCounts.get(item.kind) ?? 0} loaded nodes</small>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="panel">
            <div className="panel-heading">
              <h2>How To Use</h2>
              <p>The graph is interactive. Use it to move through connected business documents.</p>
            </div>
            <ul className="guide-list">
              {GRAPH_ACTIONS.map((action) => (
                <li key={action}>{action}</li>
              ))}
            </ul>
          </section>
        </section>
      </section>
    </main>
  );
}
