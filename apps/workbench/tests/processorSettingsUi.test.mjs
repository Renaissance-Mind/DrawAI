import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("processor cards expose enable switches and disable unavailable processors", () => {
  const source = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
  const css = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");
  const processorGridBlock = source.match(/\{settingsCategory === "processor" && \([\s\S]*?<div className="settings-model-grid" aria-label="Processors">[\s\S]*?\{processorIds\.map[\s\S]*?\}\)\}/)?.[0] || "";
  const processorDetailBlock = source.match(/\{settingsCategory === "processor" && \([\s\S]*?\{selectedProcessor && selectedProcessorSetting \? \([\s\S]*?<label className="settings-field">/)?.[0] || "";

  assert.match(processorGridBlock, /const processorEnabled = Boolean\(setting\?\.enabled\);/);
  assert.match(processorGridBlock, /const driver = processorDrivers\[setting\?\.driver_id \|\| definition\.default_driver_id\];/);
  assert.match(processorGridBlock, /const processorAvailable = processorCardAvailable\(setting, status, driver, apiDrafts\);/);
  assert.match(processorGridBlock, /className=\{`settings-model-card settings-processor-card\$\{selectedProcessorId === processorId \? " active" : ""\}\$\{processorAvailable \? "" : " disabled"\}`\}/);
  assert.match(processorGridBlock, /className="settings-processor-toggle"/);
  assert.match(processorGridBlock, /type="checkbox"[\s\S]*checked=\{processorEnabled\}[\s\S]*disabled=\{!processorAvailable\}/);
  assert.match(processorGridBlock, /aria-label=\{`\$\{processorEnabled \? "关闭" : "启用"\}\$\{definition\.label\}`\}/);
  assert.doesNotMatch(processorDetailBlock, /<span>启用 \{selectedProcessor\.processing_type\}<\/span>/);
  assert.match(css, /\.settings-processor-card\.disabled\s*\{[\s\S]*?background:\s*#f8fafc;/);
  assert.match(css, /\.settings-processor-toggle\s+input\s*\{[\s\S]*?position:\s*absolute;/);
  assert.match(css, /\.settings-processor-toggle\s+input:checked\s*\+\s*span\s*\{[\s\S]*?background:\s*var\(--teal\);/);
  assert.match(css, /\.settings-processor-toggle\s+input:disabled\s*\+\s*span\s*\{[\s\S]*?cursor:\s*not-allowed;/);
});
