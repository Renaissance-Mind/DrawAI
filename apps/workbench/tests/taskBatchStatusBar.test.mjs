import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("expanded case view keeps a centered icon-only batch action bar", () => {
  const css = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");

  const openTaskListBlock = css.match(/\.board-workspace\.case-detail-open \.task-list\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";
  const openShellBlock = css.match(/\.board-workspace\.case-detail-open \.task-batch-status-shell\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";
  const openBarBlock = css.match(/\.board-workspace\.case-detail-open \.task-batch-status-bar\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";
  const hiddenTextBlock = css.match(/\.board-workspace\.case-detail-open \.task-batch-file,[\s\S]*?\.board-workspace\.case-detail-open \.task-batch-overview\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";
  const compactActionsBlock = css.match(/\.board-workspace\.case-detail-open \.task-batch-actions\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";
  const compactActionButtonBlock = css.match(/\.board-workspace\.case-detail-open \.task-batch-action\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";
  const primaryActionBlock = css.match(/\.task-batch-action\.primary\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";
  const selectToggleActiveBlock = css.match(/\.task-batch-action\.select-toggle\.active\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";
  const compactAnimationBlock = css.match(/@keyframes task-batch-status-compact-in\s*\{[\s\S]*?from\s*\{(?<from>[^}]*)\}[\s\S]*?to\s*\{(?<to>[^}]*)\}/)?.groups || {};

  assert.match(openTaskListBlock, /align-items:\s*center;/);
  assert.match(openTaskListBlock, /padding-top:\s*82px;/);
  assert.match(openShellBlock, /transform:\s*translateX\(0\);/);
  assert.match(openShellBlock, /opacity:\s*1;/);
  assert.doesNotMatch(openShellBlock, /translateY\(-86px\)|opacity:\s*0;/);
  assert.match(openBarBlock, /width:\s*max-content;/);
  assert.match(openBarBlock, /grid-template-columns:\s*auto;/);
  assert.match(openBarBlock, /animation:\s*task-batch-status-compact-in/);
  assert.match(hiddenTextBlock, /display:\s*none;/);
  assert.match(compactActionsBlock, /justify-content:\s*center;/);
  assert.match(compactActionsBlock, /gap:\s*4px;/);
  assert.match(compactActionButtonBlock, /width:\s*32px;/);
  assert.match(compactActionButtonBlock, /height:\s*32px;/);
  assert.match(primaryActionBlock, /box-shadow:\s*none;/);
  assert.match(selectToggleActiveBlock, /box-shadow:\s*none;/);
  assert.match(compactAnimationBlock.from || "", /translateX\(72px\)/);
  assert.match(compactAnimationBlock.to || "", /translateX\(0\)/);
});
