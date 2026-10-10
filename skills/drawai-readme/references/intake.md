# 需求确认与规划请求

## 确认模板

先读已有需求，只保留未确定的项目。把尖括号替换为实际判断，不把模板原样发送给用户。

```text
当前环境：<图像生成工具可用／不可用／已有完整页面图像>；图像转 PPT 推荐 <Skill／DrawAI-Flow>。

1. 参考：<使用项目模板／从模板库挑选参考／不使用参考图>？
2. 页面：<建议 8 页、16:9；已确定的页数或比例直接写明，只询问缺失部分>。
3. 转换：<推荐模式>，还是 <另一种模式>？
   Skill：当前会话按图像重建对象、导出和检查 PPT。
   DrawAI-Flow：提交 Workbench，用工作台已配置的流程与模型解析、重建和导出。
```

例如用户说“按项目模板做 10 页，16:9，直接用 Skill”，参考、细节和模式都已确定，直接开始。用户说“按这个流程做，别问我”时直接采用已有信息与合理默认值。已经提供完整页面图像时，不再询问是否重新选择视觉参考；页数按图像数量确定。

用户只说“帮我做一套关于某主题的 PPT”时，先读可用材料与环境，再合并询问上述缺失偏好。明确回复前不把推荐项当作用户已经选择。对于无法继续的真实输入空缺，提出具体问题，不反复询问已确定偏好。

## 规划器的输入

```json
{
  "environment": {
    "model": "gpt-5.6",
    "model_source": "session_metadata",
    "image_generation_available": true,
    "image_viewing_available": true,
    "local_execution_available": true,
    "flow_available": null
  },
  "preferences": {
    "reference": "project",
    "page_count": 10,
    "aspect_ratio": "16:9",
    "mode": "skill",
    "skip_questions": false,
    "workflow_specified": true
  },
  "inputs": {
    "pptx_templates": ["/actual/project/template.pptx"],
    "reference_images": [],
    "visual_page_count": 0,
    "visual_aspect_ratio": null
  }
}
```

这是接口结构示例，模型标识和路径必须换成当前真实值。`model_source` 可为 `session_metadata`、`host_display`、`user` 或 `unknown`。能力字段可为布尔值或 `null`，不能把未知当作可用。

`reference` 可为 `project`、`provided`、`library`、`none`，未确定时省略。`mode` 可为 `auto`、`skill`、`flow`。未确定的页数和比例省略。`visual_page_count` 只统计已经确定的完整页面图像，不统计普通参考素材。

规划器返回 `decisions`、`questions`、`blockers` 与 `ready_to_start`。明确模式优先于模型策略，已有输入自动补齐相应事实。`skip_questions` 或 `workflow_specified` 为真时不返回偏好问题。只有问题为空、必要能力无阻塞时才能进入相应执行阶段。
