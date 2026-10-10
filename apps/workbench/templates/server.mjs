import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema, ListResourcesRequestSchema, ReadResourceRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { searchTemplates, findTemplate } from "./catalog.mjs";
import { prepareReference } from "./references.mjs";

const filters = {
  query: { type: "string" }, category: { type: "string" }, with_images: { type: "boolean" },
  template_ids: { type: "array", items: { type: "string" }, uniqueItems: true },
  offset: { type: "integer", minimum: 0 }, limit: { type: "integer", minimum: 1, maximum: 120 },
};
export const TOOLS = [
  {
    name: "drawai_templates",
    description: "Read the DrawAI entry skill, then use drawai-templates to search/get real visual references or retrieve keyword-ranked recommendation candidates. Use drawai_show_templates to present a shortlist to the user.",
    inputSchema: { type: "object", properties: { action: { enum: ["search", "get", "recommend"] }, template_id: { type: "string" }, ...filters }, required: ["action"], additionalProperties: false },
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
  },
  {
    name: "drawai_show_templates",
    description: "Show the DrawAI template chooser inline in the current conversation. Pass recommended template_ids or query/category filters. The user can inspect references, select structure/style, and send the selection to this conversation to continue with drawai-ppt.",
    inputSchema: { type: "object", properties: filters, additionalProperties: false },
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
  },
  {
    name: "drawai_prepare_template",
    description: "Save an explicitly selected template's verified original reference images and template-reference.json into the current task output directory for drawai-ppt. Existing different files are never overwritten. Recipe-only references contain no image files.",
    inputSchema: { type: "object", properties: { template_id: { type: "string" }, output_directory: { type: "string" } }, required: ["template_id", "output_directory"], additionalProperties: false },
    annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
    _meta: { ui: { visibility: ["model"] } },
  },
];

export async function dispatch(name, args = {}) {
  if (name === "drawai_templates") {
    if (args.action === "get") return { template: await findTemplate(args.template_id) };
    if (!["search", "recommend"].includes(args.action)) throw new Error("Unknown template action");
    return searchTemplates(args);
  }
  if (name === "drawai_show_templates") {
    const view = { with_images: args.with_images ?? !args.template_ids, ...args, limit: args.limit ?? 6, offset: args.offset ?? 0 };
    return { view, result: await searchTemplates(view) };
  }
  if (name === "drawai_prepare_template") return prepareReference(args);
  throw new Error(`Unknown DrawAI tool: ${name}`);
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
  const server = new Server({ name: "drawai-templates", version: "3.0.0" }, { capabilities: { tools: {}, resources: {} } });
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
