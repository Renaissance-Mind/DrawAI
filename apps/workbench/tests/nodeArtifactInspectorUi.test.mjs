import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const appSource = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
const stylesSource = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");

test("node artifact viewer uses DAG node navigation in the top bar", () => {
  assert.match(appSource, /className="node-artifact-node-nav"/);
  assert.match(appSource, /aria-label="选择 DAG 节点"/);
  assert.match(appSource, /onSelectNode=\{\(nodeId\) => openWorkflowNodeArtifactCanvas\(nodeArtifactViewer\.case_id, nodeId\)\}/);
  assert.match(appSource, /buildWorkflowPreviewLayout\(template\)\.nodes\.forEach/);
});

test("node artifact viewer hides the artifact switch for a single output", () => {
  assert.match(appSource, /artifactItems\.length > 1 &&/);
  assert.doesNotMatch(appSource, /artifactItems\.length > 0 \?/);
});

test("node artifact navigation buttons are borderless with hover feedback", () => {
  assert.match(stylesSource, /\.node-artifact-nav-button\s*\{[\s\S]*?border: 0;/);
  assert.match(stylesSource, /\.node-artifact-nav-button:hover:not\(:disabled\)\s*\{/);
});
