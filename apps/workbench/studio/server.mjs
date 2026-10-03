import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { createServer } from "node:http";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { StudioStore } from "./store.mjs";
import { searchTemplates, findTemplate } from "./catalog.mjs";

async function loadWorkbenchResource() {
  const text = await readFile(
    new URL("../dist-plugin/workbench.html", import.meta.url),
    "utf8",
  );
  const revision = createHash("sha256").update(text).digest("hex").slice(0, 16);
  return { uri: `ui://drawai/workbench-${revision}.html`, text };
}
const parameters = {
  action: { type: "string" },
  project_id: { type: "string" },
  task_id: { type: "string" },
  slide_id: { type: "string" },
  slide_ids: { type: "array", items: { type: "string" } },
  title: { type: "string" },
  content: { type: "string" },
  brief: { type: "string" },
  notes: { type: "string" },
  language: { type: "string" },
  aspect_ratio: { type: "string" },
  style_notes: { type: "string" },
  source_directory: { type: "string" },
  expected_revision: { type: "number" },
  reference_id: { type: "string" },
  template_id: { type: "string" },
  role: { type: "string" },
  filename: { type: "string" },
  data_base64: { type: "string" },
  kind: { type: "string" },
  instruction: { type: "string" },
  status: { type: "string" },
  message: { type: "string" },
  asset_id: { type: "string" },
  source_path: { type: "string" },
  description: { type: "string" },
};
const tool = (name, description, actions) => ({
  name,
  description,
  inputSchema: {
    type: "object",
    properties: { ...parameters, action: { type: "string", enum: actions } },
    required: ["action"],
    additionalProperties: false,
  },
});
export const TOOLS = [
  {
    name: "drawai_open_workbench",
    description:
      "Open DrawAI beside this conversation to choose visual references, manage slide pages, send generation/conversion tasks to this same conversation, and inspect real outputs. The workbench does not start another agent.",
    inputSchema: {
      type: "object",
      properties: { project_id: { type: "string" } },
    },
    _meta: {
      "openai/ui": { entrypoints: [{ type: "thread" }] },
    },
  },
  tool(
    "drawai_project",
    "Manage persistent PPT projects and ordered slide content. Actions: list/create/get/update/add_slide/update_slide/duplicate_slide/delete_slide/reorder/delete. Save exact source-grounded content before generation.",
    [
      "list",
      "create",
      "get",
      "update",
      "add_slide",
      "update_slide",
      "duplicate_slide",
      "delete_slide",
      "reorder",
      "delete",
    ],
  ),
  {
    name: "drawai_templates",
    description:
      "Search the real DrawAI visual reference catalog; use get with template_id for its recipe, provenance and image URLs.",
    inputSchema: {
      type: "object",
      properties: {
        action: { enum: ["search", "get"] },
        template_id: { type: "string" },
        query: { type: "string" },
        category: { type: "string" },
        with_images: { type: "boolean" },
        offset: { type: "number" },
        limit: { type: "number" },
      },
    },
  },
  tool(
    "drawai_reference",
    "Upload real files (base64), select a catalog template, update its role/scope, or remove a reference. Roles: content, structure, style, ppt_template. References can be combined; slide_ids empty means entire deck.",
    ["upload", "template", "update", "remove"],
  ),
  tool(
    "drawai_task",
    "Create/get/update/cancel tasks. Kinds: generate, edit_image, convert, prepare_reference, export_deck. Creation saves a request file and returns a prompt; it does not run a model. Read that request, use the current conversation image tool or drawai-ppt skill, mark running, register actual artifacts, then mark completed. Completion validates the expected artifacts. Failed work must be marked failed with its real error.",
    ["create", "get", "update", "cancel"],
  ),
  tool(
    "drawai_artifact",
    "Register a real local output file with task_id, kind and slide_id. Kinds: image/svg/pptx/preview/reference_preview/document/report. Native editable objects are required for PPTX conversion results. read returns asset base64; select chooses a prior image version; import_image uploads an existing image as a slide; archive returns a complete project ZIP. save_download saves the registered asset (asset_id) or project ZIP (omit asset_id) to Downloads/DrawAI on this host without overwriting existing files, and returns the actual saved path, size and SHA-256.",
    ["register", "read", "select", "import_image", "archive", "save_download"],
  ),
];

export async function dispatch(store, name, args = {}) {
  if (name === "drawai_open_workbench")
    return {
      ...(await store.list()),
      ...(args.project_id
        ? { project: await store.read(args.project_id) }
        : {}),
      workspace: store.root,
      view: { project_id: args.project_id || null },
    };
  if (name === "drawai_project") return store.projectAction(args);
  if (name === "drawai_templates")
    return args.action === "get"
      ? { template: await findTemplate(args.template_id) }
      : searchTemplates(args);
  if (name === "drawai_reference") return store.referenceAction(args);
  if (name === "drawai_task") return store.taskAction(args);
  if (name === "drawai_artifact") return store.artifactAction(args);
  throw new Error(`Unknown DrawAI tool: ${name}`);
}

export function createMcpServer(store = new StudioStore()) {
  // A resource URI is a host cache key. Pin its bytes for this connection;
  // rebuilding and reconnecting produces a new URI instead of a stale iframe.
  let workbench;
  const getWorkbench = () => (workbench ??= loadWorkbenchResource());
  const server = new Server(
    { name: "drawai-studio", version: "2.0.4" },
    { capabilities: { tools: {}, resources: {} } },
  );
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    const { uri } = await getWorkbench();
    return {
      tools: TOOLS.map((entry) =>
        entry.name === "drawai_open_workbench"
          ? { ...entry, _meta: { ...entry._meta, ui: { resourceUri: uri } } }
          : entry,
      ),
    };
  });
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    try {
      const data = await dispatch(
        store,
        request.params.name,
        request.params.arguments || {},
      );
      return {
        content: [
          {
            type: "text",
            text: data.data_base64
              ? JSON.stringify({ asset: data.asset, filename: data.filename })
              : JSON.stringify(data),
          },
        ],
        structuredContent: data,
        ...(request.params.name === "drawai_open_workbench"
          ? { _meta: { ui: { resourceUri: (await getWorkbench()).uri } } }
          : {}),
      };
    } catch (error) {
      return {
        isError: true,
        content: [{ type: "text", text: error.message }],
      };
    }
  });
  server.setRequestHandler(ListResourcesRequestSchema, async () => ({
    resources: [
      {
        uri: (await getWorkbench()).uri,
        name: "DrawAI Workbench",
        mimeType: "text/html;profile=mcp-app",
      },
    ],
  }));
  server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
    const { uri, text } = await getWorkbench();
    if (request.params.uri !== uri) throw new Error("Unknown resource");
    return {
      contents: [
        {
          uri,
          mimeType: "text/html;profile=mcp-app",
          text,
          _meta: {
            ui: {
              prefersBorder: false,
              csp: {
                resourceDomains: [
                  "https://assets.visualize.renaissancemind.ai",
                  "https://visualize.renaissancemind.ai",
                ],
                connectDomains: [],
              },
            },
          },
        },
      ],
    };
  });
  return server;
}

export async function startHttp(store, port) {
  const server = createServer(async (req, res) => {
    const origin = req.headers.origin;
    if (origin && !/^http:\/\/(?:127\.0\.0\.1|localhost):\d+$/.test(origin)) {
      res.writeHead(403).end("Origin not allowed");
      return;
    }
    if (origin) res.setHeader("Access-Control-Allow-Origin", origin);
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");
    if (req.method === "OPTIONS") {
      res.writeHead(204).end();
      return;
    }
    try {
      if (req.method === "GET" && req.url === "/api/studio/health") {
        res.setHeader("Content-Type", "application/json");
        res.end(
          JSON.stringify({
            status: "ok",
            mode: "plugin",
            workspace: store.root,
          }),
        );
        return;
      }
      const fileMatch = req.url?.match(
        /^\/api\/studio\/files\/(project_[a-f0-9]{16})\/(asset_[a-f0-9]{16})$/,
      );
      const archiveMatch = req.url?.match(
        /^\/api\/studio\/archive\/(project_[a-f0-9]{16})$/,
      );
      if (req.method === "GET" && (fileMatch || archiveMatch)) {
        const data = fileMatch
          ? await store.readAsset(fileMatch[1], fileMatch[2])
          : await store.artifactAction({
              action: "archive",
              project_id: archiveMatch[1],
            });
        const filename = data.asset?.filename || data.filename;
        res.writeHead(200, {
          "Content-Type": data.asset?.mime_type || data.mime_type,
          "Content-Disposition": `attachment; filename*=UTF-8''${encodeURIComponent(filename)}`,
          "Cache-Control": "no-store",
        });
        res.end(Buffer.from(data.data_base64, "base64"));
        return;
      }
      if (req.method !== "POST" || req.url !== "/api/studio/call") {
        res.writeHead(404).end("Not found");
        return;
      }
      let size = 0;
      const chunks = [];
      for await (const chunk of req) {
        size += chunk.length;
        if (size > 66 * 1024 * 1024) throw new Error("Request exceeds 66 MB");
        chunks.push(chunk);
      }
      const { name, arguments: args = {} } = JSON.parse(
        Buffer.concat(chunks).toString("utf8"),
      );
      // The browser development endpoint cannot read arbitrary filesystem paths.
      if (
        name === "drawai_artifact" &&
        ["register", "save_download"].includes(args.action)
      )
        throw new Error(
          "Local file operations require the agent MCP tool or CLI",
        );
      const data = await dispatch(store, name, args);
      res.setHeader("Content-Type", "application/json");
      res.end(JSON.stringify(data));
    } catch (error) {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: error.message }));
    }
  });
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", resolve);
  });
  return server;
}

if (
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  const store = new StudioStore();
  await store.ready();
  const portArg = process.argv.find((arg) => arg.startsWith("--http="));
  if (portArg) {
    await startHttp(store, Number(portArg.split("=")[1]));
    console.error(
      `DrawAI project service: http://127.0.0.1:${portArg.split("=")[1]}`,
    );
  } else await createMcpServer(store).connect(new StdioServerTransport());
}
