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
  assert.match(source, /settings-agent-picker/);
  assert.doesNotMatch(source, /<span>全局 Agent<\/span>/);
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
