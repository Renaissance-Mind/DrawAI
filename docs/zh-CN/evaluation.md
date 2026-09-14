# DrawAI 评测

**简体中文** | [English](../en/evaluation.md) | [DrawAI](../../README.md)

对最终 SVG 的还原性与可编辑性进行评测，共 **39 项指标：9 项 Rule 规则指标和 30 项 Rubric 裁判指标**。
评测代码已包含在 DrawAI 的 `main` 分支中，使用独立的 `drawai_evaluation` 包。
评测已有 SVG 不需要运行 DrawAI 生成流程，也不需要部署本地 SAM/OCR 服务。

数据集：[caopu/DrawAI-Bench-Lite](https://huggingface.co/datasets/caopu/DrawAI-Bench-Lite)。
这是一个独立数据集，包含知识图谱、海报、演示文稿和科学图表四类共 80 张原始图像及其元素标注，
样本 ID 连续编号为 `0001` 至 `0080`。图像路径为 `images/0001.png` 至 `images/0080.png`，
对应标注为 `annotations/0001.json` 至 `annotations/0080.json`。
领域和来源类型记录在元数据中，不通过目录名区分。

## 输入要求

**你需要提供待评方法生成的最终 SVG。** 每张 SVG 对应数据集中的一个 `bench_id`。
一个方法与模型配置的完整评测包含 80 张 SVG；也可以先评测已完成的子集，结果中会记录覆盖情况。

| 文件或参数 | 谁提供 | 用途 |
|---|---|---|
| 原始参考图像 | 下载的数据集 | 视觉还原目标 |
| GT 元素标注 JSON | 下载的数据集 | 元素类型、文本、几何形状与位置 |
| 最终候选 `.svg` | 待评方法 | 还原后的外观及可编辑对象结构 |
| 单图 ID 或批量 SVG 目录 | 用户 | 将预测结果匹配到数据集样本 |
| 内部候选清单 | 评测器自动生成 | 记录匹配的 ID 与 SVG 路径 |
| 候选 `rendered.png` | 评测器自动生成 | 与参考图进行视觉比较 |

评测器通过 Chromium 渲染候选 SVG。Rule 指标比较渲染后的像素和解析出的 SVG 对象；
Rubric 裁判读取参考图、GT JSON、最终 SVG 和渲染 PNG。
无需额外提供候选 PNG、生成日志或应用中间文件，也无需重新运行 SAM/OCR。
其他方法生成的标准 SVG 同样可评测，不强制包含 DrawAI 专用元素 ID。

完整的 39 项指标需要 SVG 输入。PNG/JPEG 不包含计算可编辑性所需的对象结构。
本包不直接解析 PPTX、PDF 或 DrawIO，请先导出为 SVG；此时分数描述的是导出后的 SVG。
导出时应保留可编辑文本和矢量对象，整图栅格化会丢失这些结构。

## 安装

需要 Linux 或 macOS、Python 3.12，以及一个基于 Chromium 的浏览器。
在 DrawAI 仓库根目录安装评测可选依赖。下文所有命令均在该目录、激活环境后执行：

```bash
uv sync --locked --extra evaluation
source .venv/bin/activate
```

也可以在已安装 Python 3.12 的环境中使用 pip：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install --pre -e '.[evaluation]'
```

建议使用 `uv sync --locked`，以安装 `uv.lock` 中记录的精确依赖版本。
评测与 DrawAI 共用兼容的基础依赖，`evaluation` 可选依赖补充图像评分和数据下载所需组件。
Rubric 通过 **Codex Python SDK** 执行，版本为 `openai-codex==0.1.0b3`，
默认裁判为 **`gpt-5.6-sol`，推理强度 `high`**。9 项 Rule 指标使用本地 Python 计算和 Chromium 渲染。

基准评测使用 Codex CLI 0.144.4。完整评测前先安装并登录；只运行 `--rule-only` 时可跳过这一步：

```bash
npm install --prefix .runtime @openai/codex@0.144.4
.runtime/node_modules/.bin/codex login
```

评测器会自动发现仓库下的 `.runtime` 安装，也可使用 `PATH` 中的 `codex`，
通过环境变量 `DRAWBENCH_CODEX_BIN` 配置，或显式传入 `--codex-bin`。
裁判每次尝试会将已登录用户的 `~/.codex/auth.json` 复制到临时 home，并在结束后清理。
认证文件位于其他目录时使用 `--host-codex-home`。不要把凭证写入候选清单或结果归档。

Chrome、Chromium 或 Edge 会自动发现；可通过 `DRAWAI_SVG_RENDERER_BROWSER` 指定浏览器可执行文件。

## 数据集

```bash
drawai-dataset download --local-dir data/DrawAI-Bench-Lite
drawai-dataset verify --local-dir data/DrawAI-Bench-Lite
```

完成一次配置后，评测命令无需再次指定数据集。查找顺序为显式 `--dataset`、
环境变量 `DRAWAI_EVALUATION_DATASET`、当前目录下的 `data/DrawAI-Bench-Lite`、
固定版本的 Hugging Face 缓存。默认本地副本需要匹配已发布的数据集版本。
若没有可用的当前版本数据，评测器会自动从 Hugging Face 下载图像和标注。
数据存放在其他位置时，可配置一次环境变量：

```bash
export DRAWAI_EVALUATION_DATASET=/path/to/DrawAI-Bench-Lite
```

默认数据集版本为 `2.0.0`，固定 revision 为 `711808882430bb59526e89218f6621baa1dda4d0`。
可在 `drawai-dataset download` 中通过 `--revision <dataset-commit>` 选择其他快照。
原图保留原始分辨率；标注 JSON 的 `canvas` 定义元素坐标系，评分前会将参考图缩放至该画布。
验证命令检查原图与标注的校验和。下载命令在新文件通过验证后，更新受管理文件，
并移除已不在新 manifest 中且未经本地修改的旧文件。

## 单图评测

指定样本 ID 和最终 SVG 路径即可：

```bash
drawai-evaluate --id 0001 --svg ./result.svg
```

ID 使用数据集的四位编号，`--id 1` 也会解析为 `0001`。
单图模式下 SVG 文件名可以任意命名；不存在的样本 ID 会报错。

命令会打印结果目录，完整评测结束后显示 Overall、Reconstruction、Editability、Rule 和 Rubric 分数。
只计算确定性的 Rule 指标时：

```bash
drawai-evaluate --id 0001 --svg ./result.svg --rule-only
```

## 批量评测

将最终 SVG 放在同一平级目录，文件名与数据集 ID 一致。
例如，`images/0001.png` 对应 `predictions/0001.svg`：

```text
predictions/
  0001.svg
  0002.svg
  ...
  0080.svg
```

随后只需指定目录：

```bash
drawai-evaluate --svg-dir ./predictions
```

批量文件名必须保留四位编号的前导零。只匹配精确的样本文件名；
其他 SVG（例如素材文件）会列为忽略项。

只把已经完成的 SVG 放到对应路径。缺失样本会跳过并列入 `coverage.json`，
因此可以先评测已完成的部分，后续有新结果时重复执行同一命令。
已存在但格式错误的 SVG 会报错；尚未完成的输出应使用临时文件名。
如果要求 80 个样本全部齐全：

```bash
drawai-evaluate --svg-dir ./predictions --require-all
```

## 参数与执行

`--dataset`、`--output-root`、`--method` 和 `--model` 均可省略。
默认输出位置为当前目录下的 `results/<input-name>-<hash>`；相同输入路径与标签会生成稳定目录名，支持复用。
默认方法与模型标签分别为 `candidate` 和 `unspecified`。需要区分实验时：

```bash
drawai-evaluate --svg-dir ./predictions \
  --method my-method --model my-model --output-root results/my-experiment
```

`--model` 仅标记生成候选 SVG 的模型，不改变 Rubric 裁判。
裁判默认仍为 `gpt-5.6-sol`，推理强度 `high`。

图像和字体资源应嵌入 SVG，或确保相对 SVG 所在目录能解析本地引用。
远程资源应先嵌入以保证可复现。资产审计会记录缺失的本地图像，评测以实际提交内容的渲染结果为准。

默认 Rule 并发 8、Rubric 并发 40、最多尝试 3 次、每次超时 1800 秒。
通过 `--rule-concurrency` 与 `--rubric-concurrency` 调整并发，Rubric 支持 1 至 150 个 worker。
需要与基准结果比较时保持 `--reasoning-effort high`。
评测器会冻结已完成候选的快照，进行渲染和规则计算，根据 GT 元素选择所需裁判组，
仅合并通过完整验证的候选。每个输出目录有独立锁，防止重复启动同一批次。

新增已完成预测后重复运行同一命令即可增量评测，未变化的 Rule 结果及通过严格验证的 Rubric 结果会复用。
标注、SVG、参考图、渲染图或本地引用资源变化时，只使受影响的证据失效。
裁判触发用量限制时返回退出码 75，请等到报告的重试时间再继续。
其他非零退出会在 `sdk_runs/<group>/attempt_*` 下保留诊断信息，不会用零分补齐缺失结果。

## 高级清单输入

对于任意文件布局或同时包含多个方法与模型配置的评测，可以使用清单：

```bash
drawai-evaluate --candidates candidates.jsonl
```

JSONL 每行包含四位 `bench_id`、SVG 路径、标签和完成状态：

```json
{"bench_id":"0001","method":"my-method","model":"my-model","candidate_svg":"predictions/0001.svg","status":"completed"}
```

路径可以是绝对路径，或相对于清单文件的路径。仅评测 `completed` 条目。
`(bench_id, method, model)` 必须唯一，标签必须非空且不能包含路径分隔符。
也支持 JSON 数组或包含 `candidates` 数组的 JSON 对象。
`--svg`、`--svg-dir` 和 `--candidates` 三种输入模式互斥。

## 输出与分数

每个候选包含 `rendered.png`、`rule_based_eval.json`、`rule_provenance.json`、
`rubric/*.json`、`sdk_runs/`，以及恰好含 39 项指标的 `full_evaluation.json`。
输出根目录包含 `input_candidates.json`、`coverage.json`、候选快照、资产审计、任务清单、
调度摘要、指标目录，以及长表和宽表格式的对比 CSV。
Rubric 运行中的部分合并结果仅包含所有必需裁判组均通过 schema 与来源验证的候选。

`coverage.json` 区分已找到和缺失的样本。
合并摘要中的 `partial` 字段表示所选预测的评分完成度，不代表部分预测目录已覆盖全部 80 个样本。

```bash
drawai-scores --evaluation-root results/my-experiment
```

汇总输出 0 至 100 分的 Overall（总体）、Reconstruction（还原性）、Editability（可编辑性）、
Rule（规则）和 Rubric（裁判）分数。MSE 类指标通过 `1 - score` 转为越高越好；
不适用指标不计入均值。先对每个候选的适用指标取均值，再对候选等权平均。
这些是基准评分，不是分类准确率百分比。不同配置应在相同样本集合上比较，部分结果须同时报告覆盖率。

裁判证据仅限 GT JSON、参考图、最终 SVG 和渲染 PNG，每个相关 GT 元素都要评分。
文本内容、整图视觉相似性与对象可编辑性使用各自对应指标。
只有 schema、元素覆盖、输入哈希、输出哈希和 SDK 完成状态一致，Rubric 任务才算完成。

## 开发与验证

```bash
uv sync --locked --extra evaluation --extra dev
source .venv/bin/activate
pytest -q tests/evaluation tests/test_drawai_project_naming.py
```

`src/drawai_evaluation/` 包含 Rule 评分器、隔离的 Rubric 调度器、Chromium 渲染器、批处理入口、
数据集加载器、结果合并器和分数聚合器，测试位于 `tests/evaluation/`。
全部 39 项指标见[指标说明](evaluation-metrics.md)，
稳定的机器可读指标 ID 见[双语 JSON 目录](../evaluation/metric_catalog.json)。
