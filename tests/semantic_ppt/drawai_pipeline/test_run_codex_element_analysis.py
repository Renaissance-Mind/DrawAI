import json

from scripts.run_codex_element_analysis import codex_cli_error_excerpt


def test_codex_cli_error_excerpt_reads_json_events(tmp_path):
    events = tmp_path / "cli_events.jsonl"
    events.write_text(
        "\n".join(
            [
                json.dumps({"type": "thread.started"}),
                json.dumps({"type": "error", "message": "first error"}),
                json.dumps({"type": "turn.failed", "error": {"message": "usage limit reached"}}),
            ]
        ),
        encoding="utf-8",
    )

    assert codex_cli_error_excerpt(events) == "usage limit reached"
