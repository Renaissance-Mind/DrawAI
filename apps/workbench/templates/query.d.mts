import type { TemplateCatalog, TemplateFilters, CatalogResult } from "../src/templates/types";
export function queryWords(query?: string): string[];
export function searchCatalog(source: TemplateCatalog, filters?: TemplateFilters): CatalogResult;
