# PPTX 属性与导出能力矩阵

这是统一文档模型的研究稿，列出设计目标。`native`、`layout` 等是导出目标，不代表已经实现。当前命令使用操作计划，完整统一文档模型和 SVG 导出器尚未实现；每项实现状态与验证状态单独记录。

- `native`：目标格式原生对象或属性。
- `office_extension`：Office 扩展，需声明应用版本。
- `resolved`：解析主题或继承后输出。
- `layout`：计算布局后生成对象位置。
- `visual`：保留静态外观，源语义在文档模型中保留。
- `approximate`：可能需要近似，严格模式需检查具体参数。
- `metadata`：只保留数据或描述，不表现动态行为。
- `poster_only`：仅静态预览，不能声明播放或激活等价。
- `opaque`：未建模部件原样保留，不表示已能原生编辑。
- `host`：依赖应用、授权或操作系统能力。

源字段的逐项清单见 [微软 Schema 属性 CSV](pptx-inventory/schema-properties.csv)；可维护语义字段见 [JSON](property-catalog.json) 和 [CSV](export-capabilities.csv)。8692 条 Schema 记录是包含继承与各上下文复用的字段出现次数，不是独立的用户设置数量。共享 DrawingML 需检查是否适用于具体 PPTX 上下文。


字段级继承、原生默认值、必填约束及原生映射尚待逐项确认，JSON/CSV 明确记录为 `not_assessed` 或 `unmapped`，不统一假定所有字段可继承。



## 文档、包与全局设置

来源范围：`PML+VBA-Presentation`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `document.id` | 文档标识 | `id` / — | native | metadata |
| `document.metadata.title` | 标题 | `text` / — | native | metadata |
| `document.metadata.subject` | 主题 | `text` / — | native | metadata |
| `document.metadata.author` | 作者 | `text` / — | native | metadata |
| `document.metadata.keywords` | 关键词 | `text[]` / — | native | metadata |
| `document.metadata.description` | 说明 | `text` / — | native | metadata |
| `document.metadata.created` | 创建时间 | `datetime` / UTC | native | metadata |
| `document.metadata.modified` | 修改时间 | `datetime` / UTC | native | metadata |
| `document.metadata.revision` | 修订号 | `text` / — | native | metadata |
| `document.metadata.custom_properties` | 自定义属性 | `typed_map` / — | native | metadata |
| `document.page_size` | 页面尺寸 | `size` / pt | native | metadata |
| `document.orientation` | 页面方向 | `enum` / — | native | metadata |
| `document.default_language` | 默认语言 | `language_tag` / — | native | metadata |
| `document.layout_direction` | 布局方向 | `enum` / — | native | metadata |
| `document.fonts.embedded` | 嵌入字体资源与字形子集 | `font_assets[]` / — | native | metadata |
| `document.fonts.fallback` | 字体替代与解析策略 | `font_rules[]` / — | native | metadata |
| `document.assets` | 媒体资源与关系 | `asset_map` / — | native | metadata |
| `document.custom_xml` | 自定义 XML 部件 | `xml_parts[]` / — | native | metadata |
| `document.color_map` | 全局颜色映射 | `theme_map` / — | native | metadata |
| `document.guides` | 参考线 | `guide[]` / pt | native | metadata |
| `document.grid_spacing` | 网格间距 | `size` / pt (x,y) | native | metadata |
| `document.sections` | 节与页面顺序 | `sections[]` / — | native | metadata |
| `document.compatibility_profile` | 目标 Office 版本与能力 | `profile` / — | native | metadata |

## 页面、显示与背景

来源范围：`PML+VBA-Slide`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `slide.id` | 稳定页面标识 | `id` / — | native | resolved |
| `slide.name` | 页面名称 | `text` / — | native | resolved |
| `slide.order` | 页面顺序 | `integer` / — | native | resolved |
| `slide.hidden` | 隐藏页面 | `boolean` / — | native | resolved |
| `slide.layout_ref` | 绑定版式 | `ref` / — | native | resolved |
| `slide.master_ref` | 绑定母版 | `ref` / — | native | resolved |
| `slide.theme_override` | 页面主题覆盖 | `theme` / — | native | resolved |
| `slide.background` | 背景填充 | `paint` / — | native | resolved |
| `slide.background_follow_master` | 继承母版背景 | `boolean` / — | native | resolved |
| `slide.show_master_shapes` | 显示母版对象 | `boolean` / — | native | resolved |
| `slide.header_footer` | 日期、页码、页脚内容和显示 | `header_footer` / — | native | resolved |
| `slide.comments_ref` | 批注关系 | `ref[]` / — | native | resolved |
| `slide.tags` | 标签与自定义数据 | `map` / — | native | resolved |
| `slide.creation_id` | Office 创建标识 | `guid` / — | native | resolved |
| `slide.color_map_override` | 颜色映射覆盖 | `theme_map` / — | native | resolved |
| `slide.objects` | 绘图对象和层级 | `object[]` / — | native | resolved |

## 主题、母版、版式与占位符

来源范围：`DML-theme+PML-master/layout`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `theme.colors` | 主题色槽与系统色 | `color_scheme` / — | native | resolved |
| `theme.fonts.major` | 标题字体与各文字系统字体 | `font_collection` / — | native | resolved |
| `theme.fonts.minor` | 正文字体与各文字系统字体 | `font_collection` / — | native | resolved |
| `theme.format_scheme` | 填充、描边和效果样式集合 | `format_scheme` / — | native | resolved |
| `theme.extra_color_schemes` | 额外配色方案 | `color_scheme[]` / — | native | resolved |
| `theme.defaults` | 对象、线条和文字默认样式 | `style_defaults` / — | native | resolved |
| `master.id` | 母版标识 | `id` / — | native | resolved |
| `master.background` | 母版背景 | `paint` / — | native | resolved |
| `master.objects` | 母版固定对象 | `object[]` / — | native | resolved |
| `master.text_styles` | 标题、正文、其他文本分级样式 | `text_styles` / — | native | resolved |
| `master.layout_refs` | 母版版式列表 | `ref[]` / — | native | resolved |
| `master.header_footer` | 母版页眉页脚 | `header_footer` / — | native | resolved |
| `layout.id` | 版式标识 | `id` / — | native | resolved |
| `layout.type` | 版式类型 | `enum` / — | native | resolved |
| `layout.master_ref` | 父母版 | `ref` / — | native | resolved |
| `layout.objects` | 版式对象 | `object[]` / — | native | resolved |
| `layout.preserve` | 保留未使用版式 | `boolean` / — | native | resolved |
| `layout.matching_name` | 版式匹配名称 | `text` / — | native | resolved |
| `placeholder.type` | 占位符类型 | `enum` / — | native | resolved |
| `placeholder.index` | 继承匹配索引 | `integer` / — | native | resolved |
| `placeholder.orientation` | 占位符方向 | `enum` / — | native | resolved |
| `placeholder.size_hint` | 占位符尺寸类别 | `enum` / — | native | resolved |
| `placeholder.style_inheritance` | 位置、文字和样式继承 | `style_ref` / — | native | resolved |
| `master.color_map` | 母版颜色映射 | `theme_map` / — | native | resolved |
| `master.preserve` | 保留未使用母版 | `boolean` / — | native | resolved |
| `master.timeline` | 母版时间树 | `time_graph` / — | native | resolved |
| `master.transition` | 母版切换 | `transition` / — | native | resolved |
| `layout.color_map_override` | 版式颜色映射覆盖 | `theme_map` / — | native | resolved |
| `layout.header_footer` | 版式页眉页脚 | `header_footer` / — | native | resolved |
| `layout.show_master_shapes` | 显示母版对象 | `boolean` / — | native | resolved |
| `layout.show_master_placeholder_animations` | 显示母版占位符动画 | `boolean` / — | native | resolved |
| `layout.timeline` | 版式时间树 | `time_graph` / — | native | resolved |
| `layout.transition` | 版式切换 | `transition` / — | native | resolved |

## 对象身份、层级、几何与锁定

来源范围：`DML-transform+PML-shape`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `object.id` | 稳定对象标识 | `id` / — | native | native |
| `object.name` | 对象名称 | `text` / — | native | native |
| `object.kind` | 对象类型 | `enum` / — | native | native |
| `object.parent_ref` | 分组父对象 | `ref` / — | native | native |
| `object.z_order` | 堆叠顺序 | `integer` / — | native | native |
| `object.frame` | 位置与尺寸 | `rect` / pt | native | native |
| `object.rotation` | 二维旋转 | `angle` / deg | native | native |
| `object.flip_horizontal` | 水平翻转 | `boolean` / — | native | native |
| `object.flip_vertical` | 垂直翻转 | `boolean` / — | native | native |
| `object.transform` | 仿射变换 | `matrix` / — | decompose_or_bake; shear requires explicit strategy | native |
| `object.group_child_frame` | 分组子坐标系 | `rect` / pt | native | native |
| `object.lock_aspect_ratio` | 锁定比例 | `boolean` / — | native | metadata/host |
| `object.locks` | 选择、移动、缩放、旋转、组合等锁定 | `lock_map` / — | native | metadata/host |
| `object.hidden` | 对象隐藏 | `boolean` / — | native | native |
| `object.black_white_mode` | 黑白打印模式 | `enum` / — | native | native |
| `object.style_ref` | 主题样式引用 | `style_ref` / — | native | native |
| `object.placeholder_ref` | 占位符绑定 | `ref` / — | native | native |
| `object.creation_id` | Office 对象创建标识 | `guid` / — | native | native |

## 预设几何、自由曲线与连接线

来源范围：`DML-geometry+VBA-Shape/ConnectorFormat`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `shape.geometry.preset` | 预设形状类型 | `enum` / — | native | native |
| `shape.geometry.adjustments` | 黄色调节柄参数 | `named_formula[]` / — | native | layout/metadata |
| `shape.geometry.guides` | 几何公式与辅助变量 | `named_formula[]` / — | native | layout/metadata |
| `shape.geometry.paths` | 多路径及轮廓 | `path[]` / path-local | native | native |
| `shape.geometry.commands` | 移动、直线、二次和三次曲线、圆弧、闭合 | `path_command[]` / path-local/deg | native | native |
| `shape.geometry.path_fill_rule` | 路径填充规则 | `enum` / — | mapping_required; distinct from path fill mode | native |
| `shape.geometry.text_rect` | 形状内文字矩形 | `formula_rect` / geometry-local/formula | native | native |
| `shape.geometry.handles` | XY/极坐标调节柄 | `handle[]` / — | native | layout/metadata |
| `shape.geometry.connection_sites` | 连接点位置与方向 | `connection_site[]` / pt/deg | native | layout/metadata |
| `shape.geometry.path_stroke` | 路径描边标记 | `boolean` / — | native | native |
| `shape.geometry.path_fill` | 路径填充模式 | `enum` / — | native | native |
| `connector.geometry` | 直线、折线或曲线连接类型 | `enum` / — | native | native |
| `connector.start_target` | 起点对象与连接点 | `connection_ref` / — | native | visual/metadata |
| `connector.end_target` | 终点对象与连接点 | `connection_ref` / — | native | visual/metadata |
| `connector.routing` | 连接路径及自动路由 | `routing` / — | native | visual/metadata |
| `shape.geometry.coordinate_space` | 独立路径坐标空间 | `coordinate_space` / local | native | native |
| `shape.geometry.path_viewport` | 路径 w/h 视口 | `size` / local | native | native |
| `shape.geometry.path_formula_refs` | 数值和公式坐标引用 | `formula_ref[]` / local | native | layout/metadata |
| `shape.geometry.extrusion_ok` | 路径允许挤出 | `boolean` / — | native | native |

## 文字片段与字体

来源范围：`DML-TextCharacterPropertiesType+VBA-Font2`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `text.run.text` | 文本内容 | `text` / — | native | native/layout |
| `text.run.font.latin` | 西文字体 | `font_ref` / — | native | native/layout |
| `text.run.font.east_asian` | 东亚字体 | `font_ref` / — | native | native/layout |
| `text.run.font.complex_script` | 复杂文字系统字体 | `font_ref` / — | native | native/layout |
| `text.run.font.symbol` | 符号字体 | `font_ref` / — | native | native/layout |
| `text.run.font.size` | 字号 | `length` / pt | native | native/layout |
| `text.run.font.bold` | 粗体 | `boolean` / — | native | native/layout |
| `text.run.font.italic` | 斜体 | `boolean` / — | native | native/layout |
| `text.run.font.face` | 字体样式字面选择 | `font_face` / — | font_face_mapping | native/layout |
| `text.run.font.charset` | 字体字符集 | `integer` / — | native | native/layout |
| `text.run.font.pitch_family` | 字距族与字体分类 | `integer` / — | native | native/layout |
| `text.run.fill` | 文字填充含渐变、图案和主题色 | `paint` / — | native | native/layout |
| `text.run.outline` | 文字轮廓描边 | `stroke` / pt | native | native/layout |
| `text.run.highlight` | 高亮填充 | `color` / — | native | native/layout |
| `text.run.underline.type` | 下划线类型 | `enum` / — | native | native/layout |
| `text.run.underline.fill` | 下划线颜色或填充 | `paint` / — | native | native/layout |
| `text.run.underline.stroke` | 下划线线型 | `stroke` / pt | native | native/layout |
| `text.run.strike` | 单线、双线删除线 | `enum` / — | native | native/layout |
| `text.run.capitalization` | 全大写、小型大写或常规 | `enum` / — | native | native/layout |
| `text.run.letter_spacing` | 字间距 | `length` / pt | native | native/layout |
| `text.run.kerning_threshold` | 字偶距启用字号阈值 | `length` / pt | native | native/layout |
| `text.run.baseline_shift` | 上标下标基线位移 | `ratio` / font-relative | native | native/layout |
| `text.run.normalize_height` | 统一字符高度 | `boolean` / — | native | native/layout |
| `text.run.kumimoji` | 纵排组合字符 | `boolean` / — | native | native/layout |
| `text.run.language` | 语言 | `language_tag` / — | native | native/layout |
| `text.run.alternative_language` | 备用语言 | `language_tag` / — | native | native/layout |
| `text.run.proofing` | 校对、错误及脏标记 | `proofing` / — | native | native/layout |
| `text.run.rtl` | 片段从右至左 | `boolean` / — | native | native/layout |
| `text.run.bookmark` | 书签 | `text` / — | native | native/layout |
| `text.run.click_link` | 点击超链接 | `hyperlink` / — | native | native/layout |
| `text.run.hover_link` | 悬停超链接 | `hyperlink` / — | native | native/layout |
| `text.run.effects` | 文字效果集合 | `effect[]` / — | native | native/layout |
| `text.field.definition` | 字段 ID、类型、缓存文字和格式 | `field` / — | native | native/layout |
| `text.run.autorotate_numbers` | 数字随竖排旋转 | `boolean` / — | mapping_required | layout |
| `text.run.equalize_spacing` | 文字等距离分布 | `boolean` / — | mapping_required | layout |

## 段落、列表、缩进与制表位

来源范围：`DML-TextParagraphPropertiesType+VBA-ParagraphFormat2`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `text.paragraph.content` | 有序文字、软换行、字段与行内公式 | `(Run\|Break\|Field\|Math)[]` / — | native | layout |
| `text.paragraph.alignment` | 左、右、居中、两端或分散对齐 | `enum` / — | native | layout |
| `text.paragraph.level` | 段落层级 | `integer` / — | native | layout |
| `text.paragraph.left_margin` | 左缩进 | `length` / pt | native | layout |
| `text.paragraph.right_margin` | 右缩进 | `length` / pt | native | layout |
| `text.paragraph.first_line_indent` | 首行或悬挂缩进 | `signed_length` / pt | native | layout |
| `text.paragraph.line_spacing` | 固定或比例行距 | `spacing` / pt/ratio | native | layout |
| `text.paragraph.space_before` | 段前间距 | `spacing` / pt/ratio | native | layout |
| `text.paragraph.space_after` | 段后间距 | `spacing` / pt/ratio | native | layout |
| `text.paragraph.default_tab_size` | 默认制表间距 | `length` / pt | native | layout |
| `text.paragraph.tab_stops` | 制表位位置和对齐 | `tab_stop[]` / pt | native | layout |
| `text.paragraph.rtl` | 段落从右至左 | `boolean` / — | native | layout |
| `text.paragraph.font_alignment` | 字符基线对齐 | `enum` / — | native | layout |
| `text.paragraph.east_asian_line_break` | 东亚换行规则 | `boolean` / — | native | layout |
| `text.paragraph.latin_line_break` | 西文换行规则 | `boolean` / — | native | layout |
| `text.paragraph.hanging_punctuation` | 标点悬挂 | `boolean` / — | native | layout |
| `text.paragraph.default_run_style` | 默认文字片段样式 | `run_style` / — | native | layout |
| `text.paragraph.end_run_style` | 段落结尾样式 | `run_style` / — | native | layout |
| `text.paragraph.bullet.kind` | 无、字符、编号或图片项目符号 | `enum` / — | native | layout |
| `text.paragraph.bullet.character` | 字符项目符号 | `text` / — | native | layout |
| `text.paragraph.bullet.numbering` | 编号样式和起始值 | `numbering` / — | native | layout |
| `text.paragraph.bullet.font` | 项目符号字体或跟随文字 | `font_ref` / — | native | layout |
| `text.paragraph.bullet.color` | 符号颜色或跟随文字 | `color` / — | native | layout |
| `text.paragraph.bullet.size` | 符号大小或跟随文字 | `size_mode` / pt/ratio | native | layout |
| `text.paragraph.bullet.image_ref` | 图片项目符号 | `asset_ref` / — | native | layout |

## 文本框、自动适应、竖排与艺术字

来源范围：`DML-BodyProperties+VBA-TextFrame2`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `text.body.paragraphs` | 段落集合 | `paragraph[]` / — | native | layout/approximate |
| `text.body.insets` | 四边内边距 | `insets` / pt | native | layout/approximate |
| `text.body.vertical_anchor` | 垂直对齐 | `enum` / — | native | layout/approximate |
| `text.body.anchor_center` | 居中锚定 | `boolean` / — | native | layout/approximate |
| `text.body.wrap` | 换行策略 | `enum` / — | native | layout/approximate |
| `text.body.autofit` | 无、缩小文字或放大形状 | `autofit` / — | native | layout/approximate |
| `text.body.autofit_scale` | 文字缩放与行距缩减 | `autofit_scale` / ratio | native | layout/approximate |
| `text.body.rotation` | 文字旋转 | `angle` / deg | native | layout/approximate |
| `text.body.vertical_mode` | 竖排及东亚竖排模式 | `enum` / — | native | layout/approximate |
| `text.body.columns` | 分栏数量 | `integer` / — | native | layout/approximate |
| `text.body.column_spacing` | 栏间距 | `length` / pt | native | layout/approximate |
| `text.body.columns_rtl` | 分栏从右至左 | `boolean` / — | native | layout/approximate |
| `text.body.wordart_warp` | 艺术字预设变形与调节参数 | `warp` / — | native | layout/approximate |
| `text.body.upright` | 保持文字直立 | `boolean` / — | native | layout/approximate |
| `text.body.vertical_overflow` | 纵向溢出行为 | `enum` / — | native | layout/approximate |
| `text.body.horizontal_overflow` | 横向溢出行为 | `enum` / — | native | layout/approximate |
| `text.body.first_last_paragraph_spacing` | 首尾段间距规则 | `boolean` / — | native | layout/approximate |
| `text.body.compatible_line_spacing` | 兼容行距规则 | `boolean` / — | native | layout/approximate |
| `text.body.force_antialias` | 强制抗锯齿 | `boolean` / — | native | layout/approximate |
| `text.body.text_3d` | 文字 3D 与平面文字 | `text3d` / — | native | layout/approximate |
| `text.body.text_layout_cache` | 导入布局和断行缓存 | `layout_cache` / pt | native | layout/approximate |

## 颜色、所有填充与渐变参数

来源范围：`DML-color/fill+VBA-FillFormat`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `paint.kind` | 无、纯色、渐变、图案、图片或组继承 | `enum` / — | native | native/approximate |
| `color.kind` | RGB、主题、系统、预设、scRGB 或 HSL | `enum` / — | native | native/approximate |
| `color.channels` | 颜色通道 | `color_components` / — | native | native/approximate |
| `color.alpha` | 透明度 | `ratio` / 0..1 | native | native/approximate |
| `color.transforms` | 色调、明暗、亮度、饱和、补色、反相、灰度、Gamma 等有序变换 | `color_transform[]` / typed | native | native/approximate |
| `paint.solid.color` | 纯色填充 | `color` / — | native | native/approximate |
| `paint.gradient.kind` | 线性、圆形、矩形、沿形状路径 | `enum` / — | native | native/approximate |
| `paint.gradient.stops` | 多色标位置、颜色与透明度 | `gradient_stop[]` / ratio | native | native/approximate |
| `paint.gradient.angle` | 线性渐变角度 | `angle` / deg | native | native/approximate |
| `paint.gradient.scaled` | 线性渐变随形状比例缩放 | `boolean` / — | native | native/approximate |
| `paint.gradient.path_kind` | 圆形、矩形或形状路径 | `enum` / — | native | approximate_or_unsupported |
| `paint.gradient.fill_to_rect` | 渐变中心/填充矩形 | `signed_insets` / ratio | native | approximate_or_unsupported |
| `paint.gradient.tile_rect` | 渐变平铺矩形 | `signed_insets` / ratio | native | approximate_or_unsupported |
| `paint.gradient.flip` | 渐变翻转 | `enum` / — | native | native/approximate |
| `paint.gradient.rotate_with_shape` | 渐变随形状旋转 | `boolean` / — | native | native/approximate |
| `paint.pattern.preset` | 图案填充类型 | `enum` / — | native | native/approximate |
| `paint.pattern.foreground` | 图案前景色 | `color` / — | native | native/approximate |
| `paint.pattern.background` | 图案背景色 | `color` / — | native | native/approximate |
| `paint.image.asset_ref` | 图片填充资源 | `asset_ref` / — | native | native/approximate |
| `paint.image.crop` | 图片填充裁剪 | `signed_insets` / ratio | native | native/approximate |
| `paint.image.mode` | 拉伸或平铺 | `enum` / — | native | native/approximate |
| `paint.image.stretch_rect` | 图片拉伸区域 | `signed_insets` / ratio | native | native/approximate |
| `paint.image.tile_offset` | 平铺偏移 | `point` / pt | native | native/approximate |
| `paint.image.tile_scale` | 平铺缩放 | `point` / ratio | native | native/approximate |
| `paint.image.tile_alignment` | 平铺对齐 | `enum` / — | native | native/approximate |
| `paint.image.tile_flip` | 平铺翻转 | `enum` / — | native | native/approximate |
| `paint.image.rotate_with_shape` | 图片填充随形状旋转 | `boolean` / — | native | native/approximate |
| `paint.group_inheritance` | 继承组填充 | `style_ref` / — | native | native/approximate |

## 描边、箭头和线型

来源范围：`DML-LineProperties+VBA-LineFormat`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `stroke.width` | 线宽 | `length` / pt | native | native/layout |
| `stroke.paint` | 线条填充 | `paint` / — | native | native/layout |
| `stroke.cap` | 平端、圆端、方端 | `enum` / — | native | native/layout |
| `stroke.join` | 斜接、圆角或斜角接合 | `enum` / — | native | native/layout |
| `stroke.miter_limit` | 斜接限制 | `ratio` / — | native | native/layout |
| `stroke.compound` | 单线、双线、粗细组合 | `enum` / — | native | layout/approximate |
| `stroke.alignment` | 居中或内侧线条对齐 | `enum` / — | native | layout/approximate |
| `stroke.dash_preset` | 预设虚线 | `enum` / — | native | native/layout |
| `stroke.dash_custom` | 自定义虚线长度间隔 | `dash[]` / stroke-relative | native | native/layout |
| `stroke.start_arrow.kind` | 起点箭头类型 | `enum` / — | native | native/layout |
| `stroke.start_arrow.width` | 起点箭头宽度类别 | `enum` / — | native | native/layout |
| `stroke.start_arrow.length` | 起点箭头长度类别 | `enum` / — | native | native/layout |
| `stroke.end_arrow.kind` | 终点箭头类型 | `enum` / — | native | native/layout |
| `stroke.end_arrow.width` | 终点箭头宽度类别 | `enum` / — | native | native/layout |
| `stroke.end_arrow.length` | 终点箭头长度类别 | `enum` / — | native | native/layout |

## 二维效果与复合效果树

来源范围：`DML-effects+VBA-Shadow/Glow/Reflection`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `effects.outer_shadow` | 外阴影颜色、模糊、偏移、缩放、斜切、对齐 | `shadow` / pt/deg/ratio | native | approximate |
| `effects.inner_shadow` | 内阴影 | `shadow` / pt/deg | native | approximate |
| `effects.preset_shadow` | 预设阴影 | `preset_shadow` / — | native | approximate |
| `effects.glow` | 发光颜色与半径 | `glow` / pt | native | approximate |
| `effects.soft_edge` | 柔化边缘半径 | `length` / pt | native | approximate |
| `effects.reflection` | 倒影透明度、距离、模糊和变换 | `reflection` / pt/deg/ratio | native | approximate |
| `effects.blur` | 模糊与边缘增长 | `blur` / pt | native | approximate |
| `effects.fill_overlay` | 填充叠加与混合 | `overlay` / — | native | approximate |
| `effects.alpha` | Alpha 反转、阈值、替换、调制和组合 | `alpha_effect[]` / ratio | native | approximate |
| `effects.color_change` | 颜色替换 | `color_change` / — | native | approximate |
| `effects.duotone` | 双色调 | `color[]` / — | native | approximate |
| `effects.tint` | 着色与明暗 | `tint` / ratio | native | approximate |
| `effects.grayscale` | 灰度 | `boolean` / — | native | approximate |
| `effects.relative_offset` | 相对偏移 | `point` / ratio | native | approximate |
| `effects.transform` | 效果变换 | `matrix` / — | native | approximate |
| `effects.dag` | 有序效果树、引用及混合模式 | `effect_graph` / — | native | approximate |

## 形状与文字 3D、相机、照明与模型

来源范围：`DML-scene3d/sp3d+Office-model3d`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `three_d.camera.preset` | 预设相机 | `enum` / — | native/office_extension | visual |
| `three_d.camera.field_of_view` | 视野 | `angle` / deg | native/office_extension | visual |
| `three_d.camera.zoom` | 相机缩放 | `ratio` / — | native/office_extension | visual |
| `three_d.camera.rotation` | 纬度、经度、旋转 | `rotation3d` / deg | native/office_extension | visual |
| `three_d.light_rig.preset` | 灯光预设 | `enum` / — | native/office_extension | visual |
| `three_d.light_rig.direction` | 光照方向 | `enum` / — | native/office_extension | visual |
| `three_d.light_rig.rotation` | 灯光旋转 | `rotation3d` / deg | native/office_extension | visual |
| `three_d.backdrop` | 背景锚点、法向与上方向 | `backdrop3d` / typed | native/office_extension | visual |
| `three_d.bevel.top` | 顶端棱台类型与尺寸 | `bevel` / pt | native/office_extension | visual |
| `three_d.bevel.bottom` | 底端棱台 | `bevel` / pt | native/office_extension | visual |
| `three_d.extrusion_depth` | 挤出深度 | `length` / pt | native/office_extension | visual |
| `three_d.contour_width` | 轮廓宽度 | `length` / pt | native/office_extension | visual |
| `three_d.z_position` | Z 轴位置 | `signed_length` / pt | native/office_extension | visual |
| `three_d.material` | 材质预设 | `enum` / — | native/office_extension | visual |
| `three_d.extrusion_color` | 挤出颜色 | `color` / — | native/office_extension | visual |
| `three_d.contour_color` | 轮廓颜色 | `color` / — | native/office_extension | visual |
| `model3d.asset_ref` | 嵌入或链接 3D 模型 | `asset_ref` / — | native/office_extension | visual |
| `model3d.viewport` | 3D 视口、缩放与相机 | `viewport3d` / typed | native/office_extension | visual |
| `model3d.poster_ref` | 3D 模型静态替代图 | `asset_ref` / — | native/office_extension | visual |
| `model3d.animation` | 3D 模型动画 | `animation3d` / — | native/office_extension | visual |

## 图片、SVG、墨迹与调整

来源范围：`DML-blip+Office-SVG/ink+VBA-PictureFormat`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `picture.asset_ref` | 图片资源 | `asset_ref` / — | native/office_extension | native/visual |
| `picture.link_ref` | 链接图片与更新关系 | `external_ref` / — | native/office_extension | native/visual |
| `picture.crop` | 裁剪与扩展 | `signed_insets` / ratio | native/office_extension | native/visual |
| `picture.geometry_mask` | 图片形状裁剪 | `geometry` / — | native/office_extension | native/visual |
| `picture.aspect_fit` | 适配、填满与保持比例 | `enum` / — | native/office_extension | native/visual |
| `picture.brightness` | 亮度 | `signed_ratio` / — | native/office_extension | native/visual |
| `picture.contrast` | 对比度 | `signed_ratio` / — | native/office_extension | native/visual |
| `picture.recolor` | 颜色重着色 | `color_effect[]` / — | native/office_extension | native/visual |
| `picture.transparent_color` | 透明颜色 | `color` / — | native/office_extension | native/visual |
| `picture.alpha` | 图片透明度 | `ratio` / 0..1 | native/office_extension | native/visual |
| `picture.artistic_effect` | 艺术效果及参数 | `picture_effect` / — | native/office_extension | native/visual |
| `picture.background_removal` | 背景移除标记 | `extension` / — | native/office_extension | native/visual |
| `picture.compression` | 图像压缩与分辨率元数据 | `compression` / — | native/office_extension | native/visual |
| `picture.svg_asset` | SVG 原资源与替代图 | `vector_asset` / — | native/office_extension | native/visual |
| `picture.local_dpi` | 使用本地 DPI 标志 | `boolean` / — | native/office_extension | native/visual |
| `picture.crop_locked` | 裁剪锁定与比例约束 | `lock_map` / — | native/office_extension | native/visual |
| `ink.strokes` | 墨迹轨迹与绘制属性 | `ink_data` / — | native/office_extension | native/visual |
| `ink.shape_binding` | 墨迹形状和图层绑定 | `ref[]` / — | native/office_extension | native/visual |

## 原生表格、单元格与样式

来源范围：`DML-table+VBA-Table`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `table.grid_columns` | 列宽 | `length[]` / pt | native | visual |
| `table.rows.height` | 行高 | `length[]` / pt | native | visual |
| `table.cells.content` | 单元格富文本 | `text_body[][]` / — | native | visual |
| `table.cells.merge` | 合并、跨行跨列及延续标志 | `merge_map` / — | native | visual |
| `table.cells.fill` | 单元格填充 | `paint` / — | native | visual |
| `table.cells.borders` | 上下左右和对角线边框 | `stroke_map` / pt | native | visual |
| `table.cells.insets` | 单元格内边距 | `insets` / pt | native | visual |
| `table.cells.vertical_anchor` | 单元格垂直对齐 | `enum` / — | native | visual |
| `table.cells.text_direction` | 单元格文字方向 | `enum` / — | native | visual |
| `table.cells.anchor_center` | 单元格居中锚定 | `boolean` / — | native | visual |
| `table.cells.overflow` | 单元格溢出策略 | `enum` / — | native | visual |
| `table.style_ref` | 表格样式及自定义样式 | `style_ref` / — | native | visual |
| `table.first_row` | 首行样式开关 | `boolean` / — | native | visual |
| `table.last_row` | 末行样式开关 | `boolean` / — | native | visual |
| `table.first_column` | 首列样式开关 | `boolean` / — | native | visual |
| `table.last_column` | 末列样式开关 | `boolean` / — | native | visual |
| `table.band_rows` | 横向条带 | `boolean` / — | native | visual |
| `table.band_columns` | 纵向条带 | `boolean` / — | native | visual |
| `table.rtl` | 表格从右至左 | `boolean` / — | native | visual |
| `table.cell_style_inheritance` | 样式与直接格式优先级 | `style_rules` / — | native | visual |

## 完整图表对象、数据与工作簿

来源范围：`DML-chart/chartex+VBA-Chart`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `chart.type` | 图表类型含现代 chartEx | `enum` / — | native/office_extension | visual |
| `chart.plots` | 组合图、分组与次坐标轴分配 | `plot[]` / — | native/office_extension | visual |
| `chart.categories` | 类别、多级类别与日期 | `category_data` / — | native/office_extension | visual |
| `chart.series` | 系列名称、数据、类别和顺序 | `series[]` / — | native/office_extension | visual |
| `chart.data_source` | 内嵌工作簿或外链 | `workbook_ref` / — | native/office_extension | visual |
| `chart.data_formulas` | 公式、区域引用与数据来源 | `formula_refs` / — | native/office_extension | visual |
| `chart.cached_data` | 类别与数据缓存 | `chart_cache` / — | native/office_extension | visual |
| `chart.external_data_update` | 外部数据更新策略 | `update_policy` / — | native/office_extension | visual |
| `chart.blank_values` | 空白值显示方式 | `enum` / — | native/office_extension | visual |
| `chart.visible_data_only` | 只绘制可见数据 | `boolean` / — | native/office_extension | visual |
| `chart.style_ref` | 图表样式、颜色和主题 | `chart_style` / — | native/office_extension | visual |
| `chart.title` | 图表富文本标题与位置 | `chart_label` / — | native/office_extension | visual |
| `chart.legend` | 图例位置、文本、条目与布局 | `legend` / — | native/office_extension | visual |
| `chart.axes` | 主次类别/数值/日期/系列轴 | `axis[]` / — | native/office_extension | visual |
| `chart.axes.scale` | 范围、对数、反向与刻度 | `axis_scale` / typed | native/office_extension | visual |
| `chart.axes.crossing` | 交叉位置与标签位置 | `axis_crossing` / typed | native/office_extension | visual |
| `chart.axes.number_format` | 数值格式及来源链接 | `number_format` / — | native/office_extension | visual |
| `chart.axes.gridlines` | 主次网格线 | `gridlines` / — | native/office_extension | visual |
| `chart.axes.title` | 坐标轴标题 | `chart_label` / — | native/office_extension | visual |
| `chart.axes.ticks` | 主次刻度线与间隔 | `axis_ticks` / — | native/office_extension | visual |
| `chart.data_labels` | 值、名称、百分比、分隔符、位置和逐点覆盖 | `data_label[]` / — | native/office_extension | visual |
| `chart.data_labels.leader_lines` | 引导线 | `stroke` / pt | native/office_extension | visual |
| `chart.markers` | 标记类型、大小和逐点样式 | `marker[]` / pt | native/office_extension | visual |
| `chart.trendlines` | 趋势线、方程与 R² | `trendline[]` / — | native/office_extension | visual |
| `chart.error_bars` | 误差线类型、值和样式 | `error_bar[]` / — | native/office_extension | visual |
| `chart.series.style` | 系列、逐点填充和描边 | `series_style[]` / — | native/office_extension | visual |
| `chart.series.gap_overlap` | 柱/条间距与重叠 | `series_spacing` / ratio | native/office_extension | visual |
| `chart.series.smoothing` | 线条平滑 | `boolean` / — | native/office_extension | visual |
| `chart.series.explosion` | 扇形分离 | `ratio` / — | native/office_extension | visual |
| `chart.series.doughnut_hole` | 圆环内径 | `ratio` / — | native/office_extension | visual |
| `chart.data_table` | 图表内数据表 | `chart_data_table` / — | native/office_extension | visual |
| `chart.manual_layout` | 图表元素手动布局 | `chart_layout` / ratio | native/office_extension | visual |
| `chart.plot_area` | 绘图区填充、边框和布局 | `chart_area` / — | native/office_extension | visual |
| `chart.chart_area` | 图表区填充、边框和布局 | `chart_area` / — | native/office_extension | visual |
| `chart.three_d` | 旋转、视角、深度、地板与墙面 | `chart3d` / typed | native/office_extension | visual |
| `chart.modern_options` | 直方图、箱线图、瀑布、树图、旭日、地图等参数 | `extension_map` / — | native/office_extension | visual |

## SmartArt 数据与布局语义

来源范围：`DML-diagram+VBA-SmartArt`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `smartart.data_model` | 节点、连接、语义结构 | `diagram_data` / — | native | visual |
| `smartart.node_text` | 节点富文本 | `text_body[]` / — | native | visual |
| `smartart.layout_ref` | 布局定义和算法参数 | `diagram_layout` / — | native | visual |
| `smartart.colors_ref` | 颜色定义 | `diagram_colors` / — | native | visual |
| `smartart.quick_style_ref` | 快速样式 | `diagram_style` / — | native | visual |
| `smartart.rendered_drawing` | 缓存的绘图部件 | `drawing_ref` / — | native | visual |
| `smartart.node_ids` | 节点标识与对象绑定 | `id_map` / — | native | visual |
| `smartart.direction` | 布局方向 | `enum` / — | native | visual |
| `smartart.node_adjustments` | 节点手动位置和大小调整 | `node_adjustments` / pt | native | visual |

## 公式与数学结构

来源范围：`OMML+Office-Drawing2010`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `math.content` | Office Math 完整表达式树 | `omml_tree` / — | native/office_extension | layout/visual |
| `math.source` | LaTeX 等源表示及溯源 | `math_source` / — | native/office_extension | layout/visual |
| `math.display_mode` | 行内或独立公式 | `enum` / — | native/office_extension | layout/visual |
| `math.style` | 数学字体、字号、颜色与字形 | `math_style` / pt | native/office_extension | layout/visual |
| `math.alignment` | 公式对齐 | `enum` / — | native/office_extension | layout/visual |
| `math.spacing` | 公式与普通文本的间距 | `math_spacing` / pt | native/office_extension | layout/visual |
| `math.compatibility_choice` | 兼容分支与替代表示 | `compatibility_tree` / — | native/office_extension | layout/visual |

## 音频、视频、旁白与播放

来源范围：`DML-media+PML-timing+VBA-MediaFormat`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `media.kind` | 音频、视频或旁白 | `enum` / — | native/office_extension | poster_only |
| `media.asset_ref` | 嵌入媒体 | `asset_ref` / — | native/office_extension | poster_only |
| `media.external_ref` | 外部媒体与在线媒体信息 | `external_ref` / — | native/office_extension | poster_only |
| `media.poster_ref` | 封面帧 | `asset_ref` / — | native/office_extension | poster_only |
| `media.trim_start` | 裁剪起点 | `duration` / ms | native/office_extension | poster_only |
| `media.trim_end` | 裁剪终点 | `duration` / ms | native/office_extension | poster_only |
| `media.volume` | 音量 | `ratio` / 0..1 | native/office_extension | poster_only |
| `media.mute` | 静音 | `boolean` / — | native/office_extension | poster_only |
| `media.loop` | 循环播放 | `boolean` / — | native/office_extension | poster_only |
| `media.play_across_slides` | 跨页播放 | `boolean` / — | native/office_extension | poster_only |
| `media.hide_when_stopped` | 停止时隐藏 | `boolean` / — | native/office_extension | poster_only |
| `media.rewind_after_play` | 播放后回到起点 | `boolean` / — | native/office_extension | poster_only |
| `media.fade_in` | 淡入时长 | `duration` / ms | native/office_extension | poster_only |
| `media.fade_out` | 淡出时长 | `duration` / ms | native/office_extension | poster_only |
| `media.bookmarks` | 书签时间点 | `media_bookmark[]` / ms | native/office_extension | poster_only |
| `media.play_trigger` | 播放触发绑定 | `trigger` / — | native/office_extension | poster_only |
| `media.controls` | 控制与全屏播放 | `media_controls` / — | native/office_extension | poster_only |
| `media.caption_tracks` | 字幕轨道集合 | `caption_track[]` / — | office_extension/host | poster_only |
| `media.caption_track.id` | 字幕轨道标识 | `id` / — | office_extension/host | poster_only |
| `media.caption_track.language` | 字幕语言 | `language_tag` / — | office_extension/host | poster_only |
| `media.caption_track.label` | 字幕轨道标签 | `text` / — | office_extension/host | poster_only |
| `media.caption_track.resource` | 嵌入或链接字幕资源 | `asset_ref` / — | office_extension/host | poster_only |
| `live_feed.properties` | Cameo 对象和 LiveFeed 属性 | `extension` / — | office_extension/host | poster_only |
| `live_feed.placeholder` | 实时摄像头占位符 | `placeholder_ref` / — | office_extension/host | poster_only |
| `live_feed.background_removal` | 实时源背景处理 | `extension` / — | office_extension/host | poster_only |
| `live_feed.poster_ref` | 实时摄像头静态替代图 | `asset_ref` / — | office_extension/host | poster_only |
| `live_feed.host_binding` | 设备、权限和运行环境绑定 | `host_binding` / — | office_extension/host | poster_only |

## 完整时间树、触发与对象动画

来源范围：`PML-timing+VBA-AnimationBehavior/Timing`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `animation.timeline` | 并行、串行与时间节点树 | `time_graph` / — | native/office_extension | metadata |
| `animation.target_ref` | 对象、文字范围或图表目标 | `animation_target` / — | native/office_extension | metadata |
| `animation.behavior` | 出现、强调、退出、动作路径及属性行为 | `enum` / — | native/office_extension | metadata |
| `animation.preset` | 预设类、ID 与子类型 | `preset_ref` / — | native/office_extension | metadata |
| `animation.trigger` | 点击、同前、后前、媒体书签、事件条件 | `trigger[]` / — | native/office_extension | metadata |
| `animation.delay` | 延迟 | `duration` / ms | native/office_extension | metadata |
| `animation.duration` | 时长及自动/不定长模式 | `time_value` / ms | native/office_extension | metadata |
| `animation.repeat` | 次数或重复时间 | `repeat` / typed | native/office_extension | metadata |
| `animation.autoreverse` | 自动反转 | `boolean` / — | native/office_extension | metadata |
| `animation.speed` | 播放速度 | `ratio` / — | native/office_extension | metadata |
| `animation.acceleration` | 加速比例 | `ratio` / 0..1 | native/office_extension | metadata |
| `animation.deceleration` | 减速比例 | `ratio` / 0..1 | native/office_extension | metadata |
| `animation.fill_mode` | 结束保留和重启规则 | `enum` / — | native/office_extension | metadata |
| `animation.keyframes` | 时间、值与插值 | `keyframe[]` / ratio | native/office_extension | metadata |
| `animation.motion_path` | 运动路径及原点 | `motion_path` / typed | native/office_extension | metadata |
| `animation.transform` | 位置、缩放和旋转动画 | `transform_animation` / typed | native/office_extension | metadata |
| `animation.color` | 颜色动画与颜色空间 | `color_animation` / — | native/office_extension | metadata |
| `animation.effect` | 滤镜、进出场与效果参数 | `effect_animation` / — | native/office_extension | metadata |
| `animation.command` | 媒体或对象播放命令 | `command` / — | native/office_extension | metadata |
| `animation.text_build` | 逐字、逐词、逐段或层级构建 | `text_build` / — | native/office_extension | metadata |
| `animation.chart_build` | 图表系列与类别构建 | `chart_build` / — | native/office_extension | metadata |
| `animation.diagram_build` | SmartArt 构建 | `diagram_build` / — | native/office_extension | metadata |
| `animation.iteration` | 迭代间隔和粒度 | `iteration` / ms/ratio | native/office_extension | metadata |
| `animation.runtime_state` | 交互序列与时间节点绑定 | `runtime_binding` / — | native/office_extension | metadata |

## 页面切换、Morph 与 Zoom

来源范围：`PML-transition+MS-PPTX-extensions`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `transition.kind` | 标准和 Office 扩展切换类型 | `enum` / — | native/office_extension | metadata/poster |
| `transition.direction` | 方向及子类型 | `enum` / — | native/office_extension | metadata/poster |
| `transition.duration` | 切换时长 | `duration` / ms | native/office_extension | metadata/poster |
| `transition.speed` | 速度预设 | `enum` / — | native/office_extension | metadata/poster |
| `transition.advance_on_click` | 单击换页 | `boolean` / — | native/office_extension | metadata/poster |
| `transition.advance_after` | 自动换页时间 | `duration` / ms | native/office_extension | metadata/poster |
| `transition.sound` | 换页声音与循环 | `media_ref` / — | native/office_extension | metadata/poster |
| `transition.morph` | Morph 模式与对象匹配标识 | `morph` / — | native/office_extension | metadata/poster |
| `zoom.kind` | 页面、节或摘要缩放 | `enum` / — | native/office_extension | metadata/poster |
| `zoom.target_refs` | 导航目标 | `ref[]` / — | native/office_extension | metadata/poster |
| `zoom.return_behavior` | 缩放返回与背景显示 | `zoom_behavior` / — | native/office_extension | metadata/poster |
| `zoom.thumbnail_ref` | 缩放缩略图资源 | `asset_ref` / — | native/office_extension | metadata/poster |

## 超链接与动作

来源范围：`DML-hyperlink+VBA-ActionSetting`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `interaction.event` | 点击或鼠标悬停 | `enum` / — | native | hyperlink/metadata |
| `interaction.hyperlink` | URL、页、文档或自定义放映目标 | `hyperlink` / — | native | native |
| `interaction.tooltip` | 提示文字 | `text` / — | native | native |
| `interaction.highlight_click` | 点击高亮与访问状态 | `boolean` / — | native | hyperlink/metadata |
| `interaction.navigation_action` | 下一页、上一页、首尾页与返回 | `enum` / — | native | hyperlink/metadata |
| `interaction.media_action` | 媒体播放动作 | `media_action` / — | native | hyperlink/metadata |
| `interaction.object_action` | OLE、程序或宏动作描述 | `action_descriptor` / — | native | hyperlink/metadata |
| `interaction.sound` | 动作声音 | `media_ref` / — | native | hyperlink/metadata |
| `interaction.history` | 导航历史设置 | `boolean` / — | native | hyperlink/metadata |

## 备注、讲义、放映与打印

来源范围：`PML-notes/handout+VBA-Presentation/SlideShowSettings`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `notes.content` | 备注页富文本与对象 | `notes_page` / — | native | metadata |
| `notes.master_ref` | 备注母版 | `ref` / — | native | metadata |
| `handout.master` | 讲义母版与对象 | `handout_master` / — | native | metadata |
| `slideshow.custom_shows` | 自定义放映页面列表 | `custom_show[]` / — | native | metadata |
| `slideshow.range` | 放映范围 | `slide_range` / — | native | metadata |
| `slideshow.kind` | 演讲者、窗口或展台模式 | `enum` / — | native | metadata |
| `slideshow.loop` | 循环放映 | `boolean` / — | native | metadata |
| `slideshow.use_timings` | 使用计时 | `boolean` / — | native | metadata |
| `slideshow.show_animation` | 显示动画 | `boolean` / — | native | metadata |
| `slideshow.show_narration` | 播放旁白 | `boolean` / — | native | metadata |
| `slideshow.pen_color` | 演示笔颜色 | `color` / — | native | metadata |
| `print.options` | 打印范围、颜色模式与讲义选项 | `print_options` / — | native | metadata |

## 批注、无障碍与协作元数据

来源范围：`PML-comments+Office-modern-comments/decorative`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `comments.legacy` | 传统批注、作者、位置和时间 | `comment[]` / — | native/office_extension | metadata |
| `comments.threads` | 现代批注、回复和解决状态 | `comment_thread[]` / — | native/office_extension | metadata |
| `comments.people` | 人员与身份引用 | `person[]` / — | native/office_extension | metadata |
| `comments.anchors` | 批注对象和文字锚定 | `comment_anchor` / — | native/office_extension | metadata |
| `accessibility.title` | 替代标题 | `text` / — | native/office_extension | native |
| `accessibility.description` | 替代描述 | `text` / — | native/office_extension | native |
| `accessibility.decorative` | 装饰性对象标志 | `boolean` / — | native/office_extension | metadata |
| `accessibility.reading_order` | 辅助阅读顺序 | `ref[]` / — | native/office_extension | metadata |
| `metadata.tags` | 对象标签 | `map` / — | native/office_extension | metadata |
| `metadata.customer_data` | 自定义部件与业务数据 | `part_refs` / — | native/office_extension | metadata |
| `metadata.hidden_data_policy` | 个人信息与隐藏内容处理策略 | `policy` / — | native/office_extension | metadata |

## 嵌入对象、控件与扩展

来源范围：`PML-OLE/control+Office-extensions`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `embedded.kind` | OLE、工作簿、控件或其他嵌入包 | `enum` / — | native/opaque | poster_only |
| `embedded.asset_ref` | 二进制或子包资源 | `asset_ref` / — | native/opaque | poster_only |
| `embedded.prog_id` | 对象程序标识 | `text` / — | native/opaque | poster_only |
| `embedded.link_ref` | 链接对象来源 | `external_ref` / — | native/opaque | poster_only |
| `embedded.preview_ref` | 对象预览图 | `asset_ref` / — | native/opaque | poster_only |
| `embedded.display_mode` | 图标或内容显示 | `enum` / — | native/opaque | poster_only |
| `embedded.activation` | 激活动作描述 | `activation` / — | native/opaque | poster_only |
| `embedded.control_properties` | 控件和持久化数据 | `opaque_parts` / — | native/opaque | poster_only |
| `embedded.web_extensions` | Web 扩展、绑定和任务窗格部件 | `opaque_parts` / — | native/opaque | poster_only |

## 保护、签名、标签与兼容保留

来源范围：`VBA-Presentation+package+MS-PPTX/ODRAWXML`。详细证据见 [研究来源](research-sources.md)。

| 语义字段 | 属性 | 类型 / 单位 | PPTX 目标 | 静态 SVG 目标 |
| --- | --- | --- | --- | --- |
| `package.security.encryption` | 加密容器与参数 | `encryption_profile` / — | host/opaque | metadata |
| `package.security.permissions` | IRM 与授权策略引用 | `rights_profile` / — | host/opaque | metadata |
| `package.security.write_protection` | 写保护与只读建议 | `protection` / — | host/opaque | metadata |
| `package.security.signature` | 数字签名及修改后的有效性 | `signature_profile` / — | host/opaque | metadata |
| `package.security.sensitivity` | 敏感度标签与策略 | `label_profile` / — | host/opaque | metadata |
| `package.macro_profile` | pptx/pptm 容器差异与宏部件 | `format_profile` / — | host/opaque | metadata |
| `compatibility.unknown_xml` | 未建模 XML 与 QName | `opaque_xml[]` / — | host/opaque | metadata |
| `compatibility.unknown_parts` | 未建模资源部件和关系 | `opaque_parts` / — | host/opaque | metadata |
| `compatibility.alternate_content` | 兼容分支及所需命名空间 | `compatibility_tree` / — | host/opaque | metadata |
| `compatibility.extension_list` | 扩展项及 URI | `extension_map` / — | host/opaque | metadata |
| `compatibility.relationship_map` | 稳定语义 ID 与本地 rId 映射 | `relation_map` / — | host/opaque | metadata |
| `compatibility.producer_metadata` | 生成器和编辑器元数据 | `producer_metadata` / — | host/opaque | metadata |
