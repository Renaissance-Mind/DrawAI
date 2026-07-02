import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import test from "node:test";
import ts from "../node_modules/typescript/lib/typescript.js";

test("failed workflow nodes expose restart and failed-node retry actions", async () => {
  const { workflowNodeRerunActions } = await loadRerunModule();

  const actions = workflowNodeRerunActions({
    stage: "refine_elements",
    nodeId: "page_spec_refine",
    nodeState: "failed"
  });

  assert.deepEqual(
    actions.map((action) => ({ kind: action.kind, stage: action.stage, nodeId: action.nodeId || "" })),
    [
      { kind: "restart", stage: "refine_elements", nodeId: "" },
      { kind: "failed_node", stage: "refine_elements", nodeId: "page_spec_refine" }
    ]
  );
});

test("successful workflow nodes keep a single default restart action", async () => {
  const { workflowNodeRerunActions } = await loadRerunModule();

  const actions = workflowNodeRerunActions({
    stage: "refine_elements",
    nodeId: "page_spec_refine",
    nodeState: "done"
  });

  assert.deepEqual(
    actions.map((action) => ({ kind: action.kind, stage: action.stage, nodeId: action.nodeId || "" })),
    [{ kind: "restart", stage: "refine_elements", nodeId: "" }]
  );
});

let rerunModulePromise;

function loadRerunModule() {
  rerunModulePromise ||= loadTsModule("../src/workflowRerunActions.ts");
  return rerunModulePromise;
}

async function loadTsModule(relativePath) {
  const source = readFileSync(new URL(relativePath, import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2020
    }
  });
  const dir = mkdtempSync(join(tmpdir(), "drawai-workflow-rerun-actions-"));
  const modulePath = join(dir, `${relativePath.split("/").at(-1).replace(/\.ts$/, "")}.mjs`);
  writeFileSync(modulePath, outputText);
  return import(pathToFileURL(modulePath).href);
}
