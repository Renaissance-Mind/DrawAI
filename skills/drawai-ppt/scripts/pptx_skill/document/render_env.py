"""Resolve declared fonts without changing user/system font configuration."""

import os
from pathlib import Path
import shutil
import subprocess
import zipfile
from lxml import etree


def office_input(source, workdir, embedded_fonts="ignore"):
    """Use installed fonts in a disposable Office input; preserve the source package."""
    if embedded_fonts not in ("ignore", "preserve"):
        raise ValueError("embedded_fonts must be ignore or preserve")
    source = Path(source)
    pns = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
    rns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    with zipfile.ZipFile(source) as package:
        tree = etree.fromstring(package.read("ppt/presentation.xml"))
        lists = tree.findall(pns + "embeddedFontLst")
        families = [
            node.get("typeface") for lst in lists for node in lst.iter(pns + "font")
        ]
        report = {
            "embedded_font_policy": embedded_fonts,
            "embedded_font_families": families,
            "rendering_copy_used": bool(lists) and embedded_fonts == "ignore",
        }
        if not report["rendering_copy_used"]:
            return source, report
        ids = {
            node.get(rns + "id")
            for lst in lists
            for node in lst.iter()
            if node.get(rns + "id")
        }
        for lst in lists:
            tree.remove(lst)
        relationships = "ppt/_rels/presentation.xml.rels"
        rels = etree.fromstring(package.read(relationships))
        for rel in list(rels):
            if rel.get("Id") in ids:
                rels.remove(rel)
        replaced = {
            "ppt/presentation.xml": etree.tostring(
                tree, xml_declaration=True, encoding="UTF-8", standalone=True
            ),
            relationships: etree.tostring(
                rels, xml_declaration=True, encoding="UTF-8", standalone=True
            ),
        }
        destination = Path(workdir) / "office-input" / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as target:
            for entry in package.infolist():
                target.writestr(
                    entry, replaced.get(entry.filename, package.read(entry.filename))
                )
    return destination, report


def office_environment(prs, workdir):
    env = os.environ.copy()
    matcher = shutil.which("fc-match") or next(
        (
            str(p)
            for p in (
                Path("/opt/homebrew/bin/fc-match"),
                Path("/usr/local/bin/fc-match"),
                Path("/usr/bin/fc-match"),
            )
            if p.is_file() and os.access(p, os.X_OK)
        ),
        None,
    )
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
        str(Path.home() / "Library/Fonts"),
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
