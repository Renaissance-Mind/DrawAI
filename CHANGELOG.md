# Changelog / 更新日志

All notable public updates are grouped by date. Each date lists user-facing feature changes and important capability updates.

## 2026-06-18

- Added the Agent CLI backend for run0 asset analysis and SVG generation, with support for `codex cli`, `claude`, `kimi-code`, and custom agent commands.
- Added Codex SDK image generation and editing support, and exposed those image-generation flows in the Workbench.
- Added native Windows deployment support, including packaged Codex CLI detection, launcher output flushing, platform-safe launcher tests, and README documentation.
- Added Workbench runtime and queue visibility so users can see backend runtime status while tasks are running.
- Hardened inherited Codex provider configuration so local and nested runtime configs resolve more reliably.
- Improved SVG generation resilience by extending Codex recovery timeout behavior and disabling SAM mask output by default in the public path.
- Updated public documentation with the GitHub-hosted demo video, audio demo link, supported agent/model notes, AutoFigure-Edit acknowledgement, and cleanup of tracked development-only docs.

## 2026-06-17

- Published the initial DrawAI source snapshot.
- Added polygon and irregular mask geometry support in the asset pipeline.
- Exposed mask and polygon geometry in asset review so users can inspect richer asset boundaries before SVG/PPTX generation.
