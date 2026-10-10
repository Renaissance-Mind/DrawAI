---
name: drawai-ppt
description: "Create and edit editable PowerPoint presentations with a self-contained Python toolkit; design from content, PPTX templates or reference images, combine native objects with generated visuals and data-driven assets, and deliver reproducible PPTX and SVG projects."
---

# DrawAI PPT

这个 skill 用于把内容提纲、数据、PPTX 模板或参考图片制作成可继续编辑的 PowerPoint，也用于修改已有演示文稿。它包含完整的 Python 工具包，可以将整个文件夹复制到其他环境使用。

Agent 负责理解内容、确定页面设计和制作素材；工具包负责读取已有 PPTX、组织页面对象、导出 PPTX 与逐页 SVG，并生成检查所需的预览。文字可以保留字体、段落和行内格式，图形可以使用形状、路径、连线、渐变和分组；表格与常用图表可以作为原生对象。照片、插画、图标和单独绘制的图表也可以作为素材放入页面。

交付效果包括页面外观和后续修改能力：原生对象可以在 PowerPoint 中继续编辑；图片素材可以替换、缩放与裁剪；带绘图代码和数据的素材可以重新生成。制作脚本与文档源保留布局和内容，使整套 PPT 能够再次导出。

## 场景与整体流程

先判断用户给了哪些输入，以及希望保留哪些内容与设计：

| 场景 | 制作方式 |
| --- | --- |
| 只有提纲或内容 | 梳理页面内容与阅读顺序，设计视觉稿，准备素材，再构建页面 |
| 有 PPTX 模板，需要新页面或重新设计 | 先解析并渲染全部模板页，识别页面用途与样式变体；为每个新页匹配相同用途的模板页，再生成视觉稿与页面 |
| 修改现有 PPTX 的文字、数据或局部样式 | 先检查并导入文件，定位对应对象，修改其内容与属性，再对照原件 |
| 有参考图，需要还原为可编辑 PPT | 查看原图，拆分文字、图形、连线与局部素材，按布局重建并对照；需要重新设计时先形成新的视觉稿 |
| 有 SVG 图形 | 导入或插入为原生绘图对象；也可作为独立矢量素材与其他对象组合 |

完整制作通常经过以下环节，局部修改只执行涉及的环节：

1. **整理输入。** 阅读提纲和数据，查看参考图；对模板或现有 PPTX 生成全部页面预览与对象清单，逐页核对文字与样式。使用模板时先识别标题页、目录页、内容页、结尾页等实际用途及其样式变体，记录各类页面的标题布局、正文区域和装饰，再为新文稿逐页确定用途并匹配模板页。具体见 [模板解析与页面匹配](references/template-analysis.md)。
2. **确定视觉设计。** 有图像生成或编辑工具时，新页面与重设计任务先生成视觉稿。每页单独提交生成请求，传入当前页的用途、内容、匹配的模板截图与该类页面的版式要求，输出一张完整页面图。多页共享模板主题，各类页面沿用自己的布局；生成结果按页保存并对照相同用途的模板页检查。已有参考图的忠实重建可直接以原图为视觉稿。
3. **制作页面素材。** 将复杂插画、图标等单独生成或编辑。数据图表可以用 Python、HTML 或 SVG 单独制作，保留数据和原始代码，导出 PNG/SVG 后再排入页面。按后续编辑需要选择原生对象或图片素材，具体见 [视觉与素材](references/visual-assets.md)。
4. **构建或修改文档。** 将视觉稿拆成页面对象；文字、形状、连线等分别设置，素材通过资源引用加入。已有 PPTX 导入后可以保留模板结构并修改指定对象。
5. **导出并检查。** 生成 PPTX 和所需的逐页 SVG，渲染实际 PPTX，与视觉稿或原件对照，修正断行、裁剪、遮挡、连线和数据展示。
6. **交付制作源。** 保存成品、Python 制作脚本、素材、素材代码和相关数据，写明重新生成的命令。更新数据时先重建素材，再重新导出 PPT。

没有图像生成工具时，直接设计页面并使用现有图片、Python 绘图或 SVG 素材。视觉生成的具体调用遵循所用工具的接口；本工具包执行文档制作与导出。按当前输入读取 [制作流程](references/workflows.md)，需要复杂图片、独立图表或可重新执行的成果包时再读 [视觉与素材](references/visual-assets.md)。

## 独立文档结构

制作源采用 `presentation.document.v1`：一个文档包含页面，每页包含文字、形状、图片、表格等对象，资源表保存素材。可以用 Python 构建和修改，也可以保存为 JSON。现有 PPTX 导入后同样成为这个结构，并携带用于保留原始内容的包数据。

- **文档 JSON** 保存页面、对象、文字、样式和资源，是可重复制作的源文件。
- **PPTX** 保存原生对象与图片资源，供 PowerPoint 继续使用和编辑。
- **SVG** 显示某一页的静态外观，并嵌入完整文档源；排版由同一 PPTX 的 LibreOffice 导出完成。

位置、尺寸、字号和线宽统一使用 **pt**。例如 960 × 540 pt 是 16:9 画布；参考图按 96 DPI 换算时，100 px 对应 75 pt。对象有文档内唯一的 `id`，创建类型由 `kind` 指定。字段、对象类型与图片插入示例见 [文档 API](references/document-api.md)。

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

字体需要在渲染环境中可用；导出报告会记录字体替代。LibreOffice 的预览与 SVG 默认使用本机字体，并在临时渲染副本中忽略嵌入字体，以避免嵌入字体造成文字漏显；原件与导出的 PPTX 保留嵌入字体。需要按嵌入字体渲染时使用 `--embedded-fonts preserve`。工具可从 PATH 查找，或通过 `--renderer`、`--rasterizer` 指定路径。

## 开始制作

CLI 用于文件导入、导出、检查和渲染。Python API 用于构造对象、定位文字、复制页面或批量修改。可先运行这个完整示例，再修改其内容与布局：

```bash
python "$SKILL_DIR/scripts/example.py" output/example
python "$SKILL_DIR/scripts/ppt.py" render output/example/deck.pptx --output-dir output/example/preview
```

需要独立图表和可重新执行的项目时，使用 [成果包示例](references/visual-assets.md#可重新执行的成果包)。查询特定属性时使用：

```bash
python "$SKILL_DIR/scripts/ppt.py" capabilities --property chart.type --property picture.crop
```

[属性矩阵](references/export-capabilities.md)列出完整取值；[实现矩阵](references/implementation-capabilities.md)说明可创建、可修改或需保留原始 XML 的条件。精确原生 XML 操作及代码扩展按需读取 [代码指南](references/code-map.md)。

## 验证与交付

```bash
python "$SKILL_DIR/scripts/ppt.py" validate output/deck.pptx
python "$SKILL_DIR/scripts/ppt.py" render output/deck.pptx --output-dir output/preview
```

检查当前任务每页的文字、断行、裁剪、遮挡、连线、渐变与数据；模板制作还要核对页面用途与对应样式，内容页沿用内容页的标题尺度和正文布局。使用模板复制页面、添加备注或编辑原生 XML 后，目标 PowerPoint 可用时实际打开 PPTX，确认页面完整且没有修复提示。出现修复提示时，在副本上比较修复前后的部件，修正制作脚本或导出器后重新导出。模板编辑对照原件；图片重建对照参考图。发现问题后修改模型，在新版本目录重新导出。SVG 是静态投影，部分效果可能使用报告中列出的图片回退；复杂功能按目标 PowerPoint 的实际显示、编辑或播放核对。

最终成果包按任务包含 PPTX、逐页 SVG、文档 JSON、Python 制作脚本、素材文件夹、素材原始代码与数据，以及预览和必要的转换报告。生成图片还保留提示词与使用的参考图，绘图素材保留可执行的生成步骤。说明图标近似、字体替代或图片回退等实际差异。修改工具包实现时运行 [代码指南](references/code-map.md#验证) 中的回归检查，普通制作的验收以当前产物为准。
