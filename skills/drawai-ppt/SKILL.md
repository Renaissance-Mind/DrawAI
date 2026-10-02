---
name: drawai-ppt
description: "Create and edit native PowerPoint with Python, reuse templates, author a portable document model, export editable PPTX and static SVG from the same source, and extend the self-contained implementation using a source-backed property matrix."
---

# DrawAI PPT

制作可继续加工的 PowerPoint，并从同一份完整文档数据导出 PPTX 和静态 SVG。支持模板导入、富文本、原生形状和路径、渐变与图案、箭头、图片、表格、图表和原生 Office XML 保留。所有说明、脚本、依赖和测试均在 skill 目录内，可移动到任意 Agent 的工作目录使用。

## 环境与入口

```bash
python -m pip install -r <skill-dir>/scripts/requirements.txt
python <skill-dir>/scripts/ppt.py --help
python <skill-dir>/scripts/ppt.py schema --mode document
python <skill-dir>/scripts/ppt.py capabilities
```

使用 Python 3.12 或更新版本。SVG 导出需要 LibreOffice `soffice`；逐页 PNG/PDF 预览另需 Poppler `pdftoppm`；LaTeX 转 Office Math 需要 Pandoc。工具可以来自 PATH 或显式命令参数。

## 创建、修改和导出

读取 [统一文档 API](references/document-api.md)，使用 `presentation.document.v1`。长度和字号均为 pt，段落保存有序 run / break / field / math。通过 `properties` 使用 [属性矩阵](references/export-capabilities.md) 的准确 ID 与枚举值。

```bash
python <skill-dir>/scripts/ppt.py export deck.document.json \
  --pptx output/deck.pptx --svg-dir output/svg --report output/report.json
python <skill-dir>/scripts/ppt.py import template.pptx --output work/template.document.json
```

模板导入后修改实际对象和文字，保留 baseline、源 ID、原生 XML 和包信息，保存新的文档 JSON，再导出新文件。用 clear_overrides 明确移除格式覆盖。源 SVG 带有本工具的制作源 metadata 时可以恢复同一模型；外观被单独改过时拒绝使用过期数据。普通外部 SVG 通过原生 DrawingML 转换导入。

当前 [实现矩阵](references/implementation-capabilities.md) 区分属性 API、模板保留或显式原生 XML、宿主依赖。全部 475 项有对应的能力记录，已有 266 项属性 API；其余设置使用真实模板及 native_bindings/native_parts，或要求宿主流程。属性 API 仍有对象上下文与值域条件，按矩阵使用，不将 XML 可保存或包校验通过宣称为全部 PowerPoint 设置都已等价实现。

静态 SVG 使用同一 PPTX 的 LibreOffice 排版投影，保留文字与路径，特殊效果可能栅格化。图表工作簿、表格编辑、动画、媒体播放等语义保存在源模型/PPTX 中。复杂 PowerPoint 属性需要在实际目标版本核对。

需要执行已有的创建/编辑操作计划时读取 [操作计划流程](references/workflows.md)。计划契约仍使用 96 DPI px；其 schema 与统一文档的 pt 单位分别保留。常见模板替换、页面复制、图片替换和基础图表数据编辑可继续使用计划命令。

## 扩展代码

修改或扩展实现时读取 [代码扩展指南](references/code-map.md)。按 [研究来源](references/research-sources.md) 和微软 [原生 Schema 清单](references/pptx-inventory/schema-properties.csv) 确认字段、枚举和所属上下文，再增加 Python 绑定、验证及能力记录。

优先操作统一模型；新增原生属性 API 后更新 capabilities.py 与当前实现矩阵。精确 XML 绑定明确列出部件、XPath、预期匹配数量和操作，绑定失败直接报错。未处理设置由默认 strict_native 拒绝；compatible 必须交付损失报告。

## 验证与交付

```bash
python <skill-dir>/scripts/check.py
python <skill-dir>/scripts/check_document.py
python <skill-dir>/scripts/build_v2_demo.py --output-dir output/demo
python <skill-dir>/scripts/ppt.py validate output/demo/demo.pptx
python <skill-dir>/scripts/ppt.py render output/demo/demo.pptx --output-dir work/preview
```

检查实际页面的字体、断行、裁剪、遮挡、渐变、箭头和分组坐标。编辑任务对照原件；发现可修复的问题，修改模型或代码后重新导出。分别验证对象/数据、包关系、静态渲染，以及复杂功能在目标 PowerPoint 的编辑或播放行为。

交付 PPTX、逐页 SVG、预览和制作源，注明实际完成的验证和必要限制。所有输出使用新路径，保留原件。没有可用渲染器或目标软件时，明确尚未完成的检查。
