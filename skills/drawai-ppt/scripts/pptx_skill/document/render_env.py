"""Resolve declared fonts without changing user/system font configuration."""

import os
from pathlib import Path
import shutil
import subprocess
from lxml import etree


def office_environment(prs, workdir):
    env = os.environ.copy()
    matcher = shutil.which("fc-match")
    if not matcher:
        return env, {"font_resolution": "renderer_default"}
    families = set()
    for part in prs.part.package.iter_parts():
        if not str(part.partname).endswith(".xml"):
            continue
        if "/theme/" in str(part.partname):
            continue
        root = etree.fromstring(
            part.blob, etree.XMLParser(resolve_entities=False, no_network=True)
        )
        families.update(
            n.get("typeface")
            for n in root.iter()
            if n.get("typeface") and not n.get("typeface").startswith("+")
        )
    dirs = set()
    fonts = []
    for family in sorted(families):
        line = subprocess.run(
            [matcher, "-f", "%{file}\t%{family}\n", family],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        ).stdout.splitlines()[0]
        path, matched = line.split("\t", 1)
        if Path(path).is_file():
            dirs.add(str(Path(path).parent))
        fonts.append(
            {
                "requested": family,
                "matched": matched,
                "file": path,
                "fallback": family.casefold()
                not in {f.strip().casefold() for f in matched.split(",")},
            }
        )
    for path in (
        "/System/Library/Fonts",
        "/Library/Fonts",
        "/usr/share/fonts",
        "/usr/local/share/fonts",
        str(Path.home() / ".local/share/fonts"),
    ):
        if Path(path).is_dir():
            dirs.add(path)
    root = etree.Element("fontconfig")
    for path in sorted(dirs):
        etree.SubElement(root, "dir").text = path
    etree.SubElement(root, "cachedir").text = str(Path(workdir) / "font-cache")
    config = Path(workdir) / "fonts.conf"
    config.write_bytes(etree.tostring(root, xml_declaration=True, encoding="UTF-8"))
    env["FONTCONFIG_FILE"] = str(config)
    return env, {"font_resolution": "fontconfig_declared_families", "fonts": fonts}
