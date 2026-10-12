"""Serve the prebuilt Workbench with the same Python runtime as the CLI."""
import os
from pathlib import Path
import subprocess
import sys

from .capabilities import require_capability
from .runtime_paths import base_config_path, initialize_home, runtime_path, workspace_path, write_preferences
from .resources import resource_path


def mount_frontend(app):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(resource_path("apps/workbench/dist")), html=True), name="workbench")


def run_workbench(args):
    require_capability("workbench")
    initialize_home()
    if args.api_url:
        return run_frontend_proxy(args.api_url, args.host, args.port)
    processes = []
    connect_host = connection_host(args.host)
    model_api = args.model_api or os.environ.get("DRAWAI_MODEL_API", "http://127.0.0.1:18080")
    env = os.environ.copy()
    start_model = args.start_model
    if start_model:
        from urllib.parse import urlparse
        if urlparse(model_api).hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("--start-model requires a local model API address")
        from .local_setup import runtime_venv_python
        python = runtime_venv_python(runtime_path())
        if not python.is_file():
            raise RuntimeError("Local model runtime is missing; run drawai setup --enable models")
        port = str(urlparse(model_api).port or 18080)
        processes.append(subprocess.Popen([str(python), "-m", "drawai.cli", "server", "model", "--runtime-root", str(runtime_path()), "--device", args.device, "--sam-port", port, "--ocr-port", port], env=env))
    from .workbench.api import create_app, settings_from_env
    from .workbench.models import WorkbenchSettings
    import uvicorn
    api_url = f"http://{connect_host}:{args.port}"
    write_preferences({"workbench_api_url": api_url, "workbench_ui_url": api_url + "/"})
    from dataclasses import replace
    settings = settings_from_env()
    if args.model_api or os.environ.get("DRAWAI_MODEL_API"):
        settings = replace(settings, sam3_base_url=model_api, ocr_base_url=model_api, rmbg_base_url=model_api)
    app = create_app(settings)
    mount_frontend(app)
    print(f"Workbench and API: {api_url}/", flush=True)
    print(f"Shared workspace: {workspace_path()}", flush=True)
    try:
        uvicorn.run(app, host=args.host, port=args.port)
    finally:
        for process in processes:
            process.terminate()
            process.wait(timeout=10)
    return 0


def run_frontend_proxy(api_url, host, port):
    import urllib.request
    import urllib.error
    from fastapi import FastAPI, Request
    from fastapi.responses import Response
    import uvicorn
    from urllib.parse import urlparse
    if urlparse(api_url).scheme not in {"http", "https"} or not urlparse(api_url).hostname:
        raise ValueError("--api must be an absolute HTTP(S) URL")
    connect_host = connection_host(host)
    write_preferences({"workbench_api_url": api_url.rstrip("/"), "workbench_ui_url": f"http://{connect_host}:{port}/"})
    app = FastAPI(title="DrawAI Workbench frontend")

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
    async def proxy(path: str, request: Request):
        import asyncio
        body = await request.body()
        headers = {key: value for key, value in request.headers.items() if key.lower() in {"content-type", "authorization", "accept"}}
        url = api_url.rstrip("/") + "/api/" + path + ("?" + str(request.query_params) if request.query_params else "")
        def send():
            outgoing = urllib.request.Request(url, data=body or None, headers=headers, method=request.method)
            try:
                result = urllib.request.urlopen(outgoing, timeout=600)
            except urllib.error.HTTPError as error:
                result = error
            with result:
                return Response(result.read(), status_code=result.status, media_type=result.headers.get("Content-Type"))
        return await asyncio.to_thread(send)

    mount_frontend(app)
    uvicorn.run(app, host=host, port=port)
    return 0


def connection_host(host):
    if host in {"0.0.0.0", "::", "[::]"}:
        return "127.0.0.1"
    return "[" + host + "]" if ":" in host and not host.startswith("[") else host
