type WorkflowNodeIconProps = {
  nodeType: string;
};

export function WorkflowNodeIcon({ nodeType }: WorkflowNodeIconProps) {
  if (nodeType === "input") return <InputNodeIcon />;
  if (nodeType === "parser") return <ParserNodeIcon />;
  if (nodeType === "fusion") return <FusionNodeIcon />;
  if (nodeType === "agent") return <AgentNodeIcon />;
  if (nodeType === "processor") return <ProcessorNodeIcon />;
  if (nodeType === "human_review") return <HumanReviewNodeIcon />;
  if (nodeType === "export") return <ExportNodeIcon />;
  if (nodeType === "output") return <OutputNodeIcon />;
  return <GenericNodeIcon />;
}

function InputNodeIcon() {
  return (
    <svg className="workflow-node-type-icon" viewBox="0 0 24 24" aria-hidden="true">
      <rect x="4.5" y="5.5" width="15" height="13" rx="2.5" />
      <path d="m7.5 15 3.2-3.3 2.4 2.5 1.6-1.8 2.8 2.6" />
      <circle cx="15.7" cy="9.2" r="1.2" />
    </svg>
  );
}

function ParserNodeIcon() {
  return (
    <svg className="workflow-node-type-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6.5 9V6.8c0-.7.6-1.3 1.3-1.3H10" />
      <path d="M14 5.5h2.2c.7 0 1.3.6 1.3 1.3V9" />
      <path d="M17.5 15v2.2c0 .7-.6 1.3-1.3 1.3H14" />
      <path d="M10 18.5H7.8c-.7 0-1.3-.6-1.3-1.3V15" />
      <circle cx="11.4" cy="11.4" r="3.1" />
      <path d="m14 14 3 3" />
    </svg>
  );
}

function FusionNodeIcon() {
  return (
    <svg className="workflow-node-type-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 7h3.6c2.2 0 3.2 1.2 4 2.6l.8 1.4c.8 1.4 1.8 2.6 4 2.6H19" />
      <path d="M5 17h3.6c2.2 0 3.2-1.2 4-2.6l.8-1.4c.8-1.4 1.8-2.6 4-2.6H19" />
      <path d="m17 8 2 2-2 2" />
      <path d="m17 12 2 2-2 2" />
    </svg>
  );
}

function AgentNodeIcon() {
  return (
    <svg className="workflow-node-type-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M8.5 17.5h7" />
      <path d="M8 11.2c0-2.3 1.8-4.2 4-4.2s4 1.9 4 4.2c0 1.5-.8 2.9-2 3.6v1.7h-4v-1.7c-1.2-.7-2-2.1-2-3.6Z" />
      <path d="M6.2 8.2 4.8 6.8" />
      <path d="M17.8 8.2 19.2 6.8" />
      <path d="M12 5V3.5" />
      <path d="M10.8 11.3h2.4" />
      <path d="M12 10.1v2.4" />
    </svg>
  );
}

function ProcessorNodeIcon() {
  return (
    <svg className="workflow-node-type-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 8h9" />
      <path d="M5 16h9" />
      <circle cx="17" cy="8" r="2" />
      <circle cx="9" cy="16" r="2" />
      <path d="M19 16h-6" />
    </svg>
  );
}

function HumanReviewNodeIcon() {
  return (
    <svg className="workflow-node-type-icon" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="10" cy="8" r="3" />
      <path d="M5.5 18.5c.7-2.9 2.2-4.3 4.5-4.3 1.5 0 2.7.6 3.5 1.8" />
      <path d="m14.5 17.3 1.8 1.8 3.2-4" />
    </svg>
  );
}

function ExportNodeIcon() {
  return (
    <svg className="workflow-node-type-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6.5 5.5h7l4 4v9a1.8 1.8 0 0 1-1.8 1.8H6.5a1.8 1.8 0 0 1-1.8-1.8V7.3a1.8 1.8 0 0 1 1.8-1.8Z" />
      <path d="M13.5 5.8V10h4" />
      <path d="M9 14h6" />
      <path d="m13 12 2 2-2 2" />
    </svg>
  );
}

function OutputNodeIcon() {
  return (
    <svg className="workflow-node-type-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6 5.5h12v13H6z" />
      <path d="M8.5 13.2 11 15.7l4.7-5.4" />
      <path d="M8.5 8.2h7" />
    </svg>
  );
}

function GenericNodeIcon() {
  return (
    <svg className="workflow-node-type-icon" viewBox="0 0 24 24" aria-hidden="true">
      <rect x="5" y="5" width="14" height="14" rx="3" />
      <path d="M9 9h6v6H9z" />
    </svg>
  );
}
