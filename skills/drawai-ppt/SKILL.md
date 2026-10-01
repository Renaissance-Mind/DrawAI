---
name: drawai-ppt
description: "Create and edit native PowerPoint PPTX with DrawAI's Python tools, reuse existing templates, insert editable SVG diagrams, and extend the supporting Python code when a requested object or style needs additional support."
---

# DrawAI PPT

使用 Python 创建和编辑可继续加工的 PPTX。已有模板以原文件为基础修改；新图形复用 DrawAI 的 SVG → DrawingML 转换器。交付实际 PPTX 和检查过的预览。

此 skill 独立维护在 `skills/drawai-ppt/`，使用本仓库的 Python 引擎。其他能够读取 skill、执行 Python 的 Agent 也可使用。依赖见仓库 `pyproject.toml`；不需要 Codex 专属的演示文稿运行时。

## 使用入口

在 DrawAI 根目录运行：

```bash
uv run python skills/drawai-ppt/scripts/ppt.py --help
uv run python skills/drawai-ppt/scripts/ppt.py schema --mode create
uv run python skills/drawai-ppt/scripts/ppt.py schema --mode edit
```

已有可用 Python 环境时可直接执行该脚本。它根据自身位置查找仓库源代码，不要求当前目录是仓库，也不要求先安装 DrawAI 包。若 skill 被复制到其他位置，使用 `--repo-root /path/to/DrawAI` 指向代码所在 checkout。

按任务读取 [创建与编辑流程](references/workflows.md)。需要新能力或修改实现时，再读 [代码扩展指南](references/code-map.md)。运行 `schema` 获取当前实际契约，不依赖过时的参数印象。

## 创建 PPT

理解用户内容、页数、受众和提供的设计参考。把内容组织成各页，选择合适的字号、层级和版面。用户给出模板时采用下面的模板流程。

创建计划使用 `drawai.pptx_create_plan.v1`，指定画布、初始 `slide_count` 和对象操作。用 `add_text`、`add_shape`、`add_image`、`add_table`、`add_chart` 创建对应的原生对象；示意图、曲线、复杂矢量装饰使用 `add_svg`。

```bash
uv run python skills/drawai-ppt/scripts/ppt.py create \
  --plan create-plan.json --output output/deck.pptx --report output/create-report.json
```

需要计划以外的精细排版或对象属性时，可在任务目录写 Python 制作脚本，使用 `drawai.pptx_editing` 和 `python-pptx` 的对象 API。SVG 只承担适合矢量绘图的部分。表格和数据图表应保留其原生对象与数据，用户要求图片表示时遵循用户要求。

## 编辑现有 PPT 或模板

先检查实际文件及相关页面的渲染，确认尺寸、文字、对象 ID、母版、版式、字体、图片裁剪和固定品牌元素。完整改编模板时检查每页后选择可复用的页面或版式。

```bash
uv run python skills/drawai-ppt/scripts/ppt.py inspect template.pptx \
  --output work/template.json --preview-dir work/before
uv run python skills/drawai-ppt/scripts/ppt.py edit template.pptx \
  --plan edit-plan.json --output output/edited.pptx --report output/edit-report.json
```

编辑计划使用 `drawai.pptx_edit_plan.v1`。采用检查结果中的页面内 `shape_id`、`layout_id` 和可选 `source_sha256`。新文件名保护原件；有多个页面使用同一母版时，局部内容编辑落在具体页面，整体设计变更才修改共享母版。

`replace_text` 用于保留混合文字样式；`set_text` 替换整个文本框，沿用对应段落和首个文字 run 的样式。图片替换保留框和裁剪或显式选择新的适配方式。原生表格、图表修改其内容或数据。`duplicate_slide` 复用示例页并独立复制可变图表、工作簿与备注；`add_slide` 采用模板实际存在的版式。

## 检查与交付

```bash
uv run python skills/drawai-ppt/scripts/ppt.py validate output/deck.pptx
uv run python skills/drawai-ppt/scripts/ppt.py render output/deck.pptx --output-dir work/final-preview
```

渲染使用 LibreOffice 和 Poppler，可通过 `--renderer`、`--rasterizer` 指定实际可执行文件。检查每页的换行、裁剪、遮挡、连接线、图表数据和视觉层级。编辑任务与原页面对照。存在差异时修改制作代码或计划并导出新版本，直到满足用户要求。包校验通过只说明文件结构可用，图片预览不能证明表格或图表可编辑；重新检查对象结构与数据。

交付最终 PPTX，按需要附 PDF、预览和可重复执行的制作脚本或计划。说明实际验证方式和影响使用的具体限制。缺少渲染器或目标 PowerPoint 环境时保留文件，如实标记尚未完成的验证，不把未验证结果表述为完全保真。

## 扩展代码

现有接口不能表达用户明确要求的功能时，先判断对象 API 或当前 SVG 转换器能否实现；再对相关 Python 实现做必要扩展。为请求选择合适的原生对象和样式，不用截图覆盖需要继续编辑的文字、表格或结构。

扩展时同步更新操作契约、执行逻辑、使用说明和必要的真实 PPTX 回归测试。新操作或复杂模板保留能力完成后，用实际导出文件验证。源码位置、添加操作的方法、测试与验证命令见 [代码扩展指南](references/code-map.md)。
