import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";

const compiled = ts.transpileModule(
  await readFile(
    new URL("../../src/studio/workflow.ts", import.meta.url),
    "utf8",
  ),
  {
    compilerOptions: {
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2020,
    },
  },
).outputText;
const { primaryAction, currentDeck, taskSlideIds } = await import(
  `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`
);

function project(count = 1) {
  return {
    brief: "",
    input_revision: 3,
    assets: [],
    references: [],
    tasks: [],
    slides: Array.from({ length: count }, (_, index) => ({
      id: `page-${index + 1}`,
      content: "准确的页面文字",
      revision: 2,
      current_image_id: null,
      current_pptx_id: null,
      content_changed: false,
    })),
  };
}
function readyImages(value) {
  value.slides.forEach((page) => {
    page.current_image_id = `image-${page.id}`;
  });
  return value;
}
function finishedDeck(value) {
  const task = {
    id: "export-1",
    kind: "export_deck",
    status: "completed",
    project_input_revision: value.input_revision,
    slide_ids: value.slides.map((page) => page.id),
    slide_revisions: Object.fromEntries(
      value.slides.map((page) => [page.id, page.revision]),
    ),
    source_image_ids: Object.fromEntries(
      value.slides.map((page) => [page.id, page.current_image_id]),
    ),
  };
  const asset = {
    id: "deck-1",
    kind: "pptx",
    slide_id: null,
    task_id: task.id,
  };
  value.tasks.push(task);
  value.assets.push(asset);
  return value;
}
const action = (
  value,
  selected = [],
  content = value.slides[0].content,
  dirty = false,
) => primaryAction(value, value.slides[0].id, selected, content, "", dirty);

test("a new page directs users to content before generation", () => {
  const value = project();
  value.slides[0].content = "";
  assert.equal(action(value).kind, "generate");
  assert.equal(action(value).disabled, true);
  assert.match(action(value).description, /填写/);
  assert.equal(action(value, [], "已填写的准确内容").disabled, false);
  value.references.push({ role: "content" });
  assert.equal(action(value).disabled, false);
});

test("the single-page next step progresses from conversion to actual PPTX download", () => {
  const value = readyImages(project());
  assert.equal(action(value).kind, "convert");
  assert.deepEqual(action(value).slideIds, ["page-1"]);
  value.assets.push({ id: "page-pptx", kind: "pptx", slide_id: "page-1" });
  value.slides[0].current_pptx_id = "page-pptx";
  assert.equal(action(value).kind, "download");
  assert.equal(action(value).asset.id, "page-pptx");
});

test("all ready pages offer one whole-deck action, and a verified current deck offers download", () => {
  const value = readyImages(project(8));
  assert.equal(action(value).kind, "export_deck");
  assert.equal(action(value).slideIds.length, 8);
  finishedDeck(value);
  assert.equal(currentDeck(value).id, "deck-1");
  assert.equal(action(value).kind, "download");
  assert.equal(action(value).asset.id, "deck-1");
});

test("content edits and unsaved requirements return the next step to image generation", () => {
  const value = finishedDeck(readyImages(project(3)));
  value.slides[0].content_changed = true;
  assert.equal(action(value).kind, "generate");
  value.slides[0].content_changed = false;
  assert.equal(action(value, [], "新的内容", true).kind, "generate");
  assert.match(action(value, [], "新的内容", true).label, /更新/);
});

test("batch selection keeps its explicit scope instead of silently exporting the whole project", () => {
  const value = readyImages(project(4));
  const selected = action(value, ["page-3", "page-1"]);
  assert.equal(selected.kind, "generate");
  assert.deepEqual(selected.slideIds, ["page-1", "page-3"]);
  assert.match(selected.label, /2 页/);
  assert.deepEqual(taskSlideIds("generate", value, ["page-3"], ["page-2"]), [
    "page-2",
  ]);
  assert.deepEqual(
    taskSlideIds("export_deck", value, ["page-3"]),
    value.slides.map((page) => page.id),
  );
  assert.deepEqual(taskSlideIds("prepare_reference", value, ["page-3"]), []);
});

test("a relevant running or waiting task becomes the next-step entry without submitting another task", () => {
  const value = project(2);
  const task = {
    id: "work-1",
    kind: "generate",
    status: "running",
    slide_ids: ["page-1"],
    message: "正在生成",
  };
  value.tasks.push(task);
  assert.equal(action(value).kind, "busy");
  assert.equal(action(value).task.id, "work-1");
  assert.equal(primaryAction(value, "page-2", [], "内容", "").kind, "generate");
  task.status = "draft";
  assert.match(action(value).label, /待发送/);
});

test("changed images, order, page revisions, references or unfinished work never offer an old deck as current", () => {
  for (const change of [
    (value) => {
      value.slides[0].current_image_id = "new-version";
    },
    (value) => {
      value.slides.reverse();
    },
    (value) => {
      value.slides[0].revision++;
    },
    (value) => {
      value.input_revision++;
    },
    (value) => {
      value.tasks[0].status = "running";
    },
    (value) => {
      delete value.tasks[0].source_image_ids;
    },
  ]) {
    const value = finishedDeck(readyImages(project(3)));
    change(value);
    assert.equal(currentDeck(value), undefined);
    assert.notEqual(action(value).kind, "download");
  }
});
