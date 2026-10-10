# DrawAI 插件

DrawAI 以当前对话为制作入口。先阅读 `drawai` 使用指南，需要参考时通过 `drawai-templates` 推荐和展示模板，再用 `drawai-ppt` 制作或编辑 PowerPoint。

## 安装

需要已安装并登录的 Codex CLI，以及 Node.js 20.19+ 或 22.12+。在仓库中执行：

```bash
cd apps/workbench
npm ci
npm run build:plugin
cd ../..
node scripts/install_plugin.mjs
```

安装器创建 `.local/plugin-marketplace`，注册 `drawai-local` 并安装 `drawai@drawai-local`。插件包包含 `drawai`、`drawai-templates`、`drawai-ppt` 三个 Skill、品牌图标和模板 MCP 连接。模板服务指向运行安装器的 checkout，重新安装会更新技能和连接路径。

安装后新建聊天，使用 `$drawai`。例如“推荐适合论文答辩的模板”“展示流程图版式”“使用这些参考，根据我的提纲制作可编辑 PPT”。制作 PPT 的 Python 依赖、LibreOffice、Poppler 与 Pandoc 准备方法见 [drawai-ppt](../../skills/drawai-ppt/SKILL.md)。

## 技能与制作

`drawai` 说明插件能力和任务路径。`drawai-templates` 根据页面用途、结构和风格推荐真实参考，展示内嵌选择界面，并准备原图与说明。`drawai-ppt` 处理内容、数据、用户上传的 PPTX 模板或参考图片，制作原生对象、导出与检查文件。

模板库保存真实参考图片、设计配方、原图哈希和来源。用户可以搜索、按分类筛选、查看设计说明，并选择多个参考，分别用于信息结构或视觉风格。图片中的示例事实和数据仅用于说明呈现方式。

内嵌界面的“用于当前任务”将选择发回绑定的对话；Codex 读取模板详情，准备真实图片并继续当前任务。只有选型需求时确认选择，制作 PPT 时按 `drawai-ppt` 的流程执行并交付文件。

## 模板工具与内嵌界面

| 工具 | 用途 |
| --- | --- |
| `drawai_templates` | 搜索、读取详情或获取按关键词相关度排序的候选 |
| `drawai_show_templates` | 在对话内展示指定候选或筛选结果 |
| `drawai_prepare_template` | 下载所选真实参考图、验证 SHA-256，并保存 `template-reference.json` |

数据工具和展示工具分开。只有 `drawai_show_templates` 关联 UI 资源，资源与初始化都声明支持 `inline` 和 `fullscreen`。界面通过 MCP Apps 标准桥接读取模板、更新选择上下文和发送会话消息。接入方式见 [OpenAI 插件 UI 文档](https://developers.openai.com/plugins/build/chatgpt-ui)。

本地 CLI 也提供相同工具，例如：

```bash
node apps/workbench/templates/cli.mjs drawai_templates '{"action":"recommend","query":"论文 消融","limit":6}'
```

## 独立模板网站

模板页可以单独构建为静态网站。网页读取随包保存的真实目录；选择后复制说明到 Codex，继续制作。

```bash
cd apps/workbench
npm run build:templates
npm run preview:templates -- --port 5198
```

浏览器打开 `http://127.0.0.1:5198/`。`dist-templates/` 包含 `index.html`、前端资源和 `template-catalog.json`，可整体部署到静态网站服务。参考图片从目录记录的真实资产地址加载。

原有位图重建浏览器工作台使用 `/`，模板开发页使用 `/templates.html`。正常前端构建同时输出这两个入口与模板目录。

## 更新与验证

修改界面后重新运行 `npm run build:plugin` 和安装器，再在新聊天中加载插件。UI 资源 URI 含内容哈希，连接配置保存构建标识。

```bash
cd apps/workbench
npm run build
npm run build:plugin
npm run build:templates
npm test
npm run test:templates
```

模板目录位于 `apps/workbench/templates/data/visual-reference-templates.json`，可通过 `node scripts/sync_visual_reference_library.mjs` 同步。目录保留来源与使用说明；相关度推荐依据元数据匹配，不代表人工设计质量评级。
