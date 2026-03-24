import type { GraphNode } from "../types";

type InspectorPanelProps = {
  node: GraphNode | null;
  onExpandNode?: (node: GraphNode) => void;
};

export function InspectorPanel({ node, onExpandNode }: InspectorPanelProps) {
  if (!node) {
    return (
      <section className="panel inspector-panel">
        <div className="panel-heading">
          <h2>Inspector</h2>
          <p>Select a node to inspect its metadata.</p>
        </div>
      </section>
    );
  }

  const entries = Object.entries(node.properties).filter(([, value]) => value !== null && value !== "");

  return (
    <section className="panel inspector-panel">
      <div className="panel-heading">
        <h2>{node.title}</h2>
        <p>
          {node.label} <span className="muted-dot">·</span> {node.id}
        </p>
        {onExpandNode ? (
          <button className="ghost-button secondary-button" onClick={() => onExpandNode(node)} type="button">
            Expand related nodes
          </button>
        ) : null}
      </div>
      <div className="inspector-grid">
        {entries.map(([key, value]) => (
          <article key={key} className="inspector-card">
            <span className="inspector-key">{key}</span>
            <span className="inspector-value">{String(value)}</span>
          </article>
        ))}
      </div>
    </section>
  );
}
