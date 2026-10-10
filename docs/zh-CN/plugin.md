# DrawAI 插件

DrawAI 的制作流程先确定页面视觉图像，再把图像转成可编辑 PPT。三个 Skill 分别负责入口与确认、视觉设计、实际转换与文件编辑。

## 安装

需要已安装并登录的 Codex CLI，以及 Node.js 20.19+ 或 22.12+。在仓库中执行：

```bash
cd apps/workbench
npm ci
npm run build:plugin
cd ../..
node scripts/install_plugin.mjs
```

安装器创建 `.local/plugin-marketplace` 并安装 `drawai@drawai-local`。插件包含 `drawai-readme`、`drawai-design`、`drawai-image2ppt`，以及模板、规划和 Workbench 桥接工具。服务指向当前 checkout；重新安装更新技能、路径与 UI 构建标识。

使用插件时从 `$drawai-readme` 开始，例如“根据项目中的模板做 10 页 16:9 的科研汇报，直接使用 Skill 转 PPT”。当前会话的图像工具和模型由 Agent 从真实会话信息检查；MCP 服务不推断隐藏的模型。

## 阶段与确认

| 技能 | 负责的工作 |
| --- | --- |
| `drawai-readme` | 读取需求与材料、检查环境、自动推荐转换模式，补齐仍缺失的信息 |
| `drawai-design` | 模板和参考选择、逐页视觉设计、图像生成或接收用户已确定的图像，交付有序清单 |
| `drawai-image2ppt` | 当前会话重建或提交 DrawAI-Flow，原生 PPT 构建与编辑、导出、检查和交付 |

只询问尚未确定的三点：是否使用参考、页数与比例、图像转 PPT 的模式。已经给出的信息直接沿用，明确“不要询问”或已说明制作流程时直接执行。问题模板与规划请求在 [需求确认](../../skills/drawai-readme/references/intake.md)。

默认模型策略为 GPT 5.6+、Claude 5+、DeepSeek Flash v4.1+ 使用当前会话 Skill，其他或版本未知使用 DrawAI-Flow。Skill 还需要看图与本地执行能力，Flow 使用工作台已有的配置。用户明确指定的模式优先。规则以 [模型策略](../../skills/drawai-readme/references/model-policy.json) 为准，不是模型质量评分。

设计阶段保存 `drawai.visual-deck.v1`，记录每页真实图像、页序、比例、内容和 SHA-256。两个转换模式使用同一份清单，最后都检查实际 PPTX、可编辑对象与渲染预览。

## MCP 与 Workbench

| 工具 | 用途 |
| --- | --- |
| `drawai_templates` | 搜索、读取参考详情和关键词相关度候选 |
| `drawai_show_templates` | 在对话内展示模板选择界面 |
| `drawai_prepare_template` | 为设计阶段准备原图与参考说明，校验哈希 |
| `drawai_plan` | 根据当前真实环境与用户偏好，返回模式、缺失问题和阻塞项 |
| `drawai_flow` | 接入现有 Workbench 的提交、启动、状态与导出 |

模板 UI 需要 MCP Apps 的 UI 资源与会话桥接，支持 Inline 和展开显示。Skill 的理解、设计与当前会话重建继续由 Agent 执行。MCP 对 Flow 的桥接直接使用现有 Workbench API，不增加 Studio 项目／任务工作台。

`drawai_flow` 的 `submit` 校验图像清单并建立排队批次，`start` 执行该批次，`status` 查询真实阶段状态，`export` 下载完成的 PPTX 到新路径。`auto_start=false` 也可通过原有批次 API 建立待执行批次；原浏览器提交默认仍立即执行。

服务默认 API 为 `http://127.0.0.1:8890`，界面为 `http://127.0.0.1:5174/`。可使用 `DRAWAI_WORKBENCH_API_URL`、`DRAWAI_WORKBENCH_UI_URL` 和 `DRAWAI_PYTHON` 配置安装环境。首次 Workbench 与模型准备见[运行文档](runtime-options.md)。Flow 的处理器和 Agent 配置是工作台配置，与当前会话的模型身份分开判断。

## 模板网页

模板页使用真实参考目录，点击卡片选择，选中显示边框。参考的示例内容不成为用户的事实或数据。可独立构建静态网站：

```bash
cd apps/workbench
npm run build:templates
npm run preview:templates -- --port 5198
```

打开 `http://127.0.0.1:5198/`。`dist-templates/` 可部署到静态服务；网页选择可复制到当前对话，继续设计。原位图重建工作台使用 `/`，模板开发页使用 `/templates.html`。

## 验证与交付

PPT 工具包位于 `skills/drawai-image2ppt`，需要 Python 3.12+ 和其依赖；渲染需要 LibreOffice 与 Poppler，公式转 Office Math 需要 Pandoc。两种模式都交付真实文件并检查，不把批次提交成功当作 PPT 完成。

```bash
cd apps/workbench
npm run build
npm run build:plugin
npm run build:templates
npm test
npm run test:templates
```

模型路由、提问规则、图像清单与 Workbench 桥接另有真实文件和 API 检查。完整模型推理与复杂页面重建的验收仍以本次实际产物为准。
