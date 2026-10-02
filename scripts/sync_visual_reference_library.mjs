import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const endpoint = 'https://upload.visualize.renaissancemind.ai/api/templates?status=all&limit=1500';
const sourceArg = process.argv.find((arg) => arg.startsWith('--source='));
const source = sourceArg ? await readFile(sourceArg.slice(9), 'utf8') : await (async () => {
  const response = await fetch(endpoint, { signal: AbortSignal.timeout(45000) });
  if (!response.ok) throw new Error(`Template source HTTP ${response.status}`);
  return response.text();
})();
const payload = JSON.parse(source);
if (!Array.isArray(payload.templates) || payload.templates.length !== payload.total) throw new Error('Template response is incomplete; import all pages before syncing');
const builtin = JSON.parse(execFileSync('python3', ['-c', 'import sys,json;sys.path.insert(0,"src");from drawai.slide_template_library import list_template_cards;print(json.dumps(list_template_cards()))'], { cwd: root, encoding: 'utf8' }));
const cards = new Map(builtin.map((card) => [card.id, { ...card, format_family: 'ppt', assets: [], origin: 'drawai' }]));
let imported = 0;
for (const card of payload.templates.filter((t) => t.format_family === 'ppt')) {
  if (!card.id || !card.name || !card.prompt_recipe) throw new Error('Template metadata is incomplete');
  const assets = card.assets.map((asset) => {
    if (!asset.original_url || !/^[a-f0-9]{64}$/.test(asset.sha256)) throw new Error(`Missing original image provenance: ${card.id}`);
    return Object.fromEntries(['id', 'filename', 'mime_type', 'width', 'height', 'size_bytes', 'sha256', 'caption', 'model', 'original_url', 'image_urls'].map((key) => [key, asset[key]]));
  });
  cards.set(card.id, { ...Object.fromEntries(['id', 'name', 'category', 'format_family', 'surface_type', 'scenario_tags', 'visual_tags', 'visual_keywords', 'palette', 'layout_archetypes', 'text_density', 'prompt_recipe', 'source_policy', 'ip_safety', 'provenance', 'tests', 'status', 'visibility', 'version'].map((key) => [key, card[key]])), assets, origin: 'visualizeanything' });
  imported++;
}
const templates = [...cards.values()].sort((a, b) => Number(b.assets.length > 0) - Number(a.assets.length > 0) || a.name.localeCompare(b.name));
const result = { schema: 'drawai.visual-reference-library.v1', source: { repository: 'https://github.com/Renaissance-Mind/VisualizeAnything-Server', endpoint, fetched_at: new Date().toISOString(), sha256: createHash('sha256').update(source).digest('hex'), imported_cards: imported }, templates };
const target = path.join(root, 'apps/workbench/studio/data/visual-reference-templates.json');
await mkdir(path.dirname(target), { recursive: true });
await writeFile(target, `${JSON.stringify(result, null, 2)}\n`);
console.log(JSON.stringify({ templates: templates.length, with_images: templates.filter((t) => t.assets.length).length, target }));
