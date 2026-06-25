import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import test from "node:test";
import ts from "../node_modules/typescript/lib/typescript.js";

test("running generation tasks render placeholder tiles and block batch submit", async () => {
  const { imageGenPanelActions, imageGenVisibleTiles } = await loadTsModule("../src/imageGenState.ts");
  const tasks = [
    imageTask({
      id: "task-1",
      status: "running",
      expectedCount: 3,
      images: []
    })
  ];

  const tiles = imageGenVisibleTiles(tasks);
  const actions = imageGenPanelActions(tasks, "off", []);

  assert.equal(tiles.length, 3);
  assert.deepEqual(tiles.map((tile) => tile.status), ["running", "running", "running"]);
  assert.equal(actions.canSubmit, false);
  assert.equal(actions.submitCount, 0);
});

test("batch submit uses all completed images after every generation finishes", async () => {
  const { imageGenPanelActions, imageGenVisibleTiles } = await loadTsModule("../src/imageGenState.ts");
  const tasks = [
    imageTask({
      id: "task-1",
      status: "completed",
      expectedCount: 2,
      images: [generatedImage("img-1"), generatedImage("img-2")]
    }),
    imageTask({
      id: "task-2",
      status: "failed",
      expectedCount: 1,
      images: []
    })
  ];

  const tiles = imageGenVisibleTiles(tasks);
  const actions = imageGenPanelActions(tasks, "off", []);

  assert.equal(tiles.length, 3);
  assert.deepEqual(actions.submitImageIds, ["img-1", "img-2"]);
  assert.equal(actions.canSubmit, true);
  assert.equal(actions.canRegenerate, false);
});

test("selection mode disables submit and regenerate until completed images are selected", async () => {
  const { imageGenPanelActions } = await loadTsModule("../src/imageGenState.ts");
  const tasks = [
    imageTask({
      id: "task-1",
      status: "completed",
      expectedCount: 2,
      images: [generatedImage("img-1"), generatedImage("img-2")]
    })
  ];

  const empty = imageGenPanelActions(tasks, "selecting", []);
  const selected = imageGenPanelActions(tasks, "selecting", ["img-2", "missing"]);

  assert.equal(empty.canSubmit, false);
  assert.equal(empty.canRegenerate, false);
  assert.equal(empty.selectIcon, "x");
  assert.deepEqual(selected.submitImageIds, ["img-2"]);
  assert.equal(selected.canSubmit, true);
  assert.equal(selected.canRegenerate, true);
});

async function loadTsModule(relativePath) {
  const source = readFileSync(new URL(relativePath, import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2020
    }
  });
  const dir = mkdtempSync(join(tmpdir(), "drawai-imagegen-state-"));
  const modulePath = join(dir, `${relativePath.split("/").at(-1).replace(/\.ts$/, "")}.mjs`);
  writeFileSync(modulePath, outputText);
  return import(pathToFileURL(modulePath).href);
}

function imageTask({ id, status, expectedCount, images }) {
  return {
    id,
    status,
    title: id,
    prompt: `Prompt ${id}`,
    expectedCount,
    images,
    error: "",
    createdAt: "2026-06-24T00:00:00Z"
  };
}

function generatedImage(id) {
  return {
    id,
    taskId: "task-1",
    status: "completed",
    url: `https://example.test/${id}.png`,
    size: "2048x1152",
    resolution: "2k",
    quality: "high",
    format: "png",
    transparent: false,
    provider: "codex",
    prompt: "Prompt"
  };
}
