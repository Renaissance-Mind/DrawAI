---
name: drawai-ppt
description: "Create and edit native PowerPoint PPTX with Python, reuse templates, insert editable SVG diagrams, and extend the included implementation using a PPTX-first property and capability specification."
---

# DrawAI PPT

创建和编辑可继续加工的 PPTX，交付实际文件和检查过的预览。文字、形状、表格和图表保留原生对象；SVG 示意图转换为可编辑的文字、路径、形状和图片。

## 标准与实现范围

完整文档模型以 PPTX 的设置和原生语义为主要目标。设计或扩展功能时读取 [统一文档规范](references/pptx-standard.md) 和 [属性/导出能力矩阵](references/export-capabilities.md)。需要精确原生字段时按名称搜索 [微软 Schema 清单](references/pptx-inventory/schema-properties.csv)。来源与覆盖限制见 [研究来源](references/research-sources.md)。

规范和矩阵是研究目标；当前命令处理创建/编辑操作计划。完整统一文档模型、全部属性映射和静态 SVG 导出器尚未实现。按实际对象、属性和值域判断能力，缺失功能明确扩展或报告，不能把设计目标声明为已支持。

## 环境与入口

使用 Python 3.12 或更新版本，将整个 skill 目录放在所需位置，安装其依赖：

```bash
python -m pip install -r <skill-dir>/scripts/requirements.txt
python <skill-dir>/scripts/ppt.py --help
python <skill-dir>/scripts/ppt.py schema --mode create
python <skill-dir>/scripts/ppt.py schema --mode edit
```

所有实现位于目录内的 `scripts/pptx_skill/`，命令可在任意工作目录运行。渲染需要 LibreOffice `soffice` 和 Poppler `pdftoppm`，公式转换需要 Pandoc。可使用 PATH 中的工具，渲染器也接受显式路径。

按任务读取 [创建与编辑流程](references/workflows.md)。需要修改实现时读取 [代码扩展指南](references/code-map.md)，在 skill 目录内维护代码。

## 创建和编辑

根据用户内容、页数、受众与设计要求组织文稿。创建计划采用 `pptx.create_plan.v1`，设置画布、初始页数和原生对象操作。已有模板先检查真实对象和页面，再用 `pptx.edit_plan.v1` 及实际 ID 修改副本。

```bash
python <skill-dir>/scripts/ppt.py create --plan create-plan.json --output output/deck.pptx
python <skill-dir>/scripts/ppt.py inspect template.pptx --output work/template.json --preview-dir work/before
python <skill-dir>/scripts/ppt.py edit template.pptx --plan edit-plan.json --output output/edited.pptx
```

`replace_text` 保留混合 run 样式；`set_text` 设置全文并沿用对应段落和首个 run 的样式。表格和图表修改其原生数据。复制页面保留布局并独立复制可变图表、工作簿和备注。局部内容编辑作用于具体页面，整体设计变更才修改共享母版或版式。保留原件，导出到新文件。

需要精细的富文本、主题或图表样式时，在任务目录编写 Python 制作脚本，使用 `pptx_skill` 和 `python-pptx` 对象 API。可复用的新能力加入 skill 内部实现；同步操作契约、使用说明和真实文件测试。

## 验证与交付

```bash
python <skill-dir>/scripts/ppt.py validate output/deck.pptx
python <skill-dir>/scripts/ppt.py render output/deck.pptx --output-dir work/final-preview
python <skill-dir>/scripts/check.py
```

检查每页的文字换行、裁剪、遮挡、连接线、数据和视觉层级。编辑任务对照原件；发现差异后修改计划或制作脚本，导出新版本并再次检查。包校验验证结构，重新检查原生对象和数据验证可编辑性。

交付 PPTX，按需要附 PDF、预览和可重复执行的计划或脚本。说明实际完成的检查。没有渲染器或目标 PowerPoint 环境时保留文件，明确尚未完成的验证。
