---
name: drawai
description: DrawAI 插件的统一入口与使用指南。使用 DrawAI、了解插件能力、推荐或选择模板、开始制作或编辑 PPT 时先读本技能，再进入模板或 PPT 技能。
---

# DrawAI

使用 DrawAI 插件时先阅读本指南。根据用户当前任务选择需要的技能，直接在当前对话完成工作。

## 包含的能力

| 技能 | 用途 |
| --- | --- |
| [drawai-templates](../drawai-templates/SKILL.md) | 推荐、搜索和展示模板参考；让用户在对话内选择版式与风格；准备真实参考图片 |
| [drawai-ppt](../drawai-ppt/SKILL.md) | 根据内容、数据、PPTX 模板或图片制作可编辑 PowerPoint；编辑已有 PPT；导出 SVG、预览和制作源 |

插件提供模板界面与本地模板工具。制作、理解内容和视觉生成由当前对话执行，PPT 文件操作由 `drawai-ppt` 的 Python 工具包完成。

## 按任务使用

**用户询问能力或用法。** 说明上述能力，结合当前任务给出具体使用方式。

**用户需要推荐或挑选模板。** 阅读 `drawai-templates`，根据内容用途、页面信息量与风格偏好查询真实目录，解释候选适合的原因，再展示内嵌模板界面。用户可以选择多个参考，并分别用于信息结构或视觉风格。

**用户需要制作或编辑 PPT。** 阅读 `drawai-ppt` 并执行其流程。用户已经提供内容、模板或参考时直接使用。需要模板选择、或用户希望看候选时再进入 `drawai-templates`，选择后继续制作。

**用户从模板界面提交选择。** 读取 `drawai.template-selection.v1` 中的模板 ID 与用途，按 `drawai-templates` 获取详情和真实图片，再继续当前任务。当前仅在选模板时确认选择；制作 PPT 时使用 `drawai-ppt`。

## 使用参考与交付

模板库中的图片与设计配方用于版式、视觉风格和内容组织。事实、文字、数据与结论来自用户材料。用户上传的 PPTX 模板按其真实页面用途与原生结构解析。

生成 PPT 时保留可编辑文字、图形、表格、图表等合适的原生对象；复杂图片作为局部素材。按 `drawai-ppt` 检查真实导出文件，交付 PPTX、预览和本次制作需要的源文件，并说明实际检查结果与已知差异。

## 模板界面与环境

模板选择通过 `drawai_show_templates` 呈现在支持 MCP Apps 的对话内。独立模板网页使用同一份真实目录，选择后可复制说明到 Codex。

创建与编辑 PPT 需要 Python 3.12+ 及 `drawai-ppt/scripts/requirements.txt` 中的依赖。预览需要 LibreOffice 和 Poppler；公式转换需要 Pandoc。具体准备和制作命令见 `drawai-ppt`。
