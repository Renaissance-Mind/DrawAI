import type {
  ApiPreset,
  ApiPresetEndpoint,
  WorkbenchAgentDiscovery,
  WorkbenchAgentSettings
} from "./types";

export const LLM_ENDPOINT_TYPES = [
  "llm_chat_completions",
  "llm_responses",
  "llm_anthropic"
] as const;

export const DIRECT_LLM_ENDPOINT_TYPES = ["llm_chat_completions", "llm_responses"] as const;

export function isLlmApiPreset(preset: ApiPreset): boolean {
  return preset.type === "llm" || LLM_ENDPOINT_TYPES.includes(preset.type as (typeof LLM_ENDPOINT_TYPES)[number]);
}

export function llmPresetEndpoints(preset: ApiPreset): ApiPresetEndpoint[] {
  if (preset.endpoints?.length) return preset.endpoints;
  if (!LLM_ENDPOINT_TYPES.includes(preset.type as (typeof LLM_ENDPOINT_TYPES)[number])) return [];
  return [
    {
      id: preset.type.replace(/^llm_/, ""),
      label: llmEndpointProtocolLabel(preset.type),
      type: preset.type as ApiPresetEndpoint["type"],
      base_url: preset.base_url,
      model: preset.model,
      api_key_env: preset.api_key_env,
      api_key: preset.api_key
    }
  ];
}

export function compatibleEndpointsForAgent(
  agent: WorkbenchAgentDiscovery | null,
  preset: ApiPreset
): ApiPresetEndpoint[] {
  if (!agent?.api_preset_types.length) return [];
  return llmPresetEndpoints(preset).filter((endpoint) => agent.api_preset_types.includes(endpoint.type));
}

export function compatibleLlmPresetsForAgent(
  agent: WorkbenchAgentDiscovery | null,
  presets: ApiPreset[]
): ApiPreset[] {
  return presets.filter((preset) => compatibleEndpointsForAgent(agent, preset).length > 0);
}

export function compatibleAgentsForEndpoint(
  agents: WorkbenchAgentDiscovery[],
  endpoint: ApiPresetEndpoint | null
): WorkbenchAgentDiscovery[] {
  if (!endpoint) return [];
  return agents.filter((agent) => agent.available && agent.api_preset_types.includes(endpoint.type));
}

export function selectedLlmEndpoint(
  preset: ApiPreset | null,
  endpointId: string
): ApiPresetEndpoint | null {
  if (!preset) return null;
  const endpoints = llmPresetEndpoints(preset);
  return endpoints.find((endpoint) => endpoint.id === endpointId) || endpoints[0] || null;
}

export function preferredCompatibleEndpoint(
  agent: WorkbenchAgentDiscovery | null,
  preset: ApiPreset | null,
  endpointId: string
): ApiPresetEndpoint | null {
  if (!preset) return null;
  const endpoints = compatibleEndpointsForAgent(agent, preset);
  return endpoints.find((endpoint) => endpoint.id === endpointId) || endpoints[0] || null;
}

export function directLlmEndpoints(preset: ApiPreset): ApiPresetEndpoint[] {
  return llmPresetEndpoints(preset).filter((endpoint) =>
    DIRECT_LLM_ENDPOINT_TYPES.includes(endpoint.type as (typeof DIRECT_LLM_ENDPOINT_TYPES)[number])
  );
}

export function agentSettingsWithLlmSelection(
  settings: WorkbenchAgentSettings,
  preset: ApiPreset,
  endpoint: ApiPresetEndpoint
): WorkbenchAgentSettings {
  return {
    ...settings,
    llm_api_preset_id: preset.id,
    llm_endpoint_id: endpoint.id,
    llm_model: endpoint.model,
    llm_base_url: endpoint.base_url,
    llm_api_key: endpoint.api_key,
    llm_api_key_env: endpoint.api_key_env,
    llm_wire_api: wireApiForEndpoint(endpoint)
  };
}

export function wireApiForEndpoint(endpoint: ApiPresetEndpoint): WorkbenchAgentSettings["llm_wire_api"] {
  if (endpoint.type === "llm_anthropic") return "anthropic";
  if (endpoint.type === "llm_responses") return "responses";
  return "chat_completions";
}

export function llmEndpointProtocolLabel(endpointType: string): string {
  if (endpointType === "llm_anthropic") return "Anthropic";
  if (endpointType === "llm_responses") return "Responses";
  return "Chat Completions";
}
