from datetime import datetime
from pathlib import Path

import pytest

from drawai.config import load_drawai_config
from drawai.prompt_plan import DEFAULT_SAM3_PROMPTS
from drawai.experiment_artifacts import next_versioned_run_dir, run_metadata_payload, safe_run_slug


def test_default_prompt_plan_is_fixed_user_plan():
    assert [(p.id, p.text, p.confidence_threshold) for p in DEFAULT_SAM3_PROMPTS] == [
        ("arrow", "arrow", 0.30),
        ("border", "border", 0.30),
        ("content_box", "content box", 0.15),
        ("diagram", "diagram", 0.20),
        ("grid", "grid", 0.30),
        ("icon", "icon", 0.30),
        ("picture", "picture", 0.30),
    ]


def test_load_main_config_uses_codex_python_sdk_defaults():
    repo_root = Path(__file__).resolve().parents[3]
    cfg = load_drawai_config("configs/drawai/config.yaml", validate_input_exists=False)
    assert cfg.input.image == repo_root / "input.png"
    assert cfg.input.output_dir == repo_root / "results/drawai_svg/config"
    assert cfg.input.normalization.enabled is True
    assert cfg.input.normalization.target_long_edge == 2048
    assert cfg.input.normalization.upscale_only is False
    assert cfg.input.normalization.flatten_transparency_background == "#ffffff"
    assert cfg.sam3.base_url == "http://127.0.0.1:18080"
    assert cfg.sam3.timeout_seconds == 600
    assert cfg.sam3.return_overlay is True
    assert cfg.sam3.return_masks is False
    assert cfg.sam3.service_merge_threshold == 0.0
    assert cfg.sam3.prompts == DEFAULT_SAM3_PROMPTS
    assert cfg.ocr.provider == "remote_paddleocr"
    assert cfg.ocr.remote_paddleocr.timeout_seconds == 600
    assert cfg.asset_selection.provider == "deterministic"
    assert cfg.asset_selection.max_attempts == 3
    assert cfg.asset_selection.disallow_crop_roles == ("arrow", "border", "grid", "text", "content_box")
    assert cfg.asset_selection.max_area_ratio == 0.35
    assert cfg.asset_materialization.rmbg.enabled is True
    assert cfg.asset_materialization.rmbg.provider == "service"
    assert cfg.asset_materialization.rmbg.base_url == "http://127.0.0.1:18080"
    assert cfg.asset_materialization.rmbg.timeout_seconds == 600
    assert cfg.asset_materialization.rmbg.model_path == ""
    assert cfg.asset_policy.enabled is True
    assert cfg.svg.max_attempts == 8
    assert cfg.svg.generation_backend == "codex_python_sdk_controlled"
    assert cfg.svg.staged_generation is True
    assert cfg.svg.timeout_seconds == 1500
    assert cfg.svg.text_rendering == "model_text"
    assert cfg.svg.visual_review_rounds == ("text_style",)
    assert cfg.svg_to_ppt.enabled is True
    assert cfg.svg_to_ppt.export_pptx is True
    assert cfg.model_runtime.provider == "codex-python-sdk"
    assert cfg.model_runtime.connection_id == "codex-python-sdk-controlled"
    assert cfg.model_runtime.model_name == "gpt-5.5"
    assert cfg.model_runtime.reasoning_effort == "xhigh"
    assert cfg.model_runtime.base_url == ""
    assert cfg.model_runtime.api_key == ""
    assert cfg.model_runtime.timeout_seconds == 600


def test_template_config_preserves_current_baseline_defaults():
    cfg = load_drawai_config("configs/drawai/config.template.yaml", validate_input_exists=False)

    assert cfg.input.normalization.target_long_edge == 2048
    assert cfg.input.normalization.upscale_only is False
    assert cfg.sam3.return_masks is False
    assert cfg.svg.generation_backend == "codex_python_sdk_controlled"
    assert cfg.svg.timeout_seconds == 1500
    assert cfg.svg_to_ppt.enabled is True
    assert cfg.svg_to_ppt.export_pptx is True
    assert cfg.model_runtime.provider == "codex-python-sdk"
    assert cfg.model_runtime.connection_id == "codex-python-sdk-controlled"
    assert cfg.model_runtime.model_name == "gpt-5.5"
    assert cfg.model_runtime.reasoning_effort == "xhigh"
    assert cfg.model_runtime.base_url == ""


def test_config_rejects_removed_svg_to_ppt_backend_options(tmp_path: Path):
    image = tmp_path / "input.png"
    image.write_bytes(b"not-used-by-config")
    config_path = tmp_path / "svg_to_ppt_options.yaml"
    config_path.write_text(
        """
input:
  image: input.png
  output_dir: out
svg_to_ppt:
  legacy_backend_option: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="only supports enabled/export_pptx"):
        load_drawai_config(config_path)


def test_config_rejects_bad_threshold(tmp_path: Path):
    image = tmp_path / "input.png"
    image.write_bytes(b"not-used-by-config")
    config_path = tmp_path / "bad.yaml"
    config_path.write_text(
        """
input:
  image: input.png
  output_dir: out
sam3:
  prompts:
    - id: arrow
      text: arrow
      confidence_threshold: 1.2
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="confidence_threshold"):
        load_drawai_config(config_path)


def test_config_parses_remote_rmbg_service_settings(tmp_path: Path):
    image = tmp_path / "input.png"
    image.write_bytes(b"not-used-by-config")
    config_path = tmp_path / "rmbg.yaml"
    config_path.write_text(
        """
input:
  image: input.png
  output_dir: out
asset_materialization:
  rmbg:
    enabled: true
    provider: service
    base_url: http://127.0.0.1:18080
    timeout_seconds: 45
    model_path: /opt/drawai/models/rmbg
""",
        encoding="utf-8",
    )

    cfg = load_drawai_config(config_path)

    assert cfg.asset_materialization.rmbg.enabled is True
    assert cfg.asset_materialization.rmbg.provider == "service"
    assert cfg.asset_materialization.rmbg.base_url == "http://127.0.0.1:18080"
    assert cfg.asset_materialization.rmbg.timeout_seconds == 45
    assert cfg.asset_materialization.rmbg.model_path == "/opt/drawai/models/rmbg"


def test_config_parses_asset_policy_settings(tmp_path: Path):
    image = tmp_path / "input.png"
    image.write_bytes(b"not-used-by-config")
    config_path = tmp_path / "asset_policy.yaml"
    config_path.write_text(
        """
input:
  image: input.png
  output_dir: out
asset_policy:
  enabled: false
""",
        encoding="utf-8",
    )

    cfg = load_drawai_config(config_path)

    assert cfg.asset_policy.enabled is False


def test_config_rejects_deprecated_ocr_placeholder_text_rendering(tmp_path: Path):
    image = tmp_path / "input.png"
    image.write_bytes(b"not-used-by-config")
    config_path = tmp_path / "bad_text_rendering.yaml"
    config_path.write_text(
        """
input:
  image: input.png
  output_dir: out
svg:
  text_rendering: ocr_placeholder
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="model_text"):
        load_drawai_config(config_path)


def test_config_rejects_unknown_visual_review_round(tmp_path: Path):
    image = tmp_path / "input.png"
    image.write_bytes(b"not-used-by-config")
    config_path = tmp_path / "bad_visual_review.yaml"
    config_path.write_text(
        """
input:
  image: input.png
  output_dir: out
svg:
  visual_review_rounds:
    - text_style
    - editability
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="visual_review_rounds"):
        load_drawai_config(config_path)


def test_config_rejects_removed_codex_sdk_svg_generation_backend(tmp_path: Path):
    image = tmp_path / "input.png"
    image.write_bytes(b"not-used-by-config")
    config_path = tmp_path / "codex_backend.yaml"
    config_path.write_text(
        """
input:
  image: input.png
  output_dir: out
svg:
  generation_backend: codex_sdk_tool_loop
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="generation_backend"):
        load_drawai_config(config_path)


def test_config_rejects_removed_svg_sdk_runner_field(tmp_path: Path):
    image = tmp_path / "input.png"
    image.write_bytes(b"not-used-by-config")
    config_path = tmp_path / "sdk_runner.yaml"
    config_path.write_text(
        """
input:
  image: input.png
  output_dir: out
svg:
  generation_backend: sdk_tool_loop
  sdk_runner: openai_responses_tool
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="sdk_runner"):
        load_drawai_config(config_path)


def test_config_rejects_removed_local_codex_context_mode(tmp_path: Path):
    image = tmp_path / "input.png"
    image.write_bytes(b"not-used-by-config")
    config_path = tmp_path / "local_context.yaml"
    config_path.write_text(
        """
input:
  image: input.png
  output_dir: out
svg:
  generation_backend: sdk_tool_loop
  local_codex_context_mode: isolated
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="local_codex_context_mode"):
        load_drawai_config(config_path)


def test_config_rejects_unknown_svg_generation_backend(tmp_path: Path):
    image = tmp_path / "input.png"
    image.write_bytes(b"not-used-by-config")
    config_path = tmp_path / "bad_svg_backend.yaml"
    config_path.write_text(
        """
input:
  image: input.png
  output_dir: out
svg:
  generation_backend: fake_user_command
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="generation_backend"):
        load_drawai_config(config_path)


def test_config_accepts_agent_cli_svg_backend_and_command(tmp_path: Path):
    image = tmp_path / "input.png"
    image.write_bytes(b"not-used-by-config")
    config_path = tmp_path / "agent_cli.yaml"
    config_path.write_text(
        """
input:
  image: input.png
  output_dir: out
svg:
  generation_backend: agent_cli
model_runtime:
  provider: agent-cli
  connection_id: kimi
  model_name: kimi-code/kimi-for-coding
  cli:
    agent: kimi
    command:
      - kimi
  timeout_seconds: 120
""",
        encoding="utf-8",
    )

    cfg = load_drawai_config(config_path)

    assert cfg.svg.generation_backend == "agent_cli"
    assert cfg.model_runtime.provider == "agent-cli"
    assert cfg.model_runtime.connection_id == "kimi"
    assert cfg.model_runtime.model_name == "kimi-code/kimi-for-coding"
    assert cfg.model_runtime.cli.agent == "kimi"
    assert cfg.model_runtime.cli.command == ("kimi",)
    assert cfg.model_runtime.to_runtime_dict()["cli"] == {
        "agent": "kimi",
        "command": ["kimi"],
    }


def test_config_accepts_acp_agent_svg_backend_and_command(tmp_path: Path):
    image = tmp_path / "input.png"
    image.write_bytes(b"not-used-by-config")
    config_path = tmp_path / "acp_agent.yaml"
    config_path.write_text(
        """
input:
  image: input.png
  output_dir: out
svg:
  generation_backend: acp_agent
model_runtime:
  provider: acp-agent
  connection_id: kimi
  model_name: kimi-code/kimi-for-coding
  acp:
    agent: kimi
    command:
      - kimi
      - acp
  timeout_seconds: 120
""",
        encoding="utf-8",
    )

    cfg = load_drawai_config(config_path)

    assert cfg.svg.generation_backend == "acp_agent"
    assert cfg.model_runtime.provider == "acp-agent"
    assert cfg.model_runtime.connection_id == "kimi"
    assert cfg.model_runtime.model_name == "kimi-code/kimi-for-coding"
    assert cfg.model_runtime.acp.agent == "kimi"
    assert cfg.model_runtime.acp.command == ("kimi", "acp")
    assert cfg.model_runtime.to_runtime_dict()["acp"] == {
        "agent": "kimi",
        "command": ["kimi", "acp"],
    }


@pytest.mark.parametrize(
    ("agent", "command"),
    [
        ("gemini", ("gemini", "--experimental-acp")),
        ("qwen", ("qwen", "--acp")),
        ("opencode", ("opencode", "acp")),
        ("goose", ("goose", "acp")),
        ("kiro", ("kiro-cli", "acp")),
        ("qoder", ("qodercli", "--acp")),
        ("cursor", ("agent", "acp")),
        ("cline", ("cline", "--acp")),
        ("copilot", ("copilot", "--acp", "--stdio")),
        ("hermes", ("hermes", "acp")),
    ],
)
def test_config_accepts_supported_acp_agent_presets(
    tmp_path: Path,
    agent: str,
    command: tuple[str, ...],
):
    image = tmp_path / "input.png"
    image.write_bytes(b"not-used-by-config")
    config_path = tmp_path / f"{agent}_acp.yaml"
    config_path.write_text(
        f"""
input:
  image: input.png
  output_dir: out
svg:
  generation_backend: acp_agent
model_runtime:
  provider: acp-agent
  connection_id: {agent}
  acp:
    agent: {agent}
    command: {list(command)}
  timeout_seconds: 120
""",
        encoding="utf-8",
    )

    cfg = load_drawai_config(config_path)

    assert cfg.svg.generation_backend == "acp_agent"
    assert cfg.model_runtime.provider == "acp-agent"
    assert cfg.model_runtime.connection_id == agent
    assert cfg.model_runtime.acp.agent == agent
    assert cfg.model_runtime.acp.command == command


def test_config_accepts_tool_agent_svg_backend(tmp_path: Path):
    image = tmp_path / "input.png"
    image.write_bytes(b"not-used-by-config")
    config_path = tmp_path / "tool_agent.yaml"
    config_path.write_text(
        """
input:
  image: input.png
  output_dir: out
svg:
  generation_backend: tool_agent
model_runtime:
  provider: drawai_tool_agent
  connection_id: drawai_tool_agent
  model_name: qwen3.7-plus
  base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
  api_key_env: DASHSCOPE_API_KEY
  wire_api: chat_completions
""",
        encoding="utf-8",
    )

    cfg = load_drawai_config(config_path)

    assert cfg.svg.generation_backend == "tool_agent"
    assert cfg.model_runtime.provider == "drawai_tool_agent"
    assert cfg.model_runtime.wire_api == "chat_completions"


def test_config_accepts_openclaw_and_hermes_agent_cli_presets(tmp_path: Path):
    image = tmp_path / "input.png"
    image.write_bytes(b"not-used-by-config")

    for agent, command in {
        "openclaw": ["openclaw", "agent"],
        "hermes": ["hermes", "chat"],
    }.items():
        config_path = tmp_path / f"{agent}.yaml"
        config_path.write_text(
            f"""
input:
  image: input.png
  output_dir: out-{agent}
svg:
  generation_backend: agent_cli
model_runtime:
  provider: agent-cli
  connection_id: {agent}
  cli:
    agent: {agent}
    command:
{chr(10).join(f"      - {part}" for part in command)}
  timeout_seconds: 120
""",
            encoding="utf-8",
        )

        cfg = load_drawai_config(config_path)

        assert cfg.svg.generation_backend == "agent_cli"
        assert cfg.model_runtime.connection_id == agent
        assert cfg.model_runtime.cli.agent == agent
        assert cfg.model_runtime.cli.command == tuple(command)


def test_config_rejects_removed_kimi_command(tmp_path: Path):
    image = tmp_path / "input.png"
    image.write_bytes(b"not-used-by-config")
    config_path = tmp_path / "bad_kimi_command.yaml"
    config_path.write_text(
        """
input:
  image: input.png
  output_dir: out
model_runtime:
  kimi_command:
    - kimi
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="kimi_command has been removed"):
        load_drawai_config(config_path)


def test_config_rejects_removed_acp_command(tmp_path: Path):
    image = tmp_path / "input.png"
    image.write_bytes(b"not-used-by-config")
    config_path = tmp_path / "bad_acp_command.yaml"
    config_path.write_text(
        """
input:
  image: input.png
  output_dir: out
model_runtime:
  acp_command:
    - kimi
    - acp
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="acp_command has been removed"):
        load_drawai_config(config_path)


def test_config_rejects_removed_acp_generation_mode(tmp_path: Path):
    image = tmp_path / "input.png"
    image.write_bytes(b"not-used-by-config")
    config_path = tmp_path / "bad_acp_mode.yaml"
    config_path.write_text(
        """
input:
  image: input.png
  output_dir: out
svg:
  generation_backend: acp
  acp_generation_mode: compact
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="acp_generation_mode has been removed"):
        load_drawai_config(config_path)


def test_config_rejects_deprecated_template_visual_refine_rounds(tmp_path: Path):
    image = tmp_path / "input.png"
    image.write_bytes(b"not-used-by-config")
    config_path = tmp_path / "bad_visual_refine.yaml"
    config_path.write_text(
        """
input:
  image: input.png
  output_dir: out
svg:
  template_visual_refine_rounds: 2
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="deprecated"):
        load_drawai_config(config_path)


def test_safe_run_slug_normalizes_free_text():
    assert safe_run_slug(" DrawAI/SAM3 Default Smoke ") == "drawai_sam3_default_smoke"
    assert safe_run_slug("...") == "run"


def test_next_versioned_run_dir_uses_date_version_time_and_slug(tmp_path: Path):
    run_root = tmp_path / "runs"
    (run_root / "20260524" / "v001_101112_box_ir_sam3").mkdir(parents=True)
    (run_root / "20260524" / "v002_111213_probe").mkdir(parents=True)

    run_dir = next_versioned_run_dir(
        run_root,
        slug="DrawAI SAM3",
        now=datetime(2026, 5, 24, 12, 34, 56),
    )

    assert run_dir == run_root.resolve() / "20260524" / "v003_123456_drawai_sam3"


def test_next_versioned_run_dir_versions_are_per_date(tmp_path: Path):
    run_root = tmp_path / "runs"
    (run_root / "20260523" / "v009_235959_old").mkdir(parents=True)

    run_dir = next_versioned_run_dir(
        run_root,
        slug="probe",
        now=datetime(2026, 5, 24, 0, 0, 1),
    )

    assert run_dir == run_root.resolve() / "20260524" / "v001_000001_probe"


def test_run_metadata_payload_records_layout_contract(tmp_path: Path):
    payload = run_metadata_payload(
        run_dir=tmp_path / "runs" / "20260524" / "v001_123456_probe",
        run_root=tmp_path / "runs",
        manifest_path=tmp_path / "manifest.jsonl",
        base_config_path=tmp_path / "default.yaml",
        script_path=tmp_path / "run_probe.py",
        args={"workers": 5},
        now=datetime(2026, 5, 24, 12, 34, 56),
    )

    assert payload["schema"] == "drawai.experiment_run_metadata.v1"
    assert payload["layout"] == "runs/YYYYMMDD/vNNN_HHMMSS_slug"
    assert payload["run_id"] == "v001_123456_probe"
    assert payload["date"] == "20260524"
    assert payload["args"] == {"workers": 5}
