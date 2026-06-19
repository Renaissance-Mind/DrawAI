import type { WorkflowEdge, WorkflowNode, WorkflowTemplate } from "./workflowTypes";

export type WorkflowPreviewNode = {
  node: WorkflowNode;
  x: number;
  y: number;
  width: number;
  height: number;
};

export type WorkflowPreviewEdge = {
  edge: WorkflowEdge;
  d: string;
  start: { x: number; y: number };
  end: { x: number; y: number };
};

export type WorkflowPreviewLayout = {
  width: number;
  height: number;
  nodes: WorkflowPreviewNode[];
  edges: WorkflowPreviewEdge[];
};

type WorkflowPreviewLayoutOptions = {
  maxColumns?: number;
  nodeWidth?: number;
  nodeHeight?: number;
  columnGap?: number;
  rowGap?: number;
  nodeGap?: number;
  paddingX?: number;
  paddingY?: number;
};

const DEFAULT_LAYOUT_OPTIONS = {
  maxColumns: 4,
  nodeWidth: 138,
  nodeHeight: 62,
  columnGap: 52,
  rowGap: 86,
  nodeGap: 24,
  paddingX: 28,
  paddingY: 28
};

export function buildWorkflowPreviewLayout(
  template: WorkflowTemplate,
  options: WorkflowPreviewLayoutOptions = {}
): WorkflowPreviewLayout {
  const settings = { ...DEFAULT_LAYOUT_OPTIONS, ...options };
  const ranks = workflowRanks(template.nodes, template.edges);
  const grouped = groupNodesByRank(template.nodes, ranks);
  const rankValues = Array.from(grouped.keys()).sort((a, b) => a - b);
  const rankToRow = new Map<number, number>();
  const rows: number[][] = [];

  rankValues.forEach((rank) => {
    const row = Math.floor(rank / settings.maxColumns);
    rankToRow.set(rank, row);
    if (!rows[row]) rows[row] = [];
    rows[row].push(rank);
  });

  const rowHeights = rows.map((rowRanks) =>
    Math.max(
      settings.nodeHeight,
      ...rowRanks.map((rank) => {
        const count = grouped.get(rank)?.length || 1;
        return count * settings.nodeHeight + (count - 1) * settings.nodeGap;
      })
    )
  );
  const usedColumns = Math.min(settings.maxColumns, Math.max(1, ...rows.map((row) => row.length)));
  const width = settings.paddingX * 2 + usedColumns * settings.nodeWidth + Math.max(0, usedColumns - 1) * settings.columnGap;
  const height = settings.paddingY * 2 + rowHeights.reduce((sum, item) => sum + item, 0) + Math.max(0, rows.length - 1) * settings.rowGap;
  const nodeLayouts: WorkflowPreviewNode[] = [];

  rankValues.forEach((rank) => {
    const nodes = grouped.get(rank) || [];
    const row = rankToRow.get(rank) || 0;
    const rowRanks = rows[row] || [];
    const rankIndexInRow = rowRanks.indexOf(rank);
    const rowColumn = row % 2 === 0 ? rankIndexInRow : rowRanks.length - 1 - rankIndexInRow;
    const x = settings.paddingX + rowColumn * (settings.nodeWidth + settings.columnGap);
    const rowTop =
      settings.paddingY +
      rowHeights.slice(0, row).reduce((sum, item) => sum + item, 0) +
      row * settings.rowGap;
    const stackHeight = nodes.length * settings.nodeHeight + Math.max(0, nodes.length - 1) * settings.nodeGap;
    const stackTop = rowTop + Math.max(0, (rowHeights[row] - stackHeight) / 2);

    nodes.forEach((node, index) => {
      nodeLayouts.push({
        node,
        x,
        y: stackTop + index * (settings.nodeHeight + settings.nodeGap),
        width: settings.nodeWidth,
        height: settings.nodeHeight
      });
    });
  });

  const byId = new Map(nodeLayouts.map((node) => [node.node.node_id, node]));
  const edges = template.edges.flatMap((edge) => {
    const source = byId.get(edge.source_node_id);
    const target = byId.get(edge.target_node_id);
    if (!source || !target) return [];
    const anchors = edgeAnchors(source, target);
    return [{ edge, ...anchors, d: edgePath(anchors.start, anchors.end) }];
  });

  return { width, height, nodes: nodeLayouts, edges };
}

function workflowRanks(nodes: WorkflowNode[], edges: WorkflowEdge[]): Map<string, number> {
  const nodeIds = new Set(nodes.map((node) => node.node_id));
  const incoming = new Map<string, number>();
  const outgoing = new Map<string, WorkflowEdge[]>();
  nodes.forEach((node) => {
    incoming.set(node.node_id, 0);
    outgoing.set(node.node_id, []);
  });
  edges.forEach((edge) => {
    if (!nodeIds.has(edge.source_node_id) || !nodeIds.has(edge.target_node_id)) return;
    incoming.set(edge.target_node_id, (incoming.get(edge.target_node_id) || 0) + 1);
    outgoing.get(edge.source_node_id)?.push(edge);
  });

  const ranks = new Map<string, number>();
  const queue = nodes.filter((node) => (incoming.get(node.node_id) || 0) === 0).map((node) => node.node_id);
  if (queue.length === 0 && nodes[0]) queue.push(nodes[0].node_id);
  queue.forEach((id) => ranks.set(id, 0));

  for (let index = 0; index < queue.length; index += 1) {
    const sourceId = queue[index];
    const sourceRank = ranks.get(sourceId) || 0;
    for (const edge of outgoing.get(sourceId) || []) {
      ranks.set(edge.target_node_id, Math.max(ranks.get(edge.target_node_id) || 0, sourceRank + 1));
      incoming.set(edge.target_node_id, Math.max(0, (incoming.get(edge.target_node_id) || 0) - 1));
      if ((incoming.get(edge.target_node_id) || 0) === 0) queue.push(edge.target_node_id);
    }
  }

  nodes.forEach((node, index) => {
    if (!ranks.has(node.node_id)) ranks.set(node.node_id, index);
  });
  return ranks;
}

function groupNodesByRank(nodes: WorkflowNode[], ranks: Map<string, number>): Map<number, WorkflowNode[]> {
  const grouped = new Map<number, WorkflowNode[]>();
  nodes.forEach((node, index) => {
    const rank = ranks.get(node.node_id) ?? index;
    const group = grouped.get(rank) || [];
    group.push(node);
    grouped.set(rank, group);
  });
  grouped.forEach((group) => {
    group.sort((a, b) => nodeSortKey(a).localeCompare(nodeSortKey(b)));
  });
  return grouped;
}

function nodeSortKey(node: WorkflowNode): string {
  const priority: Record<string, string> = {
    input: "00",
    parser: "10",
    fusion: "20",
    agent: "30",
    processor: "40",
    human_review: "50",
    export: "60",
    output: "70"
  };
  return `${priority[node.node_type] || "90"}-${node.node_id}`;
}

function edgeAnchors(source: WorkflowPreviewNode, target: WorkflowPreviewNode): { start: { x: number; y: number }; end: { x: number; y: number } } {
  const sourceCenter = { x: source.x + source.width / 2, y: source.y + source.height / 2 };
  const targetCenter = { x: target.x + target.width / 2, y: target.y + target.height / 2 };
  const dx = targetCenter.x - sourceCenter.x;
  const dy = targetCenter.y - sourceCenter.y;
  if (Math.abs(dx) >= Math.abs(dy)) {
    if (dx >= 0) {
      return {
        start: { x: source.x + source.width, y: sourceCenter.y },
        end: { x: target.x, y: targetCenter.y }
      };
    }
    return {
      start: { x: source.x, y: sourceCenter.y },
      end: { x: target.x + target.width, y: targetCenter.y }
    };
  }
  if (dy >= 0) {
    return {
      start: { x: sourceCenter.x, y: source.y + source.height },
      end: { x: targetCenter.x, y: target.y }
    };
  }
  return {
    start: { x: sourceCenter.x, y: source.y },
    end: { x: targetCenter.x, y: target.y + target.height }
  };
}

function edgePath(start: { x: number; y: number }, end: { x: number; y: number }): string {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  if (Math.abs(dx) >= Math.abs(dy)) {
    const direction = dx >= 0 ? 1 : -1;
    const offset = Math.max(28, Math.abs(dx) * 0.42);
    return `M ${start.x} ${start.y} C ${start.x + direction * offset} ${start.y}, ${end.x - direction * offset} ${end.y}, ${end.x} ${end.y}`;
  }
  const direction = dy >= 0 ? 1 : -1;
  const offset = Math.max(28, Math.abs(dy) * 0.42);
  return `M ${start.x} ${start.y} C ${start.x} ${start.y + direction * offset}, ${end.x} ${end.y - direction * offset}, ${end.x} ${end.y}`;
}
