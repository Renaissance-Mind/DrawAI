import { PointerEvent, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
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
import { WorkflowNodeIcon } from "./workflowNodeIcons";

type DraggingNode = {
  nodeId: string;
  pointerId: number;
  startClientX: number;
  startClientY: number;
  startX: number;
  startY: number;
};

type CanvasViewport = {
  x: number;
  y: number;
  zoom: number;
};

type CanvasPanState = {
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

type HandleDragState = {
  nodeId: string;
  portId: string;
  pointerId: number;
  startClientX: number;
  startClientY: number;
  start: { x: number; y: number };
  current: { x: number; y: number };
  active: boolean;
};

type NodePickerState = {
  sourceNodeId: string;
  sourcePortId: string;
  insertEdgeId?: string;
  targetNodeId?: string;
  targetPortId?: string;
  x: number;
  y: number;
  query: string;
};

type WorkflowViewMode = "library" | "canvas";

type WorkflowFolder = {
  folder_id: string;
  name: string;
  builtin?: boolean;
};

type WorkflowFolderWithCount = WorkflowFolder & {
  count: number;
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

const NODE_WIDTH = 236;
const NODE_HEIGHT = 72;
const DEFAULT_VIEWPORT: CanvasViewport = { x: 88, y: 74, zoom: 0.84 };
const MIN_ZOOM = 0.5;
const MAX_ZOOM = 1.25;
const DEFAULT_COPY_NAME = "Custom DrawAI DAG";
const BUILTIN_WORKFLOW_FOLDER_ID = "builtin";
const CUSTOM_WORKFLOW_FOLDER_ID = "custom";
const WORKFLOW_FOLDERS_STORAGE_KEY = "drawai.workflow.folders";
const DEFAULT_WORKFLOW_FOLDERS: WorkflowFolder[] = [
  { folder_id: BUILTIN_WORKFLOW_FOLDER_ID, name: "默认分类", builtin: true },
  { folder_id: CUSTOM_WORKFLOW_FOLDER_ID, name: "自定义工作流" }
];

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
  const [workflowView, setWorkflowView] = useState<WorkflowViewMode>("library");
  const [workflowFolders, setWorkflowFolders] = useState<WorkflowFolder[]>(() => loadWorkflowFolders());
  const [activeWorkflowFolderId, setActiveWorkflowFolderId] = useState(BUILTIN_WORKFLOW_FOLDER_ID);
  const [newFolderName, setNewFolderName] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [draft, setDraft] = useState<WorkflowTemplate | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState("");
  const [selectedEdgeId, setSelectedEdgeId] = useState("");
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [validation, setValidation] = useState<WorkflowValidationResult | null>(null);
  const [promptPreview, setPromptPreview] = useState<AgentPromptPreview | null>(null);
  const [dragging, setDragging] = useState<DraggingNode | null>(null);
  const [canvasPan, setCanvasPan] = useState<CanvasPanState | null>(null);
  const [viewport, setViewport] = useState<CanvasViewport>(DEFAULT_VIEWPORT);
  const [connecting, setConnecting] = useState<ConnectingPort | null>(null);
  const [handleDrag, setHandleDrag] = useState<HandleDragState | null>(null);
  const [nodePicker, setNodePicker] = useState<NodePickerState | null>(null);
  const [busy, setBusy] = useState("");
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    void loadWorkflowData();
  }, []);

  useEffect(() => {
    saveWorkflowFolders(workflowFolders);
  }, [workflowFolders]);

  useEffect(() => {
    if (workflowView !== "canvas") return;
    const viewportElement = viewportRef.current;
    if (!viewportElement) return;
    const handleWheel = (event: globalThis.WheelEvent) => handleCanvasWheel(event);
    viewportElement.addEventListener("wheel", handleWheel, { passive: false });
    return () => viewportElement.removeEventListener("wheel", handleWheel);
  }, [workflowView, draft?.template_id]);

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
      setNodePicker(null);
      setHandleDrag(null);
      setConnecting(null);
      setInspectorOpen(false);
      setViewport(DEFAULT_VIEWPORT);
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
  const canvasHasInspector = Boolean(inspectorOpen && (selectedNode || selectedEdge));
  const canvasSize = useMemo(() => workflowCanvasSize(draft), [draft]);
  const nodeStats = useMemo(() => workflowNodeStats(draft), [draft]);
  const selectedAgentInputs = useMemo(() => (draft && selectedNode ? workflowInputPreview(draft, selectedNode) : []), [draft, selectedNode]);
  const selectedAgentOutputs = selectedNode ? agentOutputsForNode(selectedNode) : [];
  const pickerItems = useMemo(() => (draft && nodePicker ? nodePickerItems(draft, nodePicker) : []), [draft, nodePicker]);
  const minimapNodes = useMemo(() => (draft ? workflowMinimapNodes(draft) : []), [draft]);
  const visibleWorkflowFolders = useMemo(() => workflowFoldersWithCounts(workflowFolders, templates), [workflowFolders, templates]);
  const activeWorkflowFolder = visibleWorkflowFolders.find((folder) => folder.folder_id === activeWorkflowFolderId) || visibleWorkflowFolders[0];
  const libraryTemplates = useMemo(
    () => templates.filter((template) => workflowFolderIdForTemplate(template) === activeWorkflowFolder.folder_id),
    [templates, activeWorkflowFolder.folder_id]
  );
  const topbarTarget = typeof document !== "undefined" ? document.getElementById("drawai-view-controls") : null;
  const topbarPortal =
    topbarTarget && workflowView === "canvas"
      ? createPortal(
          <div className="editor-banner-controls workflow-banner-controls">
            <button type="button" className="home-button workflow-home-button" title="返回工作流" aria-label="返回工作流" onClick={returnToWorkflowLibrary}>
              ←
            </button>
            <div className="editor-title">
              <strong>{selectedTemplate?.name || draft?.name || "Workflow"}</strong>
              <span>{readOnly ? "内置只读" : "可编辑"} · {selectedTemplate?.template_id || draft?.template_id || "draft"}</span>
            </div>
            <div className="toolbar-note workflow-validation-note">
              {validation ? (
                <em className={validation.ok ? "ok" : "failed"}>{validation.ok ? "校验通过" : `${validation.errors.length} 个问题`}</em>
              ) : (
                <em>未校验</em>
              )}
            </div>
            <div className="editor-actions">
              <button type="button" disabled={!draft || busy === "validate"} onClick={() => void validateDraft()}>
                校验
              </button>
              <button type="button" className="primary" disabled={!draft || readOnly || busy === "save"} onClick={() => void saveDraft()}>
                保存
              </button>
              {(selectedNode || selectedEdge) && (
                <button type="button" onClick={() => setInspectorOpen((current) => !current)}>
                  {canvasHasInspector ? "收起详情" : "详情"}
                </button>
              )}
            </div>
          </div>,
          topbarTarget
        )
      : null;

  async function copySelectedTemplate(sourceId = selectedTemplateId || "default_drawai_dag", preferredName = "") {
    const source = templates.find((item) => item.template_id === sourceId) || null;
    const targetName = preferredName.trim() || copiedWorkflowName(source?.name || DEFAULT_COPY_NAME);
    try {
      setBusy("copy");
      const response = await copyWorkflowTemplate(sourceId, targetName);
      const folderId = activeWorkflowFolderId === BUILTIN_WORKFLOW_FOLDER_ID ? CUSTOM_WORKFLOW_FOLDER_ID : activeWorkflowFolderId;
      const template = {
        ...response.template,
        defaults: { ...response.template.defaults, folder_id: folderId }
      };
      await saveWorkflowTemplate(template);
      setTemplates((current) => [...current.filter((item) => item.template_id !== template.template_id), template]);
      setActiveWorkflowFolderId(folderId);
      setWorkflowView("canvas");
      setInspectorOpen(false);
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
    const folderId = activeWorkflowFolderId === BUILTIN_WORKFLOW_FOLDER_ID ? CUSTOM_WORKFLOW_FOLDER_ID : activeWorkflowFolderId;
    const template = cloneTemplate(base);
    template.template_id = `custom_workflow_${timestamp}`;
    template.name = "Untitled Workflow";
    template.defaults = { ...template.defaults, builtin: false, read_only: false, source_template_id: base.template_id, folder_id: folderId };
    setTemplates((current) => [...current.filter((item) => item.template_id !== template.template_id), template]);
    setActiveWorkflowFolderId(folderId);
    setSelectedTemplateId(template.template_id);
    setDraft(template);
    setSelectedNodeId(defaultSelectedNodeId(template));
    setSelectedEdgeId("");
    setValidation(null);
    setPromptPreview(null);
    setNodePicker(null);
    setHandleDrag(null);
    setConnecting(null);
    setInspectorOpen(false);
    setWorkflowView("canvas");
    setViewport(DEFAULT_VIEWPORT);
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
    setNodePicker(null);
    setHandleDrag(null);
    setInspectorOpen(false);
    setViewport(DEFAULT_VIEWPORT);
  }

  function openWorkflowCanvas(templateId: string) {
    selectTemplate(templateId);
    setWorkflowView("canvas");
  }

  function returnToWorkflowLibrary() {
    setWorkflowView("library");
    setSelectedNodeId("");
    setSelectedEdgeId("");
    setNodePicker(null);
    setConnecting(null);
    setHandleDrag(null);
    setInspectorOpen(false);
  }

  function addWorkflowFolder() {
    const name = newFolderName.trim();
    if (!name) return;
    const folder: WorkflowFolder = {
      folder_id: uniqueWorkflowFolderId(workflowFolders, name),
      name
    };
    setWorkflowFolders((current) => [...current, folder]);
    setActiveWorkflowFolderId(folder.folder_id);
    setNewFolderName("");
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

  function arrangeNodes() {
    if (!draft || readOnly) return;
    const arranged = arrangeWorkflowNodes(draft);
    setDraft({ ...draft, nodes: arranged });
    setValidation(null);
    setViewport(DEFAULT_VIEWPORT);
  }

  function beginCanvasPan(event: PointerEvent<HTMLDivElement>) {
    const target = event.target;
    if (
      target instanceof HTMLElement &&
      target.closest(".workflow-node, .workflow-node-picker, .workflow-floating-validation, .workflow-zoom-control, .workflow-minimap, button, input, select, textarea")
    ) {
      return;
    }
    event.currentTarget.setPointerCapture(event.pointerId);
    setCanvasPan({
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startX: viewport.x,
      startY: viewport.y
    });
  }

  function moveCanvasPan(event: PointerEvent<HTMLDivElement>) {
    if (!canvasPan || canvasPan.pointerId !== event.pointerId) return;
    setViewport((current) => ({
      ...current,
      x: Math.round(canvasPan.startX + event.clientX - canvasPan.startClientX),
      y: Math.round(canvasPan.startY + event.clientY - canvasPan.startClientY)
    }));
  }

  function endCanvasPan(event: PointerEvent<HTMLDivElement>) {
    if (canvasPan?.pointerId === event.pointerId) setCanvasPan(null);
  }

  function handleCanvasWheel(event: globalThis.WheelEvent) {
    event.preventDefault();
    const delta = normalizedWheelDelta(event);
    if (event.ctrlKey || event.metaKey) {
      zoomCanvasByFactor(Math.exp(-delta.y * 0.002), event.clientX, event.clientY);
      return;
    }
    panCanvasByWheel(delta.x, delta.y);
  }

  function setZoomAroundPoint(nextZoomValue: number, clientX?: number, clientY?: number) {
    const rect = viewportRef.current?.getBoundingClientRect();
    setViewport((current) => {
      const nextZoom = clamp(nextZoomValue, MIN_ZOOM, MAX_ZOOM);
      if (!rect) return { ...current, zoom: nextZoom };
      const anchorX = clientX ?? rect.left + rect.width / 2;
      const anchorY = clientY ?? rect.top + rect.height / 2;
      const canvasX = (anchorX - rect.left - current.x) / current.zoom;
      const canvasY = (anchorY - rect.top - current.y) / current.zoom;
      return {
        x: Math.round(anchorX - rect.left - canvasX * nextZoom),
        y: Math.round(anchorY - rect.top - canvasY * nextZoom),
        zoom: nextZoom
      };
    });
  }

  function zoomCanvasByFactor(factor: number, clientX: number, clientY: number) {
    const rect = viewportRef.current?.getBoundingClientRect();
    setViewport((current) => {
      const nextZoom = clamp(current.zoom * factor, MIN_ZOOM, MAX_ZOOM);
      if (!rect) return { ...current, zoom: nextZoom };
      const canvasX = (clientX - rect.left - current.x) / current.zoom;
      const canvasY = (clientY - rect.top - current.y) / current.zoom;
      return {
        x: Math.round(clientX - rect.left - canvasX * nextZoom),
        y: Math.round(clientY - rect.top - canvasY * nextZoom),
        zoom: nextZoom
      };
    });
  }

  function panCanvasByWheel(deltaX: number, deltaY: number) {
    setViewport((current) => ({
      ...current,
      x: Math.round(current.x - deltaX),
      y: Math.round(current.y - deltaY)
    }));
  }

  function zoomCanvas(delta: number) {
    setZoomAroundPoint(viewport.zoom + delta);
  }

  function fitWorkflowToView() {
    if (!draft) return;
    const rect = viewportRef.current?.getBoundingClientRect();
    if (!rect) return;
    const bounds = workflowBounds(draft);
    const nextZoom = clamp(Math.min((rect.width - 220) / bounds.width, (rect.height - 130) / bounds.height, 1), MIN_ZOOM, MAX_ZOOM);
    setViewport({
      x: Math.round(rect.width / 2 - (bounds.x + bounds.width / 2) * nextZoom),
      y: Math.round(rect.height / 2 - (bounds.y + bounds.height / 2) * nextZoom),
      zoom: nextZoom
    });
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
    const nextX = Math.max(0, dragging.startX + (event.clientX - dragging.startClientX) / viewport.zoom);
    const nextY = Math.max(0, dragging.startY + (event.clientY - dragging.startClientY) / viewport.zoom);
    updateNode(dragging.nodeId, { position: { x: Math.round(nextX), y: Math.round(nextY) } });
  }

  function endNodeDrag(event: PointerEvent<HTMLElement>) {
    if (dragging?.pointerId === event.pointerId) setDragging(null);
  }

  function canvasPointFromClient(clientX: number, clientY: number): { x: number; y: number } {
    const rect = viewportRef.current?.getBoundingClientRect();
    if (!rect) return { x: clientX, y: clientY };
    return {
      x: Math.round((clientX - rect.left - viewport.x) / viewport.zoom),
      y: Math.round((clientY - rect.top - viewport.y) / viewport.zoom)
    };
  }

  function outputAnchorFor(node: WorkflowNode): { x: number; y: number } {
    return {
      x: (node.position.x || 0) + NODE_WIDTH,
      y: (node.position.y || 0) + NODE_HEIGHT / 2
    };
  }

  function openNodePicker(sourceNodeId: string, sourcePortId: string, point?: { x: number; y: number }) {
    if (!draft || readOnly) return;
    const source = draft.nodes.find((node) => node.node_id === sourceNodeId);
    if (!source) return;
    const anchor = point || outputAnchorFor(source);
    setNodePicker({
      sourceNodeId,
      sourcePortId,
      x: Math.max(0, Math.min(canvasSize.width - 236, Math.round(anchor.x + 18))),
      y: Math.max(0, Math.min(canvasSize.height - 420, Math.round(anchor.y - 36))),
      query: ""
    });
    setConnecting({ nodeId: sourceNodeId, portId: sourcePortId });
    setSelectedNodeId(sourceNodeId);
    setSelectedEdgeId("");
  }

  function openEdgePicker(edgeId: string, point: { x: number; y: number }) {
    if (!draft || readOnly) return;
    const edge = draft.edges.find((item) => item.edge_id === edgeId);
    if (!edge) return;
    setNodePicker({
      sourceNodeId: edge.source_node_id,
      sourcePortId: edge.source_port_id,
      targetNodeId: edge.target_node_id,
      targetPortId: edge.target_port_id,
      insertEdgeId: edge.edge_id,
      x: Math.max(0, Math.min(canvasSize.width - 236, Math.round(point.x - 118))),
      y: Math.max(0, Math.min(canvasSize.height - 420, Math.round(point.y + 18))),
      query: ""
    });
    setConnecting({ nodeId: edge.source_node_id, portId: edge.source_port_id });
    setSelectedNodeId("");
    setSelectedEdgeId(edge.edge_id);
  }

  function closeNodePicker() {
    setNodePicker(null);
    setConnecting(null);
  }

  function beginOutputHandlePointer(event: PointerEvent<HTMLButtonElement>, node: WorkflowNode, output: WorkflowPort) {
    if (readOnly) return;
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    const start = outputAnchorFor(node);
    setHandleDrag({
      nodeId: node.node_id,
      portId: output.port_id,
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      start,
      current: start,
      active: false
    });
    setConnecting({ nodeId: node.node_id, portId: output.port_id });
    setNodePicker(null);
    setSelectedNodeId(node.node_id);
    setSelectedEdgeId("");
  }

  function moveOutputHandlePointer(event: PointerEvent<HTMLElement>) {
    if (!handleDrag || handleDrag.pointerId !== event.pointerId) return;
    const distance = Math.hypot(event.clientX - handleDrag.startClientX, event.clientY - handleDrag.startClientY);
    setHandleDrag({
      ...handleDrag,
      current: canvasPointFromClient(event.clientX, event.clientY),
      active: handleDrag.active || distance > 5
    });
  }

  function endOutputHandlePointer(event: PointerEvent<HTMLElement>) {
    if (!handleDrag || handleDrag.pointerId !== event.pointerId) return;
    event.stopPropagation();
    const distance = Math.hypot(event.clientX - handleDrag.startClientX, event.clientY - handleDrag.startClientY);
    const dropPoint = canvasPointFromClient(event.clientX, event.clientY);
    const wasDrag = handleDrag.active || distance > 5;
    if (wasDrag) {
      const connected = connectDropTarget(handleDrag.nodeId, handleDrag.portId, event.clientX, event.clientY);
      if (!connected) openNodePicker(handleDrag.nodeId, handleDrag.portId, dropPoint);
    } else {
      openNodePicker(handleDrag.nodeId, handleDrag.portId);
    }
    setHandleDrag(null);
  }

  function completeConnection(targetNodeId: string, targetPortId: string) {
    if (!draft || !connecting || readOnly) return;
    const connected = connectNodes(connecting.nodeId, connecting.portId, targetNodeId, targetPortId);
    if (connected) return;
    setConnecting(null);
  }

  function connectNodes(sourceNodeId: string, sourcePortId: string, targetNodeId: string, targetPortId: string): boolean {
    if (!draft || readOnly) return false;
    if (sourceNodeId === targetNodeId) {
      setConnecting(null);
      return false;
    }
    const source = draft.nodes.find((node) => node.node_id === sourceNodeId);
    const target = draft.nodes.find((node) => node.node_id === targetNodeId);
    const sourcePort = source?.outputs.find((item) => item.port_id === sourcePortId);
    const targetPort = target?.inputs.find((item) => item.port_id === targetPortId);
    if (!source || !target || !sourcePort || !targetPort) return false;
    const overlap = compatibleTypes(sourcePort, targetPort);
    if (overlap.length === 0) {
      onError(`不能连接：${source.title}.${sourcePort.label} 和 ${target.title}.${targetPort.label} 没有兼容类型。`);
      setConnecting(null);
      return false;
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
    setInspectorOpen(true);
    setConnecting(null);
    setNodePicker(null);
    setValidation(null);
    return true;
  }

  function connectDropTarget(sourceNodeId: string, sourcePortId: string, clientX: number, clientY: number): boolean {
    if (!draft) return false;
    const targetElement = document.elementFromPoint(clientX, clientY);
    if (!(targetElement instanceof HTMLElement)) return false;
    const exactInput = targetElement.closest<HTMLElement>("[data-input-port]");
    if (exactInput?.dataset.nodeId && exactInput.dataset.inputPort) {
      return connectNodes(sourceNodeId, sourcePortId, exactInput.dataset.nodeId, exactInput.dataset.inputPort);
    }
    const targetNodeElement = targetElement.closest<HTMLElement>(".workflow-node[data-node-id]");
    const targetNodeId = targetNodeElement?.dataset.nodeId || "";
    const source = draft.nodes.find((node) => node.node_id === sourceNodeId);
    const sourcePort = source?.outputs.find((portItem) => portItem.port_id === sourcePortId);
    const targetNode = draft.nodes.find((node) => node.node_id === targetNodeId);
    const targetPort = sourcePort && targetNode ? bestInputForSource(sourcePort, targetNode) : null;
    return Boolean(targetPort && connectNodes(sourceNodeId, sourcePortId, targetNodeId, targetPort.port_id));
  }

  function addNodeFromPicker(preset: NodePreset) {
    if (!draft || !nodePicker || readOnly) return;
    const source = draft.nodes.find((node) => node.node_id === nodePicker.sourceNodeId);
    const sourcePort = source?.outputs.find((portItem) => portItem.port_id === nodePicker.sourcePortId);
    if (!source || !sourcePort) return;
    const targetPort = bestInputForPreset(sourcePort, preset);
    if (!targetPort) return;
    const insertTargetNode = draft.nodes.find((node) => node.node_id === nodePicker.targetNodeId);
    const insertTargetPort = insertTargetNode?.inputs.find((portItem) => portItem.port_id === nodePicker.targetPortId);
    const sourceOutput = bestOutputForTarget(preset, insertTargetPort);
    if (nodePicker.insertEdgeId && (!insertTargetNode || !insertTargetPort || !sourceOutput)) return;
    const node = buildWorkflowNode(
      draft,
      preset,
      nodePicker.insertEdgeId && insertTargetNode
        ? suggestedInsertedNodePosition(draft, source, insertTargetNode)
        : suggestedConnectedNodePosition(draft, source)
    );
    const edge: WorkflowEdge = {
      edge_id: uniqueEdgeId(draft, `${source.node_id}:${sourcePort.port_id}->${node.node_id}:${targetPort.port_id}`),
      source_node_id: source.node_id,
      source_port_id: sourcePort.port_id,
      target_node_id: node.node_id,
      target_port_id: targetPort.port_id,
      enabled_types: compatibleTypes(sourcePort, targetPort)
    };
    const nextEdges = nodePicker.insertEdgeId && insertTargetNode && insertTargetPort && sourceOutput
      ? [
          ...draft.edges.filter((item) => item.edge_id !== nodePicker.insertEdgeId),
          edge,
          {
            edge_id: uniqueEdgeId(draft, `${node.node_id}:${sourceOutput.port_id}->${insertTargetNode.node_id}:${insertTargetPort.port_id}`),
            source_node_id: node.node_id,
            source_port_id: sourceOutput.port_id,
            target_node_id: insertTargetNode.node_id,
            target_port_id: insertTargetPort.port_id,
            enabled_types: compatibleTypes(sourceOutput, insertTargetPort)
          }
        ]
      : [...draft.edges, edge];
    setDraft({ ...draft, nodes: [...draft.nodes, node], edges: nextEdges });
    setSelectedNodeId(node.node_id);
    setSelectedEdgeId("");
    setInspectorOpen(true);
    setNodePicker(null);
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

  if (workflowView === "library") {
    return (
      <main className="workflow-workspace workflow-library-workspace task-selection-workspace">
        <section className="batch-rail workflow-folder-rail" aria-label="工作流类型">
          <div className="board-panel-head">
            <div>
              <span>工作流类型</span>
              <strong>{visibleWorkflowFolders.length} 个类型</strong>
            </div>
            <button type="button" className="task-submit-button workflow-add-button" title="新建文件夹" aria-label="新建文件夹" onClick={addWorkflowFolder}>
              <PlusIcon />
            </button>
          </div>
          <div className="batch-list-modern workflow-folder-list">
            {visibleWorkflowFolders.map((folder) => (
              <article
                key={folder.folder_id}
                className={`batch-row ${folder.folder_id === activeWorkflowFolder.folder_id ? "active" : ""}`}
                role="button"
                tabIndex={0}
                onClick={() => setActiveWorkflowFolderId(folder.folder_id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    setActiveWorkflowFolderId(folder.folder_id);
                  }
                }}
              >
                <div className="batch-row-top">
                  <span className={`status-pill ${folder.builtin ? "status-completed" : ""}`}>{folder.builtin ? "内置" : "自定义"}</span>
                  <em>{folder.count} 个</em>
                </div>
                <div className="batch-row-main">
                  <strong>{folder.name}</strong>
                </div>
                <div className="batch-row-bottom">
                  <em>{folder.builtin ? "默认分类" : "本地分类"}</em>
                </div>
              </article>
            ))}
          </div>
          <div className="workflow-new-folder">
            <input
              value={newFolderName}
              placeholder="新建文件夹"
              onChange={(event) => setNewFolderName(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") addWorkflowFolder();
              }}
            />
            <button type="button" className="workflow-add-button" title="新建文件夹" aria-label="新建文件夹" onClick={addWorkflowFolder}>
              <PlusIcon />
            </button>
          </div>
        </section>

        <section className="case-lane workflow-template-lane">
          <div className="board-panel-head workflow-template-head">
            <div>
              <span>{activeWorkflowFolder.builtin ? "内置工作流" : "工作流"}</span>
              <strong>{activeWorkflowFolder.name}</strong>
            </div>
            <button type="button" className="task-submit-button workflow-add-button" title="新建工作流" aria-label="新建工作流" onClick={createLocalTemplate}>
              <PlusIcon />
            </button>
          </div>

          <div className="task-list workflow-template-list">
            {libraryTemplates.map((template) => {
              const stats = workflowNodeStats(template);
              const builtin = Boolean(template.defaults?.builtin);
              return (
                <article
                  key={template.template_id}
                  className={`task-row workflow-template-row ${template.template_id === selectedTemplateId ? "active" : ""} ${builtin ? "readonly" : ""}`}
                  role="button"
                  tabIndex={0}
                  onClick={() => openWorkflowCanvas(template.template_id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      openWorkflowCanvas(template.template_id);
                    }
                  }}
                >
                  <div className="task-row-top">
                    <span className={`status-pill ${builtin ? "status-completed" : "status-running"}`}>{builtin ? "内置" : "自定义"}</span>
                    <em>{template.version ? `v${template.version}` : "draft"}</em>
                  </div>
                  <div className="task-thumb workflow-template-thumb">
                    <WorkflowTemplatePreview template={template} />
                  </div>
                  <div className="task-bottom">
                    <div className="task-info">
                      <div className="task-main">
                        <strong>{template.name}</strong>
                        <span>{template.description || "Workflow DAG"}</span>
                      </div>
                      <div className="task-meta">
                        <em>{template.nodes.length} 节点 · {template.edges.length} 连线 · {stats.agent} Agent</em>
                      </div>
                    </div>
                  </div>
                </article>
              );
            })}
            {libraryTemplates.length === 0 && (
              <div className="workflow-library-empty">
                <strong>这个分类还没有工作流</strong>
                <button type="button" className="task-submit-button workflow-add-button" title="新建工作流" aria-label="新建工作流" onClick={createLocalTemplate}>
                  <PlusIcon />
                </button>
              </div>
            )}
          </div>
        </section>
      </main>
    );
  }

  return (
    <>
      {topbarPortal}
      <main className={`workflow-workspace workflow-canvas-workspace ${canvasHasInspector ? "inspector-open" : "inspector-closed"}`}>
        <section className="workflow-canvas-shell">
        <aside className="workflow-canvas-rail" aria-label="Workflow tools">
          <button type="button" className="active" title="编排">W</button>
          <button type="button" title="选择">↖</button>
          <button type="button" title="移动">✥</button>
          <button type="button" title="整理节点" onClick={arrangeNodes} disabled={!draft || readOnly}>▦</button>
          <button type="button" title="校验" onClick={() => void validateDraft()} disabled={!draft || busy === "validate"}>✓</button>
          <div className="workflow-rail-stats">
            <span>P {nodeStats.parser}</span>
            <span>A {nodeStats.agent}</span>
            <span>H {nodeStats.human_review}</span>
          </div>
        </aside>
        {validation && !validation.ok && (
          <div className="workflow-floating-validation failed">
            <strong>{validation.errors.length} 个校验问题</strong>
            {validation.errors.slice(0, 4).map((item, index) => (
              <button
                type="button"
                key={`${item.code}-${item.node_id}-${item.edge_id}-${index}`}
                onClick={() => {
                  if (item.node_id) setSelectedNodeId(item.node_id);
                  if (item.edge_id) setSelectedEdgeId(item.edge_id);
                  setInspectorOpen(true);
                }}
              >
                <span>{item.code}</span>
                <em>{item.node_id || item.edge_id}</em>
              </button>
            ))}
          </div>
        )}
        <div
          ref={viewportRef}
          className={`workflow-canvas-scroll ${canvasPan ? "panning" : ""}`}
          onPointerDown={beginCanvasPan}
          onPointerMove={(event) => {
            moveCanvasPan(event);
            moveOutputHandlePointer(event);
          }}
          onPointerUp={(event) => {
            endCanvasPan(event);
            endOutputHandlePointer(event);
          }}
          onPointerCancel={(event) => {
            endCanvasPan(event);
            if (handleDrag?.pointerId === event.pointerId) {
              setHandleDrag(null);
              setConnecting(null);
            }
          }}
        >
          <div
            ref={canvasRef}
            className="workflow-canvas"
            style={{
              width: canvasSize.width,
              height: canvasSize.height,
              transform: `translate3d(${viewport.x}px, ${viewport.y}px, 0) scale(${viewport.zoom})`
            }}
            onClick={(event) => {
              if (event.target === event.currentTarget) {
                setNodePicker(null);
                setConnecting(null);
              }
            }}
          >
            {draft && (
              <WorkflowEdges
                template={draft}
                selectedEdgeId={selectedEdgeId}
                readOnly={readOnly}
                onSelectEdge={(edgeId) => {
                  setSelectedEdgeId(edgeId);
                  setSelectedNodeId("");
                  setInspectorOpen(true);
                }}
                onOpenEdgeInsert={openEdgePicker}
              />
            )}
            {handleDrag?.active && <WorkflowConnectionPreview drag={handleDrag} />}
            {draft?.nodes.map((node) => {
              const sourceOutput = primaryOutputForNode(node);
              return (
                <article
                  key={node.node_id}
                  className={`workflow-node node-${node.node_type} ${node.node_id === selectedNodeId ? "active" : ""}`}
                  data-node-id={node.node_id}
                  style={{ left: node.position.x || 0, top: node.position.y || 0 }}
                  onClick={() => {
                    setSelectedNodeId(node.node_id);
                    setSelectedEdgeId("");
                    setPromptPreview(null);
                    setInspectorOpen(true);
                  }}
                  onPointerDown={(event) => beginNodeDrag(event, node)}
                  onPointerMove={moveNode}
                  onPointerUp={endNodeDrag}
                  onPointerCancel={endNodeDrag}
                >
                  <div className="workflow-node-head">
                    <span className="workflow-node-icon">
                      <WorkflowNodeIcon nodeType={node.node_type} />
                    </span>
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
                        data-node-id={node.node_id}
                        data-input-port={input.port_id}
                        aria-disabled={!connecting}
                        className={connecting && compatibleTarget(draft, connecting, node, input) ? "compatible" : ""}
                        title={`${input.label}: ${input.types.join(" / ")}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          if (connecting) completeConnection(node.node_id, input.port_id);
                        }}
                      >
                        {input.port_id}
                      </button>
                    ))}
                  </div>
                  <p>{nodeOutputSummary(node)}</p>
                  {sourceOutput && (
                    <button
                      type="button"
                      className={`workflow-node-plus ${connecting?.nodeId === node.node_id && connecting.portId === sourceOutput.port_id ? "connecting" : ""}`}
                      disabled={readOnly || node.node_type === "output"}
                      title={readOnly || node.node_type === "output" ? "不可添加下游节点" : "添加或连接下游节点"}
                      aria-label={readOnly || node.node_type === "output" ? "不可添加下游节点" : "添加或连接下游节点"}
                      onClick={(event) => event.stopPropagation()}
                      onPointerDown={(event) => beginOutputHandlePointer(event, node, sourceOutput)}
                      onPointerMove={moveOutputHandlePointer}
                      onPointerUp={endOutputHandlePointer}
                      onPointerCancel={() => {
                        setHandleDrag(null);
                        setConnecting(null);
                      }}
                    >
                      <PlusIcon />
                    </button>
                  )}
                </article>
              );
            })}
            {nodePicker && (
              <div
                className="workflow-node-picker"
                style={{ left: nodePicker.x, top: nodePicker.y, transform: `scale(${1 / viewport.zoom})` }}
                onPointerDown={(event) => event.stopPropagation()}
                onClick={(event) => event.stopPropagation()}
              >
                <div className="workflow-picker-tabs">
                  <strong>节点</strong>
                  <span>工具</span>
                  <button type="button" onClick={closeNodePicker}>×</button>
                </div>
                <label className="workflow-picker-search">
                  <span>⌕</span>
                  <input
                    value={nodePicker.query}
                    placeholder="搜索节点"
                    onChange={(event) => setNodePicker({ ...nodePicker, query: event.target.value })}
                  />
                </label>
                <div className="workflow-picker-list">
                  {pickerItems.map((item) => (
                    <button
                      type="button"
                      key={item.preset.key}
                      className={`workflow-picker-item node-${item.preset.node_type} ${item.compatible ? "compatible" : "incompatible"}`}
                      disabled={!item.compatible}
                      title={item.compatible ? item.preset.description : "当前输出没有兼容输入"}
                      onClick={() => addNodeFromPicker(item.preset)}
                    >
                      <span>
                        <WorkflowNodeIcon nodeType={item.preset.node_type} />
                      </span>
                      <strong>{item.preset.title}</strong>
                      <em>{item.group}</em>
                    </button>
                  ))}
                  {pickerItems.length === 0 && <p>没有匹配节点</p>}
                </div>
              </div>
            )}
            {connecting && !nodePicker && (
              <button type="button" className="workflow-connect-cancel" onClick={() => setConnecting(null)}>
                取消连线
              </button>
            )}
          </div>
          <div className="workflow-minimap" aria-hidden="true">
            {minimapNodes.map((node) => (
              <span
                key={node.nodeId}
                style={{ left: `${node.x}%`, top: `${node.y}%`, width: `${node.width}%`, height: `${node.height}%` }}
              />
            ))}
          </div>
          <div className="workflow-zoom-control">
            <button type="button" title="缩小" onClick={() => zoomCanvas(-0.08)}>−</button>
            <strong>{Math.round(viewport.zoom * 100)}%</strong>
            <button type="button" title="放大" onClick={() => zoomCanvas(0.08)}>+</button>
            <button type="button" title="适配画布" onClick={fitWorkflowToView}>⤢</button>
          </div>
        </div>
        </section>

      {canvasHasInspector && (
      <aside className="workflow-inspector">
        {selectedNode ? (
          <>
            <div className="workflow-panel-head">
              <div>
                <span>{selectedNode.node_type}</span>
                <strong>{selectedNode.title}</strong>
              </div>
              <button type="button" title="关闭详情" onClick={() => setInspectorOpen(false)}>×</button>
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
              <div>
                <span>Edge</span>
                <strong>{selectedEdge.edge_id}</strong>
              </div>
              <button type="button" title="关闭详情" onClick={() => setInspectorOpen(false)}>×</button>
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
      )}
      </main>
    </>
  );
}

function WorkflowEdges({
  template,
  selectedEdgeId,
  readOnly,
  onSelectEdge,
  onOpenEdgeInsert
}: {
  template: WorkflowTemplate;
  selectedEdgeId: string;
  readOnly: boolean;
  onSelectEdge: (edgeId: string) => void;
  onOpenEdgeInsert: (edgeId: string, point: { x: number; y: number }) => void;
}) {
  const nodeById = new Map(template.nodes.map((node) => [node.node_id, node]));
  const [hoveredEdgeId, setHoveredEdgeId] = useState("");
  const views = template.edges.flatMap((edge) => {
    const source = nodeById.get(edge.source_node_id);
    const target = nodeById.get(edge.target_node_id);
    if (!source || !target) return [];
    const start = outputAnchorPoint(source);
    const end = inputAnchorPoint(target);
    const d = bezierPath(start, end);
    const midpoint = bezierPoint(start, end, 0.5);
    return [{ edge, d, midpoint }];
  });
  return (
    <>
      <svg className="workflow-edges" aria-hidden="true">
        {views.map(({ edge, d }) => (
          <path
            key={edge.edge_id}
            className={edge.edge_id === selectedEdgeId ? "selected" : ""}
            d={d}
            onClick={(event) => {
              event.stopPropagation();
              onSelectEdge(edge.edge_id);
            }}
            onMouseEnter={() => setHoveredEdgeId(edge.edge_id)}
            onMouseLeave={() => setHoveredEdgeId((current) => (current === edge.edge_id ? "" : current))}
          />
        ))}
      </svg>
      {views.map(({ edge, midpoint }) => (
        <button
          type="button"
          key={`${edge.edge_id}:insert`}
          className={`workflow-edge-insert ${edge.edge_id === selectedEdgeId || edge.edge_id === hoveredEdgeId ? "visible" : ""}`}
          data-edge-id={edge.edge_id}
          disabled={readOnly}
          style={{ left: midpoint.x, top: midpoint.y }}
          title="插入节点"
          onClick={(event) => {
            event.stopPropagation();
            onOpenEdgeInsert(edge.edge_id, midpoint);
          }}
          onMouseEnter={() => setHoveredEdgeId(edge.edge_id)}
          onMouseLeave={() => setHoveredEdgeId((current) => (current === edge.edge_id ? "" : current))}
        >
          +
        </button>
      ))}
    </>
  );
}

function WorkflowConnectionPreview({ drag }: { drag: HandleDragState }) {
  const d = bezierPath(drag.start, drag.current);
  return (
    <svg className="workflow-connection-preview" aria-hidden="true">
      <path d={d} />
    </svg>
  );
}

function nodePickerItems(template: WorkflowTemplate, picker: NodePickerState): Array<{ preset: NodePreset; compatible: boolean; group: string }> {
  const source = template.nodes.find((node) => node.node_id === picker.sourceNodeId);
  const sourcePort = source?.outputs.find((portItem) => portItem.port_id === picker.sourcePortId);
  const target = template.nodes.find((node) => node.node_id === picker.targetNodeId);
  const targetPort = target?.inputs.find((portItem) => portItem.port_id === picker.targetPortId);
  const query = picker.query.trim().toLowerCase();
  return NODE_PRESETS
    .filter((preset) => {
      if (!query) return true;
      return [preset.title, preset.node_type, preset.description].some((value) => value.toLowerCase().includes(query));
    })
    .map((preset) => ({
      preset,
      compatible: Boolean(
        sourcePort
        && bestInputForPreset(sourcePort, preset)
        && (!picker.insertEdgeId || bestOutputForTarget(preset, targetPort))
      ),
      group: nodePresetGroup(preset)
    }));
}

function nodePresetGroup(preset: NodePreset): string {
  if (preset.node_type === "parser") return "解析";
  if (preset.node_type === "agent") return "Agent";
  if (preset.node_type === "processor") return "处理";
  if (preset.node_type === "fusion") return "融合";
  if (preset.node_type === "human_review") return "人工";
  if (preset.node_type === "export" || preset.node_type === "output") return "输出";
  return "输入";
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

function PlusIcon() {
  return (
    <svg className="plus-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

function WorkflowTemplatePreview({ template }: { template: WorkflowTemplate }) {
  const nodes = template.nodes.slice(0, 8);
  return (
    <div className="workflow-template-preview" aria-hidden="true">
      {nodes.map((node, index) => (
        <span
          key={node.node_id}
          className={`node-${node.node_type}`}
          style={{
            left: `${8 + (index % 4) * 22}%`,
            top: `${18 + Math.floor(index / 4) * 34}%`
          }}
        />
      ))}
      <i />
      <i />
      <i />
    </div>
  );
}

function primaryOutputForNode(node: WorkflowNode): WorkflowPort | null {
  return node.outputs[0] || null;
}

function loadWorkflowFolders(): WorkflowFolder[] {
  if (typeof window === "undefined") return DEFAULT_WORKFLOW_FOLDERS;
  const raw = window.localStorage.getItem(WORKFLOW_FOLDERS_STORAGE_KEY);
  if (!raw) return DEFAULT_WORKFLOW_FOLDERS;
  const parsed = JSON.parse(raw) as WorkflowFolder[];
  const custom = parsed.filter((folder) => folder.folder_id !== BUILTIN_WORKFLOW_FOLDER_ID && folder.folder_id !== CUSTOM_WORKFLOW_FOLDER_ID);
  return [...DEFAULT_WORKFLOW_FOLDERS, ...custom];
}

function saveWorkflowFolders(folders: WorkflowFolder[]) {
  if (typeof window === "undefined") return;
  const custom = folders.filter((folder) => !folder.builtin && folder.folder_id !== CUSTOM_WORKFLOW_FOLDER_ID);
  window.localStorage.setItem(WORKFLOW_FOLDERS_STORAGE_KEY, JSON.stringify(custom));
}

function workflowFoldersWithCounts(folders: WorkflowFolder[], templates: WorkflowTemplate[]): WorkflowFolderWithCount[] {
  const counts = new Map<string, number>();
  templates.forEach((template) => {
    const folderId = workflowFolderIdForTemplate(template);
    counts.set(folderId, (counts.get(folderId) || 0) + 1);
  });
  return folders.map((folder) => ({ ...folder, count: counts.get(folder.folder_id) || 0 }));
}

function workflowFolderIdForTemplate(template: WorkflowTemplate): string {
  if (template.defaults?.builtin || template.defaults?.read_only) return BUILTIN_WORKFLOW_FOLDER_ID;
  const folderId = String(template.defaults?.folder_id || "");
  return folderId || CUSTOM_WORKFLOW_FOLDER_ID;
}

function uniqueWorkflowFolderId(folders: WorkflowFolder[], name: string): string {
  const existing = new Set(folders.map((folder) => folder.folder_id));
  const base = `folder_${name.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "workflow"}`;
  let candidate = base;
  let index = 2;
  while (existing.has(candidate)) {
    candidate = `${base}_${index}`;
    index += 1;
  }
  return candidate;
}

function copiedWorkflowName(name: string): string {
  return `${name.replace(/\s+copy$/i, "").trim() || DEFAULT_COPY_NAME} Copy`;
}

function arrangeWorkflowNodes(template: WorkflowTemplate): WorkflowNode[] {
  const nodeById = new Map(template.nodes.map((node) => [node.node_id, node]));
  const incomingCount = new Map(template.nodes.map((node) => [node.node_id, 0]));
  const outgoing = new Map<string, string[]>();
  template.edges.forEach((edge) => {
    if (!nodeById.has(edge.source_node_id) || !nodeById.has(edge.target_node_id)) return;
    incomingCount.set(edge.target_node_id, (incomingCount.get(edge.target_node_id) || 0) + 1);
    outgoing.set(edge.source_node_id, [...(outgoing.get(edge.source_node_id) || []), edge.target_node_id]);
  });
  const layers = new Map<string, number>();
  const queue = template.nodes.filter((node) => (incomingCount.get(node.node_id) || 0) === 0).map((node) => node.node_id);
  template.nodes.forEach((node) => layers.set(node.node_id, queue.includes(node.node_id) ? 0 : 1));
  for (let cursor = 0; cursor < queue.length; cursor += 1) {
    const nodeId = queue[cursor];
    const layer = layers.get(nodeId) || 0;
    (outgoing.get(nodeId) || []).forEach((targetId) => {
      layers.set(targetId, Math.max(layers.get(targetId) || 0, layer + 1));
      incomingCount.set(targetId, (incomingCount.get(targetId) || 0) - 1);
      if ((incomingCount.get(targetId) || 0) === 0) queue.push(targetId);
    });
  }
  const grouped = new Map<number, WorkflowNode[]>();
  template.nodes.forEach((node) => {
    const layer = layers.get(node.node_id) || 0;
    grouped.set(layer, [...(grouped.get(layer) || []), node]);
  });
  const sortedLayerKeys = [...grouped.keys()].sort((left, right) => left - right);
  const positionByNodeId = new Map<string, { x: number; y: number }>();
  sortedLayerKeys.forEach((layer, layerIndex) => {
    const nodes = (grouped.get(layer) || []).sort((left, right) => (left.position.y || 0) - (right.position.y || 0));
    const columnX = 92 + layerIndex * 270;
    const startY = Math.max(92, 260 - Math.round((nodes.length - 1) * 62));
    nodes.forEach((node, rowIndex) => {
      positionByNodeId.set(node.node_id, { x: columnX, y: startY + rowIndex * 124 });
    });
  });
  return template.nodes.map((node) => ({
    ...node,
    position: positionByNodeId.get(node.node_id) || node.position
  }));
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

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function normalizedWheelDelta(event: globalThis.WheelEvent): { x: number; y: number } {
  const scale = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 120 : 1;
  return {
    x: event.deltaX * scale,
    y: event.deltaY * scale
  };
}

function workflowBounds(template: WorkflowTemplate): { x: number; y: number; width: number; height: number } {
  if (template.nodes.length === 0) return { x: 0, y: 0, width: 900, height: 520 };
  const minX = Math.min(...template.nodes.map((node) => node.position.x || 0));
  const minY = Math.min(...template.nodes.map((node) => node.position.y || 0));
  const maxX = Math.max(...template.nodes.map((node) => (node.position.x || 0) + NODE_WIDTH));
  const maxY = Math.max(...template.nodes.map((node) => (node.position.y || 0) + NODE_HEIGHT));
  return {
    x: Math.max(0, minX - 48),
    y: Math.max(0, minY - 48),
    width: Math.max(260, maxX - minX + 96),
    height: Math.max(180, maxY - minY + 96)
  };
}

function workflowMinimapNodes(template: WorkflowTemplate): Array<{ nodeId: string; x: number; y: number; width: number; height: number }> {
  const bounds = workflowBounds(template);
  return template.nodes.map((node) => ({
    nodeId: node.node_id,
    x: clamp((((node.position.x || 0) - bounds.x) / bounds.width) * 100, 0, 98),
    y: clamp((((node.position.y || 0) - bounds.y) / bounds.height) * 100, 0, 96),
    width: clamp((NODE_WIDTH / bounds.width) * 100, 6, 28),
    height: clamp((NODE_HEIGHT / bounds.height) * 100, 5, 20)
  }));
}

function compatibleTarget(template: WorkflowTemplate | null, connecting: ConnectingPort, targetNode: WorkflowNode, targetPort: WorkflowPort): boolean {
  const source = template?.nodes.find((node) => node.node_id === connecting.nodeId);
  const sourcePort = source?.outputs.find((item) => item.port_id === connecting.portId);
  return Boolean(sourcePort && source?.node_id !== targetNode.node_id && compatibleTypes(sourcePort, targetPort).length > 0);
}

function bestInputForSource(sourcePort: WorkflowPort, targetNode: WorkflowNode): WorkflowPort | null {
  return targetNode.inputs.find((input) => compatibleTypes(sourcePort, input).length > 0) || null;
}

function bestInputForPreset(sourcePort: WorkflowPort, preset: NodePreset): WorkflowPort | null {
  return preset.inputs.find((input) => compatibleTypes(sourcePort, input).length > 0) || null;
}

function bestOutputForTarget(preset: NodePreset, targetPort?: WorkflowPort): WorkflowPort | null {
  if (!targetPort) return null;
  return preset.outputs.find((output) => compatibleTypes(output, targetPort).length > 0) || null;
}

function outputAnchorPoint(node: WorkflowNode): { x: number; y: number } {
  return {
    x: (node.position.x || 0) + NODE_WIDTH,
    y: (node.position.y || 0) + NODE_HEIGHT / 2
  };
}

function inputAnchorPoint(node: WorkflowNode): { x: number; y: number } {
  return {
    x: node.position.x || 0,
    y: (node.position.y || 0) + NODE_HEIGHT / 2
  };
}

function bezierControls(start: { x: number; y: number }, end: { x: number; y: number }) {
  const offset = Math.max(44, Math.abs(end.x - start.x) * 0.42);
  return {
    c1: { x: start.x + offset, y: start.y },
    c2: { x: end.x - offset, y: end.y }
  };
}

function bezierPath(start: { x: number; y: number }, end: { x: number; y: number }): string {
  const { c1, c2 } = bezierControls(start, end);
  return `M ${start.x} ${start.y} C ${c1.x} ${c1.y}, ${c2.x} ${c2.y}, ${end.x} ${end.y}`;
}

function bezierPoint(start: { x: number; y: number }, end: { x: number; y: number }, t: number): { x: number; y: number } {
  const { c1, c2 } = bezierControls(start, end);
  const inv = 1 - t;
  return {
    x: inv ** 3 * start.x + 3 * inv ** 2 * t * c1.x + 3 * inv * t ** 2 * c2.x + t ** 3 * end.x,
    y: inv ** 3 * start.y + 3 * inv ** 2 * t * c1.y + 3 * inv * t ** 2 * c2.y + t ** 3 * end.y
  };
}

function buildWorkflowNode(template: WorkflowTemplate, preset: NodePreset, position?: { x: number; y: number }): WorkflowNode {
  const index = nextNodeIndex(template, preset.node_type);
  const nodeId = uniqueNodeId(template, preset.key.replace(/[^a-zA-Z0-9_-]/g, "_"));
  const defaultPosition = { x: 100 + (index % 4) * 230, y: 100 + Math.floor(index / 4) * 150 };
  return {
    node_id: nodeId,
    node_type: preset.node_type,
    title: preset.title,
    description: preset.description,
    inputs: cloneJson(preset.inputs),
    outputs: cloneJson(preset.outputs),
    config: cloneJson(preset.config || {}),
    position: position || defaultPosition
  };
}

function suggestedConnectedNodePosition(template: WorkflowTemplate, source: WorkflowNode): { x: number; y: number } {
  const baseX = (source.position.x || 0) + 280;
  const sourceY = source.position.y || 0;
  const occupied = new Set(template.nodes.map((node) => `${Math.round((node.position.x || 0) / 20)}:${Math.round((node.position.y || 0) / 20)}`));
  for (let offset = 0; offset < 8; offset += 1) {
    const y = Math.max(16, sourceY + offset * 112);
    const key = `${Math.round(baseX / 20)}:${Math.round(y / 20)}`;
    if (!occupied.has(key)) return { x: baseX, y };
  }
  return { x: baseX, y: sourceY + 112 };
}

function suggestedInsertedNodePosition(
  template: WorkflowTemplate,
  source: WorkflowNode,
  target: WorkflowNode
): { x: number; y: number } {
  const baseX = Math.max(0, Math.round(((source.position.x || 0) + (target.position.x || 0)) / 2));
  const baseY = Math.max(0, Math.round(((source.position.y || 0) + (target.position.y || 0)) / 2));
  // Check if position overlaps with existing nodes and offset if needed
  const occupied = new Set(
    template.nodes
      .filter((n) => n.node_id !== source.node_id && n.node_id !== target.node_id)
      .map((n) => `${Math.round((n.position.x || 0) / 20)}:${Math.round((n.position.y || 0) / 20)}`)
  );
  for (let offset = 0; offset < 12; offset += 1) {
    const y = Math.max(16, baseY + (offset % 2 === 0 ? 1 : -1) * Math.ceil(offset / 2) * 60);
    const key = `${Math.round(baseX / 20)}:${Math.round(y / 20)}`;
    if (!occupied.has(key)) return { x: baseX, y };
  }
  return { x: baseX, y: baseY + 60 };
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
