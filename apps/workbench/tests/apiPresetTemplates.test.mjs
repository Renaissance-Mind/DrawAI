import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import test from "node:test";
import ts from "../node_modules/typescript/lib/typescript.js";

test("API preset templates include common OpenAI-compatible providers", async () => {
  const { API_PRESET_TEMPLATES } = await loadTemplateModule();

  const templatesById = new Map(API_PRESET_TEMPLATES.map((template) => [template.id, template]));
  assert.equal(templatesById.get("deepseek")?.base_url, "https://api.deepseek.com/v1");
  assert.equal(templatesById.get("openrouter")?.base_url, "https://openrouter.ai/api/v1");
  assert.equal(templatesById.get("ollama")?.base_url, "http://localhost:11434/v1");
});

test("API preset templates include local provider icons", async () => {
  const { API_PRESET_TEMPLATES } = await loadTemplateModule();

  for (const template of API_PRESET_TEMPLATES) {
    assert.match(template.icon_url, /^\/provider-icons\/.+\.svg$/);
    assert.equal(existsSync(new URL(`../public${template.icon_url}`, import.meta.url)), true, template.icon_url);
  }
});

test("API preset templates create editable drafts without copying secrets", async () => {
  const { API_PRESET_TEMPLATES, apiPresetDraftFromTemplate } = await loadTemplateModule();

  const ollama = API_PRESET_TEMPLATES.find((template) => template.id === "ollama");
  const draft = apiPresetDraftFromTemplate(ollama, []);

  assert.equal(draft.id, "ollama");
  assert.equal(draft.label, "Ollama");
  assert.equal(draft.type, "llm_chat_completions");
  assert.equal(draft.api_key_env, "");
  assert.equal(draft.api_key, "");
});

test("API preset template ids are stable and deduplicated", async () => {
  const { API_PRESET_TEMPLATES, apiPresetDraftFromTemplate, blankApiPresetDraft } = await loadTemplateModule();
  const deepseek = API_PRESET_TEMPLATES.find((template) => template.id === "deepseek");

  const fromTemplate = apiPresetDraftFromTemplate(deepseek, [{ id: "deepseek" }]);
  const blank = blankApiPresetDraft([{ id: "api_preset" }, { id: "api_preset_2" }]);

  assert.equal(fromTemplate.id, "deepseek_2");
  assert.equal(blank.id, "api_preset_3");
  assert.equal(blank.base_url, "https://api.openai.com/v1");
});

test("API preset templates can be searched and matched back to saved presets", async () => {
  const { API_PRESET_TEMPLATES, apiPresetTemplateForPreset, apiPresetTemplateSearchText } = await loadTemplateModule();
  const openrouter = API_PRESET_TEMPLATES.find((template) => template.id === "openrouter");

  assert.match(apiPresetTemplateSearchText(openrouter), /openrouter\.ai/);
  assert.equal(
    apiPresetTemplateForPreset({
      id: "openrouter_2",
      label: "OpenRouter",
      type: "llm_chat_completions",
      base_url: "https://openrouter.ai/api/v1",
      model: "openai/gpt-4o-mini",
      api_key_env: "OPENROUTER_API_KEY",
      api_key: ""
    })?.icon_url,
    "/provider-icons/openrouter.svg"
  );
});

let templateModulePromise;

function loadTemplateModule() {
  templateModulePromise ||= loadTsModule("../src/apiPresetTemplates.ts");
  return templateModulePromise;
}

async function loadTsModule(relativePath) {
  const source = readFileSync(new URL(relativePath, import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2020
    }
  });
  const dir = mkdtempSync(join(tmpdir(), "drawai-api-preset-templates-"));
  const modulePath = join(dir, `${relativePath.split("/").at(-1).replace(/\.ts$/, "")}.mjs`);
  writeFileSync(modulePath, outputText);
  return import(pathToFileURL(modulePath).href);
}
