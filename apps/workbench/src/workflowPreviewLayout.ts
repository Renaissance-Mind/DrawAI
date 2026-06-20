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

type Point = { x: number; y: number };
type Side = "left" | "right" | "top" | "bottom";
type Rect = { left: number; top: number; right: number; bottom: number };
type EdgeRoute = { points: Point[]; d: string; start: Point; end: Point };
type Segment = { a: Point; b: Point };
type PortSlot = { index: number; total: number };

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
  const edgeSidesById = new Map<string, { startSide: Side; endSide: Side }>();
  const portTotals = new Map<string, number>();
  template.edges.forEach((edge) => {
    const source = byId.get(edge.source_node_id);
    const target = byId.get(edge.target_node_id);
    if (!source || !target) return;
    const sides = edgeSides(source, target);
    edgeSidesById.set(edge.edge_id, sides);
    incrementMap(portTotals, portSlotKey(edge.source_node_id, sides.startSide));
    incrementMap(portTotals, portSlotKey(edge.target_node_id, sides.endSide));
  });
  const portUse = new Map<string, number>();
  const routedSegments: Segment[] = [];
  const edges = template.edges.flatMap((edge) => {
    const source = byId.get(edge.source_node_id);
    const target = byId.get(edge.target_node_id);
    if (!source || !target) return [];
    const sides = edgeSidesById.get(edge.edge_id) || edgeSides(source, target);
    const sourceKey = portSlotKey(edge.source_node_id, sides.startSide);
    const targetKey = portSlotKey(edge.target_node_id, sides.endSide);
    const sourceSlot = nextPortSlot(portUse, sourceKey, portTotals.get(sourceKey) || 1);
    const targetSlot = nextPortSlot(portUse, targetKey, portTotals.get(targetKey) || 1);
    const route = routePreviewEdge(source, target, nodeLayouts, routedSegments, { width, height }, sides, sourceSlot, targetSlot);
    routedSegments.push(...segmentsFromPoints(route.points));
    return [{ edge, start: route.start, end: route.end, d: route.d }];
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

function routePreviewEdge(
  source: WorkflowPreviewNode,
  target: WorkflowPreviewNode,
  nodes: WorkflowPreviewNode[],
  existingSegments: Segment[],
  bounds: { width: number; height: number },
  sides = edgeSides(source, target),
  sourceSlot: PortSlot = { index: 0, total: 1 },
  targetSlot: PortSlot = { index: 0, total: 1 }
): EdgeRoute {
  const clearance = 12;
  const start = anchorPoint(source, sides.startSide, sourceSlot);
  const end = anchorPoint(target, sides.endSide, targetSlot);
  const startOutside = offsetPoint(start, sides.startSide, clearance);
  const endOutside = offsetPoint(end, sides.endSide, clearance);
  const obstacles = nodes.map((node) => expandRect(nodeRect(node), 7));
  const routedMiddle = orthogonalRoute(startOutside, endOutside, obstacles, existingSegments, bounds);
  const points = simplifyPoints([start, startOutside, ...routedMiddle.slice(1, -1), endOutside, end]);
  return { start, end, points, d: pointsToPath(points) };
}

function edgeSides(source: WorkflowPreviewNode, target: WorkflowPreviewNode): { startSide: Side; endSide: Side } {
  const sourceCenter = nodeCenter(source);
  const targetCenter = nodeCenter(target);
  const dx = targetCenter.x - sourceCenter.x;
  const dy = targetCenter.y - sourceCenter.y;
  if (Math.abs(dx) >= Math.abs(dy)) {
    if (dx >= 0) {
      return { startSide: "right", endSide: "left" };
    }
    return { startSide: "left", endSide: "right" };
  }
  if (dy >= 0) {
    return { startSide: "bottom", endSide: "top" };
  }
  return { startSide: "top", endSide: "bottom" };
}

function orthogonalRoute(
  start: Point,
  end: Point,
  obstacles: Rect[],
  existingSegments: Segment[],
  bounds: { width: number; height: number }
): Point[] {
  const xValues = routingAxisValues(start.x, end.x, obstacles, 0, bounds.width, "x");
  const yValues = routingAxisValues(start.y, end.y, obstacles, 0, bounds.height, "y");
  const points: Point[] = [];
  const indexByKey = new Map<string, number>();

  for (const x of xValues) {
    for (const y of yValues) {
      const point = { x, y };
      if (pointInsideAnyRect(point, obstacles)) continue;
      const key = pointKey(point);
      indexByKey.set(key, points.length);
      points.push(point);
    }
  }

  const startIndex = indexByKey.get(pointKey(start));
  const endIndex = indexByKey.get(pointKey(end));
  if (startIndex === undefined || endIndex === undefined) {
    return fallbackRoute(start, end);
  }

  const byX = new Map<number, number[]>();
  const byY = new Map<number, number[]>();
  points.forEach((point, index) => {
    byX.set(point.x, [...(byX.get(point.x) || []), index]);
    byY.set(point.y, [...(byY.get(point.y) || []), index]);
  });
  byX.forEach((indices) => indices.sort((left, right) => points[left].y - points[right].y));
  byY.forEach((indices) => indices.sort((left, right) => points[left].x - points[right].x));

  const neighbors = new Map<number, number[]>();
  const addClearNeighbors = (indices: number[]) => {
    for (let index = 0; index < indices.length - 1; index += 1) {
      const from = indices[index];
      const to = indices[index + 1];
      if (segmentBlocked(points[from], points[to], obstacles)) continue;
      neighbors.set(from, [...(neighbors.get(from) || []), to]);
      neighbors.set(to, [...(neighbors.get(to) || []), from]);
    }
  };
  byX.forEach(addClearNeighbors);
  byY.forEach(addClearNeighbors);

  const route = shortestRoute(points, neighbors, startIndex, endIndex, existingSegments);
  return route ? route.map((index) => points[index]) : fallbackRoute(start, end);
}

function shortestRoute(
  points: Point[],
  neighbors: Map<number, number[]>,
  startIndex: number,
  endIndex: number,
  existingSegments: Segment[]
): number[] | null {
  type Direction = "h" | "v" | "none";
  type QueueItem = { index: number; direction: Direction; cost: number; previousKey: string };
  const startKey = routeStateKey(startIndex, "none");
  const costs = new Map<string, number>([[startKey, 0]]);
  const previous = new Map<string, string>();
  const queue: QueueItem[] = [{ index: startIndex, direction: "none", cost: 0, previousKey: "" }];
  let bestEndKey = "";

  while (queue.length > 0) {
    queue.sort((left, right) => left.cost - right.cost);
    const current = queue.shift();
    if (!current) break;
    const currentKey = routeStateKey(current.index, current.direction);
    if (current.cost !== costs.get(currentKey)) continue;
    if (current.index === endIndex) {
      bestEndKey = currentKey;
      break;
    }
    for (const nextIndex of neighbors.get(current.index) || []) {
      const direction = segmentDirection(points[current.index], points[nextIndex]);
      if (!direction) continue;
      const bendCost = current.direction !== "none" && current.direction !== direction ? 22 : 0;
      const lineCost = pointDistance(points[current.index], points[nextIndex]);
      const reuseCost = segmentReusePenalty(points[current.index], points[nextIndex], existingSegments);
      const nextCost = current.cost + lineCost + bendCost + reuseCost;
      const nextKey = routeStateKey(nextIndex, direction);
      if (nextCost >= (costs.get(nextKey) ?? Number.POSITIVE_INFINITY)) continue;
      costs.set(nextKey, nextCost);
      previous.set(nextKey, currentKey);
      queue.push({ index: nextIndex, direction, cost: nextCost, previousKey: currentKey });
    }
  }

  if (!bestEndKey) return null;
  const route: number[] = [];
  let currentKey = bestEndKey;
  while (currentKey) {
    route.push(Number(currentKey.split(":")[0]));
    currentKey = previous.get(currentKey) || "";
  }
  route.reverse();
  return route[0] === startIndex ? route : null;
}

function routingAxisValues(
  start: number,
  end: number,
  obstacles: Rect[],
  min: number,
  max: number,
  axis: "x" | "y"
): number[] {
  const values = new Set<number>([roundPointValue(start), roundPointValue(end), clampRouteValue(min + 6, min, max), clampRouteValue(max - 6, min, max)]);
  const rectStarts = obstacles.map((rect) => axis === "x" ? rect.left : rect.top).sort((a, b) => a - b);
  const rectEnds = obstacles.map((rect) => axis === "x" ? rect.right : rect.bottom).sort((a, b) => a - b);
  obstacles.forEach((rect) => {
    const before = axis === "x" ? rect.left - 8 : rect.top - 8;
    const after = axis === "x" ? rect.right + 8 : rect.bottom + 8;
    values.add(clampRouteValue(before, min, max));
    values.add(clampRouteValue(after, min, max));
  });
  for (let index = 0; index < Math.min(rectStarts.length, rectEnds.length) - 1; index += 1) {
    const gapStart = rectEnds[index];
    const gapEnd = rectStarts[index + 1];
    if (gapEnd - gapStart > 18) values.add(clampRouteValue((gapStart + gapEnd) / 2, min, max));
  }
  return Array.from(values).sort((a, b) => a - b);
}

function fallbackRoute(start: Point, end: Point): Point[] {
  const midX = (start.x + end.x) / 2;
  const midY = (start.y + end.y) / 2;
  return Math.abs(end.x - start.x) >= Math.abs(end.y - start.y)
    ? [start, { x: midX, y: start.y }, { x: midX, y: end.y }, end]
    : [start, { x: start.x, y: midY }, { x: end.x, y: midY }, end];
}

function anchorPoint(node: WorkflowPreviewNode, side: Side, slot: PortSlot = { index: 0, total: 1 }): Point {
  const center = nodeCenter(node);
  const offset = portSlotOffset(node, side, slot);
  if (side === "left") return { x: node.x, y: center.y + offset };
  if (side === "right") return { x: node.x + node.width, y: center.y + offset };
  if (side === "top") return { x: center.x + offset, y: node.y };
  return { x: center.x + offset, y: node.y + node.height };
}

function portSlotOffset(node: WorkflowPreviewNode, side: Side, slot: PortSlot): number {
  if (slot.total <= 1) return 0;
  const span = (side === "left" || side === "right" ? node.height : node.width) * 0.58;
  const step = Math.min(16, span / Math.max(1, slot.total - 1));
  return (slot.index - (slot.total - 1) / 2) * step;
}

function nextPortSlot(used: Map<string, number>, key: string, total: number): PortSlot {
  const index = used.get(key) || 0;
  used.set(key, index + 1);
  return { index, total };
}

function portSlotKey(nodeId: string, side: Side): string {
  return `${nodeId}:${side}`;
}

function incrementMap(map: Map<string, number>, key: string) {
  map.set(key, (map.get(key) || 0) + 1);
}

function offsetPoint(point: Point, side: Side, amount: number): Point {
  if (side === "left") return { x: point.x - amount, y: point.y };
  if (side === "right") return { x: point.x + amount, y: point.y };
  if (side === "top") return { x: point.x, y: point.y - amount };
  return { x: point.x, y: point.y + amount };
}

function nodeCenter(node: WorkflowPreviewNode): Point {
  return { x: node.x + node.width / 2, y: node.y + node.height / 2 };
}

function nodeRect(node: WorkflowPreviewNode): Rect {
  return { left: node.x, top: node.y, right: node.x + node.width, bottom: node.y + node.height };
}

function expandRect(rect: Rect, amount: number): Rect {
  return { left: rect.left - amount, top: rect.top - amount, right: rect.right + amount, bottom: rect.bottom + amount };
}

function pointInsideAnyRect(point: Point, rects: Rect[]): boolean {
  return rects.some((rect) => point.x > rect.left && point.x < rect.right && point.y > rect.top && point.y < rect.bottom);
}

function segmentBlocked(a: Point, b: Point, rects: Rect[]): boolean {
  if (samePoint(a, b)) return false;
  return rects.some((rect) => segmentIntersectsRect(a, b, rect));
}

function segmentIntersectsRect(a: Point, b: Point, rect: Rect): boolean {
  const minX = Math.min(a.x, b.x);
  const maxX = Math.max(a.x, b.x);
  const minY = Math.min(a.y, b.y);
  const maxY = Math.max(a.y, b.y);
  if (sameValue(a.y, b.y)) {
    return a.y > rect.top && a.y < rect.bottom && maxX > rect.left && minX < rect.right;
  }
  if (sameValue(a.x, b.x)) {
    return a.x > rect.left && a.x < rect.right && maxY > rect.top && minY < rect.bottom;
  }
  return false;
}

function segmentReusePenalty(a: Point, b: Point, existingSegments: Segment[]): number {
  return existingSegments.reduce((penalty, segment) => {
    const overlap = collinearOverlapLength(a, b, segment.a, segment.b);
    if (overlap > 2) return penalty + 140 + overlap * 0.8;
    if (segmentsCrossInside(a, b, segment.a, segment.b)) return penalty + 120;
    return penalty;
  }, 0);
}

function collinearOverlapLength(a: Point, b: Point, c: Point, d: Point): number {
  if (sameValue(a.y, b.y) && sameValue(c.y, d.y) && Math.abs(a.y - c.y) < 1.5) {
    return rangeOverlapLength(a.x, b.x, c.x, d.x);
  }
  if (sameValue(a.x, b.x) && sameValue(c.x, d.x) && Math.abs(a.x - c.x) < 1.5) {
    return rangeOverlapLength(a.y, b.y, c.y, d.y);
  }
  return 0;
}

function segmentsCrossInside(a: Point, b: Point, c: Point, d: Point): boolean {
  const abHorizontal = sameValue(a.y, b.y);
  const cdHorizontal = sameValue(c.y, d.y);
  if (abHorizontal === cdHorizontal) return false;
  const horizontalA = abHorizontal ? a : c;
  const horizontalB = abHorizontal ? b : d;
  const verticalA = abHorizontal ? c : a;
  const verticalB = abHorizontal ? d : b;
  const cross = { x: verticalA.x, y: horizontalA.y };
  if (!valueBetween(cross.x, horizontalA.x, horizontalB.x) || !valueBetween(cross.y, verticalA.y, verticalB.y)) return false;
  return ![a, b, c, d].some((point) => samePoint(point, cross));
}

function rangeOverlapLength(a: number, b: number, c: number, d: number): number {
  const left = Math.max(Math.min(a, b), Math.min(c, d));
  const right = Math.min(Math.max(a, b), Math.max(c, d));
  return Math.max(0, right - left);
}

function valueBetween(value: number, a: number, b: number): boolean {
  return value > Math.min(a, b) + 0.1 && value < Math.max(a, b) - 0.1;
}

function pointDistance(a: Point, b: Point): number {
  return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
}

function segmentDirection(a: Point, b: Point): "h" | "v" | null {
  if (sameValue(a.y, b.y) && !sameValue(a.x, b.x)) return "h";
  if (sameValue(a.x, b.x) && !sameValue(a.y, b.y)) return "v";
  return null;
}

function simplifyPoints(points: Point[]): Point[] {
  const deduped = points.filter((point, index) => index === 0 || !samePoint(point, points[index - 1]));
  const simplified: Point[] = [];
  for (const point of deduped) {
    simplified.push(point);
    while (simplified.length >= 3) {
      const a = simplified[simplified.length - 3];
      const b = simplified[simplified.length - 2];
      const c = simplified[simplified.length - 1];
      if ((sameValue(a.x, b.x) && sameValue(b.x, c.x)) || (sameValue(a.y, b.y) && sameValue(b.y, c.y))) {
        simplified.splice(simplified.length - 2, 1);
      } else {
        break;
      }
    }
  }
  return simplified;
}

function segmentsFromPoints(points: Point[]): Segment[] {
  const segments: Segment[] = [];
  for (let index = 0; index < points.length - 1; index += 1) {
    if (!samePoint(points[index], points[index + 1])) segments.push({ a: points[index], b: points[index + 1] });
  }
  return segments;
}

function pointsToPath(points: Point[]): string {
  const [first, ...rest] = points;
  if (!first) return "";
  return [`M ${formatRouteNumber(first.x)} ${formatRouteNumber(first.y)}`, ...rest.map((point) => `L ${formatRouteNumber(point.x)} ${formatRouteNumber(point.y)}`)].join(" ");
}

function routeStateKey(index: number, direction: "h" | "v" | "none"): string {
  return `${index}:${direction}`;
}

function pointKey(point: Point): string {
  return `${roundPointValue(point.x)},${roundPointValue(point.y)}`;
}

function roundPointValue(value: number): number {
  return Number(value.toFixed(2));
}

function formatRouteNumber(value: number): string {
  return String(Number(value.toFixed(1)));
}

function clampRouteValue(value: number, min: number, max: number): number {
  return roundPointValue(Math.max(min, Math.min(max, value)));
}

function sameValue(left: number, right: number): boolean {
  return Math.abs(left - right) < 0.01;
}

function samePoint(left: Point, right: Point): boolean {
  return sameValue(left.x, right.x) && sameValue(left.y, right.y);
}
