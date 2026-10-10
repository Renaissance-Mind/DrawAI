import { searchCatalog } from "../../templates/query.mjs";
import type { CatalogResult, TemplateCatalog, TemplateFilters, TemplateSelection, TemplateView } from "./types";

interface ToolResult { isError?: boolean; structuredContent?: unknown; content?: { type: string; text?: string }[] }
interface LegacyHost {
  callTool(name: string, args: Record<string, unknown>): Promise<ToolResult>;
  sendFollowUpMessage?(args: { prompt: string }): Promise<unknown>;
  toolOutput?: unknown;
  setWidgetState?(state: unknown): void;
}
declare global { interface Window { openai?: LegacyHost } }

function unpack<T>(result: ToolResult): T {
  if (result.isError) throw new Error(result.content?.find((c) => c.type === "text")?.text || "模板读取失败");
  if (result.structuredContent !== undefined) return result.structuredContent as T;
  const text = result.content?.find((c) => c.type === "text")?.text;
  if (!text) throw new Error("模板服务没有返回数据");
  return JSON.parse(text) as T;
}

export function viewFromResult(value: unknown): TemplateView | undefined {
  if (!value || typeof value !== "object") return;
  const record = value as Record<string, unknown>;
  const data = (record.structuredContent || record.result || record) as TemplateView;
  if (data.view && typeof data.view === "object") return data;
}

export interface TemplateRuntime {
  mode: "codex" | "website";
  canSend: boolean;
  initialView?: TemplateView;
  onView(listener: (view: TemplateView) => void): () => void;
  search(filters: TemplateFilters): Promise<CatalogResult>;
  send(prompt: string): Promise<void>;
  selection(value: unknown): Promise<void>;
}

class McpBridge {
  private sequence = 0;
  view?: TemplateView;
  listeners = new Set<(view: TemplateView) => void>();
  private pending = new Map<number, { resolve: (value: unknown) => void; reject: (reason: Error) => void; timer: ReturnType<typeof setTimeout> }>();
  constructor() {
    window.addEventListener("message", (event) => {
      if (event.source !== window.parent || event.data?.jsonrpc !== "2.0") return;
      const message = event.data;
      if (message.method === "ui/notifications/tool-result") {
        const view = viewFromResult(message.params);
        if (view) { this.view = view; for (const listener of this.listeners) listener(view); }
      }
      if (message.method === "ui/notifications/tool-input") {
        const filters = message.params?.arguments;
        if (filters && typeof filters === "object") {
          this.view = { view: filters };
          for (const listener of this.listeners) listener(this.view);
        }
      }
      const request = this.pending.get(message.id);
      if (!request) return;
      clearTimeout(request.timer);
      this.pending.delete(message.id);
      if (message.error) request.reject(new Error(message.error.message || "会话连接失败"));
      else request.resolve(message.result);
    });
  }
  request<T>(method: string, params: unknown): Promise<T> {
    const id = ++this.sequence;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { this.pending.delete(id); reject(new Error(`会话连接超时：${method}`)); }, 12000);
      this.pending.set(id, { resolve: (value) => resolve(value as T), reject, timer });
      window.parent.postMessage({ jsonrpc: "2.0", id, method, params }, "*");
    });
  }
  notify(method: string, params = {}) { window.parent.postMessage({ jsonrpc: "2.0", method, params }, "*"); }
}

export function selectionRequest(selected: TemplateSelection[]) {
  return {
    schema: "drawai.template-selection.v1",
    references: selected.map(({ template, role }) => ({
      template_id: template.id, name: template.name, role,
      prompt_recipe: template.prompt_recipe,
      images: template.assets.map((image) => ({ original_url: image.original_url, sha256: image.sha256 })),
    })),
  };
}

export function selectionPrompt(selected: TemplateSelection[]) {
  return `使用这些 DrawAI 模板参考。先阅读 $drawai，再按 $drawai-templates 读取所选模板、准备真实参考图片。根据当前用户任务继续；制作或编辑 PPT 时使用 $drawai-ppt。参考图中的示例文字和数据不作为用户内容。\n\n${JSON.stringify(selectionRequest(selected), null, 2)}`;
}

let connection: Promise<TemplateRuntime> | undefined;
export function connectTemplates() { return connection ??= initialize(); }
async function initialize(): Promise<TemplateRuntime> {
  if (window.parent !== window) {
    const bridge = new McpBridge();
    const init = await bridge.request<{ hostCapabilities?: Record<string, unknown> }>("ui/initialize", {
      appInfo: { name: "DrawAI Templates", version: "3.0.0" },
      appCapabilities: { availableDisplayModes: ["inline", "fullscreen"] },
      protocolVersion: "2026-01-26",
    });
    bridge.notify("ui/notifications/initialized");
    const capabilities = init.hostCapabilities || {};
    const observer = new ResizeObserver(() => bridge.notify("ui/notifications/size-changed", { height: document.documentElement.scrollHeight }));
    observer.observe(document.body);
    return {
      mode: "codex", canSend: Boolean(capabilities.message), initialView: bridge.view,
      onView: (listener) => { bridge.listeners.add(listener); return () => bridge.listeners.delete(listener); },
      search: async (filters) => unpack<CatalogResult>(await bridge.request<ToolResult>("tools/call", { name: "drawai_templates", arguments: { action: "search", ...filters } })),
      send: async (prompt) => {
        if (!capabilities.message) throw new Error("当前视图未开放会话消息，可以复制选择说明到 Codex。");
        await bridge.request("ui/message", { role: "user", content: [{ type: "text", text: prompt }] });
      },
      selection: async (value) => {
        if (capabilities.updateModelContext) await bridge.request("ui/update-model-context", { content: [{ type: "text", text: JSON.stringify(value) }] });
      },
    };
  }
  if (window.openai?.callTool) {
    const host = window.openai;
    return {
      mode: "codex", canSend: Boolean(host.sendFollowUpMessage), initialView: viewFromResult(host.toolOutput),
      onView: (listener) => {
        const handle = (event: Event) => {
          const view = viewFromResult((event as CustomEvent).detail?.globals?.toolOutput);
          if (view) listener(view);
        };
        window.addEventListener("openai:set_globals", handle);
        return () => window.removeEventListener("openai:set_globals", handle);
      },
      search: async (filters) => unpack<CatalogResult>(await host.callTool("drawai_templates", { action: "search", ...filters })),
      send: async (prompt) => {
        if (!host.sendFollowUpMessage) throw new Error("请复制选择说明到 Codex。");
        await host.sendFollowUpMessage({ prompt });
      },
      selection: async (value) => { host.setWidgetState?.({ modelContent: value }); },
    };
  }
  const url = new URL(window.location.href);
  const view: TemplateFilters = { query: url.searchParams.get("q") || "", category: url.searchParams.get("category") || "" };
  let catalog: Promise<TemplateCatalog> | undefined;
  return {
    mode: "website", canSend: false, initialView: { view }, onView: () => () => {},
    search: async (filters) => {
      catalog ??= fetch(new URL("./template-catalog.json", window.location.href)).then(async (response) => {
        if (!response.ok) throw new Error(`模板目录读取失败（${response.status}）`);
        return response.json() as Promise<TemplateCatalog>;
      });
      return searchCatalog(await catalog, filters);
    },
    send: async () => { throw new Error("请复制选择说明到 Codex。"); }, selection: async () => {},
  };
}
