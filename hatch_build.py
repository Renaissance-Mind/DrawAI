"""Build one wheel containing the shared core, skills and prebuilt UI."""
from pathlib import Path
import os
import shutil
import subprocess
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

# PyPI wheels are built with the UI already compiled (DRAWAI_PREBUILT_UI=1).
# Source checkouts and sdists compile it here, which needs Node.
_NODE_HELP = (
    "Building DrawAI from a source checkout or sdist requires Node.js 20.19+ or 22.12+ "
    "so npm can compile the Workbench UI into the wheel. "
    "A wheel published to PyPI already contains that UI: `pip install drawai` and "
    "`uvx drawai` do not need Node. "
    "If apps/workbench/dist and apps/workbench/dist-plugin are already built, "
    "set DRAWAI_PREBUILT_UI=1."
)


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        if self.target_name != "wheel":
            return
        root = Path(self.root)
        app = root / "apps/workbench"
        if os.environ.get("DRAWAI_PREBUILT_UI") != "1":
            npm = "npm.cmd" if os.name == "nt" else "npm"
            if shutil.which(npm) is None:
                raise RuntimeError(_NODE_HELP)
            subprocess.run([npm, "ci"], cwd=app, check=True)
            for command in ("build", "build:plugin"):
                subprocess.run([npm, "run", command], cwd=app, check=True)
        for entry in ("dist/index.html", "dist-plugin/templates-inline.html"):
            if not (app / entry).is_file():
                raise FileNotFoundError(_NODE_HELP + " Missing " + entry + ".")
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
