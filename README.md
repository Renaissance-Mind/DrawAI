DrawAI turns raster images, including AI-generated figures such as GPT-Image and Nano Banana outputs and screenshots of paper figures or slides, into editable SVG and PPTX for people making slides and scientific figures.

[简体中文](README.zh-CN.md)

<h1 align="center">DrawAI: Make Raster Figures Editable</h1>

<p align="center">
  <a href="https://github.com/Renaissance-Mind/DrawAI"><img alt="Repository" src="https://img.shields.io/badge/repo-DrawAI-111827"></a>
  <a href="https://drawai.renaissancemind.ai/demo"><img alt="Demo" src="https://img.shields.io/badge/demo-online-F59E0B"></a>
  <a href="https://drawai.renaissancemind.ai"><img alt="Website" src="https://img.shields.io/badge/website-DrawAI-0EA5E9"></a>
  <a href="https://arxiv.org/abs/2608.00548"><img alt="arXiv:2608.00548" src="https://img.shields.io/badge/arXiv-2608.00548-DC2626"></a>
  <a href="https://huggingface.co/datasets/caopu/DrawAI-Bench-Lite"><img alt="Hugging Face Dataset" src="https://img.shields.io/badge/Hugging%20Face-Dataset-FFD21E?logo=huggingface"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.12%2B-2563EB">
  <img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-7C3AED">
  <a href="README.zh-CN.md">简体中文</a>
</p>

Use the same DrawAI installation in an Agent Session, the browser Workbench, or the CLI to design presentations, edit native PowerPoint objects, and reconstruct raster figures into text, shapes, and local assets you can keep editing.

<a id="demo"></a>
## 🎬 Demo

https://github.com/user-attachments/assets/bca69174-10d6-44c4-a73e-7b95e8eefde9

<a id="news"></a>
## 🔥 News

- **2026.08** — Our paper, [*DrawAI: Agentic Benchmark and Workflow for Making Raster Images Editable*](https://arxiv.org/abs/2608.00548), is now available on arXiv.
- **2026.08** — Added support for LLM APIs, with Agent SDK and API execution options.

<a id="paper"></a>
## Numbers from the paper

These figures are taken from [*DrawAI: Agentic Benchmark and Workflow for Making Raster Images Editable*](https://arxiv.org/abs/2608.00548) (arXiv:2608.00548). They are not re-estimated here.

- DrawAI-Bench has **80** images: scientific figures, presentation slides, posters, and diagrams, with 10 real and 10 AI-generated images in each domain (Section 3.1). The public dataset documented in this repo, [DrawAI-Bench-Lite](https://huggingface.co/datasets/caopu/DrawAI-Bench-Lite), also contains 80 images (`0001`–`0080`); see the [evaluation guide](docs/en/evaluation.md).
- The protocol has **39** criteria: 9 deterministic rule-based metrics and 30 rubric judgments, covering Fidelity and Editability (Section 3.2).
- The paper evaluates **13** models across **5** agent harnesses (Section 5.1).
- A human study used the same **200** reconstructed artifacts. Five experts gave **1,000** PPTX ratings. The mean score is **3.27**, and **79.8%** meet the usable threshold (score ≥ 3). The mean human score correlates with Overall at Spearman **ρ = 0.94** (Section 5.2, Table 1).
- Across paired outputs, DrawAI-Flow raises Fidelity from **75.7** to **78.7** and Editability from **56.4** to **74.0** relative to a direct Simple Baseline (Section 5.5).
- With GPT-5.5 on that same 80-image panel, DrawAI scores **91.0** Overall (**92.8** Fidelity, **89.1** Editability), compared with **73.7** for Crafter, **73.4** for AutoFigure-Edit, and **41.0** for Edit-Banana. DrawAI is best on **35 of 39** criteria (Section 5.7).

<a id="quick-start"></a>
## ⚡ Quick Start

Install DrawAI once, then enable Session, Workbench, or CLI capabilities. Images may use host tools or a user API. Session implementation defaults to the current Agent's model and configuration.

### Install

After a maintainer publishes a `v*` tag whose name matches `[project].version` in `pyproject.toml`, GitHub Actions publishes a wheel to PyPI. That wheel already contains the Workbench UI, so Node.js is not required:

```bash
pip install drawai
uvx drawai --help
drawai setup
drawai doctor
```

`uvx drawai` runs the same `drawai` console script. Until that release is on PyPI, install from this checkout. A source install, and an install from the PyPI source distribution, compiles the Workbench UI while building the wheel and needs Node.js 20.19+ or 22.12+:

```bash
uv tool install --python 3.12 .
drawai setup
drawai doctor
```

`pip install "drawai[workbench]"` (or `drawai setup --enable workbench`) adds the browser UI's Python dependencies. Generation still needs the model or host credentials you configure. See [unified installation](docs/en/installation.md) for updates, existing data, and optional dependencies.

### Agent Session

```bash
drawai setup --agent codex
# Claude Code: drawai setup --agent claude
```

Open a new chat with `$drawai-readme` and provide your materials and goal. Image generation can use host tools or a configured Images API. The current Claude, Codex, or other capable Agent performs final authoring. An executor changes only when you explicitly select one.

### Workbench

```bash
drawai setup --enable workbench
drawai workbench
```

Open `http://127.0.0.1:8890/`. The packaged UI shares core tools, templates, and configuration with Session and CLI. Generate images, process batches, configure processors, and inspect progress. Local models, SDKs, and preview tools are enabled only when needed.

### CLI

```bash
drawai config connections --import connections.json
drawai image generate --connection my-images --prompt "Actual page content" --output-dir visuals
drawai presentation export deck.document.json --pptx output/deck.pptx
```

Use actual connection IDs and task files. Native editing uses `drawai ppt create/edit`, visual manifests use `drawai visual`, and delegated conversion uses `drawai flow`. Existing `drawai run <image> --local` and stage commands remain compatible. Optional local models can be prepared with `drawai setup --enable models`.

### Shared configuration and capabilities

`DRAWAI_HOME` defaults to `~/.drawai`. Workbench settings, `drawai config`, and Session tools use the same connection files. Session implementation retains the host's real configuration. Standalone execution uses the shared configured backend.

```bash
drawai setup --enable preview --install-system
drawai setup --enable llm
drawai doctor --require preview
```

The base package contains presentation tools, Session planning, templates, and Images API support. Workbench, Agent SDKs, local models, and OS preview tools are optional. The Dockerfile deploys the same distribution as a controlled single-workspace service. Multi-user service requirements are documented in the installation guide.

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

**What inputs does DrawAI accept?**

Raster images. That includes AI-generated figures such as GPT-Image and Nano Banana outputs, and screenshots of scientific figures, technical diagrams, slides, posters, and flowcharts. The task starts from pixels. It does not need the original authoring file.

**What does it output?**

A semantic SVG of editable text and vector primitives plus localized images, and a PPTX exported by the bundled native-shape converter to PowerPoint DrawingML shapes and pictures. A run also writes `drawai_package.json` and a per-element asset package. PSD export is not implemented.

**Does it work on screenshots of paper figures?**

Yes. That is one of the inputs the paper and this tool are built for. DrawAI-Bench's scientific figures include images sampled from published papers as well as AI-generated figures (arXiv:2608.00548, Section 3.1). A screenshot is still a raster, so quality depends on the image and on the model, harness, and workflow. In the paper, posters are the hardest domain, and DrawAI-Flow does not improve every image.

**What is the license?**

The source code is Apache-2.0, which permits commercial use, modification, and redistribution. Model weights, fonts, and external services (including SAM, OCR, image models, and LLM APIs) keep their own upstream terms.

**How is this different from simple vectorization?**

Classic vectorization traces pixels into paths. Text can become outlines, and a whole figure can remain one embedded bitmap. The paper treats pasting the source back as a full-page bitmap as a degenerate shortcut: it can look similar while exposing no editable structure (Section 3.2). DrawAI-Flow parses the image with SAM3 and OCR, writes an explicit reconstruction plan, and has an agent emit executable graphics code. That code becomes native SVG text, shapes, connectors, formulas, and localized image crops, which can then be exported to PPTX (Section 4). On the 80-image paired comparison, the workflow mainly lifts Editability (56.4 to 74.0). Fidelity moves from 75.7 to 78.7 (Section 5.5).

**What should I do if I see `Refresh Codex login or set a working OPENAI_API_KEY before SVG generation.`?**

Log in to Codex again before setup:

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

Please cite the paper below if you use DrawAI in research. Machine-readable metadata is in [`CITATION.cff`](CITATION.cff).

## Citation

```bibtex
@article{cao2026drawai,
  title={DrawAI: Agentic Benchmark and Workflow for Making Raster Images Editable},
  author={Cao, Pu and Kong, Qingye and Yin, Xuedan and Zhao, Xuekun and Yan, Rupeng and Song, Qing and Zhang, Yao and Yang, Lu},
  journal={arXiv preprint arXiv:2608.00548},
  year={2026}
}
```
