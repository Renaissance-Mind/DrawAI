import type { ApiPreset, ImageGenerationProvider, WorkbenchAgentDiscovery } from "./types";

export interface ImageGenConnectionSettings {
  provider: ImageGenerationProvider;
  baseUrl: string;
  apiKey: string;
  model: string;
  methodId?: string;
  apiPresetId?: string;
  label?: string;
}

export type ImageGenMethodKind = "codex_builtin" | "api_preset" | "custom";

export interface ImageGenMethodCard {
  id: string;
  kind: ImageGenMethodKind;
  provider: ImageGenerationProvider;
  label: string;
  detail: string;
  model: string;
  selected: boolean;
  available: boolean;
  apiPresetId: string;
  baseUrl: string;
}

export type ImageGenMethodSelection =
  | { kind: "codex_builtin" }
  | { kind: "api_preset"; preset: ApiPreset }
  | { kind: "custom" };

export const CODEX_IMAGEGEN_METHOD_ID = "codex_builtin";
export const CUSTOM_IMAGEGEN_METHOD_ID = "custom";
const IMAGEGEN_DEFAULT_MODEL = "gpt-image-2";
const IMAGEGEN_DEFAULT_BASE_URL = "https://api.openai.com/v1";

export function codexImageGenAvailable(agents: Array<Partial<WorkbenchAgentDiscovery>>): boolean {
  return agents.some((agent) => agent.provider_id === "codex_sdk" && agent.available === true);
}

export function imageGenMethodCards(
  connection: ImageGenConnectionSettings,
  presets: ApiPreset[],
  agents: Array<Partial<WorkbenchAgentDiscovery>>
): ImageGenMethodCard[] {
  const normalized = normalizeImageGenConnection(connection);
  const imagesApiPresets = imageGenApiPresets(presets);
  const selectedId = selectedImageGenMethodId(normalized, imagesApiPresets);
  const codexAvailable = codexImageGenAvailable(agents);
  const cards: ImageGenMethodCard[] = [];
  if (codexAvailable || normalized.provider === "codex") {
    cards.push({
      id: CODEX_IMAGEGEN_METHOD_ID,
      kind: "codex_builtin",
      provider: "codex",
      label: "Codex 内置",
      detail: codexAvailable ? "Codex SDK 图像生成" : "未检测到可用 Codex SDK",
      model: normalized.provider === "codex" ? normalized.model : IMAGEGEN_DEFAULT_MODEL,
      selected: selectedId === CODEX_IMAGEGEN_METHOD_ID,
      available: codexAvailable,
      apiPresetId: "",
      baseUrl: ""
    });
  }
  for (const preset of imagesApiPresets) {
    const id = apiPresetMethodId(preset.id);
    cards.push({
      id,
      kind: "api_preset",
      provider: "api",
      label: preset.label || preset.id,
      detail: preset.base_url || "Images API",
      model: preset.model,
      selected: selectedId === id,
      available: true,
      apiPresetId: preset.id,
      baseUrl: preset.base_url
    });
  }
  if (normalized.provider === "api" && !cards.some((card) => card.selected)) {
    cards.push(customImageGenMethodCard(normalized, true));
  }
  if (cards.length === 0) {
    cards.push(customImageGenMethodCard(normalized, selectedId === CUSTOM_IMAGEGEN_METHOD_ID));
  }
  return cards;
}

export function imageGenMethodPickerOptions(
  presets: ApiPreset[],
  agents: Array<Partial<WorkbenchAgentDiscovery>>
): ImageGenMethodCard[] {
  const options = [
    customImageGenMethodCard(
      {
        provider: "api",
        baseUrl: IMAGEGEN_DEFAULT_BASE_URL,
        apiKey: "",
        model: IMAGEGEN_DEFAULT_MODEL,
        methodId: CUSTOM_IMAGEGEN_METHOD_ID,
        apiPresetId: "",
        label: "自定义"
      },
      false
    )
  ];
  if (codexImageGenAvailable(agents)) {
    options.push({
      id: CODEX_IMAGEGEN_METHOD_ID,
      kind: "codex_builtin",
      provider: "codex",
      label: "Codex 内置",
      detail: "使用已检测到的 Codex SDK",
      model: IMAGEGEN_DEFAULT_MODEL,
      selected: false,
      available: true,
      apiPresetId: "",
      baseUrl: ""
    });
  }
  return [
    ...options,
    ...imageGenApiPresets(presets).map((preset) => ({
      id: apiPresetMethodId(preset.id),
      kind: "api_preset" as const,
      provider: "api" as const,
      label: preset.label || preset.id,
      detail: `${preset.model} · ${preset.base_url}`,
      model: preset.model,
      selected: false,
      available: true,
      apiPresetId: preset.id,
      baseUrl: preset.base_url
    }))
  ];
}

export function imageGenConnectionFromMethod(
  selection: ImageGenMethodSelection,
  fallback: ImageGenConnectionSettings
): ImageGenConnectionSettings {
  const normalized = normalizeImageGenConnection(fallback);
  if (selection.kind === "codex_builtin") {
    return {
      provider: "codex",
      baseUrl: "",
      apiKey: "",
      model: normalized.model || IMAGEGEN_DEFAULT_MODEL,
      methodId: CODEX_IMAGEGEN_METHOD_ID,
      apiPresetId: "",
      label: "Codex 内置"
    };
  }
  if (selection.kind === "api_preset") {
    return {
      provider: "api",
      baseUrl: selection.preset.base_url,
      apiKey: selection.preset.api_key || normalized.apiKey,
      model: selection.preset.model || IMAGEGEN_DEFAULT_MODEL,
      methodId: apiPresetMethodId(selection.preset.id),
      apiPresetId: selection.preset.id,
      label: selection.preset.label || selection.preset.id
    };
  }
  return {
    provider: "api",
    baseUrl: normalized.provider === "api" && normalized.baseUrl ? normalized.baseUrl : IMAGEGEN_DEFAULT_BASE_URL,
    apiKey: normalized.provider === "api" ? normalized.apiKey : "",
    model: normalized.model || IMAGEGEN_DEFAULT_MODEL,
    methodId: CUSTOM_IMAGEGEN_METHOD_ID,
    apiPresetId: "",
    label: normalized.provider === "api" && !normalized.apiPresetId && normalized.methodId === CUSTOM_IMAGEGEN_METHOD_ID
      ? normalized.label || "自定义"
      : "自定义"
  };
}

export function imageGenConnectionFromMethodCard(
  method: ImageGenMethodCard,
  presets: ApiPreset[],
  fallback: ImageGenConnectionSettings
): ImageGenConnectionSettings {
  if (method.kind === "codex_builtin") {
    return imageGenConnectionFromMethod({ kind: "codex_builtin" }, fallback);
  }
  if (method.kind === "api_preset") {
    const preset = presets.find((item) => item.id === method.apiPresetId);
    if (preset) return imageGenConnectionFromMethod({ kind: "api_preset", preset }, fallback);
  }
  return imageGenConnectionFromMethod({ kind: "custom" }, fallback);
}

export function resolveImageGenConnectionDraft(
  connection: ImageGenConnectionSettings,
  presets: ApiPreset[]
): ImageGenConnectionSettings {
  const normalized = normalizeImageGenConnection(connection);
  if (normalized.provider === "codex") return normalized;

  const imagesApiPresets = imageGenApiPresets(presets);
  const selectedPreset =
    (normalized.apiPresetId ? imagesApiPresets.find((preset) => preset.id === normalized.apiPresetId) : null) ||
    (normalized.methodId?.startsWith("api_preset:")
      ? imagesApiPresets.find((preset) => apiPresetMethodId(preset.id) === normalized.methodId)
      : null) ||
    imagesApiPresets.find(
      (preset) =>
        preset.base_url.trim().replace(/\/+$/, "") === normalized.baseUrl &&
        preset.model.trim() === normalized.model
    );

  if (selectedPreset) {
    return imageGenConnectionFromMethod({ kind: "api_preset", preset: selectedPreset }, normalized);
  }
  return imageGenConnectionFromMethod({ kind: "custom" }, normalized);
}

export function normalizeImageGenConnection(connection: Partial<ImageGenConnectionSettings> | null | undefined): ImageGenConnectionSettings {
  const provider: ImageGenerationProvider = connection?.provider === "api" ? "api" : "codex";
  const apiPresetId = String(connection?.apiPresetId || "").trim();
  const methodId = String(connection?.methodId || "").trim();
  return {
    provider,
    baseUrl: String(connection?.baseUrl || "").trim().replace(/\/+$/, ""),
    apiKey: String(connection?.apiKey || "").trim(),
    model: String(connection?.model || IMAGEGEN_DEFAULT_MODEL).trim() || IMAGEGEN_DEFAULT_MODEL,
    methodId: methodId || (provider === "codex" ? CODEX_IMAGEGEN_METHOD_ID : apiPresetId ? apiPresetMethodId(apiPresetId) : CUSTOM_IMAGEGEN_METHOD_ID),
    apiPresetId,
    label: String(connection?.label || "").trim()
  };
}

export function imageGenApiPresets(presets: ApiPreset[]): ApiPreset[] {
  return presets.filter((preset) => preset.type === "images_api");
}

export function apiPresetMethodId(presetId: string): string {
  return `api_preset:${presetId}`;
}

function selectedImageGenMethodId(connection: ImageGenConnectionSettings, presets: ApiPreset[]): string {
  if (connection.provider === "codex") return CODEX_IMAGEGEN_METHOD_ID;
  if (connection.apiPresetId && presets.some((preset) => preset.id === connection.apiPresetId)) {
    return apiPresetMethodId(connection.apiPresetId);
  }
  const methodId = connection.methodId || "";
  if (methodId.startsWith("api_preset:") && presets.some((preset) => apiPresetMethodId(preset.id) === methodId)) {
    return methodId;
  }
  const matchingPreset = presets.find(
    (preset) =>
      preset.base_url.replace(/\/+$/, "") === connection.baseUrl.replace(/\/+$/, "") &&
      preset.model.trim() === connection.model.trim()
  );
  return matchingPreset ? apiPresetMethodId(matchingPreset.id) : CUSTOM_IMAGEGEN_METHOD_ID;
}

function customImageGenMethodCard(connection: ImageGenConnectionSettings, selected: boolean): ImageGenMethodCard {
  return {
    id: CUSTOM_IMAGEGEN_METHOD_ID,
    kind: "custom",
    provider: "api",
    label: connection.label || "自定义",
    detail: connection.baseUrl || "手动填写 endpoint 和密钥",
    model: connection.model || IMAGEGEN_DEFAULT_MODEL,
    selected,
    available: true,
    apiPresetId: "",
    baseUrl: connection.baseUrl
  };
}
