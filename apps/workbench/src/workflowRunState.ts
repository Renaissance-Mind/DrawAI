export type DagRunNodeState = "waiting" | "running" | "done" | "failed" | "review" | "stale";
export type DagRunEdgeState = "waiting" | "running" | "done";

export function dagRunEdgeState(sourceState: DagRunNodeState, targetState: DagRunNodeState): DagRunEdgeState {
  if (targetState === "running") return "running";
  if (sourceState === "done" && targetState === "done") return "done";
  return "waiting";
}
