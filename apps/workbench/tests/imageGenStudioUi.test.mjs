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
  const methodGridCss = css.match(/\.gen-method-card-grid\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";
  const methodFieldCss = css.match(/\.gen-method-field\s*\{(?<body>[^}]*)\}/)?.groups?.body || "";
  const requestBlock = source.match(/const request = useMemo<ImageGenerationRequest>\(\(\) => \{[\s\S]*?return body;\n  \}, \[/)?.[0] || "";
  const codexRequestBlock = requestBlock.match(/if \(provider === "codex"\) \{[\s\S]*?\n    \}/)?.[0] || "";

  assert.match(appSource, /methodCards=\{imageGenMethodCards\(imageGenConnection, imageGenApiPresetCache, imageGenAgentCache\)\}/);
  assert.match(appSource, /onSelectMethod=\{selectImageGenMethodCard\}/);
  assert.match(source, /methodCards,\s*onSelectMethod/);
  assert.match(source, /API_PRESET_TEMPLATES/);
  assert.match(source, /agentProviderIconForId\("codex_sdk"\)/);
  assert.match(source, /<Field className="gen-method-field" label="生成方式"/);
  assert.match(source, /<div className="gen-method-card-grid" role="radiogroup" aria-label="生成方式">/);
  assert.match(source, /methodIcon=\{imageGenMethodIcon\(method\)\}/);
  assert.match(source, /methodIcon \? <img src=\{methodIcon\.icon_url\} alt="" \/> : <GenerationMethodGlyph/);
  assert.match(source, /className="gen-method-card gen-method-manage-card"/);
  assert.ok(
    composerBlock.indexOf("gen-method-card-grid") >= 0
      && composerBlock.indexOf("gen-method-card-grid") < composerBlock.indexOf("gen-prompt-block gen-prompt-wide gen-prompt-bottom"),
    "generation method cards should render before the bottom prompt"
  );
  assert.match(methodGridCss, /display:\s*flex;/);
  assert.match(methodGridCss, /flex-wrap:\s*nowrap;/);
  assert.match(methodGridCss, /overflow-x:\s*auto;/);
  assert.match(methodFieldCss, /grid-column:\s*1 \/ -1;/);
  assert.match(source, /<ChoiceCards[\s\S]*options=\{RESOLUTIONS\.map/);
  assert.match(source, /<ChoiceCards[\s\S]*options=\{QUALITIES\.map/);
  assert.match(source, /<BackgroundChoiceCards/);
  assert.match(composerBlock, /<Field label="模板选择"/);
  assert.doesNotMatch(source, /if \(provider !== "codex"\) return;\s*listSlideTemplate/);
  assert.doesNotMatch(codexRequestBlock, /template_id|template_card_id/);
  assert.match(requestBlock, /if \(templateId !== "auto"\) \{[\s\S]*?body\.template_id = templateId;/);
  assert.match(requestBlock, /if \(templateCardId\) \{[\s\S]*?body\.template_card_id = templateCardId;/);
  assert.match(formCss, /grid-template-columns:\s*minmax\(280px,\s*0\.9fr\)\s+minmax\(360px,\s*1\.1fr\);/);
  assert.match(promptBottomCss, /grid-column:\s*1 \/ -1;/);
  assert.match(css, /\.gen-choice-card-grid\s*\{/);
  assert.match(css, /\.gen-background-icon\.transparent\s*\{/);
  assert.match(transparentIconCss, /box-shadow:/);
  assert.match(opaqueIconCss, /background:\s*#ffffff;/);
});
