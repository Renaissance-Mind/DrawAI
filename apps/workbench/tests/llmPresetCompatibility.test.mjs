import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import test from "node:test";
import ts from "../node_modules/typescript/lib/typescript.js";

test("multi-endpoint presets expose only harness-compatible routes", async () => {
  const {
    compatibleAgentsForEndpoint,
    compatibleEndpointsForAgent,
    preferredCompatibleEndpoint
  } = await loadModule();
  const preset = multiEndpointPreset();
  const claude = agent("claude_agent_sdk", ["llm_anthropic"]);
  const builtin = agent("drawai_tool_agent", ["llm_chat_completions"]);

  assert.deepEqual(compatibleEndpointsForAgent(claude, preset).map((endpoint) => endpoint.id), ["anthropic"]);
  assert.deepEqual(compatibleEndpointsForAgent(builtin, preset).map((endpoint) => endpoint.id), ["chat"]);
  assert.equal(preferredCompatibleEndpoint(claude, preset, "chat")?.id, "anthropic");
  assert.deepEqual(
    compatibleAgentsForEndpoint([claude, builtin], preset.endpoints[0]).map((item) => item.provider_id),
    ["claude_agent_sdk"]
  );
});

test("selecting a preset endpoint resolves runtime fields while retaining references", async () => {
  const { agentSettingsWithLlmSelection } = await loadModule();
  const preset = multiEndpointPreset();
  const endpoint = preset.endpoints[1];
  const settings = agentSettingsWithLlmSelection(baseSettings(), preset, endpoint);

  assert.equal(settings.llm_api_preset_id, "gateway");
  assert.equal(settings.llm_endpoint_id, "responses");
  assert.equal(settings.llm_model, "gpt-route");
  assert.equal(settings.llm_wire_api, "responses");
});

function multiEndpointPreset() {
  return {
    id: "gateway",
    label: "Gateway",
    type: "llm",
    base_url: "https://gateway.example/anthropic",
    model: "claude-route",
    api_key_env: "GATEWAY_KEY",
    api_key: "",
    endpoints: [
      endpoint("anthropic", "llm_anthropic", "https://gateway.example/anthropic", "claude-route"),
      endpoint("responses", "llm_responses", "https://gateway.example/v1", "gpt-route"),
      endpoint("chat", "llm_chat_completions", "https://gateway.example/v1", "chat-route")
    ]
  };
}

function endpoint(id, type, baseUrl, model) {
  return { id, label: id, type, base_url: baseUrl, model, api_key_env: "GATEWAY_KEY", api_key: "" };
}

function agent(providerId, apiPresetTypes) {
  return {
    provider_id: providerId,
    label: providerId,
    kind: "sdk",
    available: true,
    api_preset_types: apiPresetTypes
  };
}

function baseSettings() {
  return {
    selected_provider_id: "codex_sdk",
    model: "",
    reasoning_effort: "",
    fast: false,
    timeout_seconds: 0,
    llm_api_preset_id: "",
    llm_endpoint_id: "",
    llm_model: "",
    llm_base_url: "",
    llm_api_key: "",
    llm_api_key_env: "OPENAI_API_KEY",
    llm_wire_api: "chat_completions",
    llm_extra_body: {}
  };
}

let modulePromise;

function loadModule() {
  modulePromise ||= loadTsModule("../src/llmPresetCompatibility.ts");
  return modulePromise;
}

async function loadTsModule(relativePath) {
  const source = readFileSync(new URL(relativePath, import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2020 }
  });
  const dir = mkdtempSync(join(tmpdir(), "drawai-llm-preset-compatibility-"));
  const modulePath = join(dir, "llmPresetCompatibility.mjs");
  writeFileSync(modulePath, outputText);
  return import(pathToFileURL(modulePath).href);
}
