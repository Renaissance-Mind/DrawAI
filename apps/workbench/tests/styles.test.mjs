import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("image result overlays stay inside their canvas stacking context", () => {
  const css = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");
  const block = css.match(/\.image-overlay-wrap\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";

  assert.match(block, /isolation:\s*isolate;/);
});

test("left task rail renders task time above the task title without moving status tags", () => {
  const source = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
  const css = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");
  const batchMainBlock = source.match(/<div className="batch-row-main">[\s\S]*?<span className=\{`status-pill status-\$\{batch\.status\}`\}>/)?.[0] || "";
  const taskMainBlock = source.match(/<div className="task-main">[\s\S]*?<strong>\{item\.name\}<\/strong>/)?.[0] || "";
  const batchRowMainCss = css.match(/\.batch-row-main\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";
  const batchTitleCss = css.match(/\.batch-row-title\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";
  const batchTimeCss = css.match(/\.batch-created-at\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";

  assert.match(batchMainBlock, /<div className="batch-row-title">[\s\S]*?<time className="batch-created-at" dateTime=\{batch\.created_at\}>\{submittedTimeText\(batch\.created_at\)\}<\/time>[\s\S]*?<strong>\{batch\.name\}<\/strong>[\s\S]*?<\/div>\s*<span className=\{`status-pill status-\$\{batch\.status\}`\}>/);
  assert.doesNotMatch(taskMainBlock, /task-created-at|batch-created-at|submittedTimeText|item\.created_at/);
  assert.match(batchRowMainCss, /grid-template-columns:\s*minmax\(0,\s*1fr\) auto;/);
  assert.match(batchTitleCss, /align-content:\s*center;/);
  assert.match(batchTitleCss, /gap:\s*2px;/);
  assert.match(batchTimeCss, /font-size:\s*10px;/);
  assert.match(batchTimeCss, /line-height:\s*1\.15;/);
});

test("case cards keep status beside the truncated title and show only the current stage below", () => {
  const source = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
  const css = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");
  const taskTopBlock = source.match(/<div className="task-row-top">[\s\S]*?<\/div>/)?.[0] || "";
  const taskBottomBlock = source.match(/<div className="task-bottom">[\s\S]*?<div\s+className="task-card-actions"/)?.[0] || "";
  const titleRowBlock = css.match(/\.task-title-row\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";
  const titleBlock = css.match(/\.task-title-row strong\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";
  const statusHoverBlock = css.match(/\.task-batch-action\.primary:hover(?<selector>[^{]*)\{(?<body>[^}]*)\}/);

  assert.doesNotMatch(taskTopBlock, /status-pill|item\.stage|item\.phase/);
  assert.match(taskBottomBlock, /<div className="task-title-row">[\s\S]*?<strong title=\{item\.name\}>\{item\.name\}<\/strong>[\s\S]*?<span className=\{`status-pill status-\$\{item\.status\}`\}>\{humanize\(item\.status\)\}<\/span>/);
  assert.match(taskBottomBlock, /<div className="task-current-stage">[\s\S]*?<span>当前阶段<\/span>[\s\S]*?<em title=\{caseCurrentStageLabel\(item\)\}>\{caseCurrentStageLabel\(item\)\}<\/em>/);
  assert.doesNotMatch(taskBottomBlock, /editorReady\s*\?\s*"素材已准备"\s*:\s*"等待中"|humanize\(item\.phase\)\s*}\s*\/\s*\{humanize\(item\.stage\)/);
  assert.match(titleRowBlock, /grid-template-columns:\s*minmax\(0,\s*1fr\)\s+auto;/);
  assert.match(titleBlock, /overflow:\s*hidden;/);
  assert.match(titleBlock, /text-overflow:\s*ellipsis;/);
  assert.match(titleBlock, /white-space:\s*nowrap;/);
  assert.equal(statusHoverBlock, null);
});

test("task batch status bar is large enough for controls", () => {
  const css = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");
  const statusBarBlock = css.match(/\.task-batch-status-bar\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";
  const actionBlock = css.match(/\.task-batch-action\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";

  assert.match(statusBarBlock, /width:\s*min\(100%,\s*920px\);/);
  assert.match(statusBarBlock, /min-height:\s*44px;/);
  assert.match(actionBlock, /width:\s*34px;/);
  assert.match(actionBlock, /height:\s*34px;/);
});
