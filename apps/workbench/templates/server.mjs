import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema, ListResourcesRequestSchema, ReadResourceRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { searchTemplates, findTemplate } from "./catalog.mjs";
import { prepareReference } from "./references.mjs";
import { coreTool } from "./workflow.mjs";

const filters = {
  query: { type: "string" }, category: { type: "string" }, with_images: { type: "boolean" },
  template_ids: { type: "array", items: { type: "string" }, uniqueItems: true },
  offset: { type: "integer", minimum: 0 }, limit: { type: "integer", minimum: 1, maximum: 120 },
};
export const TOOLS = [
  {
    name: "drawai_image",
    description: "Generate or edit images with a shared user Images API connection. This never changes the current Session implementation Agent.",
    inputSchema: { type: "object", properties: { action: { enum: ["generate", "edit"] }, connection: { type: "string" }, prompt: { type: "string" }, source_image: { type: "string" }, output_directory: { type: "string" }, output_stem: { type: "string" }, options: { type: "object" } }, required: ["action", "prompt", "output_directory"], additionalProperties: false },
    annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
  },
  {
    name: "drawai_templates",
    description: "Read drawai-readme first. In drawai-design, search/get real visual references or retrieve keyword-ranked candidates. Use drawai_show_templates to present a shortlist to the user.",
    inputSchema: { type: "object", properties: { action: { enum: ["search", "get", "recommend"] }, template_id: { type: "string" }, ...filters }, required: ["action"], additionalProperties: false },
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
  },
  {
    name: "drawai_show_templates",
    description: "Show the DrawAI template chooser inline. Pass template_ids or query/category filters. Selected structure/style references go to drawai-design; finished visual pages are then converted with drawai-image2ppt.",
    inputSchema: { type: "object", properties: filters, additionalProperties: false },
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
  },
  {
    name: "drawai_prepare_template",
    description: "Prepare selected template references for drawai-design: verified original images and template-reference.json. Existing different files are not overwritten. Recipe-only references contain no image files.",
    inputSchema: { type: "object", properties: { template_id: { type: "string" }, output_directory: { type: "string" } }, required: ["template_id", "output_directory"], additionalProperties: false },
    annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
    _meta: { ui: { visibility: ["model"] } },
  },
  {
    name: "drawai_plan",
    description: "Resolve the DrawAI design method, current-session implementation default and missing intake questions. Supply actual current-session model/tool facts and preferences extracted from the user. The server does not detect hidden caller models. Explicit modes and no-question requests take priority.",
    inputSchema: { type: "object", properties: { request: { type: "object", description: "environment, preferences and inputs; see drawai-readme intake contract" } }, required: ["request"], additionalProperties: false },
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
  },
  {
    name: "drawai_flow",
    description: "Use the existing Workbench for DrawAI-Flow. status without batch_id checks connection. submit uploads verified visual-deck pages as a queued batch; start executes that batch; status reports actual progress; export downloads the completed PPTX to a new output_path for validation. Only act on this task's batch IDs. Flow uses Workbench's own configured workers/models.",
    inputSchema: { type: "object", properties: { action: { enum: ["submit", "start", "status", "export"] }, visual_manifest: { type: "string" }, name: { type: "string" }, batch_id: { type: "string" }, output_path: { type: "string" }, agent_settings: { type: "object" } }, required: ["action"], additionalProperties: false },
    annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
    _meta: { ui: { visibility: ["model"] } },
  },
];

export async function dispatch(name, args = {}) {
  return coreTool(name, args);
}

export function createMcpServer() {
  let resource;
  const getResource = async () => {
    if (!resource) {
      const text = await readFile(new URL("../dist-plugin/templates-inline.html", import.meta.url), "utf8");
      const hash = createHash("sha256").update(text).digest("hex").slice(0, 16);
      resource = { uri: `ui://drawai/templates-${hash}.html`, text };
    }
    return resource;
  };
  const server = new Server({ name: "drawai", version: "0.2.0" }, { capabilities: { tools: {}, resources: {} } });
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    const { uri } = await getResource();
    return { tools: TOOLS.map((tool) => tool.name === "drawai_show_templates" ? { ...tool, _meta: { ui: { resourceUri: uri } } } : tool) };
  });
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    try {
      const data = await dispatch(request.params.name, request.params.arguments);
      return {
        content: [{ type: "text", text: JSON.stringify(data) }], structuredContent: data,
        ...(request.params.name === "drawai_show_templates" ? { _meta: { ui: { resourceUri: (await getResource()).uri } } } : {}),
      };
    } catch (error) {
      return { isError: true, content: [{ type: "text", text: error.message }] };
    }
  });
  server.setRequestHandler(ListResourcesRequestSchema, async () => ({ resources: [{ uri: (await getResource()).uri, name: "DrawAI Templates", mimeType: "text/html;profile=mcp-app" }] }));
  server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
    const { uri, text } = await getResource();
    if (request.params.uri !== uri) throw new Error("Unknown template UI resource");
    return { contents: [{ uri, text, mimeType: "text/html;profile=mcp-app", _meta: {
      "openai/ui": { availableDisplayModes: ["inline", "fullscreen"] },
      ui: { prefersBorder: true, csp: { resourceDomains: ["https://assets.visualize.renaissancemind.ai", "https://visualize.renaissancemind.ai"], connectDomains: [] } },
    } }] };
  });
  return server;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await createMcpServer().connect(new StdioServerTransport());
}
