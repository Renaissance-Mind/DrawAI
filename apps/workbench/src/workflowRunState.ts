import type { ArtifactRecord, CaseProgressFile, CaseRecord, StageRunRecord, WorkflowNodeRunRecord } from "./types";
import type { WorkflowNode } from "./workflowTypes";

export type DagRunNodeState = "waiting" | "running" | "done" | "failed" | "review" | "stale" | "breakpoint";
export type DagRunEdgeState = "waiting" | "running" | "done" | "failed" | "breakpoint";

export type WorkflowStageRuntimeState = {
  stage: string;
  state: DagRunNodeState;
  meta: string;
  error: string;
};

type WorkflowStageSpec = {
  stage: string;
  title: string;
  detail: string;
  description: string;
};

const PIPELINE_STAGE_ORDER = [
  "prepare",
  "parse_elements",
  "fuse_elements",
  "refine_elements",
  "plan_assets",
  "process_assets",
  "compose_svg",
  "export",
  "package_run"
] as const;

export function dagRunEdgeState(sourceState: DagRunNodeState, targetState: DagRunNodeState): DagRunEdgeState {
  if (sourceState === "failed" || targetState === "failed") return "failed";
  if (sourceState === "breakpoint" || targetState === "breakpoint") return "breakpoint";
  if (targetState === "running") return "running";
  if (sourceState === "done" && targetState === "done") return "done";
  return "waiting";
}

export function errorDetailText(value: string): string {
  return value;
}

export function currentCaseRecord(detailCase: CaseRecord, progressCase?: CaseRecord | null): CaseRecord {
  if (!progressCase || progressCase.case_id !== detailCase.case_id) return detailCase;
  if (
    detailCase.status === "failed" &&
    Boolean(detailCase.error_message) &&
    (progressCase.status === "queued" || progressCase.status === "analysis_running" || progressCase.status === "svg_running")
  ) {
    return {
      ...detailCase,
      ...progressCase,
      status: "failed",
      phase: detailCase.phase,
      stage: detailCase.stage,
      error_message: detailCase.error_message,
      stale_from_stage: detailCase.stale_from_stage
    };
  }
  return { ...detailCase, ...progressCase };
}

export function mergedStageRuns(progressStageRuns: unknown, detailStageRuns: unknown): StageRunRecord[] {
  const byId = new Map<string, StageRunRecord>();
  for (const run of [...stageRunList(detailStageRuns), ...stageRunList(progressStageRuns)]) {
    const key = run.stage_run_id || `${run.case_id}:${run.stage_name}:${run.attempt}:${run.started_at}`;
    const previous = byId.get(key);
    byId.set(key, previous ? { ...previous, ...run } : run);
  }
  return [...byId.values()].sort(compareStageRunRecency);
}

export function stageRunList(stageRuns: unknown): StageRunRecord[] {
  return Array.isArray(stageRuns) ? stageRuns : [];
}

export function latestStageRun(stageRuns: StageRunRecord[], predicate: (stage: StageRunRecord) => boolean = () => true): StageRunRecord | null {
  const matches = stageRunList(stageRuns).filter(predicate).sort(compareStageRunRecency);
  return matches[matches.length - 1] || null;
}

export function workflowStageState(
  stage: string,
  current: CaseRecord,
  stageRuns: StageRunRecord[],
  files: CaseProgressFile[],
  artifacts: ArtifactRecord[]
): WorkflowStageRuntimeState {
  return workflowStageSpecState({ stage, title: stage, detail: stage, description: "" }, current, stageRuns, files, artifacts);
}

export function workflowStageSpecState(
  spec: WorkflowStageSpec,
  current: CaseRecord,
  stageRuns: StageRunRecord[],
  files: CaseProgressFile[],
  artifacts: ArtifactRecord[]
): WorkflowStageRuntimeState {
  const latest = latestStageRun(stageRuns, (stageRun) => stageMatchesNode(stageRun.stage_name, spec.stage));
  if (current.status === "failed" && stageMatchesNode(current.stage, spec.stage)) {
    return { stage: spec.stage, state: "failed", meta: "失败", error: current.error_message };
  }
  if (current.status === "failed" && latest?.status === "running") {
    return { stage: spec.stage, state: "failed", meta: "失败", error: current.error_message };
  }
  if (isCurrentRunningStage(current, spec.stage)) {
    return { stage: spec.stage, state: "running", meta: "正在运行", error: "" };
  }
  let state: DagRunNodeState = "waiting";
  let meta: string = spec.detail;
  let error = "";

  if (spec.stage === "plan_assets") {
    const planned = artifactOrFileReady(["asset_manifest", "approved_asset_plan", "asset_draft"], files, artifacts);
    if (
      planned ||
      current.stage === "process_assets" ||
      current.stage === "compose_svg" ||
      current.stage === "export" ||
      current.stage === "completed" ||
      current.status === "completed"
    ) {
      state = "done";
      meta = planned ? "资产计划已写入" : "已计划";
    } else if (current.status === "assets_review") {
      state = "review";
      meta = "等待资产确认";
    }
  } else if (spec.stage === "process_assets") {
    const planned = artifactOrFileReady(["asset_manifest", "approved_asset_plan"], files, artifacts);
    if (!planned) {
      meta = "等待资产计划";
    } else if (latest) {
      if (latest.status === "ok") {
        state = "done";
        meta = durationText(latest.started_at, latest.ended_at);
      } else if (latest.status === "running") {
        state = "running";
        meta = durationText(latest.started_at, "");
      } else if (latest.status === "failed") {
        state = "failed";
        meta = "失败";
        error = latest.error_message;
      }
    } else if (current.stage === "compose_svg" || current.stage === "export" || current.status === "completed") {
      state = "done";
      meta = "素材已处理";
    } else if (stageMatchesNode(current.stage, spec.stage)) {
      if (current.status === "failed") {
        state = "failed";
        meta = "失败";
        error = current.error_message;
      } else if (current.status === "analysis_running" || current.status === "svg_running") {
        state = "running";
        meta = "正在运行";
      }
    }
  } else if (latest) {
    if (latest.status === "ok") {
      state = "done";
      meta = durationText(latest.started_at, latest.ended_at);
    } else if (latest.status === "running") {
      state = "running";
      meta = durationText(latest.started_at, "");
    } else if (latest.status === "failed") {
      state = "failed";
      meta = "失败";
      error = latest.error_message;
    }
  } else if (artifactOrFileReady(stageReadyLabels(spec.stage), files, artifacts)) {
    state = "done";
    meta = "输出文件已准备";
  } else if (current.status === "completed") {
    state = "done";
    meta = "已完成";
  } else if (stageMatchesNode(current.stage, spec.stage)) {
    if (current.status === "failed") {
      state = "failed";
      meta = "失败";
      error = current.error_message;
    } else if (current.status === "analysis_running" || current.status === "svg_running") {
      state = "running";
      meta = "正在运行";
    }
  }

  if (state === "done" && isStaleStage(current.stale_from_stage, spec.stage)) {
    state = "stale";
    meta = "需重新运行";
  }

  return {
    stage: spec.stage,
    state,
    meta,
    error
  };
}

export function workflowNodeRuntimeState(
  node: WorkflowNode,
  current: CaseRecord,
  stageRuns: StageRunRecord[],
  nodeRuns: WorkflowNodeRunRecord[],
  files: CaseProgressFile[],
  artifacts: ArtifactRecord[]
): WorkflowStageRuntimeState {
  const stage = workflowStageForNode(node);
  const latestNodeRun = latestWorkflowNodeRun(nodeRuns, node.node_id);
  if (current.status === "failed" && stage && stageMatchesNode(current.stage, stage)) {
    return { state: "failed", stage, meta: "失败", error: current.error_message };
  }
  if (current.status === "failed" && latestNodeRun?.status === "running") {
    return { state: "failed", stage, meta: "失败", error: current.error_message };
  }
  if (current.workflow_breakpoint_node_id === node.node_id) {
    return { state: "breakpoint", stage, meta: current.status === "assets_review" && current.stage === node.node_id ? "断点暂停" : "已设置断点", error: "" };
  }
  if (latestNodeRun) {
    if (latestNodeRun.status === "ok") {
      return { state: "done", stage, meta: durationText(latestNodeRun.started_at, latestNodeRun.ended_at), error: "" };
    }
    if (latestNodeRun.status === "running") {
      return { state: "running", stage, meta: durationText(latestNodeRun.started_at, ""), error: "" };
    }
    if (latestNodeRun.status === "failed") {
      return { state: "failed", stage, meta: "失败", error: latestNodeRun.error_message };
    }
    if (latestNodeRun.status === "blocked") {
      return { state: "failed", stage, meta: "阻塞", error: latestNodeRun.error_message };
    }
  }
  if (node.node_type === "human_review") {
    if (current.status === "assets_review") {
      return { stage, state: "review", meta: "等待人工确认", error: "" };
    }
    if (
      current.status === "completed" ||
      stageIsAfterOrEqual(current.stage, "compose_svg") ||
      artifactOrFileReady(["approved_asset_plan", "semantic_svg", "pptx"], files, artifacts)
    ) {
      return { stage, state: "done", meta: "人工确认已完成或下游已解锁", error: "" };
    }
    if (current.status === "failed" && stageIsAfterOrEqual(current.stage, "plan_assets")) {
      return { stage, state: "failed", meta: "失败", error: current.error_message };
    }
    return { stage, state: "waiting", meta: "等待上游资产处理", error: "" };
  }

  if (node.node_type === "output") {
    if (current.status === "completed" || artifactOrFileReady(["semantic_svg", "pptx", "pptx_export_report"], files, artifacts)) {
      return { stage, state: "done", meta: "输出文件已准备", error: "" };
    }
    if (current.status === "failed" && stageIsAfterOrEqual(current.stage, "export")) {
      return { stage, state: "failed", meta: "失败", error: current.error_message };
    }
    return { stage, state: "waiting", meta: "等待 SVG / PPT 输出", error: "" };
  }

  if (!stage) {
    return {
      stage: "",
      state: current.status === "completed" ? "done" : "waiting",
      meta: node.description || "Workflow node",
      error: ""
    };
  }

  return workflowStageSpecState(
    {
      stage,
      title: node.title,
      detail: node.node_type,
      description: node.description
    },
    current,
    stageRuns,
    files,
    artifacts
  );
}

export function workflowStageForNode(node: WorkflowNode): string {
  const configuredStage = typeof node.config.stage === "string" ? node.config.stage : "";
  if (configuredStage) return configuredStage;
  if (node.node_type === "input") return "prepare";
  if (node.node_type === "parser") return "parse_elements";
  if (node.node_type === "fusion") return "fuse_elements";
  if (node.node_type === "human_review") return "asset_confirm";
  if (node.node_type === "export") return "export";
  if (node.node_type === "output") return "output";
  if (node.node_type === "processor") {
    const processorId = String(node.config.processor_id || "");
    if (processorId === "sam_parse") return "sam_parse";
    if (processorId === "ocr_parse") return "ocr_parse";
    if (processorId === "page_spec_fuse") return "fuse_elements";
    if (processorId === "page_spec_refine") return "refine_elements";
    if (processorId === "asset_prepare") return "process_assets";
    if (processorId === "svg_compose") return "compose_svg";
    if (processorId === "asset_planner") return "plan_assets";
    return "process_assets";
  }
  if (node.node_type === "agent" || node.node_type === "llm") {
    const presetId = String(node.config.preset_id || "");
    if (presetId === "svg_generation") return "compose_svg";
    return "refine_elements";
  }
  return "";
}

export function stageMatchesNode(stageName: string, nodeStage: string): boolean {
  return canonicalPipelineStage(stageName) === canonicalPipelineStage(nodeStage);
}

export function canonicalPipelineStage(stage: string): (typeof PIPELINE_STAGE_ORDER)[number] | "" {
  const aliases: Record<string, (typeof PIPELINE_STAGE_ORDER)[number]> = {
    analysis: "prepare",
    detect_structure: "parse_elements",
    detect_text: "parse_elements",
    assemble_boxir: "fuse_elements",
    asset_analyze: "refine_elements",
    asset_plan: "plan_assets",
    asset_confirm: "plan_assets",
    approved_asset_plan: "plan_assets",
    materialize: "process_assets",
    asset_materialize: "process_assets",
    asset_processing: "process_assets",
    svg: "compose_svg",
    compose: "compose_svg",
    svg_edit: "compose_svg",
    output: "package_run",
    package: "package_run"
  };
  if ((PIPELINE_STAGE_ORDER as readonly string[]).includes(stage)) {
    return stage as (typeof PIPELINE_STAGE_ORDER)[number];
  }
  return aliases[stage] || "";
}

export function stageIsAfterOrEqual(currentStage: string, targetStage: string): boolean {
  const current = canonicalPipelineStage(currentStage);
  const target = canonicalPipelineStage(targetStage);
  if (!current || !target) return false;
  return PIPELINE_STAGE_ORDER.indexOf(current) >= PIPELINE_STAGE_ORDER.indexOf(target);
}

export function artifactOrFileReady(labels: string[], files: CaseProgressFile[], artifacts: ArtifactRecord[]): boolean {
  return labels.some(
    (label) => files.some((file) => file.label === label && file.exists) || artifacts.some((artifact) => artifact.label === label)
  );
}

function stageReadyLabels(stage: string): string[] {
  if (stage === "prepare") return ["figure"];
  if (stage === "sam_parse") return ["sam_page_spec", "raw_regions", "sam_boxes_by_prompt"];
  if (stage === "ocr_parse") return ["ocr_page_spec", "ocr_boxes"];
  if (stage === "parse_elements") return ["raw_regions", "ocr_boxes", "parser_outputs"];
  if (stage === "fuse_elements") return ["box_ir", "fusion_trace"];
  if (stage === "refine_elements") return ["element_analysis", "refine_trace", "asset_draft"];
  if (stage === "plan_assets") return ["asset_manifest", "approved_asset_plan"];
  if (stage === "process_assets") return ["processor_trace"];
  if (stage === "compose_svg") return ["semantic_svg", "rendered_png", "svg_validation_report"];
  if (stage === "export") return ["pptx", "pptx_export_report"];
  return [];
}

function isStaleStage(staleFromStage: string, stage: string): boolean {
  if (!staleFromStage) return false;
  const stageOrder = PIPELINE_STAGE_ORDER as readonly string[];
  const staleIndex = stageOrder.indexOf(canonicalPipelineStage(staleFromStage));
  const stageIndex = stageOrder.indexOf(canonicalPipelineStage(stage));
  return staleIndex >= 0 && stageIndex >= staleIndex;
}

function isCurrentRunningStage(current: CaseRecord, stage: string): boolean {
  if (current.status !== "analysis_running" && current.status !== "svg_running") return false;
  return stageMatchesNode(current.stage, stage);
}

function latestWorkflowNodeRun(nodeRuns: WorkflowNodeRunRecord[], nodeId: string): WorkflowNodeRunRecord | null {
  const runs = nodeRuns.filter((run) => run.node_id === nodeId);
  if (!runs.length) return null;
  return [...runs].sort((a, b) => {
    const attemptOrder = a.attempt_id.localeCompare(b.attempt_id, undefined, { numeric: true });
    if (attemptOrder !== 0) return attemptOrder;
    return timestamp(a.started_at) - timestamp(b.started_at);
  })[runs.length - 1] || null;
}

function compareStageRunRecency(a: StageRunRecord, b: StageRunRecord): number {
  const startedOrder = timestamp(a.started_at) - timestamp(b.started_at);
  if (startedOrder !== 0) return startedOrder;
  const endedOrder = timestamp(a.ended_at) - timestamp(b.ended_at);
  if (endedOrder !== 0) return endedOrder;
  const attemptOrder = numericAttempt(a.attempt) - numericAttempt(b.attempt);
  if (attemptOrder !== 0) return attemptOrder;
  return a.stage_run_id.localeCompare(b.stage_run_id, undefined, { numeric: true });
}

function numericAttempt(value: number): number {
  return Number.isFinite(value) ? value : 0;
}

function timestamp(value: string): number {
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function durationText(startedAt: string, endedAt: string): string {
  const start = Date.parse(startedAt);
  if (!Number.isFinite(start)) return "-";
  const end = endedAt ? Date.parse(endedAt) : Date.now();
  const seconds = Math.max(0, Math.round((end - start) / 1000));
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${minutes}m ${rest}s`;
}
