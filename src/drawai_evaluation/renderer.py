from __future__ import annotations

import hashlib
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

from lxml import etree


def referenced_asset_hashes(svg_path: Path) -> dict[str, str]:
    root = etree.fromstring(
        svg_path.read_bytes(), etree.XMLParser(resolve_entities=False, no_network=True)
    )
    references: set[str] = set()
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        for key, value in element.attrib.items():
            if etree.QName(key).localname in {"href", "src"}:
                references.add(value)
            references.update(re.findall(r"url\(\s*[\'\"]?([^\'\"\)]+)", value))
        if etree.QName(element).localname == "style" and element.text:
            references.update(re.findall(r"url\(\s*[\'\"]?([^\'\"\)]+)", element.text))
    hashes = {}
    for reference in sorted(references):
        reference = reference.strip()
        if not reference or reference.startswith(("#", "data:")):
            continue
        parsed = urlsplit(reference)
        if parsed.scheme not in ("", "file") or parsed.netloc:
            raise ValueError(f"embed remote resources before evaluation: {reference}")
        path = Path(unquote(parsed.path))
        if not path.is_absolute():
            path = svg_path.parent / path
        hashes[reference] = (
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"
        )
    return hashes


_DIMENSION_RE = re.compile(r"^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))(?:px)?\s*$", re.IGNORECASE)


_BROWSER_RENDERER_ENV = "DRAWAI_SVG_RENDERER_BROWSER"


_BROWSER_RENDER_TIMEOUT_SECONDS = 600


_BROWSER_RENDERER_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]


_BROWSER_RENDERER_NAMES = [
    "google-chrome",
    "chromium",
    "chromium-browser",
    "microsoft-edge",
]


def _browser_renderer_path() -> Path | None:
    configured = os.environ.get(_BROWSER_RENDERER_ENV)
    if configured:
        if configured.strip().lower() in {"0", "false", "none", "off", "disabled"}:
            return None
        path = Path(configured)
        if path.exists() and os.access(path, os.X_OK):
            return path

    for candidate in _browser_renderer_candidate_paths():
        path = Path(candidate)
        if path.exists() and os.access(path, os.X_OK):
            return path

    for name in _BROWSER_RENDERER_NAMES:
        found = shutil.which(name)
        if found:
            return Path(found)

    return None


def _browser_renderer_candidate_paths() -> list[str]:
    candidates = list(_BROWSER_RENDERER_PATHS)
    if os.name != "nt":
        return candidates

    browser_parts = [
        ("Google", "Chrome", "Application", "chrome.exe"),
        ("Microsoft", "Edge", "Application", "msedge.exe"),
    ]
    for root_name in ("ProgramFiles", "ProgramFiles(x86)", "LocalAppData"):
        root = os.environ.get(root_name)
        if not root:
            continue
        for parts in browser_parts:
            candidates.append(str(Path(root, *parts)))
    return candidates


def _render_svg_with_browser(
    root: etree._Element, svg_dir: Path, rendered_path: Path, browser_path: Path
) -> str | None:
    canvas = _canvas_from_svg_root(root)
    if canvas is None:
        return "could not infer canvas size"

    width, height = canvas
    rendered_path.parent.mkdir(parents=True, exist_ok=True)
    rendered_path.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="drawai-svg-browser-profile-") as temp_dir:
        with tempfile.NamedTemporaryFile(
            prefix=".drawai-render-", suffix=".svg", dir=svg_dir, delete=False
        ) as handle:
            svg_path = Path(handle.name)
            handle.write(etree.tostring(root, xml_declaration=True, encoding="utf-8"))
        user_data_dir = Path(temp_dir) / "browser-profile"
        command = [
            str(browser_path),
            "--headless=new",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--hide-scrollbars",
            "--no-first-run",
            "--no-default-browser-check",
            "--allow-file-access-from-files",
            *_browser_renderer_keychain_flags(),
            f"--user-data-dir={user_data_dir}",
            f"--window-size={width},{height}",
            "--force-device-scale-factor=1",
            f"--screenshot={rendered_path}",
            svg_path.as_uri(),
        ]
        process: subprocess.Popen[str] | None = None
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=os.name == "posix",
            )
            deadline = time.monotonic() + _BROWSER_RENDER_TIMEOUT_SECONDS
            while time.monotonic() < deadline:
                if rendered_path.exists() and rendered_path.stat().st_size > 0:
                    _stop_browser_renderer(process)
                    return None
                if process.poll() is not None:
                    break
                time.sleep(0.2)

            if process.poll() is None:
                _stop_browser_renderer(process, force=True)
                return f"timed out after {_BROWSER_RENDER_TIMEOUT_SECONDS} seconds"

            stdout, stderr = process.communicate(timeout=5)
        except OSError as exc:
            return str(exc)
        except subprocess.TimeoutExpired:
            if process is not None:
                _stop_browser_renderer(process, force=True)
            return "browser renderer did not finish after process exit"
        finally:
            svg_path.unlink(missing_ok=True)

    if not rendered_path.exists():
        if process is not None and process.returncode != 0:
            return (stderr or stdout or f"exit code {process.returncode}").strip()
        return "browser completed without writing screenshot"
    return None


def _browser_renderer_keychain_flags(platform: str | None = None) -> list[str]:
    if (platform or sys.platform) != "darwin":
        return []
    return ["--use-mock-keychain", "--password-store=basic"]


def _stop_browser_renderer(process: subprocess.Popen[str], *, force: bool = False) -> None:
    if process.poll() is not None:
        return
    signal_value = signal.SIGKILL if force else signal.SIGTERM
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal_value)
        elif force:
            process.kill()
        else:
            process.terminate()
        process.wait(timeout=5)
    except ProcessLookupError:
        return
    except subprocess.TimeoutExpired:
        if not force:
            _stop_browser_renderer(process, force=True)


def _canvas_from_svg_root(root: etree._Element) -> tuple[int, int] | None:
    viewbox = root.get("viewBox")
    values = _parse_number_list(viewbox or "")
    if values is not None and len(values) == 4 and values[2] > 0 and values[3] > 0:
        return max(1, int(round(values[2]))), max(1, int(round(values[3])))
    width = _parse_dimension(root.get("width") or "")
    height = _parse_dimension(root.get("height") or "")
    if width is not None and height is not None and width > 0 and height > 0:
        return max(1, int(round(width))), max(1, int(round(height)))
    return None


def _parse_number_list(raw: str) -> tuple[float, ...] | None:
    parts = [part for part in re.split(r"[\s,]+", raw.strip()) if part]
    values: list[float] = []
    for part in parts:
        try:
            values.append(float(part))
        except ValueError:
            return None
    return tuple(values)


def _parse_dimension(raw: str) -> float | None:
    match = _DIMENSION_RE.match(raw)
    if not match:
        return None
    return float(match.group(1))
