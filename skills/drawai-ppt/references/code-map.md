# Python 代码扩展指南

仓库是这套 skill 的代码依赖，以下路径均相对于 DrawAI 根目录。skill 的脚本只是一个稳定入口；业务逻辑集中在可测试的 Python 模块中。

| 位置 | 职责 |
| --- | --- |
| `skills/drawai-ppt/scripts/ppt.py` | 定位 checkout 并调用 Python CLI，支持任意 Agent 和工作目录 |
| `src/drawai/pptx_cli.py` | `create`、`inspect`、`edit`、`schema`、`validate`、`render` 命令与 JSON 输出 |
| `src/drawai/pptx_editing.py` | 创建/编辑计划、PPT 对象清单、原生对象操作、模板复制、SVG 插入、包验证及渲染 |
| `src/drawai/svg_to_ppt.py` | SVG 规范化、原生转换适配和 LaTeX → Office Math |
| `src/drawai/_vendor/svg_pptx_converter/svg_to_pptx/` | 几何路径、文字、样式、分组与图片的 DrawingML 生成 |
| `src/drawai/tooling.py` | DrawAI Agent 工具注册；`drawai tool ppt` 与独立脚本使用同一引擎 |
| `tests/test_pptx_editing.py` | 真实 PPTX 对象和模板编辑回归 |
| `tests/test_drawai_ppt_skill.py` | 创建文稿和独立 skill 入口行为验证 |

## 为具体需求选择实现

普通创建或编辑任务先使用计划与现有 Python API。需要更精细的用户指定效果时，先查实际依赖版本中的 `python-pptx` 类和属性，再决定使用任务制作脚本还是扩展共用引擎。SVG 部分复用现有转换器；没有可靠映射的结构要在输出中保留实际语义和已验证能力。

可复用的新能力集中到共用引擎。一次性内容、位置和配色放在任务计划或制作脚本中。不要为某份演示文稿的固定内容硬编码引擎分支。

## 增加计划操作

1. 在 `pptx_editing.py` 定义 `StrictModel` 子类，用唯一的 `op: Literal[...]` 描述操作，声明实际参数并加入 `Operation` 联合类型。
2. 在 `_apply_operation` 中操作真实 PPT 对象。需要页面或对象时使用 `_slide`、`_shape`；图片素材通过 `_asset` 解析。输入错误直接暴露，不静默忽略。
3. 创建和编辑共用 `_execute_plan`，因此新操作同时可用于两条流程。`PptxCreatePlan` 与 `PptxEditPlan` 自动提供当前 JSON Schema。
4. 更新受影响的 CLI/tool 帮助、流程参考和实际使用说明。
5. 对有意义的行为编写真实文件回归：生成 PPTX、重新打开、检查对象类型/属性/数据、源文件保留和引用完整性。需要视觉保真时再渲染对照。测试不使用伪造的导出器或图片内容。

## 模板与 XML 的易错点

- 对象 ID 属于页面，复制页可以保留原 ID；在同页插入新图形要重新分配对象 ID。
- 插入 SVG 需要重新关联图片的 `rId`，还要设置分组外框与子坐标框。整页 XML 不直接替换模板页。
- `python-pptx` 的普通 shape 列表会省略 `mc:AlternateContent`。Office Math 等对象需要保留实际绘图树中的兼容性节点和命名空间。
- 复制页面时图表、内嵌工作簿和备注的可变内容需要独立复制；共用母版、版式和图片资源可保留引用。
- 全文本赋值可能改变文字 run 的格式。局部替换保留 run 属性；重建段落时明确继承哪些属性。
- 新文件在全部操作和包验证完成后发布。生成原件副本，避免覆盖源文件、编辑计划或已存在的输出。

## 验证和维护

```bash
uv run --extra dev python -m pytest \
  tests/test_drawai_ppt_skill.py tests/test_pptx_editing.py \
  tests/test_semantic_ppt_svg_to_ppt.py tests/test_pptx_inspector.py
```

对实际修改运行相关检查，通过后继续完成交付；只有新修改、失败或未解决的问题才需要追加检查。新能力要通过当前 skill 入口在实际文件上执行一次，并查看最终预览。

源码开发遵循仓库 `AGENTS.md`：默认直接在 `main` 开发，不新建分支或 worktree；代码修改提交 Conventional Commit，推送默认只到 `origin`。只有用户明确要求公开同步时才推送 `public`。PPT 制作产生的计划、素材和预览放在任务目录，避免混入无关源码提交。
