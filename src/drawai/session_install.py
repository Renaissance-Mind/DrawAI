"""Register a thin host adapter pointing at the existing DrawAI core."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

from .resources import resource_path
from .runtime_paths import drawai_home, initialize_home

SKILLS = ("drawai-readme", "drawai-design", "drawai-image2ppt")


def retain_previous(path, directory):
    if path.exists():
        backup = directory / uuid.uuid4().hex / path.name
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(backup))


def install_session(host, *, output_dir=None):
    initialize_home()
    destination = Path(output_dir).expanduser().resolve() if output_dir else drawai_home() / "integrations" / host
    for name in SKILLS:
        if (destination / "skills" / name).resolve() == resource_path("skills/" + name).resolve():
            raise ValueError("Export Session adapters to a new directory, not the source skills directory")
    destination.mkdir(parents=True, exist_ok=True)
    for name in SKILLS:
        target = destination / "skills" / name
        retain_previous(target, destination / "previous-skills")
        shutil.copytree(resource_path("skills/" + name), target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    mcp = {"mcpServers": {"drawai": {"command": sys.executable, "args": ["-m", "drawai.mcp_server"], "env": {"DRAWAI_HOME": str(drawai_home())}}}}
    (destination / ".mcp.json").write_text(json.dumps(mcp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if host == "codex":
        from importlib.metadata import version
        icon = destination / "assets/drawai_image.png"
        icon.parent.mkdir(exist_ok=True)
        shutil.copyfile(resource_path("apps/workbench/public/drawai_image.png"), icon)
        manifest = {"name": "drawai", "version": version("drawai"), "description": "Shared DrawAI tools. Session implementation stays in the current Agent; visual generation uses host tools or configured APIs.", "author": {"name": "Renaissance Mind"}, "license": "Apache-2.0", "skills": "./skills/", "mcpServers": "./.mcp.json", "interface": {"displayName": "DrawAI", "composerIcon": "./assets/drawai_image.png", "logo": "./assets/drawai_image.png", "logoDark": "./assets/drawai_image.png", "brandColor": "#3168f5", "category": "Productivity", "capabilities": ["Interactive", "Read", "Write"], "shortDescription": "模板、图像与可编辑 PowerPoint", "defaultPrompt": ["使用 $drawai-readme，根据我的材料制作 PPT。图像使用当前会话工具或我的 API；最终制作默认由当前 Agent 完成。"]}}
        directory = destination / ".codex-plugin"
        directory.mkdir(exist_ok=True)
        (directory / "plugin.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        marketplace = drawai_home() / "marketplace"
        index = marketplace / ".agents/plugins"
        index.mkdir(parents=True, exist_ok=True)
        shutil.copytree(destination, marketplace / "drawai", dirs_exist_ok=True)
        name = "drawai-" + hashlib.sha256(str(drawai_home()).encode()).hexdigest()[:10]
        (index / "marketplace.json").write_text(json.dumps({"name": name, "interface": {"displayName": "DrawAI"}, "plugins": [{"name": "drawai", "source": {"source": "local", "path": "./drawai"}, "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}, "category": "Productivity"}]}, ensure_ascii=False, indent=2), encoding="utf-8")
        for command in (["codex", "plugin", "marketplace", "add", str(marketplace), "--json"], ["codex", "plugin", "add", f"drawai@{name}", "--json"]):
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            receipt = json.loads(result.stdout)
            if receipt.get("installedPath"):
                installed = Path(receipt["installedPath"])
                shutil.copytree(destination / "skills", installed / "skills", dirs_exist_ok=True)
                shutil.copytree(destination / ".codex-plugin", installed / ".codex-plugin", dirs_exist_ok=True)
                shutil.copytree(destination / "assets", installed / "assets", dirs_exist_ok=True)
                shutil.copyfile(destination / ".mcp.json", installed / ".mcp.json")
        # Upgrade the known repository installer instead of leaving two DrawAI
        # skill sets active. Only remove it after the new adapter is installed.
        listing = subprocess.run(["codex", "plugin", "list", "--json"], check=True, capture_output=True, text=True)
        for plugin in json.loads(listing.stdout).get("installed", []):
            if plugin.get("pluginId") == "drawai@drawai-local" and plugin.get("marketplaceSource", {}).get("sourceType") == "local":
                subprocess.run(["codex", "plugin", "remove", "drawai@drawai-local", "--json"], check=True, capture_output=True, text=True)
    elif host == "claude":
        skill_root = Path.home() / ".claude/skills"
        skill_root.mkdir(parents=True, exist_ok=True)
        for name in SKILLS:
            target = skill_root / name
            if target.exists():
                # Only replace DrawAI's own skill; retain unrelated user content.
                text = (target / "SKILL.md").read_text(encoding="utf-8")
                if f"name: {name}" not in text:
                    raise FileExistsError(f"Existing skill is not a DrawAI installation: {target}")
                retain_previous(target, drawai_home() / "backups/claude-skills")
            shutil.copytree(destination / "skills" / name, target)
        # User-scope Claude configuration is JSON; preserve all unrelated fields.
        config_path = Path.home() / ".claude.json"
        config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
        previous = config.setdefault("mcpServers", {}).get("drawai", {})
        server = mcp["mcpServers"]["drawai"]
        config["mcpServers"]["drawai"] = {"type": "stdio", **server, "env": {**previous.get("env", {}), **server["env"]}}
        if config_path.exists():
            backup = drawai_home() / "backups/claude-config" / (uuid.uuid4().hex + ".json")
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_bytes(config_path.read_bytes())
            backup.chmod(0o600)
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=config_path.parent, delete=False) as stream:
            temp = Path(stream.name)
            stream.write(json.dumps(config, ensure_ascii=False, indent=2) + "\n")
        temp.chmod(0o600)
        temp.replace(config_path)

    elif host != "generic":
        raise ValueError(f"Unknown Session host: {host}")
    return {"host": host, "directory": str(destination), "python": sys.executable, "home": str(drawai_home())}


def session_cli(argv):
    if argv and argv[0] == "tool":
        from .shared_tools import tool_cli
        return tool_cli(argv[1:])
    if argv and argv[0] == "execute":
        return execute_explicit_agent(argv[1:])
    parser = argparse.ArgumentParser(prog="drawai session")
    parser.add_argument("action", choices=("install",))
    parser.add_argument("--host", choices=("codex", "claude", "generic"), required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(install_session(args.host, output_dir=args.output_dir), ensure_ascii=False, indent=2))
    return 0


def execute_explicit_agent(argv):
    parser = argparse.ArgumentParser(prog="drawai session execute", description="Run another Agent only when the user explicitly selected it; inherit that Agent's configuration.")
    parser.add_argument("--agent", choices=("claude", "codex", "custom"), required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--model", help="Override the selected Agent's model only when requested.")
    parser.add_argument("--command", type=Path, help="Custom command as a JSON array; prompt is sent to stdin.")
    parser.add_argument("--timeout", type=int, default=3600)
    args = parser.parse_args(argv)
    if args.agent == "custom":
        if args.command is None:
            parser.error("custom requires --command")
        command = json.loads(args.command.read_text(encoding="utf-8"))
        if not isinstance(command, list) or not command or not all(isinstance(value, str) and value for value in command):
            raise ValueError("Custom command must be a non-empty array of arguments")
        if args.model:
            parser.error("Set custom model arguments in the command JSON")
    else:
        command = ["claude", "--print"] if args.agent == "claude" else ["codex", "exec", "--skip-git-repo-check", "--cd", str(args.workdir.resolve()), "-"]
        if args.model:
            command[1:1] = ["--model", args.model] if args.agent == "claude" else []
            if args.agent == "codex":
                command[-1:-1] = ["--model", args.model]
    if args.timeout <= 0:
        raise ValueError("Timeout must be positive")
    args.workdir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(command, input=args.prompt_file.read_text(encoding="utf-8"), text=True, cwd=args.workdir, timeout=args.timeout)
    return result.returncode
