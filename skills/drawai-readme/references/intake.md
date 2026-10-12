# 需求确认与规划请求

默认保留当前 Session 的 Agent 配置。只询问尚缺的参考、页数、比例与实际输入；用户已指定图像来源或执行方法时沿用。图像生成可以采用宿主工具、用户 API、已有页面或本地真实排版。API 图像生成不改变最终制作 Agent。

```json
{
  "environment": {
    "context": "session",
    "agent": "claude",
    "model": "用户本轮实际模型",
    "model_source": "session_metadata",
    "image_generation_available": true,
    "image_viewing_available": true,
    "local_execution_available": true,
    "image_api_available": null,
    "flow_available": null,
    "agent_config": {}
  },
  "preferences": {
    "reference": "project",
    "page_count": 10,
    "aspect_ratio": "16:9",
    "mode": "auto",
    "image_generation": "auto",
    "implementation_agent": "current",
    "skip_questions": false
  },
  "inputs": {
    "pptx_templates": ["/actual/project/template.pptx"],
    "reference_images": [],
    "visual_page_count": 0
  }
}
```

示例中的 Agent、模型与路径须替换成真实值。`context` 可为 session、workbench、cli、server，缺省为 session；Session 默认 Skill，独立运行默认 Flow。`model_source` 可为 session_metadata、host_display、user、unknown。未知能力为 null，不按模型名称猜测。

`mode` 可为 auto、skill、flow。`image_generation` 可为 auto、session、api、local；指定 `image_connection` 即选择该 API。统一工具从共同配置解析连接和凭据是否已提供，不声称连接已通过网络调用测试。pure Python `create_plan` 使用请求中给定事实。

`implementation_agent` 缺省在 Session 为 current，在独立环境为 configured。用户明确指定其他 Agent 时填实际标识，并核实 `external_agent_available`。默认制作不启动子进程。用户指定另一个模型时，在相应宿主配置或显式执行命令中应用，不能把全局默认模型当作本轮会话模型。

返回包括 `design`、`implementation`、`decisions`、`questions`、`blockers` 和 `ready_to_start`。`implementation.configuration_source="caller_session"` 表示沿用当前 Agent 的实际配置。所缺能力形成阻塞，不自动切换执行者。

Session 用户明确选择 Flow 时，`agent` 或 `agent_config.selected_provider_id` 必须提供真实执行后端身份。Claude/Codex 身份映射为对应 CLI，已知模型与推理参数形成 `implementation.flow_agent_settings`，提交时原样作为本任务 `agent_settings`。用户要求工作台自行选择时使用 configured；该任务使用工作台配置。

完整页面图片直接采用输入数量和比例。`skip_questions` 或 `workflow_specified` 为 true 时不返回偏好问题；必要输入或工具缺失仍要明确处理。
