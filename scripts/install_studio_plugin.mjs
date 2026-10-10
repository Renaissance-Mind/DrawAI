import { mkdir, writeFile, cp, access, readFile, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const workbench = path.join(root, 'apps/workbench');
await access(path.join(workbench, 'node_modules/@modelcontextprotocol/sdk/package.json'));
await access(path.join(workbench, 'dist-plugin/workbench.html'));
const build = createHash('sha256').update(await readFile(path.join(workbench, 'dist-plugin/workbench.html'))).digest('hex').slice(0, 16);
const marketplace = path.join(root, '.local/studio-plugin-marketplace');
const plugin = path.join(marketplace, 'drawai');
await mkdir(path.join(plugin, '.codex-plugin'), { recursive: true });
await mkdir(path.join(plugin, 'assets'), { recursive: true });
await cp(path.join(workbench, 'public/drawai_image.png'), path.join(plugin, 'assets/drawai_image.png'));
const skillNames = ['drawai-studio', 'drawai-simple', 'drawai-ppt'];
async function syncSkill(source, destination) {
  await rm(destination, { recursive: true, force: true });
  await cp(source, destination, {
    recursive: true,
    filter: (file) => !file.split(path.sep).includes('__pycache__') && !file.endsWith('.pyc'),
  });
}
for (const skill of skillNames) await syncSkill(path.join(root, 'skills', skill), path.join(plugin, 'skills', skill));
const manifest = {
  name: 'drawai', version: '2.0.4', description: 'Create slide images and editable PPT in the current Codex conversation with a visual workbench.',
  author: { name: 'Renaissance Mind' }, license: 'Apache-2.0', skills: './skills/', mcpServers: './.mcp.json',
  interface: { displayName: 'DrawAI', shortDescription: '视觉参考、PPT 图片与可编辑 PowerPoint', composerIcon: './assets/drawai_image.png', logo: './assets/drawai_image.png', logoDark: './assets/drawai_image.png', brandColor: '#3168f5', defaultPrompt: ['打开 DrawAI 工作台，开始制作 PPT'], category: 'Productivity', capabilities: ['Interactive', 'Read', 'Write'] },
};
await writeFile(path.join(plugin, '.codex-plugin/plugin.json'), `${JSON.stringify(manifest, null, 2)}\n`);
const store = process.argv.find((arg) => arg.startsWith('--store='))?.slice(8);
await writeFile(path.join(plugin, '.mcp.json'), `${JSON.stringify({ mcpServers: { drawai: { command: process.execPath, args: [path.join(workbench, 'studio/server.mjs')], cwd: root, env: { DRAWAI_STUDIO_BUILD: build, ...(store ? { DRAWAI_STUDIO_HOME: path.resolve(store) } : {}) } } } }, null, 2)}\n`);
await mkdir(path.join(marketplace, '.agents/plugins'), { recursive: true });
await writeFile(path.join(marketplace, '.agents/plugins/marketplace.json'), `${JSON.stringify({ name: 'drawai-local', interface: { displayName: 'DrawAI Development' }, plugins: [{ name: 'drawai', source: { source: 'local', path: './drawai' }, policy: { installation: 'AVAILABLE', authentication: 'ON_INSTALL' }, category: 'Productivity' }] }, null, 2)}\n`);
const configured = JSON.parse(execFileSync('codex', ['plugin', 'marketplace', 'list', '--json'], { cwd: root, encoding: 'utf8' }))
  .marketplaces.find((entry) => entry.name === 'drawai-local');
if (configured && path.resolve(configured.root) !== marketplace) {
  if (configured.marketplaceSource?.sourceType !== 'local') {
    throw new Error('drawai-local is configured from a non-local source');
  }
  console.log(execFileSync('codex', ['plugin', 'marketplace', 'remove', 'drawai-local'], { cwd: root, encoding: 'utf8' }).trim());
}
for (const args of [['plugin', 'marketplace', 'add', marketplace, '--json'], ['plugin', 'add', 'drawai@drawai-local', '--json']]) {
  const output = execFileSync('codex', args, { cwd: root, encoding: 'utf8' }).trim();
  console.log(output);
  const result = JSON.parse(output);
  if (result.installedPath) {
    for (const skill of skillNames) await syncSkill(path.join(root, 'skills', skill), path.join(result.installedPath, 'skills', skill));
    for (const entry of ['.codex-plugin', '.mcp.json', 'assets']) {
      await cp(path.join(plugin, entry), path.join(result.installedPath, entry), { recursive: true });
    }
    const installedMcp = JSON.parse(await readFile(path.join(result.installedPath, '.mcp.json'), 'utf8'));
    if (installedMcp.mcpServers.drawai.cwd !== root) {
      throw new Error(`Installed DrawAI plugin does not point to ${root}`);
    }
  }
}
console.log(`DrawAI development plugin uses ${root} (UI ${build}). After UI changes, rebuild build:plugin, rerun this installer, and open a new Codex chat to load the refreshed MCP connection and versioned UI resource.`);
