# DrawAI Windows 原生部署说明

这份文档用于在一台新的 Windows 电脑上部署 DrawAI，并说明这次为了 Windows 适配对源码做了哪些修改、Linux 版本是否受到影响。

结论先说清楚：

- Windows 现在可以不依赖 Git Bash、MSYS2、tmux，直接在 PowerShell 里运行 `uv run --python 3.12 drawai setup local` 和 `uv run --python 3.12 drawai workbench`。
- Linux/macOS 的 `drawai workbench` 仍走原来的 Bash/tmux 启动脚本，Windows 分支由 `os.name == "nt"` 隔离。
- `drawai setup local` 已改为 Python 原生实现，这是跨平台变化；Linux 上命令不变，但不再依赖旧的 setup Bash 脚本。
- 本次在 Windows 主机上完成了真实部署验证；Linux 分支通过单测强制模拟非 Windows 路径验证，未在真实 Linux 机器上重跑完整模型流程。

## 1. Linux 影响范围

| 功能 | 当前行为 | Linux 影响 |
| --- | --- | --- |
| `drawai setup local` | 由 `src/drawai/local_cli.py` 调用 `src/drawai/local_setup.py`，Python 原生下载模型、创建 runtime venv、安装依赖。 | 命令不变；这是有意的跨平台改动。 |
| `drawai workbench` | Windows 原生启动模型服务、API、前端；非 Windows 调用 `scripts/start_drawai_workbench_local.sh`。 | Linux 仍走原 Bash/tmux launcher。 |
| `drawai workbench --api ...` | Windows 直接在 `apps/workbench` 调 `npm.cmd`；非 Windows 调用 `scripts/run_drawai_workbench_frontend.sh`。 | Linux 前端-only 路径不变。 |
| runtime venv 路径 | Windows 用 `.venv/Scripts/python.exe`，Linux 用 `.venv/bin/python`。 | 按 `os.name` 分支，无 Linux 路径回退。 |
| 默认超时 | OCR、模型 HTTP、Codex、doctor SDK 探测等长操作统一按 600s 处理。 | 正向变化，Linux 同样生效。 |
| SVG Codex 恢复 | Codex 超时后如果已有验证通过的 `semantic_N.svg`，会提升为 `semantic.svg`；死会话会被丢弃后重试。 | 正向变化，Linux 同样生效。 |
| SVG 重跑归档 | 跳过 `chrome-profile*`、`.playwright`、`playwright-report`、`test-results` 等临时浏览器目录，避免 Windows 长路径/锁文件问题。 | Linux 上无害。 |

锁定 Linux launcher 不被 Windows 分支影响的测试：

```powershell
uv run --python 3.12 pytest `
  tests\semantic_ppt\drawai_pipeline\test_cli_pipeline.py::test_workbench_uses_linux_shell_launcher_when_not_windows `
  tests\semantic_ppt\drawai_pipeline\test_cli_pipeline.py::test_workbench_frontend_only_uses_shared_launcher
```

## 2. Windows 适配源码改动清单

主要改动集中在这些文件：

| 文件 | 改动 |
| --- | --- |
| `src/drawai/local_setup.py` | 新增 Python 原生 setup 流程：下载 PaddleOCR/SAM3/RMBG，创建 `.local/drawai_runtime/.venv`，安装运行时依赖，输出心跳和下载速度。 |
| `src/drawai/local_cli.py` | `drawai setup local` 接入 Python-native setup；`drawai doctor local` 增加 600s SDK 探测、Windows Codex auth 路径识别。 |
| `src/drawai/server_cli.py` | `drawai workbench` 在 Windows 上原生拉起模型服务、Workbench API、Vite 前端；非 Windows 保留脚本 launcher。 |
| `src/drawai/_local_runtime_fs.py`、`src/drawai/local_runtime.py` | 统一 runtime 文件路径和 Windows/Linux venv bin 路径。 |
| `src/drawai/codex_python_sdk_svg.py` | Codex SDK 使用隔离 `CODEX_HOME`；doctor 探针改成兼容当前 SDK 的 `low` effort；保留 600s 超时。 |
| `src/drawai/pipeline.py` | SVG 生成失败/超时后重建 Codex session，并恢复最新验证通过的部分 SVG。 |
| `src/drawai/workbench/runner.py` | SVG 重跑归档支持 Windows 长路径，跳过浏览器临时目录，错误信息优先返回结构化异常。 |
| `configs/drawai/*.yaml` | 本地 OCR/模型/Codex 相关 timeout 调整到 600s。 |
| `tests/...` | 增加 Windows native launcher、Linux launcher 保持不变、SVG 超时恢复、SVG 归档、Codex auth 路径等回归测试。 |

## 3. 新 Windows 电脑前置条件

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

## 4. 准备 Codex 认证

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

## 5. 获取代码

```powershell
git clone <your-drawai-repo-url> DrawAI-dev
cd DrawAI-dev
```

后续命令都在仓库根目录执行。

## 6. 先 dry-run，不安装任何东西

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

## 7. 安装 runtime 和模型

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
- 如果 600s 内没有进展，优先检查网络、代理、杀毒软件扫描、模型源可访问性。

## 8. 验证 runtime

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

## 9. 启动完整 Workbench

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

## 10. 健康检查

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

## 11. 跑一个真实 Workbench 任务

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

## 12. 分离部署

如果模型服务已经在别的机器运行：

```powershell
uv run --python 3.12 drawai workbench --model-api http://<model-host>:18080
```

如果已经有 Workbench API，只启动前端：

```powershell
uv run --python 3.12 drawai workbench --api http://<api-host>:8890
```

Windows frontend-only 路径会直接在 `apps/workbench` 下调用 `npm.cmd`。

## 13. 常见问题

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

### SVG 生成 600s 超时

当前实现会先丢弃死掉的 Codex session 再重试。如果 Codex 已经写出验证通过的 `semantic_N.svg`，会自动提升为最终 `semantic.svg`。

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

## 14. 新机器最短可执行清单

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

## 15. 本次验证命令

本次 Windows 主机上已通过：

```powershell
uv run --python 3.12 python -m compileall `
  src\drawai\server_cli.py `
  src\drawai\local_cli.py `
  src\drawai\local_setup.py `
  src\drawai\pipeline.py `
  src\drawai\workbench\runner.py `
  tests\semantic_ppt\drawai_pipeline\test_cli_pipeline.py `
  tests\semantic_ppt\drawai_pipeline\test_local_runtime_setup.py `
  tests\semantic_ppt\drawai_pipeline\test_python_sdk_svg_adapter.py `
  tests\workbench\test_store_api.py
```

```powershell
uv run --python 3.12 pytest `
  tests\semantic_ppt\drawai_pipeline\test_cli_pipeline.py::test_workbench_uses_linux_shell_launcher_when_not_windows `
  tests\semantic_ppt\drawai_pipeline\test_cli_pipeline.py::test_workbench_frontend_only_uses_shared_launcher `
  tests\semantic_ppt\drawai_pipeline\test_cli_pipeline.py::test_workbench_frontend_only_uses_native_npm_on_windows `
  tests\semantic_ppt\drawai_pipeline\test_cli_pipeline.py::test_workbench_native_uses_runtime_python_for_api `
  tests\semantic_ppt\drawai_pipeline\test_cli_pipeline.py::test_default_svg_invoker_recreates_codex_session_after_failure `
  tests\semantic_ppt\drawai_pipeline\test_cli_pipeline.py::test_default_svg_invoker_recovers_valid_partial_codex_svg_after_timeout `
  tests\semantic_ppt\drawai_pipeline\test_local_runtime_setup.py::test_doctor_reports_codex_auth_file_from_windows_userprofile `
  tests\semantic_ppt\drawai_pipeline\test_local_runtime_setup.py::test_doctor_codex_auth_candidates_include_path_home_fallback `
  tests\semantic_ppt\drawai_pipeline\test_python_sdk_svg_adapter.py::test_codex_python_sdk_connectivity_probe_runs_low_effort_turn `
  tests\workbench\test_store_api.py::test_runner_archives_existing_svg_outputs_before_rerun
```

```powershell
uv run --python 3.12 drawai setup local --dry-run
uv run --python 3.12 drawai doctor local
Invoke-RestMethod http://127.0.0.1:18080/health
Invoke-RestMethod http://127.0.0.1:8890/api/health
(Invoke-WebRequest http://127.0.0.1:5174/).StatusCode
```

当前 Windows 验证结果：

```text
doctor: status ok, ready 18/18
model runtime: status ok
Workbench API: status ok
frontend: HTTP 200
real case: completed
```
