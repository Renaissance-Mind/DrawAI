import { readFile } from "node:fs/promises";
import { dispatch, TOOLS } from "./server.mjs";
const [name, source = "{}"] = process.argv.slice(2);
if (!name) throw new Error(`Usage: node templates/cli.mjs <${TOOLS.map((tool) => tool.name).join("|")}> <JSON|@file>`);
const args = JSON.parse(source.startsWith("@") ? await readFile(source.slice(1), "utf8") : source);
console.log(JSON.stringify(await dispatch(name, args), null, 2));
