# 文档 API

`presentation.document.v1` 是创建和编辑共同使用的完整文档模型。一个文档有 `pages`，每页有 `objects`，对象的 `properties` 保存属性。分组使用 `children`，素材使用 `assets`。长度、字号和线宽为 pt；自定义路径的点使用该路径的局部视口坐标。

Python API 的准备方式如下。`SKILL_DIR` 从环境变量取得；命令示例中的变量已在 [入口](../SKILL.md) 设置。把下面的代码保存到任务目录的 `.py` 文件即可运行：

```python
from pathlib import Path
import os
import sys

skill_dir = Path(os.environ["SKILL_DIR"])
sys.path.insert(0, str(skill_dir / "scripts"))
from pptx_skill import (
    Document, load_document, import_pptx, import_svg,
    export_pptx, export_svg, duplicate_page, insert_svg, make_connector,
)
```

在 shell 中通过 `export SKILL_DIR=/absolute/path/to/drawai-image2ppt` 设置环境变量，或在制作脚本中直接为 `skill_dir` 指定绝对路径。

## 创建文档

保存下面的 JSON 为 `deck.document.json`，即可用 `ppt.py export` 导出。Python 中可将同一字典传入 `Document.model_validate`。

```json
{
  "schema": "presentation.document.v1",
  "id": "my-deck",
  "properties": {"document.page_size": {"width": 960, "height": 540}},
  "pages": [{
    "id": "overview",
    "objects": [{
      "id": "heading",
      "kind": "text_box",
      "properties": {
        "object.frame": {"left": 40, "top": 30, "width": 880, "height": 80},
        "text.run.font.latin": "Arial",
        "text.run.font.size": 32,
        "text.body.insets": {"left": 0, "top": 0, "right": 0, "bottom": 0},
        "text.body.paragraphs": [{"content": [
          {"kind": "run", "text": "Original ", "properties": {"text.run.font.bold": true}},
          {"kind": "run", "text": "title", "properties": {"text.run.font.italic": true}}
        ]}]
      }
    }]
  }]
}
```

继续使用上面的 imports，即可在 Python 中完成加载、保存、导出和报告：

```python
import json
out = Path("output/v1")
out.mkdir(parents=True, exist_ok=True)
doc = load_document(Path("deck.document.json"))
doc.save(out / "document.json")
pptx_report = export_pptx(doc, out / "deck.pptx")
svg_report = export_svg(doc, out / "svg")
(out / "report.json").write_text(json.dumps({"pptx": pptx_report, "svg": svg_report}, ensure_ascii=False, indent=2))
```

输出文件须为新路径，SVG/预览目录须为空。默认 `profile="strict"` 要求每个请求属性都有处理结果；`profile="best_effort"` 允许跳过未实现的字段并在 `issues` 中报告。包结构、对象数据和实际外观分别检查。

## 修改文字和复制页面

`id` 是文档内的唯一标识；`kind` 决定创建类型。使用顶层字段；若同时提供 `properties` 中的 `object.id/object.kind`，其值须与顶层字段相同。修改对象类型时创建一个替代对象。

导入 PPTX 时保存原始包和字段快照。`baseline` 是导入时的属性值，`source_*` 是原对象的定位信息，`native_*` 保存未展开的格式与 XML。编辑具体 run 的 `text` 可以保留其字体、粗细和其它原有设置：

导入的渐变色标可能使用 `position`，创建时的 `offset` 也可使用；调整时保留当前结构。没有展开的描边和箭头仍保存在 `native_xml`，重设描边时给出完整的 width、paint 和箭头参数。

```python
doc = import_pptx(Path("output/v1/deck.pptx"))
page = doc.pages[0]
targets = [obj for obj in page.objects if obj.id == "heading"]
if len(targets) != 1:
    raise ValueError("先检查导入 JSON，确认标题对象 ID")
run = targets[0].properties["text.body.paragraphs"][0]["content"][0]
run["text"] = "Updated "
doc.save(Path("work/edited.document.json"))
export_pptx(doc, Path("output/v2/edited.pptx"))
```

对象的 `object.z_order` 越大越靠上；页面和分组内都按该值排序，没有该字段的对象按列表顺序。恢复格式继承时设置 `clear_overrides`，例如 `target.clear_overrides = ["text.run.font.bold"]`。它在文字和样式修改后清除最终 XML 的直接格式，让主题/版式的默认格式生效。

```python
copied = duplicate_page(doc, page.id, new_id="overview-detail")
copied.save(Path("work/two-pages.document.json"))
export_pptx(copied, Path("output/v3/two-pages.pptx"))
```

`duplicate_page` 返回新文档，生成副本的页与对象 ID，并重映射对象引用。模板的图表、工作簿和备注页面在导出时独立复制；备注母版保持与演示文稿一致的共享引用。`pages` 列表控制页面顺序。精确 XML 绑定作用于具体部件，复制相关页面时需要一起调整其部件路径；该情况直接按模型和绑定编辑。

### 用模板版式创建新页

`inspect_pptx` 返回 `layouts` 清单，每项的 `layout_id` 是版式部件路径，`name` 是版式名称，`placeholders` 列出占位符的位置与类型。占位符没有可解析的几何时，相应 frame 字段为 `null`；选取有明确位置的对象作为布局依据。导入页面的 `slide.layout_ref` 保存其实际使用的版式路径。选定参考页后，可以用相同版式绑定新页：

```python
from pptx_skill import Page, inspect_pptx

inventory = inspect_pptx(Path("template.pptx"))
doc = import_pptx(Path("template.pptx"))
layout_ref = doc.pages[0].properties["slide.layout_ref"]
layout_info = next(item for item in inventory["layouts"] if item["layout_id"] == layout_ref)
print(layout_info["name"], layout_info["placeholders"])
new_page = Page.model_validate({
    "id": "new-overview",
    "properties": {"slide.layout_ref": layout_ref},
    "objects": [{"id": "new-heading", "kind": "text_box", "properties": {
        "object.frame": {"left": 40, "top": 30, "width": 880, "height": 80},
        "text.run.font.size": 32,
        "text.body.paragraphs": [{"content": [{"text": "New page"}]}]
    }}]
})
doc.pages.append(new_page)
export_pptx(doc, Path("output/template-v1/deck.pptx"))
```

版式绑定应用原模板的版式与母版，并可能带入其默认占位符；在新页中显式创建的文本框按自己的对象属性排版。仅存在于参考页上的 Logo、页脚或装饰属于页面对象；需要沿用这类对象时，复制该页再修改内容。已有页面变更版式涉及占位符重映射，应选择适合的模板页复制，或创建新的绑定页面。

## 常用参数

| 属性 | 结构与说明 |
| --- | --- |
| `object.frame` | `{left, top, width, height}` pt；形状宽高为正，水平/竖直连接线允许其中一个尺寸为 0 |
| 字体 | `text.run.font.latin/east_asian/complex_script/symbol` 为字体名或 `{typeface, charset, pitchFamily}`；`text.run.font.size` 用 pt |
| 段落 | `properties` 设置 alignment、line_spacing、space_before/after、缩进；`content` 保留 run/break/field/math 的顺序 |
| 间距 | `{mode: points或ratio, value}`；1.2 倍行距为 `{mode:"ratio", value:1.2}` |
| 颜色 | `"#336699"` 或 `{kind:"rgb", channels:"336699", alpha:0.5, transforms:[]}`；另支持主题、系统、预设、scRGB 和 HSL |
| 渐变 | `paint.kind="gradient"`，kind 为 linear/circle/rect/shape；stops 为 `[{offset, color}]`，offset 在 0–1；angle 用 degree |
| 自动适应 | `text.body.autofit: {mode: none/shrink_text/grow_shape}`；缩放参数另设 autofit_scale |
| 变换 | `object.transform: {a,b,c,d,e,f}`，平移 pt；可分解缩放、旋转、翻转；剪切需先将几何变换为路径 |
| 路径 | paths 每项有 `w/h` 和 commands；moveTo/lineTo 用 x/y，Bezier 用 points，arcTo 用 wR/hR/stAng/swAng；后者角度为原生角度单位 |
| 箭头 | `stroke.start_arrow/end_arrow` 的 kind、width、length 分别设置；宽/长使用 sm/med/lg |
| 虚线 | `stroke.dash_custom: [{dash,gap}]`，相对线宽 |
| 图片 | `picture.asset_ref` 指向 assets；`picture.aspect_fit` 为 contain/cover/stretch；`picture.crop` 为 `{left,top,right,bottom}` 四边比例，l/t/r/b 是可用缩写 |
| 素材 | assets 中每项为 `{path,content_type}` 或 `{data:base64,content_type}`；内存模型用 asset_root 解析相对 path |

图案、3D、主题与更多属性按 ID 查询 [实现条件](implementation-capabilities.md)，具体枚举见 [属性矩阵](export-capabilities.md)。Schema 描述文档结构；复杂 `properties` 的值按本文与矩阵填写。

### 箭头

```json
{"id":"arrow","kind":"connector","properties":{
  "object.frame":{"left":40,"top":120,"width":300,"height":0},
  "connector.geometry":"straight","stroke.width":2,"stroke.paint":"#336699",
  "stroke.end_arrow.kind":"triangle","stroke.end_arrow.width":"med","stroke.end_arrow.length":"med"
}}
```

属性 ID 使用完整键名，例如 `stroke.end_arrow.kind`。起点相应使用 `stroke.start_arrow.kind/width/length`。

Python 中优先按起点和终点创建连线，向左、向上或斜向连线都使用相同接口：

```python
arrow = make_connector("return-arrow", (340, 200), (40, 90), properties={
    "stroke.width": 2, "stroke.paint": "#336699",
    "stroke.end_arrow.kind": "triangle", "stroke.end_arrow.width": "med",
    "stroke.end_arrow.length": "med"
})
doc.pages[0].objects.append(arrow)
```

两个点的坐标使用 pt。函数计算包围框和方向翻转，终点箭头指向第二个点；`connector.geometry` 可设置 straight、elbow 或 curved。直接填写 JSON 时，`object.frame` 是非负宽高的包围框，方向使用 `object.flip_horizontal/vertical` 设置。文档加载会在导出前报告无效尺寸及对应对象 ID。

### 富文本内容

```json
{"properties":{"text.paragraph.alignment":"l","text.paragraph.space_after":{"mode":"points","value":8}},"content":[
  {"kind":"run","text":"Label","properties":{"text.run.font.bold":true}},
  {"kind":"break"},
  {"kind":"field","type":"slidenum","text":"1"},
  {"kind":"math","omml":"<m:oMath xmlns:m='http://schemas.openxmlformats.org/officeDocument/2006/math'><m:r><m:t>x+1</m:t></m:r></m:oMath>"}
]}
```

字段的 id 可省略，由工具生成；math 接收 OMML 原生数学树。仅有 LaTeX 时，按 [SVG 公式流程](workflows.md#导入-svg) 转换。Office Math 的目标软件检查与普通文字检查分别进行。

### 表格

```json
{"id":"table","kind":"table","properties":{
  "object.frame":{"left":40,"top":150,"width":400,"height":120},
  "table.grid_columns":[200,200],"table.rows.height":[40,40,40],
  "table.cells.content":[["Summary",""],["A","10"],["B","20"]],
  "table.cells.merge":[{"row":0,"column":0,"row_span":1,"column_span":2}],
  "table.cells.fill":"#EAF2FF","table.first_row":false
}}
```

行、列索引从 0 开始。merge 给出起始单元格及跨度。cells.content 的单元格也可使用包含 `text.body.paragraphs` 的富文本正文。

`table.first_row=true` 会启用表格样式的首行规则，包括文字颜色。自行设置浅色填充时可显式设置单元格文字颜色，或使用本文的普通行样式。

### 图表

```json
{"id":"chart","kind":"chart","properties":{
  "object.frame":{"left":480,"top":150,"width":440,"height":300},
  "chart.type":"lineChart","chart.categories":["A","B"],
  "chart.series":[{"name":"Values","values":[10,20]}],
  "chart.legend":{"visible":false},
  "chart.axes.scale":{"index":1,"minimum":0,"maximum":25,"major_unit":5},
  "chart.data_labels":[{"show_value":true,"show_category":false,"show_series":false}],
  "chart.markers":[{"series":0,"symbol":"circle","size":6}]
}}
```

直接创建支持 barChart、lineChart、areaChart、pieChart、doughnutChart、scatterChart、bubbleChart、radarChart。散点系列用 `points:[[x,y],...]`，气泡用 `points:[[x,y,size],...]`。柱/条由 plots 的 direction col/bar 区分。现代图表与已有组合图按原生模板和 XML 保留。

series、plot 和 point 索引从 0 开始。轴索引按原生分类轴、数值轴、日期轴的顺序；普通柱/线图的 0 是分类轴、1 是数值轴。饼/环图没有这类轴。轴设置也可放在 `chart.axes:[{index,scale:{minimum,maximum},number_format,major_unit,...}]`。plots 数量须与原生图表一致；组合图编辑需已有对应的多个 plot。

## 插入图片与独立图表

生成的图标、插画以及 Python/HTML 导出的图表都可以作为 `picture`。先保存素材文件，再注册资源并设置页面边界。下面代码接在本文的公共 imports 和已有 `doc` 后，两个路径相对于 `asset_root`：

```python
from pptx_skill import Object

doc.assets["illustration"] = {
    "path": "assets/images/illustration.png", "content_type": "image/png"
}
doc.pages[0].objects.append(Object.model_validate({
    "id": "illustration", "kind": "picture", "properties": {
        "object.frame": {"left": 40, "top": 140, "width": 200, "height": 200},
        "picture.asset_ref": "illustration", "picture.aspect_fit": "contain"
    }
}))

doc.assets["trend-preview"] = {
    "path": "assets/rendered/trend.png", "content_type": "image/png"
}
doc.assets["trend-vector"] = {
    "path": "assets/rendered/trend.svg", "content_type": "image/svg+xml"
}
doc.pages[0].objects.append(Object.model_validate({
    "id": "trend", "kind": "picture", "properties": {
        "object.frame": {"left": 280, "top": 140, "width": 620, "height": 320},
        "picture.asset_ref": "trend-preview", "picture.svg_asset": "trend-vector",
        "picture.aspect_fit": "contain"
    }
}))
export_pptx(doc, Path("output/assets-v1/deck.pptx"), asset_root=Path("."))
```

`picture.asset_ref` 提供 PNG/JPEG 等位图；`picture.svg_asset` 是可选矢量附件，需要同时保留位图预览。这种图表在 PPT 中作为图片编辑，系列数据在附带的绘图代码中修改后重新生成。若需要拆分 SVG 中的文字与路径，改用下面的 `insert_svg`。完整的数据、绘图与导出示例见 [成果包](visual-assets.md#可重新执行的成果包)。

## SVG 与局部插入

```python
drawing, conversion = import_svg(Path("diagram.svg"))
# 报告指出恢复源或外部转换，以及公式与图形回退。
doc, insertion = insert_svg(doc, doc.pages[0].id, Path("diagram.svg"),
    {"left":40,"top":200,"width":400,"height":200}, fit="contain")
export_pptx(doc, Path("output/inserted/deck.pptx"))
```

`insert_svg` 返回带原生分组的新文档和转换报告，fit 为 contain 或 stretch。普通 SVG 里的位图成为独立图片对象；图表等专用部件按完整文档编辑。外部 SVG 可用 `import_svg(source,padding=3)` 增加视口留白，padding 为 viewBox 局部单位。

逐页 SVG 嵌入完整源，导入恢复所有页面和引用；`projection_page_id` 标出该 SVG 对应的显示页。外观哈希用于识别制作源是否过期。矩形/shape 渐变的局部图片回退、字体替代等记录在报告中。

大型模板和图片会增加 SVG 中制作源的体积。使用 `import_svg` 恢复文档；解压后的源默认限额为 256 MiB，Python 的 `max_source_bytes` 或 CLI 的 `--source-limit-mib` 可以调整。直接检查 SVG XML 时，使用 `etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True)` 读取大型内嵌数据。

## 原生 XML 操作

未有直接属性接口的设置可以保留模板中的原始 XML，或使用明确的 `native_bindings`。例如设置默认语言：

```json
{"owner_id":"my-deck","property_id":"document.default_language","part":"ppt/presentation.xml",
 "xpath":"/p:presentation/p:defaultTextStyle/a:defPPr/a:defRPr","action":"set_attribute",
 "name":"lang","value":"zh-CN","expected_matches":1}
```

放在 Document 的 native_bindings 数组。action 可为 set_attribute/remove_attribute/set_text/append_xml/replace_xml/remove；新增 XML 放到 value，额外命名空间放到 namespaces。目标匹配数必须与 expected_matches 相同。native_parts 用部件相对路径对应 `{content_type,data:base64}`，同时提供完整资源关系。

XML 操作检查目标和包关系；语义通过实际属性与文件验证。模板中的 SmartArt、专用图表、媒体时间树、批注和其它扩展保留原始结构。加密、权限、签名及设备激活通过相应宿主流程处理。当前导出容器为 `.pptx`。
