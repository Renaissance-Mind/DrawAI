import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("upload LLM mode selects a compatible harness and submits as agent execution", () => {
  const source = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
  const llmModeBlock = source.match(/selectedExecutionMode === "llm"[\s\S]*?selectedExecutionMode === "agent"/u)?.[0] || source;

  assert.match(source, /const llmPresets = apiPresets\.filter\(isLlmApiPreset\);/);
  assert.match(source, /compatibleAgentsForEndpoint\(agentChoices, selectedLlmEndpoint\)/);
  assert.match(source, /<span>Harness<\/span>/);
  assert.match(source, /LLM 模式需要选择 LLM 预设、Endpoint 和兼容 Harness/);
  assert.match(source, /form\.set\("execution_mode", "agent"\);/);
  assert.doesNotMatch(source, /directLlmEndpoints/);
  assert.doesNotMatch(llmModeBlock, /单次调用/);
});
