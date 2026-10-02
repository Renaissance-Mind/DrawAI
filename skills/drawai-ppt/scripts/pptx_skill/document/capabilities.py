"""Implementation coverage, separate from the matrix's design targets."""

from collections import Counter
from .model import PROPERTIES
from .rich import RUN_ATTRS, P_ATTRS, BODY_ATTRS

# These are authoring bindings, not a declaration of visual equivalence between renderers.
WRITABLE = set(
    """
document.page_size document.metadata.title document.metadata.subject document.metadata.author document.metadata.keywords document.metadata.description document.metadata.revision document.metadata.created document.metadata.modified
theme.colors theme.fonts.major theme.fonts.minor theme.format_scheme theme.defaults theme.extra_color_schemes
slide.name slide.hidden slide.background slide.show_master_shapes slide.layout_ref
object.id object.kind object.name object.frame object.rotation object.flip_horizontal object.flip_vertical object.transform object.group_child_frame object.lock_aspect_ratio object.locks object.hidden object.black_white_mode object.style_ref object.z_order
shape.geometry.preset shape.geometry.adjustments shape.geometry.guides shape.geometry.paths shape.geometry.text_rect shape.geometry.handles shape.geometry.connection_sites shape.geometry.path_stroke shape.geometry.path_fill shape.geometry.path_viewport shape.geometry.extrusion_ok shape.geometry.path_fill_rule
connector.geometry connector.start_target connector.end_target
text.run.font.latin text.run.font.east_asian text.run.font.complex_script text.run.font.symbol text.run.font.charset text.run.font.pitch_family text.run.fill text.run.outline text.run.highlight text.run.underline.fill text.run.underline.stroke text.run.click_link text.run.hover_link text.run.proofing text.run.rtl text.run.effects
text.paragraph.line_spacing text.paragraph.space_before text.paragraph.space_after text.paragraph.tab_stops text.paragraph.default_run_style text.paragraph.end_run_style text.paragraph.bullet.kind text.paragraph.bullet.color text.paragraph.bullet.font text.paragraph.bullet.size text.paragraph.bullet.character text.paragraph.bullet.numbering text.paragraph.bullet.image_ref
text.body.paragraphs text.body.insets text.body.autofit text.body.autofit_scale text.body.wordart_warp
paint.kind paint.solid.color paint.gradient.kind paint.gradient.stops paint.gradient.angle paint.gradient.scaled paint.gradient.path_kind paint.gradient.fill_to_rect paint.gradient.tile_rect paint.gradient.flip paint.gradient.rotate_with_shape paint.pattern.preset paint.pattern.foreground paint.pattern.background paint.image.asset_ref paint.image.crop paint.image.mode paint.image.stretch_rect paint.image.tile_offset paint.image.tile_scale paint.image.tile_alignment paint.image.tile_flip paint.image.rotate_with_shape
stroke.width stroke.paint stroke.cap stroke.join stroke.miter_limit stroke.compound stroke.alignment stroke.dash_preset stroke.dash_custom stroke.start_arrow.kind stroke.start_arrow.width stroke.start_arrow.length stroke.end_arrow.kind stroke.end_arrow.width stroke.end_arrow.length
effects.outer_shadow effects.inner_shadow effects.preset_shadow effects.glow effects.soft_edge effects.reflection effects.blur effects.dag
three_d.camera.preset three_d.camera.field_of_view three_d.camera.zoom three_d.camera.rotation three_d.light_rig.preset three_d.light_rig.direction three_d.light_rig.rotation three_d.backdrop three_d.bevel.top three_d.bevel.bottom three_d.extrusion_depth three_d.contour_width three_d.z_position three_d.material three_d.extrusion_color three_d.contour_color
picture.asset_ref picture.crop picture.brightness picture.contrast picture.recolor picture.transparent_color picture.alpha picture.geometry_mask
table.grid_columns table.rows.height table.cells.content table.cells.merge table.cells.fill table.cells.borders table.cells.insets table.cells.vertical_anchor table.cells.text_direction table.cells.anchor_center table.cells.overflow table.style_ref table.first_row table.last_row table.first_column table.last_column table.band_rows table.band_columns table.rtl
chart.type chart.categories chart.series chart.title chart.legend chart.blank_values chart.visible_data_only chart.style_ref chart.axes chart.series.gap_overlap chart.series.doughnut_hole chart.series.style chart.series.smoothing
notes.content transition.kind transition.direction transition.speed transition.advance_on_click transition.advance_after animation.timeline interaction.hyperlink interaction.navigation_action accessibility.title accessibility.description accessibility.decorative compatibility.extension_list embedded.asset_ref embedded.prog_id embedded.preview_ref media.asset_ref media.poster_ref
""".split()
)
WRITABLE.update("text.run." + k for k in RUN_ATTRS)
WRITABLE.update("text.paragraph." + k for k in P_ATTRS)
WRITABLE.update("text.body." + k for k in BODY_ATTRS)
WRITABLE.update(
    """chart.plots chart.axes.scale chart.axes.crossing chart.axes.number_format chart.axes.gridlines chart.axes.title chart.axes.ticks chart.markers chart.data_labels chart.trendlines chart.error_bars chart.series.explosion chart.plot_area chart.chart_area chart.data_table chart.manual_layout""".split()
)
WRITABLE.update(
    "color.kind color.channels color.alpha color.transforms text.paragraph.content".split()
)
WRITABLE.update("picture.aspect_fit picture.svg_asset".split())
CONDITIONS = {
    "object.id": "顶层 id 为文档内唯一标识；object.id 是可用别名，若同时填写须相同。",
    "object.kind": "顶层 kind 决定创建类型；object.kind 是可用别名。修改导入对象的类型时创建替代对象。",
    "object.z_order": "数值越大越靠上；页面和分组内的已建模对象按该值重排，原始扩展节点保留其位置。",
    "picture.crop": "{left, top, right, bottom} 四边比例；同时接受 l/t/r/b 缩写，重复键须一致。",
    "paint.gradient.kind": "Native linear/circle/rect/shape gradients. SVG rect/shape uses a reported local PDF/PNG fallback for unrotated top-level objects when Poppler is available; other cases retain a declared approximation.",
    "picture.svg_asset": "Native SVG image relationship plus the picture.asset_ref bitmap fallback; older readers may display the fallback.",
    "chart.type": "Native creation: barChart, lineChart, areaChart, pieChart, doughnutChart, scatterChart, bubbleChart, radarChart. Other chart families require imported native parts.",
    "shape.geometry.path_fill_rule": "Native custom paths support nonzero; evenodd requires contour conversion and is rejected in strict authoring.",
    "object.transform": "Non-singular frame transforms without shear; shear is rejected. Translations are points.",
    "animation.timeline": "Accepts an exact p:timing XML tree or namespace-qualified tree data; timing graph authoring is explicit native data.",
    "theme.format_scheme": "Exact a:fmtScheme XML tree.",
    "theme.defaults": "Exact a:objectDefaults XML tree.",
    "theme.extra_color_schemes": "Exact a:extraClrSchemeLst XML tree.",
    "effects.dag": "Exact a:effectDag XML tree.",
    "transition.kind": "Standard PML transitions; Office extensions such as Morph require native package preservation.",
    "embedded.asset_ref": "OLE creation uses an explicit ProgID and optional preview; activation is controlled by the host.",
    "slide.layout_ref": "Creating a page binds an existing layout; changing an imported page layout requires explicit placeholder remapping.",
}
HOST = {
    "package.security.encryption",
    "package.security.permissions",
    "package.security.signature",
    "package.security.sensitivity",
    "live_feed.host_binding",
    "animation.runtime_state",
    "embedded.activation",
}


def capability_report():
    rows = []
    for key, spec in PROPERTIES.items():
        status = (
            "native_authoring"
            if key in WRITABLE
            else "host_required"
            if key in HOST
            else "native_preservation"
        )
        rows.append(
            {
                "id": key,
                "label": spec["label"],
                "authoring": status,
                "native_import_roundtrip": "package_envelope",
                "svg": "static_office_projection"
                if spec["svg_static_target"] not in ("metadata", "unsupported", "host")
                else spec["svg_static_target"],
                "conditions": CONDITIONS.get(
                    key,
                    "Imported native XML/relationships retained; a new typed authoring binding is required."
                    if status == "native_preservation"
                    else "Host application, policy or device required."
                    if status == "host_required"
                    else "Native OOXML binding; renderer behavior must be checked separately.",
                ),
                "allowed_values": spec.get("allowed_values", []),
            }
        )
    return {
        "schema": "presentation.capabilities.v1",
        "property_count": len(rows),
        "counts": dict(Counter(r["authoring"] for r in rows)),
        "properties": rows,
        "preservation_contract": "Unknown parts and OOXML survive template round trips. This does not imply typed creation/editing of every preserved feature.",
        "verification": "Package validation and actual render tests are separate from authoring status.",
    }
