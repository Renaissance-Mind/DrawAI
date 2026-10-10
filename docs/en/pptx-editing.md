# Edit PPTX templates

DrawAI uses Python to inspect and edit existing PPTX files and save a new deck. SVG insertions reuse DrawAI's native DrawingML converter, including editable shapes, text, local pictures and Office Math. This path does not require OpenAI Artifact Tool or image reconstruction models.

Use `drawai ppt create --plan create-plan.json --output deck.pptx` to create a new deck with `drawai.pptx_create_plan.v1`. Creation and editing share native operations; `add_text` and `add_shape` add text boxes and preset shapes. The [drawai-image2ppt skill](../../skills/drawai-image2ppt/SKILL.md) provides the standalone agent workflow and implementation extension guide.

```bash
uv run drawai ppt inspect template.pptx --output template.json
uv run drawai ppt schema > edit-plan.schema.json
uv run drawai ppt edit template.pptx \
  --plan edit-plan.json --output edited.pptx --report edit-report.json
```

The inventory contains the source SHA256, slide size, layouts across all masters, slide-local shape IDs, text, tables, charts and pictures. Slides are **1-based**; table row/column indexes are **0-based**. Positions and font sizes use **96 DPI pixels**. Group children expose `parent_shape_id` and use group coordinates; the group's `child_frame` describes the mapping to its outer frame.

Use IDs from the actual inventory. Asset paths are relative to the plan file; image references inside SVGs are relative to the SVG file. The Python API accepts an explicit `asset_root`, defaulting to the source deck's directory.

```json
{
  "schema": "drawai.pptx_edit_plan.v1",
  "operations": [
    {"op": "replace_text", "slide": 1, "shape_id": 2,
     "find": "Original title", "text": "Research method"},
    {"op": "add_svg", "slide": 1, "path": "diagrams/method.svg",
     "frame": {"left": 80, "top": 180, "width": 600, "height": 320},
     "fit": "contain"}
  ]
}
```

Optional `source_sha256` rejects a stale plan after the template changes. The editor requires a new output filename and leaves source files intact. Unknown operations, missing targets/assets, invalid parameters and invalid chart data fail explicitly. It publishes the new file only after all edits, XML/relationship validation and a successful reopen.

The inventory identifies Office Math and other preserved compatibility objects. They are not editable through the ordinary text API. Retain them or insert a new formula through SVG LaTeX metadata; formula conversion requires Pandoc, and edit reports record conversion/fallback counts. Inventory and report destinations must also be new `.json` files.

## Operations

| Operation | Purpose |
| --- | --- |
| `add_text` | Add a native text box with `frame`, `text`, optional `style` and `name` |
| `add_shape` | Add a native preset shape with `geometry`, `frame`, fill, line and optional text |
| `replace_text` | Replace `find` with `text` within paragraphs, including matches spanning runs; retain existing run formatting |
| `set_text` | Replace the full text frame, retaining corresponding paragraph properties and each paragraph's first-run style; optional `style` |
| `replace_image` | Replace picture `path`; `fit: preserve` keeps placement/crop, `cover` recomputes centered crop |
| `set_table_cells` | Update native table `cells` with `row`, `column`, `text` and optional `style` |
| `set_chart_data` | Update native chart `data`, retaining chart type and style |
| `set_geometry` | Update `frame` and optional `rotation` in degrees |
| `set_style` | Update RGB `fill`, `line_color`, pixel `line_width`, and `text_style`; fills/lines also accept `none` |
| `add_svg` | Insert native grouped SVG objects in `frame`, with `contain` or `stretch` and optional `name` |
| `add_image` | Insert a picture in `frame`, using `contain` or `cover` |
| `add_table` | Create a native table from rectangular `values`, with `frame` and optional text `style` |
| `add_chart` | Create a native chart from `chart_type`, `data` and `frame` |
| `add_slide` | Append a slide using an existing `layout_id` |
| `duplicate_slide` | Append a copy of `slide`, cloning mutable chart/workbook/notes parts so later edits are independent |

Text styles accept `font_family`, `font_size`, `bold`, `italic`, `underline`, six-digit RGB `color`, `alignment`, `vertical_alignment`, `line_spacing` and `word_wrap`. Unspecified attributes retain their existing values. For mixed-format text, prefer `replace_text`; `set_text` formats new content with the template paragraph's first-run style.

Category chart data has `categories` and `series: [{name, values}]`, with one value per category. Scatter series use `points: [[x,y], ...]`; bubble series use `[[x,y,size], ...]`. New charts support `column`, `bar`, `line`, `area`, `pie`, `doughnut`, `scatter` and `bubble`. Data editing requires native charts/tables, not pictures of them.

## Verify the actual export

```bash
uv run drawai ppt validate edited.pptx
uv run drawai ppt render template.pptx --output-dir before-preview
uv run drawai ppt render edited.pptx --output-dir after-preview
```

Inspection and editing also accept `--preview-dir`. Rendering uses LibreOffice `soffice` and Poppler `pdftoppm`, discovered on PATH or set through `--renderer` and `--rasterizer`. It uses an isolated LibreOffice profile and produces PDF and per-slide PNG files. Preview directories must be empty to prevent stale images.

Package checks validate XML and internal references. Compare rendered output with the source to check wrapping, crop and layout. PowerPoint-specific features need verification in the target PowerPoint environment; Python and SVG conversion retain their own support limits.

## Agent and Python interfaces

```bash
uv run drawai tool help ppt --json
uv run drawai tool ppt inspect template.pptx --output template.json
uv run drawai tool ppt edit template.pptx --plan edit-plan.json --output edited.pptx
```

The tool and direct CLI share the editor. Agents inspect real objects and previews, produce a plan against the JSON Schema, then edit and render. The existing `run_drawai_tool` interface can invoke the same registered tool.

```python
from drawai.pptx_editing import inspect_pptx, edit_pptx

inventory = inspect_pptx("template.pptx")
# plan contains verified IDs and follows drawai.pptx_edit_plan.v1.
report = edit_pptx("template.pptx", plan, "edited.pptx", asset_root="assets")
```
