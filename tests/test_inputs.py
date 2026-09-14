from pathlib import Path

import pytest

from drawai_evaluation.batch import build_parser, main
from drawai_evaluation.inputs import default_output_root, folder_predictions, resolve_case_id

CASES = [{"bench_id": "maps/generated/map_01"}, {"bench_id": "slides/human/slide_02"}]


def svg(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"/>')
    return path


def test_short_and_full_ids_resolve_to_same_case():
    assert resolve_case_id(CASES, "map_01") == "maps/generated/map_01"
    assert resolve_case_id(CASES, "maps/generated/map_01") == "maps/generated/map_01"
    with pytest.raises(ValueError, match="unknown sample ID"):
        resolve_case_id(CASES, "map_99")
    with pytest.raises(ValueError, match="ambiguous sample ID"):
        resolve_case_id(CASES + [{"bench_id": "maps/human/map_01"}], "map_01")


@pytest.mark.parametrize("layout", ["mirrored", "flat"])
def test_folder_matches_both_supported_layouts(tmp_path: Path, layout: str):
    for case in CASES:
        name = case["bench_id"] if layout == "mirrored" else Path(case["bench_id"]).name
        svg(tmp_path / f"{name}.svg")
    entries, coverage = folder_predictions(CASES, tmp_path, method="m", model="v", require_all=True)
    assert {r["bench_id"] for r in entries} == {r["bench_id"] for r in CASES}
    assert all(
        r["method"] == "m" and r["model"] == "v" and r["status"] == "completed" for r in entries
    )
    assert coverage == {
        "requested_case_count": 2,
        "matched_case_count": 2,
        "missing_case_ids": [],
        "ignored_svg_paths": [],
    }


def test_folder_reports_missing_cases_and_unrelated_assets(tmp_path: Path):
    svg(tmp_path / "map_01.svg")
    svg(tmp_path / "assets/logo.svg")
    entries, coverage = folder_predictions(CASES, tmp_path, method="m", model="v")
    assert len(entries) == 1
    assert coverage["missing_case_ids"] == ["slides/human/slide_02"]
    assert coverage["ignored_svg_paths"] == ["assets/logo.svg"]
    with pytest.raises(ValueError, match="missing 1 benchmark SVGs"):
        folder_predictions(CASES, tmp_path, method="m", model="v", require_all=True)


def test_duplicate_layouts_are_rejected(tmp_path: Path):
    svg(tmp_path / "map_01.svg")
    svg(tmp_path / "maps/generated/map_01.svg")
    with pytest.raises(ValueError, match="multiple SVGs match"):
        folder_predictions(CASES, tmp_path, method="m", model="v")


def test_flat_filename_must_be_unique_in_dataset(tmp_path: Path):
    svg(tmp_path / "map_01.svg")
    cases = CASES + [{"bench_id": "maps/human/map_01"}]
    with pytest.raises(ValueError, match="ambiguous flat filename"):
        folder_predictions(cases, tmp_path, method="m", model="v")


def test_dot_in_case_id_is_not_treated_as_extension(tmp_path: Path):
    cases = [{"bench_id": "maps/generated/map.v1"}]
    svg(tmp_path / "maps/generated/map.v1.svg")
    entries, _ = folder_predictions(cases, tmp_path, method="m", model="v")
    assert entries[0]["bench_id"] == "maps/generated/map.v1"


def test_no_matches_fail_before_evaluation(tmp_path: Path):
    svg(tmp_path / "unrelated.svg")
    with pytest.raises(ValueError, match="no benchmark SVGs found"):
        folder_predictions(CASES, tmp_path, method="m", model="v")


def test_default_output_is_stable_and_separates_inputs(tmp_path: Path):
    first = default_output_root(
        tmp_path / "a.svg", method="m", model="v", case_id="maps/generated/map_01"
    )
    assert first == default_output_root(
        tmp_path / "a.svg", method="m", model="v", case_id="maps/generated/map_01"
    )
    assert first != default_output_root(
        tmp_path / "b.svg", method="m", model="v", case_id="maps/generated/map_01"
    )
    assert first != default_output_root(
        tmp_path / "a.svg", method="m", model="v2", case_id="maps/generated/map_01"
    )


@pytest.mark.parametrize(
    "args",
    [
        ["--svg", "a.svg"],
        ["--id", "map_01", "--svg-dir", "predictions"],
        ["--id", "map_01", "--svg", "a.svg", "--svg-dir", "predictions"],
        ["--id", "map_01", "--svg", "a.svg", "--require-all"],
    ],
)
def test_invalid_mode_arguments_fail_before_loading_data(args):
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2


def test_simple_commands_require_no_dataset_output_or_label_options():
    args = build_parser().parse_args(["--id", "map_01", "--svg", "a.svg"])
    assert args.dataset is None and args.output_root is None
    assert args.method == "candidate" and args.model == "unspecified"
    args = build_parser().parse_args(["--svg-dir", "predictions"])
    assert args.svg_dir == Path("predictions") and args.case_id is None
