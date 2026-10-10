import { readFile } from "node:fs/promises";
import { searchCatalog } from "./query.mjs";

export const CATALOG_PATH = new URL(
  "./data/visual-reference-templates.json",
  import.meta.url,
);
let catalog;
export async function loadCatalog() {
  catalog ??= JSON.parse(await readFile(CATALOG_PATH, "utf8"));
  return catalog;
}

export async function findTemplate(id) {
  const card = (await loadCatalog()).templates.find((item) => item.id === id);
  if (!card) throw new Error(`Unknown visual reference: ${id}`);
  return structuredClone(card);
}

export async function searchTemplates(options = {}) {
  return searchCatalog(await loadCatalog(), options);
}
