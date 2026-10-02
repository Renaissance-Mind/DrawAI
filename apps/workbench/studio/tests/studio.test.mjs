import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, readdir, readFile, writeFile, rm } from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import { createHash } from "node:crypto";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { unzipSync } from "fflate";
import { StudioStore } from "../store.mjs";
import { startHttp } from "../server.mjs";
import { loadCatalog, searchTemplates } from "../catalog.mjs";

const sourceImage = new URL(
  "../../../../skills/drawai-ppt/assets/demo/demo_figure.png",
  import.meta.url,
);
const serverPath = new URL("../server.mjs", import.meta.url).pathname;
async function workspace(t) {
  const root = await mkdtemp(path.join(os.tmpdir(), "drawai-studio-test-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  return new StudioStore(root, path.join(root, "downloads"));
}
async function imageBytes() {
  return readFile(sourceImage);
}

test("the imported library preserves real assets, recipes and provenance without duplicate IDs", async () => {
  const { templates, source } = await loadCatalog();
  assert.equal(new Set(templates.map((t) => t.id)).size, templates.length);
  assert.ok(templates.length >= 629);
  assert.equal(source.imported_cards, 609);
  assert.equal(templates.filter((t) => t.assets.length).length, 429);
  for (const t of templates) {
    assert.ok(t.prompt_recipe.trim());
    for (const a of t.assets) {
      assert.match(a.sha256, /^[a-f0-9]{64}$/);
      assert.match(
        a.original_url,
        /^https:\/\/assets\.visualize\.renaissancemind\.ai\//,
      );
    }
  }
  const result = await searchTemplates({
    query: "ablation",
    with_images: true,
  });
  assert.ok(
    result.templates.some(
      (t) => t.id === "academic_research_ablation_study_page",
    ),
  );
});

test("project ordering, content edits and persistence survive a new store instance", async (t) => {
  const store = await workspace(t);
  const { project } = await store.create({ title: "Paper presentation" });
  const one = project.slides[0].id;
  const two = (
    await store.projectAction({
      action: "add_slide",
      project_id: project.id,
      title: "Method",
    })
  ).slide_id;
  await store.projectAction({
    action: "update_slide",
    project_id: project.id,
    slide_id: one,
    title: "Overview",
    content: "Verified source text",
    expected_revision: 1,
  });
  await assert.rejects(
    store.projectAction({
      action: "update_slide",
      project_id: project.id,
      slide_id: one,
      content: "Stale editor",
      expected_revision: 1,
    }),
    /another window/,
  );
  await store.projectAction({
    action: "reorder",
    project_id: project.id,
    slide_ids: [two, one],
  });
  const reloaded = await new StudioStore(store.root).read(project.id);
  assert.deepEqual(
    reloaded.slides.map((s) => s.id),
    [two, one],
  );
  assert.equal(reloaded.slides[1].content, "Verified source text");
  await assert.rejects(
    store.projectAction({
      action: "reorder",
      project_id: project.id,
      slide_ids: [one, one],
    }),
    /exactly once/,
  );
});

test("concurrent project mutations keep both writers’ changes", async (t) => {
  const store = await workspace(t);
  const { project } = await store.create({ title: "Concurrent project" });
  const second = new StudioStore(store.root);
  await Promise.all(
    Array.from({ length: 8 }, (_, i) =>
      (i % 2 ? store : second).projectAction({
        action: "add_slide",
        project_id: project.id,
        title: `Page ${i}`,
      }),
    ),
  );
  assert.equal((await store.read(project.id)).slides.length, 9);
});

test("multiple reference roles and page scoping are preserved in the immutable task request", async (t) => {
  const store = await workspace(t);
  const { project } = await store.create({ title: "References" });
  const page = project.slides[0];
  const next = (
    await store.projectAction({ action: "add_slide", project_id: project.id })
  ).slide_id;
  for (const role of ["content", "structure", "ppt_template"])
    await store.referenceAction({
      action: "upload",
      project_id: project.id,
      role,
      filename: `${role}.png`,
      data_base64: (await imageBytes()).toString("base64"),
    });
  await store.referenceAction({
    action: "upload",
    project_id: project.id,
    role: "style",
    slide_ids: [next],
    filename: "second-page.png",
    data_base64: (await imageBytes()).toString("base64"),
  });
  const { task, request } = await store.createTask({
    project_id: project.id,
    kind: "generate",
    slide_ids: [page.id],
  });
  assert.equal(request.references.length, 3);
  assert.deepEqual(
    request.references.map((r) => r.role),
    ["content", "structure", "ppt_template"],
  );
  for (const ref of request.references)
    assert.ok((await readFile(ref.files[0])).length > 0);
  assert.equal(task.status, "draft");
  assert.ok(task.prompt.includes(task.request_path));
  await store.projectAction({
    action: "update_slide",
    project_id: project.id,
    slide_id: page.id,
    content: "Changed later",
  });
  assert.equal(
    JSON.parse(await readFile(task.request_path, "utf8")).slides[0].content,
    "",
  );
});

test("tasks require real output files and do not overwrite a newer slide revision", async (t) => {
  const store = await workspace(t);
  const { project } = await store.create({ title: "Generation" });
  const page = project.slides[0];
  const { task } = await store.createTask({
    project_id: project.id,
    kind: "generate",
    slide_ids: [page.id],
  });
  await assert.rejects(
    store.taskAction({
      action: "update",
      project_id: project.id,
      task_id: task.id,
      status: "completed",
    }),
    /no verified result/,
  );
  await assert.rejects(
    store.createTask({
      project_id: project.id,
      kind: "generate",
      slide_ids: [page.id],
    }),
    /active task/,
  );
  await store.projectAction({
    action: "update_slide",
    project_id: project.id,
    slide_id: page.id,
    content: "A newer instruction",
  });
  const registered = await store.artifactAction({
    action: "register",
    project_id: project.id,
    task_id: task.id,
    slide_id: page.id,
    kind: "image",
    source_path: sourceImage.pathname,
  });
  assert.equal(registered.project.slides[0].current_image_id, null);
  await store.taskAction({
    action: "update",
    project_id: project.id,
    task_id: task.id,
    status: "completed",
    message: "Verified real image output",
  });
  assert.equal((await store.read(project.id)).tasks[0].status, "completed");
  const exported = await store.artifactAction({
    action: "archive",
    project_id: project.id,
  });
  const entries = unzipSync(Buffer.from(exported.data_base64, "base64"));
  assert.ok(entries["project.json"]);
  assert.ok(entries[registered.asset.relative_path]);
  assert.deepEqual(
    JSON.parse(
      Buffer.from(entries[`tasks/${task.id}/request.json`]).toString("utf8"),
    ),
    JSON.parse(await readFile(task.request_path, "utf8")),
  );
});

test("cancellation and changed artifact bytes cannot be reported as successful completion", async (t) => {
  const store = await workspace(t);
  const { project } = await store.create({ title: "Verification" });
  const page = project.slides[0];
  const { task } = await store.createTask({
    project_id: project.id,
    kind: "generate",
    slide_ids: [page.id],
  });
  const { asset } = await store.artifactAction({
    action: "register",
    project_id: project.id,
    task_id: task.id,
    slide_id: page.id,
    kind: "image",
    source_path: sourceImage.pathname,
  });
  await writeFile(
    path.join(store.projectPath(project.id), asset.relative_path),
    "broken",
  );
  await assert.rejects(
    store.taskAction({
      action: "update",
      project_id: project.id,
      task_id: task.id,
      status: "completed",
    }),
    /changed on disk/,
  );
  await store.taskAction({
    action: "cancel",
    project_id: project.id,
    task_id: task.id,
  });
  await assert.rejects(
    store.artifactAction({
      action: "register",
      project_id: project.id,
      task_id: task.id,
      slide_id: page.id,
      kind: "image",
      source_path: sourceImage.pathname,
    }),
    /finished task/,
  );
});

test("late message acknowledgment and cancellation cannot regress completed work", async (t) => {
  const store = await workspace(t);
  const { project } = await store.create({ title: "Message race" });
  const page = project.slides[0];
  const { task } = await store.createTask({
    project_id: project.id,
    kind: "generate",
    slide_ids: [page.id],
  });
  await store.taskAction({
    action: "update",
    project_id: project.id,
    task_id: task.id,
    status: "running",
    message: "Actually running",
  });
  const ack = await store.taskAction({
    action: "update",
    project_id: project.id,
    task_id: task.id,
    status: "submitted",
  });
  assert.equal(ack.task.status, "running");
  assert.equal(ack.task.message, "Actually running");
  await store.artifactAction({
    action: "register",
    project_id: project.id,
    task_id: task.id,
    slide_id: page.id,
    kind: "image",
    source_path: sourceImage.pathname,
  });
  await store.taskAction({
    action: "update",
    project_id: project.id,
    task_id: task.id,
    status: "completed",
  });
  assert.equal(
    (
      await store.taskAction({
        action: "update",
        project_id: project.id,
        task_id: task.id,
        status: "submitted",
      })
    ).task.status,
    "completed",
  );
  const cancelled = await store.taskAction({
    action: "cancel",
    project_id: project.id,
    task_id: task.id,
  });
  assert.equal(cancelled.task.status, "completed");
});

test("duplicating a slide preserves its real image and scoped references with independent IDs", async (t) => {
  const store = await workspace(t);
  const { project } = await store.create({ title: "Duplication" });
  const page = project.slides[0];
  const { asset } = await store.artifactAction({
    action: "import_image",
    project_id: project.id,
    slide_id: page.id,
    filename: "source.png",
    data_base64: (await imageBytes()).toString("base64"),
  });
  await store.referenceAction({
    action: "upload",
    project_id: project.id,
    role: "style",
    slide_ids: [page.id],
    filename: "style.png",
    data_base64: (await imageBytes()).toString("base64"),
  });
  const result = await store.projectAction({
    action: "duplicate_slide",
    project_id: project.id,
    slide_id: page.id,
  });
  const duplicate = result.project.slides[1];
  assert.notEqual(duplicate.current_image_id, asset.id);
  assert.equal(
    (await store.readAsset(project.id, duplicate.current_image_id)).asset
      .sha256,
    asset.sha256,
  );
  assert.deepEqual(result.project.references[0].slide_ids, [
    page.id,
    duplicate.id,
  ]);
});

test("a result cannot replace an image explicitly selected while generation was running", async (t) => {
  const store = await workspace(t);
  const { project } = await store.create({ title: "Image race" });
  const page = project.slides[0];
  const { task } = await store.createTask({
    project_id: project.id,
    kind: "generate",
    slide_ids: [page.id],
  });
  const { asset } = await store.artifactAction({
    action: "import_image",
    project_id: project.id,
    slide_id: page.id,
    filename: "selected.png",
    data_base64: (await imageBytes()).toString("base64"),
  });
  const registered = await store.artifactAction({
    action: "register",
    project_id: project.id,
    task_id: task.id,
    slide_id: page.id,
    kind: "image",
    source_path: sourceImage.pathname,
  });
  assert.equal(registered.project.slides[0].current_image_id, asset.id);
  assert.ok(registered.task === undefined);
});

test("browser downloads return exact registered bytes and reject unrelated origins", async (t) => {
  const store = await workspace(t);
  const { project } = await store.create({ title: "Download" });
  const original = await imageBytes();
  const { asset } = await store.artifactAction({
    action: "import_image",
    project_id: project.id,
    slide_id: project.slides[0].id,
    filename: "页面.png",
    data_base64: original.toString("base64"),
  });
  const server = await startHttp(store, 0);
  t.after(() => new Promise((resolve) => server.close(resolve)));
  const url = `http://127.0.0.1:${server.address().port}/api/studio/files/${project.id}/${asset.id}`;
  const response = await fetch(url);
  assert.equal(response.status, 200);
  assert.ok(
    response.headers
      .get("content-disposition")
      .includes(encodeURIComponent("页面.png")),
  );
  assert.deepEqual(Buffer.from(await response.arrayBuffer()), original);
  assert.equal(
    (await fetch(url, { headers: { Origin: "https://unrelated.example" } }))
      .status,
    403,
  );
  const saveFromBrowser = await fetch(`${url.split("/api/")[0]}/api/studio/call`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: "drawai_artifact",
      arguments: { action: "save_download", project_id: project.id, asset_id: asset.id },
    }),
  });
  assert.equal(saveFromBrowser.status, 400);
  assert.match((await saveFromBrowser.json()).error, /MCP tool or CLI/);
});

test("local downloads preserve registered bytes and cannot overwrite files or choose another path", async (t) => {
  const store = await workspace(t);
  const { project } = await store.create({ title: "Download integrity" });
  const bytes = await imageBytes();
  const { asset } = await store.artifactAction({
    action: "import_image",
    project_id: project.id,
    slide_id: project.slides[0].id,
    filename: "../页面.png",
    data_base64: bytes.toString("base64"),
  });
  await mkdir(store.downloadsRoot, { recursive: true });
  const existing = path.join(store.downloadsRoot, "页面.png");
  await writeFile(existing, bytes);
  const receipts = await Promise.all([0, 1].map(() => store.artifactAction({
    action: "save_download",
    project_id: project.id,
    asset_id: asset.id,
    filename: "../../redirect.png",
    source_path: "/not-a-project-asset.png",
  })));
  assert.equal(new Set(receipts.map((r) => r.saved_path)).size, 2);
  for (const receipt of receipts) {
    assert.equal(path.dirname(receipt.saved_path), store.downloadsRoot);
    assert.match(receipt.filename, /^页面 \([12]\)\.png$/);
    assert.equal(receipt.sha256, asset.sha256);
    assert.equal(receipt.size, bytes.length);
    assert.deepEqual(await readFile(receipt.saved_path), bytes);
  }
  assert.deepEqual(await readFile(existing), bytes);
  const current = await store.read(project.id);
  await writeFile(await store.assetPath(current, asset.id), Buffer.from("changed bytes"));
  await assert.rejects(store.artifactAction({
    action: "save_download", project_id: project.id, asset_id: asset.id,
  }), /no longer match/);
  assert.equal((await readdir(store.downloadsRoot)).length, 3);
});

test("project download saves a real archive with source assets and immutable requests", async (t) => {
  const store = await workspace(t);
  const { project } = await store.create({ title: "项目归档" });
  const bytes = await imageBytes();
  const { asset } = await store.artifactAction({
    action: "import_image", project_id: project.id, slide_id: project.slides[0].id,
    filename: "页面.png", data_base64: bytes.toString("base64"),
  });
  const { task } = await store.taskAction({
    action: "create", project_id: project.id, kind: "generate", slide_ids: [project.slides[0].id],
  });
  const receipt = await store.artifactAction({ action: "save_download", project_id: project.id });
  const archive = await readFile(receipt.saved_path);
  assert.equal(createHash("sha256").update(archive).digest("hex"), receipt.sha256);
  const files = unzipSync(archive);
  assert.deepEqual(Buffer.from(files[asset.relative_path]), bytes);
  assert.equal(JSON.parse(Buffer.from(files["project.json"]).toString()).id, project.id);
  assert.ok(files[`tasks/${task.id}/request.json`]);
});

test("stdio MCP exposes the real workbench resource and round-trips project state", async (t) => {
  const store = await workspace(t);
  const client = new Client({
    name: "drawai-studio-integration-test",
    version: "1.0.0",
  });
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: [serverPath],
    env: {
      ...process.env,
      DRAWAI_STUDIO_HOME: store.root,
      DRAWAI_STUDIO_DOWNLOADS_DIR: store.downloadsRoot,
    },
  });
  t.after(() => client.close());
  await client.connect(transport);
  const listed = await client.listTools();
  const uiUri = listed.tools.find(
    (tool) => tool.name === "drawai_open_workbench",
  )._meta.ui.resourceUri;
  assert.match(uiUri, /^ui:\/\/drawai\/workbench-[a-f0-9]{16}\.html$/);
  const created = await client.callTool({
    name: "drawai_project",
    arguments: { action: "create", title: "MCP project" },
  });
  assert.equal(created.structuredContent.project.title, "MCP project");
  const bytes = await imageBytes();
  const imported = await client.callTool({
    name: "drawai_artifact",
    arguments: {
      action: "import_image", project_id: created.structuredContent.project.id,
      slide_id: created.structuredContent.project.slides[0].id,
      filename: "MCP download.png", data_base64: bytes.toString("base64"),
    },
  });
  const downloaded = await client.callTool({
    name: "drawai_artifact",
    arguments: {
      action: "save_download", project_id: created.structuredContent.project.id,
      asset_id: imported.structuredContent.asset.id,
    },
  });
  assert.equal(downloaded.isError, undefined);
  assert.deepEqual(await readFile(downloaded.structuredContent.saved_path), bytes);
  assert.equal(downloaded.structuredContent.sha256, imported.structuredContent.asset.sha256);
  const opened = await client.callTool({
    name: "drawai_open_workbench",
    arguments: { project_id: created.structuredContent.project.id },
  });
  assert.equal(
    opened.structuredContent.project.id,
    created.structuredContent.project.id,
  );
  assert.equal(opened._meta.ui.resourceUri, uiUri);
  assert.equal((await client.listResources()).resources[0].uri, uiUri);
  const resource = await client.readResource({ uri: uiUri });
  assert.equal(resource.contents[0].mimeType, "text/html;profile=mcp-app");
  const hash = createHash("sha256")
    .update(resource.contents[0].text)
    .digest("hex")
    .slice(0, 16);
  assert.equal(uiUri, `ui://drawai/workbench-${hash}.html`);
  assert.ok(resource.contents[0].text.includes("ui/message"));
  assert.ok(resource.contents[0].text.includes("视觉参考模板库"));
  assert.doesNotMatch(resource.contents[0].text, /<script\b[^>]*src=/);
});
