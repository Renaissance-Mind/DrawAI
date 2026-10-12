"""Optional dependencies are enabled in the installed DrawAI environment."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from .runtime_paths import drawai_home, initialize_home, runtime_path, workspace_path

CAPABILITIES = {
    "workbench": {"modules": ["fastapi", "uvicorn", "multipart", "numpy", "cairosvg"], "requirements": ["fastapi>=0.116.0", "uvicorn>=0.35.0", "python-multipart>=0.0.20", "numpy", "cairosvg>=2.9.0"]},
    "images": {"modules": [], "requirements": []},
    "llm": {"modules": ["openai"], "requirements": ["openai"]},
    "codex": {"modules": ["openai_codex"], "requirements": ["openai-codex"]},
    "claude": {"modules": ["claude_agent_sdk"], "requirements": ["claude-agent-sdk>=0.2.119"]},
    "agents": {"modules": ["openai", "openai_codex", "claude_agent_sdk"], "requirements": ["openai", "openai-codex", "claude-agent-sdk>=0.2.119"]},
}


def missing_modules(capability):
    return [module for module in CAPABILITIES[capability]["modules"] if importlib.util.find_spec(module) is None]


def require_capability(capability):
    missing = missing_modules(capability)
    if missing:
        raise RuntimeError(f"DrawAI {capability} dependencies are missing ({', '.join(missing)}). Run: drawai setup --enable {capability}")


def pip_command(requirements, python=None):
    python = str(python or sys.executable)
    uv = shutil.which("uv")
    if uv:
        return [uv, "pip", "install", "--python", python, "--prerelease", "allow", *requirements]
    return [python, "-m", "pip", "install", "--pre", *requirements]


def system_commands(kind):
    if kind == "preview":
        if shutil.which("brew"):
            commands = []
            if not shutil.which("soffice"):
                commands.append(["brew", "install", "--cask", "libreoffice"])
            if not shutil.which("pdftoppm"):
                commands.append(["brew", "install", "poppler"])
            return commands
        if shutil.which("apt-get"):
            prefix = [] if hasattr(os, "geteuid") and os.geteuid() == 0 else ["sudo"]
            return [[*prefix, "apt-get", "update"], [*prefix, "apt-get", "install", "-y", "libreoffice", "poppler-utils"]]
    elif kind == "formulas" and shutil.which("brew"):
        return [["brew", "install", "pandoc"]]
    elif kind == "formulas" and shutil.which("apt-get"):
        prefix = [] if hasattr(os, "geteuid") and os.geteuid() == 0 else ["sudo"]
        return [[*prefix, "apt-get", "update"], [*prefix, "apt-get", "install", "-y", "pandoc"]]
    raise RuntimeError(f"Install {'LibreOffice and Poppler' if kind == 'preview' else 'Pandoc'} with your OS package manager, then run drawai doctor")


def capability_status():
    checks = {name: {"available": not missing_modules(name), "missing": missing_modules(name)} for name in CAPABILITIES}
    checks["presentation"] = {"available": importlib.util.find_spec("pptx_skill") is not None}
    checks["preview"] = {"available": bool(shutil.which("soffice") and shutil.which("pdftoppm"))}
    checks["formulas"] = {"available": bool(shutil.which("pandoc"))}
    checks["models"] = {"available": (runtime_path() / ".venv").is_dir()}
    return {"home": str(drawai_home()), "workspace": str(workspace_path()), "python": sys.executable, "capabilities": checks}


def setup_cli(argv):
    parser = argparse.ArgumentParser(prog="drawai setup", description="Prepare one DrawAI installation for Session, Workbench and CLI.")
    parser.add_argument("--enable", action="append", choices=(*CAPABILITIES, "preview", "formulas", "models"), default=[])
    parser.add_argument("--agent", action="append", choices=("codex", "claude", "generic"), default=[])
    parser.add_argument("--output-dir", type=Path, help="Session integration export directory; generic hosts can load this directory.")
    parser.add_argument("--workspace", type=Path, help="Use an existing workspace without moving or overwriting its data.")
    parser.add_argument("--runtime-root", type=Path, help="Reuse an existing optional model runtime.")
    parser.add_argument("--install-system", action="store_true", help="Install requested preview/formula OS tools using the available package manager.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--device", choices=("cpu", "gpu", "mps", "auto"), default="cpu")
    args = parser.parse_args(argv)
    commands = []
    if not args.dry_run:
        from .runtime_paths import write_preferences
        fields = {}
        if args.workspace:
            fields["workspace"] = str(args.workspace.expanduser().resolve())
        if args.runtime_root:
            fields["runtime_root"] = str(args.runtime_root.expanduser().resolve())
        if fields:
            write_preferences(fields)
    for name in dict.fromkeys(args.enable):
        if name in CAPABILITIES:
            if missing_modules(name):
                commands.append(pip_command(CAPABILITIES[name]["requirements"]))
        elif name in {"preview", "formulas"}:
            tools = ("soffice", "pdftoppm") if name == "preview" else ("pandoc",)
            if not all(shutil.which(tool) for tool in tools):
                if args.install_system:
                    commands.extend(system_commands(name))
                elif not args.dry_run:
                    raise RuntimeError(f"{name} tools are missing; run drawai setup --enable {name} --install-system, or install them with your OS package manager")
        elif name == "models":
            root = args.runtime_root.expanduser().resolve() if args.runtime_root else runtime_path()
            commands.append([sys.executable, "-m", "drawai.cli", "setup", "local", "--runtime-root", str(root), "--device", args.device, "--vision-only", "--skip-doctor"])
    if args.dry_run:
        print(json.dumps({"home": str(drawai_home()), "commands": commands, "agents": args.agent}, ensure_ascii=False, indent=2))
        return 0
    initialize_home()
    for command in commands:
        subprocess.run(command, check=True)
    from .runtime_paths import read_preferences, write_preferences
    enabled = list(dict.fromkeys([*read_preferences().get("enabled_capabilities", []), *args.enable]))
    # The optional vision environment uses this same core. SDKs enter it only
    # after the user enables that executor, including enables made before models.
    from .local_setup import runtime_venv_python
    model_python = runtime_venv_python(runtime_path())
    if model_python.is_file():
        for name in ("llm", "codex", "claude", "agents"):
            if name in enabled:
                probe = subprocess.run([str(model_python), "-c", "import importlib.util,sys; sys.exit(any(importlib.util.find_spec(n) is None for n in sys.argv[1:]))", *CAPABILITIES[name]["modules"]], capture_output=True)
                if probe.returncode:
                    subprocess.run(pip_command(CAPABILITIES[name]["requirements"], model_python), check=True)
    write_preferences({"enabled_capabilities": enabled})
    if args.agent:
        from .session_install import install_session
        for agent in dict.fromkeys(args.agent):
            install_session(agent, output_dir=args.output_dir)
    print(json.dumps(capability_status(), ensure_ascii=False, indent=2))
    return 0


def doctor_cli(argv):
    parser = argparse.ArgumentParser(prog="drawai doctor")
    parser.add_argument("--require", action="append", choices=(*CAPABILITIES, "presentation", "preview", "formulas", "models"), default=[])
    args = parser.parse_args(argv)
    result = capability_status()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(any(not result["capabilities"][name]["available"] for name in args.require))
