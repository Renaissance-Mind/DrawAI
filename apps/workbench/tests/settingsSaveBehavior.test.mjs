import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("detail save closes API preset and image generation dialogs after a successful save", () => {
  const source = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");

  assert.match(source, /type SaveSettingsOptions = \{/);
  assert.match(source, /closeDetailOnSuccess\?: boolean/);
  assert.match(source, /closeSettingsDetail\(\{ discardApiDraft: false \}\)/);
  assert.match(
    source,
    /saveSettings\(\{[\s\S]*?agentSettingsOverride:[\s\S]*?closeDetailOnSuccess: settingsCategory === "api" \|\| settingsCategory === "imagegen"/
  );
  assert.match(source, /saveSettings\(\{ agentSettingsOverride: nextDraft \}\)/);
});
