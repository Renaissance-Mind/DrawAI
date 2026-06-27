export interface AgentProviderIcon {
  accent_color: string;
  icon_url: string;
}

export const AGENT_PROVIDER_ICONS: Record<string, AgentProviderIcon> = {
  codex_sdk: {
    accent_color: "#111827",
    icon_url: "/agent-icons/codex.svg"
  },
  codex_cli: {
    accent_color: "#111827",
    icon_url: "/agent-icons/codex.svg"
  },
  kimi_cli: {
    accent_color: "#111827",
    icon_url: "/agent-icons/kimi.png"
  },
  kimi_acp: {
    accent_color: "#111827",
    icon_url: "/agent-icons/kimi.png"
  },
  gemini_acp: {
    accent_color: "#4285f4",
    icon_url: "/agent-icons/gemini-cli.svg"
  },
  qwen_acp: {
    accent_color: "#615ced",
    icon_url: "/agent-icons/qwen.svg"
  },
  opencode_acp: {
    accent_color: "#111111",
    icon_url: "/agent-icons/opencode.svg"
  },
  goose_acp: {
    accent_color: "#111827",
    icon_url: "/agent-icons/goose.svg"
  },
  kiro_acp: {
    accent_color: "#7952ff",
    icon_url: "/agent-icons/kiro.svg"
  },
  qoder_acp: {
    accent_color: "#111827",
    icon_url: "/agent-icons/qoder.svg"
  },
  cursor_acp: {
    accent_color: "#111827",
    icon_url: "/agent-icons/cursor.svg"
  },
  cline_acp: {
    accent_color: "#111827",
    icon_url: "/agent-icons/cline.svg"
  },
  copilot_acp: {
    accent_color: "#111827",
    icon_url: "/agent-icons/github-copilot.svg"
  },
  hermes_acp: {
    accent_color: "#111827",
    icon_url: "/agent-icons/hermes-agent.svg"
  },
  claude_cli: {
    accent_color: "#d97757",
    icon_url: "/agent-icons/claude-code.svg"
  },
  openclaw_cli: {
    accent_color: "#3168f5",
    icon_url: "/agent-icons/openclaw.svg"
  },
  hermes_cli: {
    accent_color: "#111827",
    icon_url: "/agent-icons/hermes-agent.svg"
  },
  drawai_tool_agent: {
    accent_color: "#0f172a",
    icon_url: "/drawai_image.png"
  }
};

export function agentProviderIconForId(providerId: string): AgentProviderIcon | null {
  return AGENT_PROVIDER_ICONS[providerId] || null;
}

type SortableWorkbenchAgent = {
  available: boolean;
  provider_id: string;
};

export function sortWorkbenchAgentsForDisplay<T extends SortableWorkbenchAgent>(agents: readonly T[]): T[] {
  return [...agents].sort((first, second) => Number(second.available) - Number(first.available));
}
