import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import test from "node:test";
import ts from "../node_modules/typescript/lib/typescript.js";

test("node artifact selection uses the declared primary artifact", async () => {
  const { defaultWorkflowNodeArtifactId } = await loadSelectionModule();

  assert.equal(
    defaultWorkflowNodeArtifactId({
      primary_artifact_id: "output:semantic.svg",
      artifacts: [
        artifact({ artifact_id: "output:rendered.png", kind: "image", role: "preview", url: "/rendered.png" }),
        artifact({ artifact_id: "output:semantic.svg", kind: "svg", role: "accepted", url: "/semantic.svg" })
      ]
    }),
    "output:semantic.svg"
  );
});

test("node artifact selection exposes Agent log only when it is an artifact", async () => {
  const { defaultWorkflowNodeArtifactId, selectableWorkflowNodeArtifacts } = await loadSelectionModule();
  const artifacts = [
    artifact({
      artifact_id: "agent_log:timeline",
      kind: "agent_log",
      role: "log",
      source: "agent_log",
      url: ""
    })
  ];

  assert.equal(selectableWorkflowNodeArtifacts(artifacts).length, 1);
  assert.equal(defaultWorkflowNodeArtifactId({ primary_artifact_id: "agent_log:timeline", artifacts }), "agent_log:timeline");
});

test("node artifact selection ignores missing log files that are not declared artifacts", async () => {
  const { defaultWorkflowNodeArtifactId, selectableWorkflowNodeArtifacts } = await loadSelectionModule();
  const artifacts = [
    artifact({
      artifact_id: "agent_log:missing-file",
      kind: "agent_log",
      role: "log",
      source: "agent_log",
      exists: false,
      url: ""
    })
  ];

  assert.deepEqual(selectableWorkflowNodeArtifacts(artifacts), []);
  assert.equal(defaultWorkflowNodeArtifactId({ primary_artifact_id: "", artifacts }), "");
});

function artifact(overrides = {}) {
  return {
    artifact_id: "artifact",
    kind: "file",
    role: "output",
    source: "output",
    label: "artifact",
    relative_path: "artifact",
    exists: true,
    media_type: "text/plain",
    size_bytes: 1,
    updated_at: null,
    url: "/artifact",
    ...overrides
  };
}

let selectionModulePromise;

function loadSelectionModule() {
  selectionModulePromise ||= loadTsModule("../src/nodeArtifactSelection.ts");
  return selectionModulePromise;
}

async function loadTsModule(relativePath) {
  const source = readFileSync(new URL(relativePath, import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2020
    }
  });
  const dir = mkdtempSync(join(tmpdir(), "drawai-node-artifact-selection-"));
  const modulePath = join(dir, `${relativePath.split("/").at(-1).replace(/\.ts$/, "")}.mjs`);
  writeFileSync(modulePath, outputText);
  return import(pathToFileURL(modulePath).href);
}
