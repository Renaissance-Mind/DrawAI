export type AgentLogEntry = { source: string; item: Record<string, unknown> };

export type AgentLogTone = "request" | "tool" | "success" | "error" | "message" | "runtime" | "raw";

export type AgentLogMetaItem = {
  label: string;
  value: string;
};

export type AgentLogDisplayItem = {
  source: string;
  sourceLabel: string;
  sourceFile: string;
  kind: string;
  tone: AgentLogTone;
  title: string;
  detail: string;
  meta: AgentLogMetaItem[];
  raw: Record<string, unknown>;
  rawText: string;
};

export type AgentLogStats = {
  total: number;
  toolCalls: number;
  errors: number;
  finalResponses: number;
};

export function buildAgentLogDisplayItem(entry: AgentLogEntry, index: number): AgentLogDisplayItem {
  const item = entry.item;
  const event = recordField(item, "event") || item;
  const kind = stringField(event, "type") || stringField(item, "type") || stringField(item, "kind") || stringField(item, "event_type") || stringField(item, "level") || entry.source;
  const sourceFile = stringField(item, "source");
  const summary = stringField(item, "summary") || stringField(item, "message");
  const meta: AgentLogMetaItem[] = [];
  let tone: AgentLogTone = "raw";
  let title = kind || `事件 ${index + 1}`;
  let detail = summary;

  addMeta(meta, "来源", sourceFile);
  addMeta(meta, "序号", displayScalar(item.index));

  if (entry.source === "summary") {
    tone = "success";
    title = "最终响应";
    detail = summary || stringField(event, "final_response");
    addMeta(meta, "状态", stringField(event, "status"));
  } else if (entry.source === "runtime") {
    tone = "runtime";
    title = stringField(item, "event_type") || "运行时事件";
    detail = stringField(item, "message") || summary;
    addMeta(meta, "级别", stringField(item, "level"));
    addMeta(meta, "目标", stringField(item, "target"));
  } else if (entry.source === "session") {
    const sessionDisplay = sessionEventDisplay(item, event, summary, kind);
    tone = sessionDisplay.tone;
    title = sessionDisplay.title;
    detail = sessionDisplay.detail;
    for (const metaItem of sessionDisplay.meta) meta.push(metaItem);
  } else {
    const traceDisplay = traceEventDisplay(event, summary, kind);
    tone = traceDisplay.tone;
    title = traceDisplay.title;
    detail = traceDisplay.detail;
    for (const metaItem of traceDisplay.meta) meta.push(metaItem);
  }

  return {
    source: entry.source,
    sourceLabel: agentLogSourceLabel(entry.source),
    sourceFile,
    kind,
    tone,
    title,
    detail: detail || summary || jsonPreview(event),
    meta,
    raw: item,
    rawText: jsonPreview(item)
  };
}

export function agentLogStats(items: AgentLogDisplayItem[]): AgentLogStats {
  return {
    total: items.length,
    toolCalls: items.filter((item) => item.kind === "tool_agent_turn" || item.kind === "tool_agent_tool_result").length,
    errors: items.filter((item) => item.tone === "error").length,
    finalResponses: items.filter((item) => item.title === "最终响应").length
  };
}

export function agentLogSummaryItem(summary: unknown): AgentLogEntry | null {
  if (!isRecord(summary)) return null;
  const finalResponse = stringField(summary, "final_response").trim();
  if (!finalResponse) return null;
  return {
    source: "summary",
    item: {
      kind: stringField(summary, "status") || "final",
      summary: finalResponse,
      event: summary
    }
  };
}

export function agentLogEntryVisible(entry: AgentLogEntry): boolean {
  const eventType = stringField(entry.item, "event_type");
  if (eventType === "response.output_text.delta" || eventType === "response.function_call_arguments.delta") {
    return false;
  }
  const summary = stringField(entry.item, "summary") || stringField(entry.item, "message");
  if (summary.trim().length > 0) return true;
  const event = recordField(entry.item, "event");
  return Boolean(event && (stringField(event, "type") || stringField(event, "kind") || stringField(event, "message")));
}

function traceEventDisplay(event: Record<string, unknown>, summary: string, kind: string): Omit<AgentLogDisplayItem, "source" | "sourceLabel" | "sourceFile" | "kind" | "raw" | "rawText"> {
  const meta: AgentLogMetaItem[] = [];
  if (kind === "tool_agent_request") {
    const images = arrayField(event, "images");
    addMeta(meta, "模型", stringField(event, "model_name"));
    addMeta(meta, "协议", stringField(event, "wire_api"));
    addMeta(meta, "图片", images.length ? String(images.length) : "");
    addMeta(meta, "超时", secondsText(event.timeout_seconds));
    return {
      tone: "request",
      title: "启动内置 Agent",
      detail: compactJoin([stringField(event, "model_name"), stringField(event, "wire_api"), images.length ? `${images.length} 张图片` : ""]),
      meta
    };
  }

  if (kind === "tool_agent_turn") {
    const toolNames = toolCallNames(event);
    addMeta(meta, "轮次", displayScalar(event.iteration));
    addMeta(meta, "工具", toolNames.join(", "));
    return {
      tone: "tool",
      title: "Agent 请求工具",
      detail: toolNames.length ? toolNames.join(" -> ") : summary,
      meta
    };
  }

  if (kind === "tool_agent_tool_result") {
    const result = recordField(event, "result");
    const tool = stringField(event, "tool") || "tool";
    const ok = result ? booleanField(result, "ok") : null;
    addMeta(meta, "耗时", millisecondsText(event.duration_ms));
    if (result) {
      addMeta(meta, "输出", stringField(result, "path"));
      addMeta(meta, "大小", bytesText(result.bytes));
      addMeta(meta, "SHA", shortHash(stringField(result, "sha256")));
    }
    return {
      tone: ok === false ? "error" : "success",
      title: `工具结果：${tool}`,
      detail: result ? toolResultDetail(tool, result, summary) : summary,
      meta
    };
  }

  if (kind === "tool_agent_response") {
    addMeta(meta, "耗时", millisecondsText(event.duration_ms));
    addMeta(meta, "轮次", displayScalar(event.iterations));
    addMeta(meta, "工具调用", displayScalar(event.tool_calls));
    return {
      tone: "success",
      title: "最终响应",
      detail: stringField(event, "final_excerpt") || summary,
      meta
    };
  }

  if (kind === "agent_request" || kind === "agent_cli_request" || kind === "acp_agent_request") {
    addMeta(meta, "Provider", stringField(event, "provider_id") || stringField(event, "agent"));
    addMeta(meta, "任务", stringField(event, "task_name"));
    return {
      tone: "request",
      title: kind === "acp_agent_request" ? "启动 ACP Agent" : "启动 Agent",
      detail: compactJoin([stringField(event, "provider_id") || stringField(event, "agent"), stringField(event, "task_name")]) || summary,
      meta
    };
  }

  if (kind === "agent_response" || kind === "agent_cli_response" || kind === "acp_agent_response") {
    addMeta(meta, "返回码", displayScalar(event.returncode));
    addMeta(meta, "来源", stringField(event, "source"));
    const returnCode = event.returncode;
    return {
      tone: returnCode === 0 || returnCode === "0" || returnCode === undefined ? "success" : "error",
      title: "Agent 响应",
      detail: summary || stringField(event, "message") || stringField(event, "source"),
      meta
    };
  }

  if (kind.startsWith("acp_")) {
    addMeta(meta, "Agent", stringField(event, "agent"));
    addMeta(meta, "Method", stringField(event, "method"));
    return {
      tone: kind.includes("error") ? "error" : "message",
      title: acpTitle(kind),
      detail: compactJoin([stringField(event, "method"), stringField(event, "message")]) || summary,
      meta
    };
  }

  return {
    tone: kind.includes("error") || stringField(event, "level").toLowerCase() === "error" ? "error" : "raw",
    title: kind || "Trace event",
    detail: summary || jsonPreview(event),
    meta
  };
}

function sessionEventDisplay(item: Record<string, unknown>, event: Record<string, unknown>, summary: string, kind: string): Omit<AgentLogDisplayItem, "source" | "sourceLabel" | "sourceFile" | "kind" | "raw" | "rawText"> {
  const meta: AgentLogMetaItem[] = [];
  if (kind === "commandExecution") {
    addMeta(meta, "状态", stringField(event, "status"));
    addMeta(meta, "退出码", displayScalar(event.exitCode));
    return {
      tone: event.exitCode === 0 || event.exitCode === "0" || event.exitCode === undefined ? "success" : "error",
      title: "命令执行",
      detail: stringField(event, "command") || summary,
      meta
    };
  }

  if (kind === "agentMessage") {
    const phase = stringField(event, "phase") || "message";
    addMeta(meta, "阶段", phase);
    return {
      tone: phase === "final_answer" ? "success" : "message",
      title: phase === "final_answer" ? "最终响应" : "Agent 消息",
      detail: stringField(event, "text") || summary,
      meta
    };
  }

  if (kind === "imageView") {
    return {
      tone: "message",
      title: "查看图片",
      detail: stringField(event, "path") || summary,
      meta
    };
  }

  return {
    tone: kind.includes("error") ? "error" : "message",
    title: kind || stringField(item, "kind") || "Session event",
    detail: summary || jsonPreview(event),
    meta
  };
}

function toolResultDetail(tool: string, result: Record<string, unknown>, summary: string): string {
  if (tool === "copy_file") {
    const source = stringField(result, "source");
    const path = stringField(result, "path");
    return compactJoin([source && path ? `${source} -> ${path}` : path || source, validationText(result)]);
  }
  if (tool === "open_image") {
    const dimensions = imageDimensionsText(result);
    return compactJoin([stringField(result, "path"), dimensions, stringField(result, "encoding") || stringField(result, "mime_type")]);
  }
  return compactJoin([stringField(result, "message"), stringField(result, "path"), validationText(result)]) || summary || jsonPreview(result);
}

function validationText(result: Record<string, unknown>): string {
  const validation = recordField(result, "auto_validation");
  if (!validation) return "";
  const ok = booleanField(validation, "ok");
  if (ok === null) return "";
  return ok ? "validation ok" : "validation failed";
}

function imageDimensionsText(result: Record<string, unknown>): string {
  const width = displayScalar(result.width_px);
  const height = displayScalar(result.height_px);
  return width && height ? `${width}x${height}` : "";
}

function toolCallNames(event: Record<string, unknown>): string[] {
  return arrayField(event, "tool_calls")
    .map((item) => (isRecord(item) ? stringField(item, "name") : ""))
    .filter(Boolean);
}

function addMeta(meta: AgentLogMetaItem[], label: string, value: string): void {
  const trimmed = value.trim();
  if (trimmed) meta.push({ label, value: trimmed });
}

function agentLogSourceLabel(source: string): string {
  if (source === "trace") return "Trace";
  if (source === "session") return "Session";
  if (source === "runtime") return "Runtime";
  if (source === "summary") return "Summary";
  return source || "Log";
}

function acpTitle(kind: string): string {
  if (kind === "acp_request") return "ACP 请求";
  if (kind === "acp_notification") return "ACP 通知";
  if (kind === "acp_client_method") return "ACP 方法";
  if (kind.includes("error")) return "ACP 错误";
  return "ACP 事件";
}

function displayScalar(value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}

function millisecondsText(value: unknown): string {
  if (typeof value !== "number") return "";
  if (value >= 1000) return `${(value / 1000).toFixed(1)}s`;
  return `${Math.round(value)}ms`;
}

function secondsText(value: unknown): string {
  if (typeof value !== "number") return "";
  return `${value}s`;
}

function bytesText(value: unknown): string {
  if (typeof value !== "number") return "";
  if (value >= 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`;
  if (value >= 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${value} B`;
}

function shortHash(value: string): string {
  return value.length > 12 ? `${value.slice(0, 12)}...` : value;
}

function compactJoin(values: string[]): string {
  return values.map((value) => value.trim()).filter(Boolean).join(" · ");
}

function stringField(item: Record<string, unknown>, key: string): string {
  const value = item[key];
  return typeof value === "string" ? value : "";
}

function booleanField(item: Record<string, unknown>, key: string): boolean | null {
  const value = item[key];
  return typeof value === "boolean" ? value : null;
}

function recordField(item: Record<string, unknown>, key: string): Record<string, unknown> | null {
  const value = item[key];
  return isRecord(value) ? value : null;
}

function arrayField(item: Record<string, unknown>, key: string): unknown[] {
  const value = item[key];
  return Array.isArray(value) ? value : [];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function jsonPreview(value: unknown): string {
  return JSON.stringify(value, null, 2) || "";
}
