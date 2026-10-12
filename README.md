<h1 align="center">DrawAI：让位图可编辑</h1>

<p align="center">
  <a href="https://github.com/Renaissance-Mind/DrawAI"><img alt="Repository" src="https://img.shields.io/badge/repo-DrawAI-111827"></a>
  <a href="https://drawai.renaissancemind.ai/demo"><img alt="Demo" src="https://img.shields.io/badge/demo-online-F59E0B"></a>
  <a href="https://drawai.renaissancemind.ai"><img alt="Website" src="https://img.shields.io/badge/website-DrawAI-0EA5E9"></a>
  <a href="https://arxiv.org/abs/2608.00548"><img alt="arXiv:2608.00548" src="https://img.shields.io/badge/arXiv-2608.00548-DC2626"></a>
  <a href="https://huggingface.co/datasets/caopu/DrawAI-Bench-Lite"><img alt="Hugging Face Dataset" src="https://img.shields.io/badge/Hugging%20Face-Dataset-FFD21E?logo=huggingface"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.12%2B-2563EB">
  <img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-7C3AED">
  <a href="README-en.md">English</a>
</p>

**DrawAI 把一张位图论文图、技术图或幻灯片截图，重建成可编辑的 SVG 和 PPTX。**

同一套 DrawAI 可在 Agent Session、浏览器 Workbench 和 CLI 中使用，支持页面设计、原生 PPT 编辑，以及将位图拆成可继续编辑的结构、文字和局部素材。

<a id="demo"></a>
## 🎬 演示

https://github.com/user-attachments/assets/bca69174-10d6-44c4-a73e-7b95e8eefde9

<a id="news"></a>
## 🔥 News

- **2026.08** — DrawAI 论文《[DrawAI: Agentic Benchmark and Workflow for Making Raster Images Editable](https://arxiv.org/abs/2608.00548)》已在 arXiv 上线，欢迎阅读。
- **2026.08** — 新增 LLM API 支持，支持 Agent SDK 与 API 执行。

<a id="quick-start"></a>
## ⚡ 快速上手

安装一次 DrawAI，再按需求启用 Session、Workbench 或 CLI。图像可使用当前会话能力或外接 API；Session 最终制作默认保留当前 Agent 的模型和配置。

### 安装

在当前代码目录执行，源码安装需要 Node.js 20.19+ 或 22.12+，前端由安装过程构建：

```bash
uv tool install --python 3.12 .
drawai setup
drawai doctor
```

已有 wheel 可直接安装，用户运行时无需 Node.js 或源码目录。完整安装、更新、已有数据复用和依赖启用见[统一安装指南](docs/zh-CN/installation.md)。

### 在 Agent Session 使用

```bash
drawai setup --agent codex
# Claude Code 使用：drawai setup --agent claude
```

打开新会话，使用 `$drawai-readme` 并提供材料与要求。图像生成可用宿主工具或用户配置的 Images API。默认由当前 Claude、Codex 或其他具备能力的 Agent 制作；用户明确选择其他执行方式时才切换。

### 在 Workbench 使用

```bash
drawai setup --enable workbench
drawai workbench
```

打开 `http://127.0.0.1:8890/`。工作台使用安装包内预构建的前端，与 CLI/Session 共用配置、模板和工具。可生成图片、批量转换、配置处理器和查看阶段进度。本地模型、SDK、预览与公式依赖按需启用。

### 在 CLI 使用

```bash
drawai config connections --import connections.json
drawai image generate --connection my-images --prompt "实际页面内容" --output-dir visuals
drawai presentation export deck.document.json --pptx output/deck.pptx
```

上面的连接 ID 和输入文件来自实际配置与任务。CLI 原生编辑使用 `drawai ppt create/edit`，图像清单使用 `drawai visual`，委托转换使用 `drawai flow`。原有 `drawai run <image> --local` 与分阶段命令保持兼容；本地视觉模型可以通过 `drawai setup --enable models` 准备。

### 共同配置与依赖

默认数据目录是 `~/.drawai`，可用 `DRAWAI_HOME` 覆盖。Workbench 设置、`drawai config` 和 Session 工具使用同一连接目录。当前会话的实施模型仍由宿主决定；独立运行从共同配置选择执行后端。

```bash
drawai setup --enable preview --install-system
drawai setup --enable llm
drawai doctor --require preview
```

基础安装包括原生 PPT 工具、Session 规划、模板与 Images API。Workbench、LLM/Agent SDK、本地视觉模型和系统预览工具按需准备。模型权重与 GPU 环境只在所选处理器需要时安装。服务端可用仓库 Dockerfile 部署同一发行包；当前是受控单工作区服务，多用户服务能力另见安装指南。

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
  drawai_package.json
  elements/E001/element.json
  elements/E001/asset_package.json
  reports/svg_validation_report.json
  reports/svg_to_ppt_export_report.json
  svg/semantic.svg
  svg/rendered.png
  exports/
```

`drawai_package.json` 是运行级索引，`elements/<element_id>/asset_package.json` 是元素级素材包。Workbench 会保留旧版本结果的展示和下载入口；这类历史结果不会再进入 `asset process`、`compose` 或 `export` 的二次处理链路。

Workbench 的任务和上传文件默认写到：

```text
~/.drawai/workbench/
```

## 💬 联系我们

欢迎通过 [GitHub Issue](https://github.com/Renaissance-Mind/DrawAI/issues) 反馈问题，也欢迎直接提交 PR。想参与测试或了解最新进展，也可以扫码加入 DrawAI 微信群。

<p align="center">
  <img src="wechat.jpg" alt="DrawAI 微信群二维码" width="260">
</p>

## 🧩 结果是什么形态

DrawAI 的目标不是把原图简单塞进 PPT，而是尽量生成可编辑、可检查、可继续加工的结果：

- `package`：完整运行数据包，记录元素、素材、处理结果和导出状态
- `svg`：主要可编辑矢量结果
- `pptx`：可直接进入幻灯片流程的导出结果
- `psd`：TODO

当前 PPTX 导出固定使用内置 native-shape converter，将 SVG primitives、文本和局部图片转成 PowerPoint 原生 DrawingML 形状和图片；不再提供 SVG 嵌入或外部转换器切换。

## 📚 更多文档

- [drawai-image2ppt：图像转 PPT、原生编辑与工具包](skills/drawai-image2ppt/SKILL.md)
- [编辑现有 PPTX 模板：对象检查、原生编辑与 SVG 插入](docs/zh-CN/pptx-editing.md)
- [运行方式、参数、端口和模型路径](docs/zh-CN/runtime-options.md)
- [评测指南：数据集、单图与批量 SVG 评测](docs/zh-CN/evaluation.md)
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

## 引用

```bibtex
@article{cao2026drawai,
  title={DrawAI: Agentic Benchmark and Workflow for Making Raster Images Editable},
  author={Cao, Pu and Kong, Qingye and Yin, Xuedan and Zhao, Xuekun and Yan, Rupeng and Song, Qing and Zhang, Yao and Yang, Lu},
  journal={arXiv preprint arXiv:2608.00548},
  year={2026}
}
```
