import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import test from "node:test";
import ts from "../node_modules/typescript/lib/typescript.js";

test("agent picker choices include only available agents and keep current first", async () => {
  const { workbenchAgentPickerChoices } = await loadSelectionModule();

  const choices = workbenchAgentPickerChoices(
    [
      agent({ provider_id: "codex_cli", label: "Codex CLI", available: true }),
      agent({ provider_id: "kimi_cli", label: "Kimi", available: true }),
      agent({ provider_id: "claude_cli", label: "Claude", available: false })
    ],
    "kimi_cli"
  );

  assert.deepEqual(
    choices.map((item) => item.provider_id),
    ["kimi_cli", "codex_cli"]
  );
  assert.equal(choices[0].selected, true);
});

test("settings UI selects the current Agent from overview instead of the Agent page", () => {
  const source = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");

  assert.match(source, /aria-label="选择当前 Agent"/);
  assert.match(source, /saveSettings\(\{ agentSettingsOverride: nextDraft \}\)/);
  assert.match(source, /settings-agent-picker/);
  assert.doesNotMatch(source, /aria-label="保存当前 Agent"/);
  assert.doesNotMatch(source, /<span>全局 Agent<\/span>/);
});

test("settings navigation keeps overview above engine and node groups", () => {
  const source = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
  const navBlock = source.match(/const WORKBENCH_SETTINGS_NAV_SECTIONS[\s\S]*?const BOARD_NAV_ITEMS/)?.[0] || "";

  assert.ok(navBlock.indexOf('{ id: "overview"') < navBlock.indexOf('label: "引擎"'));
  assert.ok(navBlock.indexOf('label: "引擎"') < navBlock.indexOf('label: "节点"'));
  assert.doesNotMatch(navBlock, /label:\s*"工作空间"/);
  assert.doesNotMatch(navBlock, /label:\s*"运行"/);
  assert.match(source, /\{section\.label && <div className="settings-nav-heading">\{section\.label\}<\/div>\}/);
});

test("settings overview and Agent cards use provider icons and bottom-aligned actions", () => {
  const source = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
  const css = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");

  assert.match(source, /const selectedAgentIcon = selectedAgent \? agentProviderIconForId\(selectedAgent\.provider_id\) : null;/);
  assert.match(source, /className=\{`settings-overview-agent-icon\$\{selectedAgentIcon \? " settings-provider-logo-mini" : ""\}`\}/);
  assert.match(source, /selectedAgentIcon \? <img src=\{selectedAgentIcon\.icon_url\} alt="" \/> : <SettingsNavIcon icon="agent" \/>/);
  assert.match(source, /<div className="settings-model-card-bottom">[\s\S]*?<dl className="settings-model-meta">[\s\S]*?<button type="button" className="settings-model-action"/);
  assert.match(css, /\.settings-model-card-bottom\s*\{[\s\S]*?grid-template-columns:\s*minmax\(0,\s*1fr\) auto;/);
  assert.match(css, /\.settings-model-action\s*\{[\s\S]*?align-self:\s*end;/);
});

let selectionModulePromise;

function loadSelectionModule() {
  selectionModulePromise ||= loadTsModule("../src/settingsAgentSelection.ts");
  return selectionModulePromise;
}

function agent(overrides) {
  return {
    provider_id: "codex_sdk",
    label: "Codex SDK",
    kind: "sdk",
    available: true,
    status: "ok",
    detail: "",
    fix: "",
    executable_path: "",
    command: [],
    version: "",
    auth: { available: true, detail: "" },
    workflow_provider_id: "codex_sdk",
    pipeline_agent: "codex-python-sdk-controlled",
    description: "",
    ...overrides
  };
}

async function loadTsModule(relativePath) {
  const source = readFileSync(new URL(relativePath, import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2020
    }
  });
  const dir = mkdtempSync(join(tmpdir(), "drawai-settings-agent-selection-"));
  const modulePath = join(dir, `${relativePath.split("/").at(-1).replace(/\.ts$/, "")}.mjs`);
  writeFileSync(modulePath, outputText);
  return import(pathToFileURL(modulePath).href);
}
