# PPTX / SVG 属性矩阵

表中列出具体取值和格式表达方式。格式目标、实际代码和验证状态分别记录；详细调用条件见 [当前实现矩阵](implementation-capabilities.md)。统一文档已可导出 PPTX 和静态 SVG，仍须按属性的实际处理方式使用。

枚举保留完整选项：原生枚举使用其 XML 值；统一语义选项明确注明来源。大列表在同一单元格内展开，不以 enum 或省略号替代。

箭头 sm/med/lg 是相对线宽的类别，不是固定像素值。SVG 能画出对应宽度和长度，但需 marker 几何映射；精确视觉等价仍需 PowerPoint 对照标定。

## 文档、包与全局设置

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 文档标识<br>`document.id` | 稳定标识字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 标题<br>`document.metadata.title` | 字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 主题<br>`document.metadata.subject` | 字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 作者<br>`document.metadata.author` | 字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 关键词<br>`document.metadata.keywords` | 结构参数 `text[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 说明<br>`document.metadata.description` | 字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 创建时间<br>`document.metadata.created` | 结构参数 `datetime`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 修改时间<br>`document.metadata.modified` | 结构参数 `datetime`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 修订号<br>`document.metadata.revision` | 字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 自定义属性<br>`document.metadata.custom_properties` | 结构参数 `typed_map`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 页面尺寸<br>`document.page_size` | {width, height}；有限数值，尺寸需满足原生正值约束 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 页面方向<br>`document.orientation` | portrait / landscape | 通过页面尺寸和方向设置表示 portrait / landscape。 | 通过画布/viewBox 的宽高表示。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 默认语言<br>`document.default_language` | 语言标签，如 zh-CN / en-US | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 布局方向<br>`document.layout_direction` | ltr / rtl | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 嵌入字体资源与字形子集<br>`document.fonts.embedded` | 结构参数 `font_assets[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 字体替代与解析策略<br>`document.fonts.fallback` | 结构参数 `font_rules[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 媒体资源与关系<br>`document.assets` | 结构参数 `asset_map`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 自定义 XML 部件<br>`document.custom_xml` | 结构参数 `xml_parts[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 全局颜色映射<br>`document.color_map` | 结构参数 `theme_map`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 参考线<br>`document.guides` | 结构参数 `guide[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 网格间距<br>`document.grid_spacing` | {width, height}；有限数值，尺寸需满足原生正值约束 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 节与页面顺序<br>`document.sections` | 结构参数 `sections[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 目标 Office 版本与能力<br>`document.compatibility_profile` | 结构参数 `profile`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |

## 页面、显示与背景

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 稳定页面标识<br>`slide.id` | 稳定标识字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 页面名称<br>`slide.name` | 字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 页面顺序<br>`slide.order` | 整数；单位 —；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 隐藏页面<br>`slide.hidden` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 绑定版式<br>`slide.layout_ref` | 结构参数 `ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 绑定母版<br>`slide.master_ref` | 结构参数 `ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 页面主题覆盖<br>`slide.theme_override` | 结构参数 `theme`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 背景填充<br>`slide.background` | 结构参数 `paint`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 继承母版背景<br>`slide.background_follow_master` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 显示母版对象<br>`slide.show_master_shapes` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 日期、页码、页脚内容和显示<br>`slide.header_footer` | 结构参数 `header_footer`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 批注关系<br>`slide.comments_ref` | 结构参数 `ref[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 标签与自定义数据<br>`slide.tags` | 结构参数 `map`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| Office 创建标识<br>`slide.creation_id` | GUID | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 颜色映射覆盖<br>`slide.color_map_override` | 结构参数 `theme_map`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 绘图对象和层级<br>`slide.objects` | 结构参数 `object[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |

## 主题、母版、版式与占位符

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 主题色槽与系统色<br>`theme.colors` | 结构参数 `color_scheme`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 标题字体与各文字系统字体<br>`theme.fonts.major` | 结构参数 `font_collection`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 正文字体与各文字系统字体<br>`theme.fonts.minor` | 结构参数 `font_collection`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 填充、描边和效果样式集合<br>`theme.format_scheme` | 结构参数 `format_scheme`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 额外配色方案<br>`theme.extra_color_schemes` | 结构参数 `color_scheme[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 对象、线条和文字默认样式<br>`theme.defaults` | 结构参数 `style_defaults`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 母版标识<br>`master.id` | 稳定标识字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 母版背景<br>`master.background` | 结构参数 `paint`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 母版固定对象<br>`master.objects` | 结构参数 `object[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 标题、正文、其他文本分级样式<br>`master.text_styles` | 结构参数 `text_styles`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 母版版式列表<br>`master.layout_refs` | 结构参数 `ref[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 母版页眉页脚<br>`master.header_footer` | 结构参数 `header_footer`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 版式标识<br>`layout.id` | 稳定标识字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 版式类型<br>`layout.type` | title（Title） / tx（Text） / twoColTx（TwoColumnText） / tbl（Table） / txAndChart（TextAndChart） / chartAndTx（ChartAndText） / dgm（Diagram） / chart（Chart） / txAndClipArt（TextAndClipArt） / clipArtAndTx（ClipArtAndText） / titleOnly（TitleOnly） / blank（Blank） / txAndObj（TextAndObject） / objAndTx（ObjectAndText） / objOnly（ObjectOnly） / obj（Object） / txAndMedia（TextAndMedia） / mediaAndTx（MidiaAndText） / objOverTx（ObjectOverText） / txOverObj（TextOverObject） / txAndTwoObj（TextAndTwoObjects） / twoObjAndTx（TwoObjectsAndText） / twoObjOverTx（TwoObjectsOverText） / fourObj（FourObjects） / vertTx（VerticalText） / clipArtAndVertTx（ClipArtAndVerticalText） / vertTitleAndTx（VerticalTitleAndText） / vertTitleAndTxOverChart（VerticalTitleAndTextOverChart） / twoObj（TwoObjects） / objAndTwoObj（ObjectAndTwoObjects） / twoObjAndObj（TwoObjectsAndObject） / cust（Custom） / secHead（SectionHeader） / twoTxTwoObj（TwoTextAndTwoObjects） / objTx（ObjectText） / picTx（PictureText） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 父母版<br>`layout.master_ref` | 结构参数 `ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 版式对象<br>`layout.objects` | 结构参数 `object[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 保留未使用版式<br>`layout.preserve` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 版式匹配名称<br>`layout.matching_name` | 字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 占位符类型<br>`placeholder.type` | title（Title） / body（Body） / ctrTitle（CenteredTitle） / subTitle（SubTitle） / dt（DateAndTime） / sldNum（SlideNumber） / ftr（Footer） / hdr（Header） / obj（Object） / chart（Chart） / tbl（Table） / clipArt（ClipArt） / dgm（Diagram） / media（Media） / sldImg（SlideImage） / pic（Picture） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 继承匹配索引<br>`placeholder.index` | 整数；单位 —；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 占位符方向<br>`placeholder.orientation` | horz（Horizontal） / vert（Vertical） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 占位符尺寸类别<br>`placeholder.size_hint` | full（Full） / half（Half） / quarter（Quarter） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 位置、文字和样式继承<br>`placeholder.style_inheritance` | 结构参数 `style_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 母版颜色映射<br>`master.color_map` | 结构参数 `theme_map`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 保留未使用母版<br>`master.preserve` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 母版时间树<br>`master.timeline` | 结构参数 `time_graph`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 母版切换<br>`master.transition` | 结构参数 `transition`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 版式颜色映射覆盖<br>`layout.color_map_override` | 结构参数 `theme_map`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 版式页眉页脚<br>`layout.header_footer` | 结构参数 `header_footer`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 显示母版对象<br>`layout.show_master_shapes` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 显示母版占位符动画<br>`layout.show_master_placeholder_animations` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 版式时间树<br>`layout.timeline` | 结构参数 `time_graph`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 版式切换<br>`layout.transition` | 结构参数 `transition`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |

## 对象身份、层级、几何与锁定

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 稳定对象标识<br>`object.id` | 稳定标识字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 对象名称<br>`object.name` | 字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 对象类型<br>`object.kind` | text_box / shape / connector / group / picture / table / chart / smartart / equation / audio / video / model3d / ink / ole / control / web_extension / zoom / live_feed | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 分组父对象<br>`object.parent_ref` | 结构参数 `ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 堆叠顺序<br>`object.z_order` | 整数；单位 —；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 位置与尺寸<br>`object.frame` | {left, top, width, height}；位置可为负，尺寸需满足原生约束 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 二维旋转<br>`object.rotation` | 有限数值；单位 deg；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 水平翻转<br>`object.flip_horizontal` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 垂直翻转<br>`object.flip_vertical` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 仿射变换<br>`object.transform` | {a, b, c, d, e, f}；完整仿射矩阵，平移单位见映射 | a:xfrm 支持位置、尺寸、旋转和翻转，不能直接存任意矩阵；剪切需要分解或烘焙，文字等对象可能无法保持同等编辑能力。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 分组子坐标系<br>`object.group_child_frame` | {left, top, width, height}；位置可为负，尺寸需满足原生约束 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 锁定比例<br>`object.lock_aspect_ratio` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 静态格式无对应编辑锁；可作为元数据供特定编辑器使用。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 选择、移动、缩放、旋转、组合等锁定<br>`object.locks` | 结构参数 `lock_map`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 静态格式无对应编辑锁；可作为元数据供特定编辑器使用。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 对象隐藏<br>`object.hidden` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 黑白打印模式<br>`object.black_white_mode` | clr（Color） / auto（Auto） / gray（Gray） / ltGray（LightGray） / invGray（InvGray） / grayWhite（GrayWhite） / blackGray（BlackGray） / blackWhite（BlackWhite） / black（Black） / white（White） / hidden（Hidden） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 主题样式引用<br>`object.style_ref` | 结构参数 `style_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 占位符绑定<br>`object.placeholder_ref` | 结构参数 `ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| Office 对象创建标识<br>`object.creation_id` | GUID | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |

## 预设几何、自由曲线与连接线

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 预设形状类型<br>`shape.geometry.preset` | line（Line） / lineInv（LineInverse） / triangle（Triangle） / rtTriangle（RightTriangle） / rect（Rectangle） / diamond（Diamond） / parallelogram（Parallelogram） / trapezoid（Trapezoid） / nonIsoscelesTrapezoid（NonIsoscelesTrapezoid） / pentagon（Pentagon） / hexagon（Hexagon） / heptagon（Heptagon） / octagon（Octagon） / decagon（Decagon） / dodecagon（Dodecagon） / star4（Star4） / star5（Star5） / star6（Star6） / star7（Star7） / star8（Star8） / star10（Star10） / star12（Star12） / star16（Star16） / star24（Star24） / star32（Star32） / roundRect（RoundRectangle） / round1Rect（Round1Rectangle） / round2SameRect（Round2SameRectangle） / round2DiagRect（Round2DiagonalRectangle） / snipRoundRect（SnipRoundRectangle） / snip1Rect（Snip1Rectangle） / snip2SameRect（Snip2SameRectangle） / snip2DiagRect（Snip2DiagonalRectangle） / plaque（Plaque） / ellipse（Ellipse） / teardrop（Teardrop） / homePlate（HomePlate） / chevron（Chevron） / pieWedge（PieWedge） / pie（Pie） / blockArc（BlockArc） / donut（Donut） / noSmoking（NoSmoking） / rightArrow（RightArrow） / leftArrow（LeftArrow） / upArrow（UpArrow） / downArrow（DownArrow） / stripedRightArrow（StripedRightArrow） / notchedRightArrow（NotchedRightArrow） / bentUpArrow（BentUpArrow） / leftRightArrow（LeftRightArrow） / upDownArrow（UpDownArrow） / leftUpArrow（LeftUpArrow） / leftRightUpArrow（LeftRightUpArrow） / quadArrow（QuadArrow） / leftArrowCallout（LeftArrowCallout） / rightArrowCallout（RightArrowCallout） / upArrowCallout（UpArrowCallout） / downArrowCallout（DownArrowCallout） / leftRightArrowCallout（LeftRightArrowCallout） / upDownArrowCallout（UpDownArrowCallout） / quadArrowCallout（QuadArrowCallout） / bentArrow（BentArrow） / uturnArrow（UTurnArrow） / circularArrow（CircularArrow） / leftCircularArrow（LeftCircularArrow） / leftRightCircularArrow（LeftRightCircularArrow） / curvedRightArrow（CurvedRightArrow） / curvedLeftArrow（CurvedLeftArrow） / curvedUpArrow（CurvedUpArrow） / curvedDownArrow（CurvedDownArrow） / swooshArrow（SwooshArrow） / cube（Cube） / can（Can） / lightningBolt（LightningBolt） / heart（Heart） / sun（Sun） / moon（Moon） / smileyFace（SmileyFace） / irregularSeal1（IrregularSeal1） / irregularSeal2（IrregularSeal2） / foldedCorner（FoldedCorner） / bevel（Bevel） / frame（Frame） / halfFrame（HalfFrame） / corner（Corner） / diagStripe（DiagonalStripe） / chord（Chord） / arc（Arc） / leftBracket（LeftBracket） / rightBracket（RightBracket） / leftBrace（LeftBrace） / rightBrace（RightBrace） / bracketPair（BracketPair） / bracePair（BracePair） / straightConnector1（StraightConnector1） / bentConnector2（BentConnector2） / bentConnector3（BentConnector3） / bentConnector4（BentConnector4） / bentConnector5（BentConnector5） / curvedConnector2（CurvedConnector2） / curvedConnector3（CurvedConnector3） / curvedConnector4（CurvedConnector4） / curvedConnector5（CurvedConnector5） / callout1（Callout1） / callout2（Callout2） / callout3（Callout3） / accentCallout1（AccentCallout1） / accentCallout2（AccentCallout2） / accentCallout3（AccentCallout3） / borderCallout1（BorderCallout1） / borderCallout2（BorderCallout2） / borderCallout3（BorderCallout3） / accentBorderCallout1（AccentBorderCallout1） / accentBorderCallout2（AccentBorderCallout2） / accentBorderCallout3（AccentBorderCallout3） / wedgeRectCallout（WedgeRectangleCallout） / wedgeRoundRectCallout（WedgeRoundRectangleCallout） / wedgeEllipseCallout（WedgeEllipseCallout） / cloudCallout（CloudCallout） / cloud（Cloud） / ribbon（Ribbon） / ribbon2（Ribbon2） / ellipseRibbon（EllipseRibbon） / ellipseRibbon2（EllipseRibbon2） / leftRightRibbon（LeftRightRibbon） / verticalScroll（VerticalScroll） / horizontalScroll（HorizontalScroll） / wave（Wave） / doubleWave（DoubleWave） / plus（Plus） / flowChartProcess（FlowChartProcess） / flowChartDecision（FlowChartDecision） / flowChartInputOutput（FlowChartInputOutput） / flowChartPredefinedProcess（FlowChartPredefinedProcess） / flowChartInternalStorage（FlowChartInternalStorage） / flowChartDocument（FlowChartDocument） / flowChartMultidocument（FlowChartMultidocument） / flowChartTerminator（FlowChartTerminator） / flowChartPreparation（FlowChartPreparation） / flowChartManualInput（FlowChartManualInput） / flowChartManualOperation（FlowChartManualOperation） / flowChartConnector（FlowChartConnector） / flowChartPunchedCard（FlowChartPunchedCard） / flowChartPunchedTape（FlowChartPunchedTape） / flowChartSummingJunction（FlowChartSummingJunction） / flowChartOr（FlowChartOr） / flowChartCollate（FlowChartCollate） / flowChartSort（FlowChartSort） / flowChartExtract（FlowChartExtract） / flowChartMerge（FlowChartMerge） / flowChartOfflineStorage（FlowChartOfflineStorage） / flowChartOnlineStorage（FlowChartOnlineStorage） / flowChartMagneticTape（FlowChartMagneticTape） / flowChartMagneticDisk（FlowChartMagneticDisk） / flowChartMagneticDrum（FlowChartMagneticDrum） / flowChartDisplay（FlowChartDisplay） / flowChartDelay（FlowChartDelay） / flowChartAlternateProcess（FlowChartAlternateProcess） / flowChartOffpageConnector（FlowChartOffpageConnector） / actionButtonBlank（ActionButtonBlank） / actionButtonHome（ActionButtonHome） / actionButtonHelp（ActionButtonHelp） / actionButtonInformation（ActionButtonInformation） / actionButtonForwardNext（ActionButtonForwardNext） / actionButtonBackPrevious（ActionButtonBackPrevious） / actionButtonEnd（ActionButtonEnd） / actionButtonBeginning（ActionButtonBeginning） / actionButtonReturn（ActionButtonReturn） / actionButtonDocument（ActionButtonDocument） / actionButtonSound（ActionButtonSound） / actionButtonMovie（ActionButtonMovie） / gear6（Gear6） / gear9（Gear9） / funnel（Funnel） / mathPlus（MathPlus） / mathMinus（MathMinus） / mathMultiply（MathMultiply） / mathDivide（MathDivide） / mathEqual（MathEqual） / mathNotEqual（MathNotEqual） / cornerTabs（CornerTabs） / squareTabs（SquareTabs） / plaqueTabs（PlaqueTabs） / chartX（ChartX） / chartStar（ChartStar） / chartPlus（ChartPlus） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 187 种预设必须解析各自几何和调节参数为 SVG 路径；SVG 没有对应的 PowerPoint 预设形状枚举。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 黄色调节柄参数<br>`shape.geometry.adjustments` | 结构参数 `named_formula[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 几何公式与辅助变量<br>`shape.geometry.guides` | 结构参数 `named_formula[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 多路径及轮廓<br>`shape.geometry.paths` | 结构参数 `path[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 移动、直线、二次和三次曲线、圆弧、闭合<br>`shape.geometry.commands` | moveTo / lineTo / quadBezierTo / cubicBezierTo / arcTo / close；点为路径局部数值或公式 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 路径填充规则<br>`shape.geometry.path_fill_rule` | nonzero / evenodd | 没有与 SVG nonzero/evenodd 同名的单一属性；需要几何与路径规则转换，不能等同 a:path/@fill。 | fill-rule 原生支持 nonzero / evenodd。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 形状内文字矩形<br>`shape.geometry.text_rect` | 结构参数 `formula_rect`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| XY/极坐标调节柄<br>`shape.geometry.handles` | 结构参数 `handle[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 连接点位置与方向<br>`shape.geometry.connection_sites` | 结构参数 `connection_site[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 路径描边标记<br>`shape.geometry.path_stroke` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 路径填充模式<br>`shape.geometry.path_fill` | none（None） / norm（Norm） / lighten（Lighten） / lightenLess（LightenLess） / darken（Darken） / darkenLess（DarkenLess） | a:path/@fill 原生支持 none/norm/lighten/lightenLess/darken/darkenLess。 | none/norm 可直接表达；lighten/darken 需要颜色或分层处理，不是 fill-rule。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 直线、折线或曲线连接类型<br>`connector.geometry` | straight / elbow / curved | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 线形可绘制；端点对象绑定和自动重路由不是 SVG 的同等原生编辑能力。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 起点对象与连接点<br>`connector.start_target` | 结构参数 `connection_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 线形可绘制；端点对象绑定和自动重路由不是 SVG 的同等原生编辑能力。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 终点对象与连接点<br>`connector.end_target` | 结构参数 `connection_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 线形可绘制；端点对象绑定和自动重路由不是 SVG 的同等原生编辑能力。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 连接路径及自动路由<br>`connector.routing` | 结构参数 `routing`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 线形可绘制；端点对象绑定和自动重路由不是 SVG 的同等原生编辑能力。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 独立路径坐标空间<br>`shape.geometry.coordinate_space` | 结构参数 `coordinate_space`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 路径 w/h 视口<br>`shape.geometry.path_viewport` | {width, height}；有限数值，尺寸需满足原生正值约束 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 数值和公式坐标引用<br>`shape.geometry.path_formula_refs` | 结构参数 `formula_ref[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 路径允许挤出<br>`shape.geometry.extrusion_ok` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |

## 文字片段与字体

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 文本内容<br>`text.run.text` | 字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 西文字体<br>`text.run.font.latin` | 结构参数 `font_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 东亚字体<br>`text.run.font.east_asian` | 结构参数 `font_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 复杂文字系统字体<br>`text.run.font.complex_script` | 结构参数 `font_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 符号字体<br>`text.run.font.symbol` | 结构参数 `font_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 字号<br>`text.run.font.size` | 有限数值；单位 pt；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 粗体<br>`text.run.font.bold` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 斜体<br>`text.run.font.italic` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 字体样式字面选择<br>`text.run.font.face` | 结构参数 `font_face`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 字体字符集<br>`text.run.font.charset` | 整数；单位 —；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 字距族与字体分类<br>`text.run.font.pitch_family` | 整数；单位 —；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 文字填充含渐变、图案和主题色<br>`text.run.fill` | 结构参数 `paint`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 文字轮廓描边<br>`text.run.outline` | 结构参数 `stroke`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 高亮填充<br>`text.run.highlight` | 结构参数 `color`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 下划线类型<br>`text.run.underline.type` | none（None） / words（Words） / sng（Single） / dbl（Double） / heavy（Heavy） / dotted（Dotted） / dottedHeavy（HeavyDotted） / dash（Dash） / dashHeavy（DashHeavy） / dashLong（DashLong） / dashLongHeavy（DashLongHeavy） / dotDash（DotDash） / dotDashHeavy（DotDashHeavy） / dotDotDash（DotDotDash） / dotDotDashHeavy（DotDotDashHeavy） / wavy（Wavy） / wavyHeavy（WavyHeavy） / wavyDbl（WavyDouble） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 基本下划线可原生 text-decoration；点线、粗线、双线和波浪等通常需额外几何，并验证随文字排版。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 下划线颜色或填充<br>`text.run.underline.fill` | 结构参数 `paint`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 下划线线型<br>`text.run.underline.stroke` | 结构参数 `stroke`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 单线、双线删除线<br>`text.run.strike` | noStrike（NoStrike） / sngStrike（SingleStrike） / dblStrike（DoubleStrike） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 全大写、小型大写或常规<br>`text.run.capitalization` | none（None） / small（Small） / all（All） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 字间距<br>`text.run.letter_spacing` | 有限数值；单位 pt；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 字偶距启用字号阈值<br>`text.run.kerning_threshold` | 有限数值；单位 pt；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 上标下标基线位移<br>`text.run.baseline_shift` | 有限数值；具体值域按该属性的原生约束，不能全部假定为 0–1 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 统一字符高度<br>`text.run.normalize_height` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 纵排组合字符<br>`text.run.kumimoji` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 语言<br>`text.run.language` | 语言标签，如 zh-CN / en-US | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 备用语言<br>`text.run.alternative_language` | 语言标签，如 zh-CN / en-US | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 校对、错误及脏标记<br>`text.run.proofing` | 结构参数 `proofing`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 片段从右至左<br>`text.run.rtl` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 书签<br>`text.run.bookmark` | 字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 点击超链接<br>`text.run.click_link` | 结构参数 `hyperlink`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 悬停超链接<br>`text.run.hover_link` | 结构参数 `hyperlink`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 文字效果集合<br>`text.run.effects` | 结构参数 `effect[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 字段 ID、类型、缓存文字和格式<br>`text.field.definition` | 结构参数 `field`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 数字随竖排旋转<br>`text.run.autorotate_numbers` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 文字等距离分布<br>`text.run.equalize_spacing` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |

## 段落、列表、缩进与制表位

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 有序文字、软换行、字段与行内公式<br>`text.paragraph.content` | 结构参数 `(Run\|Break\|Field\|Math)[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 左、右、居中、两端或分散对齐<br>`text.paragraph.alignment` | l（Left） / ctr（Center） / r（Right） / just（Justified） / justLow（JustifiedLow） / dist（Distributed） / thaiDist（ThaiDistributed） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | l/ctr/r 可用 text-anchor/定位；just/justLow/dist/thaiDist 需各自排版策略与语言处理，不能只映射一个 CSS 属性。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 段落层级<br>`text.paragraph.level` | 整数；单位 —；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 左缩进<br>`text.paragraph.left_margin` | 有限数值；单位 pt；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 右缩进<br>`text.paragraph.right_margin` | 有限数值；单位 pt；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 首行或悬挂缩进<br>`text.paragraph.first_line_indent` | 有限数值；单位 pt；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 固定或比例行距<br>`text.paragraph.line_spacing` | {mode: points或ratio, value: 有限数值}；固定值与相对倍数分别保存 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 段前间距<br>`text.paragraph.space_before` | {mode: points或ratio, value: 有限数值}；固定值与相对倍数分别保存 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 段后间距<br>`text.paragraph.space_after` | {mode: points或ratio, value: 有限数值}；固定值与相对倍数分别保存 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 默认制表间距<br>`text.paragraph.default_tab_size` | 有限数值；单位 pt；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 制表位位置和对齐<br>`text.paragraph.tab_stops` | [{position: pt, alignment: l/ctr/r/dec}]；左/居中/右/小数点对齐 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 段落从右至左<br>`text.paragraph.rtl` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 字符基线对齐<br>`text.paragraph.font_alignment` | auto（Automatic） / t（Top） / ctr（Center） / base（Baseline） / b（Bottom） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 东亚换行规则<br>`text.paragraph.east_asian_line_break` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 西文换行规则<br>`text.paragraph.latin_line_break` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 标点悬挂<br>`text.paragraph.hanging_punctuation` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 默认文字片段样式<br>`text.paragraph.default_run_style` | 结构参数 `run_style`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 段落结尾样式<br>`text.paragraph.end_run_style` | 结构参数 `run_style`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 无、字符、编号或图片项目符号<br>`text.paragraph.bullet.kind` | none / character / auto_number / picture | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 字符项目符号<br>`text.paragraph.bullet.character` | 字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 编号样式和起始值<br>`text.paragraph.bullet.numbering` | 结构参数 `numbering`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 项目符号字体或跟随文字<br>`text.paragraph.bullet.font` | 结构参数 `font_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 符号颜色或跟随文字<br>`text.paragraph.bullet.color` | 结构参数 `color`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 符号大小或跟随文字<br>`text.paragraph.bullet.size` | 结构参数 `size_mode`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 图片项目符号<br>`text.paragraph.bullet.image_ref` | 结构参数 `asset_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |

## 文本框、自动适应、竖排与艺术字

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 段落集合<br>`text.body.paragraphs` | 结构参数 `paragraph[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 四边内边距<br>`text.body.insets` | {left, top, right, bottom}；有限数值，单位见本行 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 垂直对齐<br>`text.body.vertical_anchor` | t（Top） / ctr（Center） / b（Bottom） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 居中锚定<br>`text.body.anchor_center` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 换行策略<br>`text.body.wrap` | none（None） / square（Square） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 无、缩小文字或放大形状<br>`text.body.autofit` | {mode: none/shrink_text/grow_shape}；shrinking 另带文字缩放和行距缩减参数 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 文字缩放与行距缩减<br>`text.body.autofit_scale` | 结构参数 `autofit_scale`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 文字旋转<br>`text.body.rotation` | 有限数值；单位 deg；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 竖排及东亚竖排模式<br>`text.body.vertical_mode` | horz（Horizontal） / vert（Vertical） / vert270（Vertical270） / wordArtVert（WordArtVertical） / eaVert（EastAsianVetical） / mongolianVert（MongolianVertical） / wordArtVertRtl（WordArtLeftToRight） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 分栏数量<br>`text.body.columns` | 整数；单位 —；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 栏间距<br>`text.body.column_spacing` | 有限数值；单位 pt；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 分栏从右至左<br>`text.body.columns_rtl` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 艺术字预设变形与调节参数<br>`text.body.wordart_warp` | 结构参数 `warp`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 保持文字直立<br>`text.body.upright` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 纵向溢出行为<br>`text.body.vertical_overflow` | overflow（Overflow） / ellipsis（Ellipsis） / clip（Clip） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 横向溢出行为<br>`text.body.horizontal_overflow` | overflow（Overflow） / clip（Clip） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 首尾段间距规则<br>`text.body.first_last_paragraph_spacing` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 兼容行距规则<br>`text.body.compatible_line_spacing` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 强制抗锯齿<br>`text.body.force_antialias` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 文字 3D 与平面文字<br>`text.body.text_3d` | 结构参数 `text3d`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 导入布局和断行缓存<br>`text.body.text_layout_cache` | 结构参数 `layout_cache`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |

## 颜色、所有填充与渐变参数

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 无、纯色、渐变、图案、图片或组继承<br>`paint.kind` | none / solid / gradient / pattern / image / group_inherit | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | none/solid 可直接表达；gradient/pattern/image 生成相应定义；group_inherit 需解析继承。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| RGB、主题、系统、预设、scRGB 或 HSL<br>`color.kind` | rgb / scrgb / hsl / scheme / system / preset | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | RGB/HSL 可直接输出颜色；主题、系统、预设和 scRGB/变换需要解析到输出颜色并确认颜色空间。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 颜色通道<br>`color.channels` | rgb/scRGB/HSL/主题/系统/预设颜色的通道或原生代码；由 color.kind 限定 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 透明度<br>`color.alpha` | 有限数值；0–1 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 色调、明暗、亮度、饱和、补色、反相、灰度、Gamma 等有序变换<br>`color.transforms` | 结构参数 `color_transform[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 纯色填充<br>`paint.solid.color` | 结构参数 `color`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 线性、圆形、矩形、沿形状路径<br>`paint.gradient.kind` | linear / circle / rect / shape | DrawingML gradFill：线性 lin 和 circle/rect/shape 路径渐变及色标等参数。 | linear/circle 可用 linearGradient/radialGradient；rect/shape 没有直接同型原生渐变，需专门渲染或近似，不能统一标为完全支持。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 多色标位置、颜色与透明度<br>`paint.gradient.stops` | [{offset: 0–1, color: 颜色对象}]；位置有序，允许同位置色标形成突变 | DrawingML gradFill：线性 lin 和 circle/rect/shape 路径渐变及色标等参数。 | linear/circle 可用 linearGradient/radialGradient；rect/shape 没有直接同型原生渐变，需专门渲染或近似，不能统一标为完全支持。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 线性渐变角度<br>`paint.gradient.angle` | 有限数值；单位 deg；允许负值/上下限需按属性确认 | DrawingML gradFill：线性 lin 和 circle/rect/shape 路径渐变及色标等参数。 | linear/circle 可用 linearGradient/radialGradient；rect/shape 没有直接同型原生渐变，需专门渲染或近似，不能统一标为完全支持。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 线性渐变随形状比例缩放<br>`paint.gradient.scaled` | false / true；未设置另行保留缺省行为 | DrawingML gradFill：线性 lin 和 circle/rect/shape 路径渐变及色标等参数。 | linear/circle 可用 linearGradient/radialGradient；rect/shape 没有直接同型原生渐变，需专门渲染或近似，不能统一标为完全支持。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 圆形、矩形或形状路径<br>`paint.gradient.path_kind` | shape（Shape） / circle（Circle） / rect（Rectangle） | DrawingML gradFill：线性 lin 和 circle/rect/shape 路径渐变及色标等参数。 | linear/circle 可用 linearGradient/radialGradient；rect/shape 没有直接同型原生渐变，需专门渲染或近似，不能统一标为完全支持。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 渐变中心/填充矩形<br>`paint.gradient.fill_to_rect` | {left, top, right, bottom}；允许负值，具体边界按原生字段 | DrawingML gradFill：线性 lin 和 circle/rect/shape 路径渐变及色标等参数。 | linear/circle 可用 linearGradient/radialGradient；rect/shape 没有直接同型原生渐变，需专门渲染或近似，不能统一标为完全支持。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 渐变平铺矩形<br>`paint.gradient.tile_rect` | {left, top, right, bottom}；允许负值，具体边界按原生字段 | DrawingML gradFill：线性 lin 和 circle/rect/shape 路径渐变及色标等参数。 | linear/circle 可用 linearGradient/radialGradient；rect/shape 没有直接同型原生渐变，需专门渲染或近似，不能统一标为完全支持。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 渐变翻转<br>`paint.gradient.flip` | none（None） / x（Horizontal） / y（Vertical） / xy（HorizontalAndVertical） | DrawingML gradFill：线性 lin 和 circle/rect/shape 路径渐变及色标等参数。 | linear/circle 可用 linearGradient/radialGradient；rect/shape 没有直接同型原生渐变，需专门渲染或近似，不能统一标为完全支持。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 渐变随形状旋转<br>`paint.gradient.rotate_with_shape` | false / true；未设置另行保留缺省行为 | DrawingML gradFill：线性 lin 和 circle/rect/shape 路径渐变及色标等参数。 | linear/circle 可用 linearGradient/radialGradient；rect/shape 没有直接同型原生渐变，需专门渲染或近似，不能统一标为完全支持。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 图案填充类型<br>`paint.pattern.preset` | pct5（Percent5） / pct10（Percent10） / pct20（Percent20） / pct25（Percent25） / pct30（Percent30） / pct40（Percent40） / pct50（Percent50） / pct60（Percent60） / pct70（Percent70） / pct75（Percent75） / pct80（Percent80） / pct90（Percent90） / horz（Horizontal） / vert（Vertical） / ltHorz（LightHorizontal） / ltVert（LightVertical） / dkHorz（DarkHorizontal） / dkVert（DarkVertical） / narHorz（NarrowHorizontal） / narVert（NarrowVertical） / dashHorz（DashedHorizontal） / dashVert（DashedVertical） / cross（Cross） / dnDiag（DownwardDiagonal） / upDiag（UpwardDiagonal） / ltDnDiag（LightDownwardDiagonal） / ltUpDiag（LightUpwardDiagonal） / dkDnDiag（DarkDownwardDiagonal） / dkUpDiag（DarkUpwardDiagonal） / wdDnDiag（WideDownwardDiagonal） / wdUpDiag（WideUpwardDiagonal） / dashDnDiag（DashedDownwardDiagonal） / dashUpDiag（DashedUpwardDiagonal） / diagCross（DiagonalCross） / smCheck（SmallCheck） / lgCheck（LargeCheck） / smGrid（SmallGrid） / lgGrid（LargeGrid） / dotGrid（DotGrid） / smConfetti（SmallConfetti） / lgConfetti（LargeConfetti） / horzBrick（HorizontalBrick） / diagBrick（DiagonalBrick） / solidDmnd（SolidDiamond） / openDmnd（OpenDiamond） / dotDmnd（DottedDiamond） / plaid（Plaid） / sphere（Sphere） / weave（Weave） / divot（Divot） / shingle（Shingle） / wave（Wave） / trellis（Trellis） / zigZag（ZigZag） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 54 种图案可通过 pattern 绘制；须逐种实现图案几何、比例、前背景色，不是自动一对一映射。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 图案前景色<br>`paint.pattern.foreground` | 结构参数 `color`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 图案背景色<br>`paint.pattern.background` | 结构参数 `color`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 图片填充资源<br>`paint.image.asset_ref` | 结构参数 `asset_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 图片填充裁剪<br>`paint.image.crop` | {left, top, right, bottom}；允许负值，具体边界按原生字段 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 拉伸或平铺<br>`paint.image.mode` | stretch / tile | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | stretch 用 image/填充框；tile 用 pattern，需要对齐、缩放、偏移和裁剪转换。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 图片拉伸区域<br>`paint.image.stretch_rect` | {left, top, right, bottom}；允许负值，具体边界按原生字段 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 平铺偏移<br>`paint.image.tile_offset` | {x, y}；数值和单位见本行 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 平铺缩放<br>`paint.image.tile_scale` | {x, y}；数值和单位见本行 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 平铺对齐<br>`paint.image.tile_alignment` | tl（TopLeft） / t（Top） / tr（TopRight） / l（Left） / ctr（Center） / r（Right） / bl（BottomLeft） / b（Bottom） / br（BottomRight） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 平铺翻转<br>`paint.image.tile_flip` | none（None） / x（Horizontal） / y（Vertical） / xy（HorizontalAndVertical） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 图片填充随形状旋转<br>`paint.image.rotate_with_shape` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 继承组填充<br>`paint.group_inheritance` | 结构参数 `style_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |

## 描边、箭头和线型

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 线宽<br>`stroke.width` | 有限数值；单位 pt；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 线条填充<br>`stroke.paint` | 结构参数 `paint`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 平端、圆端、方端<br>`stroke.cap` | rnd（Round） / sq（Square） / flat（Flat） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 斜接、圆角或斜角接合<br>`stroke.join` | miter / round / bevel | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 斜接限制<br>`stroke.miter_limit` | 有限数值；具体值域按该属性的原生约束，不能全部假定为 0–1 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 单线、双线、粗细组合<br>`stroke.compound` | sng（Single） / dbl（Double） / thickThin（ThickThin） / thinThick（ThinThick） / tri（Triple） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 单线可直接描边；复合线和内侧对齐需额外路径/裁剪，不能认为所有选项有同型 SVG 属性。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 居中或内侧线条对齐<br>`stroke.alignment` | ctr（Center） / in（Insert） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 单线可直接描边；复合线和内侧对齐需额外路径/裁剪，不能认为所有选项有同型 SVG 属性。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 预设虚线<br>`stroke.dash_preset` | solid（Solid） / dot（Dot） / dash（Dash） / lgDash（LargeDash） / dashDot（DashDot） / lgDashDot（LargeDashDot） / lgDashDotDot（LargeDashDotDot） / sysDash（SystemDash） / sysDot（SystemDot） / sysDashDot（SystemDashDot） / sysDashDotDot（SystemDashDotDot） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 自定义虚线长度间隔<br>`stroke.dash_custom` | [{dash, gap}]；相对线宽的长度，非负；需确认目标格式单位 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 起点箭头类型<br>`stroke.start_arrow.kind` | none（无） / triangle（三角） / stealth（燕尾） / diamond（菱形） / oval（椭圆） / arrow（开放箭头） | 原生 `a:headEnd/@type`；支持本行全部原生取值。 | 用 marker-start/marker-end 的矢量几何表达形状，并用 markerWidth/markerHeight、viewBox 和 markerUnits 控制尺寸；宽/长没有同名三档枚举，需按形状、线宽和变换映射并标定。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 起点箭头宽度类别<br>`stroke.start_arrow.width` | sm（窄） / med（中） / lg（宽） | 原生 `a:headEnd/@w`；支持本行全部原生取值。 | 用 marker-start/marker-end 的矢量几何表达形状，并用 markerWidth/markerHeight、viewBox 和 markerUnits 控制尺寸；宽/长没有同名三档枚举，需按形状、线宽和变换映射并标定。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 起点箭头长度类别<br>`stroke.start_arrow.length` | sm（短） / med（中） / lg（长） | 原生 `a:headEnd/@len`；支持本行全部原生取值。 | 用 marker-start/marker-end 的矢量几何表达形状，并用 markerWidth/markerHeight、viewBox 和 markerUnits 控制尺寸；宽/长没有同名三档枚举，需按形状、线宽和变换映射并标定。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 终点箭头类型<br>`stroke.end_arrow.kind` | none（无） / triangle（三角） / stealth（燕尾） / diamond（菱形） / oval（椭圆） / arrow（开放箭头） | 原生 `a:tailEnd/@type`；支持本行全部原生取值。 | 用 marker-start/marker-end 的矢量几何表达形状，并用 markerWidth/markerHeight、viewBox 和 markerUnits 控制尺寸；宽/长没有同名三档枚举，需按形状、线宽和变换映射并标定。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 终点箭头宽度类别<br>`stroke.end_arrow.width` | sm（窄） / med（中） / lg（宽） | 原生 `a:tailEnd/@w`；支持本行全部原生取值。 | 用 marker-start/marker-end 的矢量几何表达形状，并用 markerWidth/markerHeight、viewBox 和 markerUnits 控制尺寸；宽/长没有同名三档枚举，需按形状、线宽和变换映射并标定。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 终点箭头长度类别<br>`stroke.end_arrow.length` | sm（短） / med（中） / lg（长） | 原生 `a:tailEnd/@len`；支持本行全部原生取值。 | 用 marker-start/marker-end 的矢量几何表达形状，并用 markerWidth/markerHeight、viewBox 和 markerUnits 控制尺寸；宽/长没有同名三档枚举，需按形状、线宽和变换映射并标定。 | 原生属性 API（有条件）；完整验证仍按用例记录 |

## 二维效果与复合效果树

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 外阴影颜色、模糊、偏移、缩放、斜切、对齐<br>`effects.outer_shadow` | 结构参数 `shadow`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 部分可用 filter；效果和混合算法需逐项验证，不能统一声明等价。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 内阴影<br>`effects.inner_shadow` | 结构参数 `shadow`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 部分可用 filter；效果和混合算法需逐项验证，不能统一声明等价。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 预设阴影<br>`effects.preset_shadow` | 结构参数 `preset_shadow`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 部分可用 filter；效果和混合算法需逐项验证，不能统一声明等价。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 发光颜色与半径<br>`effects.glow` | 结构参数 `glow`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 部分可用 filter；效果和混合算法需逐项验证，不能统一声明等价。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 柔化边缘半径<br>`effects.soft_edge` | 有限数值；单位 pt；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 部分可用 filter；效果和混合算法需逐项验证，不能统一声明等价。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 倒影透明度、距离、模糊和变换<br>`effects.reflection` | 结构参数 `reflection`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 部分可用 filter；效果和混合算法需逐项验证，不能统一声明等价。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 模糊与边缘增长<br>`effects.blur` | 结构参数 `blur`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 部分可用 filter；效果和混合算法需逐项验证，不能统一声明等价。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 填充叠加与混合<br>`effects.fill_overlay` | 结构参数 `overlay`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 部分可用 filter；效果和混合算法需逐项验证，不能统一声明等价。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| Alpha 反转、阈值、替换、调制和组合<br>`effects.alpha` | 结构参数 `alpha_effect[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 部分可用 filter；效果和混合算法需逐项验证，不能统一声明等价。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 颜色替换<br>`effects.color_change` | 结构参数 `color_change`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 部分可用 filter；效果和混合算法需逐项验证，不能统一声明等价。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 双色调<br>`effects.duotone` | 结构参数 `color[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 部分可用 filter；效果和混合算法需逐项验证，不能统一声明等价。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 着色与明暗<br>`effects.tint` | 结构参数 `tint`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 部分可用 filter；效果和混合算法需逐项验证，不能统一声明等价。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 灰度<br>`effects.grayscale` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 部分可用 filter；效果和混合算法需逐项验证，不能统一声明等价。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 相对偏移<br>`effects.relative_offset` | {x, y}；数值和单位见本行 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 部分可用 filter；效果和混合算法需逐项验证，不能统一声明等价。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 效果变换<br>`effects.transform` | {a, b, c, d, e, f}；完整仿射矩阵，平移单位见映射 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 部分可用 filter；效果和混合算法需逐项验证，不能统一声明等价。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 有序效果树、引用及混合模式<br>`effects.dag` | 结构参数 `effect_graph`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 部分可用 filter；效果和混合算法需逐项验证，不能统一声明等价。 | 原生属性 API（有条件）；完整验证仍按用例记录 |

## 形状与文字 3D、相机、照明与模型

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 预设相机<br>`three_d.camera.preset` | legacyObliqueTopLeft（LegacyObliqueTopLeft） / legacyObliqueTop（LegacyObliqueTop） / legacyObliqueTopRight（LegacyObliqueTopRight） / legacyObliqueLeft（LegacyObliqueLeft） / legacyObliqueFront（LegacyObliqueFront） / legacyObliqueRight（LegacyObliqueRight） / legacyObliqueBottomLeft（LegacyObliqueBottomLeft） / legacyObliqueBottom（LegacyObliqueBottom） / legacyObliqueBottomRight（LegacyObliqueBottomRight） / legacyPerspectiveTopLeft（LegacyPerspectiveTopLeft） / legacyPerspectiveTop（LegacyPerspectiveTop） / legacyPerspectiveTopRight（LegacyPerspectiveTopRight） / legacyPerspectiveLeft（LegacyPerspectiveLeft） / legacyPerspectiveFront（LegacyPerspectiveFront） / legacyPerspectiveRight（LegacyPerspectiveRight） / legacyPerspectiveBottomLeft（LegacyPerspectiveBottomLeft） / legacyPerspectiveBottom（LegacyPerspectiveBottom） / legacyPerspectiveBottomRight（LegacyPerspectiveBottomRight） / orthographicFront（OrthographicFront） / isometricTopUp（IsometricTopUp） / isometricTopDown（IsometricTopDown） / isometricBottomUp（IsometricBottomUp） / isometricBottomDown（IsometricBottomDown） / isometricLeftUp（IsometricLeftUp） / isometricLeftDown（IsometricLeftDown） / isometricRightUp（IsometricRightUp） / isometricRightDown（IsometricRightDown） / isometricOffAxis1Left（IsometricOffAxis1Left） / isometricOffAxis1Right（IsometricOffAxis1Right） / isometricOffAxis1Top（IsometricOffAxis1Top） / isometricOffAxis2Left（IsometricOffAxis2Left） / isometricOffAxis2Right（IsometricOffAxis2Right） / isometricOffAxis2Top（IsometricOffAxis2Top） / isometricOffAxis3Left（IsometricOffAxis3Left） / isometricOffAxis3Right（IsometricOffAxis3Right） / isometricOffAxis3Bottom（IsometricOffAxis3Bottom） / isometricOffAxis4Left（IsometricOffAxis4Left） / isometricOffAxis4Right（IsometricOffAxis4Right） / isometricOffAxis4Bottom（IsometricOffAxis4Bottom） / obliqueTopLeft（ObliqueTopLeft） / obliqueTop（ObliqueTop） / obliqueTopRight（ObliqueTopRight） / obliqueLeft（ObliqueLeft） / obliqueRight（ObliqueRight） / obliqueBottomLeft（ObliqueBottomLeft） / obliqueBottom（ObliqueBottom） / obliqueBottomRight（ObliqueBottomRight） / perspectiveFront（PerspectiveFront） / perspectiveLeft（PerspectiveLeft） / perspectiveRight（PerspectiveRight） / perspectiveAbove（PerspectiveAbove） / perspectiveBelow（PerspectiveBelow） / perspectiveAboveLeftFacing（PerspectiveAboveLeftFacing） / perspectiveAboveRightFacing（PerspectiveAboveRightFacing） / perspectiveContrastingLeftFacing（PerspectiveContrastingLeftFacing） / perspectiveContrastingRightFacing（PerspectiveContrastingRightFacing） / perspectiveHeroicLeftFacing（PerspectiveHeroicLeftFacing） / perspectiveHeroicRightFacing（PerspectiveHeroicRightFacing） / perspectiveHeroicExtremeLeftFacing（PerspectiveHeroicExtremeLeftFacing） / perspectiveHeroicExtremeRightFacing（PerspectiveHeroicExtremeRightFacing） / perspectiveRelaxed（PerspectiveRelaxed） / perspectiveRelaxedModerately（PerspectiveRelaxedModerately） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 视野<br>`three_d.camera.field_of_view` | 有限数值；单位 deg；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 相机缩放<br>`three_d.camera.zoom` | 有限数值；具体值域按该属性的原生约束，不能全部假定为 0–1 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 纬度、经度、旋转<br>`three_d.camera.rotation` | 结构参数 `rotation3d`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 灯光预设<br>`three_d.light_rig.preset` | legacyFlat1（LegacyFlat1） / legacyFlat2（LegacyFlat2） / legacyFlat3（LegacyFlat3） / legacyFlat4（LegacyFlat4） / legacyNormal1（LegacyNormal1） / legacyNormal2（LegacyNormal2） / legacyNormal3（LegacyNormal3） / legacyNormal4（LegacyNormal4） / legacyHarsh1（LegacyHarsh1） / legacyHarsh2（LegacyHarsh2） / legacyHarsh3（LegacyHarsh3） / legacyHarsh4（LegacyHarsh4） / threePt（ThreePoints） / balanced（Balanced） / soft（Soft） / harsh（Harsh） / flood（Flood） / contrasting（Contrasting） / morning（Morning） / sunrise（Sunrise） / sunset（Sunset） / chilly（Chilly） / freezing（Freezing） / flat（Flat） / twoPt（TwoPoints） / glow（Glow） / brightRoom（BrightRoom） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 光照方向<br>`three_d.light_rig.direction` | tl（TopLeft） / t（Top） / tr（TopRight） / l（Left） / r（Right） / bl（BottomLeft） / b（Bottom） / br（BottomRight） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 灯光旋转<br>`three_d.light_rig.rotation` | 结构参数 `rotation3d`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 背景锚点、法向与上方向<br>`three_d.backdrop` | 结构参数 `backdrop3d`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 顶端棱台类型与尺寸<br>`three_d.bevel.top` | 结构参数 `bevel`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 底端棱台<br>`three_d.bevel.bottom` | 结构参数 `bevel`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 挤出深度<br>`three_d.extrusion_depth` | 有限数值；单位 pt；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 轮廓宽度<br>`three_d.contour_width` | 有限数值；单位 pt；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| Z 轴位置<br>`three_d.z_position` | 有限数值；单位 pt；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 材质预设<br>`three_d.material` | legacyMatte（LegacyMatte） / legacyPlastic（LegacyPlastic） / legacyMetal（LegacyMetal） / legacyWireframe（LegacyWireframe） / matte（Matte） / plastic（Plastic） / metal（Metal） / warmMatte（WarmMatte） / translucentPowder（TranslucentPowder） / powder（Powder） / dkEdge（DarkEdge） / softEdge（SoftEdge） / clear（Clear） / flat（Flat） / softmetal（SoftMetal） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 挤出颜色<br>`three_d.extrusion_color` | 结构参数 `color`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 轮廓颜色<br>`three_d.contour_color` | 结构参数 `color`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 嵌入或链接 3D 模型<br>`model3d.asset_ref` | 结构参数 `asset_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 3D 视口、缩放与相机<br>`model3d.viewport` | 结构参数 `viewport3d`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 3D 模型静态替代图<br>`model3d.poster_ref` | 结构参数 `asset_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 3D 模型动画<br>`model3d.animation` | 结构参数 `animation3d`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |

## 图片、SVG、墨迹与调整

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 图片资源<br>`picture.asset_ref` | 结构参数 `asset_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 链接图片与更新关系<br>`picture.link_ref` | 结构参数 `external_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 裁剪与扩展<br>`picture.crop` | {left, top, right, bottom}；允许负值，具体边界按原生字段 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 图片形状裁剪<br>`picture.geometry_mask` | 结构参数 `geometry`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 适配、填满与保持比例<br>`picture.aspect_fit` | contain / cover / stretch | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 亮度<br>`picture.brightness` | 有限数值；具体值域按该属性的原生约束，不能全部假定为 0–1 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 对比度<br>`picture.contrast` | 有限数值；具体值域按该属性的原生约束，不能全部假定为 0–1 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 颜色重着色<br>`picture.recolor` | 结构参数 `color_effect[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 透明颜色<br>`picture.transparent_color` | 结构参数 `color`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 图片透明度<br>`picture.alpha` | 有限数值；0–1 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 艺术效果及参数<br>`picture.artistic_effect` | 结构参数 `picture_effect`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 背景移除标记<br>`picture.background_removal` | 结构参数 `extension`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 图像压缩与分辨率元数据<br>`picture.compression` | 结构参数 `compression`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| SVG 原资源与替代图<br>`picture.svg_asset` | 结构参数 `vector_asset`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 使用本地 DPI 标志<br>`picture.local_dpi` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 裁剪锁定与比例约束<br>`picture.crop_locked` | 结构参数 `lock_map`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 墨迹轨迹与绘制属性<br>`ink.strokes` | 结构参数 `ink_data`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 墨迹形状和图层绑定<br>`ink.shape_binding` | 结构参数 `ref[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |

## 原生表格、单元格与样式

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 列宽<br>`table.grid_columns` | 结构参数 `length[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 行高<br>`table.rows.height` | 结构参数 `length[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 单元格富文本<br>`table.cells.content` | 结构参数 `text_body[][]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 合并、跨行跨列及延续标志<br>`table.cells.merge` | 结构参数 `merge_map`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 单元格填充<br>`table.cells.fill` | 结构参数 `paint`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 上下左右和对角线边框<br>`table.cells.borders` | 结构参数 `stroke_map`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 单元格内边距<br>`table.cells.insets` | {left, top, right, bottom}；有限数值，单位见本行 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 单元格垂直对齐<br>`table.cells.vertical_anchor` | t（Top） / ctr（Center） / b（Bottom） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 单元格文字方向<br>`table.cells.text_direction` | horz（Horizontal） / vert（Vertical） / vert270（Vertical270） / wordArtVert（WordArtVertical） / eaVert（EastAsianVetical） / mongolianVert（MongolianVertical） / wordArtVertRtl（WordArtLeftToRight） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 单元格居中锚定<br>`table.cells.anchor_center` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 单元格溢出策略<br>`table.cells.overflow` | overflow（Overflow） / clip（Clip） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 表格样式及自定义样式<br>`table.style_ref` | 结构参数 `style_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 首行样式开关<br>`table.first_row` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 末行样式开关<br>`table.last_row` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 首列样式开关<br>`table.first_column` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 末列样式开关<br>`table.last_column` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 横向条带<br>`table.band_rows` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 纵向条带<br>`table.band_columns` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 表格从右至左<br>`table.rtl` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 样式与直接格式优先级<br>`table.cell_style_inheritance` | 结构参数 `style_rules`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |

## 完整图表对象、数据与工作簿

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 图表类型含现代 chartEx<br>`chart.type` | area3DChart / areaChart / bar3DChart / barChart / bubbleChart / doughnutChart / line3DChart / lineChart / ofPieChart / pie3DChart / pieChart / radarChart / scatterChart / stockChart / surface3DChart / surfaceChart / combo / histogram / pareto / boxWhisker / waterfall / funnel / treemap / sunburst / regionMap | 经典图表子元素、组合图和现代 chartEx 布局可保存；柱/条、堆叠、平滑和 3D 等由附加参数区分。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 组合图、分组与次坐标轴分配<br>`chart.plots` | 结构参数 `plot[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 类别、多级类别与日期<br>`chart.categories` | 结构参数 `category_data`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 系列名称、数据、类别和顺序<br>`chart.series` | 结构参数 `series[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 内嵌工作簿或外链<br>`chart.data_source` | 结构参数 `workbook_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 公式、区域引用与数据来源<br>`chart.data_formulas` | 结构参数 `formula_refs`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 类别与数据缓存<br>`chart.cached_data` | 结构参数 `chart_cache`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 外部数据更新策略<br>`chart.external_data_update` | 结构参数 `update_policy`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 空白值显示方式<br>`chart.blank_values` | span（Span） / gap（Gap） / zero（Zero） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 只绘制可见数据<br>`chart.visible_data_only` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 图表样式、颜色和主题<br>`chart.style_ref` | 结构参数 `chart_style`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 图表富文本标题与位置<br>`chart.title` | 结构参数 `chart_label`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 图例位置、文本、条目与布局<br>`chart.legend` | 结构参数 `legend`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 主次类别/数值/日期/系列轴<br>`chart.axes` | 结构参数 `axis[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 范围、对数、反向与刻度<br>`chart.axes.scale` | 结构参数 `axis_scale`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 交叉位置与标签位置<br>`chart.axes.crossing` | 结构参数 `axis_crossing`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 数值格式及来源链接<br>`chart.axes.number_format` | 结构参数 `number_format`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 主次网格线<br>`chart.axes.gridlines` | 结构参数 `gridlines`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 坐标轴标题<br>`chart.axes.title` | 结构参数 `chart_label`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 主次刻度线与间隔<br>`chart.axes.ticks` | 结构参数 `axis_ticks`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 值、名称、百分比、分隔符、位置和逐点覆盖<br>`chart.data_labels` | 结构参数 `data_label[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 引导线<br>`chart.data_labels.leader_lines` | 结构参数 `stroke`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 标记类型、大小和逐点样式<br>`chart.markers` | 结构参数 `marker[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 趋势线、方程与 R²<br>`chart.trendlines` | 结构参数 `trendline[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 误差线类型、值和样式<br>`chart.error_bars` | 结构参数 `error_bar[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 系列、逐点填充和描边<br>`chart.series.style` | 结构参数 `series_style[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 柱/条间距与重叠<br>`chart.series.gap_overlap` | 结构参数 `series_spacing`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 线条平滑<br>`chart.series.smoothing` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 扇形分离<br>`chart.series.explosion` | 有限数值；具体值域按该属性的原生约束，不能全部假定为 0–1 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 圆环内径<br>`chart.series.doughnut_hole` | 有限数值；具体值域按该属性的原生约束，不能全部假定为 0–1 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 图表内数据表<br>`chart.data_table` | 结构参数 `chart_data_table`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 图表元素手动布局<br>`chart.manual_layout` | 结构参数 `chart_layout`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 绘图区填充、边框和布局<br>`chart.plot_area` | 结构参数 `chart_area`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 图表区填充、边框和布局<br>`chart.chart_area` | 结构参数 `chart_area`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 旋转、视角、深度、地板与墙面<br>`chart.three_d` | 结构参数 `chart3d`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 直方图、箱线图、瀑布、树图、旭日、地图等参数<br>`chart.modern_options` | 结构参数 `extension_map`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |

## SmartArt 数据与布局语义

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 节点、连接、语义结构<br>`smartart.data_model` | 结构参数 `diagram_data`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 节点富文本<br>`smartart.node_text` | 结构参数 `text_body[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 布局定义和算法参数<br>`smartart.layout_ref` | 结构参数 `diagram_layout`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 颜色定义<br>`smartart.colors_ref` | 结构参数 `diagram_colors`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 快速样式<br>`smartart.quick_style_ref` | 结构参数 `diagram_style`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 缓存的绘图部件<br>`smartart.rendered_drawing` | 结构参数 `drawing_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 节点标识与对象绑定<br>`smartart.node_ids` | 结构参数 `id_map`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 布局方向<br>`smartart.direction` | norm（Normal） / rev（Reversed） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 节点手动位置和大小调整<br>`smartart.node_adjustments` | 结构参数 `node_adjustments`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |

## 公式与数学结构

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| Office Math 完整表达式树<br>`math.content` | 结构参数 `omml_tree`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| LaTeX 等源表示及溯源<br>`math.source` | 结构参数 `math_source`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 行内或独立公式<br>`math.display_mode` | inline / display | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 数学字体、字号、颜色与字形<br>`math.style` | 结构参数 `math_style`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 公式对齐<br>`math.alignment` | left / center / right / center_group | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 公式与普通文本的间距<br>`math.spacing` | 结构参数 `math_spacing`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 兼容分支与替代表示<br>`math.compatibility_choice` | 结构参数 `compatibility_tree`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |

## 音频、视频、旁白与播放

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 音频、视频或旁白<br>`media.kind` | audio / video / narration | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 嵌入媒体<br>`media.asset_ref` | 结构参数 `asset_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 外部媒体与在线媒体信息<br>`media.external_ref` | 结构参数 `external_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 封面帧<br>`media.poster_ref` | 结构参数 `asset_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 裁剪起点<br>`media.trim_start` | 有限数值；单位 ms；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 裁剪终点<br>`media.trim_end` | 有限数值；单位 ms；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 音量<br>`media.volume` | 有限数值；0–1 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 静音<br>`media.mute` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 循环播放<br>`media.loop` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 跨页播放<br>`media.play_across_slides` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 停止时隐藏<br>`media.hide_when_stopped` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 播放后回到起点<br>`media.rewind_after_play` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 淡入时长<br>`media.fade_in` | 有限数值；单位 ms；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 淡出时长<br>`media.fade_out` | 有限数值；单位 ms；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 书签时间点<br>`media.bookmarks` | 结构参数 `media_bookmark[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 播放触发绑定<br>`media.play_trigger` | 结构参数 `trigger`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 控制与全屏播放<br>`media.controls` | 结构参数 `media_controls`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 字幕轨道集合<br>`media.caption_tracks` | 结构参数 `caption_track[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 字幕轨道标识<br>`media.caption_track.id` | 稳定标识字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 字幕语言<br>`media.caption_track.language` | 语言标签，如 zh-CN / en-US | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 字幕轨道标签<br>`media.caption_track.label` | 字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 嵌入或链接字幕资源<br>`media.caption_track.resource` | 结构参数 `asset_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| Cameo 对象和 LiveFeed 属性<br>`live_feed.properties` | 结构参数 `extension`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 实时摄像头占位符<br>`live_feed.placeholder` | 结构参数 `placeholder_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 实时源背景处理<br>`live_feed.background_removal` | 结构参数 `extension`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 实时摄像头静态替代图<br>`live_feed.poster_ref` | 结构参数 `asset_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 设备、权限和运行环境绑定<br>`live_feed.host_binding` | 结构参数 `host_binding`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 宿主 / 容器流程；完整验证仍按用例记录 |

## 完整时间树、触发与对象动画

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 并行、串行与时间节点树<br>`animation.timeline` | 结构参数 `time_graph`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 对象、文字范围或图表目标<br>`animation.target_ref` | 结构参数 `animation_target`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 出现、强调、退出、动作路径及属性行为<br>`animation.behavior` | entrance / emphasis / exit / motion_path / property / command / media | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 预设类、ID 与子类型<br>`animation.preset` | 结构参数 `preset_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 点击、同前、后前、媒体书签、事件条件<br>`animation.trigger` | 结构参数 `trigger[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 延迟<br>`animation.delay` | 有限数值；单位 ms；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 时长及自动/不定长模式<br>`animation.duration` | 毫秒数值 / automatic / indefinite；不同时间字段分别限制 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 次数或重复时间<br>`animation.repeat` | 结构参数 `repeat`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 自动反转<br>`animation.autoreverse` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 播放速度<br>`animation.speed` | 有限数值；具体值域按该属性的原生约束，不能全部假定为 0–1 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 加速比例<br>`animation.acceleration` | 有限数值；0–1 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 减速比例<br>`animation.deceleration` | 有限数值；0–1 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 结束保留和重启规则<br>`animation.fill_mode` | remove（Remove） / freeze（Freeze） / hold（Hold） / transition（Transition） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 时间、值与插值<br>`animation.keyframes` | 结构参数 `keyframe[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 运动路径及原点<br>`animation.motion_path` | 结构参数 `motion_path`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 位置、缩放和旋转动画<br>`animation.transform` | 结构参数 `transform_animation`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 颜色动画与颜色空间<br>`animation.color` | 结构参数 `color_animation`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 滤镜、进出场与效果参数<br>`animation.effect` | 结构参数 `effect_animation`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 媒体或对象播放命令<br>`animation.command` | 结构参数 `command`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 逐字、逐词、逐段或层级构建<br>`animation.text_build` | 结构参数 `text_build`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 图表系列与类别构建<br>`animation.chart_build` | 结构参数 `chart_build`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| SmartArt 构建<br>`animation.diagram_build` | 结构参数 `diagram_build`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 迭代间隔和粒度<br>`animation.iteration` | 结构参数 `iteration`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 交互序列与时间节点绑定<br>`animation.runtime_state` | 结构参数 `runtime_binding`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 宿主 / 容器流程；完整验证仍按用例记录 |

## 页面切换、Morph 与 Zoom

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 标准和 Office 扩展切换类型<br>`transition.kind` | p14:conveyor / p14:doors / p14:ferris / p14:flash / p14:flip / p14:flythrough / p14:gallery / p14:glitter / p14:honeycomb / p14:pan / p14:prism / p14:reveal / p14:ripple / p14:shred / p14:switch / p14:vortex / p14:warp / p14:wheelReverse / p14:window / p15:prstTrans / p:blinds / p:checker / p:circle / p:comb / p:cover / p:cut / p:diamond / p:dissolve / p:fade / p:newsflash / p:plus / p:pull / p:push / p:random / p:randomBar / p:split / p:strips / p:wedge / p:wheel / p:wipe / p:zoom / p159:morph / none | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 方向及子类型<br>`transition.direction` | l / u / r / d / lu / ru / ld / rd / out / in / horz / vert | 方向仅按具体效果使用：侧向 l/r/u/d、角向 lu/ru/ld/rd、进出 in/out、朝向 horz/vert；不是每个效果支持全部。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 切换时长<br>`transition.duration` | 有限数值；单位 ms；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 速度预设<br>`transition.speed` | slow（Slow） / med（Medium） / fast（Fast） | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 单击换页<br>`transition.advance_on_click` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 自动换页时间<br>`transition.advance_after` | 有限数值；单位 ms；允许负值/上下限需按属性确认 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 换页声音与循环<br>`transition.sound` | 结构参数 `media_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| Morph 模式与对象匹配标识<br>`transition.morph` | 结构参数 `morph`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 页面、节或摘要缩放<br>`zoom.kind` | slide / section / summary | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 导航目标<br>`zoom.target_refs` | 结构参数 `ref[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 缩放返回与背景显示<br>`zoom.return_behavior` | 结构参数 `zoom_behavior`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 缩放缩略图资源<br>`zoom.thumbnail_ref` | 结构参数 `asset_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |

## 超链接与动作

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 点击或鼠标悬停<br>`interaction.event` | click / hover | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| URL、页、文档或自定义放映目标<br>`interaction.hyperlink` | 结构参数 `hyperlink`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 提示文字<br>`interaction.tooltip` | 字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 点击高亮与访问状态<br>`interaction.highlight_click` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 下一页、上一页、首尾页与返回<br>`interaction.navigation_action` | next_slide / previous_slide / first_slide / last_slide / last_viewed_slide / end_show / named_slide / custom_show | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 媒体播放动作<br>`interaction.media_action` | 结构参数 `media_action`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| OLE、程序或宏动作描述<br>`interaction.object_action` | 结构参数 `action_descriptor`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 动作声音<br>`interaction.sound` | 结构参数 `media_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 导航历史设置<br>`interaction.history` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | SVG 可表达对应外观；本行的布局、语义或参数转换需实现。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |

## 备注、讲义、放映与打印

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 备注页富文本与对象<br>`notes.content` | 结构参数 `notes_page`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 备注母版<br>`notes.master_ref` | 结构参数 `ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 讲义母版与对象<br>`handout.master` | 结构参数 `handout_master`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 自定义放映页面列表<br>`slideshow.custom_shows` | 结构参数 `custom_show[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 放映范围<br>`slideshow.range` | 结构参数 `slide_range`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 演讲者、窗口或展台模式<br>`slideshow.kind` | speaker / window / kiosk | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 循环放映<br>`slideshow.loop` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 使用计时<br>`slideshow.use_timings` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 显示动画<br>`slideshow.show_animation` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 播放旁白<br>`slideshow.show_narration` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 演示笔颜色<br>`slideshow.pen_color` | 结构参数 `color`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 打印范围、颜色模式与讲义选项<br>`print.options` | 结构参数 `print_options`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |

## 批注、无障碍与协作元数据

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 传统批注、作者、位置和时间<br>`comments.legacy` | 结构参数 `comment[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 现代批注、回复和解决状态<br>`comments.threads` | 结构参数 `comment_thread[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 人员与身份引用<br>`comments.people` | 结构参数 `person[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 批注对象和文字锚定<br>`comments.anchors` | 结构参数 `comment_anchor`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 替代标题<br>`accessibility.title` | 字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 替代描述<br>`accessibility.description` | 字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 装饰性对象标志<br>`accessibility.decorative` | false / true；未设置另行保留缺省行为 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 辅助阅读顺序<br>`accessibility.reading_order` | 结构参数 `ref[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 对象标签<br>`metadata.tags` | 结构参数 `map`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 自定义部件与业务数据<br>`metadata.customer_data` | 结构参数 `part_refs`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 个人信息与隐藏内容处理策略<br>`metadata.hidden_data_policy` | 结构参数 `policy`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |

## 嵌入对象、控件与扩展

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| OLE、工作簿、控件或其他嵌入包<br>`embedded.kind` | ole / embedded_package / activex_control / web_extension | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 二进制或子包资源<br>`embedded.asset_ref` | 结构参数 `asset_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 对象程序标识<br>`embedded.prog_id` | 字符串 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 链接对象来源<br>`embedded.link_ref` | 结构参数 `external_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 对象预览图<br>`embedded.preview_ref` | 结构参数 `asset_ref`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 图标或内容显示<br>`embedded.display_mode` | content / icon | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 激活动作描述<br>`embedded.activation` | 结构参数 `activation`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 宿主 / 容器流程；完整验证仍按用例记录 |
| 控件和持久化数据<br>`embedded.control_properties` | 结构参数 `opaque_parts`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| Web 扩展、绑定和任务窗格部件<br>`embedded.web_extensions` | 结构参数 `opaque_parts`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |

## 保护、签名、标签与兼容保留

| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |
| --- | --- | --- | --- | --- |
| 加密容器与参数<br>`package.security.encryption` | 结构参数 `encryption_profile`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 宿主 / 容器流程；完整验证仍按用例记录 |
| IRM 与授权策略引用<br>`package.security.permissions` | 结构参数 `rights_profile`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 宿主 / 容器流程；完整验证仍按用例记录 |
| 写保护与只读建议<br>`package.security.write_protection` | 结构参数 `protection`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 数字签名及修改后的有效性<br>`package.security.signature` | 结构参数 `signature_profile`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 宿主 / 容器流程；完整验证仍按用例记录 |
| 敏感度标签与策略<br>`package.security.sensitivity` | 结构参数 `label_profile`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 宿主 / 容器流程；完整验证仍按用例记录 |
| pptx/pptm 容器差异与宏部件<br>`package.macro_profile` | 结构参数 `format_profile`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 未建模 XML 与 QName<br>`compatibility.unknown_xml` | 结构参数 `opaque_xml[]`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 未建模资源部件和关系<br>`compatibility.unknown_parts` | 结构参数 `opaque_parts`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 兼容分支及所需命名空间<br>`compatibility.alternate_content` | 结构参数 `compatibility_tree`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 扩展项及 URI<br>`compatibility.extension_list` | 结构参数 `extension_map`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 原生属性 API（有条件）；完整验证仍按用例记录 |
| 稳定语义 ID 与本地 rId 映射<br>`compatibility.relationship_map` | 结构参数 `relation_map`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
| 生成器和编辑器元数据<br>`compatibility.producer_metadata` | 结构参数 `producer_metadata`；不是单个固定枚举 | PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。 | 主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。 | 模板保留 / 显式 XML 绑定；完整验证仍按用例记录 |
