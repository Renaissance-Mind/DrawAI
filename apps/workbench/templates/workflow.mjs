// Compatibility bridge: all operations run the installed DrawAI core.
import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = fileURLToPath(new URL("../../..", import.meta.url));
const python = process.env.DRAWAI_PYTHON || [".venv/bin/python", ".venv/Scripts/python.exe"].map(p => path.join(root, p)).find(existsSync) || "python3";
export async function coreTool(name, args) {
  return new Promise((resolve, reject) => {
    const env = { ...process.env, PYTHONPATH: [path.join(root, "src"), process.env.PYTHONPATH].filter(Boolean).join(path.delimiter) };
    const child = execFile(python, ["-m", "drawai.cli", "session", "tool", name, "-"], { cwd: root, env, maxBuffer: 8 * 1024 * 1024, encoding: "utf8" }, (error, stdout, stderr) => {
      if (error) reject(new Error(stderr || error.message));
      else resolve(JSON.parse(stdout));
    });
    child.stdin.end(JSON.stringify(args));
  });
}
export const planWorkflow = request => coreTool("drawai_plan", { request });
export const flowAction = args => coreTool("drawai_flow", args);
