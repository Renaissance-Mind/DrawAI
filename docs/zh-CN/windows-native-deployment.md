# DrawAI Windows 原生部署说明

在 Windows 10/11 上使用 PowerShell 部署 DrawAI，安装本地模型 runtime，启动 Workbench，并通过健康检查确认服务可用。`drawai setup local` 和 `drawai workbench` 支持 Windows 原生运行。

## 1. 新 Windows 电脑前置条件

建议使用 Windows 10/11 x64，PowerShell 或 PowerShell 7 均可。

必须安装：

| 依赖 | 要求 | 检查命令 |
| --- | --- | --- |
| Git for Windows | 用于 clone 仓库和 SAM3 源码 | `git --version` |
| uv | 用于项目环境和 runtime venv | `uv --version` |
| Python | 不需要单独管理，`uv run --python 3.12` 会解析/安装所需 Python | `uv python list` |
| Node.js + npm | Vite 要求 Node `^20.19.0 || >=22.12.0` | `node --version`; `npm --version` |
| Google Chrome | SVG 渲染验证使用 | `chrome --version` 或确认 Chrome 已安装 |
| Codex 登录或 OpenAI API Key | SVG 生成使用 Codex Python SDK | 见下一节 |
| NVIDIA driver | 可选，仅 GPU 模式需要 | `nvidia-smi` |

如果这台机器可以使用 winget，可参考：

```powershell
winget install --id Git.Git -e
winget install --id astral-sh.uv -e
winget install --id OpenJS.NodeJS.LTS -e
winget install --id Google.Chrome -e
```

uv 官方安装文档也可以参考：https://docs.astral.sh/uv/getting-started/installation/

## 2. 准备 Codex 认证

推荐方式是先在这台 Windows 电脑上登录 Codex app/CLI，让本机存在：

```powershell
Test-Path "$env:USERPROFILE\.codex\auth.json"
```

返回 `True` 后，`drawai doctor local` 会识别这个认证文件。

如果你的 Codex home 不在默认位置，显式设置：

```powershell
$env:DRAWAI_HOST_CODEX_HOME = "D:\path\to\.codex"
```

如果不用 Codex 登录文件，也可以使用 API key：

```powershell
$env:OPENAI_API_KEY = "sk-..."
```

## 3. 获取代码

```powershell
git clone <your-drawai-repo-url> DrawAI-dev
cd DrawAI-dev
```

后续命令都在仓库根目录执行。

## 4. 先 dry-run，不安装任何东西

```powershell
uv run --python 3.12 drawai setup local --dry-run
```

期望看到：

```text
[drawai-setup] setup implementation: python-native
[drawai-setup] download models: source=modelscope components=paddle,sam3,rmbg
[drawai-setup] bootstrap runtime venv
dry_run: no files were downloaded or modified
```

这一步只验证 uv、项目入口和参数解析，不会下载模型或改 runtime。

## 5. 安装 runtime 和模型

CPU 默认安装：

```powershell
uv run --python 3.12 drawai setup local --device cpu
```

有 NVIDIA GPU 时：

```powershell
uv run --python 3.12 drawai setup local --device gpu
```

如果需要手动指定 PyTorch CUDA wheel：

```powershell
uv run --python 3.12 drawai setup local --device gpu --torch-backend cu126
uv run --python 3.12 drawai setup local --device gpu --torch-backend cu128
uv run --python 3.12 drawai setup local --device gpu --torch-backend cu130
```

默认模型源是 ModelScope。如果要走 Hugging Face：

```powershell
$env:HF_TOKEN = "hf_..."
uv run --python 3.12 drawai setup local --source huggingface --accept-sam3-license
```

安装产物在：

```text
.local/drawai_runtime/
  .venv/
  source/sam3/
  models/sam3/
  models/paddlex/official_models/
  models/rmbg2/
  tools/
```

进度判断：

- setup 子命令会每 10 秒打印一次 heartbeat。
- 直接下载文件会每 3 秒打印已下载字节数、当前速度、平均速度。
- 网络和 HTTP 操作的超时为 600s。
- SVG Codex 生成阶段单独允许等待 1500s。
- 如果非 SVG 阶段 600s 内没有进展，优先检查网络、代理、杀毒软件扫描、模型源可访问性。

## 6. 验证 runtime

```powershell
uv run --python 3.12 drawai doctor local
```

完整可用时应看到：

```text
status: ok
ready: 18/18
Action queue
  none
```

如果 Codex auth 报错：

```powershell
Test-Path "$env:USERPROFILE\.codex\auth.json"
uv run --python 3.12 drawai doctor local
```

如果 SDK auth 报错但 auth 文件存在，通常是 Codex 登录过期、网络代理问题，或 `OPENAI_API_KEY` 不可用。刷新登录后重试 doctor。

## 7. 启动完整 Workbench

```powershell
uv run --python 3.12 drawai workbench
```

Windows 下这个命令会原生启动三个子进程：

| 进程 | 地址 | 日志 |
| --- | --- | --- |
| 模型服务 | `http://127.0.0.1:18080/health` | `.local/drawai-local-services.log` |
| Workbench API | `http://127.0.0.1:8890/api/health` | `.local/workbench-api.log` |
| 前端 | `http://127.0.0.1:5174/` | `.local/workbench-frontend.log` |

浏览器打开：

```text
http://127.0.0.1:5174/
```

launcher PID 会写入：

```text
.local/workbench-start.pid
```

前台运行时用 `Ctrl+C` 停止。如果是后台进程，可用任务管理器或 PowerShell 停掉对应 Python/Node 子进程。

## 8. 健康检查

另开一个 PowerShell：

```powershell
Invoke-RestMethod http://127.0.0.1:18080/health
Invoke-RestMethod http://127.0.0.1:8890/api/health
(Invoke-WebRequest http://127.0.0.1:5174/).StatusCode
```

期望：

```text
模型服务 status = ok
API status = ok
前端 HTTP status = 200
```

## 9. 跑一个真实 Workbench 任务

在 `http://127.0.0.1:5174/` 中：

1. 上传 PNG/JPG 图片。
2. 运行 analysis。
3. 检查并确认 assets。
4. 运行 SVG generation。
5. 导出 PPTX。

成功后 case 目录类似：

```text
.local/workbench/runs/<batch_id>/<case_id>/
  svg/semantic.svg
  svg/rendered.png
  reports/svg_validation_report.json
  reports/svg_to_ppt_export_report.json
  svg_to_ppt/semantic.svg_to_ppt.pptx
```

Workbench 状态应为：

```text
case.status = completed
stage svg = ok
stage export = ok
```

## 10. 分离部署

如果模型服务已经在别的机器运行：

```powershell
uv run --python 3.12 drawai workbench --model-api http://<model-host>:18080
```

如果已经有 Workbench API，只启动前端：

```powershell
uv run --python 3.12 drawai workbench --api http://<api-host>:8890
```

Windows frontend-only 路径会直接在 `apps/workbench` 下调用 `npm.cmd`。

## 11. 常见问题

### `openai-codex is required`

原因通常是 API 没有使用 `.local/drawai_runtime/.venv` 里的 Python。

处理：

```powershell
uv run --python 3.12 drawai setup local --bootstrap-only
uv run --python 3.12 drawai doctor local
uv run --python 3.12 drawai workbench
```

### `Codex/OpenAI auth` 或 `Codex SDK auth connectivity` 失败

先确认默认 auth 文件：

```powershell
Test-Path "$env:USERPROFILE\.codex\auth.json"
```

如果不是默认路径：

```powershell
$env:DRAWAI_HOST_CODEX_HOME = "D:\path\to\.codex"
uv run --python 3.12 drawai doctor local
```

如果使用 API key：

```powershell
$env:OPENAI_API_KEY = "sk-..."
uv run --python 3.12 drawai doctor local
```

### SVG 生成 1500s 超时

当前实现会给 SVG Codex 生成阶段单独等待 1500s，然后丢弃死掉的 Codex session 再重试。如果 Codex 已经写出验证通过的 `semantic_N.svg`，会自动提升为最终 `semantic.svg`。如果 partial SVG 已合法但缺少 `iteration_log.md/jsonl`，会自动补一份 recovery log，避免因为日志缺失重跑整轮。

检查 trace：

```powershell
Get-Content .local\workbench\runs\<batch_id>\<case_id>\trace\svg_generation_model.jsonl -Tail 40
```

看到下面事件说明部分 SVG 恢复生效：

```text
codex_python_sdk_partial_svg_recovered
```

### OCR HTTP 500

先看模型服务日志：

```powershell
Get-Content .local\drawai-local-services.log -Tail 120
```

再检查服务：

```powershell
Invoke-RestMethod http://127.0.0.1:18080/health
```

### 前端启动失败

确认 Node 版本满足要求：

```powershell
node --version
npm --version
```

重新安装前端依赖：

```powershell
cd apps\workbench
npm ci
cd ..\..
uv run --python 3.12 drawai workbench
```

## 12. 新机器最短可执行清单

```powershell
git clone <your-drawai-repo-url> DrawAI-dev
cd DrawAI-dev

uv run --python 3.12 drawai setup local --dry-run
uv run --python 3.12 drawai setup local --device cpu
uv run --python 3.12 drawai doctor local
uv run --python 3.12 drawai workbench
```

然后检查：

```powershell
Invoke-RestMethod http://127.0.0.1:18080/health
Invoke-RestMethod http://127.0.0.1:8890/api/health
(Invoke-WebRequest http://127.0.0.1:5174/).StatusCode
```

可用标准：

- `drawai doctor local` 为 `status: ok`。
- 模型服务和 API health 都返回 `ok`。
- 前端返回 HTTP 200。
- 一个真实上传 case 能到 `completed`。
- case 目录中存在 `svg/semantic.svg`、`svg/rendered.png`、`svg_to_ppt/semantic.svg_to_ppt.pptx`。
