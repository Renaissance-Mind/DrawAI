export type SourceStrategy = "svg_self_draw" | "crop" | "crop_nobg";
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
export type ReferenceMode =
  | "reference_context"
  | "reference_tokens_only"
  | "reference_edit_low"
  | "reference_edit_high"
  | "content_edit";

export interface SlideTemplateCard {
  id: string;
  name: string;
  category: string;
  scenario_tags: string[];
  visual_tags: string[];
  prompt_recipe: string;
  visual_keywords: string[];
  palette: string[];
  layout_archetypes: string[];
  text_density: string;
  reference_images: Array<Record<string, unknown>>;
  sample_outputs: string[];
  source_policy: string;
  ip_safety?: string;
  tests: string[];
  provenance: Array<Record<string, unknown>>;
}

export interface SlideTemplateCardsResponse {
  schema: string;
  count: number;
  cards: SlideTemplateCard[];
}

export interface SlideTemplateGalleryPage {
  page_id: string;
  page_title: string;
  page_index: number;
  page_count: number;
  status: string;
  image_url: string;
  prompt_url: string;
  payload_url: string;
  record_url: string;
}

export interface SlideTemplateGalleryItem {
  template_id: string;
  template_name: string;
  category: string;
  reason: string;
  template_dir: string;
  page_count: number;
  ok_count: number;
  status: string;
  contact_sheet_url: string;
  pages: SlideTemplateGalleryPage[];
}

export interface SlideTemplateGalleryResponse {
  schema: string;
  status: string;
  output_dir: string;
  user_prompt: string;
  template_count: number;
  pages_per_template: number;
  count: number;
  templates: SlideTemplateGalleryItem[];
  contact_sheet_url: string;
  summary_url: string;
  summary_md_url: string;
  message?: string;
}

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
  source_image_path?: string;
  reference_image_path?: string;
  reference_image_paths?: string[];
  api_base_url?: string;
  api_key?: string;
  language?: string;
  output_language?: string;
  research_context?: unknown;
  sources?: unknown;
  citations?: unknown;
  claims?: unknown;
  data_sources?: unknown;
  locked_visible_text?: unknown;
  exact_visible_text?: unknown;
  do_not_translate_visible_text?: unknown;
  locked_visible_text_exact?: boolean;
  visible_text?: unknown;
  visible_text_blocks?: unknown;
  text_density?: string;
  subtitle?: string;
  key_message?: string;
  style?: string;
  visual_style?: string;
  template?: string;
  template_id?: string;
  template_card_id?: string;
  template_card?: unknown;
  strategy?: string;
  deck_type?: string;
  intent?: string;
  source_mode?: string;
  rendering_mode?: string;
  ip_safety_mode?: string;
  reference_mode?: ReferenceMode;
  reference_image_tokens?: unknown;
  spec_guided_enabled?: boolean;
  template_spec?: unknown;
  slot_schema?: unknown;
  reference_style_spec?: unknown;
  design_tokens?: unknown;
  spec_lock?: unknown;
  reference_roles?: unknown;
  style_candidate_index?: number;
  style_candidate_count?: number;
  candidate_index?: number;
  candidate_count?: number;
  design_system?: unknown;
  quality_gates?: unknown;
  composition_guidance?: unknown;
  visual_richness_guidance?: unknown;
  drawai_postprocess?: unknown;
  must_include?: unknown;
  must_avoid?: unknown;
  negative_prompt?: string;
  slide_mode?: string;
  slide_type?: string;
  audience?: string;
  tone?: string;
  brand?: unknown;
  fact_policy?: string;
  source_policy?: string;
  text_policy?: string;
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
  files: CaseProgressFile[];
  svg_attempts: SvgAttemptProgress[];
  pptx_export: PptxExportProgress;
}
