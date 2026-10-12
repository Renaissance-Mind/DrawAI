# 构建与编辑流程

本文使用已经安装统一 DrawAI 的 Python，核心 API 为 `pptx_skill`。`SKILL_DIR` 指向技能文件夹，旧脚本继续转交已安装核心。在任务目录工作，源文件保留原件，每次输出使用独立版本目录，例如 `output/v1`、`output/v2`。

CLI 的输入输出路径相对于当前工作目录；文档 JSON 中的素材路径相对于该 JSON 文件；SVG 内的图片路径相对于 SVG 文件。Python API 传入内存模型时，用 `asset_root` 指定素材目录。

## 从内容创建

1. 读取已经确定的页面图像、文字、数据与画布，沿用保存的页序和参考要求。
2. 查看视觉稿。需要重新设计时先进入 `drawai-design` 完成新的页面图像，再继续构建。
3. 拆分视觉稿中的文字、图形、连线和素材。复杂图像与数据图表按 [视觉与素材](visual-assets.md) 单独制作，保留可复用的文件。
4. 构建 `Document`。小型内容可直接保存文档 JSON；多页或数据驱动的制作使用 Python 脚本，把内容、布局和素材引用组织起来。
5. 导出、渲染并对照视觉稿。调整后在新版本目录导出，整理制作源。

完整示例会生成 `document.json`、`deck.pptx` 和报告：

```bash
python "$SKILL_DIR/scripts/example.py" output/create-v1 --svg
python "$SKILL_DIR/scripts/ppt.py" inspect output/create-v1/deck.pptx --output output/create-v1/inventory.json
python "$SKILL_DIR/scripts/ppt.py" render output/create-v1/deck.pptx --output-dir output/create-v1/preview
```

也可以将 [API 示例](document-api.md) 保存为 `deck.document.json`，只导出 PPTX，或同时导出两种格式：

```bash
python "$SKILL_DIR/scripts/ppt.py" export deck.document.json --pptx output/v1/deck.pptx
python "$SKILL_DIR/scripts/ppt.py" export deck.document.json --pptx output/v2/deck.pptx --svg-dir output/v2/svg --report output/v2/report.json
```

检查每页文字、图形、数据及视觉层级。最终交付文档源、脚本、素材和成品；含独立绘图素材的完整示例见 [成果包](visual-assets.md#可重新执行的成果包)。

## 修改 PPTX 与复用模板

模板是用户提供的普通 `.pptx` 文件，包括其中的主题、版式、页脚、装饰和内容对象。

```bash
python "$SKILL_DIR/scripts/ppt.py" inspect template.pptx --output work/inventory.json --preview-dir work/before
python "$SKILL_DIR/scripts/ppt.py" import template.pptx --output work/template.document.json --report work/import-report.json
```

先打开 `work/before` 的每页预览，对照清单中的标题、正文、日期与页脚文字，并检查配色和版式。确认文字完整显示后再把截图用于图像生成。预览和 SVG 默认在临时副本中忽略嵌入字体，使用本机匹配的字体；报告的 `fonts` 记录处理方式和替代结果，模板原件与最终 PPTX 保留原始字体资源。需要对照嵌入字体的渲染时，可在新目录使用 `--embedded-fonts preserve`。

从导入 JSON 中查找页面和对象 `id`，确认目标文字所在的 paragraph / run。只修改需要改变的文字或属性；导入产生的 `template`、`baseline`、`source_slide`、`source_shape_id` 和 `native_*` 数据用于保存原始结构。

### 使用模板制作新页面

先按 [模板解析与页面匹配](template-analysis.md) 查看全部页面、版式和母版，区分实际出现的页面用途与样式变体。将模板页的分类依据、布局特征，以及每个新页的用途和来源页记录到任务的 `template-analysis.json`。这份记录用于选择参考图和复用页面。

有图像生成或编辑工具时，按匹配记录为每个新页选择相同用途的模板截图，单独提交本页内容、用途和该类页面的版式要求，每页生成一张完整视觉稿。截图从真实模板渲染获得；若工具只接收图片，将对应预览 PNG 传给它。查看视觉稿，确认标题区、正文区和装饰符合所选页面类型，再制作对象与局部素材。

构建新页时，导入模板后复制匹配的来源页，保留其中适用的对象并替换内容；或在导入文档中添加绑定对应版式的新页。内容页从内容页或对应版式创建，结尾页从结尾页创建。标题、文字与图形按对象制作，复杂图片加入资源表。母版、主题与可编辑对象通过导入文档保留，页面专属装饰按匹配的类型复用。`duplicate_page` 与 `slide.layout_ref` 的使用见 [文档 API](document-api.md#修改文字和复制页面)。

### 修改已有页面

这个完整命令修改示例中 `heading` 对象的一个 run，并保存新 JSON 和 PPTX：

```bash
python "$SKILL_DIR/scripts/example.py" output/edit-v1 --source output/create-v1/deck.pptx --object-id heading --find "Original " --text "Updated " --svg
python "$SKILL_DIR/scripts/ppt.py" render output/edit-v1/deck.pptx --output-dir output/edit-v1/preview
```

将对象 ID 和原文字替换为实际检查到的值。示例在未找到或找到多个目标时报告错误；先检查目标，而不是把整个文本框重新写成单一样式。完整 Python 修改示例见 [API](document-api.md#修改文字和复制页面)。

页面排序使用 `pages` 列表；普通页面复制使用 `duplicate_page`，它会为副本的页面、分组及子对象生成新 ID。新页面可以用 `slide.layout_ref` 绑定检查到的版式。包含精确 XML 绑定的页面复制需要同步新的部件目标，按 [XML 操作](document-api.md#原生-xml-操作)处理。

最后对照原件，检查修改内容以及主题、字号、图片裁剪、Logo 和页脚等用户要求保留的设计。

## 根据图片重建

1. 查看图片，记录宽高与整体比例。选定 pt 画布；如果采用 96 DPI 换算，所有像素坐标与字号一起乘 0.75。
2. 列出文字、卡片、图标、连线、图表和局部图片。记录每个对象的边界、颜色、大小和层叠顺序。
3. 确认文字与数据。曲线图片通常无法恢复原始精确数据；有原数据时使用数据，无原数据时注明重建近似。
4. 用文本框、预设形状、自定义路径和分组构造文档。图标可以用原生形状、SVG 或独立图片表示；复杂局部素材可裁取原图中对应区域。需要重新设计的元素交回 `drawai-design`，取得确定的新素材后再排入页面。
5. 图表有原数据时，使用原生图表或单独绘图后插入；需要复杂坐标轴、误差带、多子图等外观时，优先单独制作并保留代码与数据。具体选择见 [素材流程](visual-assets.md#根据数据单独制作图表)。
6. 导出、渲染，将原图与实际输出按同一比例对照，修正文字越框、连线方向、图标大小和遮挡。

例如参考图中的框为 `(x=100, y=80, width=400, height=160)` px，采用上述换算后，`object.frame` 为 `{left:75, top:60, width:300, height:120}` pt。忠实重建直接以原图为视觉稿。全页位图插入适用于用户需要整页图片的任务；需要编辑文字与图形时，按对象重建，并将局部图片作为独立素材。

`scripts/build_v2_demo.py` 展示如何人工编写模型重建参考图；`assets/demo/` 是它的固定参考素材。制作自己的图时创建任务脚本和文档源，并交付实际使用的近似说明。

## 导入 SVG

```bash
python "$SKILL_DIR/scripts/ppt.py" import diagram.svg --output work/diagram.document.json --report work/svg-import.json
python "$SKILL_DIR/scripts/ppt.py" export work/diagram.document.json --pptx output/svg-v1/deck.pptx --svg-dir output/svg-v1/svg --report output/svg-v1/export.json
```

| SVG 类型 | 导入结果与检查 |
| --- | --- |
| 本工具导出的 SVG | 恢复完整文档源；报告 `projection_page_id` 指出该 SVG 展示哪页 |
| 外部 SVG | 转换路径、基本形状、文字、分组与图片；检查 `conversion` 中的原生结构、公式转换与回退记录 |
| 要放入已有 PPTX 的 SVG | 使用 `insert_svg` 加入目标页，返回带原生分组的新文档和转换报告；完整例子见 [API](document-api.md#svg-与局部插入) |

常用外部元素包括 rect、circle、ellipse、line、polygon、polyline、path、text/tspan、g、image 和可解析的 use 引用。复杂 CSS、滤镜、裁剪、任意变换与第三方扩展按实际转换结果判断，成功读取不等于所有效果均已重建。

导入报告的 `formula_export` 记录原生 Office Math 和图形回退。已有 SVG 公式只有字形路径时，导入结果仍是路径；LaTeX 转换需要下面的元数据和 Pandoc：

```xml
<g id="equation" data-pb-role="formula" data-pb-formula-latex="x^2+y^2" data-pb-formula-bbox="40 60 220 60">
  <text x="40" y="100" font-size="30">x²+y²</text>
</g>
```

若本工具 SVG 的外观经过手动修改而制作源未更新，哈希检查会提示源过期。修改原始文档源后重新导出；若要把当前外观当外部 SVG 重建，移除该制作源 metadata 后导入，并检查转换损失。

## 环境与常见调整

检查需要用到的工具：

```bash
python -c "import shutil; print({name: shutil.which(name) for name in ['soffice', 'pdftoppm', 'pandoc']})"
python "$SKILL_DIR/scripts/ppt.py" render output/deck.pptx --output-dir output/preview --renderer /path/to/soffice --rasterizer /path/to/pdftoppm
```

| 情况 | 调整 |
| --- | --- |
| 输入文件或素材不存在 | 核对当前工作目录与素材根目录 |
| 找不到 soffice / pdftoppm | 安装对应工具或传入显式路径；只制作 PPTX 时可先单独导出 |
| 输出文件已存在、预览目录非空 | 使用新的版本目录；组合导出中途失败时，先查看已生成的文件，再只重做缺少的输出 |
| 属性未实现或参数错误 | 查询该属性的条件与结构，修正输入；需要允许跳过时使用 `--profile best_effort` 并检查报告 |
| 字体替代 | 选择目标环境已安装的字体，重新渲染 |
| 清单有文字，预览缺少文字 | 核对字体处理报告及可见文字；本机字体仍无法正确显示时，使用目标 PowerPoint 渲染并检查完整预览后再制作视觉稿 |
| 连线方向向左或向上 | 用 `make_connector` 的起点、终点生成连线；它会计算非负宽高与方向翻转，见 [API](document-api.md#箭头) |
| 目标对象没有匹配或匹配多个 | 查看导入 JSON 与清单，明确对象 ID 和 run |

包校验检查 XML 和内部引用；对象清单检查可编辑结构；PNG/PDF 与浏览器 SVG 检查外观。交付时分别说明实际完成的检查。
