import { copyFile, rename } from "node:fs/promises";
import path from "node:path";
const directory = path.resolve(process.argv[2] || "dist");
await copyFile(new URL("./data/visual-reference-templates.json", import.meta.url), path.join(directory, "template-catalog.json"));
if (process.argv.includes("--index")) await rename(path.join(directory, "templates.html"), path.join(directory, "index.html"));
console.log(`Standalone template catalog: ${directory}`);
