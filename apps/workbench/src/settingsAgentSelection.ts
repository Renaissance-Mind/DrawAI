import type { WorkbenchAgentDiscovery } from "./types";

export type WorkbenchAgentPickerChoice = WorkbenchAgentDiscovery & {
  selected: boolean;
};

export function selectedWorkbenchAgent(
  agents: WorkbenchAgentDiscovery[],
  selectedProviderId: string
): WorkbenchAgentDiscovery | null {
  return agents.find((agent) => agent.provider_id === selectedProviderId) || null;
}

export function workbenchAgentPickerChoices(
  agents: WorkbenchAgentDiscovery[],
  selectedProviderId: string
): WorkbenchAgentPickerChoice[] {
  return agents
    .filter((agent) => agent.available)
    .map((agent) => ({
      ...agent,
      selected: agent.provider_id === selectedProviderId
    }))
    .sort((left, right) => {
      if (left.selected !== right.selected) return left.selected ? -1 : 1;
      return 0;
    });
}
