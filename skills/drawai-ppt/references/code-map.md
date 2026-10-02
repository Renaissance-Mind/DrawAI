# Python 代码扩展指南

所有路径相对于 skill 目录。依赖和实现均在目录内维护。

| 位置 | 职责 |
| --- | --- |
| scripts/ppt.py / pptx_skill/cli.py | 任意工作目录可运行的统一入口、Schema、导入/导出和计划命令 |
| pptx_skill/document/model.py | presentation.document.v1、稳定 ID、资源、模板、属性目录验证和原生绑定契约 |
| document/export.py | 原生对象创建/修改、模板页面管理、包合并和结构验证 |
| document/xml.py | 单位换算、颜色、填充、渐变、图片填充、线与 XML 顺序 |
| document/rich.py | 有序富文本、段落、文本框、路径、效果与 3D |
| document/advanced.py / charts.py | 主题、图片、可访问性、变换、图表轴/标记/标签/趋势线等 |
| document/importer.py | PPTX 模板导入、正文与图片/表格/图表读取、SVG 字形引用展开和制作源恢复 |
| document/svg.py / render_env.py | 静态矢量投影、自包含 SVG metadata、字体解析与渲染报告 |
| document/svg_fallback.py | Office SVG 过滤器无法正确表达的路径渐变局部图片回退和受影响对象报告 |
| document/package.py / editing.py / identity.py | 精确原生 XML 绑定、格式覆盖移除、语义 ID 与原生 ID 分离 |
| document/capabilities.py | 实际属性 API、上下文条件、宿主依赖与模板保留覆盖 |
| pptx_skill/engine.py | 保留的操作计划契约、模板复制和文件发布；单位为 px |
| pptx_skill/svg_export.py / svg_native/ | SVG 规范化、几何、文字、公式、图片与 DrawingML 转换 |
| pptx_skill/native_builder.py | 单 SVG 原生 PPTX 包装，包括最小页面尺寸的等比调整 |
| check.py / check_document.py | 可脱离仓库执行的真实文件回归检查 |
| build_v2_demo.py / assets/demo/ | 已有参考图与公式的可复现重建与导出 |
| update_implementation_matrix.py | 生成实际能力 JSON、CSV 和 Markdown |
| research_pptx.py / build_capability_matrix.py | 固定微软来源和具体枚举值的研究目录 |

表格中包路径在 scripts/pptx_skill/ 下。制作脚本将 skill 的 scripts 目录加入 sys.path 后加载 `pptx_skill.document`；不要加入宿主仓库路径或建立额外运行时依赖。

## 增加属性 API

先在当前实现矩阵确认对应 ID、枚举和值结构，再从 Schema 清单确认原生类型和上下文。颜色、长度、比例、角度分别由 xml.py 的统一转换实现；路径视口坐标保留原有局部单位。新绑定放入负责该对象的模块，返回实际处理过的属性 ID；不通过前缀匹配把未处理参数算成支持。

缺省保留继承，显式 false 和 0 有效。将互斥的填充类型、子类型和布局条件明确限制。输入错误直接暴露；不能凭相似名称或任意 XML 能写入就宣布语义已实现。

更新 capabilities.py、其条件说明和真实文件检查，执行 update_implementation_matrix.py。研究属性目录与实际实现记录分别维护；研究稿里的未确认默认值/继承规则不能因为已有代码就自动改成已验证。

## 导入与模板保留

导入保存完整包和 baseline，修改只覆盖实际变化的属性。正文的 native_ppr/native_rpr 与 baseline_properties 保留未建模的格式；文字变化不应重建全部样式。图表不改数据时保留工作簿和公式，改数值时更新真正的工作簿。

保留关系闭包、未知扩展、mc:AlternateContent 和未被普通 shapes 列表识别的对象。复制页独立复制可变图表、工作簿和备注。分组维护外框和子坐标系，创建新子对象后恢复未修改的原分组变换。新输出经过实际包验证与重新打开后发布。

## 原生 XML 与静态 SVG

native_bindings 逐项声明属性 ID、owner、部件和 XPath，检查匹配数量。native_parts 与 native_xml 用于明确的原生资源/对象树；所有内部引用仍须通过包校验。XML 模式是开放的底层能力，不代替每个功能的高级属性 API 和语义验证。宿主安全/激活设置不能用 XML 绑定伪装完成。

SVG 从实际的同一 PPTX 排版导出。模型压缩嵌入 metadata，资源内嵌，外观哈希防止恢复过期源。普通 SVG 导入则使用原生转换器；改变公式画布大小时等比缩放，并保持字形路径与视口关系。

## 检查

```bash
python <skill-dir>/scripts/check.py
python <skill-dir>/scripts/check_document.py
python <skill-dir>/scripts/update_implementation_matrix.py
```

修改视觉效果还需导出并检查实际 PPTX/SVG，按 PowerPoint 和 LibreOffice 分别记录结果。回归使用真实文件、真实 XML、关系、工作簿和对象，避免镜像实现或替代渲染器的 mock。
