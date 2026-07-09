# OpenHands ACP Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-class OpenHands ACP provider, configure an OpenHands Codex subscription agent, and verify a complete real-image DrawAI run.

**Architecture:** Register OpenHands in DrawAI's existing ACP preset registry so config, workflow routing, and Workbench discovery inherit support. Keep OpenHands installation and subscription credentials external to DrawAI, and communicate only through the existing JSON-RPC stdio ACP client.

**Tech Stack:** Python 3.12, pytest, ACP JSON-RPC, OpenHands CLI/SDK, React/TypeScript Workbench, Node test runner, SVG/PPTX artifact validators.

---

### Task 1: Add the OpenHands ACP contract with TDD

**Files:**
- Modify: `tests/semantic_ppt/drawai_pipeline/test_acp_agent.py`
- Modify: `tests/semantic_ppt/drawai_pipeline/test_config.py`
- Modify: `tests/workbench/test_workflow_api.py`
- Modify: `src/drawai/acp_agent_presets.py`

- [x] **Step 1: Add failing preset and config expectations**

Add `openhands` to the expected command maps and parameterized config cases:

```python
"openhands": ("openhands", "acp", "--always-approve")
```

Add the Workbench tuple:

```python
("openhands_acp", "openhands", ("openhands", "acp", "--always-approve"))
```

- [x] **Step 2: Run the focused tests and verify RED**

Run:

```bash
uv run pytest \
  tests/semantic_ppt/drawai_pipeline/test_acp_agent.py \
  tests/semantic_ppt/drawai_pipeline/test_config.py \
  tests/workbench/test_workflow_api.py -q
```

Expected: failures show that `openhands`/`openhands_acp` is not registered.

- [x] **Step 3: Register the preset**

Add this value to `ACP_AGENT_PRESETS`:

```python
"openhands": AcpAgentPreset(
    agent_id="openhands",
    provider_id="openhands_acp",
    label="OpenHands ACP",
    executable="openhands",
    default_command=("openhands", "acp", "--always-approve"),
    description="OpenHands Agent Client Protocol provider for file-backed Agent tasks.",
    inline_image_blocks=False,
),
```

- [x] **Step 4: Run the focused tests and verify GREEN**

Run the Step 2 command. Expected: all selected tests pass.

- [x] **Step 5: Cover OpenHands transport and file-output constraints**

Keep local image paths in the controlled prompt while omitting inline base64 image
blocks for OpenHands. Require OpenHands to write SVG/JSON through `file_editor`
instead of long terminal here-doc commands, and preserve other ACP presets' inline
image behavior.

### Task 2: Add the real Workbench provider icon with TDD

**Files:**
- Modify: `apps/workbench/tests/agentProviderPresentation.test.mjs`
- Modify: `apps/workbench/src/agentProviderPresentation.ts`
- Create: `apps/workbench/public/agent-icons/openhands.svg`
- Create or modify: `apps/workbench/public/agent-icons/NOTICE.openhands-logo.txt`

- [x] **Step 1: Add the failing icon coverage expectation**

Add `openhands_acp` to `EXPECTED_AGENT_PROVIDER_IDS`.

- [x] **Step 2: Run the exact test and verify RED**

Run:

```bash
cd apps/workbench
node --test tests/agentProviderPresentation.test.mjs
```

Expected: `openhands_acp` has no icon mapping.

- [x] **Step 3: Add an upstream-sourced icon and mapping**

Add this mapping:

```ts
openhands_acp: {
  accent_color: "#111827",
  icon_url: "/agent-icons/openhands.svg"
},
```

Bundle the upstream icon and record its source/license in the notice file.

- [x] **Step 4: Run Workbench tests and build**

Run:

```bash
cd apps/workbench
npm test
npm run build
```

Expected: 0 failing tests and a successful TypeScript/Vite build.

### Task 3: Document installation, authentication, and configuration

**Files:**
- Modify: `README.md`
- Modify: `README-en.md`
- Modify: `docs/zh-CN/runtime-options.md`

- [x] **Step 1: Document first-class support in both READMEs**

Keep the bilingual feature lists aligned and name `OpenHands ACP` alongside the
other supported agents.

- [x] **Step 2: Add exact runtime configuration instructions**

Document:

```bash
uv tool install --force --python 3.12 \
  'openhands @ git+https://github.com/OpenHands/OpenHands-CLI.git@2df8a2835d3f1bd2f2eadf5a7a2e1ad0dfb0d271'
openhands acp --help
```

Explain that OpenHands must be configured with its own subscription OAuth grant for
the same ChatGPT account, and that DrawAI launches
`openhands acp --always-approve`.

- [x] **Step 3: Check documentation consistency**

Run:

```bash
rg -n "OpenHands|openhands" README.md README-en.md docs/zh-CN/runtime-options.md
```

Expected: support, install, authentication, command, and unattended-approval details
are present without tokens or machine-specific secrets.

### Task 4: Install and configure OpenHands subscription mode

**Files:**
- External state: `~/.local/share/uv/tools/openhands/`
- External state: `~/.openhands/auth/`
- External state: `~/.openhands/agent_settings.json`

- [x] **Step 1: Install and inspect OpenHands**

Run:

```bash
uv tool install --force --python 3.12 \
  'openhands @ git+https://github.com/OpenHands/OpenHands-CLI.git@2df8a2835d3f1bd2f2eadf5a7a2e1ad0dfb0d271'
openhands --version
openhands acp --help
```

Expected: the CLI and ACP command are available.

- [x] **Step 2: Create a native subscription LLM grant**

Use the OpenHands tool environment to call:

```python
LLM.subscription_login(vendor="openai", model="gpt-5.4-mini")
```

Authorize the same ChatGPT account reported by `codex login status`. Do not copy
`~/.codex/auth.json` tokens.

- [x] **Step 3: Persist an OpenHands CLI Agent**

Create the default CLI Agent from the subscription LLM and save it through
`openhands_cli.stores.AgentStore` to `~/.openhands/agent_settings.json`.

- [x] **Step 4: Verify subscription mode and a real model turn**

Load the saved Agent and assert:

```python
agent.llm.auth_type == "subscription"
agent.llm.is_subscription is True
```

Then run one real headless OpenHands prompt and require exit code 0.

### Task 5: Run the named JPEG end to end through OpenHands

**Files:**
- Input: `/Users/chunqiu/Downloads/飞书20260608-121219.jpg`
- Output: `/Users/chunqiu/Downloads/drawai-openhands-e2e/`

- [x] **Step 1: Build an external OpenHands base config**

Copy the runtime values from `configs/drawai/config.yaml` and override:

```yaml
v2:
  enabled: true
  refine:
    enabled: false
svg:
  generation_backend: acp_agent
  staged_generation: false
  visual_review_rounds: []
model_runtime:
  provider: acp-agent
  connection_id: openhands
  model_name: ""
  timeout_seconds: 3600
  max_concurrent: 1
  acp:
    agent: openhands
    command: [openhands, acp, --always-approve]
```

- [x] **Step 2: Run the full local pipeline**

Run:

```bash
uv run drawai run /Users/chunqiu/Downloads/飞书20260608-121219.jpg \
  --local \
  --device mps \
  --runtime-root /Users/chunqiu/.drawai \
  --base-config /Users/chunqiu/Downloads/drawai-openhands-e2e/openhands.yaml \
  --out /Users/chunqiu/Downloads/drawai-openhands-e2e/runs \
  --run-name openhands_acp_final_verified
```

Expected: exit code 0 and pipeline status `ok`.

- [x] **Step 3: Audit real artifacts**

Require a complete semantic SVG, rendered PNG, and PPTX. Parse the SVG as XML,
inspect the rendered PNG, run `unzip -t` on the PPTX, and verify at least one slide
with `python-pptx`.

- [x] **Step 4: Confirm OpenHands was actually used**

Inspect execution manifests and ACP traces. Require provider id `openhands_acp` or
ACP agent `openhands`, the real `openhands acp --always-approve` command, and
non-empty model/agent events.

### Task 6: Full verification and commit

**Files:**
- All modified repository files

- [x] **Step 1: Run the full Python suite**

```bash
uv run pytest -q
```

Expected: 0 failures.

- [x] **Step 2: Run Workbench tests and build again**

```bash
cd apps/workbench
npm test
npm run build
```

Expected: 0 failures and a successful build.

- [x] **Step 3: Review repository state**

```bash
git diff --check
git status --short
git diff --stat
```

Expected: only the intended provider, presentation, icon, tests, and docs changes.

- [x] **Step 4: Commit the implementation**

```bash
git add src tests apps/workbench README.md README-en.md docs
git commit -m "feat(agent): add OpenHands ACP provider"
```
