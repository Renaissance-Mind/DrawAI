import type { WorkflowNodeArtifact, WorkflowNodeViewer } from "./types";

type ArtifactLike = Pick<WorkflowNodeArtifact, "artifact_id" | "exists" | "kind" | "role" | "url">;

export function selectableWorkflowNodeArtifacts<T extends ArtifactLike>(artifacts: T[] | null | undefined): T[] {
  return (artifacts || []).filter((artifact) => artifact.exists && (Boolean(artifact.url) || artifact.kind === "agent_log"));
}

export function defaultWorkflowNodeArtifactId(viewer: Pick<WorkflowNodeViewer, "artifacts" | "primary_artifact_id">): string {
  const artifacts = selectableWorkflowNodeArtifacts(viewer.artifacts);
  return (
    artifacts.find((artifact) => artifact.artifact_id === viewer.primary_artifact_id)?.artifact_id ||
    artifacts.find((artifact) => artifact.kind !== "agent_log" && artifact.role !== "log")?.artifact_id ||
    artifacts[0]?.artifact_id ||
    ""
  );
}
