export function projectIdFromToolResult(value: unknown): string | undefined {
  if (!value || typeof value !== "object") return undefined;
  const record = value as Record<string, unknown>;
  const data =
    record.structuredContent && typeof record.structuredContent === "object"
      ? (record.structuredContent as Record<string, unknown>)
      : record;
  const view = data.view as { project_id?: unknown } | undefined;
  const project = data.project as { id?: unknown } | undefined;
  const id = view?.project_id ?? project?.id;
  return typeof id === "string" && /^project_[a-f0-9]{16}$/.test(id)
    ? id
    : undefined;
}

export function projectIdFromToolInput(value: unknown): string | undefined {
  if (!value || typeof value !== "object") return undefined;
  const record = value as Record<string, unknown>;
  const args =
    record.arguments && typeof record.arguments === "object"
      ? (record.arguments as Record<string, unknown>)
      : record;
  const id = args.project_id;
  return typeof id === "string" && /^project_[a-f0-9]{16}$/.test(id)
    ? id
    : undefined;
}
