import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("API preset detail save closes the detail dialog after a successful save", () => {
  const source = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");

  assert.match(source, /type SaveSettingsOptions = \{/);
  assert.match(source, /closeDetailOnSuccess\?: boolean/);
  assert.match(source, /closeSettingsDetail\(\{ discardApiDraft: false \}\)/);
  assert.match(source, /saveSettings\(\{ closeDetailOnSuccess: settingsCategory === "api" \}\)/);
  assert.match(source, /saveSettings\(\{ agentSettingsOverride: nextDraft \}\)/);
});
