# 当前实现矩阵

同一文档模型可导出 PPTX 和静态 SVG。此表覆盖属性目录中的全部 475 行，列出实际调用方式。

“原生属性 API”表示已有 Python 绑定，并按列出的条件使用；不是全部对象上下文和渲染器均已逐项验证。其余属性可通过原模板保留，或使用显式 `native_bindings` / `native_parts` 编辑原生 XML。XML 绑定检查精确目标和包关系，语义与目标 PowerPoint 外观仍需参考文件验证。宿主设置不能用 XML 替代。

静态 SVG 由同一 PPTX 的 LibreOffice Impress 排版导出，文字与路径尽量保留原生 SVG 元素；特殊效果可由渲染器栅格化。SVG 包含模型 metadata，可恢复该页面的原生制作源，并检查外观哈希是否仍对应。

当前分布：266 项属性 API；202 项模板保留或显式 XML 绑定；7 项宿主依赖。

| 属性 | 当前调用方式 | 条件 / 验证边界 |
| --- | --- | --- |
| `document.id` 文档标识 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `document.metadata.title` 标题 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `document.metadata.subject` 主题 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `document.metadata.author` 作者 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `document.metadata.keywords` 关键词 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `document.metadata.description` 说明 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `document.metadata.created` 创建时间 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `document.metadata.modified` 修改时间 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `document.metadata.revision` 修订号 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `document.metadata.custom_properties` 自定义属性 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `document.page_size` 页面尺寸 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `document.orientation` 页面方向 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `document.default_language` 默认语言 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `document.layout_direction` 布局方向 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `document.fonts.embedded` 嵌入字体资源与字形子集 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `document.fonts.fallback` 字体替代与解析策略 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `document.assets` 媒体资源与关系 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `document.custom_xml` 自定义 XML 部件 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `document.color_map` 全局颜色映射 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `document.guides` 参考线 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `document.grid_spacing` 网格间距 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `document.sections` 节与页面顺序 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `document.compatibility_profile` 目标 Office 版本与能力 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `slide.id` 稳定页面标识 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `slide.name` 页面名称 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `slide.order` 页面顺序 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `slide.hidden` 隐藏页面 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `slide.layout_ref` 绑定版式 | 原生属性 API（有条件） | Creating a page binds an existing layout; changing an imported page layout requires explicit placeholder remapping. |
| `slide.master_ref` 绑定母版 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `slide.theme_override` 页面主题覆盖 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `slide.background` 背景填充 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `slide.background_follow_master` 继承母版背景 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `slide.show_master_shapes` 显示母版对象 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `slide.header_footer` 日期、页码、页脚内容和显示 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `slide.comments_ref` 批注关系 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `slide.tags` 标签与自定义数据 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `slide.creation_id` Office 创建标识 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `slide.color_map_override` 颜色映射覆盖 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `slide.objects` 绘图对象和层级 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `theme.colors` 主题色槽与系统色 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `theme.fonts.major` 标题字体与各文字系统字体 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `theme.fonts.minor` 正文字体与各文字系统字体 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `theme.format_scheme` 填充、描边和效果样式集合 | 原生属性 API（有条件） | Exact a:fmtScheme XML tree. |
| `theme.extra_color_schemes` 额外配色方案 | 原生属性 API（有条件） | Exact a:extraClrSchemeLst XML tree. |
| `theme.defaults` 对象、线条和文字默认样式 | 原生属性 API（有条件） | Exact a:objectDefaults XML tree. |
| `master.id` 母版标识 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `master.background` 母版背景 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `master.objects` 母版固定对象 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `master.text_styles` 标题、正文、其他文本分级样式 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `master.layout_refs` 母版版式列表 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `master.header_footer` 母版页眉页脚 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `layout.id` 版式标识 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `layout.type` 版式类型 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `layout.master_ref` 父母版 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `layout.objects` 版式对象 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `layout.preserve` 保留未使用版式 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `layout.matching_name` 版式匹配名称 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `placeholder.type` 占位符类型 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `placeholder.index` 继承匹配索引 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `placeholder.orientation` 占位符方向 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `placeholder.size_hint` 占位符尺寸类别 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `placeholder.style_inheritance` 位置、文字和样式继承 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `object.id` 稳定对象标识 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `object.name` 对象名称 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `object.kind` 对象类型 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `object.parent_ref` 分组父对象 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `object.z_order` 堆叠顺序 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `object.frame` 位置与尺寸 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `object.rotation` 二维旋转 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `object.flip_horizontal` 水平翻转 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `object.flip_vertical` 垂直翻转 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `object.transform` 仿射变换 | 原生属性 API（有条件） | Non-singular frame transforms without shear; shear is rejected. Translations are points. |
| `object.group_child_frame` 分组子坐标系 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `object.lock_aspect_ratio` 锁定比例 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `object.locks` 选择、移动、缩放、旋转、组合等锁定 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `object.hidden` 对象隐藏 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `object.black_white_mode` 黑白打印模式 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `object.style_ref` 主题样式引用 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `object.placeholder_ref` 占位符绑定 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `object.creation_id` Office 对象创建标识 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `shape.geometry.preset` 预设形状类型 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `shape.geometry.adjustments` 黄色调节柄参数 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `shape.geometry.guides` 几何公式与辅助变量 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `shape.geometry.paths` 多路径及轮廓 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `shape.geometry.commands` 移动、直线、二次和三次曲线、圆弧、闭合 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `shape.geometry.path_fill_rule` 路径填充规则 | 原生属性 API（有条件） | Native custom paths support nonzero; evenodd requires contour conversion and is rejected in strict authoring. |
| `shape.geometry.text_rect` 形状内文字矩形 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `shape.geometry.handles` XY/极坐标调节柄 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `shape.geometry.connection_sites` 连接点位置与方向 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `shape.geometry.path_stroke` 路径描边标记 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `shape.geometry.path_fill` 路径填充模式 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `connector.geometry` 直线、折线或曲线连接类型 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `connector.start_target` 起点对象与连接点 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `connector.end_target` 终点对象与连接点 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `connector.routing` 连接路径及自动路由 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `text.run.text` 文本内容 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `text.run.font.latin` 西文字体 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.font.east_asian` 东亚字体 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.font.complex_script` 复杂文字系统字体 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.font.symbol` 符号字体 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.font.size` 字号 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.font.bold` 粗体 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.font.italic` 斜体 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.font.face` 字体样式字面选择 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `text.run.font.charset` 字体字符集 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.font.pitch_family` 字距族与字体分类 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.fill` 文字填充含渐变、图案和主题色 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.outline` 文字轮廓描边 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.highlight` 高亮填充 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.underline.type` 下划线类型 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.underline.fill` 下划线颜色或填充 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.underline.stroke` 下划线线型 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.strike` 单线、双线删除线 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.capitalization` 全大写、小型大写或常规 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.letter_spacing` 字间距 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.kerning_threshold` 字偶距启用字号阈值 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.baseline_shift` 上标下标基线位移 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.normalize_height` 统一字符高度 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.kumimoji` 纵排组合字符 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.language` 语言 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.alternative_language` 备用语言 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.proofing` 校对、错误及脏标记 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.rtl` 片段从右至左 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.bookmark` 书签 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.click_link` 点击超链接 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.hover_link` 悬停超链接 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.effects` 文字效果集合 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.field.definition` 字段 ID、类型、缓存文字和格式 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `text.paragraph.content` 有序文字、软换行、字段与行内公式 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.alignment` 左、右、居中、两端或分散对齐 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.level` 段落层级 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.left_margin` 左缩进 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.right_margin` 右缩进 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.first_line_indent` 首行或悬挂缩进 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.line_spacing` 固定或比例行距 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.space_before` 段前间距 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.space_after` 段后间距 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.default_tab_size` 默认制表间距 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.tab_stops` 制表位位置和对齐 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.rtl` 段落从右至左 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.font_alignment` 字符基线对齐 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.east_asian_line_break` 东亚换行规则 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.latin_line_break` 西文换行规则 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.hanging_punctuation` 标点悬挂 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.default_run_style` 默认文字片段样式 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.end_run_style` 段落结尾样式 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.bullet.kind` 无、字符、编号或图片项目符号 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.bullet.character` 字符项目符号 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.bullet.numbering` 编号样式和起始值 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.bullet.font` 项目符号字体或跟随文字 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.bullet.color` 符号颜色或跟随文字 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.bullet.size` 符号大小或跟随文字 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.paragraph.bullet.image_ref` 图片项目符号 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.body.paragraphs` 段落集合 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.body.insets` 四边内边距 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.body.vertical_anchor` 垂直对齐 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.body.anchor_center` 居中锚定 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.body.wrap` 换行策略 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.body.autofit` 无、缩小文字或放大形状 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.body.autofit_scale` 文字缩放与行距缩减 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.body.rotation` 文字旋转 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.body.vertical_mode` 竖排及东亚竖排模式 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.body.columns` 分栏数量 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.body.column_spacing` 栏间距 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.body.columns_rtl` 分栏从右至左 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.body.wordart_warp` 艺术字预设变形与调节参数 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.body.upright` 保持文字直立 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.body.vertical_overflow` 纵向溢出行为 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.body.horizontal_overflow` 横向溢出行为 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.body.first_last_paragraph_spacing` 首尾段间距规则 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.body.compatible_line_spacing` 兼容行距规则 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.body.force_antialias` 强制抗锯齿 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.body.text_3d` 文字 3D 与平面文字 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `text.body.text_layout_cache` 导入布局和断行缓存 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `paint.kind` 无、纯色、渐变、图案、图片或组继承 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `color.kind` RGB、主题、系统、预设、scRGB 或 HSL | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `color.channels` 颜色通道 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `color.alpha` 透明度 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `color.transforms` 色调、明暗、亮度、饱和、补色、反相、灰度、Gamma 等有序变换 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.solid.color` 纯色填充 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.gradient.kind` 线性、圆形、矩形、沿形状路径 | 原生属性 API（有条件） | Native linear/circle/rect/shape gradients. SVG rect/shape uses a reported local PDF/PNG fallback for unrotated top-level objects when Poppler is available; other cases retain a declared approximation. |
| `paint.gradient.stops` 多色标位置、颜色与透明度 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.gradient.angle` 线性渐变角度 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.gradient.scaled` 线性渐变随形状比例缩放 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.gradient.path_kind` 圆形、矩形或形状路径 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.gradient.fill_to_rect` 渐变中心/填充矩形 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.gradient.tile_rect` 渐变平铺矩形 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.gradient.flip` 渐变翻转 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.gradient.rotate_with_shape` 渐变随形状旋转 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.pattern.preset` 图案填充类型 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.pattern.foreground` 图案前景色 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.pattern.background` 图案背景色 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.image.asset_ref` 图片填充资源 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.image.crop` 图片填充裁剪 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.image.mode` 拉伸或平铺 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.image.stretch_rect` 图片拉伸区域 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.image.tile_offset` 平铺偏移 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.image.tile_scale` 平铺缩放 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.image.tile_alignment` 平铺对齐 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.image.tile_flip` 平铺翻转 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.image.rotate_with_shape` 图片填充随形状旋转 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `paint.group_inheritance` 继承组填充 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `stroke.width` 线宽 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `stroke.paint` 线条填充 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `stroke.cap` 平端、圆端、方端 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `stroke.join` 斜接、圆角或斜角接合 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `stroke.miter_limit` 斜接限制 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `stroke.compound` 单线、双线、粗细组合 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `stroke.alignment` 居中或内侧线条对齐 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `stroke.dash_preset` 预设虚线 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `stroke.dash_custom` 自定义虚线长度间隔 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `stroke.start_arrow.kind` 起点箭头类型 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `stroke.start_arrow.width` 起点箭头宽度类别 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `stroke.start_arrow.length` 起点箭头长度类别 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `stroke.end_arrow.kind` 终点箭头类型 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `stroke.end_arrow.width` 终点箭头宽度类别 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `stroke.end_arrow.length` 终点箭头长度类别 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `effects.outer_shadow` 外阴影颜色、模糊、偏移、缩放、斜切、对齐 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `effects.inner_shadow` 内阴影 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `effects.preset_shadow` 预设阴影 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `effects.glow` 发光颜色与半径 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `effects.soft_edge` 柔化边缘半径 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `effects.reflection` 倒影透明度、距离、模糊和变换 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `effects.blur` 模糊与边缘增长 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `effects.fill_overlay` 填充叠加与混合 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `effects.alpha` Alpha 反转、阈值、替换、调制和组合 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `effects.color_change` 颜色替换 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `effects.duotone` 双色调 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `effects.tint` 着色与明暗 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `effects.grayscale` 灰度 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `effects.relative_offset` 相对偏移 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `effects.transform` 效果变换 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `effects.dag` 有序效果树、引用及混合模式 | 原生属性 API（有条件） | Exact a:effectDag XML tree. |
| `three_d.camera.preset` 预设相机 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `three_d.camera.field_of_view` 视野 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `three_d.camera.zoom` 相机缩放 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `three_d.camera.rotation` 纬度、经度、旋转 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `three_d.light_rig.preset` 灯光预设 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `three_d.light_rig.direction` 光照方向 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `three_d.light_rig.rotation` 灯光旋转 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `three_d.backdrop` 背景锚点、法向与上方向 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `three_d.bevel.top` 顶端棱台类型与尺寸 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `three_d.bevel.bottom` 底端棱台 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `three_d.extrusion_depth` 挤出深度 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `three_d.contour_width` 轮廓宽度 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `three_d.z_position` Z 轴位置 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `three_d.material` 材质预设 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `three_d.extrusion_color` 挤出颜色 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `three_d.contour_color` 轮廓颜色 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `model3d.asset_ref` 嵌入或链接 3D 模型 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `model3d.viewport` 3D 视口、缩放与相机 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `model3d.poster_ref` 3D 模型静态替代图 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `model3d.animation` 3D 模型动画 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `picture.asset_ref` 图片资源 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `picture.link_ref` 链接图片与更新关系 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `picture.crop` 裁剪与扩展 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `picture.geometry_mask` 图片形状裁剪 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `picture.aspect_fit` 适配、填满与保持比例 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `picture.brightness` 亮度 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `picture.contrast` 对比度 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `picture.recolor` 颜色重着色 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `picture.transparent_color` 透明颜色 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `picture.alpha` 图片透明度 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `picture.artistic_effect` 艺术效果及参数 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `picture.background_removal` 背景移除标记 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `picture.compression` 图像压缩与分辨率元数据 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `picture.svg_asset` SVG 原资源与替代图 | 原生属性 API（有条件） | Native SVG image relationship plus the picture.asset_ref bitmap fallback; older readers may display the fallback. |
| `picture.local_dpi` 使用本地 DPI 标志 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `picture.crop_locked` 裁剪锁定与比例约束 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `ink.strokes` 墨迹轨迹与绘制属性 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `ink.shape_binding` 墨迹形状和图层绑定 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `table.grid_columns` 列宽 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `table.rows.height` 行高 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `table.cells.content` 单元格富文本 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `table.cells.merge` 合并、跨行跨列及延续标志 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `table.cells.fill` 单元格填充 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `table.cells.borders` 上下左右和对角线边框 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `table.cells.insets` 单元格内边距 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `table.cells.vertical_anchor` 单元格垂直对齐 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `table.cells.text_direction` 单元格文字方向 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `table.cells.anchor_center` 单元格居中锚定 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `table.cells.overflow` 单元格溢出策略 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `table.style_ref` 表格样式及自定义样式 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `table.first_row` 首行样式开关 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `table.last_row` 末行样式开关 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `table.first_column` 首列样式开关 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `table.last_column` 末列样式开关 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `table.band_rows` 横向条带 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `table.band_columns` 纵向条带 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `table.rtl` 表格从右至左 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `table.cell_style_inheritance` 样式与直接格式优先级 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `chart.type` 图表类型含现代 chartEx | 原生属性 API（有条件） | Native creation: barChart, lineChart, areaChart, pieChart, doughnutChart, scatterChart, bubbleChart, radarChart. Other chart families require imported native parts. |
| `chart.plots` 组合图、分组与次坐标轴分配 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.categories` 类别、多级类别与日期 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.series` 系列名称、数据、类别和顺序 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.data_source` 内嵌工作簿或外链 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `chart.data_formulas` 公式、区域引用与数据来源 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `chart.cached_data` 类别与数据缓存 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `chart.external_data_update` 外部数据更新策略 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `chart.blank_values` 空白值显示方式 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.visible_data_only` 只绘制可见数据 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.style_ref` 图表样式、颜色和主题 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.title` 图表富文本标题与位置 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.legend` 图例位置、文本、条目与布局 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.axes` 主次类别/数值/日期/系列轴 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.axes.scale` 范围、对数、反向与刻度 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.axes.crossing` 交叉位置与标签位置 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.axes.number_format` 数值格式及来源链接 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.axes.gridlines` 主次网格线 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.axes.title` 坐标轴标题 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.axes.ticks` 主次刻度线与间隔 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.data_labels` 值、名称、百分比、分隔符、位置和逐点覆盖 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.data_labels.leader_lines` 引导线 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `chart.markers` 标记类型、大小和逐点样式 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.trendlines` 趋势线、方程与 R² | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.error_bars` 误差线类型、值和样式 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.series.style` 系列、逐点填充和描边 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.series.gap_overlap` 柱/条间距与重叠 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.series.smoothing` 线条平滑 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.series.explosion` 扇形分离 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.series.doughnut_hole` 圆环内径 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.data_table` 图表内数据表 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.manual_layout` 图表元素手动布局 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.plot_area` 绘图区填充、边框和布局 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.chart_area` 图表区填充、边框和布局 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `chart.three_d` 旋转、视角、深度、地板与墙面 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `chart.modern_options` 直方图、箱线图、瀑布、树图、旭日、地图等参数 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `smartart.data_model` 节点、连接、语义结构 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `smartart.node_text` 节点富文本 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `smartart.layout_ref` 布局定义和算法参数 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `smartart.colors_ref` 颜色定义 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `smartart.quick_style_ref` 快速样式 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `smartart.rendered_drawing` 缓存的绘图部件 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `smartart.node_ids` 节点标识与对象绑定 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `smartart.direction` 布局方向 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `smartart.node_adjustments` 节点手动位置和大小调整 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `math.content` Office Math 完整表达式树 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `math.source` LaTeX 等源表示及溯源 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `math.display_mode` 行内或独立公式 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `math.style` 数学字体、字号、颜色与字形 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `math.alignment` 公式对齐 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `math.spacing` 公式与普通文本的间距 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `math.compatibility_choice` 兼容分支与替代表示 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `media.kind` 音频、视频或旁白 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `media.asset_ref` 嵌入媒体 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `media.external_ref` 外部媒体与在线媒体信息 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `media.poster_ref` 封面帧 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `media.trim_start` 裁剪起点 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `media.trim_end` 裁剪终点 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `media.volume` 音量 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `media.mute` 静音 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `media.loop` 循环播放 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `media.play_across_slides` 跨页播放 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `media.hide_when_stopped` 停止时隐藏 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `media.rewind_after_play` 播放后回到起点 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `media.fade_in` 淡入时长 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `media.fade_out` 淡出时长 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `media.bookmarks` 书签时间点 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `media.play_trigger` 播放触发绑定 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `media.controls` 控制与全屏播放 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.timeline` 并行、串行与时间节点树 | 原生属性 API（有条件） | Accepts an exact p:timing XML tree or namespace-qualified tree data; timing graph authoring is explicit native data. |
| `animation.target_ref` 对象、文字范围或图表目标 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.behavior` 出现、强调、退出、动作路径及属性行为 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.preset` 预设类、ID 与子类型 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.trigger` 点击、同前、后前、媒体书签、事件条件 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.delay` 延迟 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.duration` 时长及自动/不定长模式 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.repeat` 次数或重复时间 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.autoreverse` 自动反转 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.speed` 播放速度 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.acceleration` 加速比例 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.deceleration` 减速比例 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.fill_mode` 结束保留和重启规则 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.keyframes` 时间、值与插值 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.motion_path` 运动路径及原点 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.transform` 位置、缩放和旋转动画 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.color` 颜色动画与颜色空间 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.effect` 滤镜、进出场与效果参数 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.command` 媒体或对象播放命令 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.text_build` 逐字、逐词、逐段或层级构建 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.chart_build` 图表系列与类别构建 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.diagram_build` SmartArt 构建 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.iteration` 迭代间隔和粒度 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `animation.runtime_state` 交互序列与时间节点绑定 | 宿主 / 容器流程 | Host application, policy or device required. |
| `transition.kind` 标准和 Office 扩展切换类型 | 原生属性 API（有条件） | Standard PML transitions; Office extensions such as Morph require native package preservation. |
| `transition.direction` 方向及子类型 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `transition.duration` 切换时长 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `transition.speed` 速度预设 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `transition.advance_on_click` 单击换页 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `transition.advance_after` 自动换页时间 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `transition.sound` 换页声音与循环 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `transition.morph` Morph 模式与对象匹配标识 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `zoom.kind` 页面、节或摘要缩放 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `zoom.target_refs` 导航目标 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `zoom.return_behavior` 缩放返回与背景显示 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `zoom.thumbnail_ref` 缩放缩略图资源 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `interaction.event` 点击或鼠标悬停 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `interaction.hyperlink` URL、页、文档或自定义放映目标 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `interaction.tooltip` 提示文字 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `interaction.highlight_click` 点击高亮与访问状态 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `interaction.navigation_action` 下一页、上一页、首尾页与返回 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `interaction.media_action` 媒体播放动作 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `interaction.object_action` OLE、程序或宏动作描述 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `interaction.sound` 动作声音 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `interaction.history` 导航历史设置 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `notes.content` 备注页富文本与对象 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `notes.master_ref` 备注母版 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `handout.master` 讲义母版与对象 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `slideshow.custom_shows` 自定义放映页面列表 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `slideshow.range` 放映范围 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `slideshow.kind` 演讲者、窗口或展台模式 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `slideshow.loop` 循环放映 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `slideshow.use_timings` 使用计时 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `slideshow.show_animation` 显示动画 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `slideshow.show_narration` 播放旁白 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `slideshow.pen_color` 演示笔颜色 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `print.options` 打印范围、颜色模式与讲义选项 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `comments.legacy` 传统批注、作者、位置和时间 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `comments.threads` 现代批注、回复和解决状态 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `comments.people` 人员与身份引用 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `comments.anchors` 批注对象和文字锚定 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `accessibility.title` 替代标题 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `accessibility.description` 替代描述 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `accessibility.decorative` 装饰性对象标志 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `accessibility.reading_order` 辅助阅读顺序 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `metadata.tags` 对象标签 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `metadata.customer_data` 自定义部件与业务数据 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `metadata.hidden_data_policy` 个人信息与隐藏内容处理策略 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `embedded.kind` OLE、工作簿、控件或其他嵌入包 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `embedded.asset_ref` 二进制或子包资源 | 原生属性 API（有条件） | OLE creation uses an explicit ProgID and optional preview; activation is controlled by the host. |
| `embedded.prog_id` 对象程序标识 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `embedded.link_ref` 链接对象来源 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `embedded.preview_ref` 对象预览图 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `embedded.display_mode` 图标或内容显示 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `embedded.activation` 激活动作描述 | 宿主 / 容器流程 | Host application, policy or device required. |
| `embedded.control_properties` 控件和持久化数据 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `embedded.web_extensions` Web 扩展、绑定和任务窗格部件 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `package.security.encryption` 加密容器与参数 | 宿主 / 容器流程 | Host application, policy or device required. |
| `package.security.permissions` IRM 与授权策略引用 | 宿主 / 容器流程 | Host application, policy or device required. |
| `package.security.write_protection` 写保护与只读建议 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `package.security.signature` 数字签名及修改后的有效性 | 宿主 / 容器流程 | Host application, policy or device required. |
| `package.security.sensitivity` 敏感度标签与策略 | 宿主 / 容器流程 | Host application, policy or device required. |
| `package.macro_profile` pptx/pptm 容器差异与宏部件 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `compatibility.unknown_xml` 未建模 XML 与 QName | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `compatibility.unknown_parts` 未建模资源部件和关系 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `compatibility.alternate_content` 兼容分支及所需命名空间 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `compatibility.extension_list` 扩展项及 URI | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `compatibility.relationship_map` 稳定语义 ID 与本地 rId 映射 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `compatibility.producer_metadata` 生成器和编辑器元数据 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `master.color_map` 母版颜色映射 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `master.preserve` 保留未使用母版 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `master.timeline` 母版时间树 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `master.transition` 母版切换 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `layout.color_map_override` 版式颜色映射覆盖 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `layout.header_footer` 版式页眉页脚 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `layout.show_master_shapes` 显示母版对象 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `layout.show_master_placeholder_animations` 显示母版占位符动画 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `layout.timeline` 版式时间树 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `layout.transition` 版式切换 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `shape.geometry.coordinate_space` 独立路径坐标空间 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `shape.geometry.path_viewport` 路径 w/h 视口 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `shape.geometry.path_formula_refs` 数值和公式坐标引用 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `shape.geometry.extrusion_ok` 路径允许挤出 | 原生属性 API（有条件） | Native OOXML binding; renderer behavior must be checked separately. |
| `text.run.autorotate_numbers` 数字随竖排旋转 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `text.run.equalize_spacing` 文字等距离分布 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `media.caption_tracks` 字幕轨道集合 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `media.caption_track.id` 字幕轨道标识 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `media.caption_track.language` 字幕语言 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `media.caption_track.label` 字幕轨道标签 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `media.caption_track.resource` 嵌入或链接字幕资源 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `live_feed.properties` Cameo 对象和 LiveFeed 属性 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `live_feed.placeholder` 实时摄像头占位符 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `live_feed.background_removal` 实时源背景处理 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `live_feed.poster_ref` 实时摄像头静态替代图 | 模板保留 / 显式 XML 绑定 | Imported native XML/relationships retained; a new typed authoring binding is required. |
| `live_feed.host_binding` 设备、权限和运行环境绑定 | 宿主 / 容器流程 | Host application, policy or device required. |
