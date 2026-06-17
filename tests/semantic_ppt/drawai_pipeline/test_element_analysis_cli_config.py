from scripts import run_codex_element_analysis


def test_cli_config_args_can_inherit_host_codex_model_provider(monkeypatch, tmp_path):
    host_codex_home = tmp_path / "host_codex"
    host_codex_home.mkdir()
    (host_codex_home / "config.toml").write_text(
        """
model_provider = "custom"
model = "gpt-5.5"

[model_providers.custom]
name = "custom"
wire_api = "responses"
requires_openai_auth = true
base_url = "http://127.0.0.1:15721/v1"
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("DRAWAI_HOST_CODEX_HOME", str(host_codex_home))
    monkeypatch.setenv("DRAWAI_CODEX_INHERIT_HOST_CONFIG", "1")

    args = run_codex_element_analysis.cli_config_args("medium", [])
    overrides = [args[index + 1] for index, value in enumerate(args) if value == "-c"]

    assert 'model_provider="custom"' in overrides
    assert 'model="gpt-5.5"' in overrides
    assert 'model_providers.custom.base_url="http://127.0.0.1:15721/v1"' in overrides
    assert 'model_reasoning_effort="medium"' in overrides
