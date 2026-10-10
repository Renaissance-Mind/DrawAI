<h1 align="center">DrawAI: Make Raster Figures Editable</h1>

<p align="center">
  <a href="https://github.com/Renaissance-Mind/DrawAI"><img alt="Repository" src="https://img.shields.io/badge/repo-DrawAI-111827"></a>
  <a href="https://drawai.renaissancemind.ai/demo"><img alt="Demo" src="https://img.shields.io/badge/demo-online-F59E0B"></a>
  <a href="https://drawai.renaissancemind.ai"><img alt="Website" src="https://img.shields.io/badge/website-DrawAI-0EA5E9"></a>
  <a href="https://arxiv.org/abs/2608.00548"><img alt="arXiv:2608.00548" src="https://img.shields.io/badge/arXiv-2608.00548-DC2626"></a>
  <a href="https://huggingface.co/datasets/caopu/DrawAI-Bench-Lite"><img alt="Hugging Face Dataset" src="https://img.shields.io/badge/Hugging%20Face-Dataset-FFD21E?logo=huggingface"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.12%2B-2563EB">
  <img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-7C3AED">
  <a href="README.md">简体中文</a>
</p>

**DrawAI turns raster paper figures, technical diagrams, and slide screenshots into editable SVG and PPTX artifacts.**

It decomposes input images into structure, text, and local assets, then generates vector results that are easier to keep editing. Use it as a CLI, or start the Workbench in the browser for batch uploads, progress tracking, and artifact management.

<a id="demo"></a>
## 🎬 Demo

https://github.com/user-attachments/assets/bca69174-10d6-44c4-a73e-7b95e8eefde9

<a id="news"></a>
## 🔥 News

- **2026.08** — Our paper, [*DrawAI: Agentic Benchmark and Workflow for Making Raster Images Editable*](https://arxiv.org/abs/2608.00548), is now available on arXiv.
- **2026.08** — Added support for LLM APIs, with Claude Code SDK as the default inference backend.

<a id="quick-start"></a>
## ⚡ Quick Start

### Option 1: Codex plugin

The DrawAI plugin contains three skills: `drawai` is the entry guide, `drawai-templates` recommends and displays real visual references, and `drawai-ppt` creates and edits editable PowerPoint. Browse templates inline in Codex, choose layout and style references, then continue creating the deck in the current conversation.

```bash
cd apps/workbench
npm ci
npm run build:plugin
cd ../..
node scripts/install_plugin.mjs
```

Open a new Codex chat and start with `$drawai`. Ask for templates for a research talk or provide your content and request an editable presentation. Template selection uses an inline chooser; presentation creation uses `drawai-ppt` directly.

See the [plugin guide](docs/zh-CN/plugin.md) for installation, skill responsibilities, and the standalone template website.

### Option 2: 🧑‍💻 Browser workbench

Use the browser workbench for raster reconstruction, batch uploads, and pipeline progress:

```bash
uv run drawai setup local
uv run drawai workbench
```

Open `http://127.0.0.1:5174/`. See the [runtime options](docs/zh-CN/runtime-options.md) for remote deployment, model services, and port configuration.

### Option 3: 🖥️ CLI

This is the simplest single-machine path and the best way to confirm that DrawAI runs correctly.

```bash
uv run drawai setup local
uv run drawai run examples/demo_figure.png --local
```

`setup local` automatically runs a doctor check after it finishes.

Run your own image:

```bash
uv run drawai run /path/to/your/image.png --local --run-name my_first_drawai_run
```

Use the same device profile during setup and runtime when you want NVIDIA GPU or Apple Silicon MPS support:

```bash
uv run drawai setup local --device gpu
uv run drawai run /path/to/your/image.png --local --device gpu
```

```bash
uv run drawai setup local --device mps
uv run drawai run /path/to/your/image.png --local --device mps
```

## 🧰 Requirements

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- Node.js 20.19+ or 22.12+ for the Workbench frontend
- Working Codex/OpenAI authentication, or a configured Agent CLI/ACP Agent such as Kimi (`kimi`), Claude (`claude`), Codex (`codex exec`), OpenClaw (`openclaw agent`), Hermes (`hermes chat`), or OpenHands (`openhands acp`), for run0 asset analysis and SVG generation
- >8 GB disk space for model weights and the installed runtime environment

The default local runtime directory is:

```text
.local/drawai_runtime/
```

It is not tracked by git. Model downloads use ModelScope by default. See [runtime options](docs/zh-CN/runtime-options.md) for Hugging Face downloads, manual model paths, Torch backend selection, custom ports, and other advanced settings.

### Choose Codex SDK, Agent CLI, Or ACP Agent

The default config continues to use the Codex Python SDK. To use a direct CLI instead, switch the SVG backend and runtime provider to `agent_cli`, then choose `kimi`, `claude`, `codex`, `openclaw`, `hermes`, or a custom command under `model_runtime.cli`:

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

The Agent CLI path is used for both run0 asset analysis and SVG generation. No config change is needed when staying on the Codex SDK. For Claude, Codex, OpenClaw, or Hermes CLI, change `agent` and `command` to the corresponding command, for example `claude`, `codex exec`, `openclaw agent`, or `hermes chat`.

OpenHands connects over the ACP JSON-RPC stdio protocol. After installing OpenHands and completing its own ChatGPT subscription authorization, select the built-in `openhands` preset; its default command is `openhands acp --always-approve`:

```yaml
svg:
  generation_backend: acp_agent
model_runtime:
  provider: acp-agent
  connection_id: openhands
  acp:
    agent: openhands
```

OpenHands keeps separate OAuth credentials under `~/.openhands`; do not copy `~/.codex/auth.json`. See the [runtime options](docs/zh-CN/runtime-options.md#openhands-acp-后端) for the currently verified install, authorization, and compatibility commands.

<a id="outputs"></a>
## 📦 Output Locations

CLI runs write timestamped folders under:

```text
runs/<date>/<time>_<run-name>/
```

The most useful files are usually:

```text
reports/run_summary.json
outputs/case_001_*/
  reports/pipeline_summary.json
  drawai_package.json
  elements/E001/element.json
  elements/E001/asset_package.json
  reports/svg_validation_report.json
  reports/svg_to_ppt_export_report.json
  svg/semantic.svg
  svg/rendered.png
  exports/
```

`drawai_package.json` is the run-level index, and `elements/<element_id>/asset_package.json` stores the package for each element. The Workbench keeps legacy results visible and downloadable, but legacy run roots are read-only for the new asset processing, compose, and export commands.

Workbench tasks and uploaded files are stored by default under:

```text
.local/workbench/
```

## 💬 Contact Us

Feel free to open a [GitHub issue](https://github.com/Renaissance-Mind/DrawAI/issues) or submit a PR. You can also scan the QR code to join the DrawAI WeChat group for testing and updates.

<p align="center">
  <img src="wechat.jpg" alt="DrawAI WeChat group QR code" width="260">
</p>

## 🧩 Artifact Types

DrawAI is not meant to simply place the original bitmap into a PowerPoint file. It tries to produce artifacts that are editable, inspectable, and suitable for further work:

- `package`: the complete run data package with elements, assets, processing results, and export state
- `svg`: the primary editable vector result
- `pptx`: export artifact ready for slide workflows
- `psd`: TODO

The PPTX export path always uses the bundled native-shape converter, mapping SVG primitives, text, and local images to PowerPoint native DrawingML shapes and images. SVG embedding and external converter switching are no longer exposed.

## 📚 Documentation

- [drawai-ppt standalone skill: create/edit PPTX with Python and extend the implementation](skills/drawai-ppt/SKILL.md)
- [Edit existing PPTX templates: inspect objects, edit native content and insert SVG](docs/en/pptx-editing.md)
- [Runtime options, ports, and model paths](docs/zh-CN/runtime-options.md)
- [Evaluation guide: dataset, single-image and batch SVG evaluation](docs/en/evaluation.md)
- [Changelog](CHANGELOG.md)

## ❓ FAQ

**Q: What should I do if I see `Refresh Codex login or set a working OPENAI_API_KEY before SVG generation.`?**

A: Log in to Codex again before setup:

```bash
codex login
```

## 🙏 Acknowledgements

DrawAI's design and implementation were informed by ideas and practices from these open-source projects:

- [hugohe3/ppt-master](https://github.com/hugohe3/ppt-master)
- [ningzimu/image-to-editable-ppt-skill](https://github.com/ningzimu/image-to-editable-ppt-skill)
- [llmsresearch/paperbanana](https://github.com/llmsresearch/paperbanana)
- [ResearAI/AutoFigure-Edit](https://github.com/ResearAI/AutoFigure-Edit)

## ⚖️ License And Commercial Use

DrawAI source code is released under Apache-2.0. The source-code license permits commercial use, modification, and redistribution.

Third-party models, model weights, fonts, and external services follow their own upstream terms.

## Citation

```bibtex
@article{cao2026drawai,
  title={DrawAI: Agentic Benchmark and Workflow for Making Raster Images Editable},
  author={Cao, Pu and Kong, Qingye and Yin, Xuedan and Zhao, Xuekun and Yan, Rupeng and Song, Qing and Zhang, Yao and Yang, Lu},
  journal={arXiv preprint arXiv:2608.00548},
  year={2026}
}
```
