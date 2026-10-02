#!/usr/bin/env python3
"""Populate concrete choices and render the property matrix from its catalog."""

from __future__ import annotations

import csv
import json
from pathlib import Path


REFERENCES = Path(__file__).resolve().parents[1] / "references"
DML = "schemas_openxmlformats_org_drawingml_2006_main.json"
PML = "schemas_openxmlformats_org_presentationml_2006_main.json"
CHART = "schemas_openxmlformats_org_drawingml_2006_chart.json"
DIAGRAM = "schemas_openxmlformats_org_drawingml_2006_diagram.json"

NATIVE_ENUMS = {
    "layout.type": (PML, "SlideLayoutValues"),
    "placeholder.type": (PML, "PlaceholderValues"),
    "placeholder.orientation": (PML, "DirectionValues"),
    "placeholder.size_hint": (PML, "PlaceholderSizeValues"),
    "object.black_white_mode": (DML, "BlackWhiteModeValues"),
    "shape.geometry.preset": (DML, "ShapeTypeValues"),
    "shape.geometry.path_fill": (DML, "PathFillModeValues"),
    "text.run.underline.type": (DML, "TextUnderlineValues"),
    "text.run.strike": (DML, "TextStrikeValues"),
    "text.run.capitalization": (DML, "TextCapsValues"),
    "text.paragraph.alignment": (DML, "TextAlignmentTypeValues"),
    "text.paragraph.font_alignment": (DML, "TextFontAlignmentValues"),
    "text.body.vertical_anchor": (DML, "TextAnchoringTypeValues"),
    "text.body.wrap": (DML, "TextWrappingValues"),
    "text.body.vertical_mode": (DML, "TextVerticalValues"),
    "text.body.vertical_overflow": (DML, "TextVerticalOverflowValues"),
    "text.body.horizontal_overflow": (DML, "TextHorizontalOverflowValues"),
    "paint.gradient.path_kind": (DML, "PathShadeValues"),
    "paint.gradient.flip": (DML, "TileFlipValues"),
    "paint.pattern.preset": (DML, "PresetPatternValues"),
    "paint.image.tile_alignment": (DML, "RectangleAlignmentValues"),
    "paint.image.tile_flip": (DML, "TileFlipValues"),
    "stroke.cap": (DML, "LineCapValues"),
    "stroke.compound": (DML, "CompoundLineValues"),
    "stroke.alignment": (DML, "PenAlignmentValues"),
    "stroke.dash_preset": (DML, "PresetLineDashValues"),
    "stroke.start_arrow.kind": (DML, "LineEndValues"),
    "stroke.start_arrow.width": (DML, "LineEndWidthValues"),
    "stroke.start_arrow.length": (DML, "LineEndLengthValues"),
    "stroke.end_arrow.kind": (DML, "LineEndValues"),
    "stroke.end_arrow.width": (DML, "LineEndWidthValues"),
    "stroke.end_arrow.length": (DML, "LineEndLengthValues"),
    "three_d.camera.preset": (DML, "PresetCameraValues"),
    "three_d.light_rig.preset": (DML, "LightRigValues"),
    "three_d.light_rig.direction": (DML, "LightRigDirectionValues"),
    "three_d.material": (DML, "PresetMaterialTypeValues"),
    "table.cells.vertical_anchor": (DML, "TextAnchoringTypeValues"),
    "table.cells.text_direction": (DML, "TextVerticalValues"),
    "table.cells.overflow": (DML, "TextHorizontalOverflowValues"),
    "chart.blank_values": (CHART, "DisplayBlanksAsValues"),
    "smartart.direction": (DIAGRAM, "DirectionValues"),
    "animation.fill_mode": (PML, "TimeNodeFillValues"),
    "transition.speed": (PML, "TransitionSpeedValues"),
}

# Semantic discriminators are finite choices of different native structures,
# not claims that an attribute with the same name exists in both formats.
SEMANTIC_ENUMS = {
    "document.orientation": ["portrait", "landscape"],
    "document.layout_direction": ["ltr", "rtl"],
    "object.kind": ["text_box", "shape", "connector", "group", "picture", "table", "chart", "smartart", "equation", "audio", "video", "model3d", "ink", "ole", "control", "web_extension", "zoom", "live_feed"],
    "shape.geometry.path_fill_rule": ["nonzero", "evenodd"],
    "connector.geometry": ["straight", "elbow", "curved"],
    "text.paragraph.bullet.kind": ["none", "character", "auto_number", "picture"],
    "paint.kind": ["none", "solid", "gradient", "pattern", "image", "group_inherit"],
    "color.kind": ["rgb", "scrgb", "hsl", "scheme", "system", "preset"],
    "paint.gradient.kind": ["linear", "circle", "rect", "shape"],
    "paint.image.mode": ["stretch", "tile"],
    "stroke.join": ["miter", "round", "bevel"],
    "picture.aspect_fit": ["contain", "cover", "stretch"],
    "math.display_mode": ["inline", "display"],
    "math.alignment": ["left", "center", "right", "center_group"],
    "media.kind": ["audio", "video", "narration"],
    "animation.behavior": ["entrance", "emphasis", "exit", "motion_path", "property", "command", "media"],
    "zoom.kind": ["slide", "section", "summary"],
    "interaction.event": ["click", "hover"],
    "interaction.navigation_action": ["next_slide", "previous_slide", "first_slide", "last_slide", "last_viewed_slide", "end_show", "named_slide", "custom_show"],
    "slideshow.kind": ["speaker", "window", "kiosk"],
    "embedded.kind": ["ole", "embedded_package", "activex_control", "web_extension"],
    "embedded.display_mode": ["content", "icon"],
}


def native_choices(inventory, file, name):
    matches = [item for item in inventory["enums"] if item["schema_file"] == file and item["sdk_name"] == name]
    if len(matches) != 1:
        raise ValueError(f"Ambiguous or missing source enum: {file}/{name}")
    item = matches[0]
    return [value["wire_value"] for value in item["values"]], item["type"]


def domain_mapping(row):
    domain = row["domain"]
    pptx = "PPTX 可表示；精确 XML 字段和参数条件仍需逐项绑定。"
    svg = "SVG 可表达对应外观；本行的布局、语义或参数转换需实现。"
    if domain in {"document", "notes", "package_policy", "review"}:
        svg = "主要为 metadata；静态 SVG 不提供对应的放映、包、审阅或安全行为。"
    if domain == "theme":
        svg = "解析主题和继承后生成外观；不保留 PowerPoint 母版/版式编辑语义。"
    if domain in {"animation", "transition"}:
        svg = "静态 SVG 不执行动画、切换和导航；只能存描述或静态预览。"
    if domain in {"three_d", "media", "embedded"}:
        svg = "静态预览或渲染结果；不提供 3D 编辑、媒体播放、实时源或对象激活。"
    if domain in {"table", "chart", "smartart", "math"}:
        svg = "需要专门布局后绘制；不具有相同的原生表格/图表/SmartArt/公式编辑接口。"
    if domain in {"paragraph", "text_body"}:
        svg = "按段落/文本框设置计算断行和位置；需验证字体、换行及艺术字/3D 等效果。"
    if domain == "effects":
        svg = "部分可用 filter；效果和混合算法需逐项验证，不能统一声明等价。"
    return pptx, svg


def enrich(catalog, inventory):
    for row in catalog["properties"]:
        identifier = row["id"]
        row["pptx_mapping"], row["svg_mapping"] = domain_mapping(row)
        row["value_source"] = "结构参数或数值；见类型/单位和原生记录"
        row["allowed_values"] = []
        row["allowed_value_labels"] = {}
        row["native_enum"] = None
        if row["value_type"] == "enum":
            if identifier in NATIVE_ENUMS:
                file, name = NATIVE_ENUMS[identifier]
                row["allowed_values"], native_type = native_choices(inventory, file, name)
                declaration = next(item for item in inventory["enums"] if item["schema_file"] == file and item["sdk_name"] == name)
                row["native_enum"] = {"schema_file": file, "sdk_name": name, "type": native_type}
                row["allowed_value_labels"] = {value["wire_value"]: value["sdk_name"] for value in declaration["values"]}
                row["value_source"] = f"原生枚举 {native_type}（{file}）"
            elif identifier in SEMANTIC_ENUMS:
                row["allowed_values"] = SEMANTIC_ENUMS[identifier]
                row["value_source"] = "统一语义选项；导出时映射到不同原生结构"
            elif identifier == "transition.kind":
                values = sorted({field["wire_name"] for field in inventory["properties"]
                                 if field["schema_file"] == PML and field["sdk_class"] == "Transition"
                                 and field["kind"] == "element" and field["wire_name"] not in {"p:sndAc", "p:extLst"}})
                row["allowed_values"] = values + ["p159:morph", "none"]
                row["value_source"] = "Transition 的原生效果子元素；Morph 来自 MS-PPTX"
            elif identifier == "transition.direction":
                values = []
                for name in ("TransitionSlideDirectionValues", "TransitionCornerDirectionValues", "TransitionInOutDirectionValues", "DirectionValues"):
                    choices, _ = native_choices(inventory, PML, name)
                    values.extend(choices)
                row["allowed_values"] = list(dict.fromkeys(values))
                row["value_source"] = "多个原生方向枚举的并集；按具体切换效果限制"
            elif identifier == "chart.type":
                row["allowed_values"] = sorted({field["wire_name"].split(":")[-1] for field in inventory["properties"]
                    if field["schema_file"] == CHART and field["sdk_class"] == "PlotArea" and field["kind"] == "element"
                    and field["wire_name"].split(":")[-1].endswith("Chart")}) + ["combo", "histogram", "pareto", "boxWhisker", "waterfall", "funnel", "treemap", "sunburst", "regionMap"]
                row["value_source"] = "经典 PlotArea 图表子元素 + 现代 chartEx 布局类型；子类型另有参数"
            else:
                raise ValueError(f"No concrete choices for {identifier}")
            row["value_description"] = " / ".join(
                f"{value}（{row['allowed_value_labels'][value]}）" if value in row["allowed_value_labels"] else value
                for value in row["allowed_values"])
        elif row["value_type"] == "boolean":
            row["allowed_values"] = [False, True]
            row["value_description"] = "false / true；未设置另行保留缺省行为"
        elif row["value_type"] in {"ratio", "signed_ratio"}:
            row["value_description"] = "有限数值；" + ("0–1" if row["canonical_unit"] in {"0..1", "ratio"} and row["value_type"] == "ratio" else "具体值域按该属性的原生约束，不能全部假定为 0–1")
        elif row["value_type"] in {"length", "signed_length", "angle", "duration", "integer"}:
            row["value_description"] = f"{'整数' if row['value_type']=='integer' else '有限数值'}；单位 {row['canonical_unit']}；允许负值/上下限需按属性确认"
        elif row["value_type"] in {"text", "id", "guid", "language_tag"}:
            row["value_description"] = {"text": "字符串", "id": "稳定标识字符串", "guid": "GUID", "language_tag": "语言标签，如 zh-CN / en-US"}[row["value_type"]]
        else:
            row["value_description"] = f"结构参数 `{row['value_type']}`；不是单个固定枚举"
        parameters = {
            "size": "{width, height}；有限数值，尺寸需满足原生正值约束",
            "rect": "{left, top, width, height}；位置可为负，尺寸需满足原生约束",
            "point": "{x, y}；数值和单位见本行",
            "insets": "{left, top, right, bottom}；有限数值，单位见本行",
            "signed_insets": "{left, top, right, bottom}；允许负值，具体边界按原生字段",
            "matrix": "{a, b, c, d, e, f}；完整仿射矩阵，平移单位见映射",
            "spacing": "{mode: points或ratio, value: 有限数值}；固定值与相对倍数分别保存",
            "gradient_stop[]": "[{offset: 0–1, color: 颜色对象}]；位置有序，允许同位置色标形成突变",
            "tab_stop[]": "[{position: pt, alignment: l/ctr/r/dec}]；左/居中/右/小数点对齐",
            "path_command[]": "moveTo / lineTo / quadBezierTo / cubicBezierTo / arcTo / close；点为路径局部数值或公式",
            "autofit": "{mode: none/shrink_text/grow_shape}；shrinking 另带文字缩放和行距缩减参数",
            "time_value": "毫秒数值 / automatic / indefinite；不同时间字段分别限制",
            "dash[]": "[{dash, gap}]；相对线宽的长度，非负；需确认目标格式单位",
            "color_components": "rgb/scRGB/HSL/主题/系统/预设颜色的通道或原生代码；由 color.kind 限定",
        }
        if row["value_type"] in parameters:
            row["value_description"] = parameters[row["value_type"]]

        if identifier.startswith("stroke.") and "_arrow." in identifier:
            end = "headEnd" if identifier.startswith("stroke.start_arrow.") else "tailEnd"
            attribute = {"kind": "type", "width": "w", "length": "len"}[identifier.rsplit(".", 1)[-1]]
            row["pptx_mapping"] = f"原生 `a:{end}/@{attribute}`；支持本行全部原生取值。"
            row["svg_mapping"] = "用 marker-start/marker-end 的矢量几何表达形状，并用 markerWidth/markerHeight、viewBox 和 markerUnits 控制尺寸；宽/长没有同名三档枚举，需按形状、线宽和变换映射并标定。"
            row["exporter_status"] = "not_implemented_in_unified_exporters"
            labels = {"sm": "窄" if attribute == "w" else "短", "med": "中", "lg": "宽" if attribute == "w" else "长", "none": "无", "triangle": "三角", "stealth": "燕尾", "diamond": "菱形", "oval": "椭圆", "arrow": "开放箭头"}
            row["allowed_value_labels"] = labels
            row["value_description"] = " / ".join(f"{value}（{labels[value]}）" for value in row["allowed_values"])
        if identifier.startswith("paint.gradient."):
            row["pptx_mapping"] = "DrawingML gradFill：线性 lin 和 circle/rect/shape 路径渐变及色标等参数。"
            row["svg_mapping"] = "linear/circle 可用 linearGradient/radialGradient；rect/shape 没有直接同型原生渐变，需专门渲染或近似，不能统一标为完全支持。"
        if identifier == "text.paragraph.alignment":
            row["svg_mapping"] = "l/ctr/r 可用 text-anchor/定位；just/justLow/dist/thaiDist 需各自排版策略与语言处理，不能只映射一个 CSS 属性。"
        if identifier == "text.run.underline.type":
            row["svg_mapping"] = "基本下划线可原生 text-decoration；点线、粗线、双线和波浪等通常需额外几何，并验证随文字排版。"
        if identifier == "shape.geometry.preset":
            row["svg_mapping"] = "187 种预设必须解析各自几何和调节参数为 SVG 路径；SVG 没有对应的 PowerPoint 预设形状枚举。"
        if identifier == "paint.pattern.preset":
            row["svg_mapping"] = "54 种图案可通过 pattern 绘制；须逐种实现图案几何、比例、前背景色，不是自动一对一映射。"
        if identifier.startswith("object.lock"):
            row["svg_mapping"] = "SVG 静态格式无对应编辑锁；可作为元数据供特定编辑器使用。"
        if identifier.startswith("connector."):
            row["svg_mapping"] = "线形可绘制；端点对象绑定和自动重路由不是 SVG 的同等原生编辑能力。"
        if identifier == "object.transform":
            row["pptx_mapping"] = "a:xfrm 支持位置、尺寸、旋转和翻转，不能直接存任意矩阵；剪切需要分解或烘焙，文字等对象可能无法保持同等编辑能力。"
        if identifier == "shape.geometry.path_fill_rule":
            row["pptx_mapping"] = "没有与 SVG nonzero/evenodd 同名的单一属性；需要几何与路径规则转换，不能等同 a:path/@fill。"
            row["svg_mapping"] = "fill-rule 原生支持 nonzero / evenodd。"
        if identifier == "shape.geometry.path_fill":
            row["pptx_mapping"] = "a:path/@fill 原生支持 none/norm/lighten/lightenLess/darken/darkenLess。"
            row["svg_mapping"] = "none/norm 可直接表达；lighten/darken 需要颜色或分层处理，不是 fill-rule。"
        if identifier in {"stroke.compound", "stroke.alignment"}:
            row["svg_mapping"] = "单线可直接描边；复合线和内侧对齐需额外路径/裁剪，不能认为所有选项有同型 SVG 属性。"
        if identifier == "document.orientation":
            row["pptx_mapping"] = "通过页面尺寸和方向设置表示 portrait / landscape。"
            row["svg_mapping"] = "通过画布/viewBox 的宽高表示。"
        if identifier == "color.kind":
            row["svg_mapping"] = "RGB/HSL 可直接输出颜色；主题、系统、预设和 scRGB/变换需要解析到输出颜色并确认颜色空间。"
        if identifier == "paint.kind":
            row["svg_mapping"] = "none/solid 可直接表达；gradient/pattern/image 生成相应定义；group_inherit 需解析继承。"
        if identifier == "paint.image.mode":
            row["svg_mapping"] = "stretch 用 image/填充框；tile 用 pattern，需要对齐、缩放、偏移和裁剪转换。"
        if identifier == "transition.direction":
            row["pptx_mapping"] = "方向仅按具体效果使用：侧向 l/r/u/d、角向 lu/ru/ld/rd、进出 in/out、朝向 horz/vert；不是每个效果支持全部。"
        if identifier == "chart.type":
            row["pptx_mapping"] = "经典图表子元素、组合图和现代 chartEx 布局可保存；柱/条、堆叠、平滑和 3D 等由附加参数区分。"
    return catalog


def render(catalog, references):
    rows = catalog["properties"]
    with (references / "export-capabilities.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        fields = ["domain", "id", "label", "value_description", "value_source", "pptx_mapping", "svg_mapping", "exporter_status", "test_status", "value_type", "canonical_unit"]
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# PPTX / SVG 属性矩阵", "", "表中列出具体取值和格式表达方式。格式可表达不等于当前代码已经实现；统一文档导出器仍待实现，代码与验证状态单列。", "",
             "枚举保留完整选项：原生枚举使用其 XML 值；统一语义选项明确注明来源。大列表在同一单元格内展开，不以 enum 或省略号替代。", "",
             "箭头 sm/med/lg 是相对线宽的类别，不是固定像素值。SVG 能画出对应宽度和长度，但需 marker 几何映射；精确视觉等价仍需 PowerPoint 对照标定。", ""]
    for group in catalog["domains"]:
        lines += ["## " + group["title"], "", "| 属性 | 具体取值 / 参数 | PPTX 表达 | SVG 表达与限制 | 当前代码 / 验证 |", "| --- | --- | --- | --- | --- |"]
        for row in rows:
            if row["domain"] != group["id"]:
                continue
            cells = [f"{row['label']}<br>`{row['id']}`", row["value_description"], row["pptx_mapping"], row["svg_mapping"],
                     "统一导出器未实现；未验证" if row["test_status"] == "not_tested" else row["exporter_status"] + "; " + row["test_status"]]
            lines.append("| " + " | ".join(str(cell).replace("|", "\\|").replace("\n", " ") for cell in cells) + " |")
        lines.append("")
    (references / "export-capabilities.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main():
    path = REFERENCES / "property-catalog.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))
    inventory = json.loads((REFERENCES / "pptx-inventory/schema-inventory.json").read_text(encoding="utf-8"))
    catalog = enrich(catalog, inventory)
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    render(catalog, REFERENCES)
    print(json.dumps({"properties": len(catalog["properties"]), "enum_properties": sum(row["value_type"] == "enum" for row in catalog["properties"])}))


if __name__ == "__main__":
    main()
