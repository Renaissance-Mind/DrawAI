# 创建与编辑流程

以下命令从仓库根目录执行。使用其他工作目录时，替换为脚本的绝对路径；脚本自身定位源代码。所有计划中的素材路径相对于计划文件，SVG 内的图片路径相对于 SVG 文件。

## 创建文稿

创建契约为 `drawai.pptx_create_plan.v1`。默认画布是 1280 × 720 px，默认初始化一页空白页面。`slide_count` 控制初始空白页数，后续追加或复制页面会增加实际页数；交付时核对最终页数与用户要求。

下面的计划创建一个原生文本框和一个带文字的原生圆角矩形。内容用于说明 API，不是用户任务的默认布局。

```json
{
  "schema": "drawai.pptx_create_plan.v1",
  "title": "DrawAI PPT",
  "slide_size": {"width": 1280, "height": 720},
  "slide_count": 1,
  "operations": [
    {
      "op": "add_text", "slide": 1, "name": "title",
      "frame": {"left": 80, "top": 60, "width": 1120, "height": 80},
      "text": "可编辑的 PPT 对象",
      "style": {"font_family": "Arial", "font_size": 42, "bold": true, "color": "#17324D"}
    },
    {
      "op": "add_shape", "slide": 1, "name": "diagram-node", "geometry": "round_rect",
      "frame": {"left": 80, "top": 220, "width": 460, "height": 180},
      "fill": "#E6EEF8", "line_color": "#537BAA", "line_width": 2,
      "text": "Python 创建原生对象",
      "text_style": {"font_size": 28, "alignment": "center", "vertical_alignment": "middle"}
    }
  ]
}
```

```bash
uv run python skills/drawai-ppt/scripts/ppt.py create \
  --plan create-plan.json --output output/deck.pptx --report output/report.json
uv run python skills/drawai-ppt/scripts/ppt.py inspect output/deck.pptx
```

几何、字号、线宽、行距使用 96 DPI px；32 px 字号相当于 24 pt。文字样式支持字体、字号、颜色、粗体、斜体、下划线、水平和垂直对齐、行距、自动换行。`add_shape.geometry` 接受 `rect`、`round_rect`、`roundRect`、`ellipse`，也接受 `python-pptx` 的 `MSO_AUTO_SHAPE_TYPE` 成员名，例如 `RIGHT_ARROW`、`CHEVRON`、`HEXAGON`。复杂路径和渐变可以使用 SVG。

## 编辑和复用模板

先运行 `inspect`，读取页面、对象、版式、原生数据与文字样式。位置属于页面或分组坐标空间，检查结果中的 `parent_shape_id`、`coordinate_space`、`child_frame` 描述这一点。先看预览再决定修改对象。

已有文稿的编辑计划使用 `drawai.pptx_edit_plan.v1`。例如：

```json
{
  "schema": "drawai.pptx_edit_plan.v1",
  "operations": [
    {"op": "replace_text", "slide": 1, "shape_id": 2,
     "find": "原来的标题", "text": "新标题"}
  ]
}
```

示例中的 ID 和原文需要替换成实际检查结果。可加入检查结果中的 `source_sha256`，模板变化后旧计划会被拒绝。用 `duplicate_slide` 追加示例页副本，再通过新页面编号修改其中的对象；用 `add_slide` 和真实 `layout_id` 追加采用已有版式的页面。保留 Logo、页脚、主题、字号、固定装饰和图片裁剪等用户要求的设计。

完整的编辑操作、图表数据、图片适配与分组说明在仓库 [PPTX 编辑文档](../../../docs/zh-CN/pptx-editing.md)。当前准确的参数类型以脚本 `schema --mode edit` 的输出为准。

## SVG、公式与原生数据

`add_svg` 接收 SVG 路径和目标框，使用 `contain` 等比适配或 `stretch` 填满。转换结果以原生分组插入，局部图片作为独立图片资源导入。支持的 SVG 能力沿用 DrawAI 现有转换器。

带 LaTeX 元数据的 SVG 公式通过真实 Pandoc 转为 Office Math；报告记录转换和回退数量。原公式中的 Office Math 兼容性节点会被保留，但普通文字替换 API 不用于修改公式。原生数据图表用 `add_chart` / `set_chart_data`，表格用 `add_table` / `set_table_cells`；它们保留数据或单元格结构。

## 精细 Python 制作脚本

计划覆盖常见操作；更精细的富文本、段落、主题、图表样式可直接使用同一 Python 环境中的 `python-pptx`。在任务目录维护制作脚本，重复导出新版本并验证。

```python
from pptx import Presentation
from drawai.pptx_editing import validate_pptx_package

prs = Presentation("template.pptx")
# 从实际对象清单定位目标，再按需要设置 text_frame、paragraph、run 或图表属性。
prs.save("edited.pptx")
validate_pptx_package("edited.pptx")
```

保存到新文件。直接脚本同样需要源文件检查、真实对象定位、生成后渲染和模板对照。不能仅凭属性赋值或导出成功判断视觉效果。

## 验证环境

```bash
uv run python skills/drawai-ppt/scripts/ppt.py validate output/deck.pptx
uv run python skills/drawai-ppt/scripts/ppt.py render output/deck.pptx --output-dir work/preview
```

渲染依赖 LibreOffice `soffice` 和 Poppler `pdftoppm`。它们可通过 PATH 或命令参数传入。预览目录必须为空；输出 PDF 和每页 PNG。使用模板时渲染原文件和最终文件并对照，保持可编辑性的对象检查与外观检查都要完成。复杂 PowerPoint 特性需要在实际目标软件中核对；声明实际完成的检查。
