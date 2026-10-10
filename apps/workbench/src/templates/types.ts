export interface TemplateImage {
  filename: string;
  original_url: string;
  sha256: string;
  width: number;
  height: number;
  image_urls?: { thumb?: string; card?: string; modal?: string };
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
  assets: TemplateImage[];
  source_policy?: string;
  provenance: { source_name?: string; source?: string; source_url?: string; license_note?: string }[];
}
export interface TemplateFilters {
  query?: string;
  category?: string;
  with_images?: boolean;
  template_ids?: string[];
  offset?: number;
  limit?: number;
  action?: "search" | "recommend";
}
export interface TemplateCatalog { templates: VisualTemplate[]; source?: unknown }
export interface CatalogResult {
  total: number;
  library_count: number;
  image_count: number;
  categories: string[];
  offset: number;
  limit: number;
  templates: VisualTemplate[];
  ranking?: string;
}
export interface TemplateSelection { template: VisualTemplate; role: "structure" | "style" }
export interface TemplateView { view?: TemplateFilters; result?: CatalogResult }
