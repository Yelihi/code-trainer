import type { Assistance } from './api.ts';

export type GraphEvidence = { id: string; root_key: string; root_label: string; framework: boolean; set_id: string | null; context_id: string | null; unit_id: string | null; title: string; kind: string; assistance?: Assistance; withdrawn: boolean; deleted?: boolean };
export type GraphSource = { id: string; title: string; version: number; state: string; note_id: string | null; quote: string; basis?: string; disposition?: 'supports' | 'refutes'; metadata?: { locator?: string } };
export type GraphNode = { added_at?: string; context_id?: string | null; unit_id?: string; source_available?: boolean; id: string; kind: 'concept' | 'foundation' | 'unit' | 'note'; label: string; scope: string; descriptions: string[]; exercise_ids: string[];
  note_id?: string; needs_review?: boolean; ontology_status?: string; aliases?: string[]; sources?: GraphSource[]; claims?: { text: string; scope: string; contested: boolean; sources: GraphSource[] }[] };
export type GraphEdge = { id: string; source: string; target: string; kind: 'evidence' | 'prerequisite' | 'coverage' | 'PREREQUISITE_OF' | 'BROADER_THAN' | 'USED_IN' | 'RELATED_TO'; label: string; description: string; exercise_ids: string[]; sources?: GraphSource[] };
export type KnowledgeGraph = {
  nodes: GraphNode[]; edges: GraphEdge[]; exercises: GraphEvidence[];
  state: 'empty' | 'stale' | 'running' | 'ready' | 'failed'; error: string; ai_available: boolean;
  records: { id: string; created_at: string }[]; record_id: string | null; created_at: string | null; current_passed_count: number;
};
export type Point = { x: number; y: number };
export type ViewBox = Point & { width: number; height: number };

export function neighbors(id: string, edges: GraphEdge[]) {
  return new Set([id, ...edges.flatMap(edge => edge.source === id ? [edge.target] : edge.target === id ? [edge.source] : [])]);
}

export function zoomView(view: ViewBox, factor: number, anchor: Point, base: ViewBox): ViewBox {
  const width = Math.max(base.width / 5, Math.min(base.width * 2, view.width * factor));
  const ratio = width / view.width;
  return { x: anchor.x - (anchor.x - view.x) * ratio, y: anchor.y - (anchor.y - view.y) * ratio,
    width, height: view.height * ratio };
}

export function layoutGraph(nodes: GraphNode[], edges: GraphEdge[]) {
  const links = new Map(nodes.map(node => [node.id, new Set<string>()]));
  for (const edge of edges) {
    if (!links.has(edge.source) || !links.has(edge.target)) continue;
    links.get(edge.source)!.add(edge.target); links.get(edge.target)!.add(edge.source);
  }
  const remaining = new Set([...links.keys()].sort());
  const components: { points: Map<string, Point>; width: number; height: number }[] = [];
  while (remaining.size) {
    const queue = [remaining.values().next().value!];
    remaining.delete(queue[0]);
    for (let i = 0; i < queue.length; i++) for (const next of links.get(queue[i])!) {
      if (remaining.delete(next)) queue.push(next);
    }
    queue.sort((a, b) => links.get(b)!.size - links.get(a)!.size || a.localeCompare(b));
    const points = new Map(queue.map((id, i) => [id, { x: Math.cos(i * 2.4) * 130 * Math.sqrt(i), y: Math.sin(i * 2.4) * 130 * Math.sqrt(i) }]));
    const componentEdges = edges.filter(edge => points.has(edge.source) && points.has(edge.target));
    // Static layout keeps hover and keyboard focus stable; use a worker if measured layout time grows.
    for (let step = 0; step < 70; step++) {
      const shifts = new Map(queue.map(id => [id, { x: 0, y: 0 }]));
      for (let i = 0; i < queue.length; i++) for (let j = i + 1; j < queue.length; j++) {
        const a = points.get(queue[i])!, b = points.get(queue[j])!;
        const dx = a.x - b.x, dy = a.y - b.y, distance = Math.hypot(dx, dy) || 1;
        if (distance > 210) continue;
        const force = (210 - distance) * .09 / distance;
        shifts.get(queue[i])!.x += dx * force; shifts.get(queue[i])!.y += dy * force;
        shifts.get(queue[j])!.x -= dx * force; shifts.get(queue[j])!.y -= dy * force;
      }
      for (const edge of componentEdges) {
        const a = points.get(edge.source)!, b = points.get(edge.target)!;
        const dx = b.x - a.x, dy = b.y - a.y, distance = Math.hypot(dx, dy) || 1;
        const force = (distance - 180) * .025 / distance;
        shifts.get(edge.source)!.x += dx * force; shifts.get(edge.source)!.y += dy * force;
        shifts.get(edge.target)!.x -= dx * force; shifts.get(edge.target)!.y -= dy * force;
      }
      for (const [id, point] of points) {
        const shift = shifts.get(id)!;
        point.x += Math.max(-10, Math.min(10, shift.x)); point.y += Math.max(-10, Math.min(10, shift.y));
      }
    }
    let xs = [...points.values()].map(point => point.x), ys = [...points.values()].map(point => point.y);
    if (Math.max(...ys) - Math.min(...ys) > Math.max(...xs) - Math.min(...xs)) {
      for (const point of points.values()) [point.x, point.y] = [point.y, point.x];
      [xs, ys] = [ys, xs];
    }
    const minX = Math.min(...xs), minY = Math.min(...ys);
    for (const point of points.values()) { point.x += 95 - minX; point.y += 70 - minY; }
    components.push({ points, width: Math.max(...xs) - minX + 190, height: Math.max(...ys) - minY + 160 });
  }
  components.sort((a, b) => b.points.size - a.points.size);
  const rowWidth = Math.max(600, Math.sqrt(components.reduce((sum, item) => sum + item.width * item.height, 0)) * 1.45);
  const positions = new Map<string, Point>();
  const columns: { x: number; width: number; height: number }[] = [];
  let width = 0;
  for (const component of components) {
    let column = columns.filter(item => item.width >= component.width).sort((a, b) => a.height - b.height)[0];
    const availableWidth = Math.max(rowWidth, ...columns.map(item => item.height * 1.8));
    if (!column || width + component.width + 36 <= availableWidth) {
      column = { x: columns.length ? width + 36 : 0, width: component.width, height: 0 };
      columns.push(column); width = column.x + column.width;
    }
    for (const [id, point] of component.points) positions.set(id, { x: column.x + point.x, y: column.height + point.y });
    column.height += component.height + 36;
  }
  return { positions, bounds: { x: -30, y: -30, width: Math.max(400, width + 60), height: Math.max(300, ...columns.map(column => column.height + 24)) } };
}
