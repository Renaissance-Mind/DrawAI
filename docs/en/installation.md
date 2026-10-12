# One DrawAI installation

Session, Workbench and CLI use the same Python core, template resources, API connections and presentation toolkit. Image generation and the implementation Agent are independent choices. Sessions default to the current Agent's real configuration; standalone execution reads the shared Workbench settings.

## Install and enable capabilities

From this checkout, installation builds and packages the frontend automatically. Source builds require Node.js 20.19+ or 22.12+. uv can provision Python 3.12:

```bash
uv tool install --python 3.12 .
drawai setup
drawai doctor
```

A prebuilt wheel needs neither Node nor the source checkout:

```bash
uv tool install --python 3.12 /path/to/drawai-0.2.0-py3-none-any.whl
```

Build a wheel with `uv build --wheel`. This describes the current source distribution; it does not assert that 0.2.0 is published to a public registry. Update the installation with `uv tool install --reinstall --python 3.12 <source>`, then register your Session host again.

Enable only the required capabilities in the same environment:

```bash
drawai setup --agent codex
# Claude Code: drawai setup --agent claude
drawai setup --enable workbench
drawai setup --enable llm
# Optional SDKs: --enable codex, --enable claude, or --enable agents
drawai setup --enable preview --install-system
# Optional formula support: --enable formulas --install-system
# Optional local vision models: --enable models --device cpu
```

The base package includes PPT authoring, visual manifests, Session planning, templates and Images API support. Host CLI backends use their existing installation and authentication; SDK dependencies are optional. OS preview/formula installation supports Homebrew and apt-get; other platforms install LibreOffice, Poppler or Pandoc through their package manager. `drawai setup --dry-run` makes no changes. `drawai doctor --require workbench --require preview` checks readiness without requiring unused capabilities.

## Shared configuration

`DRAWAI_HOME` defaults to `~/.drawai`. It contains `config.yaml`, `preferences.json`, `workbench/settings`, task data, optional model runtime and host integrations. API presets are the same files used by Workbench and CLI; configuration output masks keys.

Reuse existing workspaces and model files without moving their data:

```bash
drawai setup --workspace /existing/.local/workbench --runtime-root /existing/.local/drawai_runtime
```

Existing `DRAWAI_WORKBENCH_WORKSPACE`, `DRAWAI_LOCAL_RUNTIME_ROOT` and `DRAWAI_WORKBENCH_DEFAULT_CONFIG` overrides remain supported. Workbench settings can create image/LLM connections, or import the same JSON:

```bash
drawai config connections --import connections.json
drawai config image --source api --connection personal-images
drawai config agent --provider drawai_tool_agent --connection personal-llm --endpoint chat
```

An image preset uses `type=images_api`, `base_url`, `model` and `api_key_env`. An LLM preset uses `type=llm` and `endpoints`, each with an id, protocol type, URL, model and key reference. Protocol types are `llm_chat_completions`, `llm_responses`, and `llm_anthropic`; the selected executor must support the selected protocol. The built-in API tool Agent currently uses Chat Completions and requires tool calling. Vision tasks require image input support. See the [complete connection example](../zh-CN/installation.md).

## Session

Register your host, open a new chat and use `$drawai-readme`. The current Claude, Codex or other capable Agent performs the final work with its own model, reasoning settings and permissions. Unknown versions do not replace that Agent. Missing capabilities are reported.

Images may come from the host image tool, a user API, existing pages or real local rendering. Selecting an image API does not select another implementation Agent:

```bash
drawai image generate --connection personal-images --prompt "Actual page content" --output-dir visuals --stem page-001
drawai image edit --connection personal-images --source visuals/page-001.png --prompt "Actual changes" --output-dir visuals --stem page-001-v2
```

Only explicit user selection starts another Agent. Its own model/configuration is inherited unless `--model` is specified:

```bash
drawai session execute --agent claude --prompt-file task.md --workdir /path/to/task
```

Custom hosts can load `drawai session install --host generic --output-dir /path/to/adapter`; explicit custom execution accepts `--agent custom --command command.json` with an argument array and prompt on stdin.

## Workbench and CLI

```bash
drawai setup --enable workbench
drawai workbench
```

Open `http://127.0.0.1:8890/`. One Python process serves UI and API, using prebuilt assets. Add `--start-model` only to start a prepared local vision runtime. A chosen pipeline still requires its configured processors and models. Developer Vite mode remains available through `--dev`.

```bash
drawai visual save visual-spec.json visual-deck.json
drawai presentation export deck.document.json --pptx output/deck.pptx
drawai presentation inspect output/deck.pptx --output output/inventory.json
drawai presentation render output/deck.pptx --output-dir output/preview
drawai ppt edit source.pptx --plan changes.json --output output/edited.pptx
```

Explicit Flow delegation uses the same transport in CLI and MCP:

```bash
drawai flow submit --manifest /absolute/visual-deck.json --agent-settings task-agent.json
drawai flow start --batch-id batch_RETURNED_ID
drawai flow status --batch-id batch_RETURNED_ID
drawai flow export --batch-id batch_RETURNED_ID --output /absolute/output/deck.pptx
```

A Session supplies the planner's `implementation.flow_agent_settings` as per-task settings to preserve the caller Agent and known model parameters. Credentials remain at the execution host; global settings are retained. A user explicitly choosing the configured Workbench Agent can omit that override. Standalone uploads default to shared Workbench settings.

`drawai config flow --api-url <API> --ui-url <UI>` saves the common addresses. Legacy `drawai run ... --local`, pipeline stages and skill scripts remain compatible, using packaged resources and the same core. CLI image runs use saved Workbench Agent settings when configured.

## Server distribution

The Docker image builds and installs the same wheel and includes CPU PPT preview tools:

```bash
docker build -t drawai .
docker run --rm -p 8890:8890 -v drawai-data:/data drawai
```

Data is persisted under `/data`. Cloud mode disables server-local directory uploads. This is a single-workspace deployment for controlled environments. Multi-user authentication, tenant isolation, encrypted credential services, durable distributed scheduling and quotas remain separate service work and must be implemented before offering a public multi-user service.
