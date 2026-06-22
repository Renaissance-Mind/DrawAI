import json
from pathlib import Path

import pytest
from PIL import Image

import drawai.svg_validation as svg_validation
from drawai.svg_validation import validate_svg_file


VALID_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80"><rect x="0" y="0" width="100" height="80" fill="white"/><circle cx="20" cy="20" r="10" fill="red"/></svg>'


@pytest.fixture(autouse=True)
def disable_browser_renderer_for_unit_tests(monkeypatch):
    monkeypatch.setenv("DRAWAI_SVG_RENDERER_BROWSER", "none")


def test_validate_svg_accepts_renderable_nonblank_svg(tmp_path: Path):
    svg = tmp_path / "ok.svg"
    svg.write_text(VALID_SVG, encoding="utf-8")
    report = validate_svg_file(svg, canvas=(100, 80), asset_manifest={"assets": []}, rendered_path=tmp_path / "rendered.png")
    assert report["status"] == "ok"
    assert (tmp_path / "rendered.png").exists()


def test_validate_svg_prefers_configured_browser_renderer(tmp_path: Path, monkeypatch):
    browser = tmp_path / "browser_renderer.py"
    args_path = tmp_path / "browser_args.json"
    browser.write_text(
        "#!/usr/bin/env python3\n"
        "import base64\n"
        "import json\n"
        "import os\n"
        "import sys\n"
        "args_path = os.environ.get('DRAWAI_TEST_BROWSER_ARGS')\n"
        "if args_path:\n"
        "    with open(args_path, 'w', encoding='utf-8') as handle:\n"
        "        json.dump(sys.argv, handle)\n"
        "png = base64.b64decode(\n"
        "    'iVBORw0KGgoAAAANSUhEUgAAAAQAAAAECAYAAACp8Z5+AAAAFUlEQVR4nGP8z8DwnwEJMCFziBMAAIPRAgYEvCRHAAAAAElFTkSuQmCC'\n"
        ")\n"
        "for arg in sys.argv:\n"
        "    if arg.startswith('--screenshot='):\n"
        "        with open(arg.split('=', 1)[1], 'wb') as handle:\n"
        "            handle.write(png)\n"
        "        break\n",
        encoding="utf-8",
    )
    browser.chmod(0o755)
    svg = tmp_path / "ok.svg"
    svg.write_text(VALID_SVG, encoding="utf-8")
    monkeypatch.setenv("DRAWAI_SVG_RENDERER_BROWSER", str(browser))
    monkeypatch.setenv("DRAWAI_TEST_BROWSER_ARGS", str(args_path))
    monkeypatch.setattr(svg_validation, "_browser_renderer_keychain_flags", lambda: ["--use-mock-keychain", "--password-store=basic"])

    report = validate_svg_file(svg, canvas=(100, 80), asset_manifest={"assets": []}, rendered_path=tmp_path / "rendered.png")

    assert report["status"] == "ok"
    assert report["render"]["backend"] == "browser"
    assert (tmp_path / "rendered.png").exists()
    args = json.loads(args_path.read_text(encoding="utf-8"))
    assert "--use-mock-keychain" in args
    assert "--password-store=basic" in args


def test_browser_renderer_keychain_flags_are_macos_only():
    assert svg_validation._browser_renderer_keychain_flags("darwin") == ["--use-mock-keychain", "--password-store=basic"]
    assert svg_validation._browser_renderer_keychain_flags("linux") == []


def test_validate_svg_rejects_external_href(tmp_path: Path):
    svg = tmp_path / "bad.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80"><image href="https://example.com/a.png"/></svg>', encoding="utf-8")
    report = validate_svg_file(svg, canvas=(100, 80), asset_manifest={"assets": []}, rendered_path=tmp_path / "rendered.png")
    assert report["status"] == "failed"
    assert any(issue["code"] == "external_href" for issue in report["issues"])


def test_validate_svg_rejects_viewbox_mismatch(tmp_path: Path):
    svg = tmp_path / "bad.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 90 80"></svg>', encoding="utf-8")
    report = validate_svg_file(svg, canvas=(100, 80), asset_manifest={"assets": []}, rendered_path=tmp_path / "rendered.png")
    assert any(issue["code"] == "viewbox_mismatch" for issue in report["issues"])


def test_validate_svg_rejects_solid_white_blank_render(tmp_path: Path):
    svg = tmp_path / "blank.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80"><rect width="100" height="80" fill="white"/></svg>',
        encoding="utf-8",
    )
    report = validate_svg_file(svg, canvas=(100, 80), asset_manifest={"assets": []}, rendered_path=tmp_path / "rendered.png")
    assert report["status"] == "failed"
    assert any(issue["code"] == "blank_render" for issue in report["issues"])


def test_validate_svg_rejects_script_element(tmp_path: Path):
    svg = tmp_path / "script.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80"><script>alert(1)</script></svg>',
        encoding="utf-8",
    )
    report = validate_svg_file(svg, canvas=(100, 80), asset_manifest={"assets": []}, rendered_path=tmp_path / "rendered.png")
    assert report["status"] == "failed"
    assert any(issue["code"] == "script_element" for issue in report["issues"])


def test_validate_svg_rejects_doctype(tmp_path: Path):
    svg = tmp_path / "doctype.svg"
    svg.write_text(
        '<!DOCTYPE svg [<!ENTITY local SYSTEM "file:///etc/passwd">]><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80"></svg>',
        encoding="utf-8",
    )
    report = validate_svg_file(svg, canvas=(100, 80), asset_manifest={"assets": []}, rendered_path=tmp_path / "rendered.png")
    assert report["status"] == "failed"
    assert any(issue["code"] == "doctype" for issue in report["issues"])
    assert any(issue["code"] == "external_entity" for issue in report["issues"])
    assert not (tmp_path / "rendered.png").exists()


def test_validate_svg_rejects_css_import_external_url_before_render(tmp_path: Path):
    svg = tmp_path / "import.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80"><style>@import "https://example.com/a.css";</style><rect width="100" height="80" fill="white"/></svg>',
        encoding="utf-8",
    )
    report = validate_svg_file(svg, canvas=(100, 80), asset_manifest={"assets": []}, rendered_path=tmp_path / "rendered.png")
    assert report["status"] == "failed"
    assert any(issue["code"] == "external_href" for issue in report["issues"])
    assert not any(issue["code"] == "render_failed" for issue in report["issues"])
    assert not (tmp_path / "rendered.png").exists()


def test_validate_svg_rejects_asset_href_not_in_manifest(tmp_path: Path):
    asset = tmp_path / "asset.png"
    Image.new("RGBA", (1, 1), (255, 0, 0, 255)).save(asset)
    svg = tmp_path / "bad_asset.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80"><image href="asset.png" width="10" height="10"/></svg>',
        encoding="utf-8",
    )
    report = validate_svg_file(svg, canvas=(100, 80), asset_manifest={"assets": []}, rendered_path=tmp_path / "rendered.png")
    assert report["status"] == "failed"
    assert any(issue["code"] == "asset_href_not_in_manifest" for issue in report["issues"])


def test_validate_svg_rejects_feimage_href_not_in_manifest(tmp_path: Path):
    asset = tmp_path / "asset.png"
    Image.new("RGBA", (1, 1), (255, 0, 0, 255)).save(asset)
    svg = tmp_path / "bad_feimage.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80"><defs><filter id="f"><feImage href="asset.png"/></filter></defs><rect width="100" height="80" fill="red"/></svg>',
        encoding="utf-8",
    )
    report = validate_svg_file(svg, canvas=(100, 80), asset_manifest={"assets": []}, rendered_path=tmp_path / "rendered.png")
    assert report["status"] == "failed"
    assert any(issue["code"] == "asset_href_not_in_manifest" for issue in report["issues"])


def test_validate_svg_accepts_local_manifest_asset_href(tmp_path: Path):
    asset = tmp_path / "asset.png"
    Image.new("RGBA", (1, 1), (255, 0, 0, 255)).save(asset)
    svg = tmp_path / "ok_asset.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80"><rect width="100" height="80" fill="white"/><image href="asset.png" width="10" height="10"/></svg>',
        encoding="utf-8",
    )
    report = validate_svg_file(
        svg,
        canvas=(100, 80),
        asset_manifest={"assets": [{"path": str(asset)}]},
        rendered_path=tmp_path / "rendered.png",
    )
    assert report["status"] == "ok"
    assert (tmp_path / "rendered.png").exists()


def test_validate_svg_accepts_manifest_approved_feimage_href(tmp_path: Path):
    asset = tmp_path / "asset.png"
    Image.new("RGBA", (1, 1), (255, 0, 0, 255)).save(asset)
    svg = tmp_path / "ok_feimage.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80"><defs><filter id="f"><feImage href="asset.png"/></filter></defs><rect width="100" height="80" fill="red"/></svg>',
        encoding="utf-8",
    )
    report = validate_svg_file(
        svg,
        canvas=(100, 80),
        asset_manifest={"assets": [{"path": str(asset)}]},
        rendered_path=tmp_path / "rendered.png",
    )
    assert report["status"] == "ok"
    assert (tmp_path / "rendered.png").exists()


def test_validate_svg_attempt_uses_final_svg_reference_dir_for_svg_href_assets(tmp_path: Path):
    final_svg_dir = tmp_path / "out" / "svg"
    attempt_dir = final_svg_dir / "attempts" / "001"
    asset = tmp_path / "out" / "assets" / "crops" / "AF01.png"
    attempt_dir.mkdir(parents=True)
    asset.parent.mkdir(parents=True)
    Image.new("RGBA", (2, 2), (255, 0, 0, 255)).save(asset)
    svg = attempt_dir / "semantic.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100" height="80">'
        '<rect width="100" height="80" fill="white"/>'
        '<image href="../assets/crops/AF01.png" width="10" height="10"/>'
        "</svg>",
        encoding="utf-8",
    )

    report = validate_svg_file(
        svg,
        canvas=(100, 80),
        asset_manifest={"assets": [{"asset_id": "AF01", "svg_href": "../assets/crops/AF01.png"}]},
        rendered_path=attempt_dir / "rendered.png",
        reference_dir=final_svg_dir,
    )

    assert report["status"] == "ok"
    assert (attempt_dir / "rendered.png").exists()


def test_validate_svg_rejects_external_url_attribute_before_render(tmp_path: Path):
    svg = tmp_path / "external_attr.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80"><defs><filter id="f"/></defs><rect width="100" height="80" fill="red" filter="url(file:///tmp/filter.svg)"/></svg>',
        encoding="utf-8",
    )
    report = validate_svg_file(svg, canvas=(100, 80), asset_manifest={"assets": []}, rendered_path=tmp_path / "rendered.png")
    assert report["status"] == "failed"
    assert any(issue["code"] == "external_href" for issue in report["issues"])
    assert not any(issue["code"] == "render_failed" for issue in report["issues"])
    assert not (tmp_path / "rendered.png").exists()


def test_validate_svg_rejects_local_url_attribute_not_in_manifest(tmp_path: Path):
    asset = tmp_path / "paint.svg"
    asset.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>', encoding="utf-8")
    svg = tmp_path / "local_attr.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80"><rect width="100" height="80" fill="url(paint.svg)"/></svg>',
        encoding="utf-8",
    )
    report = validate_svg_file(svg, canvas=(100, 80), asset_manifest={"assets": []}, rendered_path=tmp_path / "rendered.png")
    assert report["status"] == "failed"
    assert any(issue["code"] == "asset_href_not_in_manifest" for issue in report["issues"])


def test_validate_svg_allows_fragment_url_attribute(tmp_path: Path):
    svg = tmp_path / "fragment_attr.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80"><defs><linearGradient id="g"><stop offset="0" stop-color="red"/></linearGradient></defs><rect width="100" height="80" fill="url(#g)"/></svg>',
        encoding="utf-8",
    )
    report = validate_svg_file(svg, canvas=(100, 80), asset_manifest={"assets": []}, rendered_path=tmp_path / "rendered.png")
    assert report["status"] == "ok"
    assert (tmp_path / "rendered.png").exists()


def test_validate_svg_removes_stale_render_when_next_validation_fails(tmp_path: Path):
    rendered = tmp_path / "rendered.png"
    ok_svg = tmp_path / "ok.svg"
    ok_svg.write_text(VALID_SVG, encoding="utf-8")
    ok_report = validate_svg_file(ok_svg, canvas=(100, 80), asset_manifest={"assets": []}, rendered_path=rendered)
    assert ok_report["status"] == "ok"
    assert rendered.exists()

    bad_svg = tmp_path / "bad.svg"
    bad_svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80"><image href="https://example.com/a.png"/></svg>',
        encoding="utf-8",
    )
    bad_report = validate_svg_file(bad_svg, canvas=(100, 80), asset_manifest={"assets": []}, rendered_path=rendered)
    assert bad_report["status"] == "failed"
    assert any(issue["code"] == "external_href" for issue in bad_report["issues"])
    assert not rendered.exists()


def test_validate_svg_accepts_tiny_nonwhite_shape(tmp_path: Path):
    svg = tmp_path / "tiny.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80"><rect width="100" height="80" fill="white"/><rect x="50" y="40" width="1" height="1" fill="blue"/></svg>',
        encoding="utf-8",
    )
    report = validate_svg_file(svg, canvas=(100, 80), asset_manifest={"assets": []}, rendered_path=tmp_path / "rendered.png")
    assert report["status"] == "ok"
    assert (tmp_path / "rendered.png").exists()


def test_fallback_renderer_respects_svg_font_size(tmp_path: Path):
    svg = tmp_path / "large_text.svg"
    rendered = tmp_path / "rendered.png"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 90">'
        '<rect width="180" height="90" fill="white"/>'
        '<text x="90" y="62" text-anchor="middle" font-size="42" fill="black">Title</text>'
        "</svg>",
        encoding="utf-8",
    )
    report = validate_svg_file(svg, canvas=(180, 90), asset_manifest={"assets": []}, rendered_path=rendered)
    assert report["status"] == "ok"

    image = Image.open(rendered).convert("RGBA")
    dark_pixels = [
        (x, y)
        for y in range(image.height)
        for x in range(image.width)
        if image.getpixel((x, y))[0] < 64 and image.getpixel((x, y))[3] > 0
    ]
    ys = [y for _, y in dark_pixels]
    xs = [x for x, _ in dark_pixels]
    assert max(ys) - min(ys) >= 24
    assert 20 < min(xs) < 90
    assert 90 < max(xs) < 160


def test_validate_svg_rejects_af_placeholder_text(tmp_path: Path):
    svg = tmp_path / "placeholder.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80"><text x="10" y="20">AF01</text></svg>',
        encoding="utf-8",
    )
    report = validate_svg_file(svg, canvas=(100, 80), asset_manifest={"assets": []}, rendered_path=tmp_path / "rendered.png")
    assert report["status"] == "failed"
    assert any(issue["code"] == "af_placeholder" for issue in report["issues"])


def test_validate_svg_rejects_conflicting_width_height(tmp_path: Path):
    svg = tmp_path / "size.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="101px" height="80"></svg>',
        encoding="utf-8",
    )
    report = validate_svg_file(svg, canvas=(100, 80), asset_manifest={"assets": []}, rendered_path=tmp_path / "rendered.png")
    assert report["status"] == "failed"
    assert any(issue["code"] == "size_mismatch" for issue in report["issues"])
