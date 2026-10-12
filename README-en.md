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

Use the same DrawAI installation in an Agent Session, the browser Workbench or CLI to design presentations, edit native PowerPoint objects and reconstruct raster figures.

<a id="demo"></a>
## 🎬 Demo

https://github.com/user-attachments/assets/bca69174-10d6-44c4-a73e-7b95e8eefde9

<a id="news"></a>
## 🔥 News

- **2026.08** — Our paper, [*DrawAI: Agentic Benchmark and Workflow for Making Raster Images Editable*](https://arxiv.org/abs/2608.00548), is now available on arXiv.
- **2026.08** — Added support for LLM APIs, with Agent SDK and API execution options.

<a id="quick-start"></a>
## ⚡ Quick Start

Install DrawAI once, then enable Session, Workbench or CLI capabilities. Images may use host tools or a user API; Session implementation defaults to the current Agent's model and configuration.

### Install

From this checkout, with Node.js 20.19+ or 22.12+ available for the source frontend build:

```bash
uv tool install --python 3.12 .
drawai setup
drawai doctor
```

Prebuilt wheels need neither Node.js nor the source checkout at runtime. See [unified installation](docs/en/installation.md) for updates, existing data and optional dependencies.

### Agent Session

```bash
drawai setup --agent codex
# Claude Code: drawai setup --agent claude
```

Open a new chat with `$drawai-readme` and provide your materials and goal. Image generation can use host tools or a configured Images API. The current Claude, Codex or other capable Agent performs final authoring; an executor changes only when explicitly selected by the user.

### Workbench

```bash
drawai setup --enable workbench
drawai workbench
```

Open `http://127.0.0.1:8890/`. The packaged UI shares core tools, templates and configuration with Session and CLI. Generate images, process batches, configure processors and inspect progress. Local models, SDKs and preview tools are enabled only when needed.

### CLI

```bash
drawai config connections --import connections.json
drawai image generate --connection my-images --prompt "Actual page content" --output-dir visuals
drawai presentation export deck.document.json --pptx output/deck.pptx
```

Use actual connection IDs and task files. Native editing uses `drawai ppt create/edit`, visual manifests use `drawai visual`, and delegated conversion uses `drawai flow`. Existing `drawai run <image> --local` and stage commands remain compatible; optional local models can be prepared with `drawai setup --enable models`.

### Shared configuration and capabilities

`DRAWAI_HOME` defaults to `~/.drawai`. Workbench settings, `drawai config` and Session tools use the same connection files. Session implementation retains the host's real configuration; standalone execution uses the shared configured backend.

```bash
drawai setup --enable preview --install-system
drawai setup --enable llm
drawai doctor --require preview
```

The base package contains presentation tools, Session planning, templates and Images API support. Workbench, Agent SDKs, local models and OS preview tools are optional. The Dockerfile deploys the same distribution as a controlled single-workspace service; multi-user service requirements are documented in the installation guide.

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
~/.drawai/workbench/
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

- [drawai-image2ppt: conversion, native editing, and the Python toolkit](skills/drawai-image2ppt/SKILL.md)
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
