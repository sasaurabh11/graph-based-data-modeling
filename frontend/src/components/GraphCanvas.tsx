import { useEffect, useMemo, useRef } from "react";
import cytoscape, { type Core, type EdgeSingular, type ElementDefinition } from "cytoscape";
import type { GraphEdge, GraphNode } from "../types";

type GraphCanvasProps = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  initialNodeIds: string[];
  highlightedNodeIds: string[];
  selectedNodeId: string | null;
  onSelectNode: (node: GraphNode) => void;
};

const kindColor: Record<string, string> = {
  customer: "#ff6b6b",
  address: "#f59e0b",
  plant: "#10b981",
  product: "#38bdf8",
  sales_order: "#8b5cf6",
  sales_order_item: "#a78bfa",
  delivery: "#22c55e",
  delivery_item: "#84cc16",
  billing_document: "#fb7185",
  billing_document_item: "#f97316",
  journal_entry: "#60a5fa",
  payment: "#14b8a6",
};

const kindShape: Record<string, string> = {
  customer: "round-rectangle",
  address: "round-rectangle",
  plant: "ellipse",
  product: "hexagon",
  sales_order: "round-rectangle",
  sales_order_item: "rectangle",
  delivery: "round-rectangle",
  delivery_item: "rectangle",
  billing_document: "round-rectangle",
  billing_document_item: "rectangle",
  journal_entry: "diamond",
  payment: "diamond",
};

const kindLabel: Record<string, string> = {
  customer: "Customer",
  address: "Address",
  plant: "Plant",
  product: "Product",
  sales_order: "Sales Order",
  sales_order_item: "Order Item",
  delivery: "Delivery",
  delivery_item: "Delivery Item",
  billing_document: "Billing Doc",
  billing_document_item: "Billing Item",
  journal_entry: "Journal",
  payment: "Payment",
};

function truncateLabel(label: string): string {
  return label.length > 26 ? `${label.slice(0, 23)}...` : label;
}

function toElements(nodes: GraphNode[], edges: GraphEdge[], visibleNodeIds: Set<string>): ElementDefinition[] {
  const nodeElements = nodes
    .filter((node) => visibleNodeIds.has(node.id))
    .map((node) => ({
      data: {
        id: node.id,
        label: `${kindLabel[node.kind] ?? node.title}\n${truncateLabel(node.label)}`,
        kind: node.kind,
        degree: node.degree,
      },
    }));

  const edgeElements = edges
    .filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target))
    .map((edge) => ({
      data: {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        relation: edge.relation,
      },
    }));

  return [...nodeElements, ...edgeElements];
}

export function GraphCanvas(props: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);

  const nodeMap = useMemo(() => new Map(props.nodes.map((node) => [node.id, node])), [props.nodes]);
  const visibleNodeIds = useMemo(() => new Set(props.initialNodeIds), [props.initialNodeIds]);

  useEffect(() => {
    if (!containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      elements: toElements(props.nodes, props.edges, visibleNodeIds),
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "font-size": 11,
            color: "#e5eefb",
            "text-wrap": "wrap",
            "text-max-width": 140,
            "text-valign": "center",
            "text-halign": "center",
            "text-outline-width": 2,
            "text-outline-color": "#020617",
            "background-color": (ele) => kindColor[ele.data("kind")] || "#94a3b8",
            shape: (ele) => kindShape[ele.data("kind")] || "ellipse",
            width: (ele) => Math.max(40, Math.min(88, 36 + Number(ele.data("degree")) * 0.45)),
            height: (ele) => Math.max(40, Math.min(88, 36 + Number(ele.data("degree")) * 0.45)),
            "border-width": 1.5,
            "border-color": "#0f172a",
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.4,
            "curve-style": "bezier",
            "line-color": "#334155",
            "target-arrow-color": "#334155",
            "target-arrow-shape": "triangle",
            "arrow-scale": 0.8,
            opacity: 0.55,
          },
        },
        {
          selector: ".selected",
          style: {
            "border-color": "#f8fafc",
            "border-width": 3,
            "overlay-opacity": 0,
            "z-compound-depth": "top",
          },
        },
        {
          selector: ".highlighted",
          style: {
            "background-color": "#facc15",
            "line-color": "#facc15",
            "target-arrow-color": "#facc15",
            color: "#111827",
            "text-outline-color": "#fef08a",
            opacity: 1,
          },
        },
        {
          selector: "edge.highlighted",
          style: {
            width: 2.4,
            label: "data(relation)",
            "font-size": 9,
            color: "#f8fafc",
            "text-background-opacity": 1,
            "text-background-color": "#0f172a",
            "text-background-padding": 3,
            "text-rotation": "autorotate",
          },
        },
      ],
      layout: {
        name: "cose",
        animate: false,
        fit: true,
        padding: 30,
        idealEdgeLength: 120,
        nodeRepulsion: 320000,
      },
    });

    cy.on("tap", "node", (event) => {
      const node = nodeMap.get(event.target.id());
      if (!node) return;
      props.onSelectNode(node);
    });

    cyRef.current = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [nodeMap, props.edges, props.nodes, props.onSelectNode, visibleNodeIds]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const nextVisible = new Set(cy.nodes().map((node) => node.id()));
    props.initialNodeIds.forEach((id) => nextVisible.add(id));

    cy.elements().remove();
    cy.add(toElements(props.nodes, props.edges, nextVisible));
    cy.layout({
      name: "cose",
      animate: false,
      fit: true,
      padding: 30,
      idealEdgeLength: 120,
      nodeRepulsion: 320000,
    }).run();
  }, [props.edges, props.initialNodeIds, props.nodes]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().removeClass("highlighted selected");
    cy.edges().removeClass("highlighted");

    props.highlightedNodeIds.forEach((id) => {
      const node = cy.getElementById(id);
      if (node.nonempty()) {
        node.addClass("highlighted");
      }
    });

    if (props.selectedNodeId) {
      const selected = cy.getElementById(props.selectedNodeId);
      if (selected.nonempty()) {
        selected.addClass("selected");
      }
    }

    const highlightedSet = new Set(props.highlightedNodeIds);
    cy.edges().forEach((edge: EdgeSingular) => {
      if (highlightedSet.has(edge.source().id()) && highlightedSet.has(edge.target().id())) {
        edge.addClass("highlighted");
      }
    });
  }, [props.highlightedNodeIds, props.selectedNodeId]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    if (props.highlightedNodeIds.length > 0) {
      const neighborhood = cy.collection(
        props.highlightedNodeIds.flatMap((id) => {
          const node = cy.getElementById(id);
          return node.nonempty() ? [node, ...node.connectedEdges().toArray(), ...node.neighborhood().toArray()] : [];
        }),
      );
      if (neighborhood.nonempty()) {
        cy.fit(neighborhood, 50);
        return;
      }
    }

    if (props.selectedNodeId) {
      const selected = cy.getElementById(props.selectedNodeId);
      if (selected.nonempty()) {
        cy.fit(selected.closedNeighborhood(), 60);
      }
    }
  }, [props.highlightedNodeIds, props.selectedNodeId]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const handleResize = () => cy.resize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return <div className="graph-canvas" ref={containerRef} />;
}
