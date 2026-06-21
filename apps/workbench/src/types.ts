export type SourceStrategy = "svg_self_draw" | "crop" | "crop_nobg";
export type RunCompatibilityMode = "v2" | "legacy_readonly" | "none";
export type V2AssetStatus = "pending" | "running" | "ok" | "failed" | "unsupported" | string;
export type AssetGeometry =
  | { kind: "bbox"; bbox: [number, number, number, number]; coordinate_system?: string }
  | { kind: "polygon"; points: Array<[number, number]>; bbox?: [number, number, number, number]; coordinate_system?: string }
  | { kind: "mask"; mask_path?: string; bbox: [number, number, number, number]; coordinate_system?: string };

export type BatchStatus = "queued" | "running" | "waiting_review" | "completed" | "failed" | "canceled";
export type CaseStatus =
  | "queued"
  | "analysis_running"
  | "assets_review"
  | "svg_running"
  | "completed"
  | "failed"
  | "canceled";

export interface HealthResponse {
  status: string;
  workspace: string;
  cloud_mode: boolean;
  runtime_services: Record<string, RuntimeServiceStatus>;
  runtime_activity?: Record<string, RuntimeActivityStatus>;
}

export interface RuntimeServiceStatus {
  name: string;
  base_url: string;
  health_url: string;
  status: "online" | "offline" | string;
  error?: string;
}

export interface RuntimeActivityStatus {
  limit: number;
  queued: number;
  running: number;
}

export interface BatchRecord {
  batch_id: string;
  name: string;
  input_mode: string;
  status: BatchStatus;
  max_concurrent_cases: number;
  auto_run_svg_after_analysis: boolean;
  created_at: string;
  updated_at: string;
  case_counts: Record<string, number>;
  workflow_template_id: string;
  error_message: string;
}

export interface CaseRecord {
  case_id: string;
  batch_id: string;
  name: string;
  status: CaseStatus;
  phase: string;
  stage: string;
  source_image_path: string;
  preview_url?: string;
  editor_ready?: boolean;
  run_root: string;
  config_path: string;
  error_message: string;
  stale_from_stage: string;
  compatibility_mode?: RunCompatibilityMode;
  can_fork_from_source?: boolean;
}

export interface V2ProcessingIntent {
  object_type: string;
  processing_type: string;
  parameters: Record<string, unknown>;
}

export interface V2ElementPlan {
  schema: string;
  element_id: string;
  source_candidate_ids: string[];
  element_type: string;
  bbox: [number, number, number, number];
  geometry: Record<string, unknown>;
  z_order: number;
  confidence: "low" | "medium" | "high" | string;
  processing_intent: V2ProcessingIntent;
  review_status: "deterministic" | "agent_refined" | "user_edited" | string;
  created_by_stage: string;
  change_reason: string;
}

export interface V2ProcessorRun {
  processor_type: string;
  status: V2AssetStatus;
  started_at: string;
  ended_at: string;
  input_refs: Record<string, unknown>;
  output_refs: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface V2AssetResult {
  result_id: string;
  processor_type: string;
  status: V2AssetStatus;
  kind: string;
  path?: string;
  files?: Array<Record<string, unknown>>;
  metadata?: Record<string, unknown>;
  width?: number;
  height?: number;
  created_at?: string;
}

export interface V2AssetPackage {
  schema: string;
  asset_id: string;
  element_id: string;
  processor_type: string;
  status: V2AssetStatus;
  files: string[];
  metadata: Record<string, unknown>;
  processor_runs: V2ProcessorRun[];
  all_results: V2AssetResult[];
  active_result: V2AssetResult | null;
  editable_payload: Record<string, unknown> | null;
  failure: string | null;
  created_at: string;
}

export interface V2RunPackage {
  schema: string;
  run_id: string;
  root: string;
  source_image: string;
  canvas: Record<string, unknown>;
  created_at: string;
  metadata: Record<string, unknown>;
  elements?: V2ElementPlan[];
  source_elements?: V2ElementPlan[];
  asset_packages?: V2AssetPackage[];
  compose_outputs?: Record<string, unknown>;
  export_outputs?: Record<string, unknown>;
}

export interface V2Compatibility {
  mode: RunCompatibilityMode;
  can_fork_from_source: boolean;
}

export interface ArtifactRecord {
  artifact_token: string;
  case_id: string;
  label: string;
  media_type: string;
  created_at: string;
  url: string;
}

export interface SvgSourceResponse {
  svg: string;
  size_bytes: number;
  updated_at: number;
  artifact: ArtifactRecord;
  case: CaseRecord;
}

export interface StageRunRecord {
  stage_run_id: string;
  case_id: string;
  stage_name: string;
  status: string;
  attempt: number;
  started_at: string;
  ended_at: string;
  log_path: string;
  error_message: string;
}

export interface WorkflowNodeRunRecord {
  node_id: string;
  attempt_id: string;
  status: string;
  started_at: string;
  ended_at: string;
  error_message: string;
  workdir: string;
}

export interface CaseProgressFile {
  label: string;
  relative_path: string;
  exists: boolean;
  media_type: string;
  size_bytes: number;
  updated_at: number | null;
  url: string;
}

export interface WorkflowNodeViewer {
  case_id: string;
  node_id: string;
  available: boolean;
  kind: "element_candidates" | "element_plans" | "element_analysis" | "none" | string;
  title: string;
  message: string;
  source_image: {
    relative_path: string;
    url: string;
  };
  workdir: string;
  attempt_id: string;
  source_path?: string;
  node_run: Record<string, unknown> | null;
  input_manifest: Record<string, unknown> | null;
  files: CaseProgressFile[];
  elements: V2ElementPlan[];
}

export interface SvgAttemptProgress {
  phase: string;
  attempt: string;
  relative_path: string;
  status: string;
  issue_count: number;
  issue_summaries: string[];
  error_message: string;
  updated_at: number | null;
  files: CaseProgressFile[];
}

export interface PptxExportProgress {
  status: string;
  export_backend: string;
  requested_export_mode: string;
  effective_export_mode: string;
  export_mode: string;
  editable_surface: string;
  report_url: string;
}

export interface AssetElement {
  box_id: string;
  source_candidate_ids: string[];
  refinement_action: string;
  bbox: [number, number, number, number];
  source_strategy: SourceStrategy;
  visual_role: string;
  type: string;
  confidence: string;
  reason: string;
  evidence: string[];
  geometry?: AssetGeometry;
  geometry_kind?: string;
  geometry_locked?: boolean;
  geometry_preview_relative_path?: string;
  mask_preview?: string;
  current_pipeline_method?: string;
  recommended_asset_source?: string;
  processed_asset_relative_path?: string;
  processed_asset_source_strategy?: SourceStrategy;
  processed_asset_updated_at?: string;
  processed_asset_width?: number;
  processed_asset_height?: number;
  processing_status?: "pending" | "processed" | "failed" | string;
  processing_error?: string;
  rmbg_elapsed_ms?: number;
  rmbg_artifacts?: Record<string, unknown>;
}

export interface AssetPlan {
  schema: string;
  case_id: string;
  source: string;
  updated_at?: string;
  elements: AssetElement[];
  categories?: Record<string, number>;
}

export interface ProcessedAssetRecord {
  box_id: string;
  source_strategy: SourceStrategy;
  relative_path: string;
  url: string;
  width: number;
  height: number;
  rmbg_elapsed_ms: number;
}

export interface AssetProcessingResponse {
  asset_plan: AssetPlan;
  processed_assets: ProcessedAssetRecord[];
}

export type ImageGenerationProvider = "api" | "codex";

export interface ImageGenerationRequest {
  provider?: ImageGenerationProvider;
  model: string;
  prompt: string;
  size: string;
  quality: string;
  background: string;
  moderation: string;
  output_format: string;
  output_compression?: number;
  n: number;
  api_base_url?: string;
  api_key?: string;
}

export interface ImageEditRequest {
  provider: "codex";
  source_image_path: string;
  prompt: string;
  model?: string;
  size?: string;
  quality?: string;
  background?: string;
  output_format?: string;
}

export type ImageGenerationResponse = Record<string, unknown>;

export interface BatchDetail {
  batch: BatchRecord;
  cases: CaseRecord[];
}

export interface CaseDetail {
  case: CaseRecord;
  stage_runs: StageRunRecord[];
  artifacts: ArtifactRecord[];
}

export interface CaseProgress {
  case: CaseRecord;
  stage_runs: StageRunRecord[];
  workflow_node_runs: WorkflowNodeRunRecord[];
  files: CaseProgressFile[];
  svg_attempts: SvgAttemptProgress[];
  pptx_export: PptxExportProgress;
}
