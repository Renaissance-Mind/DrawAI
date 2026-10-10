"""Chart-native labels, markers, axes, trendlines and uncertainty bindings."""

from lxml import etree
from .xml import el, ensure, ordered, paint, replace, stroke, tag
from .rich import text_body


def chart_details(chart, props, ctx):
    used = set()
    tree = chart._chartSpace
    plot = tree.find(".//" + tag("c:plotArea"))
    series = tree.findall(".//" + tag("c:ser"))
    plots = [n for n in plot if etree.QName(n).localname.endswith("Chart")]

    def val(parent, name, value):
        replace(
            parent,
            "c:" + name,
            el("c:" + name, {"val": int(value) if isinstance(value, bool) else value}),
        )

    if "chart.plots" in props:
        if len(props["chart.plots"]) != len(plots):
            raise ValueError(
                "chart.plots must match the native plot count; import a combo template for multiple plots"
            )
        for p, spec in zip(plots, props["chart.plots"]):
            for key, name in [
                ("direction", "barDir"),
                ("grouping", "grouping"),
                ("vary_colors", "varyColors"),
                ("radar_style", "radarStyle"),
                ("scatter_style", "scatterStyle"),
                ("gap_width", "gapWidth"),
                ("overlap", "overlap"),
                ("first_slice_angle", "firstSliceAng"),
            ]:
                if key in spec:
                    val(p, name, spec[key])
        used.add("chart.plots")
    axes = (
        plot.findall(tag("c:catAx"))
        + plot.findall(tag("c:valAx"))
        + plot.findall(tag("c:dateAx"))
    )
    for full, action in [
        ("chart.axes.scale", "scale"),
        ("chart.axes.crossing", "crossing"),
        ("chart.axes.number_format", "format"),
        ("chart.axes.ticks", "ticks"),
        ("chart.axes.title", "title"),
        ("chart.axes.gridlines", "gridlines"),
    ]:
        if full not in props:
            continue
        specs = props[full] if isinstance(props[full], list) else [props[full]]
        for spec in specs:
            ax = axes[spec.get("index", 1)]
            if action == "scale":
                scaling = ensure(ax, "c:scaling")
                for key, name in [
                    ("minimum", "min"),
                    ("maximum", "max"),
                    ("log_base", "logBase"),
                    ("orientation", "orientation"),
                ]:
                    if key in spec:
                        val(scaling, name, spec[key])
                for key, name in [
                    ("major_unit", "majorUnit"),
                    ("minor_unit", "minorUnit"),
                ]:
                    if key in spec:
                        val(ax, name, spec[key])
                ordered(
                    scaling,
                    ["c:logBase", "c:orientation", "c:max", "c:min", "c:extLst"],
                )
            elif action == "crossing":
                if "mode" in spec:
                    val(ax, "crosses", spec["mode"])
                if "value" in spec:
                    replace(ax, "c:crosses", None)
                    val(ax, "crossesAt", spec["value"])
            elif action == "format":
                replace(
                    ax,
                    "c:numFmt",
                    el(
                        "c:numFmt",
                        {
                            "formatCode": spec["code"],
                            "sourceLinked": spec.get("source_linked", False),
                        },
                    ),
                )
            elif action == "ticks":
                for key, name in [
                    ("major", "majorTickMark"),
                    ("minor", "minorTickMark"),
                    ("label_position", "tickLblPos"),
                ]:
                    if key in spec:
                        val(ax, name, spec[key])
            elif action == "gridlines":
                for key, name in [
                    ("major", "majorGridlines"),
                    ("minor", "minorGridlines"),
                ]:
                    if key in spec:
                        if spec[key] is None:
                            replace(ax, "c:" + name, None)
                        else:
                            replace(
                                ax,
                                "c:" + name,
                                el(
                                    "c:" + name,
                                    children=[
                                        el(
                                            "c:spPr",
                                            children=[
                                                stroke(
                                                    spec[key],
                                                    chart.part,
                                                    ctx.doc.assets,
                                                    ctx.root,
                                                )
                                            ],
                                        )
                                    ],
                                ),
                            )
            elif action == "title":
                tx = el(
                    "c:rich",
                    children=[
                        el("a:bodyPr"),
                        el("a:lstStyle"),
                        el(
                            "a:p",
                            children=[el("a:r", children=[el("a:rPr"), el("a:t")])],
                        ),
                    ],
                )
                tx.find(".//" + tag("a:t")).text = spec["text"]
                replace(
                    ax,
                    "c:title",
                    el(
                        "c:title",
                        children=[
                            el("c:tx", children=[tx]),
                            el("c:overlay", {"val": False}),
                        ],
                    ),
                )
        used.add(full)
    if "chart.markers" in props:
        for spec in props["chart.markers"]:
            ser = series[spec["series"]]
            target = ser
            if "point" in spec:
                target = el("c:dPt", children=[el("c:idx", {"val": spec["point"]})])
                ser.append(target)
            marker = el(
                "c:marker",
                children=[
                    el("c:symbol", {"val": spec.get("symbol", "circle")}),
                    el("c:size", {"val": spec.get("size", 6)}),
                ],
            )
            if "fill" in spec:
                marker.append(
                    el(
                        "c:spPr",
                        children=[
                            paint(spec["fill"], chart.part, ctx.doc.assets, ctx.root)
                        ],
                    )
                )
            replace(target, "c:marker", marker)
        used.add("chart.markers")
    if "chart.data_labels" in props:
        specs = props["chart.data_labels"]
        for spec in specs:
            target = (
                series[spec["series"]]
                if "series" in spec
                else plots[spec.get("plot", 0)]
            )
            dl = el("c:dLbls")
            if "position" in spec:
                val(dl, "dLblPos", spec["position"])
            for key, name in [
                ("show_legend_key", "showLegendKey"),
                ("show_value", "showVal"),
                ("show_category", "showCatName"),
                ("show_series", "showSerName"),
                ("show_percent", "showPercent"),
                ("show_bubble_size", "showBubbleSize"),
                ("show_leader_lines", "showLeaderLines"),
            ]:
                if key in spec:
                    val(dl, name, spec[key])
            if "number_format" in spec:
                dl.append(
                    el(
                        "c:numFmt",
                        {"formatCode": spec["number_format"], "sourceLinked": False},
                    )
                )
            if "separator" in spec:
                n = el("c:separator")
                n.text = spec["separator"]
                dl.append(n)
            if "properties" in spec:
                body = el(
                    "c:txPr", children=[el("a:bodyPr"), el("a:lstStyle"), el("a:p")]
                )
                text_body(
                    body, spec["properties"], chart.part, ctx.doc.assets, ctx.root
                )
                dl.append(body)
            ordered(
                dl,
                [
                    "c:dLbl",
                    "c:delete",
                    "c:numFmt",
                    "c:spPr",
                    "c:txPr",
                    "c:dLblPos",
                    "c:showLegendKey",
                    "c:showVal",
                    "c:showCatName",
                    "c:showSerName",
                    "c:showPercent",
                    "c:showBubbleSize",
                    "c:separator",
                    "c:showLeaderLines",
                    "c:leaderLines",
                    "c:extLst",
                ],
            )
            replace(target, "c:dLbls", dl)
        used.add("chart.data_labels")
    if "chart.trendlines" in props:
        for spec in props["chart.trendlines"]:
            node = el("c:trendline")
            if "name" in spec:
                n = el("c:name")
                n.text = spec["name"]
                node.append(n)
            if "stroke" in spec:
                node.append(
                    el(
                        "c:spPr",
                        children=[
                            stroke(spec["stroke"], chart.part, ctx.doc.assets, ctx.root)
                        ],
                    )
                )
            for key, name in [
                ("type", "trendlineType"),
                ("order", "order"),
                ("period", "period"),
                ("forward", "forward"),
                ("backward", "backward"),
                ("intercept", "intercept"),
                ("show_r_squared", "dispRSqr"),
                ("show_equation", "dispEq"),
            ]:
                if key in spec:
                    val(node, name, spec[key])
            series[spec["series"]].append(node)
        used.add("chart.trendlines")
    if "chart.error_bars" in props:
        for spec in props["chart.error_bars"]:
            node = el("c:errBars")
            for key, name in [
                ("direction", "errDir"),
                ("bar_type", "errBarType"),
                ("value_type", "errValType"),
                ("no_end_cap", "noEndCap"),
                ("value", "val"),
            ]:
                if key in spec:
                    val(node, name, spec[key])
            if "stroke" in spec:
                node.append(
                    el(
                        "c:spPr",
                        children=[
                            stroke(spec["stroke"], chart.part, ctx.doc.assets, ctx.root)
                        ],
                    )
                )
            series[spec["series"]].append(node)
        used.add("chart.error_bars")
    for key, name in [("chart.series.explosion", "explosion")]:
        if key in props:
            for ser in series:
                val(ser, name, round(props[key] * 100))
            used.add(key)
    for full, target in [("chart.plot_area", plot), ("chart.chart_area", tree)]:
        if full in props:
            value = props[full]
            sp = el("c:spPr")
            if "fill" in value:
                sp.append(paint(value["fill"], chart.part, ctx.doc.assets, ctx.root))
            if "stroke" in value:
                sp.append(stroke(value["stroke"], chart.part, ctx.doc.assets, ctx.root))
            replace(target, "c:spPr", sp)
            used.add(full)
    if "chart.data_table" in props:
        value = props["chart.data_table"]
        dt = el("c:dTable")
        for key, name in [
            ("horizontal_border", "showHorzBorder"),
            ("vertical_border", "showVertBorder"),
            ("outline", "showOutline"),
            ("legend_keys", "showKeys"),
        ]:
            if key in value:
                val(dt, name, value[key])
        replace(plot, "c:dTable", dt)
        used.add("chart.data_table")
    if "chart.manual_layout" in props:
        value = props["chart.manual_layout"]
        ml = el("c:manualLayout")
        for k in (
            "layoutTarget",
            "xMode",
            "yMode",
            "wMode",
            "hMode",
            "x",
            "y",
            "w",
            "h",
        ):
            if k in value:
                val(ml, k, value[k])
        replace(plot, "c:layout", el("c:layout", children=[ml]))
        used.add("chart.manual_layout")
    for ax in axes:
        ordered(
            ax,
            [
                "c:axId",
                "c:scaling",
                "c:delete",
                "c:axPos",
                "c:majorGridlines",
                "c:minorGridlines",
                "c:title",
                "c:numFmt",
                "c:majorTickMark",
                "c:minorTickMark",
                "c:tickLblPos",
                "c:spPr",
                "c:txPr",
                "c:crossAx",
                "c:crosses",
                "c:crossesAt",
                "c:crossBetween",
                "c:majorUnit",
                "c:minorUnit",
                "c:baseTimeUnit",
                "c:majorTimeUnit",
                "c:minorTimeUnit",
                "c:auto",
                "c:lblAlgn",
                "c:lblOffset",
                "c:tickLblSkip",
                "c:tickMarkSkip",
                "c:noMultiLvlLbl",
                "c:extLst",
            ],
        )
    for p in plots:
        ordered(
            p,
            [
                "c:barDir",
                "c:grouping",
                "c:radarStyle",
                "c:scatterStyle",
                "c:varyColors",
                "c:ser",
                "c:dLbls",
                "c:dropLines",
                "c:hiLowLines",
                "c:upDownBars",
                "c:gapWidth",
                "c:gapDepth",
                "c:overlap",
                "c:serLines",
                "c:firstSliceAng",
                "c:holeSize",
                "c:axId",
                "c:extLst",
            ],
        )
    for ser in series:
        ordered(
            ser,
            [
                "c:idx",
                "c:order",
                "c:tx",
                "c:spPr",
                "c:invertIfNegative",
                "c:pictureOptions",
                "c:marker",
                "c:explosion",
                "c:dPt",
                "c:dLbls",
                "c:trendline",
                "c:errBars",
                "c:cat",
                "c:xVal",
                "c:val",
                "c:yVal",
                "c:bubbleSize",
                "c:smooth",
                "c:shape",
                "c:extLst",
            ],
        )
    ordered(
        plot,
        [
            "c:layout",
            *["c:" + etree.QName(p).localname for p in plots],
            "c:catAx",
            "c:valAx",
            "c:dateAx",
            "c:serAx",
            "c:dTable",
            "c:spPr",
            "c:extLst",
        ],
    )
    ordered(
        tree,
        [
            "c:date1904",
            "c:lang",
            "c:roundedCorners",
            "c:AlternateContent",
            "c:style",
            "c:clrMapOvr",
            "c:pivotSource",
            "c:protection",
            "c:chart",
            "c:spPr",
            "c:txPr",
            "c:externalData",
            "c:printSettings",
            "c:userShapes",
            "c:extLst",
        ],
    )
    return used
