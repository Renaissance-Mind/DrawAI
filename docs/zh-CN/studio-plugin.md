# DrawAI 插件工作台

DrawAI 工作台围绕一份 PPT 项目组织内容、视觉参考、页面图片和可编辑结果。图像生成和重建由当前 Codex 会话执行；本地项目服务只保存文件、管理任务和返回界面资源。

## 启动与安装

需要 Node.js 20.19+ 或 22.12+。在仓库中运行：

```bash
cd apps/workbench
npm ci
npm run build:plugin
cd ../..
node scripts/install_studio_plugin.mjs
```

安装器创建本地 marketplace 并安装 `drawai@drawai-local`，打包 `drawai-studio`、`drawai-simple` 和 `drawai-ppt` 三个 Skills。这个开发安装指向当前 checkout 的项目服务与前端构建，适合在 `drawai-v2` worktree 中迭代；移动 checkout 后重新安装。插件通过标准 MCP stdio 连接运行，不需要图像生成 API key、模型服务或独立 Agent 进程。

在能加载该插件的 Codex 会话中调用 `drawai_open_workbench`。工作台显示在会话旁。新装插件若尚未出现在会话工具中，需要让客户端重新加载插件工具。发送能力由 MCP Apps 握手中的 `message` 能力确认，工作台不会把普通浏览器误报为已连接的 Codex 会话。

默认项目目录为 `~/.local/share/drawai/studio`。开发或测试时可隔离数据：

```bash
node scripts/install_studio_plugin.mjs --store=/absolute/path/to/studio-data
```

## 制作流程

创建项目，填写整份 PPT 的目标、语言和比例，再编辑各页准确内容。模板库提供真实案例图和配方；上传的文件可以是图片、PPTX、PDF 或文本材料。支持同时组合：

| 参考用途 | 作用 |
| --- | --- |
| 内容材料 | 事实、文案、数据和论文内容 |
| 信息结构 | 模块组织、流程、比较和图文关系 |
| 视觉风格 | 配色、视觉语言和排版节奏 |
| PPT 格式模板 | 页面格式、主题、页眉页脚等要求 |

每份参考可应用于整份 PPT 或指定页面。上传的 PPTX 保留原文件；内嵌缩略图可立即预览，完整页面预览由当前会话通过已有 PPT Skill 渲染并登记。

点击生成会先保存不可变任务请求，再通过 MCP Apps `ui/message` 发送到绑定的会话。当前 Agent 读取项目和参考，使用图像生成工具完成页面，通过项目工具登记图片。工作台支持比较版本、标记修改区域、导入已有图片，以及选择需要转换的页面。

转可编辑任务使用 `drawai-simple` 重建 SVG，使用 `drawai-ppt` 导出原生 PowerPoint 对象并渲染检查。整套导出按项目页序组装。图片变更后旧 PPTX 不再成为当前结果；任务执行期间页面内容或选定图片变化时，旧任务结果保留为历史，不覆盖新选择。

## 项目与任务

项目保存为 `project.json`、独立素材文件和每次任务的 `request.json`。任务状态包括待发送、已提交、执行中、已完成、失败和已取消。发送成功不会被当作生成成功；完成状态要求真实产物存在、哈希一致，并覆盖任务选定的页面。PPTX 转换结果需要包含原生可编辑对象。

Agent 使用以下工具：

- `drawai_project`：项目、页面内容和页序。
- `drawai_templates`：参考库检索和详情。
- `drawai_reference`：文件、参考用途和页面范围。
- `drawai_task`：读取请求、进度更新和取消。
- `drawai_artifact`：登记实际文件、选择版本、读取和导出。

没有 MCP 工具时，同一套操作可使用真实项目 CLI：

```bash
node apps/workbench/studio/cli.mjs drawai_project '{"action":"list"}'
node apps/workbench/studio/cli.mjs drawai_task @task-update.json
```

CLI 与插件必须使用相同的 `DRAWAI_STUDIO_HOME`。文件上传上限为 48 MB。项目删除会移动到该目录下的 `.trash`，保留恢复能力。

## 浏览器开发与验证

本轮只实现插件执行模式。浏览器开发视图可以管理同一份项目并创建任务请求，通过复制请求交给会话执行；它不运行独立 Agent SDK 后端。

```bash
cd apps/workbench
npm run studio:serve
# 另一个终端
npm run dev -- --host 127.0.0.1 --port 5190
```

项目服务默认监听 `127.0.0.1:8896`。使用 `DRAWAI_STUDIO_API_URL` 修改前端代理目标。界面沿用 Workbench 的字体、浅色背景、蓝灰边框与绿色强调色，宽屏使用页面栏/画布/属性栏，窄面板将页面与属性收为可展开面板。

```bash
npm run build:plugin
npm run test:studio
npm test
```

`test:studio` 使用真实文件系统和实际 stdio MCP 进程检查持久化、并发写入、参考范围、版本保护、产物校验和 UI 资源。端到端验收另需在实际 Codex 宿主完成一次消息发送、图像生成、PPT 转换与状态回写。

## 模板库来源与更新

模板库来自 VisualizeAnything 的真实资产目录和 DrawAI 现有配方。清单保存在 `apps/workbench/studio/data/visual-reference-templates.json`，保存来源、原图 URL、尺寸和 SHA-256。原图在选用并创建任务时下载到项目，核验哈希后再交给 Agent；无图片的配方明确标记为配方模板。

```bash
node scripts/sync_visual_reference_library.mjs
```

同步保留来源状态与使用说明；现有资产状态不等同于已经过人工设计质量审核。公开发布时按仓库的明确发布流程处理。
