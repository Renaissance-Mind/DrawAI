# DrawAI Session 集成

Session、Workbench 与 CLI 使用同一 DrawAI 安装。完整安装、依赖和配置见 [统一安装与使用](installation.md)。

```bash
uv tool install --python 3.12 .
drawai setup --agent codex
# Claude Code 使用：drawai setup --agent claude
```

打开新会话，从 `$drawai-readme` 提供材料与目标。三个技能负责读取需求、设计页面和制作/检查 PPT。通用宿主用 `drawai session install --host generic --output-dir /path/to/adapter` 导出 Skills 与 MCP 配置。

## 当前会话与模型

默认由当前 Agent 制作：Claude 会话使用当前 Claude 配置，Codex 会话使用当前 Codex 配置。宿主模型和推理设置沿用本轮实际值；未知版本不自动改用另一个 Agent。需要看图和真实代码执行能力，缺项直接报告。只有用户明确指定其他 Agent、模型或 Flow 时才改变相应执行方式。

图像来源独立选择：当前 Session 的图像工具、用户提供的 Images API、已有图片或可真实渲染的本地排版。外接图像 API 不改变最终执行 Agent。连接由工作台设置或 `drawai config connections` 共用管理。

## MCP 工具

| 工具 | 用途 |
| --- | --- |
| drawai_templates | 查找、读取、推荐真实模板 |
| drawai_show_templates | 内嵌模板界面；无 MCP Apps 的宿主仍可通过数据工具读取模板 |
| drawai_prepare_template | 下载并检查参考图片哈希 |
| drawai_plan | 当前 Session 规划，分别确定图像来源与实施 Agent |
| drawai_image | 使用共用 Images API 连接生成/编辑真实图像 |
| drawai_flow | 用户明确委托的工作台提交、执行、状态和导出 |

安装后的 MCP 使用安装包的 Python，直接调用共同核心；用户不必构建 Node MCP 服务。前端在发行构建时准备。工具包代码位于安装包中的 `pptx_skill`，技能脚本保持兼容。

## Flow 与独立模型配置

Session 明确使用 Flow 时，把 `drawai_plan` 返回的 `implementation.flow_agent_settings` 传为提交的 `agent_settings`。本任务保留调用者 Agent 类型、已知模型与推理参数，工作台使用自己的认证；全局配置保持原值。用户明确选择工作台已有 Agent 时使用 configured。

```bash
drawai setup --enable workbench
drawai workbench
```

默认 UI 和 API 共用 `http://127.0.0.1:8890/`。地址通过 `drawai config flow` 或既有 `DRAWAI_WORKBENCH_API_URL` / `DRAWAI_WORKBENCH_UI_URL` 设置；设置在三个入口间共享。

## 维护

更新 DrawAI 安装后重新执行 `drawai setup --agent <宿主>`，并打开新会话。原 `node scripts/install_plugin.mjs` 兼容命令转交统一安装器。源码 UI 开发仍可执行 `npm run build:plugin`、`npm run build:templates`；普通安装使用已构建资源。

两种转换方法都检查实际 PPTX、可编辑对象、文字/数据和渲染预览，并交付制作源与报告。
