# 统一文档制作与模板编辑

使用 `presentation.document.v1` 创建完整文档，以 pt 为物理长度单位。属性 ID 与 [属性目录](property-catalog.json) 一致；实际调用方式和限制见 [当前实现矩阵](implementation-capabilities.md)。示例、素材、脚本与依赖均在 skill 内。

## 同一源数据导出两种格式

```json
{
  "schema": "presentation.document.v1",
  "id": "my-deck",
  "properties": {
    "document.page_size": {"width": 960, "height": 540},
    "document.metadata.title": "Editable presentation"
  },
  "assets": {},
  "pages": [{
    "id": "overview",
    "objects": [{
      "id": "title",
      "kind": "text_box",
      "properties": {
        "object.frame": {"left": 40, "top": 30, "width": 880, "height": 80},
        "text.run.font.latin": "Arial",
        "text.run.font.east_asian": "PingFang SC",
        "text.run.font.size": 32,
        "text.body.insets": {"left": 0, "top": 0, "right": 0, "bottom": 0},
        "text.body.paragraphs": [{
          "properties": {"text.paragraph.alignment": "l"},
          "content": [
            {"kind": "run", "text": "原生文字", "properties": {"text.run.font.bold": true}},
            {"kind": "run", "text": "与统一文档模型", "properties": {"text.run.fill": "#2F80C9"}}
          ]
        }]
      }
    }, {
      "id": "gradient",
      "kind": "shape",
      "properties": {
        "object.frame": {"left": 40, "top": 150, "width": 400, "height": 200},
        "shape.geometry.preset": "roundRect",
        "paint.kind": "gradient",
        "paint.gradient.kind": "linear",
        "paint.gradient.angle": 35,
        "paint.gradient.stops": [{"offset": 0, "color": "#244E9B"}, {"offset": 1, "color": "#49B8CF"}],
        "stroke.width": 1.5,
        "stroke.paint": "#17354D"
      }
    }]
  }]
}
```

```bash
python <skill-dir>/scripts/ppt.py schema --mode document
python <skill-dir>/scripts/ppt.py export deck.document.json \
  --pptx output/deck.pptx --svg-dir output/svg --report output/report.json
```

可在 Python 中加载 `pptx_skill.document` 的 `Document`、`Page`、`Object`、`export_pptx`，以及 `document.svg.export_svg`、`document.importer.import_pptx/import_svg`。构造字典或 Pydantic 对象均可。相对素材路径属于源 JSON 的目录；调用 Python API 并传入内存对象时，使用 `asset_root` 指定素材根目录。

`strict_native` 默认拒绝未处理的属性；`compatible` 允许已报告的遗漏并记录对象 ID、属性和原因。需要交付可编辑对象时使用默认模式，并检查原生对象和数据。渲染校验独立进行，不能用 `strict_native` 的成功代替视觉验证。

## 值的结构与单位

| 设置 | 数据结构 |
| --- | --- |
| 富文本 | `text.body.paragraphs` 中每段有 `properties` 和有序 `content`；run / break / field / math 分别保存 |
| 字体 | Latin / East Asian / Complex Script / Symbol 可分别设置；字符串简写或 `{typeface, charset, pitchFamily}` |
| 段落 | 对齐使用原生 `l/ctr/r/just/justLow/dist/thaiDist`；行距、段前后为 `{mode: points或ratio, value}` |
| 颜色 | RGB 字符串；或 `{kind: rgb/scrgb/hsl/scheme/system/preset, channels, alpha, transforms}`，变换有序 |
| 渐变 | 色标 `{offset, color}`，也接受早期 `position` 别名；linear / circle / rect / shape 均写原生 DrawingML |
| 自动适应 | `{mode: none/shrink_text/grow_shape}`；也接受 `none/shrink/resize` 简写；缩放另设 `text.body.autofit_scale` |
| 矩阵 | `{a,b,c,d,e,f}` 或六项列表；平移 pt；保留可分解的缩放、旋转和翻转；剪切报错 |
| 路径 | 每条 path 有 `w/h` 局部视口和 `commands`；moveTo/lineTo/quadBezierTo/cubicBezierTo/arcTo/close；也接受 DrawingML 名称 |
| 箭头 | 起止分别设置 kind / width / length，原生 `sm/med/lg`；静态 SVG 使用渲染出的实际外形 |
| 虚线 | `stroke.dash_custom: [{dash,gap}]`，相对线宽；也接受二项列表简写 |
| 图片 | `picture.asset_ref` 指向 `assets`；contain / cover / stretch；crop 是四边比例；SVG 资源需要位图后备图与 `picture.svg_asset` |
| 原生图表 | `chart.type` 使用矩阵中的 `barChart/lineChart/...`；category 图表为 `chart.categories` 与 `chart.series`；scatter/bubble 为每个 series 的 `points` |
| 图表细节 | plots、轴尺度/交叉/格式/网格线、数据标签、标记、趋势线、误差线、区域样式和布局分别设置；原生工作簿保留 |
| 表格 | grid_columns 与 rows.height 用 pt；cells.content 为二维字符串或富文本正文；cells.merge 使用 row/column/row_span/column_span |
| 3D | 原生 camera、light rig、bevel、extrusion、material 等；SVG 为渲染器提供的静态外观 |

填充只设置当前 `paint.kind` 所需的参数，避免同时携带 solid / gradient / pattern 的互斥配置。缺省表示保留缺省或模板值，显式 false 和 0 有效。资源可采用 `{path, content_type}` 或 `{data: base64, content_type}`。导出的 SVG metadata 会嵌入素材和制作源，复制 SVG 后仍可恢复模型。

## 复用已有模板

```bash
python <skill-dir>/scripts/ppt.py import template.pptx --output work/template.document.json
python <skill-dir>/scripts/ppt.py export work/edited.document.json \
  --pptx output/edited.pptx --svg-dir output/svg --report output/report.json
```

导入记录模板哈希、完整包内容、实际页面和对象 ID、可编辑的文字/几何/图片/表格/常用图表以及原生 XML。修改 `properties` 或段落/run 中的文字后导出新文件。`baseline`、`source_slide`、`source_shape_id`、`native_xml`、`native_ppr/native_rpr` 属于往返保留数据，保留这些字段，不用猜测或删除。

`clear_overrides: ["text.run.font.bold"]` 可明确移除格式覆盖，恢复继承。删除 `properties` 中的键不会自动擦除模板 XML。复制或重新排序页面使用 pages 列表；复制页需生成新的页面和对象语义 ID。新页面的 `slide.layout_ref` 绑定模板中实际存在的版式；已有页切换版式还涉及占位符重映射，不能仅改一个字符串。

导出的 SVG 包含可恢复的同一制作源：`ppt.py import slide.svg --output recovered.document.json`。外观哈希不匹配时拒绝使用过期模型。普通外部 SVG 则转换为可编辑路径、文字和分组；复杂 SVG 的支持边界来自实际转换报告。已描边的公式字形是原生路径，不能宣称为可编辑公式字符；OMML 保存在原生 Office Math 树中。

## 显式原生 XML

未有属性 API 的复杂功能使用真实模板保留，或提供明确的 `native_bindings`。示例修改默认语言：

```json
{
  "owner_id": "my-deck",
  "property_id": "document.default_language",
  "part": "ppt/presentation.xml",
  "xpath": "/p:presentation/p:defaultTextStyle/a:defPPr/a:defRPr",
  "action": "set_attribute",
  "name": "lang",
  "value": "zh-CN",
  "expected_matches": 1
}
```

将此记录放到 Document 的 `native_bindings` 数组。action 支持 set_attribute / remove_attribute / set_text / append_xml / replace_xml / remove；XML 内容放到 value，额外命名空间放到 namespaces。精确目标匹配失败会报错。新增部件放入 `native_parts`，每项为包内相对路径对应 `{content_type, data: base64}`；关系及资源闭包也必须完整。`native_xml` 支持已有原生对象树。XML 绑定报告标为 explicit_native_xml，不能据此宣布该语义属性的高级 API 或外观已验证。

主题格式、时间树和效果 DAG 可以保存原生 XML 树。SmartArt、现代图表、复杂媒体时间树、批注和未知 Office 扩展优先从模板保留，并对需要改变的部件使用精确绑定。加密、IRM、签名、Cameo 设备绑定和对象激活需要宿主流程。此导出 profile 使用 `.pptx`，拒绝宏工程混入，修改签名模板也会拒绝；这些不能通过改几个 XML 节点获得同等效果。

## 验证与示例

```bash
python <skill-dir>/scripts/check.py
python <skill-dir>/scripts/check_document.py
python <skill-dir>/scripts/build_v2_demo.py --output-dir output/demo
python <skill-dir>/scripts/ppt.py render output/demo/demo.pptx --output-dir work/preview
```

示例使用目录内已有的两张参考图和矢量公式：重建图表/流程图、中文 Agent 工作流、富文本与渐变样例，另测试公式 SVG。PNG 是参考图，没有铺成整页背景。工作流装饰图标使用简化的原生形状；这是重建示例，不能当作逐像素复刻结果。

SVG 导出需要 LibreOffice；PNG/PDF 预览另需 Poppler。矩形和 shape 路径渐变存在 office SVG 过滤器的外观差异，未旋转的顶层对象可由实际 PPTX 的 PDF 区域局部生成图片回退，包含区域内文字并在报告中列出受影响对象，制作源与 PPTX 仍保留原生设置。该回退需要 Poppler；旋转/变换场景或缺少 Poppler 时保留并报告近似，不能宣称纯矢量等价。

使用 `--renderer` / `--rasterizer` 传入显式路径。字体配置在临时目录解析实际字体，不修改系统配置；报告记录缺失与替代字体。对目标 PowerPoint 版本检查复杂属性的实际显示、编辑和播放；LibreOffice 验证结果分别记录。极窄公式 SVG 可通过 Python `import_svg(source, padding=3)` 增加视口留白；保留原件，避免字形贴边被裁切。
