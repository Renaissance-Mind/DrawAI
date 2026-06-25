import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import test from "node:test";
import ts from "../node_modules/typescript/lib/typescript.js";

const EXPECTED_AGENT_PROVIDER_IDS = [
  "codex_sdk",
  "codex_cli",
  "kimi_cli",
  "kimi_acp",
  "gemini_acp",
  "qwen_acp",
  "opencode_acp",
  "goose_acp",
  "kiro_acp",
  "qoder_acp",
  "cursor_acp",
  "cline_acp",
  "copilot_acp",
  "hermes_acp",
  "claude_cli",
  "openclaw_cli",
  "hermes_cli"
];

test("Agent provider icon mapping covers selectable Workbench agents", async () => {
  const { AGENT_PROVIDER_ICONS } = await loadPresentationModule();

  for (const providerId of EXPECTED_AGENT_PROVIDER_IDS) {
    assert.ok(AGENT_PROVIDER_ICONS[providerId], providerId);
  }
});

test("Agent provider icon mapping uses bundled image assets", async () => {
  const { AGENT_PROVIDER_ICONS } = await loadPresentationModule();

  for (const [providerId, icon] of Object.entries(AGENT_PROVIDER_ICONS)) {
    assert.match(icon.icon_url, /^\/agent-icons\/.+\.(?:svg|png)$/, providerId);
    assert.equal(existsSync(new URL(`../public${icon.icon_url}`, import.meta.url)), true, icon.icon_url);
  }
});

test("Agent display sorting keeps available providers first", async () => {
  const { sortWorkbenchAgentsForDisplay } = await loadPresentationModule();
  const sorted = sortWorkbenchAgentsForDisplay([
    { provider_id: "codex_cli", available: false },
    { provider_id: "kimi_cli", available: true },
    { provider_id: "claude_cli", available: false },
    { provider_id: "codex_sdk", available: true }
  ]);

  assert.deepEqual(
    sorted.map((agent) => agent.provider_id),
    ["kimi_cli", "codex_sdk", "codex_cli", "claude_cli"]
  );
});

let presentationModulePromise;

function loadPresentationModule() {
  presentationModulePromise ||= loadTsModule("../src/agentProviderPresentation.ts");
  return presentationModulePromise;
}

async function loadTsModule(relativePath) {
  const source = readFileSync(new URL(relativePath, import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2020
    }
  });
  const dir = mkdtempSync(join(tmpdir(), "drawai-agent-provider-presentation-"));
  const modulePath = join(dir, `${relativePath.split("/").at(-1).replace(/\.ts$/, "")}.mjs`);
  writeFileSync(modulePath, outputText);
  return import(pathToFileURL(modulePath).href);
}
