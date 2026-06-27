import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("image generation composer uses method cards and bottom prompt layout", () => {
  const appSource = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
  const source = readFileSync(new URL("../src/ImageGenStudio.tsx", import.meta.url), "utf8");
  const css = readFileSync(new URL("../src/imagegen.css", import.meta.url), "utf8");
  const composerBlock = source.match(/<div className="gen-form gen-settings-form">[\s\S]*?<footer className="gen-settings-footer">/)?.[0] || "";
  const formCss = css.match(/\.gen-settings-form\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";
  const promptBottomCss = css.match(/\.gen-prompt-bottom\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";
  const transparentIconCss = css.match(/\.gen-background-icon\.transparent\s+\.gen-background-object\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";
  const opaqueIconCss = css.match(/\.gen-background-icon\.opaque\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";

  assert.match(appSource, /methodCards=\{imageGenMethodCards\(imageGenConnection, imageGenApiPresetCache, imageGenAgentCache\)\}/);
  assert.match(appSource, /onSelectMethod=\{selectImageGenMethodCard\}/);
  assert.match(source, /methodCards,\s*onSelectMethod/);
  assert.match(source, /<div className="gen-method-card-grid" role="radiogroup" aria-label="生成方式">/);
  assert.ok(
    composerBlock.indexOf("gen-method-card-grid") >= 0
      && composerBlock.indexOf("gen-method-card-grid") < composerBlock.indexOf("gen-prompt-block gen-prompt-wide gen-prompt-bottom"),
    "generation method cards should render before the bottom prompt"
  );
  assert.match(source, /<ChoiceCards[\s\S]*options=\{RESOLUTIONS\.map/);
  assert.match(source, /<ChoiceCards[\s\S]*options=\{QUALITIES\.map/);
  assert.match(source, /<BackgroundChoiceCards/);
  assert.match(formCss, /grid-template-columns:\s*minmax\(280px,\s*0\.9fr\)\s+minmax\(360px,\s*1\.1fr\);/);
  assert.match(promptBottomCss, /grid-column:\s*1 \/ -1;/);
  assert.match(css, /\.gen-choice-card-grid\s*\{/);
  assert.match(css, /\.gen-background-icon\.transparent\s*\{/);
  assert.match(transparentIconCss, /box-shadow:/);
  assert.match(opaqueIconCss, /background:\s*#ffffff;/);
});
