import { mkdir, readFile, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { createHash } from "node:crypto";
import path from "node:path";
import { findTemplate } from "./catalog.mjs";

async function saveFile(filename, bytes) {
  if (existsSync(filename)) {
    if (!(await readFile(filename)).equals(Buffer.from(bytes))) throw new Error(`File already exists with different content: ${filename}`);
    return;
  }
  await writeFile(filename, bytes, { flag: "wx" });
}

export async function prepareReference({ template_id, output_directory }) {
  if (!output_directory?.trim()) throw new Error("output_directory is required");
  const template = await findTemplate(template_id);
  const directory = path.join(path.resolve(output_directory), template.id.replace(/[^a-zA-Z0-9_-]/g, "_"));
  await mkdir(directory, { recursive: true });
  const images = [];
  for (const [index, asset] of template.assets.entries()) {
    const url = new URL(asset.original_url);
    if (url.protocol !== "https:" || url.hostname !== "assets.visualize.renaissancemind.ai") throw new Error(`Unsupported template asset source: ${template.id}`);
    const response = await fetch(url, { signal: AbortSignal.timeout(45000) });
    if (!response.ok) throw new Error(`Template image HTTP ${response.status}: ${template.id}`);
    const bytes = Buffer.from(await response.arrayBuffer());
    const sha256 = createHash("sha256").update(bytes).digest("hex");
    if (sha256 !== asset.sha256) throw new Error(`Template image hash mismatch: ${template.id}`);
    const filename = `${index + 1}-${path.basename(asset.filename || url.pathname).replace(/[^a-zA-Z0-9._-]/g, "_")}`;
    const file = path.join(directory, filename);
    await saveFile(file, bytes);
    images.push({ path: file, sha256, original_url: asset.original_url, width: asset.width, height: asset.height });
  }
  const reference = { schema: "drawai.template-reference.v1", template, images };
  const manifest = path.join(directory, "template-reference.json");
  await saveFile(manifest, `${JSON.stringify(reference, null, 2)}\n`);
  return { ...reference, manifest };
}
