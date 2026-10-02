---
name: drawai-ppt
description: "Create and edit editable PowerPoint presentations with a self-contained Python toolkit; reuse PPTX templates, reconstruct diagrams from reference images, and export PPTX and SVG from one document model."
---

# DrawAI PPT

这是一个可整体复制使用的 Python 制作工具包。Agent 负责分析内容、设计布局并构建文档；工具包负责生成文件、读取模板和验证输出。

所有创建和修改都使用 `presentation.document.v1`：

- **文档 JSON** 保存页面、对象、文字、样式和素材，是可重复制作的源文件。
- **PPTX** 保存 PowerPoint 中可继续编辑的文字、形状、路径、表格和图表。
- **SVG** 显示某一页的静态外观，并嵌入完整文档源。排版由同一 PPTX 的 LibreOffice 导出完成。

位置、尺寸、字号和线宽统一使用 **pt**。例如 960 × 540 pt 是 16:9 画布；参考图按 96 DPI 换算时，100 px 对应 75 pt。对象有文档内唯一的 `id`，创建类型由 `kind` 指定。

## 准备环境

将 `SKILL_DIR` 替换为此 skill 文件夹的绝对路径。使用 Python 3.12 或更新版本，在任务目录执行：

```bash
export SKILL_DIR=/absolute/path/to/drawai-ppt
python -m pip install -r "$SKILL_DIR/scripts/requirements.txt"
python "$SKILL_DIR/scripts/ppt.py" --help
```

| 工作 | 所需环境 |
| --- | --- |
| 创建、导入或修改 PPTX | Python 依赖 |
| 导出 SVG | LibreOffice，命令为 `soffice` |
| 生成 PDF/PNG 预览、复杂渐变图片回退 | LibreOffice 与 Poppler，后者命令为 `pdftoppm` |
| LaTeX 公式转 Office Math | Pandoc，命令为 `pandoc` |

字体需要在渲染环境中可用；导出报告会记录字体替代。工具可从 PATH 查找，或通过 `--renderer`、`--rasterizer` 指定路径。

## 按输入选择工作流

读取 [制作流程](references/workflows.md) 中与任务对应的一节，按输入、制作、导出、检查的顺序完成：

| 用户输入 | 操作 |
| --- | --- |
| 文字、内容提纲、数据 | 创建文档模型，设置页面与对象，然后导出 |
| 已有 PPTX 或 PPTX 模板 | 检查并导入文件，定位对象，局部修改模型，再导出新文件 |
| 参考图片 | 查看图片，拆分文字、图形和连线，按坐标重建模型，渲染对照 |
| 已有 SVG | 导入并检查转换报告；本工具生成的 SVG 可恢复完整制作源，外部 SVG 转换为原生绘图对象 |

CLI 用于文件导入、导出、检查和渲染。Python API 用于构造对象、定位文字、复制页面或批量修改。可先运行这个完整示例，再修改其内容与布局：

```bash
python "$SKILL_DIR/scripts/example.py" output/example
python "$SKILL_DIR/scripts/ppt.py" render output/example/deck.pptx --output-dir output/example/preview
```

具体字段和结构见 [文档 API](references/document-api.md)。查询特定属性时使用：

```bash
python "$SKILL_DIR/scripts/ppt.py" capabilities --property chart.type --property picture.crop
```

[属性矩阵](references/export-capabilities.md)列出完整取值；[实现矩阵](references/implementation-capabilities.md)说明可创建、可修改或需保留原始 XML 的条件。精确原生 XML 操作及代码扩展按需读取 [代码指南](references/code-map.md)。

## 验证与交付

```bash
python "$SKILL_DIR/scripts/ppt.py" validate output/deck.pptx
python "$SKILL_DIR/scripts/ppt.py" render output/deck.pptx --output-dir output/preview
```

检查当前任务每页的文字、断行、裁剪、遮挡、连线、渐变与数据。模板编辑对照原件；图片重建对照参考图。发现问题后修改模型，在新版本目录重新导出。SVG 是静态投影，部分效果可能使用报告中列出的图片回退；复杂功能按目标 PowerPoint 的实际显示、编辑或播放核对。

交付 PPTX、SVG、文档 JSON、预览和必要的转换报告。说明图标近似、字体替代或图片回退等实际差异。修改工具包实现时运行 [代码指南](references/code-map.md#验证) 中的回归检查，普通制作的验收以当前产物为准。
