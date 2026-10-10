const aliases = {
  技术架构: "technical architecture", 工作流程: "workflow flow", 消融: "ablation",
  组会: "research", 学术: "academic", 论文: "academic", 科研: "research",
  教学: "teaching", 课程: "course", 架构: "architecture", 流程: "flow",
  图表: "chart", 数据: "data", 方法: "method", 实验: "experiment",
  对比: "comparison", 时间线: "timeline", 极简: "minimal", 咨询: "consulting",
  品牌: "brand", 产品: "product", 信息图: "infographic", 答辩: "academic",
};

export function queryWords(query = "") {
  let normalized = query.trim().toLowerCase();
  for (const [zh, en] of Object.entries(aliases)) normalized = normalized.replaceAll(zh, ` ${en} `);
  return [...new Set(normalized.split(/[^\p{L}\p{N}_-]+/u).filter(Boolean))];
}

export function searchCatalog(source, {
  query = "", category = "", with_images = false, template_ids,
  offset = 0, limit = 12, action = "search",
} = {}) {
  if (!Number.isInteger(offset) || offset < 0) throw new Error("offset must be a non-negative integer");
  if (!Number.isInteger(limit) || limit < 1 || limit > 120) throw new Error("limit must be between 1 and 120");
  const all = source.templates;
  if (template_ids) {
    for (const id of template_ids) if (!all.some((card) => card.id === id)) throw new Error(`Unknown template: ${id}`);
  }
  const words = queryWords(query);
  const candidates = all.filter((card) =>
    (!category || card.category === category) &&
    (!with_images || card.assets.length > 0) &&
    (!template_ids || template_ids.includes(card.id)),
  );
  const ranked = candidates.map((card) => {
    const fields = [
      [card.name, 4], [card.category, 3], [(card.scenario_tags || []).join(" "), 3],
      [(card.layout_archetypes || []).join(" "), 3],
      [(card.visual_tags || []).join(" "), 2], [card.prompt_recipe, 1], [card.id, 1],
    ];
    const matched = words.filter((word) => fields.some(([text]) => String(text).toLowerCase().includes(word)));
    const score = words.reduce((sum, word) => sum + fields.reduce((n, [text, weight]) =>
      n + (String(text).toLowerCase().includes(word) ? weight : 0), 0), 0);
    return { card, matched, score };
  }).filter(({ matched }) => !words.length || (action === "recommend" ? matched.length > 0 : matched.length === words.length));
  if (action === "recommend") ranked.sort((a, b) => b.score - a.score || a.card.name.localeCompare(b.card.name));
  else if (template_ids) ranked.sort((a, b) => template_ids.indexOf(a.card.id) - template_ids.indexOf(b.card.id));
  return {
    total: ranked.length,
    library_count: all.length,
    image_count: all.filter((card) => card.assets.length).length,
    categories: [...new Set(all.map((card) => card.category))].sort(),
    offset, limit,
    templates: ranked.slice(offset, offset + limit).map(({ card }) => card),
    ...(action === "recommend" ? { ranking: "keyword_relevance" } : {}),
    source: source.source,
  };
}
