export type WorkflowNodeRerunActionKind = "restart" | "failed_node";

export type WorkflowNodeRerunAction = {
  kind: WorkflowNodeRerunActionKind;
  stage: string;
  nodeId?: string;
};

export function workflowNodeRerunActions({
  stage,
  nodeId,
  nodeState
}: {
  stage: string;
  nodeId: string;
  nodeState: string;
}): WorkflowNodeRerunAction[] {
  const cleanStage = stage.trim();
  if (!cleanStage) return [];
  const actions: WorkflowNodeRerunAction[] = [{ kind: "restart", stage: cleanStage }];
  const cleanNodeId = nodeId.trim();
  if (nodeState === "failed" && cleanNodeId) {
    actions.push({ kind: "failed_node", stage: cleanStage, nodeId: cleanNodeId });
  }
  return actions;
}
