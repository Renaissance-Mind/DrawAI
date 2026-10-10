import { mkdir, writeFile, cp, access, readFile, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const workbench = path.join(root, 'apps/workbench');
await access(path.join(workbench, 'node_modules/@modelcontextprotocol/sdk/package.json'));
const html = await readFile(path.join(workbench, 'dist-plugin/templates-inline.html'));
const build = createHash('sha256').update(html).digest('hex').slice(0, 16);
const marketplace = path.join(root, '.local/plugin-marketplace');
const plugin = path.join(marketplace, 'drawai');
const skillNames = ['drawai-readme', 'drawai-design', 'drawai-image2ppt'];

async function syncSkills(destination) {
  await rm(path.join(destination, 'skills'), { recursive: true, force: true });
  for (const name of skillNames) {
    await cp(path.join(root, 'skills', name), path.join(destination, 'skills', name), {
      recursive: true,
      filter: (file) => !file.split(path.sep).includes('__pycache__') && !file.endsWith('.pyc'),
    });
  }
}

await mkdir(path.join(plugin, '.codex-plugin'), { recursive: true });
await mkdir(path.join(plugin, 'assets'), { recursive: true });
await cp(path.join(workbench, 'public/drawai_image.png'), path.join(plugin, 'assets/drawai_image.png'));
await syncSkills(plugin);
const manifest = {
  name: 'drawai', version: '4.0.0',
  description: 'Read the DrawAI guide, determine page visuals, then convert images to editable PowerPoint in the current session or with DrawAI-Flow in Workbench.',
  author: { name: 'Renaissance Mind' }, license: 'Apache-2.0', skills: './skills/', mcpServers: './.mcp.json',
  interface: {
    displayName: 'DrawAI', shortDescription: '模板参考与可编辑 PowerPoint',
    composerIcon: './assets/drawai_image.png', logo: './assets/drawai_image.png', logoDark: './assets/drawai_image.png',
    brandColor: '#3168f5',
    defaultPrompt: ['使用 $drawai-readme，先检查当前图像工具与模型，再按我的需求完成视觉设计和图像转 PPT。已说明的需求直接沿用。'],
    category: 'Productivity', capabilities: ['Interactive', 'Read', 'Write'],
  },
};
const mcp = { mcpServers: { drawai: {
  command: process.execPath, args: [path.join(workbench, 'templates/server.mjs')], cwd: root,
  env: { DRAWAI_TEMPLATES_BUILD: build },
} } };
await writeFile(path.join(plugin, '.codex-plugin/plugin.json'), `${JSON.stringify(manifest, null, 2)}\n`);
await writeFile(path.join(plugin, '.mcp.json'), `${JSON.stringify(mcp, null, 2)}\n`);
await mkdir(path.join(marketplace, '.agents/plugins'), { recursive: true });
await writeFile(path.join(marketplace, '.agents/plugins/marketplace.json'), `${JSON.stringify({
  name: 'drawai-local', interface: { displayName: 'DrawAI Development' },
  plugins: [{ name: 'drawai', source: { source: 'local', path: './drawai' }, policy: { installation: 'AVAILABLE', authentication: 'ON_INSTALL' }, category: 'Productivity' }],
}, null, 2)}\n`);
const configured = JSON.parse(execFileSync('codex', ['plugin', 'marketplace', 'list', '--json'], { cwd: root, encoding: 'utf8' }))
  .marketplaces.find((entry) => entry.name === 'drawai-local');
if (configured && path.resolve(configured.root) !== marketplace) {
  if (configured.marketplaceSource?.sourceType !== 'local') throw new Error('drawai-local is configured from a non-local source');
  console.log(execFileSync('codex', ['plugin', 'marketplace', 'remove', 'drawai-local'], { cwd: root, encoding: 'utf8' }).trim());
}
for (const args of [['plugin', 'marketplace', 'add', marketplace, '--json'], ['plugin', 'add', 'drawai@drawai-local', '--json']]) {
  const output = execFileSync('codex', args, { cwd: root, encoding: 'utf8' }).trim();
  console.log(output);
  const result = JSON.parse(output);
  if (result.installedPath) {
    await syncSkills(result.installedPath);
    for (const entry of ['.codex-plugin', '.mcp.json', 'assets']) await cp(path.join(plugin, entry), path.join(result.installedPath, entry), { recursive: true });
    const installed = JSON.parse(await readFile(path.join(result.installedPath, '.mcp.json'), 'utf8'));
    if (installed.mcpServers.drawai.args[0] !== mcp.mcpServers.drawai.args[0]) throw new Error('Installed DrawAI template service path is stale');
  }
}
console.log(`DrawAI 4.0.0 installed with ${skillNames.join(', ')} (UI ${build}). Use $drawai-readme to begin the staged workflow.`);
