import type { ChatPayload, GraphPayload, MetaPayload } from "./types";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Request failed");
  }
  return payload as T;
}

export function getGraph() {
  return request<GraphPayload>("/api/graph");
}

export function getMeta() {
  return request<MetaPayload>("/api/meta");
}

export function getNeighbors(nodeId: string) {
  return request<Pick<GraphPayload, "nodes" | "edges">>(`/api/graph/neighbors/${encodeURIComponent(nodeId)}`);
}

export function askQuestion(question: string) {
  return request<ChatPayload>("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
}
