from pathlib import Path

from PIL import Image

from drawai.asset_materialization import materialize_run0_refined_assets


def test_run0_polygon_crop_materializes_alpha_png(tmp_path: Path):
    case_dir = tmp_path / "case"
    image_path = case_dir / "inputs" / "figure.png"
    image_path.parent.mkdir(parents=True)
    Image.new("RGBA", (10, 10), (255, 0, 0, 255)).save(image_path)

    manifest = materialize_run0_refined_assets(
        image_path,
        {
            "case_dir": str(case_dir),
            "elements": [
                {
                    "box_id": "N001",
                    "bbox": [2, 2, 8, 8],
                    "category": "crop",
                    "geometry": {
                        "kind": "polygon",
                        "points": [[2, 2], [8, 2], [2, 8]],
                    },
                }
            ],
        },
        case_dir / "svg_to_ppt" / "assets",
        svg_dir=case_dir / "svg",
    )

    asset = manifest["assets"][0]
    assert asset["geometry"]["kind"] == "polygon"
    output_path = case_dir / "svg_to_ppt" / "assets" / "crops" / "run0_refined" / "R0_N001.png"
    with Image.open(output_path) as output:
        rgba = output.convert("RGBA")
    assert rgba.getpixel((1, 1))[3] == 255
    assert rgba.getpixel((5, 5))[3] == 0
