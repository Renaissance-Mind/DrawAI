# 代码指南

所有代码与依赖都在 skill 目录内。公共 API 从 `pptx_skill` 导入，统一使用 `presentation.document.v1` 和 pt。

| scripts/ 下的位置 | 职责 |
| --- | --- |
| ppt.py / pptx_skill/cli.py | schema、import、export、inspect、validate、render 与属性查询 |
| example.py | 完整的创建与局部文字修改示例 |
| pptx_skill/document/model.py | 文档、页面、对象、资源、属性验证与 XML 绑定契约 |
| document/export.py | 创建/修改原生对象、页面与分组堆叠顺序、包发布 |
| document/importer.py | PPTX 原始包与对象读取、SVG 转换和制作源恢复 |
| document/editing.py / insert.py | 格式覆盖清除、页面复制、SVG 插入 |
| document/authoring.py | 根据起点与终点创建连线，计算包围框与方向翻转 |
| document/identity.py | 文档对象 ID；复制或导入重复标识时生成唯一值 |
| document/xml.py / rich.py | 单位、颜色、填充、线、富文本、段落、路径、效果与 3D |
| document/advanced.py / charts.py | 主题、图片、变换、可访问性及图表细节 |
| document/svg.py / svg_fallback.py / render_env.py | SVG 静态投影、完整制作源、渐变回退和字体环境 |
| document/package.py | 精确的原生 XML 部件修改 |
| pptx_skill/io.py | PPTX 清单、关系校验、PDF/PNG 渲染和可变部件复制 |
| svg_export.py / svg_native/ / native_builder.py | SVG 原生绘图、文字、图片和 Office Math 转换与打包 |
| check.py / check_document.py / check_workflows.py | 真实文件、属性与完整操作流程回归 |
| build_v2_demo.py / assets/demo/ | 固定参考图的人工重建示例 |
| update_implementation_matrix.py | 一次更新两份矩阵的 JSON、CSV、Markdown |
| research_pptx.py / build_capability_matrix.py | 原生字段、枚举与固定来源的研究目录 |

`assets/rebuildable-deck/` 是可以复制到任务目录的制作项目：`build.py` 调用 `assets/src/line_chart.py`，读取 CSV 并生成独立图表，再组合原生文字与图片对象。它的 Matplotlib 依赖只用于示例绘图；修改布局、换数据源或增加素材时编辑复制后的项目文件。流程与交付方式见 [视觉与素材](visual-assets.md)。

## 扩展属性

查询属性 ID 的 [实现条件](implementation-capabilities.md)，需要原生字段时再查 [Schema 清单](pptx-inventory/schema-properties.csv) 和 [来源](research-sources.md)。新增绑定放到相应对象模块，返回实际处理的属性 ID。

在属性契约中说明值结构、单位、缺省/继承行为、互斥条件，以及创建和修改的适用对象。颜色、长度、比例和角度由统一构造函数转换；路径坐标保留局部单位。原生 XML 树接口应明确其 QName、资源关系和例子。

修改 `document/capabilities.py` 后统一生成矩阵：

```bash
python "$SKILL_DIR/scripts/update_implementation_matrix.py"
```

`property-catalog.json` 是字段与枚举的目录，capabilities.py 是实际接口与条件的事实源；矩阵文件是生成结果。研究默认值与继承条款根据原生依据更新，实施绑定与实际验证分别记录。

## 保留与编辑

导入保存完整 PPTX 包和 baseline。原始 native_ppr/native_rpr 保留未建模格式，文字变化只改对应 run。清除覆盖作用于最终 XML；对象排序重排绘图树中的已建模节点，原始扩展节点保留其位置。

复制页面生成新的语义 ID，保留页面内数字形状 ID，独立复制可变图表、工作簿和备注页面，备注母版保持共享引用。包校验核对活动备注页面的母版已在演示文稿中注册。插入 SVG 为原生分组，重新分配数字 ID 和图片关系。精确 XML 绑定按具体部件路径工作，涉及页面复制时同步目标路径与引用。

SVG 从实际 PPTX 导出，写入完整文档源和外观哈希。预览与 SVG 的 LibreOffice 输入默认使用忽略嵌入字体的临时副本，字体由本机字体环境解析；`embedded_fonts="preserve"` 使用原始字体引用。交付 PPTX 与 SVG 中嵌入的制作源保留原始包。修改导出器时检查背景、母版对象、静态可见性、字体与特殊效果。回退报告列出实际受影响对象。

## 验证

```bash
python "$SKILL_DIR/scripts/check.py"
python "$SKILL_DIR/scripts/check_document.py"
python "$SKILL_DIR/scripts/check_workflows.py"
```

验证创建、修改、复制、重新导入、字段值、引用闭包与真实渲染。新增参数示例也执行验证；视觉变化检查实际 PPTX 和浏览器 SVG。任务产物与工具包回归分别检查。
