export type GraphNode = {
  id: string;
  label: string;
  kind: string;
  title: string;
  degree: number;
  properties: Record<string, unknown>;
};

export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  relation: string;
  properties?: Record<string, unknown>;
};

export type GraphPayload = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  initialNodeIds: string[];
  examples: string[];
};

export type MetaPayload = {
  examples: string[];
  tables: string[];
};

export type ChatPayload = {
  question: string;
  intent: string;
  rationale?: string;
  sql: string;
  answer: string;
  evidence: Record<string, unknown>[];
  highlightNodeIds: string[];
  trace: Array<Record<string, unknown>>;
};
