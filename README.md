<h1 align="center">DrawAI：让位图可编辑</h1>

<p align="center">
  <a href="https://github.com/Renaissance-Mind/DrawAI-dev"><img alt="Repository" src="https://img.shields.io/badge/repo-DrawAI-111827"></a>
  <a href="https://drawai.renaissancemind.ai/demo"><img alt="Demo" src="https://img.shields.io/badge/demo-online-F59E0B"></a>
  <a href="https://drawai.renaissancemind.ai"><img alt="Website" src="https://img.shields.io/badge/website-DrawAI-0EA5E9"></a>
  <img alt="arXiv" src="https://img.shields.io/badge/arXiv-TODO-DC2626">
  <img alt="Python" src="https://img.shields.io/badge/python-3.12%2B-2563EB">
  <img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-7C3AED">
  <a href="README-en.md">English</a>
</p>

**DrawAI 把一张位图论文图、技术图或幻灯片截图，重建成可编辑的 SVG 和 PPTX。**

它会把输入图片拆成结构、文字和局部素材，再生成更容易继续编辑的矢量结果。你可以把它当成一个 CLI，也可以启动 Workbench，在浏览器里批量上传、查看进度和管理结果。

<a id="demo"></a>
## 🎬 演示

https://github.com/user-attachments/assets/59a81ac2-cdbe-49b6-a4fa-8db897afc6bb

<details>
<summary>更新日志</summary>

### 2026-06-18

- 支持 Agent CLI 后端，可用于资产分析和 SVG 生成，已支持 `codex cli`、`claude`、`kimi-code`、`OpenClaw`、`Hermes` 和自定义 agent 命令。
- 支持 Codex SDK 图像生成和编辑，并在 Workbench 中开放相关图像生成流程。
- 支持 Windows 原生部署，包括 packaged Codex CLI 检测、启动器输出刷新、跨平台路径测试和 README 说明。
- 增加 Workbench 运行时和队列状态展示，便于任务运行时查看后端状态。
- 强化继承式 Codex provider 配置，提升本地和嵌套运行配置的解析稳定性。
- 提升 SVG 生成恢复能力，延长 Codex recovery timeout，并在公开路径默认关闭 SAM mask 输出。

### 2026-06-17

- 发布 DrawAI 初始源码快照。
- 在资产 review 中展示 mask 和 polygon 几何，方便在 SVG/PPTX 生成前检查更细的资产边界。

</details>

<a id="roadmap"></a>
## 🗺️ 规划

为了开源版本的稳定性，DrawAI 暂时收起了一些仍在验证中的能力。它们会在跨平台测试、依赖整理和协议确认之后逐步测试并开放。

- [x] 支持 Windows 系统（已支持原生部署，Mac 和 Linux 保持兼容）
- [ ] 支持多边形和不规则 Mask
- [ ] 支持用 GPT-Image-2 重绘素材
- [ ] 支持更复杂的生成模式（各种图像生成 Skill 等）
- [ ] 支持以 Skills 方式使用
- [ ] 支持其他 Agent 和模型（已支持 `codex cli`、`claude`、`kimi-code`、`OpenClaw`、`Hermes`）

> 备注：由于目前删减了 Mask 和重绘能力，对于全图复杂背景的鲁棒性有下降，目前正在火速支持中。

<a id="quick-start"></a>
## ⚡ 快速上手

### 方式一：🧑‍💻 Workbench 图形化工作台

Workbench 会一起启动模型服务、后端 API 和前端页面。它更适合反复测试、批量上传、看阶段进度和检查中间结果。

```bash
uv run drawai setup local
uv run drawai workbench
```

浏览器打开：

```text
http://127.0.0.1:5174/
```

如果要让局域网里的其他机器访问 Workbench，把服务监听到所有网卡：

```bash
uv run drawai workbench --host 0.0.0.0
```

然后用服务器真实 IP 访问，例如：

```text
http://192.168.50.10:5174/
```

更细的远程模型服务、Workbench API 分离部署、端口和配置文件分阶段运行，统一放在[运行参数文档](docs/zh-CN/runtime-options.md)里。

### 方式二：🖥️ CLI 命令行终端

最简单的单机方式，适合先确认项目能不能跑通。

```bash
uv run drawai setup local
uv run drawai run examples/demo_figure.png --local
```

`setup local` 完成后会自动执行一次 doctor 检查。

换成自己的图片：

```bash
uv run drawai run /path/to/your/image.png --local --run-name my_first_drawai_run
```

如果你想用 GPU 或 Apple Silicon MPS，可以在 setup 和 run 时使用同一个设备配置：

```bash
uv run drawai setup local --device gpu
uv run drawai run /path/to/your/image.png --local --device gpu
```

```bash
uv run drawai setup local --device mps
uv run drawai run /path/to/your/image.png --local --device mps
```

## 🧰 运行前需要准备什么

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- Node.js 20.19+ 或 22.12+，仅 Workbench 前端需要
- 可用的 Codex/OpenAI 认证，或已登录/配置的 Agent CLI，例如 Kimi（`kimi`）、Claude（`claude`）、Codex（`codex exec`）、OpenClaw（`openclaw agent`）或 Hermes（`hermes chat`），用于 run0 资产分析和 SVG 生成阶段
- >8GB 磁盘空间以保存模型和安装环境

模型和运行时默认放在：

```text
.local/drawai_runtime/
```

它不会被提交到 git。模型下载默认走 ModelScope；如果你希望用 Hugging Face、手动模型目录、不同 Torch 后端或自定义端口，请看[运行参数文档](docs/zh-CN/runtime-options.md)。

### 选择 Codex SDK 或 Agent CLI

默认配置继续使用 Codex Python SDK。要改用直接 CLI，把配置中的 SVG backend 和 runtime provider 切到 `agent_cli`，再在 `model_runtime.cli` 里选择 `kimi`、`claude`、`codex`、`openclaw`、`hermes` 或自定义命令：

```yaml
svg:
  generation_backend: agent_cli
model_runtime:
  provider: agent-cli
  connection_id: kimi
  cli:
    agent: kimi
    command:
      - kimi
```

Agent CLI 路径会同时用于 run0 资产分析和 SVG 生成；继续使用 Codex SDK 时无需改动默认配置。Claude/Codex/OpenClaw/Hermes CLI 只需要把 `agent` 和 `command` 换成对应命令，例如 `claude`、`codex exec`、`openclaw agent` 或 `hermes chat`。

<a id="outputs"></a>
## 📦 输出结果在哪里

CLI 默认写到：

```text
runs/<date>/<time>_<run-name>/
```

你最常看的文件通常是：

```text
reports/run_summary.json
outputs/case_001_*/
  reports/pipeline_summary.json
  box_ir/box_ir.json
  svg/semantic.svg
  svg/rendered.png
  svg_to_ppt/semantic.svg_to_ppt.pptx
```

Workbench 的任务和上传文件默认写到：

```text
.local/workbench/
```

## 💬 联系我们

欢迎通过 [GitHub Issue](https://github.com/Renaissance-Mind/DrawAI-dev/issues) 反馈问题，也欢迎直接提交 PR。想参与测试或了解最新进展，也可以扫码加入 DrawAI 微信群。

<p align="center">
  <img src="wechat.jpg" alt="DrawAI 微信群二维码" width="260">
</p>

## 🧩 结果是什么形态

DrawAI 的目标不是把原图简单塞进 PPT，而是尽量生成可编辑、可检查、可继续加工的结果：

- `svg`：主要可编辑矢量结果
- `pptx`：可直接进入幻灯片流程的导出结果
- `psd`：TODO

当前 PPTX 导出固定使用内置 native-shape converter，将 SVG primitives、文本和局部图片转成 PowerPoint 原生 DrawingML 形状和图片；不再提供 SVG 嵌入或外部转换器切换。

## 📚 更多文档

- [运行方式、参数、端口和模型路径](docs/zh-CN/runtime-options.md)
- [更新日志](CHANGELOG.md)

## ❓ FAQ

**Q：出现 `Refresh Codex login or set a working OPENAI_API_KEY before SVG generation.` 怎么办？**

A：重新登录 Codex 再进行 setup：

```bash
codex login
```

## 🙏 致谢

DrawAI 的设计和实现参考了这些开源项目的思路与实践：

- [hugohe3/ppt-master](https://github.com/hugohe3/ppt-master)
- [ningzimu/image-to-editable-ppt-skill](https://github.com/ningzimu/image-to-editable-ppt-skill)
- [llmsresearch/paperbanana](https://github.com/llmsresearch/paperbanana)
- [ResearAI/AutoFigure-Edit](https://github.com/ResearAI/AutoFigure-Edit)

## ⚖️ 协议和商用

DrawAI 源码以 Apache-2.0 发布，源码层面允许商用、修改和再分发。

第三方模型、模型权重、字体和外部服务分别遵循各自许可证。
