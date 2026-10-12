"""Cache the exact installed distribution for the optional model environment."""
import base64
import csv
import hashlib
from importlib.metadata import distribution
import io
from pathlib import Path
import tempfile
import zipfile

from .runtime_paths import drawai_home


def runtime_install_arguments(source_root: Path):
    if (source_root / "pyproject.toml").is_file() and (source_root / "src/drawai").is_dir():
        return ["-e", str(source_root) + "[workbench]"]
    dist = distribution("drawai")
    fingerprint = hashlib.sha256((dist.read_text("RECORD") or "").encode()).hexdigest()[:12]
    output = drawai_home() / "cache" / f"drawai-{dist.version}-1{fingerprint}-py3-none-any.whl"
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.exists():
        records = []
        metadata_dir = None
        with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".whl", delete=False) as stream:
            temporary = Path(stream.name)
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file in dist.files or ():
                name = str(file).replace("\\", "/")
                first = name.split("/", 1)[0]
                if first not in {"drawai", "pptx_skill", "drawai_evaluation"} and not (first.startswith("drawai-") and first.endswith(".dist-info")):
                    continue
                if "__pycache__" in name or name.endswith((".pyc", "/RECORD", "/direct_url.json")):
                    continue
                if first.endswith(".dist-info"):
                    metadata_dir = first
                data = dist.locate_file(file).read_bytes()
                archive.writestr(name, data)
                digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
                records.append((name, "sha256=" + digest, str(len(data))))
            if metadata_dir is None:
                raise RuntimeError("Installed DrawAI wheel metadata is missing")
            name = metadata_dir + "/RECORD"
            records.append((name, "", ""))
            stream = io.StringIO()
            csv.writer(stream).writerows(records)
            archive.writestr(name, stream.getvalue())
        temporary.replace(output)
    return [str(output) + "[workbench]"]
