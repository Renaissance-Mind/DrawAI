# DrawAI 统一安装与使用

DrawAI 安装一次，Agent Session、Workbench 和 CLI 调用同一套核心、模板、模型连接和 PPT 工具。图像来源和最终制作 Agent 分别选择。Session 默认使用当前 Agent 的配置；独立工作台与 CLI 使用共同配置中的执行后端。

## 安装

从当前源码目录安装，安装过程自动构建并打包前端。源码构建需要 Node.js 20.19+ 或 22.12+；uv 可准备 Python 3.12：

```bash
uv tool install --python 3.12 .
drawai setup
drawai doctor
```

安装已有 wheel 时，客户端无需 Node.js 或源码仓库：

```bash
uv tool install --python 3.12 /path/to/drawai-0.2.0-py3-none-any.whl
drawai setup
```

本地构建 wheel 可用 `uv build --wheel`。wheel 包含共同 Python 核心、三个 Skills、PPT 工具包、模板目录、兼容脚本和预先构建的 Workbench。更新同一来源使用 `uv tool install --reinstall --python 3.12 <安装来源>`，再重新注册相应宿主。这里说明当前仓库的安装流程，不表示 0.2.0 已发布到公共包仓库。

## 按需要启用能力

基础包可处理 PPT 文档、图像清单、Session 规划、模板与 Images API。下面的操作都使用同一个安装中的 Python 环境：

| 能力 | 操作 |
| --- | --- |
| 注册 Codex Session | `drawai setup --agent codex` |
| 注册 Claude Code Session | `drawai setup --agent claude` |
| 导出通用宿主适配 | `drawai session install --host generic --output-dir /path/to/adapter` |
| 启用 Workbench 与 Flow 依赖 | `drawai setup --enable workbench` |
| 直接 LLM API 执行 | `drawai setup --enable llm` |
| Codex SDK 执行 | `drawai setup --enable codex` |
| Claude Agent SDK 执行 | `drawai setup --enable claude` |
| 全部 SDK 执行适配 | `drawai setup --enable agents` |
| LibreOffice 与 Poppler 预览 | `drawai setup --enable preview --install-system` |
| Pandoc 公式转换 | `drawai setup --enable formulas --install-system` |
| 本地视觉模型 | `drawai setup --enable models --device cpu` |

宿主 Agent CLI 已安装时，可直接选择 CLI 后端，无需安装其 SDK。系统工具自动安装支持已有的 Homebrew 或 apt-get；其他平台通过系统包管理器安装 LibreOffice、Poppler 或 Pandoc，再运行 doctor。`--install-system` 明确启用系统包安装，Linux 非 root 环境使用 sudo。

`drawai setup --dry-run` 显示计划，不写配置或安装依赖。`drawai doctor --require workbench --require preview` 检查指定能力并以退出码报告缺项。本地模型准备保留许可证确认和设备设置；需要细分模型、下载源或已有 Torch 环境时，使用兼容命令 `drawai setup local --help`。

## 共同配置与已有数据

默认数据目录为 `~/.drawai`，可通过 `DRAWAI_HOME` 指定。三个入口共同使用：

```text
~/.drawai/
  config.yaml                 CLI 与 Workbench 的管线基础配置
  preferences.json            图像来源、默认连接及 Flow 地址
  workbench/settings/
    api_presets.json           图像与 LLM 连接
    agent.json                 独立执行的 Agent 配置
    processor.json             素材处理器配置
  workbench/                   上传、任务、结果与数据库
  runtime/                     可选模型运行环境
  integrations/                宿主 Skills 与 MCP 适配
```

旧工作台和模型数据可以直接引用，不迁移或覆盖原文件：

```bash
drawai setup --workspace /existing/.local/workbench --runtime-root /existing/.local/drawai_runtime
```

`DRAWAI_WORKBENCH_WORKSPACE`、`DRAWAI_LOCAL_RUNTIME_ROOT` 和 `DRAWAI_WORKBENCH_DEFAULT_CONFIG` 仍可显式覆盖对应路径。`drawai config show` 显示脱敏配置；API 密钥优先用环境变量引用，配置文件限制为用户读写。

## 配置图像 API 与独立执行模型

在 Workbench 设置中新增连接，或导入同一格式的 JSON。下面是连接结构，模型名和地址须替换为真实提供方配置：

```json
{
  "presets": [
    {
      "id": "personal-images",
      "label": "我的图像 API",
      "type": "images_api",
      "base_url": "https://provider.example/v1",
      "model": "实际图像模型",
      "api_key_env": "MY_DRAWAI_IMAGE_KEY"
    },
    {
      "id": "personal-llm",
      "label": "我的 LLM API",
      "type": "llm",
      "endpoints": [
        {
          "id": "chat",
          "type": "llm_chat_completions",
          "base_url": "https://provider.example/v1",
          "model": "实际多模态模型",
          "api_key_env": "MY_DRAWAI_LLM_KEY"
        }
      ]
    }
  ]
}
```

```bash
drawai config connections --import connections.json
drawai config image --source api --connection personal-images
drawai config agent --provider drawai_tool_agent --connection personal-llm --endpoint chat
```

最后一条配置独立工作台/CLI 的执行器。Session 默认最终制作仍使用调用者的当前 Agent。API 预设可声明 Chat Completions、Responses 和 Anthropic 协议；执行后端必须支持所选协议，当前内置 API Agent 使用 Chat Completions 并需要工具调用能力。看图任务需要视觉输入支持；图像生成使用独立 Images API。

## Agent Session

注册相应宿主后打开新会话，直接提供材料和要求：

```text
使用 $drawai-readme，根据这份材料制作 10 页、16:9 的汇报。
图像使用当前会话图像工具，最后由当前 Agent 制作可编辑 PPT。
```

也可指定外接图像 API：

```text
使用 personal-images 连接生成页面图像，最后继续由当前 Agent 制作 PPT。
```

Claude Session 默认由当前 Claude 制作，Codex Session 默认由当前 Codex 制作；其他具备看图和执行能力的宿主同样使用当前会话。未知模型版本不触发自动换 Agent。缺少能力时报告具体缺项。

Session 图像 API 可通过 MCP `drawai_image` 或下面的共同 CLI 调用：

```bash
drawai image generate --connection personal-images --prompt "实际页面内容" --output-dir visuals --stem page-001
drawai image edit --connection personal-images --source visuals/page-001.png --prompt "实际修改要求" --output-dir visuals --stem page-001-v2
```

用户明确要求另一个 Agent 时，使用显式入口，默认模型、认证和权限沿用该 Agent 自身配置；需要改变模型才传 `--model`：

```bash
drawai session execute --agent claude --prompt-file task.md --workdir /path/to/task
```

通用宿主可使用 `--agent custom --command command.json`，命令文件为参数数组，任务通过 stdin 传入。默认 Session 制作不会启动额外 Agent 进程。

## Workbench 与 CLI

```bash
drawai setup --enable workbench
drawai workbench
```

打开 `http://127.0.0.1:8890/`。在设置中选择实际 Agent、模型连接与所需处理器；未启用的 SDK 或本地模型会显示对应缺项。UI 和 API 使用同一进程，不要求 Node.js；要同时启动已准备的本地模型，加 `--start-model`。仅使用外部模型服务或图像/LLM API 时按所选流程配置连接，缺失处理器仍会报告错误。

常见 CLI 使用同一安装：

```bash
drawai visual save visual-spec.json visual-deck.json
drawai visual verify visual-deck.json
drawai presentation export deck.document.json --pptx output/deck.pptx
drawai presentation inspect output/deck.pptx --output output/inventory.json
drawai presentation render output/deck.pptx --output-dir output/preview
drawai ppt edit source.pptx --plan changes.json --output output/edited.pptx
```

Flow 同样可以在 Session 或 CLI 提交。CLI 缺省使用工作台配置；Session 提交应传规划器的 `implementation.flow_agent_settings`，保留当前 Agent 类型与已知模型参数，使用执行主机的认证：

```bash
drawai flow status
drawai flow submit --manifest /absolute/visual-deck.json --agent-settings task-agent.json
drawai flow start --batch-id batch_实际返回值
drawai flow status --batch-id batch_实际返回值
drawai flow export --batch-id batch_实际返回值 --output /absolute/output/deck.pptx
```

`task-agent.json` 是本任务配置，例如 `{"selected_provider_id":"claude_cli","model":"实际会话模型"}`；不修改全局 Agent 配置。用户明确选择工作台 Agent 时省略该文件，并在规划请求中使用 configured。

Flow 地址共同保存：

```bash
drawai config flow --api-url http://127.0.0.1:8890 --ui-url http://127.0.0.1:8890/
```

保留的 `drawai run <image> --local`、`drawai workflow`、`drawai server model/api` 使用共同安装与资源。CLI 本地图片运行读取已保存的工作台 Agent 设置。旧技能脚本和 `node scripts/install_plugin.mjs` 是共同核心的兼容入口。开发前端可用 `drawai workbench --dev`，默认用户路径使用预构建页面。

## 服务端部署

Docker 使用相同 wheel、核心、配置和预构建页面。镜像包含 CPU 导出与预览环境，本地视觉模型按需另外部署：

```bash
docker build -t drawai .
docker run --rm -p 8890:8890 -v drawai-data:/data drawai
```

容器通过 `DRAWAI_HOME=/data` 保存配置和结果，cloud_mode 关闭服务器本地目录上传。这里提供单工作区服务部署，适用于单用户或受控环境。多人在线服务的账号鉴权、用户隔离、加密密钥系统、持久任务队列和限额仍需实现；在公网使用前应完成相应服务能力。

## 交付与检查

统一工具生成真实 PPTX、SVG、页面预览、图像清单、素材与报告。图像 API 提供画面；最终执行者负责对象重建与检查。对复杂插画保留局部图片，图表数据不足时明确近似；预览与目标 PowerPoint 的验证分别记录。
