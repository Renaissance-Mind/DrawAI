import { DragEvent, PointerEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  copyWorkflowTemplate,
  listWorkflowProviders,
  listWorkflowTemplates,
  previewAgentPrompt,
  saveWorkflowTemplate,
  validateWorkflowTemplate
} from "./workflowApi";
import type {
  AgentPromptPreview,
  AgentProviderSpec,
  WorkflowEdge,
  WorkflowNode,
  WorkflowPort,
  WorkflowTemplate,
  WorkflowValidationResult
} from "./workflowTypes";

type DraggingNode = {
  nodeId: string;
  pointerId: number;
  startClientX: number;
  startClientY: number;
  startX: number;
  startY: number;
};

type ConnectingPort = {
  nodeId: string;
  portId: string;
};

type NodePreset = {
  key: string;
  node_type: string;
  title: string;
  icon: string;
  description: string;
  inputs: WorkflowPort[];
  outputs: WorkflowPort[];
  config?: Record<string, unknown>;
};

type AgentInputPreview = ReturnType<typeof workflowInputPreview>[number];
type AgentOutputConfig = {
  port_id: string;
  path: string;
  format_id: string;
  type: string;
  description: string;
};

const NODE_WIDTH = 184;
const NODE_HEIGHT = 102;
const DEFAULT_COPY_NAME = "Custom DrawAI DAG";

const NODE_PRESETS: NodePreset[] = [
  {
    key: "input",
    node_type: "input",
    title: "Input",
    icon: "I",
    description: "Source image input.",
    inputs: [],
    outputs: [port("image", "Image", ["image"], "drawai.image.v1", false)]
  },
  {
    key: "parser",
    node_type: "parser",
    title: "Parser",
    icon: "P",
    description: "Fixed parser node such as SAM or OCR.",
    inputs: [port("image", "Image", ["image"], "drawai.image.v1")],
    outputs: [port("candidates", "Candidates", ["element_candidates"], "drawai.element_candidates.v1", false)],
    config: { parser_id: "custom_parser" }
  },
  {
    key: "merge",
    node_type: "fusion",
    title: "Merge",
    icon: "M",
    description: "Merge compatible outputs before passing to a single-input node.",
    inputs: [port("candidates", "Candidates", ["element_candidates"], "drawai.element_candidates.v1", true, "many")],
    outputs: [port("elements", "Elements", ["element_plans"], "drawai.element_plans.v1", false)],
    config: { fusion_id: "priority_nms" }
  },
  {
    key: "run0-agent",
    node_type: "agent",
    title: "Run0 Agent",
    icon: "A",
    description: "Agent node that refines element plans.",
    inputs: [port("elements", "Element Plans", ["element_plans"], "drawai.element_plans.v1")],
    outputs: [port("elements", "Element Plans", ["element_plans"], "drawai.element_plans.v1", false)],
    config: {
      preset_id: "run0_element_refine",
      provider_id: "codex_sdk",
      prompt_fragments: "Refine element bbox, size, and type. Preserve IDs unless merge/delete is declared.",
      outputs: [
        {
          port_id: "elements",
          path: "output/elements.json",
          format_id: "drawai.element_plans.v1",
          type: "element_plans",
          description: "Refined DrawAI element plans."
        }
      ]
    }
  },
  {
    key: "svg-agent",
    node_type: "agent",
    title: "SVG Agent",
    icon: "A",
    description: "Agent node that generates semantic SVG.",
    inputs: [
      port("elements", "Element Plans", ["element_plans"], "drawai.element_plans.v1"),
      port("asset_packages", "Asset Packages", ["asset_packages"], "drawai.asset_packages.v1")
    ],
    outputs: [port("semantic_svg", "Semantic SVG", ["semantic_svg"], "drawai.semantic_svg.v1", false, "single", "deliverable")],
    config: {
      preset_id: "svg_generation",
      provider_id: "codex_sdk",
      prompt_fragments: "Generate an editable SVG using connected element plans and confirmed assets.",
      outputs: [
        {
          port_id: "semantic_svg",
          path: "output/semantic.svg",
          format_id: "drawai.semantic_svg.v1",
          type: "semantic_svg",
          description: "Editable semantic SVG rooted at an svg element."
        }
      ]
    }
  },
  {
    key: "processor",
    node_type: "processor",
    title: "Processor",
    icon: "R",
    description: "Fixed processor node for asset planning or asset processing.",
    inputs: [port("elements", "Elements", ["element_plans"], "drawai.element_plans.v1")],
    outputs: [port("asset_packages", "Asset Packages", ["asset_packages"], "drawai.asset_packages.v1", false)],
    config: { processor_id: "asset_processors" }
  },
  {
    key: "human",
    node_type: "human_review",
    title: "Asset Confirm",
    icon: "H",
    description: "Human review node that opens the assets canvas/table page.",
    inputs: [port("asset_packages", "Asset Packages", ["asset_packages"], "drawai.asset_packages.v1")],
    outputs: [port("asset_packages", "Confirmed Assets", ["asset_packages"], "drawai.asset_packages.v1", false)],
    config: { review_surface: "assets", result_path: "output/confirmed_asset_packages.json" }
  },
  {
    key: "export",
    node_type: "export",
    title: "SVG to PPT",
    icon: "E",
    description: "Fixed export node.",
    inputs: [port("semantic_svg", "Semantic SVG", ["semantic_svg"], "drawai.semantic_svg.v1")],
    outputs: [port("pptx", "PPTX", ["pptx"], "drawai.pptx.v1", false, "single", "deliverable")],
    config: { exporter_id: "svg_to_ppt" }
  },
  {
    key: "output",
    node_type: "output",
    title: "Output",
    icon: "O",
    description: "Collect visible final files.",
    inputs: [port("deliverables", "Deliverables", ["semantic_svg", "pptx"], "", true, "many")],
    outputs: [port("final_outputs", "Final Outputs", ["final_outputs"], "drawai.final_outputs.v1", false)],
    config: { auto_collect_deliverables: true }
  }
];

export default function WorkflowWorkspace({ onError }: { onError: (message: string) => void }) {
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [providers, setProviders] = useState<AgentProviderSpec[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [draft, setDraft] = useState<WorkflowTemplate | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState("");
  const [selectedEdgeId, setSelectedEdgeId] = useState("");
  const [validation, setValidation] = useState<WorkflowValidationResult | null>(null);
  const [promptPreview, setPromptPreview] = useState<AgentPromptPreview | null>(null);
  const [copyName, setCopyName] = useState(DEFAULT_COPY_NAME);
  const [dragging, setDragging] = useState<DraggingNode | null>(null);
  const [connecting, setConnecting] = useState<ConnectingPort | null>(null);
  const [busy, setBusy] = useState("");
  const canvasRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    void loadWorkflowData();
  }, []);

  async function loadWorkflowData(preferredTemplateId = selectedTemplateId) {
    try {
      setBusy("load");
      const [templateResponse, providerResponse] = await Promise.all([
        listWorkflowTemplates(),
        listWorkflowProviders()
      ]);
      setTemplates(templateResponse.templates);
      setProviders(providerResponse.providers);
      const next =
        templateResponse.templates.find((item) => item.template_id === preferredTemplateId) ||
        templateResponse.templates[0] ||
        null;
      setSelectedTemplateId(next?.template_id || "");
      setDraft(next ? cloneTemplate(next) : null);
      setSelectedNodeId(next ? defaultSelectedNodeId(next) : "");
      setSelectedEdgeId("");
      setValidation(null);
      setPromptPreview(null);
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  }

  const selectedNode = useMemo(
    () => draft?.nodes.find((node) => node.node_id === selectedNodeId) || null,
    [draft, selectedNodeId]
  );
  const selectedEdge = useMemo(
    () => draft?.edges.find((edge) => edge.edge_id === selectedEdgeId) || null,
    [draft, selectedEdgeId]
  );
  const selectedTemplate = templates.find((template) => template.template_id === selectedTemplateId) || null;
  const readOnly = Boolean(draft?.defaults?.read_only);
  const canvasSize = useMemo(() => workflowCanvasSize(draft), [draft]);
  const nodeStats = useMemo(() => workflowNodeStats(draft), [draft]);
  const selectedAgentInputs = useMemo(() => (draft && selectedNode ? workflowInputPreview(draft, selectedNode) : []), [draft, selectedNode]);
  const selectedAgentOutputs = selectedNode ? agentOutputsForNode(selectedNode) : [];

  async function copySelectedTemplate() {
    const sourceId = selectedTemplateId || "default_drawai_dag";
    try {
      setBusy("copy");
      const response = await copyWorkflowTemplate(sourceId, copyName.trim() || DEFAULT_COPY_NAME);
      await loadWorkflowData(response.template.template_id);
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  }

  function createLocalTemplate() {
    const base = templates.find((item) => item.template_id === "default_drawai_dag") || draft;
    if (!base) return;
    const timestamp = Date.now().toString(36);
    const template = cloneTemplate(base);
    template.template_id = `custom_workflow_${timestamp}`;
    template.name = "Untitled Workflow";
    template.defaults = { ...template.defaults, builtin: false, read_only: false, source_template_id: base.template_id };
    setTemplates((current) => [...current.filter((item) => item.template_id !== template.template_id), template]);
    setSelectedTemplateId(template.template_id);
    setDraft(template);
    setSelectedNodeId(defaultSelectedNodeId(template));
    setSelectedEdgeId("");
    setValidation(null);
    setPromptPreview(null);
  }

  async function validateDraft() {
    if (!draft) return;
    try {
      setBusy("validate");
      const response = await validateWorkflowTemplate(draft);
      setValidation(response.validation);
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  }

  async function saveDraft() {
    if (!draft || readOnly) return;
    try {
      setBusy("save");
      const response = await saveWorkflowTemplate(draft);
      setDraft(cloneTemplate(response.template));
      await loadWorkflowData(response.template.template_id);
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  }

  async function renderPromptForNode(node: WorkflowNode) {
    if (!draft || node.node_type !== "agent") return;
    const presetId = String(node.config.preset_id || "");
    if (!presetId) {
      onError("这个 Agent 节点没有 preset_id。");
      return;
    }
    try {
      setBusy("prompt");
      const response = await previewAgentPrompt({
        preset_id: presetId,
        node_config: node.config,
        inputs: workflowInputPreview(draft, node)
      });
      setPromptPreview(response.prompt);
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  }

  function selectTemplate(templateId: string) {
    const template = templates.find((item) => item.template_id === templateId) || null;
    setSelectedTemplateId(template?.template_id || "");
    setDraft(template ? cloneTemplate(template) : null);
    setSelectedNodeId(template ? defaultSelectedNodeId(template) : "");
    setSelectedEdgeId("");
    setValidation(null);
    setPromptPreview(null);
    setConnecting(null);
  }

  function updateDraft(patch: Partial<WorkflowTemplate>) {
    setDraft((current) => (current ? { ...current, ...patch } : current));
  }

  function updateNode(nodeId: string, updater: Partial<WorkflowNode> | ((node: WorkflowNode) => WorkflowNode)) {
    setDraft((current) => {
      if (!current) return current;
      return {
        ...current,
        nodes: current.nodes.map((node) => {
          if (node.node_id !== nodeId) return node;
          return typeof updater === "function" ? updater(node) : { ...node, ...updater };
        })
      };
    });
    setPromptPreview(null);
    setValidation(null);
  }

  function updateSelectedNodeConfig(patch: Record<string, unknown>) {
    if (!selectedNode) return;
    updateNode(selectedNode.node_id, (node) => ({ ...node, config: { ...node.config, ...patch } }));
  }

  function addNode(preset: NodePreset, position?: { x: number; y: number }) {
    if (!draft || readOnly) return;
    const index = nextNodeIndex(draft, preset.node_type);
    const nodeId = uniqueNodeId(draft, preset.key.replace(/[^a-zA-Z0-9_-]/g, "_"));
    const defaultPosition = { x: 100 + (index % 4) * 230, y: 100 + Math.floor(index / 4) * 150 };
    const node: WorkflowNode = {
      node_id: nodeId,
      node_type: preset.node_type,
      title: preset.title,
      description: preset.description,
      inputs: cloneJson(preset.inputs),
      outputs: cloneJson(preset.outputs),
      config: cloneJson(preset.config || {}),
      position: position || defaultPosition
    };
    setDraft({ ...draft, nodes: [...draft.nodes, node] });
    setSelectedNodeId(node.node_id);
    setSelectedEdgeId("");
    setValidation(null);
  }

  function beginLibraryDrag(event: DragEvent<HTMLButtonElement>, preset: NodePreset) {
    if (!draft || readOnly) return;
    event.dataTransfer.effectAllowed = "copy";
    event.dataTransfer.setData("application/x-drawai-node", preset.key);
  }

  function dropLibraryNode(event: DragEvent<HTMLDivElement>) {
    const presetKey = event.dataTransfer.getData("application/x-drawai-node");
    if (!presetKey) return;
    event.preventDefault();
    const preset = NODE_PRESETS.find((item) => item.key === presetKey);
    if (!preset || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    addNode(preset, {
      x: Math.max(0, Math.round(event.clientX - rect.left - NODE_WIDTH / 2)),
      y: Math.max(0, Math.round(event.clientY - rect.top - NODE_HEIGHT / 2))
    });
  }

  function deleteSelectedNode() {
    if (!draft || !selectedNode || readOnly) return;
    const nextNodes = draft.nodes.filter((node) => node.node_id !== selectedNode.node_id);
    setDraft({
      ...draft,
      nodes: nextNodes,
      edges: draft.edges.filter((edge) => edge.source_node_id !== selectedNode.node_id && edge.target_node_id !== selectedNode.node_id)
    });
    setSelectedNodeId(nextNodes[0]?.node_id || "");
    setSelectedEdgeId("");
    setPromptPreview(null);
    setValidation(null);
  }

  function deleteSelectedEdge() {
    if (!draft || !selectedEdge || readOnly) return;
    setDraft({ ...draft, edges: draft.edges.filter((edge) => edge.edge_id !== selectedEdge.edge_id) });
    setSelectedEdgeId("");
    setValidation(null);
  }

  function beginNodeDrag(event: PointerEvent<HTMLElement>, node: WorkflowNode) {
    if (readOnly) return;
    const target = event.target;
    if (target instanceof HTMLElement && target.closest("button, input, select, textarea")) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragging({
      nodeId: node.node_id,
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startX: node.position.x || 0,
      startY: node.position.y || 0
    });
  }

  function moveNode(event: PointerEvent<HTMLElement>) {
    if (!dragging || dragging.pointerId !== event.pointerId) return;
    const nextX = Math.max(0, dragging.startX + event.clientX - dragging.startClientX);
    const nextY = Math.max(0, dragging.startY + event.clientY - dragging.startClientY);
    updateNode(dragging.nodeId, { position: { x: Math.round(nextX), y: Math.round(nextY) } });
  }

  function endNodeDrag(event: PointerEvent<HTMLElement>) {
    if (dragging?.pointerId === event.pointerId) setDragging(null);
  }

  function startConnection(nodeId: string, portId: string) {
    if (readOnly) return;
    setConnecting({ nodeId, portId });
    setSelectedNodeId(nodeId);
    setSelectedEdgeId("");
  }

  function completeConnection(targetNodeId: string, targetPortId: string) {
    if (!draft || !connecting || readOnly) return;
    if (connecting.nodeId === targetNodeId) {
      setConnecting(null);
      return;
    }
    const source = draft.nodes.find((node) => node.node_id === connecting.nodeId);
    const target = draft.nodes.find((node) => node.node_id === targetNodeId);
    const sourcePort = source?.outputs.find((item) => item.port_id === connecting.portId);
    const targetPort = target?.inputs.find((item) => item.port_id === targetPortId);
    if (!source || !target || !sourcePort || !targetPort) return;
    const overlap = compatibleTypes(sourcePort, targetPort);
    if (overlap.length === 0) {
      onError(`不能连接：${source.title}.${sourcePort.label} 和 ${target.title}.${targetPort.label} 没有兼容类型。`);
      setConnecting(null);
      return;
    }
    const edge: WorkflowEdge = {
      edge_id: uniqueEdgeId(draft, `${source.node_id}:${sourcePort.port_id}->${target.node_id}:${targetPort.port_id}`),
      source_node_id: source.node_id,
      source_port_id: sourcePort.port_id,
      target_node_id: target.node_id,
      target_port_id: targetPort.port_id,
      enabled_types: overlap
    };
    setDraft({ ...draft, edges: [...draft.edges, edge] });
    setSelectedEdgeId(edge.edge_id);
    setSelectedNodeId("");
    setConnecting(null);
    setValidation(null);
  }

  function updateAgentInputOverride(input: AgentInputPreview, patch: Record<string, unknown>) {
    if (!selectedNode || selectedNode.node_type !== "agent") return;
    const key = inputOverrideKey(input);
    const overrides = { ...(selectedNode.config.input_overrides as Record<string, Record<string, unknown>> | undefined) };
    overrides[key] = { ...(overrides[key] || {}), ...patch };
    updateSelectedNodeConfig({ input_overrides: overrides });
  }

  function updateAgentOutput(index: number, patch: Partial<AgentOutputConfig>) {
    if (!selectedNode || selectedNode.node_type !== "agent") return;
    const outputs = agentOutputsForNode(selectedNode);
    outputs[index] = { ...outputs[index], ...patch };
    updateNode(selectedNode.node_id, (node) => {
      const outputConfig = outputs.map((item) => ({ ...item }));
      const nextPorts = node.outputs.map((port) => {
        const config = outputConfig.find((item) => item.port_id === port.port_id);
        if (!config) return port;
        return {
          ...port,
          types: [config.type].filter(Boolean),
          formats: [config.format_id].filter(Boolean),
          description: port.description.includes("deliverable") ? `deliverable · ${config.description}` : config.description
        };
      });
      return {
        ...node,
        outputs: nextPorts,
        config: { ...node.config, outputs: outputConfig }
      };
    });
  }

  function addAgentOutput() {
    if (!selectedNode || selectedNode.node_type !== "agent") return;
    const portId = uniquePortId(selectedNode, "output");
    const output: AgentOutputConfig = {
      port_id: portId,
      path: `output/${portId}.json`,
      format_id: "drawai.element_plans.v1",
      type: "element_plans",
      description: "Agent declared output."
    };
    updateNode(selectedNode.node_id, (node) => ({
      ...node,
      outputs: [...node.outputs, port(portId, portId, [output.type], output.format_id, false)],
      config: { ...node.config, outputs: [...agentOutputsForNode(node), output] }
    }));
  }

  function removeAgentOutput(index: number) {
    if (!draft || !selectedNode || selectedNode.node_type !== "agent" || readOnly) return;
    const outputs = agentOutputsForNode(selectedNode);
    const removed = outputs[index];
    const nextOutputs = outputs.filter((_item, itemIndex) => itemIndex !== index);
    updateNode(selectedNode.node_id, (node) => ({
      ...node,
      outputs: node.outputs.filter((port) => port.port_id !== removed.port_id),
      config: { ...node.config, outputs: nextOutputs }
    }));
    setDraft((current) =>
      current
        ? {
            ...current,
            edges: current.edges.filter((edge) => !(edge.source_node_id === selectedNode.node_id && edge.source_port_id === removed.port_id))
          }
        : current
    );
  }

  return (
    <main className="workflow-workspace">
      <header className="workflow-topbar">
        <div className="workflow-topbar-main">
          <label className="workflow-inline-field">
            <span>Template</span>
            <select value={selectedTemplateId} onChange={(event) => selectTemplate(event.target.value)}>
              {templates.map((template) => (
                <option value={template.template_id} key={template.template_id}>
                  {template.name}
                </option>
              ))}
            </select>
          </label>
          <label className="workflow-copy-inline">
            <span>Copy name</span>
            <input value={copyName} onChange={(event) => setCopyName(event.target.value)} />
          </label>
          <button type="button" disabled={busy === "copy"} onClick={() => void copySelectedTemplate()}>
            复制内置
          </button>
          <button type="button" onClick={createLocalTemplate}>
            新建
          </button>
          <button type="button" disabled={!draft || busy === "validate"} onClick={() => void validateDraft()}>
            校验
          </button>
          <button type="button" className="primary" disabled={!draft || readOnly || busy === "save"} onClick={() => void saveDraft()}>
            保存
          </button>
        </div>
        <div className="workflow-topbar-status">
          {selectedTemplate && <span>{selectedTemplate.template_id}</span>}
          <strong>{readOnly ? "内置只读" : "可编辑"}</strong>
          {validation && <em className={validation.ok ? "ok" : "failed"}>{validation.ok ? "校验通过" : `${validation.errors.length} 个问题`}</em>}
        </div>
      </header>

      <aside className="workflow-sidebar">
        <div className="workflow-panel-head">
          <span>Node Library</span>
          <strong>拖入或点击添加</strong>
        </div>
        <div className="workflow-node-library">
          {NODE_PRESETS.map((preset) => (
            <button
              type="button"
              key={preset.key}
              className={`workflow-tool node-${preset.node_type}`}
              disabled={!draft || readOnly}
              draggable={Boolean(draft) && !readOnly}
              title={preset.description}
              onClick={() => addNode(preset)}
              onDragStart={(event) => beginLibraryDrag(event, preset)}
            >
              <span>{preset.icon}</span>
              <strong>{preset.title}</strong>
              <em>{preset.node_type}</em>
            </button>
          ))}
        </div>
        <div className="workflow-stats" aria-label="节点类型">
          <span>Parser <strong>{nodeStats.parser}</strong></span>
          <span>Agent <strong>{nodeStats.agent}</strong></span>
          <span>Human <strong>{nodeStats.human_review}</strong></span>
          <span>Export <strong>{nodeStats.export}</strong></span>
        </div>
        {validation && !validation.ok && (
          <div className="workflow-validation failed">
            <strong>{validation.errors.length} 个校验问题</strong>
            {validation.errors.slice(0, 6).map((item, index) => (
              <button
                type="button"
                key={`${item.code}-${item.node_id}-${item.edge_id}-${index}`}
                onClick={() => {
                  if (item.node_id) setSelectedNodeId(item.node_id);
                  if (item.edge_id) setSelectedEdgeId(item.edge_id);
                }}
              >
                <span>{item.code}</span>
                <em>{item.node_id || item.edge_id}</em>
              </button>
            ))}
          </div>
        )}
      </aside>

      <section className="workflow-canvas-shell">
        <div className="workflow-canvas-scroll">
          <div
            ref={canvasRef}
            className="workflow-canvas"
            style={{ width: canvasSize.width, height: canvasSize.height }}
            onDragOver={(event) => {
              if (event.dataTransfer.types.includes("application/x-drawai-node")) {
                event.preventDefault();
                event.dataTransfer.dropEffect = "copy";
              }
            }}
            onDrop={dropLibraryNode}
          >
            {draft && (
              <WorkflowEdges
                template={draft}
                selectedEdgeId={selectedEdgeId}
                onSelectEdge={(edgeId) => {
                  setSelectedEdgeId(edgeId);
                  setSelectedNodeId("");
                }}
              />
            )}
            {draft?.nodes.map((node) => (
              <article
                key={node.node_id}
                className={`workflow-node node-${node.node_type} ${node.node_id === selectedNodeId ? "active" : ""}`}
                style={{ left: node.position.x || 0, top: node.position.y || 0 }}
                onClick={() => {
                  setSelectedNodeId(node.node_id);
                  setSelectedEdgeId("");
                  setPromptPreview(null);
                }}
                onPointerDown={(event) => beginNodeDrag(event, node)}
                onPointerMove={moveNode}
                onPointerUp={endNodeDrag}
                onPointerCancel={endNodeDrag}
              >
                <div className="workflow-node-head">
                  <span className="workflow-node-icon">{nodeIcon(node)}</span>
                  <div>
                    <em>{node.node_type}</em>
                    <strong>{node.title}</strong>
                  </div>
                </div>
                <div className="workflow-node-port-row inputs">
                  {node.inputs.map((input) => (
                    <button
                      type="button"
                      key={input.port_id}
                      disabled={!connecting}
                      className={connecting && compatibleTarget(draft, connecting, node, input) ? "compatible" : ""}
                      title={`${input.label}: ${input.types.join(" / ")}`}
                      onClick={(event) => {
                        event.stopPropagation();
                        completeConnection(node.node_id, input.port_id);
                      }}
                    >
                      {input.port_id}
                    </button>
                  ))}
                </div>
                <p>{nodeOutputSummary(node)}</p>
                <div className="workflow-node-port-row outputs">
                  {node.outputs.map((output) => (
                    <button
                      type="button"
                      key={output.port_id}
                      className={connecting?.nodeId === node.node_id && connecting.portId === output.port_id ? "connecting" : ""}
                      title={`${output.label}: ${output.types.join(" / ")}`}
                      onClick={(event) => {
                        event.stopPropagation();
                        startConnection(node.node_id, output.port_id);
                      }}
                    >
                      {output.port_id}
                    </button>
                  ))}
                </div>
              </article>
            ))}
            {connecting && (
              <button type="button" className="workflow-connect-cancel" onClick={() => setConnecting(null)}>
                取消连线
              </button>
            )}
          </div>
        </div>
      </section>

      <aside className="workflow-inspector">
        {selectedNode ? (
          <>
            <div className="workflow-panel-head">
              <span>{selectedNode.node_type}</span>
              <strong>{selectedNode.title}</strong>
            </div>
            <label className="workflow-field">
              <span>Title</span>
              <input
                value={selectedNode.title}
                disabled={readOnly}
                onChange={(event) => updateNode(selectedNode.node_id, { title: event.target.value })}
              />
            </label>
            <label className="workflow-field">
              <span>Description</span>
              <textarea
                value={selectedNode.description || ""}
                disabled={readOnly}
                rows={2}
                onChange={(event) => updateNode(selectedNode.node_id, { description: event.target.value })}
              />
            </label>

            {selectedNode.node_type === "agent" && (
              <div className="workflow-agent-editor">
                <label className="workflow-field">
                  <span>Provider</span>
                  <select
                    value={String(selectedNode.config.provider_id || "")}
                    disabled={readOnly}
                    onChange={(event) => updateSelectedNodeConfig({ provider_id: event.target.value })}
                  >
                    {providers.map((provider) => (
                      <option value={provider.provider_id} key={provider.provider_id}>
                        {provider.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="workflow-field">
                  <span>Preset</span>
                  <select
                    value={String(selectedNode.config.preset_id || "run0_element_refine")}
                    disabled={readOnly}
                    onChange={(event) => updateSelectedNodeConfig({ preset_id: event.target.value })}
                  >
                    <option value="run0_element_refine">Run0 Element Refinement</option>
                    <option value="svg_generation">SVG Generation</option>
                  </select>
                </label>

                <div className="workflow-inspector-section">
                  <div className="workflow-section-title">
                    <span>Input files</span>
                    <strong>{selectedAgentInputs.length}</strong>
                  </div>
                  {selectedAgentInputs.map((input) => {
                    const override = inputOverrideFor(selectedNode, input);
                    const included = override.include !== false;
                    return (
                      <div className="workflow-agent-input" key={inputOverrideKey(input)}>
                        <label>
                          <input
                            type="checkbox"
                            checked={included}
                            disabled={readOnly}
                            onChange={(event) => updateAgentInputOverride(input, { include: event.target.checked })}
                          />
                          <strong>{String(input.source_node_id)}.{String(input.source_port_id)}</strong>
                        </label>
                        <code>{String(input.path)}</code>
                        <textarea
                          rows={2}
                          disabled={readOnly || !included}
                          value={String(override.description ?? input.description ?? "")}
                          onChange={(event) => updateAgentInputOverride(input, { description: event.target.value })}
                        />
                      </div>
                    );
                  })}
                  {selectedAgentInputs.length === 0 && <p className="workflow-muted">还没有连接输入。</p>}
                </div>

                <div className="workflow-inspector-section">
                  <div className="workflow-section-title">
                    <span>Output declarations</span>
                    <button type="button" disabled={readOnly} onClick={addAgentOutput}>添加</button>
                  </div>
                  {selectedAgentOutputs.map((output, index) => (
                    <div className="workflow-agent-output" key={`${output.port_id}-${index}`}>
                      <div className="workflow-output-grid">
                        <label>
                          <span>Port</span>
                          <input value={output.port_id} disabled={readOnly} onChange={(event) => updateAgentOutput(index, { port_id: event.target.value })} />
                        </label>
                        <label>
                          <span>Type</span>
                          <input value={output.type} disabled={readOnly} onChange={(event) => updateAgentOutput(index, { type: event.target.value })} />
                        </label>
                        <label>
                          <span>Format</span>
                          <input value={output.format_id} disabled={readOnly} onChange={(event) => updateAgentOutput(index, { format_id: event.target.value })} />
                        </label>
                        <label>
                          <span>Path</span>
                          <input value={output.path} disabled={readOnly} onChange={(event) => updateAgentOutput(index, { path: event.target.value })} />
                        </label>
                      </div>
                      <textarea
                        rows={2}
                        disabled={readOnly}
                        value={output.description}
                        onChange={(event) => updateAgentOutput(index, { description: event.target.value })}
                      />
                      <button type="button" disabled={readOnly || selectedAgentOutputs.length <= 1} onClick={() => removeAgentOutput(index)}>
                        删除输出
                      </button>
                    </div>
                  ))}
                </div>

                <label className="workflow-field">
                  <span>Task prompt</span>
                  <textarea
                    rows={5}
                    disabled={readOnly}
                    value={promptFragmentText(selectedNode)}
                    onChange={(event) => updateSelectedNodeConfig({ prompt_fragments: event.target.value })}
                  />
                </label>
                <button type="button" disabled={busy === "prompt"} onClick={() => void renderPromptForNode(selectedNode)}>
                  预览最终 Prompt
                </button>
              </div>
            )}

            {selectedNode.node_type === "human_review" && (
              <div className="workflow-inspector-section">
                <div className="workflow-section-title">
                  <span>Human review surface</span>
                </div>
                <label className="workflow-field">
                  <span>Surface</span>
                  <select
                    value={String(selectedNode.config.review_surface || "assets")}
                    disabled={readOnly}
                    onChange={(event) => updateSelectedNodeConfig({ review_surface: event.target.value })}
                  >
                    <option value="assets">Assets canvas/table</option>
                    <option value="output">Output visualization</option>
                  </select>
                </label>
                <label className="workflow-field">
                  <span>Result path</span>
                  <input
                    value={String(selectedNode.config.result_path || "")}
                    disabled={readOnly}
                    onChange={(event) => updateSelectedNodeConfig({ result_path: event.target.value })}
                  />
                </label>
              </div>
            )}

            <div className="workflow-inspector-section">
              <div className="workflow-section-title">
                <span>Ports</span>
              </div>
              {[...selectedNode.inputs, ...selectedNode.outputs].map((portItem) => (
                <div className="workflow-port-row" key={`${portItem.port_id}-${portItem.required ? "in" : "out"}`}>
                  <span>{portItem.port_id}</span>
                  <em>{portItem.types.join(" / ") || "control"}</em>
                </div>
              ))}
            </div>
            <div className="workflow-node-actions">
              <button type="button" className="danger" disabled={readOnly} onClick={deleteSelectedNode}>
                删除节点
              </button>
            </div>
            {promptPreview && (
              <div className="workflow-prompt-preview">
                <div>
                  <span>{promptPreview.provider_id}</span>
                  <strong>{promptPreview.preset_id}</strong>
                </div>
                <pre>{promptPreview.text}</pre>
              </div>
            )}
          </>
        ) : selectedEdge ? (
          <div className="workflow-edge-inspector">
            <div className="workflow-panel-head">
              <span>Edge</span>
              <strong>{selectedEdge.edge_id}</strong>
            </div>
            <dl className="workflow-node-meta">
              <div><dt>Source</dt><dd>{selectedEdge.source_node_id}.{selectedEdge.source_port_id}</dd></div>
              <div><dt>Target</dt><dd>{selectedEdge.target_node_id}.{selectedEdge.target_port_id}</dd></div>
              <div><dt>Types</dt><dd>{selectedEdge.enabled_types.join(" / ") || "auto"}</dd></div>
            </dl>
            <button type="button" className="danger" disabled={readOnly} onClick={deleteSelectedEdge}>
              删除连线
            </button>
          </div>
        ) : (
          <div className="workflow-empty">选择节点或连线</div>
        )}
      </aside>
    </main>
  );
}

function WorkflowEdges({
  template,
  selectedEdgeId,
  onSelectEdge
}: {
  template: WorkflowTemplate;
  selectedEdgeId: string;
  onSelectEdge: (edgeId: string) => void;
}) {
  const nodeById = new Map(template.nodes.map((node) => [node.node_id, node]));
  return (
    <svg className="workflow-edges" aria-hidden="true">
      {template.edges.map((edge) => {
        const source = nodeById.get(edge.source_node_id);
        const target = nodeById.get(edge.target_node_id);
        if (!source || !target) return null;
        const start = {
          x: (source.position.x || 0) + NODE_WIDTH,
          y: (source.position.y || 0) + NODE_HEIGHT / 2
        };
        const end = {
          x: target.position.x || 0,
          y: (target.position.y || 0) + NODE_HEIGHT / 2
        };
        const mid = Math.max(44, Math.abs(end.x - start.x) * 0.42);
        const d = `M ${start.x} ${start.y} C ${start.x + mid} ${start.y}, ${end.x - mid} ${end.y}, ${end.x} ${end.y}`;
        return (
          <path
            key={edge.edge_id}
            className={edge.edge_id === selectedEdgeId ? "selected" : ""}
            d={d}
            onClick={(event) => {
              event.stopPropagation();
              onSelectEdge(edge.edge_id);
            }}
          />
        );
      })}
    </svg>
  );
}

function workflowInputPreview(template: WorkflowTemplate, node: WorkflowNode): Array<Record<string, unknown>> {
  return template.edges
    .filter((edge) => edge.target_node_id === node.node_id)
    .map((edge) => {
      const source = template.nodes.find((item) => item.node_id === edge.source_node_id);
      const sourcePort = source?.outputs.find((portItem) => portItem.port_id === edge.source_port_id);
      const formatId = sourcePort?.formats[0] || "";
      return {
        path: `nodes/${edge.source_node_id}/runs/latest/output/${edge.source_port_id}.${fileExtensionForFormat(formatId)}`,
        format_id: formatId,
        type: sourcePort?.types[0] || "",
        source_node_id: edge.source_node_id,
        source_port_id: edge.source_port_id,
        description: sourcePort?.description || `${source?.title || edge.source_node_id} output`
      };
    });
}

function workflowCanvasSize(template: WorkflowTemplate | null): { width: number; height: number } {
  if (!template) return { width: 1200, height: 640 };
  const maxX = Math.max(...template.nodes.map((node) => node.position.x || 0), 900);
  const maxY = Math.max(...template.nodes.map((node) => node.position.y || 0), 480);
  return { width: maxX + NODE_WIDTH + 240, height: maxY + NODE_HEIGHT + 160 };
}

function workflowNodeStats(template: WorkflowTemplate | null): Record<string, number> {
  const stats: Record<string, number> = { parser: 0, agent: 0, processor: 0, export: 0, human_review: 0 };
  template?.nodes.forEach((node) => {
    if (node.node_type in stats) stats[node.node_type] += 1;
  });
  return stats;
}

function defaultSelectedNodeId(template: WorkflowTemplate): string {
  return template.nodes.find((node) => node.node_type === "agent")?.node_id || template.nodes[0]?.node_id || "";
}

function nodeOutputSummary(node: WorkflowNode): string {
  const formats = node.outputs.flatMap((item) => item.formats);
  if (formats.length > 0) return formats.join(" · ");
  return node.outputs.map((item) => item.types.join("/")).join(" · ") || "control";
}

function nodeIcon(node: WorkflowNode): string {
  if (node.node_type === "human_review") return "H";
  if (node.node_type === "fusion") return "M";
  return (node.node_type[0] || "N").toUpperCase();
}

function port(
  port_id: string,
  label: string,
  types: string[],
  format = "",
  required = true,
  cardinality: "single" | "many" = "single",
  description = ""
): WorkflowPort {
  return {
    port_id,
    label,
    types,
    required,
    cardinality,
    formats: format ? [format] : [],
    description
  };
}

function compatibleTypes(sourcePort: WorkflowPort, targetPort: WorkflowPort): string[] {
  const targetTypes = new Set(targetPort.types);
  return sourcePort.types.filter((item) => targetTypes.has(item));
}

function compatibleTarget(template: WorkflowTemplate | null, connecting: ConnectingPort, targetNode: WorkflowNode, targetPort: WorkflowPort): boolean {
  const source = template?.nodes.find((node) => node.node_id === connecting.nodeId);
  const sourcePort = source?.outputs.find((item) => item.port_id === connecting.portId);
  return Boolean(sourcePort && source?.node_id !== targetNode.node_id && compatibleTypes(sourcePort, targetPort).length > 0);
}

function uniqueNodeId(template: WorkflowTemplate, base: string): string {
  const existing = new Set(template.nodes.map((node) => node.node_id));
  let candidate = base;
  let index = 2;
  while (existing.has(candidate)) {
    candidate = `${base}_${index}`;
    index += 1;
  }
  return candidate;
}

function uniqueEdgeId(template: WorkflowTemplate, base: string): string {
  const existing = new Set(template.edges.map((edge) => edge.edge_id));
  let candidate = base;
  let index = 2;
  while (existing.has(candidate)) {
    candidate = `${base}#${index}`;
    index += 1;
  }
  return candidate;
}

function uniquePortId(node: WorkflowNode, base: string): string {
  const existing = new Set(node.outputs.map((item) => item.port_id));
  let candidate = base;
  let index = 2;
  while (existing.has(candidate)) {
    candidate = `${base}_${index}`;
    index += 1;
  }
  return candidate;
}

function nextNodeIndex(template: WorkflowTemplate, nodeType: string): number {
  return template.nodes.filter((node) => node.node_type === nodeType).length + 1;
}

function agentOutputsForNode(node: WorkflowNode): AgentOutputConfig[] {
  const raw = node.config.outputs || node.config.output_declarations;
  if (Array.isArray(raw)) {
    return raw.filter(isAgentOutputConfig).map((item) => ({ ...item }));
  }
  return node.outputs.map((output) => ({
    port_id: output.port_id,
    path: defaultOutputPath(output),
    format_id: output.formats[0] || "",
    type: output.types[0] || "",
    description: output.description || `${output.label} output`
  }));
}

function isAgentOutputConfig(value: unknown): value is AgentOutputConfig {
  if (!value || typeof value !== "object") return false;
  const item = value as Record<string, unknown>;
  return ["port_id", "path", "format_id", "type", "description"].every((key) => typeof item[key] === "string");
}

function defaultOutputPath(output: WorkflowPort): string {
  const extension = fileExtensionForFormat(output.formats[0] || "");
  return `output/${output.port_id}.${extension}`;
}

function fileExtensionForFormat(formatId: string): string {
  if (formatId.includes("svg")) return "svg";
  if (formatId.includes("pptx")) return "pptx";
  if (formatId.includes("image")) return "png";
  return "json";
}

function promptFragmentText(node: WorkflowNode): string {
  const raw = node.config.prompt_fragments ?? node.config.user_prompt ?? "";
  if (Array.isArray(raw)) return raw.filter((item) => typeof item === "string").join("\n\n");
  return typeof raw === "string" ? raw : "";
}

function inputOverrideKey(input: AgentInputPreview): string {
  return `${String(input.source_node_id || "")}.${String(input.source_port_id || "")}`;
}

function inputOverrideFor(node: WorkflowNode, input: AgentInputPreview): Record<string, unknown> {
  const raw = node.config.input_overrides;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return {};
  const overrides = raw as Record<string, Record<string, unknown>>;
  return overrides[inputOverrideKey(input)] || overrides[String(input.path || "")] || {};
}

function cloneTemplate(template: WorkflowTemplate): WorkflowTemplate {
  return cloneJson(template);
}

function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}
