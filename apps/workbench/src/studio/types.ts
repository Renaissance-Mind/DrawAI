export type ReferenceRole = "content" | "structure" | "style" | "ppt_template";
export type TaskKind =
  | "generate"
  | "edit_image"
  | "convert"
  | "prepare_reference"
  | "export_deck";
export type TaskStatus =
  | "draft"
  | "submitted"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";
export interface StudioAsset {
  id: string;
  filename: string;
  mime_type: string;
  size: number;
  sha256: string;
  relative_path: string;
  created_at: string;
  kind: string;
  slide_id?: string | null;
  task_id?: string | null;
  source_image_id?: string | null;
  description?: string;
}
export interface TemplateAsset {
  filename: string;
  original_url: string;
  sha256: string;
  width: number;
  height: number;
  image_urls?: { thumb?: string; card?: string; modal?: string };
  caption?: string;
}
export interface VisualTemplate {
  id: string;
  name: string;
  category: string;
  prompt_recipe: string;
  scenario_tags: string[];
  visual_tags: string[];
  palette: string[];
  layout_archetypes: string[];
  assets: TemplateAsset[];
  origin: string;
  provenance: Array<{
    source_name?: string;
    source?: string;
    source_url?: string;
    license_note?: string;
  }>;
}
export interface StudioReference {
  id: string;
  name: string;
  role: ReferenceRole;
  notes: string;
  slide_ids: string[];
  asset_ids: string[];
  preview_asset_id?: string;
  template_id?: string;
  recipe?: string;
  template?: VisualTemplate;
}
export interface StudioSlide {
  id: string;
  title: string;
  content: string;
  notes: string;
  reference_ids: string[];
  revision: number;
  current_image_id: string | null;
  current_pptx_id: string | null;
  content_changed?: boolean;
}
export interface StudioTask {
  id: string;
  kind: TaskKind;
  status: TaskStatus;
  slide_ids: string[];
  instruction: string;
  created_at: string;
  updated_at: string;
  message: string;
  prompt: string;
  request_path: string;
  artifact_ids: string[];
  project_input_revision?: number;
  slide_revisions?: Record<string, number>;
  source_image_ids?: Record<string, string | null>;
  events: Array<{ at: string; status: string; message: string }>;
}
export interface StudioProject {
  id: string;
  title: string;
  brief: string;
  language: string;
  aspect_ratio: string;
  style_notes: string;
  source_directory: string;
  revision: number;
  input_revision?: number;
  created_at: string;
  updated_at: string;
  slides: StudioSlide[];
  references: StudioReference[];
  assets: StudioAsset[];
  tasks: StudioTask[];
}
export interface ProjectSummary {
  id: string;
  title: string;
  updated_at: string;
  slide_count: number;
  task_count: number;
}
export interface CatalogResult {
  total: number;
  library_count: number;
  image_count: number;
  categories: string[];
  offset: number;
  limit: number;
  templates: VisualTemplate[];
}
export interface ToolResult {
  project?: StudioProject;
  task?: StudioTask;
  slide_id?: string;
  asset?: StudioAsset;
  projects?: ProjectSummary[];
  data_base64?: string;
  filename?: string;
  mime_type?: string;
}
