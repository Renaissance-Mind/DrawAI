# PPTX 优先的统一文档规范

状态：研究稿 v0.2；调研日期：2026-10-02。目标是完整保留 PPTX 的文档、对象、样式、交互和扩展语义，再按各输出格式的能力导出。统一文档已实现，字段契约的研究状态与 [当前实现矩阵](implementation-capabilities.md) 分别记录。

## 调研依据和覆盖口径

调研使用三个层次的证据：ISO/ECMA 对应的 PresentationML、DrawingML、图表、Diagram、Office Math 等结构；微软 MS-PPTX/MS-ODRAWXML 扩展；PowerPoint/Office 对象模型中的可设置属性。

微软 Open XML SDK 固定版本 `431ab05cf160248cc3885a4a766026d4f8243792` 的 60 个 Schema 文件提供 2,009 条类型声明、8,692 条属性/子元素出现记录、241 个枚举。记录包含继承属性和不同上下文的复用，不能当作 8,692 个独立的 PowerPoint 用户设置。共享 DrawingML 有 Word/Excel 同用的类型，必须在具体 PPTX 对象上下文检查适用性。

在此基础上，整理 [25 个领域、475 项语义属性](export-capabilities.md)，可维护数据位于 [property-catalog.json](property-catalog.json)。Schema 原始字段、枚举、基类继承与版本线索位于 [Schema 清单](pptx-inventory/schema-inventory.json) 和 [属性 CSV](pptx-inventory/schema-properties.csv)。完整来源、固定版本和哈希位于 [研究来源](research-sources.md) 及 [来源清单](pptx-inventory/schema-sources.json)。

这些清单用于发现遗漏、设计对象模型和逐项验证，不构成“当前导出器已完整支持 PowerPoint”的声明。部分设置依赖 Office 版本、宿主应用、媒体编码、字体或授权，某些 API 属性只是窗口/应用运行状态，不是应写入统一文档的属性。

## 文档模型

序列化标识为 `presentation.document.v1`。API 使用属性目录 ID、稳定对象 ID、页面、资源、原生包与显式 XML 绑定。具体可运行结构见 [统一文档 API](document-api.md)；以下结构描述完整语义目标：

```text
Document
  metadata / assets / embedded fonts / compatibility profile
  themes / masters / layouts / notes master / handout master
  pages[]
    stable id / layout binding / background / header-footer
    objects[]
      identity / geometry / transform / style / children
      text body -> paragraphs -> ordered Run / Break / Field / Math
      native table / chart / diagram / equation / media / embedded object
    timeline / transition / comments / notes / interactions
  sections / custom shows / slideshow settings
  preserved package parts / extension namespaces / relationships
```

创建和修改作用于同一完整对象模型，保存能够重建页面的内容、样式、资源和原始部件。

每个对象必须保持稳定语义 ID。PPTX 的本地数字对象 ID、关系 `rId` 和 SVG 的元素 ID 属于各自导出空间，建立独立映射。路径保留独立视口、任意局部坐标和公式引用。段落保留 Run/Break/Field/Math 有序混合序列，字段保存 ID、类型、缓存文字和格式。路径、文字、表格、图表、SmartArt 和公式保留各自原生语义，不在模型中提前展开成无区别的绘图碎片。

## 属性定义契约

字段级契约仍需依据原生条款逐项完成，目录中的 `not_assessed`/`unmapped` 是实际未确认状态。每项属性记录：唯一字段 ID、对象类型、值类型、单位、值域/枚举、是否可继承、未设置的行为、互斥条件、版本和平台要求、原生 XML 映射、导出目标、实际实现状态、验证用例与结果。

`property-catalog.json` 提供语义字段及导出目标的初版。`schema-inventory.json` 提供精确的原生父类型、属性/子元素 QName、SDK 类型、基类声明、校验器和枚举。开发时建立明确映射；不能凭字段名称相似就视为相同语义。

### 单位

| 类型 | 规范单位及约束 | 原生转换 |
| --- | --- | --- |
| 位置、尺寸、内边距、线宽、缩进 | pt；明确允许负值的字段使用 signed length | 1 pt = 12,700 EMU；SVG 96 DPI 下 1 pt = 4/3 px |
| 自定义路径、几何公式和调节柄 | 保留路径 w/h 定义的局部坐标、数值或公式；没有固定物理单位 | 通过形状坐标系与路径视口映射；不直接按 pt 解释 |
| 字号、字间距、字偶距阈值 | pt | DrawingML 对应字段使用其声明的百分之一 pt 等单位 |
| 角度 | degree | 常见 DrawingML 角度单位为 1/60,000 degree；具体字段仍按原生类型确认 |
| 比例、透明度、渐变色标 | ratio | 原生百分比常采用 100,000 = 100%；允许负值或超过 100% 的字段保留 signed ratio |
| 行距、段前段后间距 | `{mode: points\|ratio, value}` | 保留固定值与百分比值的区别 |
| 时间 | ms 或显式的 automatic/indefinite 模式 | 动画时间节点分别映射，不能把无穷/自动当作 0 |
| 日期 | 带时区时间；规范化存储为 UTC | 对象元数据和批注按原始语义保存 |

文档模型的物理长度统一为 pt；从 96 DPI 位图估计位置时，像素值乘 0.75 后写入模型。

### 未设置、继承与显式值

属性缺省表示 `unset`，保留原生继承和格式默认行为；显式 `false`、0、透明填充和“无填充”均是有效且不同的值。需要恢复继承时使用明确的 `clear_overrides` 操作。不要将缺省属性自动写成 false 或固定值。

保留直接格式和主题/样式引用，另外计算用于渲染的 resolved style。默认继承模型需要覆盖文档主题、母版、版式、占位符、段落层级、文字片段及表格/图表样式规则。不同属性有不同的继承规则，不能用一条全局 CSS 式优先级替代 OOXML 规则。

### 颜色和填充

颜色保留 RGB、scRGB、HSL、主题色、系统色、预设色以及有序的颜色变换。转换包含 tint/shade、alpha、色相、饱和度、亮度、补色、反相、灰度和 Gamma 等，值域来自原生字段。

填充保留无填充、纯色、组继承、图案、图片填充和完整渐变结构。渐变保留色标及透明度、线性角度和 scaled、路径类型 circle/rect/shape、fill-to-rectangle、tile rectangle、flip 和 rotate-with-shape。图案保留原生预设枚举及前景/背景；图片填充保留裁剪、拉伸、平铺、偏移、缩放、对齐与旋转语义。

### 文字结构

文字片段保存字体的 Latin/East Asian/Complex Script/Symbol 分类、字号、粗斜体、下划线及其独立描边/填充、删除线、大小写、字间距、字偶距阈值、基线位移、文字填充/轮廓/效果、语言、校对和超链接。

段落保存对齐、0–8 的原生层级语义、左右缩进、首行/悬挂缩进、固定或比例行距、段前段后距离、制表位、RTL 和中西文换行规则、项目符号/编号/图片以及默认和段落结束 run 样式。

文本框保存内边距、锚定、分栏、竖排/东亚竖排、旋转、溢出、自动适应及其缩放、艺术字变形、文字 3D 和兼容排版规则。完整设置必须有实际布局处理；同样的参数不能直接保证不同软件得到同样的断行。

## 导出能力契约

每个导出器声明格式、应用/版本、字体和资源环境、输出 profile，以及每项属性的处理方式。属性目标状态分为原生、Office 扩展、布局生成、静态外观、近似、仅元数据、静态替代、原样保留和宿主依赖。实现进度另行记录，不与这些目标状态混用。

PPTX 是主要保真目标。静态 SVG 是文档的视觉投影：它可以显示表格、图表、SmartArt、公式和 3D 的当前外观，同时在源模型保留原生数据；不能声明其动态行为或原生编辑结构已同样得到保留。

当前 SVG 的标准渐变只有线性/径向对应结构，矩形和 shape path 渐变需要专门的可验证实现或近似报告。文字布局、3D、艺术效果、媒体和动画需要逐项讨论输出 profile。SVG 中存在某种表达方式也不代表所有 SVG 查看器都能以相同方式执行。

导出策略：

- `strict`：每个请求属性有处理结果，否则报出对象 ID、字段和原因。
- `best_effort`：允许跳过未实现属性，记录实际遗漏。

视觉验证在字体和渲染环境中分别进行，以实际页面、区域和数据为证据。

损失报告包括对象 ID、属性 ID、请求值、实际导出值或替代方式、损失的语义、目标应用/版本与验证证据。没有验证的视觉等价不能标记为已验证。

## 导入与往返保留

未建模的 XML、`extLst`、`mc:AlternateContent`、命名空间、关系和二进制资源整体进入兼容性区域。原样保留不表示能原生创建或编辑。只有改变相关对象时才解析并重建其需要的部分；保留引用闭包和互斥兼容分支。

已有图表的工作簿、公式、数据缓存、外链和来源分别保存；不能用纯数值快照替代原公式和来源。SmartArt 保存数据、布局、颜色、样式及缓存绘图。复制页面时独立复制可变的数据，稳定绑定对象、动画、批注及导航目标。

修改签名文档会影响签名有效性，不能原样复制签名部件后宣称仍有效。加密/IRM 和敏感度策略需要独立容器/宿主流程。`.pptx` 与宏启用容器 `.pptm` 分别建 profile，不能把宏工程偷偷塞入普通 PPTX。导入不执行宏、动作、外链或嵌入程序。

## 完成与验证标准

实现状态采用 `not_assessed / planned / implemented / verified`；验证记录必须说明创建、读取、修改、往返保存、对象编辑和渲染各自是否通过。SDK 有属性或原文件能被保存，均不足以标为已完整支持。

每项功能需要实际参考文件和测量：属性值及原生枚举、XML 结构/关系、资源完整性、在目标 PowerPoint 中可编辑、导入再导出保留情况、逐页或区域渲染、动态功能实际执行。使用 LibreOffice 的结果单独记录，不能替代 PowerPoint 的验证。

基准场景至少覆盖：混合 run 样式、中英和复杂文字、9 级列表、固定/比例行距、缩进和制表、字体缺失、全部颜色/填充类别、渐变参数、组合与连接点、完整图表和工作簿、合并表格、公式、SmartArt、媒体、时间树、Morph/Zoom、批注、嵌入对象和未知扩展保留。自动测试和人工 PowerPoint 验证分别列出证据。

## 当前实现口径

当前支持完整 `presentation.document.v1`、PPTX 导入/导出和静态 SVG 投影。266 项属性已有原生 API，202 项使用模板保留或显式 XML 绑定，7 项需要宿主或容器流程。该分布不表示 475 项都有同等的高级 API，或所有 PowerPoint 版本与 SVG 渲染器已有完整等价验证。

所有创建和编辑统一使用文档模型，长度为 pt。SVG 通过同一实际 PPTX 的 LibreOffice 排版导出，嵌入制作源并检查外观哈希；特殊效果可能栅格化，字体与目标 PowerPoint 差异需分别确认。包校验、属性值检查、模板保留和实际外观/播放验证分别记录。

## 已确认的模型约束

任意仿射矩阵与 PPTX 的 frame/rotation/flip 不能直接等同：导出时声明组合顺序、可分解条件、剪切烘焙或其他替代策略。路径的非零/奇偶填充规则与 DrawingML 的 normal/lighten/darken 填充模式不同，不能用同一枚举字段映射。路径 stroke 的原生缺省值为 true、extrusionOk 缺省为 false，二者不是通用主题继承。

网格保存独立的 x/y 间距。文档原始 revision 保存字符串，需要整数计数时另设派生值。母版和版式的颜色映射、页眉页脚、时间与切换各自保留作用域。字幕和 LiveFeed/Cameo 的持久化信息与宿主设备/权限状态分别表示。

SDK 快照未覆盖 Morph 等部分扩展，规范依据和补充条款单独记录；不能把 SDK 的类型清单当作完整的 PowerPoint 产品能力边界。
