# Python 代码扩展指南

以下路径相对于 skill 目录，代码、依赖和测试均在目录内维护。

| 位置 | 职责 |
| --- | --- |
| `scripts/ppt.py` | 加载 skill 内的 Python 包并执行 CLI |
| `scripts/requirements.txt` | Python 依赖清单 |
| `scripts/pptx_skill/cli.py` | 创建、检查、编辑、Schema、验证和渲染命令 |
| `scripts/pptx_skill/engine.py` | 当前计划契约、对象操作、模板复制和文件发布 |
| `scripts/pptx_skill/svg_export.py` | SVG 规范化、箭头、文字位置与 Office Math |
| `scripts/pptx_skill/native_builder.py` | 原生绘图 XML、图片与引用关系的 PPTX 打包 |
| `scripts/pptx_skill/svg_native/` | 几何、曲线、文字、分组、图片和填充的 DrawingML 转换 |
| `scripts/check.py` | 真实文件回归检查 |
| `scripts/research_pptx.py` | 固定版本的微软 Schema 属性与枚举提取 |

## 选择实现位置

普通任务先使用计划或 `python-pptx` 的对象 API。一次性的内容、位置和配色保存在任务制作脚本中。可复用的新对象或样式加入 `engine.py`；SVG 几何和样式问题修改 `svg_native/`；参数与命令修改 `cli.py`。

精细制作脚本可在加入实际 skill 的 scripts 目录后加载 API：

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(skill_dir) / "scripts"))
from pptx_skill import create_pptx, edit_pptx, inspect_pptx, validate_pptx_package
```

## 扩展操作与文档模型

新增计划操作时定义 `StrictModel` 子类及唯一的 `op: Literal[...]`，加入 `Operation` 并在 `_apply_operation` 实现。创建和编辑共用 `_execute_plan`，其 Schema 随类型声明更新。同步 CLI 帮助和真实文件测试。

完整文档模型遵循 [PPTX 优先规范](pptx-standard.md)。先按 [属性清单](property-catalog.json) 定义值类型、单位、继承、原生映射与输出 profile，再实现导入和导出。现有编辑计划不能代替完整文档。能力矩阵的设计目标与代码状态分别维护。

## 模板与 XML 的关键约束

对象 ID 属于页面；插入对象重新分配 ID。图片关系重新绑定到目标页面。SVG 分组设置外框和子坐标系。

保留 `mc:AlternateContent` 等普通 shape 列表遗漏的对象和命名空间。复制页时独立复制可变的图表、工作簿与备注；保持主题、母版和版式引用。局部文字替换保留 run 属性。

完成全部操作和包校验后发布到新文件。保存与实际渲染分别验证；不将未建模的属性静默丢弃或宣称已支持。

## 验证

```bash
python <skill-dir>/scripts/check.py
python <skill-dir>/scripts/ppt.py validate output/deck.pptx
python <skill-dir>/scripts/ppt.py render output/deck.pptx --output-dir work/preview
```

测试使用临时目录、真实 PPTX/SVG/图片和实际对象。Pandoc 可用时测试真实公式转换。修改视觉效果时检查最终逐页预览，并按目标 PowerPoint 环境记录验证结果。
