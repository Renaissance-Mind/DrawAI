# 视觉设计、独立素材与成果包

页面可以同时包含原生文字与图形、生成的图像元素、根据数据绘制的图表。先确定各部分的制作方式，再组合成文档。本文说明图像工具如何参与制作、素材如何插入，以及如何保存可重新执行的项目。

## 用视觉稿确定页面设计

如果目标环境提供图像生成或编辑工具，新页面与重设计任务先用它生成视觉稿。读取对应工具或 Imagegen skill 的说明，按其接口传入内容与参考图片。提示词说明本页内容、画布比例、阅读顺序、整体风格、文字位置和需要保留的设计；连续多页使用一致的视觉要求。

有 PPTX 模板时，先生成模板截图：

```bash
python "$SKILL_DIR/scripts/ppt.py" inspect template.pptx --output work/template-inventory.json --preview-dir work/template-preview
```

查看截图和清单，选择合适页面，将预览 PNG 作为生成参考。新内容与模板参考一起输入，获得视觉稿后检查标题、层级、配色、边距和素材风格。原模板、参考图和最终视觉稿分别保存在任务的输入与参考目录中。

视觉稿指导页面重建：识别文字、卡片、箭头、图表和插画，分别确定边界与层叠关系。把文字和需要继续编辑的结构做成原生对象，将复杂插画做成独立素材。生成的整页图中出现文字或数据错误时，按用户提供的内容与真实数据制作最终对象。已有页面的局部文字或数据修改可以直接操作导入对象。

## 生成或编辑图像元素

图标、插画、装饰、照片与纹理可以单独生成。给工具提供目标元素、页面风格、比例与参考图；透明图标或抠图按工具接口请求透明背景。修改已有素材时传入对应文件及明确的编辑要求。保存实际生成文件，再引用到页面中。

按照用途选择素材形式：

| 用途 | 形式与后续修改方式 |
| --- | --- |
| 简单图标、框和箭头，需要调整节点或文字 | 原生形状、路径与连线；在 PowerPoint 中直接编辑 |
| 插画、照片、复杂图标 | PNG/JPEG 图片对象；保留原图，可以替换、缩放或裁剪 |
| 矢量图标或独立 SVG 图表，需作为一个完整素材使用 | PNG 预览配合 `picture.svg_asset`；支持 SVG 的 PowerPoint 可使用矢量图像 |
| SVG 图形，需要拆分为绘图对象 | 使用 `insert_svg`；检查转换报告和渲染结果 |

生成素材放在 `assets/images/`，保存提示词、所用参考图路径和生成工具信息，例如 `assets/src/icon.prompt.md`。后续重导出直接使用已经保存的图片；只有需要修改素材时才再次调用生成工具。

## 根据数据单独制作图表

折线图、复杂坐标轴、误差带、热力图、多子图等可以由独立的 Python、HTML 或 SVG 源生成，再放入文档。原生 `chart` 对象适合需要在 PowerPoint 内修改系列数据的常用图表；独立绘图适合需要精确控制图表外观的任务，两者都可以参与同一页面。

1. 保存实际使用的数据，如 `data/metrics.csv`，标明单位、系列与必要的数据处理。
2. 用 Matplotlib/Plotly、HTML 页面或 SVG 源制作图表，把轴、刻度、图例、配色、标注和输出尺寸写进源码。HTML 图表等到字体、图像和图表实际渲染后再截图。
3. 导出 PNG 作为稳定预览，需要矢量画质时同时导出 SVG。位图宽高至少覆盖页面中实际显示尺寸；例如 480 pt 宽、按 2 倍 96 DPI 制作时，宽度约为 1280 px。
4. 通过 `assets` 加入 PNG，必要时再附加 SVG；或用 `insert_svg` 转成原生绘图对象。图表作为图片时，系列数据通过所附代码和数据重新生成。
5. 对照数据检查坐标、数值、趋势、单位与图例，再查看 PPTX 的实际显示。

图像生成工具适合图表周围的视觉素材；准确的数据图表由数据与绘图代码生成。只有曲线截图时，数字化得到的近似数据应记录来源与精度，避免把近似值当作原始数据。

图片与矢量素材的字段示例见 [文档 API](document-api.md#插入图片与独立图表)。

## 可重新执行的成果包

根据实际使用的素材整理项目，例如：

```text
presentation-project/
├── build.py                  构建文档、重建绘图素材、导出
├── requirements.txt          制作脚本与绘图代码的依赖
├── inputs/                   模板、内容和原始参考图（如有）
├── references/               页面视觉稿（如有）
├── data/                     图表数据（如有）
├── assets/
│   ├── images/               已保存的生成图片与其他图片素材
│   ├── src/                  图表代码、SVG/HTML 源、图像提示词
│   └── rendered/             从源与数据生成的 PNG/SVG
└── output/v1/
    ├── document.json
    ├── deck.pptx
    ├── svg/
    ├── preview/
    └── report.json
```

`build.py` 使用项目内的相对路径读取数据与素材，通过 `SKILL_DIR` 定位独立工具包。输出 JSON 中的资源路径相对于该 JSON 文件；API 导出内存文档时显式传入 `asset_root`。将工具包与项目一起交付，或注明完整工具包的位置及依赖安装命令。

提供实际可执行的重建步骤：修改数据，运行绘图源码，再构建文档、导出和渲染。可以由 `build.py` 一次完成；生成图片只读取已保存的文件。每次选择新的输出版本目录，保留原件与之前的成品。

可复制的例子在 `assets/rebuildable-deck/`。它使用注明为示例的数据，通过 Matplotlib 输出折线图 PNG/SVG，将图表作为图片素材与原生标题、说明组合，并保存数据来源摘要与图表代码。每个输出版本还保存所用数据、源码和生成素材的快照，之前版本的文档源可以独立再次导出。先安装核心依赖，然后在任务目录运行：

```bash
cp -R "$SKILL_DIR/assets/rebuildable-deck" ./presentation-project
python -m pip install -r presentation-project/requirements.txt
python presentation-project/build.py --output output/v1 --svg --preview
```

输出路径相对于复制后的项目根目录，因此结果在 `presentation-project/output/v1/`。更新 `presentation-project/data/metrics.csv` 后再次执行：

```bash
python presentation-project/build.py --output output/v2 --svg --preview
```

需要增加图标或插画时，将图片放到项目内的素材文件夹，并按 [API](document-api.md#插入图片与独立图表) 添加图片对象。示例使用的 Matplotlib 是可选绘图依赖，核心工具包可以独立运行。
