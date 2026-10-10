# 视觉设计、独立素材与成果包

页面可以同时包含原生文字与图形、生成的图像元素、根据数据绘制的图表。先确定各部分的制作方式，再组合成文档。本文说明图像工具如何参与制作、素材如何插入，以及如何保存可重新执行的项目。

## 复用已确定的视觉与素材

读取 `drawai-design` 交付的页面图像、模板匹配记录和素材。将已确定的文字与简单图形重建为原生对象，复杂局部图像可以使用真实裁剪或已保存素材。记录各素材的来源与用途。

需要改变页面设计、生成新插画或修改素材外观时，交回设计阶段完成，再以新的图像和素材继续构建。构建阶段采用已确定的视觉，不重新决定整套设计。

图片通过资源表中的实际路径或数据引用加入文档，裁剪、位置与尺寸按视觉图像设置。后续导出复用已保存文件；相关路径与属性见 [文档 API](document-api.md)。

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
