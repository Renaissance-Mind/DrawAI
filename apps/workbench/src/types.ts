export type SourceStrategy = "svg_self_draw" | "crop" | "crop_nobg";
export type AssetGeometry =
  | { kind: "bbox"; bbox: [number, number, number, number]; coordinate_system?: string }
  | { kind: "polygon"; points: Array<[number, number]>; bbox?: [number, number, number, number]; coordinate_system?: string }
  | { kind: "mask"; mask_path: string; bbox: [number, number, number, number]; coordinate_system?: string };

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
}

export interface RuntimeServiceStatus {
  name: string;
  base_url: string;
  health_url: string;
  status: "online" | "offline" | string;
  error?: string;
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

export interface CaseProgressFile {
  label: string;
  relative_path: string;
  exists: boolean;
  media_type: string;
  size_bytes: number;
  updated_at: number | null;
  url: string;
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

export interface ImageGenerationRequest {
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
  files: CaseProgressFile[];
  svg_attempts: SvgAttemptProgress[];
  pptx_export: PptxExportProgress;
}
