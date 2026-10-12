"""Build one wheel containing the shared core, skills and prebuilt UI."""
from pathlib import Path
import os
import subprocess
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        if self.target_name != "wheel":
            return
        root = Path(self.root)
        app = root / "apps/workbench"
        # Source builds require Node; the resulting installed wheel does not.
        if os.environ.get("DRAWAI_PREBUILT_UI") != "1":
            npm = "npm.cmd" if os.name == "nt" else "npm"
            subprocess.run([npm, "ci"], cwd=app, check=True)
            for command in ("build", "build:plugin"):
                subprocess.run([npm, "run", command], cwd=app, check=True)
        for entry in ("dist/index.html", "dist-plugin/templates-inline.html"):
            if not (app / entry).is_file():
                raise FileNotFoundError("Build DrawAI UI before using DRAWAI_PREBUILT_UI=1: " + entry)
        resources = {
            "configs": "configs", "templates": "templates", "scripts": "scripts",
            "skills/drawai-readme": "skills/drawai-readme",
            "skills/drawai-design": "skills/drawai-design",
            "skills/drawai-image2ppt": "skills/drawai-image2ppt",
            "apps/workbench/dist": "apps/workbench/dist",
            "apps/workbench/dist-plugin": "apps/workbench/dist-plugin",
            "apps/workbench/templates/data": "apps/workbench/templates/data",
            "apps/workbench/public/drawai_image.png": "apps/workbench/public/drawai_image.png",
        }
        force = build_data.setdefault("force_include", {})
        for source, target in resources.items():
            force[str(root / source)] = "drawai/_resources/" + target
