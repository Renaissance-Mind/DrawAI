"""Fixed runtime configuration for the benchmark judge."""


def controlled_codex_config_overrides() -> tuple[str, ...]:
    return (
        'web_search="disabled"',
        "features.shell_tool=true",
        "features.image_generation=false",
        "features.rmcp_client=false",
        "features.multi_agent=false",
        "features.memories=false",
        "features.hooks=false",
        "features.apps=false",
        "project_doc_max_bytes=0",
        "project_doc_fallback_filenames=[]",
        'cli_auth_credentials_store="file"',
        "shell_environment_policy.ignore_default_excludes=false",
        'shell_environment_policy.exclude=["CODEX_HOME","DRAWAI_HOST_HOME","DRAWAI_HOST_CODEX_HOME"]',
        'sandbox_mode="workspace-write"',
    )
