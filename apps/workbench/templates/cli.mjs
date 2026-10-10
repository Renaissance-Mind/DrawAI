import { readFile } from "node:fs/promises";
import { dispatch } from "./server.mjs";
const [name, source = "{}"] = process.argv.slice(2);
if (!name) throw new Error("Usage: node templates/cli.mjs <drawai_templates|drawai_show_templates|drawai_prepare_template> <JSON|@file>");
const args = JSON.parse(source.startsWith("@") ? await readFile(source.slice(1), "utf8") : source);
console.log(JSON.stringify(await dispatch(name, args), null, 2));
