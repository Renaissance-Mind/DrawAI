// Compatibility entry point for the unified Python installer.
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const python = process.env.DRAWAI_PYTHON || [".venv/bin/python", ".venv/Scripts/python.exe"].map(p => path.join(root,p)).find(existsSync) || "python3";
execFileSync(python, ["-m", "drawai.cli", "session", "install", "--host", "codex", ...process.argv.slice(2)], { cwd: root, env: { ...process.env, PYTHONPATH: [path.join(root,"src"), process.env.PYTHONPATH].filter(Boolean).join(path.delimiter) }, stdio: "inherit" });
