#!/usr/bin/env node
import { readFile } from "node:fs/promises";
import { StudioStore } from "./store.mjs";
import { dispatch } from "./server.mjs";

const [name, argument] = process.argv.slice(2);
if (!name || name === "--help") {
  console.log(
    "Usage: node studio/cli.mjs <drawai_project|drawai_templates|drawai_reference|drawai_task|drawai_artifact> <JSON|@arguments.json>\nUses DRAWAI_STUDIO_HOME or ~/.local/share/drawai/studio.",
  );
} else {
  const args = JSON.parse(
    argument?.startsWith("@")
      ? await readFile(argument.slice(1), "utf8")
      : argument || "{}",
  );
  console.log(
    JSON.stringify(await dispatch(new StudioStore(), name, args), null, 2),
  );
}
