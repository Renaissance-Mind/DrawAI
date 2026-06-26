import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import test from "node:test";
import ts from "../node_modules/typescript/lib/typescript.js";

test("image generation methods include Codex only when detected and images API presets", async () => {
  const { imageGenMethodCards } = await loadImageGenSettingsModule();
  const methods = imageGenMethodCards(
    { provider: "codex", baseUrl: "", apiKey: "", model: "gpt-image-2" },
    [
      apiPreset("openai_images", "images_api", "https://api.openai.com/v1", "gpt-image-2"),
      apiPreset("openrouter", "llm_chat_completions", "https://openrouter.ai/api/v1", "openai/gpt-4o-mini")
    ],
    [
      { provider_id: "codex_sdk", label: "Codex SDK", kind: "sdk", available: true, status: "ok", command: [], version: "" }
    ]
  );

  assert.deepEqual(
    methods.map((method) => method.id),
    ["codex_builtin", "api_preset:openai_images"]
  );
  assert.equal(methods[0].selected, true);
  assert.equal(methods[1].provider, "api");
});

test("image generation methods hide Codex picker option when Codex is unavailable", async () => {
  const { codexImageGenAvailable, imageGenMethodPickerOptions } = await loadImageGenSettingsModule();
  const agents = [
    { provider_id: "codex_sdk", label: "Codex SDK", kind: "sdk", available: false, status: "missing", command: [], version: "" }
  ];

  assert.equal(codexImageGenAvailable(agents), false);
  assert.deepEqual(
    imageGenMethodPickerOptions([apiPreset("openai_images", "images_api", "https://api.openai.com/v1", "gpt-image-2")], agents).map((option) => option.id),
    ["custom", "api_preset:openai_images"]
  );
});

test("image generation method selection resolves to the active connection", async () => {
  const { imageGenConnectionFromMethod } = await loadImageGenSettingsModule();
  const fallback = { provider: "codex", baseUrl: "", apiKey: "", model: "gpt-image-2" };
  const preset = apiPreset("apimart_images", "images_api", "https://api.apimart.ai/v1", "gpt-image-2");

  assert.deepEqual(imageGenConnectionFromMethod({ kind: "codex_builtin" }, fallback), {
    provider: "codex",
    baseUrl: "",
    apiKey: "",
    model: "gpt-image-2",
    methodId: "codex_builtin",
    apiPresetId: "",
    label: "Codex 内置"
  });
  assert.deepEqual(imageGenConnectionFromMethod({ kind: "api_preset", preset }, fallback), {
    provider: "api",
    baseUrl: "https://api.apimart.ai/v1",
    apiKey: "plain-key",
    model: "gpt-image-2",
    methodId: "api_preset:apimart_images",
    apiPresetId: "apimart_images",
    label: "API Mart Images"
  });
  assert.deepEqual(imageGenConnectionFromMethod({ kind: "custom" }, { ...fallback, label: "Codex 内置" }), {
    provider: "api",
    baseUrl: "https://api.openai.com/v1",
    apiKey: "",
    model: "gpt-image-2",
    methodId: "custom",
    apiPresetId: "",
    label: "自定义"
  });
});

test("image generation connection draft resolves selected API preset after reload", async () => {
  const { resolveImageGenConnectionDraft } = await loadImageGenSettingsModule();
  const draft = {
    provider: "api",
    baseUrl: "https://stale.example/v1",
    apiKey: "old-key",
    model: "stale-model",
    methodId: "api_preset:apimart_images",
    apiPresetId: "apimart_images",
    label: "Old Images"
  };

  assert.deepEqual(resolveImageGenConnectionDraft(draft, [apiPreset("apimart_images", "images_api", "https://api.apimart.ai/v1", "gpt-image-2")]), {
    provider: "api",
    baseUrl: "https://api.apimart.ai/v1",
    apiKey: "plain-key",
    model: "gpt-image-2",
    methodId: "api_preset:apimart_images",
    apiPresetId: "apimart_images",
    label: "API Mart Images"
  });
});

function apiPreset(id, type, baseUrl, model) {
  return {
    id,
    label: id === "apimart_images" ? "API Mart Images" : id,
    type,
    base_url: baseUrl,
    model,
    api_key_env: "OPENAI_API_KEY",
    api_key: id === "apimart_images" ? "plain-key" : ""
  };
}

let imageGenSettingsModulePromise;

function loadImageGenSettingsModule() {
  imageGenSettingsModulePromise ||= loadTsModule("../src/imageGenSettings.ts");
  return imageGenSettingsModulePromise;
}

async function loadTsModule(relativePath) {
  const source = readFileSync(new URL(relativePath, import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2020
    }
  });
  const dir = mkdtempSync(join(tmpdir(), "drawai-imagegen-settings-"));
  const modulePath = join(dir, `${relativePath.split("/").at(-1).replace(/\.ts$/, "")}.mjs`);
  writeFileSync(modulePath, outputText);
  return import(pathToFileURL(modulePath).href);
}
