import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import test from "node:test";
import ts from "../node_modules/typescript/lib/typescript.js";

test("Agent log presentation turns tool-agent trace events into readable timeline items", async () => {
  const {
    agentLogStats,
    buildAgentLogDisplayItem
  } = await loadPresentationModule();
  const events = [
    {
      source: "trace",
      item: {
        source: "drawai_tool_agent_trace.jsonl",
        type: "tool_agent_request",
        summary: "{}",
        event: {
          type: "tool_agent_request",
          model_name: "qwen3.7-plus",
          wire_api: "chat_completions",
          images: [{ image_path: "input.png" }],
          timeout_seconds: 600
        }
      }
    },
    {
      source: "trace",
      item: {
        type: "tool_agent_turn",
        event: {
          type: "tool_agent_turn",
          iteration: 1,
          tool_calls: [{ name: "copy_file" }, { name: "open_image" }]
        }
      }
    },
    {
      source: "trace",
      item: {
        type: "tool_agent_tool_result",
        event: {
          type: "tool_agent_tool_result",
          tool: "copy_file",
          duration_ms: 151,
          result: {
            ok: true,
            source: "nodes/page_spec_fuse/runs/001/output/page_spec.json",
            path: "nodes/page_spec_refine/runs/001/output/page_spec.json",
            bytes: 243172,
            sha256: "bc4440e0f6aa63f6620566fa39146ad34a24f3a4b737a5736791f15081dcbc8c",
            auto_validation: { ok: true }
          }
        }
      }
    },
    {
      source: "trace",
      item: {
        type: "tool_agent_response",
        event: {
          type: "tool_agent_response",
          duration_ms: 4825,
          final_excerpt: "validated copied drawai.page_spec.v1 output",
          iterations: 1,
          tool_calls: 2
        }
      }
    }
  ];

  const displayItems = events.map((entry, index) => buildAgentLogDisplayItem(entry, index));

  assert.equal(displayItems[0].title, "启动内置 Agent");
  assert.match(displayItems[0].detail, /qwen3\.7-plus/);
  assert.equal(displayItems[1].title, "Agent 请求工具");
  assert.equal(displayItems[1].detail, "copy_file -> open_image");
  assert.equal(displayItems[2].title, "工具结果：copy_file");
  assert.match(displayItems[2].detail, /page_spec_fuse/);
  assert.match(displayItems[2].detail, /validation ok/);
  assert.equal(displayItems[3].title, "最终响应");
  assert.equal(displayItems[3].detail, "validated copied drawai.page_spec.v1 output");
  assert.deepEqual(agentLogStats(displayItems), {
    total: 4,
    toolCalls: 2,
    errors: 0,
    finalResponses: 1
  });
});

test("Agent log presentation filters low-value runtime deltas", async () => {
  const { agentLogEntryVisible } = await loadPresentationModule();

  assert.equal(
    agentLogEntryVisible({
      source: "runtime",
      item: {
        event_type: "response.output_text.delta",
        message: "partial"
      }
    }),
    false
  );
  assert.equal(
    agentLogEntryVisible({
      source: "trace",
      item: {
        event: {
          type: "tool_agent_response",
          final_excerpt: "done"
        }
      }
    }),
    true
  );
});

let presentationModulePromise;

function loadPresentationModule() {
  presentationModulePromise ||= loadTsModule("../src/agentLogPresentation.ts");
  return presentationModulePromise;
}

async function loadTsModule(relativePath) {
  const source = readFileSync(new URL(relativePath, import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2020
    }
  });
  const dir = mkdtempSync(join(tmpdir(), "drawai-agent-log-presentation-"));
  const modulePath = join(dir, `${relativePath.split("/").at(-1).replace(/\.ts$/, "")}.mjs`);
  writeFileSync(modulePath, outputText);
  return import(pathToFileURL(modulePath).href);
}
