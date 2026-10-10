import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { existsSync } from "node:fs";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../../..", import.meta.url));
const exec = promisify(execFile);
const python = process.env.DRAWAI_PYTHON || [".venv/bin/python", ".venv/Scripts/python.exe"].map((name) => path.join(root, name)).find(existsSync) || "python3";
const api = (process.env.DRAWAI_WORKBENCH_API_URL || "http://127.0.0.1:8890").replace(/\/$/, "");
const ui = process.env.DRAWAI_WORKBENCH_UI_URL || "http://127.0.0.1:5174/";

export async function planWorkflow(request) {
  const script = path.join(root, "skills/drawai-readme/scripts/plan.py");
  const input = JSON.stringify(request);
  const output = await new Promise((resolve, reject) => {
    const child = execFile(python, [script, "-"], { cwd: root, maxBuffer: 1024 * 1024, encoding: "utf8" }, (error, stdout, stderr) => {
      if (error) reject(new Error(stderr || error.message));
      else resolve(stdout);
    });
    child.stdin.end(input);
  });
  return JSON.parse(output);
}

async function call(url, options = {}) {
  const response = await fetch(url, { ...options, signal: AbortSignal.timeout(60000) });
  if (!response.ok) throw new Error(`Workbench HTTP ${response.status}: ${await response.text()}`);
  return response;
}

export async function flowAction(args) {
  if (args.action === "status" && !args.batch_id) return { ui_url: ui, health: await (await call(`${api}/api/health`)).json() };
  if (args.action === "submit") {
    if (!args.visual_manifest) throw new Error("visual_manifest is required");
    if (!path.isAbsolute(args.visual_manifest)) throw new Error("visual_manifest must be an absolute task path");
    await exec(python, [path.join(root, "skills/drawai-image2ppt/scripts/visual_deck.py"), "verify", args.visual_manifest], { cwd: root });
    const deck = JSON.parse(await readFile(args.visual_manifest, "utf8"));
    const form = new FormData();
    form.set("input_mode", "upload");
    form.set("name", args.name || deck.title || "DrawAI PPT");
    form.set("auto_start", "false");
    form.set("auto_run_svg_after_analysis", "true");
    for (const page of deck.pages) {
      const filename = `${String(page.order).padStart(4, "0")}-${path.basename(page.image)}`;
      form.append("files", new Blob([await readFile(page.image)]), filename);
    }
    const result = await (await call(`${api}/api/batches`, { method: "POST", body: form })).json();
    return { ...result, ui_url: ui, visual_manifest: path.resolve(args.visual_manifest), state: "queued" };
  }
  if (!args.batch_id || !/^batch_[a-zA-Z0-9]+$/.test(args.batch_id)) throw new Error("A batch_id from this task's Flow submission is required");
  if (args.action === "start") return { ui_url: ui, ...await (await call(`${api}/api/batches/${args.batch_id}/run`, { method: "POST" })).json() };
  if (args.action === "status") return { ui_url: ui, ...await (await call(`${api}/api/batches/${args.batch_id}`)).json() };
  if (args.action === "export") {
    if (!args.output_path) throw new Error("output_path is required");
    if (!path.isAbsolute(args.output_path) || path.extname(args.output_path).toLowerCase() !== ".pptx") throw new Error("output_path must be a new absolute .pptx task path");
    const target = path.resolve(args.output_path);
    if (existsSync(target)) throw new Error("Choose a new output file; existing files are not overwritten");
    const response = await call(`${api}/api/batches/${args.batch_id}/pptx`);
    const bytes = Buffer.from(await response.arrayBuffer());
    if (bytes.subarray(0, 2).toString() !== "PK") throw new Error("Workbench did not return a PPTX package");
    await mkdir(path.dirname(target), { recursive: true });
    await writeFile(target, bytes, { flag: "wx" });
    return { path: target, size: bytes.length, needs_validation: true };
  }
  throw new Error(`Unknown Flow action: ${args.action}`);
}
