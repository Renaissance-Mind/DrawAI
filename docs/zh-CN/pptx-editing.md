# 编辑 PPTX 模板

DrawAI 使用 Python 读取现有 PPTX、执行对象编辑计划，并保存为新文件。新图形通过现有 SVG → DrawingML 转换器插入模板页面，保留原生形状、文字、图片和 Office Math。模板编辑不需要 OpenAI 的 Artifact Tool，也不需要运行图像重建模型。

从空白文稿创建 PPTX 可使用 `drawai ppt create --plan create-plan.json --output deck.pptx`，计划格式为 `drawai.pptx_create_plan.v1`。创建和编辑共用原生对象操作，新增文本框与预设形状分别使用 `add_text` 和 `add_shape`。完整的独立 Agent 使用流程和代码扩展方式见 [drawai-image2ppt skill](../../skills/drawai-image2ppt/SKILL.md)。

## 读取模板

```bash
uv run drawai ppt inspect template.pptx --output template.json
uv run drawai ppt schema > edit-plan.schema.json
```

`template.json` 包含源文件 SHA256、画布尺寸、所有母版下的版式、每页的对象 ID、文字、表格、图表和图片信息。页面编号从 **1** 开始，`shape_id` 是页面内的对象 ID。表格行列编号从 **0** 开始。几何和字号使用 **96 DPI 的像素**：32 px 相当于 24 pt。

分组内部的对象具有 `parent_shape_id`，其 `frame` 属于分组坐标空间；分组的 `child_frame` 与页面中的 `frame` 描述坐标映射。修改前结合页面预览确认对象和位置，尤其是存在嵌套、缩放或旋转的分组。

## 执行编辑计划

计划使用 `drawai.pptx_edit_plan.v1` 格式。把 `shape_id` 替换为检查结果中的实际 ID；`source_sha256` 可填写检查结果中的哈希，以拒绝在模板发生变化后执行旧计划。

```json
{
  "schema": "drawai.pptx_edit_plan.v1",
  "operations": [
    {
      "op": "replace_text",
      "slide": 1,
      "shape_id": 2,
      "find": "原来的标题",
      "text": "研究方法"
    },
    {
      "op": "add_svg",
      "slide": 1,
      "path": "diagrams/method.svg",
      "frame": {"left": 80, "top": 180, "width": 600, "height": 320},
      "fit": "contain"
    }
  ]
}
```

```bash
uv run drawai ppt edit template.pptx \
  --plan edit-plan.json --output edited.pptx --report edit-report.json
```

CLI 中的素材路径相对于**计划 JSON 所在目录**解析；SVG 内的图片路径相对于 SVG 所在目录解析。Python API 的 `asset_root` 可显式指定素材根目录，默认是源 PPTX 所在目录。

编辑器要求新的输出文件名。找不到目标、模板哈希不符、未知操作、非法参数、缺失素材或无效图表数据都会报错。只有全部操作完成、包结构校验通过且重新打开成功后才发布输出。原始 PPTX 和 SVG 不会被修改。

对象清单会标出 Office Math 和其他保留的兼容性对象。这些对象不能通过普通文字 API 修改；可以保留原对象，或通过带 LaTeX 元数据的 SVG 插入新公式。公式转换需要 Pandoc，编辑报告记录实际转换与回退数量。清单和报告也要求新的 `.json` 文件名。

## 可用操作

| 操作 | 用途与字段 |
| --- | --- |
| `add_text` | 使用 `frame`、`text`、可选 `style` 和 `name` 创建原生文本框 |
| `add_shape` | 使用 `geometry`、`frame`、填充、边框和可选文字创建原生预设形状 |
| `replace_text` | 在指定文本对象中替换 `find` 为 `text`，支持跨文字 run 匹配，保留原有段落和文字样式；不跨段落或换行匹配 |
| `set_text` | 设置整个文本框的 `text`；新段落沿用对应原段落的属性和首个 run 的样式，可提供 `style` |
| `replace_image` | 替换指定图片的 `path`；`fit: preserve` 保留位置与裁剪，`cover` 根据新图片重新居中裁剪 |
| `set_table_cells` | 更新原生表格的 `cells`，每项包含 `row`、`column`、`text` 和可选 `style` |
| `set_chart_data` | 更新原生图表的 `data`，保留原图表类型和样式 |
| `set_geometry` | 设置对象 `frame` 和可选 `rotation`，旋转使用角度 |
| `set_style` | 设置 `fill`、`line_color`、`line_width`、`text_style`；颜色为六位 RGB，形状填充与边框还接受 `none` |
| `add_svg` | 将 `path` 转为原生对象分组，放入 `frame`；`contain` 等比适配，`stretch` 填满；可提供分组 `name` |
| `add_image` | 将图片放入 `frame`；支持 `contain` 和 `cover` |
| `add_table` | 根据矩形 `values` 数组创建原生表格，放入 `frame`；可提供文字 `style` |
| `add_chart` | 根据 `chart_type`、`data` 和 `frame` 创建原生图表 |
| `add_slide` | 使用检查结果中的 `layout_id` 追加页面，复用该版式及母版 |
| `duplicate_slide` | 复制指定 `slide` 并追加到末尾；复制图表、工作簿与备注，后续修改副本图表不会改变原页 |

`text_style` 和 `style` 接受 `font_family`、`font_size`、`bold`、`italic`、`underline`、RGB `color`、`alignment`、`vertical_alignment`、`line_spacing` 和 `word_wrap`。未指定的属性沿用原对象。`set_text` 用首个 run 的样式排新内容；需要保留混合样式时用 `replace_text`。

类别图表的数据示例：

```json
{
  "categories": ["类别 A", "类别 B"],
  "series": [{"name": "系列名称", "values": [10, 20]}]
}
```

散点图使用 `series[].points: [[x, y], ...]`；气泡图使用 `[[x, y, size], ...]`。创建图表支持 `column`、`bar`、`line`、`area`、`pie`、`doughnut`、`scatter` 和 `bubble`。导入后为图片的表格或图表需要按图片处理；原生数据编辑要求对应的原生对象。

## 检查实际文件

```bash
uv run drawai ppt validate edited.pptx
uv run drawai ppt render template.pptx --output-dir before-preview
uv run drawai ppt render edited.pptx --output-dir after-preview
```

也可在 `inspect` 或 `edit` 命令中指定 `--preview-dir`。渲染需要 LibreOffice 的 `soffice` 和 Poppler 的 `pdftoppm`，默认从 PATH 查找，也可通过 `--renderer` 和 `--rasterizer` 指定可执行文件。渲染使用独立的 LibreOffice 配置目录，输出 PDF 和逐页 PNG；预览目录必须为空，避免旧图片混入。

包结构校验检查 XML、必要文件和内部资源关系。渲染与原模板对照用于检查外观、裁剪、换行和排版；需要 PowerPoint 特有功能时，还应在目标 PowerPoint 环境检查。复杂特性仍受 python-pptx 和现有 SVG 转换器的支持范围限制。

## 给 Agent 使用

```bash
uv run drawai tool help ppt --json
uv run drawai tool ppt inspect template.pptx --output template.json
uv run drawai tool ppt edit template.pptx --plan edit-plan.json --output edited.pptx
```

`drawai tool ppt` 与 `drawai ppt` 使用同一编辑器。Agent 读取对象清单和预览，按 JSON Schema 生成编辑计划，再调用编辑和渲染命令。此入口也能通过已有的 `run_drawai_tool` 调用方式接入。

Python 调用：

```python
from drawai.pptx_editing import inspect_pptx, edit_pptx

inventory = inspect_pptx("template.pptx")
# plan 使用真实对象 ID 和 drawai.pptx_edit_plan.v1 契约。
report = edit_pptx("template.pptx", plan, "edited.pptx", asset_root="assets")
```
