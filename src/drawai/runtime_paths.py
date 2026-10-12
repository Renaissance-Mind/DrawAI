"""One user configuration and workspace across Session, Workbench and CLI."""
import json
import os
from pathlib import Path
import tempfile

from .resources import resource_path


def drawai_home() -> Path:
    return Path(os.environ.get("DRAWAI_HOME", Path.home() / ".drawai")).expanduser().resolve()


def workspace_path() -> Path:
    return Path(os.environ.get("DRAWAI_WORKBENCH_WORKSPACE", read_preferences().get("workspace", drawai_home() / "workbench"))).expanduser().resolve()


def runtime_path() -> Path:
    return Path(os.environ.get("DRAWAI_LOCAL_RUNTIME_ROOT", read_preferences().get("runtime_root", drawai_home() / "runtime"))).expanduser().resolve()


def base_config_path() -> Path:
    explicit = os.environ.get("DRAWAI_WORKBENCH_DEFAULT_CONFIG")
    if explicit:
        return Path(explicit).expanduser().resolve()
    configured = drawai_home() / "config.yaml"
    return configured if configured.is_file() else resource_path("configs/drawai/config.yaml")


def read_preferences() -> dict:
    path = drawai_home() / "preferences.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def write_preferences(fields: dict) -> dict:
    data = {**read_preferences(), **fields}
    path = drawai_home() / "preferences.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        stream.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    temp.chmod(0o600)
    temp.replace(path)
    return data


def flow_urls() -> tuple[str, str]:
    settings = read_preferences()
    return (
        os.environ.get("DRAWAI_WORKBENCH_API_URL", settings.get("workbench_api_url", "http://127.0.0.1:8890")).rstrip("/"),
        os.environ.get("DRAWAI_WORKBENCH_UI_URL", settings.get("workbench_ui_url", "http://127.0.0.1:5174/")),
    )


def initialize_home() -> dict:
    import yaml
    home = drawai_home()
    home.mkdir(parents=True, exist_ok=True)
    workspace_path().mkdir(parents=True, exist_ok=True)
    config = home / "config.yaml"
    if not config.exists():
        data = yaml.safe_load(resource_path("configs/drawai/config.yaml").read_text(encoding="utf-8"))
        data["input"]["image"] = str(home / "input.png")
        data["input"]["output_dir"] = str(home / "runs")
        with config.open("x", encoding="utf-8") as stream:
            yaml.safe_dump(data, stream, allow_unicode=True, sort_keys=False)
        config.chmod(0o600)
    return {"home": str(home), "workspace": str(workspace_path()), "runtime": str(runtime_path()), "config": str(base_config_path())}
