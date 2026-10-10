import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";
const source = await readFile(
  new URL("../../src/studio/hostContext.ts", import.meta.url),
  "utf8",
);
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ESNext,
    target: ts.ScriptTarget.ES2020,
  },
}).outputText;
const { projectIdFromToolInput, projectIdFromToolResult } = await import(
  `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`
);
const id = "project_db740a5bc2e74202";

test("the host-selected project survives both standard MCP and compatibility outputs", () => {
  assert.equal(projectIdFromToolInput({ arguments: { project_id: id } }), id);
  assert.equal(projectIdFromToolInput({ project_id: id }), id);
  assert.equal(
    projectIdFromToolResult({ structuredContent: { project: { id } } }),
    id,
  );
  assert.equal(
    projectIdFromToolResult({
      view: { project_id: id },
      project: { id: "project_0000000000000000" },
    }),
    id,
  );
});

test("unrelated or malformed notifications do not change the selected project", () => {
  for (const value of [
    null,
    {},
    { project_id: "../other" },
    { project: { id: "external" } },
    { structuredContent: null },
  ]) {
    assert.equal(projectIdFromToolInput(value), undefined);
    assert.equal(projectIdFromToolResult(value), undefined);
  }
});
