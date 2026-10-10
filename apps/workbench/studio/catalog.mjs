import { readFile } from "node:fs/promises";

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

export async function searchTemplates({
  query = "",
  category = "",
  with_images = false,
  offset = 0,
  limit = 60,
} = {}) {
  const source = await loadCatalog();
  const aliases = {
    消融: "ablation",
    流程: "flow",
    架构: "architecture",
    论文: "academic",
    教学: "teaching",
    课程: "course",
    图表: "chart",
    数据: "data",
    方法: "method",
    对比: "comparison",
    时间线: "timeline",
    极简: "minimal",
    咨询: "consulting",
    品牌: "brand",
    产品: "product",
    信息图: "infographic",
    实验: "experiment",
  };
  let normalized = query.trim().toLowerCase();
  for (const [zh, en] of Object.entries(aliases))
    normalized = normalized.replaceAll(zh, ` ${en} `);
  const words = normalized.split(/\s+/).filter(Boolean);
  const all = source.templates;
  const categories = [...new Set(all.map((card) => card.category))].sort();
  const matches = all.filter(
    (card) =>
      (!category || card.category === category) &&
      (!with_images || card.assets.length > 0) &&
      words.every((word) =>
        [
          card.id,
          card.name,
          card.category,
          card.prompt_recipe,
          ...(card.scenario_tags || []),
          ...(card.visual_tags || []),
          ...(card.layout_archetypes || []),
        ]
          .join(" ")
          .toLowerCase()
          .includes(word),
      ),
  );
  const start = Math.max(0, Math.floor(offset));
  const count = Math.max(1, Math.min(120, Math.floor(limit)));
  return {
    total: matches.length,
    library_count: all.length,
    image_count: all.filter((card) => card.assets.length).length,
    categories,
    offset: start,
    limit: count,
    templates: matches.slice(start, start + count),
    source: source.source,
  };
}
