import type { CaseRecord, WorkflowNodeMetadata, WorkflowNodeRunRecord } from "./types";
import type { WorkflowNode } from "./workflowTypes";

export interface WorkflowNodeInfoRow {
  label: string;
  value: string;
}

export function dagRunCaseIdentifier(caseRecord: Pick<CaseRecord, "case_id" | "name">): string {
  return String(caseRecord.case_id || caseRecord.name || "").trim();
}

export function latestWorkflowNodeRunForNode(
  runs: WorkflowNodeRunRecord[],
  nodeId: string
): WorkflowNodeRunRecord | null {
  const matching = runs.filter((run) => run.node_id === nodeId);
  if (matching.length === 0) return null;
  return matching[matching.length - 1] || null;
}

export function workflowNodeExtraInfoRows({
  node,
  nodeRun,
  metadata
}: {
  node: WorkflowNode;
  nodeRun?: Partial<WorkflowNodeRunRecord> | null;
  metadata?: Partial<WorkflowNodeMetadata> | null;
}): WorkflowNodeInfoRow[] {
  const rows: WorkflowNodeInfoRow[] = [];
  const providerId = clean(nodeRun?.provider_id) || clean(metadata?.provider_id) || clean(node.config.provider_id);
  const providerLabel = clean(nodeRun?.provider_label) || clean(metadata?.provider_label) || fallbackProviderLabel(providerId);
  if (providerLabel) {
    rows.push({ label: "Agent", value: providerLabel });
  }
  if (providerId && providerId !== providerLabel) {
    rows.push({ label: "Provider ID", value: providerId });
  }
  const model = clean(metadata?.model) || clean(node.config.model) || clean(node.config.model_name);
  if (model) {
    rows.push({ label: "Model", value: model });
  }
  const processorTypes = (metadata?.processor_types || [])
    .map(clean)
    .filter((value, index, values) => value && values.indexOf(value) === index);
  if (processorTypes.length > 0) {
    rows.push({ label: "Classification Processors", value: processorTypes.join(", ") });
  }
  const apiPresetLabels = (metadata?.api_presets || [])
    .map((preset) => clean(preset.api_preset_label) || clean(preset.api_preset_id))
    .filter((value, index, values) => value && values.indexOf(value) === index);
  if (apiPresetLabels.length > 0) {
    rows.push({ label: "API Preset", value: apiPresetLabels.join(", ") });
  }
  return rows;
}

function clean(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function fallbackProviderLabel(providerId: string): string {
  if (!providerId) return "";
  return providerId
    .split("_")
    .filter(Boolean)
    .map((part) => part.slice(0, 1).toUpperCase() + part.slice(1))
    .join(" ");
}
