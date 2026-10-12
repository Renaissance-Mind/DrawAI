---
name: drawai-readme
description: DrawAI 的 Session 制作入口。图像可使用宿主能力或用户配置的 API；最终制作默认保留当前 Agent 的模型和配置，调用统一核心完成设计、转换与检查。
---

# DrawAI

读取用户需求、材料和当前项目，明确输入是内容、参考图、完整页面图片还是已有 PPTX。DrawAI 安装一次，Session、Workbench 和 CLI 使用同一套核心、模板、配置与工具。

## 制作流程

| 技能 | 职责 |
| --- | --- |
| drawai-readme | 读取材料，检查看图、执行和图像工具，补齐内容需求 |
| drawai-design | 选择参考，确定页序与内容，生成或登记真实页面图片 |
| drawai-image2ppt | 重建或编辑原生对象，导出 PPTX/SVG，检查并交付 |

从材料制作：读取内容 → 选择参考 → 确定页面图片 → 转换 → 检查。已有完整页面图片时直接核对和登记；已有 PPTX 的局部修改进入原生编辑；只选模板时进入模板库。

## 当前 Agent 与图像来源

最终制作默认由当前会话 Agent 执行，沿用其真实模型、推理配置、认证和工具权限。Claude 会话由当前 Claude 执行，Codex 会话由当前 Codex 执行，其他具备相应能力的宿主同样处理。模型名称或版本未知时继续保留当前 Agent；缺少看图或代码执行能力时说明缺项，不能自行启动另一个 Agent 或转交工作台。

图像生成与最终制作分别选择。用户指定图像 API 或连接时使用该选择；否则优先使用会话本身的图像工具。宿主缺少图像能力时，可使用已配置的 Images API、已有图片或有实际渲染能力的本地排版。外接图像 API 不改变最终制作 Agent。

Images API 连接与 Workbench/CLI 共用。用 `drawai config connections --import connections.json` 配置，或在 Workbench 设置中新增；用 `drawai config image --source api --connection <真实ID>` 设默认。执行实际图片生成/编辑时可调用 `drawai_image`，或 `drawai image generate/edit`；使用宿主图像工具时直接调用当前宿主提供的工具。

只有用户明确选择另一个 Agent、模型或 DrawAI-Flow 时才改变对应执行选择。用户明确要求另一个 CLI Agent 时，使用 `drawai session execute --agent claude|codex --prompt-file <任务文件> --workdir <任务目录>`；只有明确指定模型才传 `--model`。其他宿主可使用 custom 命令适配。执行器沿用所选 Agent 的配置与权限。

## 规划与提问

用 `drawai_plan` 或 `drawai plan request.json` 传入真实会话环境与已知偏好。`environment.agent` 来自宿主身份；`model` 与 `model_source` 来自本轮实际信息，未知时如实记录。规划器保留当前会话，图像来源可为 `auto/session/api/local`，用户明确选择优先。完整输入和返回契约见 [需求确认](references/intake.md)。执行策略见 [执行策略](references/model-policy.json)。

只补齐尚缺的参考、页数、比例和实际输入。已经提供的要求直接沿用；默认当前 Agent 的实施方式无需再次询问。明确不要提问或已指定流程时，采用已知信息及合理默认值：页面图像数量或 8 页，已知比例或 16:9。具体缺少的文件、凭据或工具必须暴露。

## 明确选择 Flow

用户选择 Flow 后，连接同一安装的 Workbench 或明确的远程地址。Session 提交时将规划结果 `implementation.flow_agent_settings` 作为 `drawai_flow.submit.agent_settings`，把真实当前 Agent 类型和已知模型参数保留为本任务配置，不覆盖工作台全局配置。执行主机使用自己的认证；不复制当前会话密钥。无法确认当前 Agent 类型时，需要用户提供身份或明确选择工作台已配置 Agent。

用户明确选择工作台 Agent 时传 `preferences.implementation_agent="configured"`。独立 Workbench/CLI 默认读取共同配置中的执行后端。Flow 提交、执行、查询和导出后，仍须检查实际文件。

## 核心与交付

工具使用统一安装的 `drawai`：`drawai visual save/verify` 管理图像清单，`drawai presentation` 制作、导出、检查与渲染文档，`drawai ppt create/edit` 保留现有原生操作计划。Python API 从 `pptx_skill` 导入；实现只有一份，旧技能脚本是兼容入口。

交付真实 PPTX、已检查的预览、页面图像与清单、制作源、素材和报告。事实与数据来自用户材料或查证来源。首次安装与依赖启用见仓库安装文档；可用 `drawai doctor` 检查同一环境。
