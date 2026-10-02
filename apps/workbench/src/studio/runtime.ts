import { projectIdFromToolInput, projectIdFromToolResult } from "./hostContext";

type Content = { type: string; text?: string };
interface McpResult {
  isError?: boolean;
  structuredContent?: unknown;
  content?: Content[];
}
interface LegacyBridge {
  callTool(name: string, args: Record<string, unknown>): Promise<McpResult>;
  sendFollowUpMessage?(args: { prompt: string }): Promise<unknown>;
  toolOutput?: unknown;
  setWidgetState?(state: unknown): void;
}
declare global {
  interface Window {
    openai?: LegacyBridge;
  }
}

export interface StudioRuntime {
  mode: "codex" | "browser";
  canSend: boolean;
  initialProjectId(): string | undefined;
  onOpenProject(listener: (projectId: string) => void): () => void;
  call<T>(name: string, args?: Record<string, unknown>): Promise<T>;
  send(prompt: string): Promise<void>;
  context(value: unknown): Promise<void>;
  download(resource: DownloadResource): Promise<DownloadReceipt | void>;
}
export interface DownloadResource {
  project_id: string;
  asset_id?: string;
}
export interface DownloadReceipt {
  filename: string;
  saved_path: string;
  size: number;
  sha256: string;
}

function unpack<T>(result: McpResult): T {
  if (result.isError)
    throw new Error(
      result.content?.find((c) => c.type === "text")?.text ||
        "DrawAI operation failed",
    );
  if (result.structuredContent !== undefined)
    return result.structuredContent as T;
  const text = result.content?.find((c) => c.type === "text")?.text;
  if (!text) throw new Error("DrawAI returned no result");
  return JSON.parse(text) as T;
}
function saveLink(url: string) {
  const a = document.createElement("a");
  a.href = url;
  a.download = "";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

class McpRpcError extends Error {
  constructor(message: string, readonly code?: number) {
    super(message);
  }
}

class McpBridge {
  private sequence = 0;
  projectId: string | undefined;
  projectListeners = new Set<(projectId: string) => void>();
  private pending = new Map<
    string,
    {
      resolve: (value: unknown) => void;
      reject: (reason: Error) => void;
      timer: ReturnType<typeof setTimeout>;
    }
  >();
  constructor() {
    window.addEventListener("message", (event) => {
      if (event.source !== window.parent || event.data?.jsonrpc !== "2.0")
        return;
      const value = event.data;
      if (
        value.method === "ui/notifications/tool-input" ||
        value.method === "ui/notifications/tool-result"
      ) {
        const projectId =
          value.method === "ui/notifications/tool-input"
            ? projectIdFromToolInput(value.params)
            : projectIdFromToolResult(value.params);
        if (projectId) {
          this.projectId = projectId;
          for (const listener of this.projectListeners) listener(projectId);
        }
        return;
      }
      const pending = this.pending.get(value.id);
      if (!pending) return;
      clearTimeout(pending.timer);
      this.pending.delete(value.id);
      if (value.error)
        pending.reject(
          new McpRpcError(
            value.error.message || "Codex request failed",
            value.error.code,
          ),
        );
      else pending.resolve(value.result);
    });
  }
  notify(method: string, params = {}) {
    window.parent.postMessage({ jsonrpc: "2.0", method, params }, "*");
  }
  request<T>(method: string, params: unknown, timeout = 60000): Promise<T> {
    const id = `drawai-${++this.sequence}`;
    return new Promise<T>((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Codex 未响应 ${method}，请重试或重新打开工作台。`));
      }, timeout);
      this.pending.set(id, {
        resolve: (value) => resolve(value as T),
        reject,
        timer,
      });
      window.parent.postMessage({ jsonrpc: "2.0", id, method, params }, "*");
    });
  }
}

let runtimePromise: Promise<StudioRuntime> | undefined;
export function connectStudio(): Promise<StudioRuntime> {
  runtimePromise ??= initializeRuntime().catch((error) => {
    runtimePromise = undefined;
    throw error;
  });
  return runtimePromise;
}
async function initializeRuntime(): Promise<StudioRuntime> {
  if (window.parent !== window) {
    const bridge = new McpBridge();
    const result = await bridge.request<{
      hostCapabilities?: Record<string, unknown>;
    }>(
      "ui/initialize",
      {
        appInfo: { name: "DrawAI Workbench", version: "2.0.2" },
        appCapabilities: { availableDisplayModes: ["inline", "fullscreen"] },
        protocolVersion: "2026-01-26",
      },
      12000,
    );
    bridge.notify("ui/notifications/initialized");
    const capabilities = result.hostCapabilities || {};
    const call = async <T>(name: string, args = {}) =>
      unpack<T>(
        await bridge.request<McpResult>("tools/call", { name, arguments: args }),
      );
    return {
      mode: "codex",
      canSend: Boolean(capabilities.message),
      initialProjectId: () => bridge.projectId,
      onOpenProject: (listener) => {
        bridge.projectListeners.add(listener);
        return () => {
          bridge.projectListeners.delete(listener);
        };
      },
      call,
      send: async (prompt) => {
        if (!capabilities.message)
          throw new Error(
            "当前视图未开放会话消息，请从 Codex 会话重新打开工作台。",
          );
        await bridge.request("ui/message", {
          role: "user",
          content: [{ type: "text", text: prompt }],
        });
      },
      context: async (value) => {
        if (capabilities.updateModelContext)
          await bridge.request("ui/update-model-context", {
            content: [{ type: "text", text: JSON.stringify(value) }],
          });
      },
      download: async (resource) => {
        const save = () => call<DownloadReceipt>("drawai_artifact", {
          action: "save_download",
          ...resource,
        });
        if (!capabilities.downloadFile) return save();
        const data = await call<{
          asset?: { filename: string; mime_type: string };
          filename?: string;
          mime_type?: string;
          data_base64: string;
        }>("drawai_artifact", {
          action: resource.asset_id ? "read" : "archive",
          ...resource,
        });
        const filename = data.asset?.filename || data.filename!;
        const mimeType = data.asset?.mime_type || data.mime_type!;
        try {
          await bridge.request("ui/download-file", {
            contents: [
              {
                type: "resource",
                resource: {
                  uri: `drawai-download:///${encodeURIComponent(filename)}`,
                  mimeType,
                  blob: data.data_base64,
                },
              },
            ],
          });
        } catch (error) {
          if (!(error instanceof McpRpcError) || error.code !== -32601)
            throw error;
          return save();
        }
      },
    };
  }
  if (window.openai?.callTool) {
    const host = window.openai;
    return {
      mode: "codex",
      canSend: Boolean(host.sendFollowUpMessage),
      initialProjectId: () => projectIdFromToolResult(host.toolOutput),
      onOpenProject: (listener) => {
        const handle = (event: Event) => {
          const id = projectIdFromToolResult(
            (event as CustomEvent).detail?.globals?.toolOutput,
          );
          if (id) listener(id);
        };
        window.addEventListener("openai:set_globals", handle);
        return () => window.removeEventListener("openai:set_globals", handle);
      },
      call: async <T>(name: string, args = {}) =>
        unpack<T>(await host.callTool(name, args)),
      send: async (prompt) => {
        if (!host.sendFollowUpMessage)
          throw new Error("当前宿主未开放消息接口");
        await host.sendFollowUpMessage({ prompt });
      },
      context: async (value) => {
        host.setWidgetState?.({ modelContent: value });
      },
      download: async (resource) => unpack<DownloadReceipt>(
        await host.callTool("drawai_artifact", { action: "save_download", ...resource }),
      ),
    };
  }
  return {
    mode: "browser",
    canSend: false,
    initialProjectId: () => undefined,
    onOpenProject: () => () => {},
    call: async <T>(name: string, args = {}) => {
      const response = await fetch("/api/studio/call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, arguments: args }),
      });
      const data = await response.json();
      if (!response.ok)
        throw new Error(data.error || `HTTP ${response.status}`);
      return data as T;
    },
    send: async () => {
      throw new Error(
        "请在 Codex 插件工作台中发送，或将任务请求复制到当前会话。",
      );
    },
    context: async () => {},
    download: async (resource) => {
      saveLink(
        resource.asset_id
          ? `/api/studio/files/${encodeURIComponent(resource.project_id)}/${encodeURIComponent(resource.asset_id)}`
          : `/api/studio/archive/${encodeURIComponent(resource.project_id)}`,
      );
    },
  };
}

export async function fileBase64(file: File): Promise<string> {
  if (file.size > 48 * 1024 * 1024)
    throw new Error("单个文件请控制在 48 MB 以内。");
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error);
    reader.onload = () => resolve(String(reader.result).split(",")[1]);
    reader.readAsDataURL(file);
  });
}
