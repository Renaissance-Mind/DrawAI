import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { loadCatalog, findTemplate, searchTemplates } from "../catalog.mjs";
import { dispatch } from "../server.mjs";
import { prepareReference } from "../references.mjs";

test("the real catalog retains its images, recipes and provenance", async () => {
  const catalog = await loadCatalog();
  assert.ok(catalog.templates.length >= 629);
  assert.equal(new Set(catalog.templates.map((card) => card.id)).size, catalog.templates.length);
  assert.ok(catalog.source.repository.startsWith("https://github.com/"));
  for (const template of catalog.templates) {
    assert.ok(template.prompt_recipe);
    for (const asset of template.assets) {
      assert.equal(new URL(asset.original_url).hostname, "assets.visualize.renaissancemind.ai");
      assert.match(asset.sha256, /^[a-f0-9]{64}$/);
    }
  }
});

test("Chinese search and category/image filters retrieve real matching references", async () => {
  const result = await searchTemplates({ query: "消融", category: "academic_research", with_images: true });
  assert.ok(result.total > 0);
  assert.ok(result.templates.every((card) => card.category === "academic_research" && card.assets.length));
  assert.ok(result.templates.some((card) => card.id.includes("ablation")));
});

test("recommendations use partial keyword relevance without dropping a useful candidate", async () => {
  const result = await searchTemplates({ action: "recommend", query: "论文 消融 不存在的词", limit: 6 });
  assert.equal(result.ranking, "keyword_relevance");
  assert.equal(result.templates.length, 6);
  assert.ok(result.templates[0].id.includes("ablation"));
});

test("inline shortlists preserve requested order and include recipe-only references", async () => {
  const catalog = await loadCatalog();
  const recipe = catalog.templates.find((card) => !card.assets.length);
  const image = catalog.templates.find((card) => card.assets.length);
  const ids = [recipe.id, image.id];
  const shown = await dispatch("drawai_show_templates", { template_ids: ids });
  assert.deepEqual(shown.result.templates.map((card) => card.id), ids);
  assert.equal(shown.view.with_images, false);
  assert.equal(shown.view.limit, 6);
});

test("pagination is stable and unknown IDs or invalid bounds are exposed", async () => {
  const first = await searchTemplates({ limit: 6 });
  const second = await searchTemplates({ offset: 6, limit: 6 });
  assert.equal(new Set([...first.templates, ...second.templates].map((card) => card.id)).size, 12);
  await assert.rejects(searchTemplates({ template_ids: ["missing-reference"] }), /Unknown template/);
  await assert.rejects(findTemplate("missing-reference"), /Unknown visual reference/);
  await assert.rejects(searchTemplates({ limit: 0 }), /limit/);
  await assert.rejects(searchTemplates({ offset: -1 }), /offset/);
});

test("recipe preparation saves actual metadata and never overwrites a different file", async (t) => {
  const directory = await mkdtemp(path.join(os.tmpdir(), "drawai-template-reference-"));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const { templates } = await loadCatalog();
  const recipe = templates.find((card) => !card.assets.length);
  const prepared = await prepareReference({ template_id: recipe.id, output_directory: directory });
  assert.deepEqual(prepared.images, []);
  assert.equal(JSON.parse(await readFile(prepared.manifest, "utf8")).template.prompt_recipe, recipe.prompt_recipe);
  await prepareReference({ template_id: recipe.id, output_directory: directory });
  await writeFile(prepared.manifest, "existing user file");
  await assert.rejects(prepareReference({ template_id: recipe.id, output_directory: directory }), /different content/);
  assert.equal(await readFile(prepared.manifest, "utf8"), "existing user file");
});

test("the actual MCP server exposes template, plan and Flow tools with one inline resource", async (t) => {
  const client = new Client({ name: "drawai-template-integration", version: "1.0.0" });
  t.after(() => client.close());
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [fileURLToPath(new URL("../server.mjs", import.meta.url))] }));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((tool) => tool.name), ["drawai_image", "drawai_templates", "drawai_show_templates", "drawai_prepare_template", "drawai_plan", "drawai_flow"]);
  const data = tools.find((tool) => tool.name === "drawai_templates");
  assert.equal(data._meta?.ui?.resourceUri, undefined);
  const render = tools.find((tool) => tool.name === "drawai_show_templates");
  assert.match(render._meta.ui.resourceUri, /^ui:\/\/drawai\/templates-[a-f0-9]{16}\.html$/);
  const result = await client.callTool({ name: data.name, arguments: { action: "search", query: "消融", limit: 2 } });
  assert.equal(result.isError, undefined);
  const ids = result.structuredContent.templates.map((card) => card.id);
  const shown = await client.callTool({ name: render.name, arguments: { template_ids: ids } });
  assert.deepEqual(shown.structuredContent.result.templates.map((card) => card.id), ids);
  const resource = await client.readResource({ uri: shown._meta.ui.resourceUri });
  const content = resource.contents[0];
  assert.deepEqual(content._meta["openai/ui"].availableDisplayModes, ["inline", "fullscreen"]);
  const domains = new Set(content._meta.ui.csp.resourceDomains);
  for (const card of shown.structuredContent.result.templates) {
    for (const image of card.assets) {
      for (const url of [image.original_url, ...Object.values(image.image_urls || {})]) assert.ok(domains.has(new URL(url).origin));
    }
  }
  const hash = createHash("sha256").update(content.text).digest("hex").slice(0, 16);
  assert.ok(content.uri.includes(hash));
  assert.doesNotMatch(content.text, /<script\b[^>]*src=/);
  const logo = await readFile(new URL("../../public/drawai_image.png", import.meta.url));
  assert.ok(content.text.includes(`data:image/png;base64,${logo.toString("base64")}`));
  const plan = await client.callTool({ name: "drawai_plan", arguments: { request: {
    environment: { model: "gpt-6.1-sol", model_source: "session_metadata", image_generation_available: true, image_viewing_available: true, local_execution_available: true },
    preferences: { skip_questions: true },
  } } });
  assert.equal(plan.isError, undefined);
  assert.equal(plan.structuredContent.decisions.mode, "skill");
  assert.deepEqual(plan.structuredContent.questions, []);
});
