#!/usr/bin/env python3
"""Generate implementation coverage without changing the researched value domains."""

import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pptx_skill.document.capabilities import capability_report

ROOT = Path(__file__).resolve().parents[1] / "references"


def main():
    report = capability_report()
    (ROOT / "implementation-capabilities.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    labels = {
        "native_authoring": "原生属性 API（有条件）",
        "native_preservation": "模板保留 / 显式 XML 绑定",
        "host_required": "宿主 / 容器流程",
    }
    with (ROOT / "implementation-capabilities.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "label",
                "authoring",
                "native_import_roundtrip",
                "svg",
                "conditions",
            ],
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(report["properties"])
    lines = [
        "# 当前实现矩阵",
        "",
        "同一文档模型可导出 PPTX 和静态 SVG。此表覆盖属性目录中的全部 475 行，列出实际调用方式。",
        "",
        "“原生属性 API”表示已有 Python 绑定，并按列出的条件使用；不是全部对象上下文和渲染器均已逐项验证。其余属性可通过原模板保留，或使用显式 `native_bindings` / `native_parts` 编辑原生 XML。XML 绑定检查精确目标和包关系，语义与目标 PowerPoint 外观仍需参考文件验证。宿主设置不能用 XML 替代。",
        "",
        "静态 SVG 由同一 PPTX 的 LibreOffice Impress 排版导出，文字与路径尽量保留原生 SVG 元素；特殊效果可由渲染器栅格化。SVG 包含模型 metadata，可恢复该页面的原生制作源，并检查外观哈希是否仍对应。",
        "",
        f"当前分布：{report['counts']['native_authoring']} 项属性 API；{report['counts']['native_preservation']} 项模板保留或显式 XML 绑定；{report['counts']['host_required']} 项宿主依赖。",
        "",
        "| 属性 | 当前调用方式 | 条件 / 验证边界 |",
        "| --- | --- | --- |",
    ]
    for row in report["properties"]:
        lines.append(
            "| `"
            + row["id"]
            + "` "
            + row["label"]
            + " | "
            + labels[row["authoring"]]
            + " | "
            + row["conditions"].replace("|", "\\|")
            + " |"
        )
    (ROOT / "implementation-capabilities.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(report["counts"]))


if __name__ == "__main__":
    main()
