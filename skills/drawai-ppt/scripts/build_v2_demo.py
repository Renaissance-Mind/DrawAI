#!/usr/bin/env python3
"""Reconstruct two established demo figures with editable native objects.

Input PNGs are reference pictures, not backgrounds in the resulting slides.
The fourth formula page is imported from the established vector formula demo.
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pptx_skill.document import Document, export_pptx
from pptx_skill.document.importer import import_svg
from pptx_skill.document.svg import export_svg

HERE = Path(__file__).resolve().parents[1]
BLUE = "#2F80C9"
DARK = "#193A55"
GRAY = "#576B7B"
LIGHT = "#EFF7FD"
TEAL = "#2FAFAC"


def box(id, x, y, w, h, fill="#FFFFFF", line="none", preset="rect", extra=None):
    p = {
        "object.frame": {"left": x, "top": y, "width": w, "height": h},
        "shape.geometry.preset": preset,
        "paint.kind": "solid",
        "paint.solid.color": fill,
        "stroke.paint": line,
        "stroke.width": 0.8,
    }
    p.update(extra or {})
    if p["paint.kind"] != "solid":
        p.pop("paint.solid.color", None)
    return {"id": id, "kind": "shape", "properties": p}


def text(id, x, y, w, h, value, size=13, color=DARK, bold=False, extra=None):
    p = {
        "object.frame": {"left": x, "top": y, "width": w, "height": h},
        "text.run.font.latin": "Arial",
        "text.run.font.east_asian": "PingFang SC",
        "text.run.font.size": size,
        "text.run.font.bold": bold,
        "text.run.fill": color,
        "text.body.insets": {"left": 0, "right": 0, "top": 0, "bottom": 0},
        "text.body.wrap": "square",
        "text.body.autofit": "none",
        "text.body.paragraphs": [
            {
                "properties": {
                    "text.paragraph.line_spacing": {"mode": "ratio", "value": 1.05}
                },
                "content": [{"kind": "run", "text": line}],
            }
            for line in value.split("\n")
        ],
    }
    p.update(extra or {})
    return {"id": id, "kind": "text_box", "properties": p}


def line(id, x1, y1, x2, y2, color=BLUE, width=2, arrow=False, extra=None):
    p = {
        "object.frame": {
            "left": min(x1, x2),
            "top": min(y1, y2),
            "width": max(abs(x2 - x1), 0.05),
            "height": max(abs(y2 - y1), 0.05),
        },
        "object.flip_horizontal": x2 < x1,
        "object.flip_vertical": y2 < y1,
        "connector.geometry": "straight",
        "stroke.paint": color,
        "stroke.width": width,
    }
    if arrow:
        p.update(
            {
                "stroke.end_arrow.kind": "triangle",
                "stroke.end_arrow.width": "med",
                "stroke.end_arrow.length": "med",
            }
        )
    p.update(extra or {})
    return {"id": id, "kind": "connector", "properties": p}


def chart(id, kind, x, y, w, h, categories, series):
    return {
        "id": id,
        "kind": "chart",
        "properties": {
            "object.frame": {"left": x, "top": y, "width": w, "height": h},
            "chart.type": {"column": "barChart", "line": "lineChart"}[kind],
            "chart.categories": categories,
            "chart.series": series,
            "chart.legend": {"visible": False},
            "chart.series.style": [
                {"index": 0, "fill": BLUE, "stroke": {"width": 2, "paint": BLUE}}
            ],
        },
    }


def figure():
    o = [
        text("fig-title", 32, 20, 850, 38, "DrawAI Demo Figure", 28, bold=True),
        text(
            "fig-subtitle",
            33,
            60,
            850,
            25,
            "Synthetic test image for local SAM3 + OCR + SVG reconstruction",
            13,
            GRAY,
        ),
    ]
    for id, x, y in [("a", 32, 104), ("b", 488, 104), ("c", 32, 340), ("d", 488, 340)]:
        o.append(
            box(
                "panel-" + id,
                x,
                y,
                440,
                220,
                "#FFFFFF",
                "#CAD8E3",
                extra={
                    "effects.outer_shadow": {
                        "blur": 2,
                        "distance": 1,
                        "direction": 90,
                        "color": {"kind": "rgb", "channels": "193A55", "alpha": 0.06},
                    }
                },
            )
        )
    o.extend(
        [
            text(
                "a-title",
                48,
                117,
                390,
                25,
                "A  Signal recovery over time",
                16,
                bold=True,
            ),
            text(
                "b-title",
                504,
                117,
                390,
                25,
                "B  Editable region classes",
                16,
                bold=True,
            ),
            text("c-title", 48, 354, 390, 25, "C  Pipeline smoke path", 16, bold=True),
            text(
                "d-title",
                504,
                354,
                390,
                25,
                "D  Mixed assets for OCR / crops",
                16,
                bold=True,
            ),
        ]
    )
    values = [0.19, 0.29, 0.22, 0.42, 0.56, 0.47, 0.65, 0.88, 0.73, 0.74, 0.91]
    o.append(
        chart(
            "signal-chart",
            "line",
            58,
            150,
            392,
            160,
            [str(i) for i in range(11)],
            [{"name": "signal", "values": values}],
        )
    )
    o[-1]["properties"]["chart.axes"] = [
        {"index": 1, "scale": {"minimum": 0, "maximum": 1}, "major_unit": 0.2}
    ]
    o.append(text("peak-label", 308, 150, 134, 25, "detected peak", 11, BLUE))
    o.append(line("peak-arrow", 354, 170, 326, 194, BLUE, 1.2, True))
    o.append(
        chart(
            "regions-chart",
            "column",
            510,
            150,
            398,
            160,
            ["text", "shape", "crop", "nobg"],
            [{"name": "regions", "values": [74, 58, 38, 26]}],
        )
    )
    o[-1]["properties"]["chart.axes"] = [
        {"index": 1, "scale": {"minimum": 0, "maximum": 80}, "major_unit": 20}
    ]
    for j, (label, fill) in enumerate(
        [
            ("Input", "#E8F1FB"),
            ("SAM3", "#D4EBFB"),
            ("OCR", "#D3F3E6"),
            ("SVG", "#FDE3B9"),
        ]
    ):
        x = 55 + j * 102
        o.append(box("step-" + str(j), x, 409, 80, 64, fill, "#7296AD", "roundRect"))
        o.append(
            text(
                "step-label-" + str(j),
                x,
                431,
                80,
                20,
                label,
                16,
                bold=True,
                extra={
                    "text.body.vertical_anchor": "ctr",
                    "text.body.paragraphs": [
                        {
                            "properties": {"text.paragraph.alignment": "ctr"},
                            "content": [{"text": label}],
                        }
                    ],
                },
            )
        )
        if j < 3:
            o.append(
                line(
                    "pipeline-arrow-" + str(j), x + 84, 442, x + 99, 442, DARK, 2, True
                )
            )
    o.append(
        text(
            "pipeline-goal",
            55,
            504,
            390,
            27,
            "Goal: semantic SVG + PPTX smoke export",
            12,
            GRAY,
        )
    )
    for j, (cx, cy, r, fill) in enumerate(
        [
            (560, 432, 27, "#C4F2F5"),
            (603, 443, 31, "#76D9E5"),
            (572, 477, 22, "#A4E8ED"),
        ]
    ):
        o.append(
            box(
                "mixed-circle-" + str(j),
                cx - r,
                cy - r,
                2 * r,
                2 * r,
                fill,
                TEAL,
                "ellipse",
            )
        )
    o.extend(
        [
            line("mixed-arrow", 629, 452, 681, 452, "#D65353", 2, True),
            text("callout-title", 693, 410, 201, 23, "Callouts", 17, bold=True),
            text(
                "callout-text",
                693,
                442,
                205,
                92,
                "• text remains editable\n• arrows stay vectors\n• crops keep fidelity",
                12,
                GRAY,
            ),
            text(
                "figure-footer",
                32,
                577,
                888,
                18,
                "Source: the established demo_figure.png · rebuilt with editable chart, text and shape objects",
                10,
                GRAY,
            ),
        ]
    )
    return {
        "id": "figure",
        "properties": {
            "slide.name": "Demo figure reconstruction",
            "slide.background": "#F8FBFE",
        },
        "objects": o,
    }


def workflow():
    o = [
        text("workflow-title", 30, 20, 870, 40, "Agent 工作流架构", 28, bold=True),
        text(
            "workflow-subtitle",
            31,
            67,
            870,
            25,
            "Agent 需要在意图识别、检索增强、工具调用和引用回溯之间保持状态。",
            14,
            GRAY,
        ),
    ]
    bullets = [
        "文档接入、知识治理、权限边界是进入工作流前的基础。",
        "RAG 检索提供上下文，工具调用处理结构化操作。",
        "引用回溯保留证据链，人工反馈用于持续评估。",
        "数值如出现仅为测试样例，不代表真实业务结果。",
    ]
    o.append(
        text(
            "workflow-bullets",
            33,
            109,
            865,
            91,
            "\n".join("✓ " + s for s in bullets),
            12,
            GRAY,
        )
    )
    labels = ["用户问题", "意图识别", "检索增强", "工具调用", "答案生成", "引用回溯"]
    captions = [
        "业务域：合同管理\n文档范围：制度、流程、模板\n语言：中文",
        "理解用户意图\n提取关键实体与约束条件",
        "在企业文档体系中检索\n相关内容，构建增强上下文",
        "调用内置工具或系统接口\n执行结构化操作",
        "基于上下文与工具结果\n生成准确、可验证的答案",
        "关联证据来源，保留证据链\n支持回溯与审计",
    ]
    states = ["input", "intent", "context", "tool_result", "draft_answer", "evidence"]
    for j, label in enumerate(labels):
        x = 31 + j * 151
        o.append(
            box(
                "workflow-card-" + str(j),
                x,
                230,
                139,
                185,
                "#FFFFFF",
                "#B8D4E8",
                "roundRect",
            )
        )
        o.append(
            box(
                "workflow-number-" + str(j), x + 9, 241, 23, 23, BLUE, "none", "ellipse"
            )
        )
        o.append(
            text(
                "workflow-number-label-" + str(j),
                x + 9,
                246,
                23,
                17,
                str(j + 1),
                10,
                "#FFFFFF",
                True,
                extra={
                    "text.body.paragraphs": [
                        {
                            "properties": {"text.paragraph.alignment": "ctr"},
                            "content": [{"text": str(j + 1)}],
                        }
                    ]
                },
            )
        )
        o.append(
            text("workflow-label-" + str(j), x + 38, 244, 98, 23, label, 14, bold=True)
        )
        # Native symbols stay editable; these simplify the reference page's decorative icons.
        o.append(
            box(
                "workflow-icon-" + str(j),
                x + 56,
                282,
                30,
                30,
                "#E7F4FD",
                BLUE,
                [
                    "wedgeRoundRectCallout",
                    "ellipse",
                    "rect",
                    "roundRect",
                    "foldedCorner",
                    "hexagon",
                ][j],
            )
        )
        o.append(
            text(
                "workflow-caption-" + str(j),
                x + 10,
                328,
                121,
                61,
                captions[j],
                10.5,
                GRAY,
            )
        )
        o.append(
            text(
                "workflow-state-" + str(j),
                x + 10,
                394,
                123,
                15,
                "state: " + states[j],
                8.5,
                BLUE,
            )
        )
        if j < 5:
            o.append(
                line(
                    "workflow-forward-" + str(j),
                    x + 141,
                    304,
                    x + 149,
                    304,
                    BLUE,
                    2.5,
                    True,
                )
            )
    o.append(
        line(
            "workflow-trace",
            51,
            426,
            910,
            426,
            BLUE,
            0.8,
            False,
            {"stroke.dash_preset": "dash"},
        )
    )
    o.append(
        text(
            "workflow-trace-label",
            313,
            432,
            330,
            19,
            "trace：状态与引用证据全程保留",
            11,
            BLUE,
        )
    )
    o.append(
        box("workflow-feedback", 767, 461, 151, 88, "#F5FBF6", "#86BE94", "roundRect")
    )
    o.append(
        text("workflow-feedback-title", 780, 473, 123, 23, "7  人工反馈", 14, bold=True)
    )
    o.append(
        text(
            "workflow-feedback-text",
            780,
            503,
            123,
            37,
            "评估质量与引用准确性\n修正意见或补充信息",
            10,
            GRAY,
        )
    )
    o.append(line("workflow-feedback-loop", 822, 451, 227, 451, "#58A575", 1.5, True))
    o.append(
        text(
            "workflow-feedback-caption",
            249,
            462,
            488,
            20,
            "反馈闭环：持续优化意图理解与检索效果",
            11,
            "#4F9470",
        )
    )
    for j, (label, content) in enumerate(
        [
            ("知识治理", "统一接入 · 元数据 · 版本管理"),
            ("权限边界", "角色访问 · 最小权限 · 边界校验"),
            ("持续评估", "人工评分 · 问题标注 · 知识与工具优化"),
        ]
    ):
        x = 31 + j * 242
        o.append(
            box(
                "workflow-foundation-" + str(j),
                x,
                495,
                229,
                64,
                LIGHT,
                "#CBDFEE",
                "roundRect",
            )
        )
        o.append(
            text(
                "workflow-foundation-title-" + str(j),
                x + 12,
                504,
                205,
                20,
                label,
                12,
                bold=True,
            )
        )
        o.append(
            text(
                "workflow-foundation-content-" + str(j),
                x + 12,
                533,
                205,
                17,
                content,
                9.5,
                GRAY,
            )
        )
    o.append(
        text(
            "workflow-footer",
            31,
            580,
            900,
            16,
            "Source: established developer_docs / Agent 工作流架构 demo · all content objects remain editable",
            9,
            GRAY,
        )
    )
    return {
        "id": "workflow",
        "properties": {
            "slide.name": "Agent workflow reconstruction",
            "slide.background": "#FFFFFF",
            "notes.content": "根据已有 Agent 工作流架构 demo 重建。装饰图标简化为 PowerPoint 原生形状。",
        },
        "objects": o,
    }


def styles():
    o = [
        text(
            "styles-title",
            32,
            22,
            860,
            40,
            "统一模型：富文本、渐变与箭头",
            27,
            bold=True,
        ),
        text(
            "styles-subtitle",
            33,
            68,
            870,
            25,
            "同一份 Python 文档数据导出原生 PPTX 与静态 SVG；长度单位为 pt。",
            13,
            GRAY,
        ),
    ]
    rich = text(
        "rich-text",
        40,
        124,
        425,
        175,
        "",
        15,
        extra={
            "text.body.insets": {"left": 12, "right": 12, "top": 12, "bottom": 12},
            "text.body.paragraphs": [
                {
                    "properties": {
                        "text.paragraph.line_spacing": {"mode": "ratio", "value": 1.3},
                        "text.paragraph.space_after": {"mode": "points", "value": 12},
                        "text.paragraph.first_line_indent": 18,
                    },
                    "content": [
                        {
                            "text": "混合样式：",
                            "properties": {"text.run.font.bold": True},
                        },
                        {
                            "text": "蓝色字间距",
                            "properties": {
                                "text.run.fill": BLUE,
                                "text.run.letter_spacing": 1.2,
                            },
                        },
                        {
                            "text": "、下划线",
                            "properties": {"text.run.underline.type": "dbl"},
                        },
                        {
                            "text": "与上标 2",
                            "properties": {
                                "text.run.baseline_shift": 0.3,
                                "text.run.font.size": 11,
                            },
                        },
                    ],
                },
                {
                    "properties": {
                        "text.paragraph.left_margin": 18,
                        "text.paragraph.first_line_indent": -12,
                        "text.paragraph.bullet.kind": "character",
                        "text.paragraph.bullet.character": "•",
                        "text.paragraph.space_after": {"mode": "points", "value": 8},
                    },
                    "content": [{"text": "段前段后、首行与悬挂缩进"}],
                },
                {
                    "properties": {"text.paragraph.alignment": "r"},
                    "content": [
                        {
                            "text": "右对齐 / 独立段落样式",
                            "properties": {"text.run.font.italic": True},
                        }
                    ],
                },
            ],
        },
    )
    o.append(box("rich-panel", 33, 110, 440, 202, LIGHT, "#C9DEEF", "roundRect"))
    o.append(rich)
    for j, k in enumerate(["linear", "circle", "rect", "shape"]):
        x = 505 + (j % 2) * 203
        y = 111 + (j // 2) * 109
        o.append(
            box(
                "gradient-" + k,
                x,
                y,
                184,
                92,
                extra={
                    "paint.kind": "gradient",
                    "paint.gradient.kind": k,
                    "paint.gradient.angle": 35,
                    "paint.gradient.stops": [
                        {
                            "position": 0,
                            "color": {"kind": "rgb", "channels": "244E9B", "alpha": 1},
                        },
                        {"position": 0.5, "color": "#49B8CF"},
                        {"position": 1, "color": "#F3DAAC"},
                    ],
                    "paint.gradient.fill_to_rect": {
                        "l": 0.5,
                        "t": 0.5,
                        "r": 0.5,
                        "b": 0.5,
                    },
                    "effects.outer_shadow": {
                        "blur": 4,
                        "distance": 2,
                        "direction": 45,
                        "color": {"kind": "rgb", "channels": "17354D", "alpha": 0.16},
                    },
                },
            )
        )
        o.append(
            text("gradient-label-" + k, x + 9, y + 9, 166, 24, k, 13, "#FFFFFF", True)
        )
    for j, k in enumerate(["triangle", "stealth", "diamond", "oval", "arrow", "none"]):
        x = 50 + (j % 3) * 301
        y = 361 + (j // 3) * 92
        o.append(
            text("arrow-label-" + k, x, y, 271, 21, k + " · sm / med / lg", 12, GRAY)
        )
        for index, size in enumerate(["sm", "med", "lg"]):
            o.append(
                line(
                    "arrow-" + k + "-" + size,
                    x + 10,
                    y + 35 + index * 13,
                    x + 255,
                    y + 35 + index * 13,
                    BLUE,
                    1.7,
                    False,
                    {
                        "stroke.end_arrow.kind": k,
                        "stroke.end_arrow.width": size,
                        "stroke.end_arrow.length": size,
                        "stroke.cap": "rnd",
                    },
                )
            )
    o.append(
        text(
            "style-footer",
            33,
            581,
            876,
            18,
            "SVG 为静态视觉投影；动画、图表工作簿和媒体播放语义保存在 PPTX / 源模型中。",
            10,
            GRAY,
        )
    )
    return {"id": "styles", "properties": {"slide.background": "#FFFFFF"}, "objects": o}


def build(output, renderer=None):
    output.mkdir(parents=True, exist_ok=True)
    document = Document.model_validate(
        {
            "schema": "presentation.document.v1",
            "id": "drawai-v2-demo",
            "properties": {
                "document.page_size": {"width": 960, "height": 610},
                "document.metadata.title": "DrawAI V2 editable demos",
                "document.metadata.author": "DrawAI",
            },
            "pages": [figure(), workflow(), styles()],
        }
    )
    document.save(output / "demo.document.json")
    report = {
        "pptx": export_pptx(document, output / "demo.pptx"),
        "svg": export_svg(document, output / "svg", renderer=renderer),
    }
    formula, imported = import_svg(HERE / "assets/demo/formula.svg", padding=3)
    formula.save(output / "formula.document.json")
    report["formula"] = {
        "import": imported,
        "pptx": export_pptx(formula, output / "formula.pptx"),
        "svg": export_svg(formula, output / "formula-svg", renderer=renderer),
    }
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument("--renderer")
    a = p.parse_args()
    print(json.dumps(build(a.output_dir, a.renderer), ensure_ascii=False, indent=2))
