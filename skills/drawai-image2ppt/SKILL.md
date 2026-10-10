---
name: drawai-image2ppt
description: 把已经确定的页面图像转成可编辑 PowerPoint。支持 Workbench 中的 DrawAI-Flow 和当前会话 Skill 两种模式，按当前模型与工具能力给出默认路由；包含原生 PPT 构建、编辑、导出和检查工具包。
---

# DrawAI Image2PPT

在 DrawAI 插件中使用时，先阅读 [drawai-readme](../drawai-readme/SKILL.md)，沿用已经确认的模式。输入是 [drawai-design](../drawai-design/SKILL.md) 确定的页面图像，或用户直接提供的完整页面图像。本阶段负责实际 PPT 构建、原生对象编辑、导出、检查与制作源交付。独立复制本目录的工具包时，可直接使用其 Python API／CLI 和用户已经指定的转换方式。

## 输入与模式

先验证 `drawai.visual-deck.v1` 清单，按保存的页序与原图处理：

```bash
python "$SKILL_DIR/scripts/visual_deck.py" verify visual-deck.json
```

只提供图片时先登记清单；已有可编辑 PPTX 的明确局部修改可直接进入原生编辑流程。模板和视觉设计需要改变时回到 `drawai-design` 更新输入，不暗中改动已确定的内容。

| 模式 | 执行方式 |
| --- | --- |
| DrawAI-Flow | 将图像提交现有 Workbench，由其配置的流程、处理器与模型完成解析、素材处理、重建和导出，工作台显示实际阶段进度 |
| Skill | 在当前会话看图、编写和执行本地重建代码，调用本技能工具包创建与检查 PPT，不启动另一个 Agent 进程处理视觉理解 |

默认使用 `drawai-readme/scripts/plan.py` 或 `drawai_plan` 的路由：GPT 5.6+、Claude 5+、DeepSeek Flash v4.1+ 使用 Skill，其余或版本未知使用 Flow。用户明确选择优先；Skill 需要看图与本地执行能力，Flow 需要现有 Workbench 与已配置的运行环境。模型名单只是默认执行策略，不能替代实际文件验收。

## DrawAI-Flow

先确认 Workbench 可连接、所需处理器与 Agent 配置可用。默认浏览器入口是 `http://127.0.0.1:5174/`，API 是 `http://127.0.0.1:8890`；使用当前安装配置的实际地址。启动和首次模型准备遵循仓库运行文档，不重建 Studio 项目服务。

有 `drawai_flow` 时使用以下操作：

1. `status` 不带批次 ID，检查当前连接与实际健康信息。
2. `submit` 传入 `visual_manifest`，上传经过验证的页面图像，返回本任务的排队批次与 Workbench 地址；提交本身不代表转换成功。
3. 用户指定在工作台手动操作时打开该入口继续。用户要求直接制作或已经确定执行流程时调用 `start`，执行本任务的批次，随后用 `status` 查看真实进度。出现失败或等待素材审阅时处理实际原因；不要把请求发送成功当成成品。
4. 全部页面完成后调用 `export`，传入本任务的 `batch_id` 和新的 `output_path`，下载完整 PPTX，再按下述文件验收检查。

只有使用本任务提交结果中的批次 ID 才能启动或导出。`DRAWAI_WORKBENCH_API_URL` 与 `DRAWAI_WORKBENCH_UI_URL` 配置服务地址；本地 Python 路径可用 `DRAWAI_PYTHON` 指定。没有 MCP 时，可在 Workbench 上传相同图像并执行，或使用现有 REST API／CLI 完成同一流程。

## 当前会话 Skill

查看每页原图与已知文字、数据，拆分文字、形状、连线、表格、图表和复杂局部素材。简单结构用原生对象；照片、复杂插画与纹理可用局部原图裁剪。需要可编辑的内容按对象重建，不能把整页图像当成最终 PPT 背景。

保持确定的画布、相对位置、样式、分组与层叠顺序。有真实原始数据时使用数据构建图表；只有曲线图片时记录无法恢复的精确数据与近似。用户 PPTX 模板的格式要求通过实际模板解析与原生结构处理。

文档使用 `presentation.document.v1`，以 pt 作为位置、尺寸、字号与线宽单位；96 DPI 下像素坐标统一乘 0.75。可写文档 JSON，或用 Python 构造页面对象。将重建与修改的实现、素材处理和导出源保存在任务目录。

```bash
python "$SKILL_DIR/scripts/ppt.py" export deck.document.json --pptx output/v1/deck.pptx --svg-dir output/v1/svg --report output/v1/export.json
```

文档 API 与图片重建、PPTX 原生修改、SVG 插入流程分别见 [文档 API](references/document-api.md) 和 [制作与编辑](references/workflows.md)。复杂素材见 [素材](references/visual-assets.md)，属性条件见 [实现矩阵](references/implementation-capabilities.md)。实际实现与扩展方法见 [代码指南](references/code-map.md)。

## 环境与验证

使用 Python 3.12+，安装本目录 `scripts/requirements.txt`。LibreOffice 与 Poppler 用于真实 PPTX 渲染和 SVG 导出；LaTeX 转 Office Math 需要 Pandoc。字体必须可用，报告记录实际字体替代。预览默认忽略临时渲染副本的嵌入字体引用，交付原件保留嵌入字体；需要原字体渲染时使用 `--embedded-fonts preserve`。

```bash
python "$SKILL_DIR/scripts/ppt.py" validate output/v1/deck.pptx
python "$SKILL_DIR/scripts/ppt.py" inspect output/v1/deck.pptx --output output/v1/inventory.json
python "$SKILL_DIR/scripts/ppt.py" render output/v1/deck.pptx --output-dir output/v1/preview
```

两种模式都检查实际 PPTX：页数、页序、尺寸、文字与数据、可编辑对象、引用关系，以及预览中的断行、裁剪、遮挡、连线与模板一致性。发现问题后在新版本目录修正并重新导出。模板复制、备注或原生 XML 编辑涉及结构时，目标 PowerPoint 可用则实际打开，确认没有修复提示；不具备该环境时说明实际完成的检查。

最终交付 PPTX、页面预览、视觉图像清单，以及所用脚本、文档源、素材、相关数据和转换报告。Flow 的完整运行包和 Skill 的文档模型保留各自实际来源；统一阶段输入与交付，不把内部数据格式差异伪装成同一种运行记录。
