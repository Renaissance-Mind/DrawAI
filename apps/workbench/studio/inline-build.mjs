import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../dist-plugin",
);
let html = await readFile(path.join(root, "studio.html"), "utf8");
const scripts = [
  ...html.matchAll(/<script\b[^>]*src="([^"]+)"[^>]*><\/script>/g),
];
for (const match of scripts) {
  const code = await readFile(path.join(root, match[1]), "utf8");
  html = html.replace(
    match[0],
    () =>
      `<script type="module">${code.replaceAll("</script", "<\\/script")}</script>`,
  );
}
const styles = [...html.matchAll(/<link\b[^>]*href="([^"]+\.css)"[^>]*>/g)];
for (const match of styles) {
  const css = await readFile(path.join(root, match[1]), "utf8");
  html = html.replace(match[0], () => `<style>${css}</style>`);
}
html = html.replace(/<link\b[^>]*rel="icon"[^>]*>/g, "");
await writeFile(path.join(root, "workbench.html"), html);
console.log(`MCP App resource built: ${path.join(root, "workbench.html")}`);
