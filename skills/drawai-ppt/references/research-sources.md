# PPTX 规范研究来源

调研日期：2026-10-02。属性设计综合文件结构、Office 扩展和应用对象模型。下面的来源用于不同层次，不能用应用 API 的存在直接推断某个 XML 字段或跨平台支持情况。

## 文件结构与精确字段

- [微软 Open XML SDK](https://github.com/dotnet/Open-XML-SDK)：固定提交 `431ab05cf160248cc3885a4a766026d4f8243792` 的 Schema 元数据用于生成字段、子元素、基类继承、校验器和枚举清单。
- [PresentationML 文档结构](https://learn.microsoft.com/zh-cn/office/open-xml/presentation/structure-of-a-presentationml-document)：页面、母版、版式、主题、备注及其他部件的边界。
- [DrawingML 段落属性](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.drawing.textparagraphpropertiestype?view=openxml-3.0.1)：段落、列表、行距、段距和缩进。
- [DrawingML 字符属性](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.drawing.textcharacterpropertiestype?view=openxml-3.0.1)：字符级样式、字体、填充、字间距和字偶距。
- [DrawingML 路径渐变](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.drawing.pathgradientfill?view=openxml-3.0.1)：圆形、矩形和沿形状路径的渐变。

生成的 60 个文件的原始 URL 和 SHA256 位于 [schema-sources.json](pptx-inventory/schema-sources.json)。可用以下命令重新生成：

```bash
python <skill-dir>/scripts/research_pptx.py \
  --revision 431ab05cf160248cc3885a4a766026d4f8243792 \
  --output <inventory-dir> --cache <cache-dir>
```

SDK 元数据是实现参考，不是规范的替代品。其部分默认值、语义和互斥条件需要继续查对应 ISO/ECMA 条款及实际 PowerPoint 文件。共享 DrawingML 类型必须检查具体 PPTX 上下文。固定版本保证清单可重复，后续更新要记录版本差异。

## Office 扩展

- [MS-PPTX：PowerPoint 扩展](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-pptx/efd8bb2d-d888-4e2e-af25-cad476730c9f)：标准 PresentationML 之外的元素、属性和兼容结构。
- [MS-ODRAWXML：绘图扩展](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-odrawxml/06cff208-c6e1-4db7-bb68-665135e5f0de)：绘图、图片、效果及新版本功能的扩展。
- [切换扩展](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-pptx/22ebe6b5-2ade-43d9-977a-98fa194725c2)：扩展和兼容分支需要单独处理。
- [Morph 元素](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-pptx/68d26d78-f7f5-47ab-835d-4e6c82ff39f0) 与 [CT_MorphTransition](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-pptx/41ca8fbf-efc8-49ac-8a32-7bd0856544bd)：SDK 快照未包含该元素，需直接依据 MS-PPTX 补充。
- [字幕轨道 CT_Track](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-pptx/d6e01ce6-91b3-4065-88d4-257fca7eb817) 与 [LiveFeed/Cameo](https://learn.microsoft.com/zh-cn/openspecs/office_standards/ms-odrawxml/758f6386-63d2-4271-bd91-dfc51670c16b)：媒体与实时摄像头扩展，播放、设备和授权需要宿主环境。

覆盖的 Schema 包括 Drawing 2010–2021、PowerPoint 2010–2023 的相关声明，以及 SVG、墨迹、3D 模型、模型动画、手绘线条、现代 chartEx、现代批注和导航等。命名空间年份和 SDK 版本标签不能直接代替桌面/Web/Mac 的运行验证。

## PowerPoint 中的可设置能力

- [完整 PowerPoint 对象模型入口](https://learn.microsoft.com/en-us/office/vba/api/overview/powerpoint/object-model)
- [Presentation](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.presentation)：文档、主题、母版、放映、打印、签名、权限及标签等。
- [Shape](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.shape)：形状、自由几何、图片、连接线、表格、嵌入对象和 3D 对象。
- [TextFrame2](https://learn.microsoft.com/en-us/office/vba/api/office.textframe2)、[Font2](https://learn.microsoft.com/en-us/office/vba/api/office.font2)、[ParagraphFormat2](https://learn.microsoft.com/en-us/office/vba/api/office.paragraphformat2)：文本框、文字片段和段落的不同层次。
- [FillFormat](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.fillformat)：颜色与各类填充。
- [Chart](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.chart)：图表数据、系列、坐标轴、样式、布局和 3D。
- [Table](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.table)：表格、单元格、行列和表格样式。
- [SmartArt](https://learn.microsoft.com/en-us/office/vba/api/office.smartart)：原生图示的语义和布局。
- [MediaFormat](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.mediaformat)：媒体对象。
- [AnimationBehavior](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.animationbehavior)、[Timing](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.timing)、[SlideShowTransition](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.slideshowtransition)：对象动画、时间和页面切换。

对象模型还包含应用、窗口、选区、剪贴板、服务器同步等状态。这些不能自动纳入文档属性。动画、媒体、外链、加密、签名和嵌入对象需要对应的宿主、编码或授权环境。

## SVG 的次级输出边界

- [W3C SVG 文字](https://www.w3.org/TR/SVG/text.html)：字符、定位、文本布局与不同层次的文字属性。
- [W3C SVG 填充和渐变](https://www.w3.org/TR/SVG/pservers.html)：线性、径向渐变、坐标与色标等。

## 规范交叉检查

- [DrawingML Point](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.drawing.point?view=openxml-3.0.1)、[Path](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.drawing.path?view=openxml-3.0.1)：路径局部坐标、公式、视口及原生默认值。
- [Paragraph](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.drawing.paragraph?view=openxml-3.0.1)：段内有序的 run、换行和字段内容。
- [SlideMaster](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.presentation.slidemaster?view=openxml-3.0.1)、[SlideLayout](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.presentation.slidelayout?view=openxml-3.0.1)：母版/版式各自的颜色映射、显示、时间及切换作用域。
- [PackageProperties.Revision](https://learn.microsoft.com/en-us/dotnet/api/system.io.packaging.packageproperties.revision?view=windowsdesktop-9.0)：原始修订值保留字符串，不强制转成整数。

SVG 标准表达能力、具体查看器支持和当前导出器实现分别验证。静态 SVG 不承担 PowerPoint 时间树、放映、原生图表编辑、工作簿来源、嵌入对象激活和授权策略的完整语义。

## 静态 SVG 排版后端

- [LibreOffice SVG 导出器](https://github.com/LibreOffice/core/blob/master/filter/source/svg/svgexport.cxx)：页面、母版、背景、文字及演示元数据的实际导出实现。
- [LibreOffice SVG 过滤器](https://github.com/LibreOffice/core/blob/master/filter/source/svg/svgfilter.cxx)：命令行页面选择与可见页面处理。

2026-10-02 结合真实文件检查静态输出：移除播放脚本后需要显示实际页面并显式引用页面背景和母版对象。矩形/shape 渐变在 SVG 过滤器中的差异通过局部 PDF 图片回退记录；这些是实际后端行为及处理策略，不表示 SVG 与所有 PowerPoint 特性原生等价。
