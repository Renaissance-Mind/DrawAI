import { mkdir, writeFile, cp, access, readFile } from 'node:fs/promises';
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
for (const skill of ['drawai-studio', 'drawai-simple', 'drawai-ppt']) await cp(path.join(root, 'skills', skill), path.join(plugin, 'skills', skill), { recursive: true });
const manifest = {
  name: 'drawai', version: '2.0.1', description: 'Create slide images and editable PPT in the current Codex conversation with a visual workbench.',
  author: { name: 'Renaissance Mind' }, license: 'Apache-2.0', skills: './skills/', mcpServers: './.mcp.json',
  interface: { displayName: 'DrawAI', shortDescription: '视觉参考、PPT 图片与可编辑 PowerPoint', defaultPrompt: ['打开 DrawAI 工作台，开始制作 PPT'], category: 'Productivity', capabilities: ['Interactive', 'Read', 'Write'] },
};
await writeFile(path.join(plugin, '.codex-plugin/plugin.json'), `${JSON.stringify(manifest, null, 2)}\n`);
const store = process.argv.find((arg) => arg.startsWith('--store='))?.slice(8);
await writeFile(path.join(plugin, '.mcp.json'), `${JSON.stringify({ mcpServers: { drawai: { command: process.execPath, args: [path.join(workbench, 'studio/server.mjs')], cwd: root, env: { DRAWAI_STUDIO_BUILD: build, ...(store ? { DRAWAI_STUDIO_HOME: path.resolve(store) } : {}) } } } }, null, 2)}\n`);
await mkdir(path.join(marketplace, '.agents/plugins'), { recursive: true });
await writeFile(path.join(marketplace, '.agents/plugins/marketplace.json'), `${JSON.stringify({ name: 'drawai-local', interface: { displayName: 'DrawAI Development' }, plugins: [{ name: 'drawai', source: { source: 'local', path: './drawai' }, policy: { installation: 'AVAILABLE', authentication: 'ON_INSTALL' }, category: 'Productivity' }] }, null, 2)}\n`);
for (const args of [['plugin', 'marketplace', 'add', marketplace, '--json'], ['plugin', 'add', 'drawai@drawai-local', '--json']]) {
  console.log(execFileSync('codex', args, { cwd: root, encoding: 'utf8' }).trim());
}
console.log(`DrawAI development plugin uses ${root} (UI ${build}). After UI changes, rebuild build:plugin, rerun this installer, and open a new Codex chat to load the refreshed MCP connection and versioned UI resource.`);
