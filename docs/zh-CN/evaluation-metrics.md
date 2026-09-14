# 评测指标

**简体中文** | [English](../en/evaluation-metrics.md) | [评测指南](evaluation.md)

共 39 项指标：9 项 Rule 和 30 项 Rubric。

| 一级 | 二级 | 指标 | 计算方式 | 方法 | 方向 |
|---|---|---|---|---|---|
| 还原性 | 整图视觉还原 | 结构匹配 | SSIM | rule | 越高越好 |
| 还原性 | 整图视觉还原 | 边缘对齐 | Edge F1 | rule | 越高越好 |
| 还原性 | 整图视觉还原 | 像素误差 | MSE | rule | 越低越好 |
| 还原性 | 整图视觉还原 | 整体可读性 | VLM Score | rubric | 越高越好 |
| 还原性 | 整图视觉还原 | 布局骨架 | Layout QA | rubric | 越高越好 |
| 还原性 | 整图视觉还原 | 视觉层级 | Hierarchy QA | rubric | 越高越好 |
| 还原性 | 文本保真度 | 文本内容 | Text F1 | rule | 越高越好 |
| 还原性 | 文本保真度 | 位置与行列 | Layout QA | rubric | 越高越好 |
| 还原性 | 文本保真度 | 对齐与间距 | Layout QA | rubric | 越高越好 |
| 还原性 | 文本保真度 | 溢出遮挡 | Occlusion QA | rubric | 越高越好 |
| 还原性 | 文本保真度 | 色彩强调 | Style QA | rubric | 越高越好 |
| 还原性 | 文本保真度 | 字体观感 | Style QA | rubric | 越高越好 |
| 还原性 | 文本保真度 | 样式一致性 | Style QA | rubric | 越高越好 |
| 还原性 | 图像保真度 | 图像区域 | Region MSE | rule | 越低越好 |
| 还原性 | 图像保真度 | 图像对齐 | Image mIoU | rule | 越高越好 |
| 还原性 | 公式保真度 | 符号保留 | Formula QA | rubric | 越高越好 |
| 还原性 | 公式保真度 | 结构关系 | Formula QA | rubric | 越高越好 |
| 还原性 | 公式保真度 | 位置可读性 | Formula QA | rubric | 越高越好 |
| 还原性 | Shape 保真度 | 存在覆盖 | Shape QA | rubric | 越高越好 |
| 还原性 | Shape 保真度 | 视觉属性 | Shape QA | rubric | 越高越好 |
| 还原性 | Shape 保真度 | 相邻关系 | Shape QA | rubric | 越高越好 |
| 还原性 | 连接线保真度 | 路径存在 | Connector QA | rubric | 越高越好 |
| 还原性 | 连接线保真度 | 端点方向 | Connector QA | rubric | 越高越好 |
| 还原性 | 连接线保真度 | 线型干扰 | Connector QA | rubric | 越高越好 |
| 还原性 | 表格保真度 | 网格结构 | Table QA | rubric | 越高越好 |
| 还原性 | 表格保真度 | 内容归属 | Table QA | rubric | 越高越好 |
| 还原性 | 表格保真度 | 可读对齐 | Table QA | rubric | 越高越好 |
| 可编辑性 | 文本可编辑性 | 文本框 | Box Recall | rule | 越高越好 |
| 可编辑性 | 图像组件可编辑性 | 图像源对象 | Image Recall | rule | 越高越好 |
| 可编辑性 | Shape 可编辑性 | 对象独立性 | VLM-QA | rubric | 越高越好 |
| 可编辑性 | Shape 可编辑性 | 框位置 | BBox QA | rubric | 越高越好 |
| 可编辑性 | Shape 可编辑性 | 冲突诊断 | VLM-QA | rubric | 越高越好 |
| 可编辑性 | 连接线可编辑性 | 独立路径 | VLM-QA | rubric | 越高越好 |
| 可编辑性 | 连接线可编辑性 | 端点控制 | VLM-QA | rubric | 越高越好 |
| 可编辑性 | 连接线可编辑性 | 误合并检查 | VLM-QA | rubric | 越高越好 |
| 可编辑性 | 公式可编辑性 | 可编辑表示 | Object Recall | rule | 越高越好 |
| 可编辑性 | 表格可编辑性 | 独立表格区域 | VLM-QA | rubric | 越高越好 |
| 可编辑性 | 表格可编辑性 | 可编辑网格 | VLM-QA | rubric | 越高越好 |
| 可编辑性 | 表格可编辑性 | 文本归属 | VLM-QA | rubric | 越高越好 |

原始 MSE 分数越低越好，汇总时通过 `1 - score` 归一化为越高越好。
GT 中不存在对应元素类型时，该指标标记为 `not_applicable`，分数为 null，不计入均值。
先对单个候选的适用指标取均值，再对候选等权平均，最终以 0 至 100 分显示。

稳定的指标 ID、Rule 键和 Rubric 组映射见[双语 JSON 目录](../evaluation/metric_catalog.json)。
