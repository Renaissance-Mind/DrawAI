# 模板库

按 [drawai-design](../SKILL.md) 的当前任务选择参考。整体流程见 [drawai-readme](../../drawai-readme/SKILL.md)。

## 推荐与展示

根据用户给出的主题、受众、页面用途、信息量与视觉偏好查询 `drawai_templates`：

- `action: search`：按关键词、`category` 和 `with_images` 查找真实目录；用 `offset`、`limit` 翻页。
- `action: recommend`：返回按关键词相关度排序的候选。结合模板图片、`prompt_recipe`、场景与结构标签判断适配性；相关度排序不代表设计质量或人工评审结果。
- `action: get` 与 `template_id`：读取完整设计配方、原图 URL、哈希和来源说明。

给出与当前任务相关的少量候选，说明适合的页面与取舍。调用 `drawai_show_templates`，传入候选的 `template_ids`，或使用 `query`、`category` 筛选。该工具关联可内嵌的模板界面；用户可以查看详情、选择多个参考和指定信息结构或视觉风格。浏览全部模板时不必先要求用户确定风格。

目录包含有真实图片的视觉参考与只有设计配方的条目。以工具返回的实际字段说明参考形式。用户提供的 PPTX 文件在设计阶段检查、渲染并按用途匹配页面。

## 接收选择并制作

界面“用于当前任务”将 `drawai.template-selection.v1` 交回当前对话。读取每个条目的 `template_id` 和 `role`；以目录详情核实参考。独立网页提供同样的选择说明，用户可以复制到对话中。

需要图片用于生成或重建时，调用 `drawai_prepare_template`，传入模板 ID 和当前任务的 `output_directory`。工具下载目录中真实的原图并校验 SHA-256，返回本地图片路径与 `template-reference.json`。查看图片，保留结构、配色、版式与来源记录，再按 `drawai-design` 确定页面图像。设计配方条目会返回说明文件，图片列表为空。

参考用途以用户选择为准。参考图中的示例文案和数值仅用于说明呈现方式；实际内容来自当前任务材料。不同页面可使用适合各自用途的参考，不把某张封面的布局套到全部内容页。

## 工具与网页

模板相关工具是 `drawai_templates`、`drawai_show_templates` 和 `drawai_prepare_template`。不支持内嵌界面的宿主可用工具返回的详情与真实图片继续选型。

在源码仓库中，也可以使用 `node apps/workbench/templates/cli.mjs <工具名> @参数.json` 执行相同操作。独立模板网站由 `apps/workbench` 中的 `npm run build:templates` 生成，部署静态目录或通过 HTTP 打开后可浏览和复制参考选择。
