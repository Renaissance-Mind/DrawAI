# OpenHands ACP Integration Design

## Objective

Add OpenHands as a first-class DrawAI ACP provider, configure the locally installed
OpenHands agent to use the same ChatGPT subscription account used by Codex, and
prove the integration with a complete DrawAI run of
`/Users/chunqiu/Downloads/飞书20260608-121219.jpg`.

## Decision

DrawAI will launch OpenHands through ACP rather than through OpenHands headless CLI
output parsing or a direct OpenHands SDK dependency.

The provider identity is:

- ACP agent id: `openhands`
- Workbench provider id: `openhands_acp`
- Display label: `OpenHands ACP`
- Executable: `openhands`
- Default command: `openhands acp --always-approve`

`--always-approve` is required for unattended DrawAI runs. DrawAI already constrains
the ACP workspace and validates declared output paths. A confirmation-oriented
OpenHands command remains available through DrawAI's custom command configuration
when a human is present.

## Alternatives Considered

### Custom ACP configuration only

DrawAI can already run a custom ACP command. This is useful as a diagnostic but does
not satisfy first-class support: OpenHands would be absent from config validation,
Workbench discovery, provider labels, icon presentation, and regression tests.

### Parse OpenHands headless CLI output

The headless CLI is suitable for shell automation, but its output is not DrawAI's
agent protocol. Parsing terminal output would lose ACP filesystem, image, permission,
terminal, session, and structured-event semantics.

### Embed OpenHands SDK into DrawAI

This would make OpenHands a Python dependency of DrawAI and duplicate lifecycle,
tool, and authentication responsibilities already exposed by `openhands acp`. It
would also couple DrawAI releases to the OpenHands SDK version.

## Components

### Provider registry

`src/drawai/acp_agent_presets.py` owns the new preset. Existing registry-derived
Workbench and workflow maps then expose `openhands_acp` without new routing branches.

### Workbench presentation

`apps/workbench/src/agentProviderPresentation.ts` maps `openhands_acp` to a bundled
OpenHands icon. The icon is sourced from an upstream project or an existing licensed
icon set; no placeholder or hand-drawn substitute is used.

### Authentication

OpenHands uses its native subscription mode:

1. Install OpenHands with `uv tool install openhands --python 3.12`.
2. Call `LLM.subscription_login(vendor="openai", ...)` using the same ChatGPT account
   that `codex login status` reports as logged in.
3. Persist an OpenHands CLI Agent whose LLM has `auth_type="subscription"`.
4. Keep OpenHands credentials under `~/.openhands/auth/` and Codex credentials under
   `~/.codex/`; do not copy refresh tokens between clients.

The separate OAuth grant avoids refresh-token rotation conflicts while using the
same ChatGPT subscription entitlement.

### Runtime flow

For each DrawAI agent task:

1. DrawAI starts `openhands acp --always-approve` over stdio.
2. DrawAI initializes ACP and opens a session rooted at the stage workspace.
3. DrawAI sends the controlled prompt and local image blocks.
4. OpenHands uses its subscription-backed Codex model and its own tools.
5. DrawAI validates required files, records ACP trace/stdout/stderr, and continues the
   pipeline.

## Error Handling

- Missing executable is reported by the existing Workbench discovery path.
- Missing OpenHands Agent settings produces the ACP authentication error from the
  OpenHands server and remains visible in DrawAI's ACP stderr/trace artifacts.
- Permission prompts cannot deadlock an unattended run because the default preset
  uses `--always-approve`.
- A process failure, malformed ACP response, timeout, missing declared output, or
  output outside the stage workspace continues to fail through DrawAI's existing
  explicit ACP errors.

## Verification

Automated verification covers:

- preset support, label, executable, and exact default command;
- config parsing for `model_runtime.acp.agent: openhands`;
- Workbench discovery and generated case configuration;
- Workbench icon coverage and bundled asset existence;
- the complete Python and Workbench test suites.

Real verification covers:

- OpenHands CLI version and persisted subscription mode;
- a real DrawAI-to-OpenHands ACP handshake and model turn;
- a full local DrawAI run of the named JPEG with OpenHands selected;
- successful pipeline summary and required SVG, rendered PNG, and PPTX artifacts;
- SVG/XML validity, PNG visual inspection, and PPTX ZIP/slide/media checks.

## Success Criteria

The work is complete only when the repository tests pass, OpenHands is discoverable
as `openhands_acp`, the installed OpenHands agent makes a real subscription-backed
Codex request, the named JPEG finishes the full DrawAI pipeline through OpenHands,
the output artifacts pass structural and visual checks, and all repository changes
are committed on the feature branch.
