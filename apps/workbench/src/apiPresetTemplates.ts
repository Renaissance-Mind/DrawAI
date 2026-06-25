import type { ApiPreset } from "./types";

export interface ApiPresetTemplate {
  id: string;
  label: string;
  description: string;
  type: ApiPreset["type"];
  base_url: string;
  model: string;
  api_key_env: string;
  accent_color: string;
  icon_url: string;
  model_fetch: "openai_compatible" | "openrouter" | "ollama" | "none";
  badge_label: string;
  suggested_models: string[];
}

// Curated from LiteLLM's MIT-licensed provider/model metadata and checked against provider docs.
// Keep this list small: it is a template gallery, not a full model catalog.
export const API_PRESET_TEMPLATES: ApiPresetTemplate[] = [
  {
    id: "openai_responses",
    label: "OpenAI",
    description: "Responses API for OpenAI chat, vision, and tool-capable models.",
    type: "llm_responses",
    base_url: "https://api.openai.com/v1",
    model: "gpt-4o",
    api_key_env: "OPENAI_API_KEY",
    accent_color: "#111827",
    icon_url: "/provider-icons/openai.svg",
    model_fetch: "openai_compatible",
    badge_label: "OpenAI 兼容",
    suggested_models: ["gpt-4o", "gpt-4o-mini", "gpt-4.1"]
  },
  {
    id: "openai_images",
    label: "OpenAI Images",
    description: "Images API preset for generated and edited visual assets.",
    type: "images_api",
    base_url: "https://api.openai.com/v1",
    model: "gpt-image-2",
    api_key_env: "OPENAI_API_KEY",
    accent_color: "#0f766e",
    icon_url: "/provider-icons/openai-images.svg",
    model_fetch: "none",
    badge_label: "Images API",
    suggested_models: ["gpt-image-2", "gpt-image-1.5", "dall-e-3"]
  },
  {
    id: "deepseek",
    label: "DeepSeek",
    description: "OpenAI-compatible chat and reasoning models from DeepSeek.",
    type: "llm_chat_completions",
    base_url: "https://api.deepseek.com/v1",
    model: "deepseek-chat",
    api_key_env: "DEEPSEEK_API_KEY",
    accent_color: "#4d6bfe",
    icon_url: "/provider-icons/deepseek.svg",
    model_fetch: "openai_compatible",
    badge_label: "OpenAI 兼容",
    suggested_models: ["deepseek-chat", "deepseek-reasoner"]
  },
  {
    id: "openrouter",
    label: "OpenRouter",
    description: "Unified OpenAI-compatible access to many model providers.",
    type: "llm_chat_completions",
    base_url: "https://openrouter.ai/api/v1",
    model: "openai/gpt-4o-mini",
    api_key_env: "OPENROUTER_API_KEY",
    accent_color: "#111111",
    icon_url: "/provider-icons/openrouter.svg",
    model_fetch: "openrouter",
    badge_label: "OpenAI 兼容",
    suggested_models: ["openai/gpt-4o-mini", "anthropic/claude-sonnet-4.5", "google/gemini-2.5-flash"]
  },
  {
    id: "dashscope_qwen",
    label: "Qwen / DashScope",
    description: "Alibaba Cloud compatible-mode endpoint for Qwen chat models.",
    type: "llm_chat_completions",
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    model: "qwen-plus",
    api_key_env: "DASHSCOPE_API_KEY",
    accent_color: "#615ced",
    icon_url: "/provider-icons/qwen.svg",
    model_fetch: "openai_compatible",
    badge_label: "OpenAI 兼容",
    suggested_models: ["qwen-plus", "qwen-turbo", "qwen-max"]
  },
  {
    id: "moonshot",
    label: "Moonshot",
    description: "Kimi and Moonshot models through an OpenAI-compatible API.",
    type: "llm_chat_completions",
    base_url: "https://api.moonshot.cn/v1",
    model: "kimi-latest",
    api_key_env: "MOONSHOT_API_KEY",
    accent_color: "#0ea5e9",
    icon_url: "/provider-icons/moonshot.png",
    model_fetch: "openai_compatible",
    badge_label: "OpenAI 兼容",
    suggested_models: ["kimi-latest", "kimi-latest-128k", "moonshot-v1-32k"]
  },
  {
    id: "zai",
    label: "Z.ai",
    description: "GLM family models through an OpenAI-compatible endpoint.",
    type: "llm_chat_completions",
    base_url: "https://api.z.ai/api/paas/v4",
    model: "glm-4.6",
    api_key_env: "ZAI_API_KEY",
    accent_color: "#6d5dfc",
    icon_url: "/provider-icons/zai.svg",
    model_fetch: "openai_compatible",
    badge_label: "OpenAI 兼容",
    suggested_models: ["glm-4.6", "glm-4.5", "glm-4.5-flash"]
  },
  {
    id: "groq",
    label: "Groq",
    description: "Fast OpenAI-compatible inference for hosted open models.",
    type: "llm_chat_completions",
    base_url: "https://api.groq.com/openai/v1",
    model: "llama-3.3-70b-versatile",
    api_key_env: "GROQ_API_KEY",
    accent_color: "#f55036",
    icon_url: "/provider-icons/groq.svg",
    model_fetch: "openai_compatible",
    badge_label: "OpenAI 兼容",
    suggested_models: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-120b"]
  },
  {
    id: "mistral",
    label: "Mistral",
    description: "Mistral chat and coding models through the v1 API.",
    type: "llm_chat_completions",
    base_url: "https://api.mistral.ai/v1",
    model: "mistral-large-latest",
    api_key_env: "MISTRAL_API_KEY",
    accent_color: "#ff7000",
    icon_url: "/provider-icons/mistral.svg",
    model_fetch: "openai_compatible",
    badge_label: "OpenAI 兼容",
    suggested_models: ["mistral-large-latest", "mistral-small-latest", "codestral-latest"]
  },
  {
    id: "xai",
    label: "xAI",
    description: "Grok models exposed with an OpenAI-compatible API.",
    type: "llm_chat_completions",
    base_url: "https://api.x.ai/v1",
    model: "grok-4-latest",
    api_key_env: "XAI_API_KEY",
    accent_color: "#202124",
    icon_url: "/provider-icons/xai.svg",
    model_fetch: "openai_compatible",
    badge_label: "OpenAI 兼容",
    suggested_models: ["grok-4-latest", "grok-3-latest", "grok-code-fast-1"]
  },
  {
    id: "aihubmix",
    label: "AiHubMix",
    description: "OpenAI-compatible aggregator endpoint for multiple model families.",
    type: "llm_chat_completions",
    base_url: "https://aihubmix.com/v1",
    model: "gpt-4o-mini",
    api_key_env: "AIHUBMIX_API_KEY",
    accent_color: "#2563eb",
    icon_url: "/provider-icons/aihubmix.svg",
    model_fetch: "openai_compatible",
    badge_label: "OpenAI 兼容",
    suggested_models: ["gpt-4o-mini", "deepseek-chat", "claude-3-5-sonnet-20241022"]
  },
  {
    id: "lmstudio",
    label: "LM Studio",
    description: "Local OpenAI-compatible server for downloaded desktop models.",
    type: "llm_chat_completions",
    base_url: "http://localhost:1234/v1",
    model: "local-model",
    api_key_env: "",
    accent_color: "#0f9f6e",
    icon_url: "/provider-icons/lmstudio.svg",
    model_fetch: "openai_compatible",
    badge_label: "本地服务",
    suggested_models: ["local-model"]
  },
  {
    id: "ollama",
    label: "Ollama",
    description: "Local OpenAI-compatible endpoint backed by Ollama models.",
    type: "llm_chat_completions",
    base_url: "http://localhost:11434/v1",
    model: "llama3.1",
    api_key_env: "",
    accent_color: "#111827",
    icon_url: "/provider-icons/ollama.svg",
    model_fetch: "ollama",
    badge_label: "本地服务",
    suggested_models: ["llama3.1", "qwen2.5", "deepseek-r1"]
  }
];

export function apiPresetDraftFromTemplate(template: ApiPresetTemplate, existing: ApiPreset[]): ApiPreset {
  return {
    id: uniqueApiPresetId(existing, template.id),
    label: template.label,
    type: template.type,
    base_url: template.base_url,
    model: template.model,
    api_key_env: template.api_key_env,
    api_key: ""
  };
}

export function apiPresetTemplateForPreset(preset: ApiPreset): ApiPresetTemplate | null {
  const normalizedPresetId = preset.id.replace(/_\d+$/, "");
  return (
    API_PRESET_TEMPLATES.find(
      (template) =>
        template.id === preset.id ||
        template.id === normalizedPresetId ||
        (template.base_url === preset.base_url && template.model === preset.model)
    ) || null
  );
}

export function apiPresetTemplateSearchText(template: ApiPresetTemplate): string {
  return [
    template.id,
    template.label,
    template.description,
    template.type,
    template.base_url,
    template.model,
    template.api_key_env,
    template.badge_label,
    ...template.suggested_models
  ]
    .join(" ")
    .toLowerCase();
}

export function blankApiPresetDraft(existing: ApiPreset[]): ApiPreset {
  return {
    id: uniqueApiPresetId(existing, "api_preset"),
    label: "新建 API 预设",
    type: "images_api",
    base_url: "https://api.openai.com/v1",
    model: "gpt-image-2",
    api_key_env: "OPENAI_API_KEY",
    api_key: ""
  };
}

export function uniqueApiPresetId(existing: ApiPreset[], base: string): string {
  const normalizedBase = base.replace(/[^a-zA-Z0-9_-]/g, "_") || "api_preset";
  const taken = new Set(existing.map((preset) => preset.id));
  if (!taken.has(normalizedBase)) return normalizedBase;
  for (let index = 2; index < 1000; index += 1) {
    const candidate = `${normalizedBase}_${index}`;
    if (!taken.has(candidate)) return candidate;
  }
  return `${normalizedBase}_${Date.now()}`;
}
