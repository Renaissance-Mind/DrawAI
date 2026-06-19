import { PointerEvent, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  copyWorkflowTemplate,
  listWorkflowProviders,
  listWorkflowTemplates,
  saveWorkflowTemplate,
  validateWorkflowTemplate
} from "./workflowApi";
import type {
  AgentProviderSpec,
  WorkflowEdge,
  WorkflowNode,
  WorkflowPort,
  WorkflowTemplate,
  WorkflowValidationResult
} from "./workflowTypes";
import { buildWorkflowPreviewLayout } from "./workflowPreviewLayout";
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
type WorkflowDialogMode = "folder" | "workflow" | null;

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
type WorkflowFormatOption = {
  format_id: string;
  type: string;
  label: string;
  description: string;
};
type SamPromptConfig = {
  id: string;
  text: string;
  confidence_threshold: number;
};
type NodePickerItem = {
  preset: NodePreset;
  compatible: boolean;
  group: string;
};
type NodePickerGroup = {
  group: string;
  items: NodePickerItem[];
};

const NODE_WIDTH = 236;
const NODE_HEIGHT = 72;
const NODE_COLUMN_SPACING = 270;
const NODE_ROW_SPACING = 124;
const NODE_DEFAULT_GRID_X = 230;
const NODE_DEFAULT_GRID_Y = 150;
const NODE_INSERT_COLLISION_STEP = 60;
const DEFAULT_VIEWPORT: CanvasViewport = { x: 88, y: 74, zoom: 0.84 };
const MIN_ZOOM = 0.5;
const MAX_ZOOM = 1.25;
const DEFAULT_COPY_NAME = "Custom DrawAI DAG";
const DEFAULT_BLANK_WORKFLOW_NAME = "Untitled Workflow";
const WORKFLOW_TEMPLATE_SCHEMA = "drawai.workflow_template.v1";
const BUILTIN_WORKFLOW_FOLDER_ID = "builtin";
const CUSTOM_WORKFLOW_FOLDER_ID = "custom";
const WORKFLOW_FOLDERS_STORAGE_KEY = "drawai.workflow.folders";
const DEFAULT_WORKFLOW_FOLDERS: WorkflowFolder[] = [
  { folder_id: BUILTIN_WORKFLOW_FOLDER_ID, name: "DrawAI默认工作流", builtin: true },
  { folder_id: CUSTOM_WORKFLOW_FOLDER_ID, name: "自定义工作流" }
];
const AGENT_DEFAULT_TASKS: Record<string, string> = {
  run0_element_refine: `DrawAI asset post-processing and source analysis task.

We are performing an image vectorization task: a bitmap image will eventually be transformed into an editable representation. The whole process has three parts:
- Asset parsing: divide the image into independent assets. Each asset may be text, an icon, table, frame, arrow, and so on.
- Asset post-processing: refine the pre-parsed assets.
- Editable reconstruction: combine assets and finish the final visual result.

Some assets should become editable forms, such as text, frames, arrows, and simple vector graphics. Some assets should instead be cropped from the original image and pasted back into their original positions. The parser/OCR/fusion outputs are evidence, not truth. Execute the second stage, asset post-processing, and produce the refined element/source analysis that later asset materialization and SVG generation will consume.

Task 1: refine the connected candidates into minimum independent assets.
Each output element should be the smallest independent visual part, such as one icon, image, frame, arrow, text line, chart mark, chart block, or diagram component.
- Split a candidate when one box contains multiple independent parts.
- Add a new element when an asset is visible in the original image but not covered by any current candidate.
- Adjust the bbox when the current position is wrong or misses part of a component.
- Remove or merge a candidate only when it is clearly duplicate, noise, or wholly represented by another retained element.
- Preserve traceability through source_candidate_ids. Use stable IDs for split or added elements.
- Bboxes must be visual extents in image pixels. For straight lines/dividers, give at least 1 pixel of thickness.
- For geometry_kind="mask", use mask_preview PNGs and the mask preview sheet as visual evidence. Do not adjust or resize the mask region; preserve its bbox/geometry when keeping it.

Task 2: run a bounded visualization/refinement loop, at most 3 iterations.
1. Write reports/element_analysis_codex/refine_iteration_<N>.json.
2. Run assets_visualization.py with the original image and that iteration JSON.
3. Inspect reports/element_analysis_codex/assets_visualization_iteration_<N>.png.
4. Correct assets, splits/merges, removals, and bbox coordinates.
5. Save reports/element_analysis_codex/refined_assets_final.json.

Task 3: classify every final retained element into exactly one source category.
- svg_self_draw: editable SVG primitives/text/paths for text, arrows, boxes, lines, charts, simple diagrams, and simple icons.
- crop: precise source-image crop with local background preserved for screenshots, photos, dense textures, heatmaps, complex small raster icons, or background-coupled details.
- crop_nobg: crop after background removal/transparent subject extraction when foreground should sit over reconstructed SVG background.

Important coverage rules:
- Treat SAM/OCR/current asset plan as evidence, not truth.
- Do not skip candidates. Every original candidate must be represented by retained output elements or removed/merged records.
- The type field must be a concrete DrawAI element type: text, icon, picture, table, chart, diagram, arrow, frame, grid, symbol, content_box, or unknown.
- New IDs are allowed only for split or added refined elements.
- If uncertain, choose the most faithful final-source strategy and mark confidence low or medium.

Final JSON schema: drawai.codex_element_analysis.v1. Include strategy_summary, refinement_summary, refinement_iterations, category counts, refinement_action counts, retained elements, optional removal records, and notes. Also write reports/element_analysis_codex/analysis_notes.md. The JSON file is the source of truth.`,
  svg_generation: `IMAGE VECTORIZATION TASK
Goal: convert one bitmap figure into an editable, PPT-stable SVG.

OVERALL DRAWAI PIPELINE
1. Asset parsing: split the bitmap figure into independent visual assets.
2. Asset post-processing: refine assets, adjust bboxes, split/merge elements, add missing elements, and decide svg_self_draw/crop/crop_nobg source strategy.
3. Image editabilization: reconstruct the whole figure as editable SVG/PPT by combining SVG primitives/text with allowed raster crop assets.

The current Agent node executes stage 3 only. Do not redo stage 1 or stage 2. Use their outputs as evidence, especially refined element/source analysis and the asset manifest. Create one complete first-pass SVG, then refine it for up to 3 rounds inside the same Agent run.

Primary reading order:
1. Original/current reference image and refined element/source analysis.
2. Asset manifest and native_backfill_request before inserting any raster href.
3. OCR only when text details need help.
4. SVG template IR or layout IR only as fallback hints.

SOURCE POLICY
- svg_self_draw: editable SVG primitives/text for text, formulas, arrows, frames, tables, axes, borders, simple charts, simple icons, and simple diagram components.
- crop: exact local crop image for screenshots, photos, dense raster texture, heatmaps, complex small icons, or details unsuitable for faithful SVG redraw.
- crop_nobg: no-background crop image when a foreground object should sit over reconstructed editable SVG background.
- Use refined source labels as the default; override only when visible evidence and current render show another strategy is more faithful.
- Insert only hrefs listed in asset_manifest or native_backfill_request.
- Do not use raster images to cover text, arrows, panels, tables, formulas, axes, or structure that should remain editable.

RUN1 / COMPLETE FIRST PASS
- Write semantic_0.svg.
- It must be a complete whole-figure SVG, not a placeholder map, skeleton, gray-box map, or list of asset boxes.
- Cover the whole canvas.
- Use SVG/text for svg_self_draw elements.
- Use manifest image hrefs for crop/crop_nobg elements when available.
- Preserve refined bboxes unless visible evidence shows they need adjustment.
- Render/validate semantic_0.svg to rendered_0.png and validation_report_0.json.
- Record Run1 in iteration_log.md and iteration_log.jsonl.

REFINE LOOP / MAX 3 ROUNDS
At each round, render the latest SVG, compare against the original image, inspect whole figure first then local regions, and fix the highest-impact issues. Consider layout mismatch, text mismatch, connector/arrow mismatch, shape/table/axis mismatch, asset source mismatch, editability regression, PPT stability issues, and validator issues.

Round outputs:
- Round 1 writes semantic_1.svg, rendered_1.png, validation_report_1.json.
- Round 2 writes semantic_2.svg, rendered_2.png, validation_report_2.json.
- Round 3 writes semantic_3.svg, rendered_3.png, validation_report_3.json.

Stop before 3 rounds only when the render is close enough, editable structures remain editable, crop/crop_nobg regions use allowed sources, validation is ok, and another round is unlikely to help.

FINALIZATION
- Choose the latest acceptable SVG as final.
- Write semantic.svg and the declared SVG output.
- Render/validate semantic.svg to rendered.png and validation_report_final.json.
- Write iteration_log.md and iteration_log.jsonl.

OVERALL SVG/PPT PROFILE
Target DrawAI Scientific SVG Profile v1 for editable PPT conversion. Use rect, circle/ellipse, line/polyline/path, polygon, text/tspan, g, and simple defs/markers/gradients. Use image only for explicit manifest raster assets. Do not output CSS style blocks, filters, masks, clipPath, foreignObject, textPath, pattern fills, base64 images, external image URLs, absolute paths, symbol, or use. Prefer direct presentation attributes. Preserve editable text/formulas with text/tspan and Unicode math/superscript/subscript. Mark non-editable raster assets data-pb-editable="false" and editable vectors/text data-pb-editable="true".`,
  custom_agent: `Use the connected input files as context and produce exactly the output files declared by this node configuration.

This is a configurable DrawAI Agent node. The node editor controls the task, input inclusion, input descriptions, output declarations, provider, model/profile/reasoning settings, timeout, and runtime constraints. Read the connected files listed in the prompt, follow the declared output formats, and write only the declared outputs.`
};
const AGENT_DEFAULT_CONSTRAINTS: Record<string, string[]> = {
  run0_element_refine: [
    "Use only the connected input files listed in this prompt and files under the current DrawAI case/workspace root.",
    "Do not render final SVG/PPT and do not modify repository code. This node only refines/classifies assets.",
    "Do not use MCP tools, apps, web search, memories, skills, hooks, or multi-agent delegation.",
    "Do not print full request JSON to the terminal or logs; start from compact candidate tables and read exact details only when needed.",
    "Every source candidate must be represented by retained output elements or explicit removed/merged records.",
    "Write the declared output files exactly, in UTF-8 JSON or markdown according to the output declaration."
  ],
  svg_generation: [
    "Use only connected files and files under the current DrawAI workspace/case root.",
    "Do not redo parsing or asset-source analysis; consume the connected refined elements and asset manifest as evidence.",
    "Do not use MCP tools, apps, web search, memories, skills, hooks, or multi-agent delegation.",
    "Do not invent image hrefs, external URLs, file:// URLs, absolute paths, or base64 images.",
    "Do not rasterize panels, arrows, text, formulas, grids, tables, axes, or whole diagram structure.",
    "Write the declared SVG/render/log outputs exactly and keep the final chat response short."
  ],
  custom_agent: [
    "Treat every connected input file as explicit node context.",
    "Honor the configured output declarations over node defaults.",
    "Write only the declared output paths inside this node work directory."
  ]
};
const WORKFLOW_TYPE_CONTRACTS: Record<string, string> = {
  image: "Raster image file. Use it as visual evidence; do not rewrite it unless this node declares an image output.",
  element_candidates:
    "Parser candidate elements before fusion/refinement. JSON contains candidates with candidate_id, source_parser, element_type, bbox [x, y, width, height], geometry, confidence, optional text, evidence_files, provenance, and raw_ref.",
  element_plans:
    "Refined/planned DrawAI elements. JSON contains elements with element_id, source_candidate_ids, element_type, bbox [x, y, width, height], geometry, z_order, confidence low|medium|high, processing_intent {object_type, processing_type, parameters}, review_status, created_by_stage, and change_reason.",
  element_analysis:
    "Run0 asset/source analysis JSON. JSON contains schema drawai.codex_element_analysis.v1, case_dir, source, strategy_summary, refinement_summary, categories, refinement_actions, elements, optional removal_records, and notes. Each retained element uses box_id or element_id, source_candidate_ids, refinement_action, category svg_self_draw|crop|crop_nobg, confidence, visual_role, reason, evidence, bbox [x1, y1, x2, y2], type, current_pipeline_method, and recommended_asset_source.",
  asset_packages:
    "Processed asset package collection. JSON contains asset_packages with asset_id, element_id, processor_type, status pending|running|ok|failed|unsupported, files, metadata, processor_runs, all_results, active_result, editable_payload, and failure.",
  semantic_svg: "Editable SVG file with an <svg> root following the DrawAI semantic SVG/PPT profile.",
  pptx: "PowerPoint Open XML .pptx package.",
  final_outputs: "Output-node manifest listing collected deliverables and optional mirrored paths."
};
const WORKFLOW_FORMAT_CONTRACTS: Record<string, string> = {
  "drawai.image.v1": "Openable raster image file, usually PNG/JPEG/WebP.",
  "drawai.element_candidates.v1": "UTF-8 JSON object with a candidates array, or a JSON array of element candidate objects.",
  "drawai.element_plans.v1": "UTF-8 JSON object with an elements array, or a JSON array of element plan objects.",
  "drawai.codex_element_analysis.v1":
    "UTF-8 JSON object with schema drawai.codex_element_analysis.v1 and an elements array. Retained elements use box_id/element_id, bbox as x1,y1,x2,y2, category svg_self_draw|crop|crop_nobg, source_candidate_ids, type, confidence, reason, and evidence; removed or merged candidates may appear in removal_records.",
  "drawai.asset_package.v1": "UTF-8 JSON object for one DrawAI asset package.",
  "drawai.asset_packages.v1": "UTF-8 JSON object with an asset_packages array, or a JSON array of asset package objects.",
  "drawai.semantic_svg.v1": "SVG XML file whose document root is <svg>.",
  "drawai.pptx.v1": "Valid zipped PowerPoint Open XML package containing [Content_Types].xml and ppt/presentation.xml.",
  "drawai.final_outputs.v1": "UTF-8 JSON object with an outputs array generated by an output node."
};
const DEFAULT_SAM_PROMPTS: SamPromptConfig[] = [
  { id: "arrow", text: "arrow", confidence_threshold: 0.3 },
  { id: "border", text: "border", confidence_threshold: 0.3 },
  { id: "content_box", text: "content box", confidence_threshold: 0.15 },
  { id: "grid", text: "grid", confidence_threshold: 0.3 },
  { id: "icon", text: "icon", confidence_threshold: 0.3 },
  { id: "picture", text: "picture", confidence_threshold: 0.3 }
];
const NODE_PICKER_GROUP_ORDER = ["Parser", "Agent", "Processor", "Review", "Fusion", "Export"];
const WORKFLOW_FORMAT_OPTIONS: WorkflowFormatOption[] = [
  {
    format_id: "drawai.image.v1",
    type: "image",
    label: "Image",
    description: "Generated or edited image file."
  },
  {
    format_id: "drawai.element_candidates.v1",
    type: "element_candidates",
    label: "Element Candidates",
    description: "Parser-style element candidate JSON."
  },
  {
    format_id: "drawai.element_plans.v1",
    type: "element_plans",
    label: "Element Plans",
    description: "DrawAI element plan JSON."
  },
  {
    format_id: "drawai.codex_element_analysis.v1",
    type: "element_analysis",
    label: "Element Analysis",
    description: "Run0 asset/source analysis JSON."
  },
  {
    format_id: "drawai.asset_packages.v1",
    type: "asset_packages",
    label: "Asset Packages",
    description: "Renderable asset package JSON."
  },
  {
    format_id: "drawai.semantic_svg.v1",
    type: "semantic_svg",
    label: "Semantic SVG",
    description: "Editable semantic SVG file."
  },
  {
    format_id: "drawai.pptx.v1",
    type: "pptx",
    label: "PPTX",
    description: "Exported PowerPoint presentation."
  },
  {
    format_id: "drawai.final_outputs.v1",
    type: "final_outputs",
    label: "Final Outputs",
    description: "Collected output manifest JSON."
  }
];
const WORKFLOW_ANY_TYPES = WORKFLOW_FORMAT_OPTIONS.map((option) => option.type);

const NODE_PRESETS: NodePreset[] = [
  {
    key: "sam-parser",
    node_type: "parser",
    title: "SAM Parser",
    icon: "P",
    description: "Segment visual structure with configurable text prompts and thresholds.",
    inputs: [port("image", "Image", ["image"], "drawai.image.v1")],
    outputs: [port("candidates", "Candidates", ["element_candidates"], "drawai.element_candidates.v1", false)],
    config: { parser_id: "sam3_structure_parser", resource: "sam3", prompts: DEFAULT_SAM_PROMPTS }
  },
  {
    key: "ocr-parser",
    node_type: "parser",
    title: "OCR Parser",
    icon: "P",
    description: "Extract text candidates from the source image.",
    inputs: [port("image", "Image", ["image"], "drawai.image.v1")],
    outputs: [port("candidates", "Candidates", ["element_candidates"], "drawai.element_candidates.v1", false)],
    config: { parser_id: "ocr_text_parser", resource: "ocr" }
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
    key: "asset-refine-agent",
    node_type: "agent",
    title: "Asset Refine Agent",
    icon: "A",
    description: "Agent node that refines element plans.",
    inputs: [port("elements", "Element Plans", ["element_plans"], "drawai.element_plans.v1")],
    outputs: [port("analysis", "Element Analysis", ["element_analysis"], "drawai.codex_element_analysis.v1", false)],
    config: {
      preset_id: "run0_element_refine",
      provider_id: "codex_sdk",
      task: AGENT_DEFAULT_TASKS.run0_element_refine,
      constraints: AGENT_DEFAULT_CONSTRAINTS.run0_element_refine,
      scripts: [
        {
          script_id: "assets_visualization",
          path: "scripts/assets_visualization.py",
          description: "Renders asset-refinement bbox JSON over the source image for Run0 visual QA iterations.",
          usage:
            "python {script} --image <image> --json <iteration_json> --output <png> --summary-output <summary_json> --color-mode action --label-mode id_type"
        }
      ],
      outputs: [
        {
          port_id: "analysis",
          path: "output/element_analysis.json",
          format_id: "drawai.codex_element_analysis.v1",
          type: "element_analysis",
          description: "Run0 refined asset/source analysis in the standard DrawAI Codex element analysis JSON format."
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
      task: AGENT_DEFAULT_TASKS.svg_generation,
      constraints: AGENT_DEFAULT_CONSTRAINTS.svg_generation,
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
    key: "custom-agent",
    node_type: "agent",
    title: "Custom Agent",
    icon: "A",
    description: "Unconstrained Agent node that reads connected files and writes declared outputs.",
    inputs: [port("inputs", "Inputs", WORKFLOW_ANY_TYPES, "", true, "many")],
    outputs: [port("image", "Image", ["image"], "drawai.image.v1", false)],
    config: {
      preset_id: "custom_agent",
      provider_id: "codex_sdk",
      task: AGENT_DEFAULT_TASKS.custom_agent,
      constraints: AGENT_DEFAULT_CONSTRAINTS.custom_agent,
      outputs: [
        {
          port_id: "image",
          path: "output/image.png",
          format_id: "drawai.image.v1",
          type: "image",
          description: "Generated or edited image file."
        }
      ]
    }
  },
  {
    key: "asset-planner",
    node_type: "processor",
    title: "Asset Planner",
    icon: "R",
    description: "Convert Run0 element analysis into DrawAI element plans and asset draft.",
    inputs: [port("analysis", "Element Analysis", ["element_analysis"], "drawai.codex_element_analysis.v1")],
    outputs: [port("elements", "Element Plans", ["element_plans"], "drawai.element_plans.v1", false)],
    config: { processor_id: "asset_planner" }
  },
  {
    key: "asset-processors",
    node_type: "processor",
    title: "Asset Processors",
    icon: "R",
    description: "Run fixed asset processors and produce asset packages.",
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
  const [workflowDialog, setWorkflowDialog] = useState<WorkflowDialogMode>(null);
  const [workflowFolders, setWorkflowFolders] = useState<WorkflowFolder[]>(() => loadWorkflowFolders());
  const [activeWorkflowFolderId, setActiveWorkflowFolderId] = useState(BUILTIN_WORKFLOW_FOLDER_ID);
  const [folderNameDraft, setFolderNameDraft] = useState("");
  const [workflowNameDraft, setWorkflowNameDraft] = useState("");
  const [selectedCopyTemplateId, setSelectedCopyTemplateId] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [draft, setDraft] = useState<WorkflowTemplate | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState("");
  const [selectedEdgeId, setSelectedEdgeId] = useState("");
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [validation, setValidation] = useState<WorkflowValidationResult | null>(null);
  const [dragging, setDragging] = useState<DraggingNode | null>(null);
  const [canvasPan, setCanvasPan] = useState<CanvasPanState | null>(null);
  const [viewport, setViewport] = useState<CanvasViewport>(DEFAULT_VIEWPORT);
  const [connecting, setConnecting] = useState<ConnectingPort | null>(null);
  const [handleDrag, setHandleDrag] = useState<HandleDragState | null>(null);
  const [nodePicker, setNodePicker] = useState<NodePickerState | null>(null);
  const [busy, setBusy] = useState("");
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const handleDragRef = useRef<HandleDragState | null>(null);

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
      setNodePicker(null);
      handleDragRef.current = null;
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
  const selectedAgentPromptText = useMemo(
    () => selectedNode && selectedNode.node_type === "agent" ? workflowAgentPromptText(selectedNode, selectedAgentInputs) : "",
    [selectedNode, selectedAgentInputs]
  );
  const selectedSamPrompts = selectedNode ? samPromptsForNode(selectedNode) : [];
  const pickerItems = useMemo(() => (draft && nodePicker ? nodePickerItems(draft, nodePicker) : []), [draft, nodePicker]);
  const pickerGroups = useMemo(() => nodePickerGroups(pickerItems), [pickerItems]);
  const minimapNodes = useMemo(() => (draft ? workflowMinimapNodes(draft) : []), [draft]);
  const visibleWorkflowFolders = useMemo(() => workflowFoldersWithCounts(workflowFolders, templates), [workflowFolders, templates]);
  const activeWorkflowFolder = visibleWorkflowFolders.find((folder) => folder.folder_id === activeWorkflowFolderId) || visibleWorkflowFolders[0];
  const libraryTemplates = useMemo(
    () => templates.filter((template) => workflowFolderIdForTemplate(template) === activeWorkflowFolder.folder_id),
    [templates, activeWorkflowFolder.folder_id]
  );
  const builtinWorkflowTemplates = useMemo(
    () => templates.filter((template) => workflowFolderIdForTemplate(template) === BUILTIN_WORKFLOW_FOLDER_ID),
    [templates]
  );
  const topbarTarget = typeof document !== "undefined" ? document.getElementById("drawai-view-controls") : null;
  const modalTarget = typeof document !== "undefined" ? document.body : null;
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
  const workflowDialogPortal =
    modalTarget && workflowDialog
      ? createPortal(
          <WorkflowLibraryDialog
            mode={workflowDialog}
            folderName={folderNameDraft}
            workflowName={workflowNameDraft}
            selectedCopyTemplateId={selectedCopyTemplateId}
            builtinTemplates={builtinWorkflowTemplates}
            busy={busy}
            onClose={closeWorkflowDialog}
            onFolderNameChange={setFolderNameDraft}
            onWorkflowNameChange={setWorkflowNameDraft}
            onSelectCopyTemplate={setSelectedCopyTemplateId}
            onCreateFolder={confirmAddWorkflowFolder}
            onCopyWorkflow={() => void copyWorkflowFromDialog()}
            onCreateBlankWorkflow={createBlankWorkflowFromDialog}
          />,
          modalTarget
        )
      : null;

  async function copySelectedTemplate(sourceId = selectedTemplateId || "default_drawai_dag", preferredName = ""): Promise<boolean> {
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
      return true;
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
      return false;
    } finally {
      setBusy("");
    }
  }

  function createBlankWorkflowFromDialog() {
    const folderId = activeWorkflowFolderId === BUILTIN_WORKFLOW_FOLDER_ID ? CUSTOM_WORKFLOW_FOLDER_ID : activeWorkflowFolderId;
    const template = blankWorkflowTemplate(
      uniqueTemplateId(templates, "custom_workflow"),
      workflowNameDraft.trim() || DEFAULT_BLANK_WORKFLOW_NAME,
      folderId
    );
    setTemplates((current) => [...current.filter((item) => item.template_id !== template.template_id), template]);
    setActiveWorkflowFolderId(folderId);
    setSelectedTemplateId(template.template_id);
    setDraft(template);
    setSelectedNodeId(defaultSelectedNodeId(template));
    setSelectedEdgeId("");
    setValidation(null);
    setNodePicker(null);
    handleDragRef.current = null;
    setHandleDrag(null);
    setConnecting(null);
    setInspectorOpen(false);
    setWorkflowView("canvas");
    setViewport(DEFAULT_VIEWPORT);
    closeWorkflowDialog();
  }

  async function copyWorkflowFromDialog() {
    if (!selectedCopyTemplateId) return;
    const copied = await copySelectedTemplate(selectedCopyTemplateId, workflowNameDraft);
    if (copied) closeWorkflowDialog();
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

  function selectTemplate(templateId: string) {
    const template = templates.find((item) => item.template_id === templateId) || null;
    setSelectedTemplateId(template?.template_id || "");
    setDraft(template ? cloneTemplate(template) : null);
    setSelectedNodeId(template ? defaultSelectedNodeId(template) : "");
    setSelectedEdgeId("");
    setValidation(null);
    setConnecting(null);
    setNodePicker(null);
    handleDragRef.current = null;
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
    handleDragRef.current = null;
    setHandleDrag(null);
    setInspectorOpen(false);
  }

  function openFolderDialog() {
    setFolderNameDraft("");
    setWorkflowDialog("folder");
  }

  function openWorkflowDialog() {
    setWorkflowNameDraft("");
    setSelectedCopyTemplateId("");
    setWorkflowDialog("workflow");
  }

  function closeWorkflowDialog() {
    setWorkflowDialog(null);
    setFolderNameDraft("");
    setWorkflowNameDraft("");
    setSelectedCopyTemplateId("");
  }

  function confirmAddWorkflowFolder() {
    const name = folderNameDraft.trim();
    if (!name) return;
    const folder: WorkflowFolder = {
      folder_id: uniqueWorkflowFolderId(workflowFolders, name),
      name
    };
    setWorkflowFolders((current) => [...current, folder]);
    setActiveWorkflowFolderId(folder.folder_id);
    closeWorkflowDialog();
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

  function beginOutputHandlePointer(event: PointerEvent<HTMLButtonElement>, node: WorkflowNode, output: WorkflowPort) {
    if (readOnly) return;
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    const start = outputAnchorFor(node);
    const nextDrag = {
      nodeId: node.node_id,
      portId: output.port_id,
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      start,
      current: start,
      active: false
    };
    handleDragRef.current = nextDrag;
    setHandleDrag(nextDrag);
    setConnecting({ nodeId: node.node_id, portId: output.port_id });
    setNodePicker(null);
    setSelectedNodeId(node.node_id);
    setSelectedEdgeId("");
  }

  function moveOutputHandlePointer(event: PointerEvent<HTMLElement>) {
    const currentDrag = handleDragRef.current || handleDrag;
    if (!currentDrag || currentDrag.pointerId !== event.pointerId) return;
    const distance = Math.hypot(event.clientX - currentDrag.startClientX, event.clientY - currentDrag.startClientY);
    const nextDrag = {
      ...currentDrag,
      current: canvasPointFromClient(event.clientX, event.clientY),
      active: currentDrag.active || distance > 5
    };
    handleDragRef.current = nextDrag;
    setHandleDrag(nextDrag);
  }

  function endOutputHandlePointer(event: PointerEvent<HTMLElement>) {
    const currentDrag = handleDragRef.current || handleDrag;
    if (!currentDrag || currentDrag.pointerId !== event.pointerId) return;
    event.stopPropagation();
    const distance = Math.hypot(event.clientX - currentDrag.startClientX, event.clientY - currentDrag.startClientY);
    const dropPoint = canvasPointFromClient(event.clientX, event.clientY);
    const wasDrag = currentDrag.active || distance > 5;
    if (wasDrag) {
      const connected = connectDropTarget(currentDrag.nodeId, currentDrag.portId, event.clientX, event.clientY);
      if (!connected) openNodePicker(currentDrag.nodeId, currentDrag.portId, dropPoint);
    } else {
      openNodePicker(currentDrag.nodeId, currentDrag.portId);
    }
    handleDragRef.current = null;
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
    const customInsertOutput = isCustomAgentPreset(preset) && insertTargetPort ? outputPortForTarget(insertTargetPort) : null;
    const sourceOutput = customInsertOutput || bestOutputForTarget(preset, insertTargetPort);
    if (nodePicker.insertEdgeId && (!insertTargetNode || !insertTargetPort || !sourceOutput)) return;
    const insertionLayout =
      nodePicker.insertEdgeId && insertTargetNode
        ? workflowInsertionLayout(draft, source, insertTargetNode)
        : null;
    const workingDraft = insertionLayout ? { ...draft, nodes: insertionLayout.nodes } : draft;
    const insertTarget = insertionLayout?.target || insertTargetNode;
    let node = buildWorkflowNode(
      workingDraft,
      preset,
      insertionLayout ? insertionLayout.position : suggestedConnectedNodePosition(workingDraft, source)
    );
    node = customizeCustomAgentNode(node, customInsertOutput);
    const reservedEdgeIds = new Set(workingDraft.edges.map((item) => item.edge_id));
    const edge: WorkflowEdge = {
      edge_id: uniqueEdgeIdFromSet(reservedEdgeIds, `${source.node_id}:${sourcePort.port_id}->${node.node_id}:${targetPort.port_id}`),
      source_node_id: source.node_id,
      source_port_id: sourcePort.port_id,
      target_node_id: node.node_id,
      target_port_id: targetPort.port_id,
      enabled_types: compatibleTypes(sourcePort, targetPort)
    };
    const inheritedEdges = inheritedCustomAgentInputEdges(workingDraft, source, node, targetPort, reservedEdgeIds);
    const nextEdges = nodePicker.insertEdgeId && insertTarget && insertTargetPort && sourceOutput
      ? [
          ...workingDraft.edges.filter((item) => item.edge_id !== nodePicker.insertEdgeId),
          edge,
          ...inheritedEdges,
          {
            edge_id: uniqueEdgeIdFromSet(reservedEdgeIds, `${node.node_id}:${sourceOutput.port_id}->${insertTarget.node_id}:${insertTargetPort.port_id}`),
            source_node_id: node.node_id,
            source_port_id: sourceOutput.port_id,
            target_node_id: insertTarget.node_id,
            target_port_id: insertTargetPort.port_id,
            enabled_types: compatibleTypes(sourceOutput, insertTargetPort)
          }
        ]
      : [...workingDraft.edges, edge, ...inheritedEdges];
    setDraft({ ...workingDraft, nodes: [...workingDraft.nodes, node], edges: nextEdges });
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

  function updateSamPrompt(index: number, patch: Partial<SamPromptConfig>) {
    if (!selectedNode || selectedNode.node_type !== "parser") return;
    const prompts = samPromptsForNode(selectedNode);
    prompts[index] = { ...prompts[index], ...patch };
    updateSelectedNodeConfig({ prompts });
  }

  function addSamPrompt() {
    if (!selectedNode || selectedNode.node_type !== "parser") return;
    const prompts = samPromptsForNode(selectedNode);
    const nextId = uniqueSamPromptId(prompts, "prompt");
    updateSelectedNodeConfig({
      prompts: [
        ...prompts,
        {
          id: nextId,
          text: "object",
          confidence_threshold: 0.3
        }
      ]
    });
  }

  function removeSamPrompt(index: number) {
    if (!selectedNode || selectedNode.node_type !== "parser" || readOnly) return;
    const prompts = samPromptsForNode(selectedNode);
    if (prompts.length <= 1) return;
    updateSelectedNodeConfig({ prompts: prompts.filter((_item, itemIndex) => itemIndex !== index) });
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

  function updateAgentOutputFormat(index: number, formatId: string) {
    if (!selectedNode || selectedNode.node_type !== "agent") return;
    const outputs = agentOutputsForNode(selectedNode);
    const current = outputs[index];
    if (!current) return;
    const option = workflowFormatOption(formatId);
    updateAgentOutput(index, {
      format_id: option.format_id,
      type: option.type,
      path: defaultOutputPathForPort(current.port_id, option.format_id),
      description: option.description
    });
  }

  function addAgentOutput() {
    if (!selectedNode || selectedNode.node_type !== "agent") return;
    const portId = uniquePortId(selectedNode, "output");
    const presetId = String(selectedNode.config.preset_id || "custom_agent");
    const defaultOption = presetId === "custom_agent"
      ? workflowFormatOption("drawai.image.v1")
      : presetId === "run0_element_refine"
        ? workflowFormatOption("drawai.codex_element_analysis.v1")
        : workflowFormatOption("drawai.element_plans.v1");
    const output: AgentOutputConfig = {
      port_id: portId,
      path: defaultOutputPathForPort(portId, defaultOption.format_id),
      format_id: defaultOption.format_id,
      type: defaultOption.type,
      description: defaultOption.description
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
      <>
        {workflowDialogPortal}
        <main className="workflow-workspace workflow-library-workspace task-selection-workspace">
          <section className="batch-rail workflow-folder-rail" aria-label="工作流类型">
            <div className="board-panel-head">
              <div>
                <span>工作流类型</span>
                <strong>{visibleWorkflowFolders.length} 个类型</strong>
              </div>
              <button type="button" className="task-submit-button workflow-add-button" title="新建工作流类型" aria-label="新建工作流类型" onClick={openFolderDialog}>
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
                    <em>{folder.builtin ? "内置类型" : "本地分类"}</em>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="case-lane workflow-template-lane">
            <div className="board-panel-head workflow-template-head">
              <div>
                <span>{activeWorkflowFolder.builtin ? "内置工作流" : "工作流"}</span>
                <strong>{activeWorkflowFolder.name}</strong>
              </div>
              <button type="button" className="task-submit-button workflow-add-button" title="新建工作流" aria-label="新建工作流" onClick={openWorkflowDialog}>
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
                  <button type="button" className="task-submit-button workflow-add-button" title="新建工作流" aria-label="新建工作流" onClick={openWorkflowDialog}>
                    <PlusIcon />
                  </button>
                </div>
              )}
            </div>
          </section>
        </main>
      </>
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
            if ((handleDragRef.current || handleDrag)?.pointerId === event.pointerId) {
              handleDragRef.current = null;
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
                  setNodePicker(null);
                  setConnecting(null);
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
                  onClick={(event) => {
                    const target = event.target;
                    if (target instanceof Element && target.closest(".workflow-node-plus, [data-input-port]")) return;
                    setSelectedNodeId(node.node_id);
                    setSelectedEdgeId("");
                    setInspectorOpen(true);
                    setNodePicker(null);
                    setConnecting(null);
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
                        aria-label={`${node.title} ${input.label}`}
                        className={connecting && compatibleTarget(draft, connecting, node, input) ? "compatible" : ""}
                        title={`${input.label}: ${input.types.join(" / ")}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          if (connecting) completeConnection(node.node_id, input.port_id);
                        }}
                      />
                    ))}
                  </div>
                  {sourceOutput && (
                    <button
                      type="button"
                      className={`workflow-node-plus ${connecting?.nodeId === node.node_id && connecting.portId === sourceOutput.port_id ? "connecting" : ""}`}
                      disabled={readOnly || node.node_type === "output"}
                      title={readOnly || node.node_type === "output" ? "不可添加下游节点" : "添加或连接下游节点"}
                      aria-label={readOnly || node.node_type === "output" ? "不可添加下游节点" : "添加或连接下游节点"}
                      onClick={(event) => {
                        event.stopPropagation();
                        if (!readOnly && node.node_type !== "output") openNodePicker(node.node_id, sourceOutput.port_id);
                      }}
                      onPointerDown={(event) => beginOutputHandlePointer(event, node, sourceOutput)}
                      onPointerMove={moveOutputHandlePointer}
                      onPointerUp={endOutputHandlePointer}
                      onPointerCancel={() => {
                        handleDragRef.current = null;
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
                <label className="workflow-picker-search">
                  <span>⌕</span>
                  <input
                    value={nodePicker.query}
                    placeholder="搜索节点"
                    onChange={(event) => setNodePicker({ ...nodePicker, query: event.target.value })}
                  />
                </label>
                <div className="workflow-picker-list">
                  {pickerGroups.map((group) => (
                    <section className="workflow-picker-group" key={group.group}>
                      <h4>{group.group}</h4>
                      {group.items.map((item) => (
                        <button
                          type="button"
                          key={item.preset.key}
                          className={`workflow-picker-item node-${item.preset.node_type} ${item.compatible ? "compatible" : "incompatible"}`}
                          disabled={!item.compatible}
                          title={item.compatible ? item.preset.description : "当前输出没有兼容输入"}
                          onClick={() => addNodeFromPicker(item.preset)}
                        >
                          <span className="workflow-picker-item-icon">
                            <WorkflowNodeIcon nodeType={item.preset.node_type} />
                          </span>
                          <div className="workflow-picker-item-copy">
                            <strong>{item.preset.title}</strong>
                            <em>{item.preset.description}</em>
                          </div>
                        </button>
                      ))}
                    </section>
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
                <span>{nodeTypeLabel(selectedNode.node_type)}</span>
                <strong>{selectedNode.title}</strong>
              </div>
              <button type="button" title="关闭详情" onClick={() => setInspectorOpen(false)}>×</button>
            </div>
            <label className="workflow-field">
              <span>标题</span>
              <input
                value={selectedNode.title}
                disabled={readOnly}
                onChange={(event) => updateNode(selectedNode.node_id, { title: event.target.value })}
              />
            </label>
            <label className="workflow-field">
              <span>描述</span>
              <textarea
                value={selectedNode.description || ""}
                disabled={readOnly}
                rows={2}
                onChange={(event) => updateNode(selectedNode.node_id, { description: event.target.value })}
              />
            </label>

            {selectedNode.node_type === "parser" && (
              <div className="workflow-parser-editor">
                <div className="workflow-inspector-section">
                  <div className="workflow-section-title">
                    <span>解析器</span>
                  </div>
                  <label className="workflow-field">
                    <span>Parser ID</span>
                    <input
                      value={String(selectedNode.config.parser_id || "")}
                      disabled={readOnly}
                      onChange={(event) => updateSelectedNodeConfig({ parser_id: event.target.value })}
                    />
                  </label>
                  <label className="workflow-field">
                    <span>Resource</span>
                    <input
                      value={String(selectedNode.config.resource || "")}
                      disabled={readOnly}
                      onChange={(event) => updateSelectedNodeConfig({ resource: event.target.value })}
                    />
                  </label>
                </div>

                {isSamParserNode(selectedNode) ? (
                  <div className="workflow-inspector-section">
                    <div className="workflow-section-title">
                      <span>SAM Prompts</span>
                      <button type="button" disabled={readOnly} onClick={addSamPrompt}>添加</button>
                    </div>
                    {selectedSamPrompts.map((prompt, index) => (
                      <div className="workflow-sam-prompt" key={`${prompt.id}-${index}`}>
                        <div className="workflow-sam-prompt-grid">
                          <label>
                            <span>ID</span>
                            <input
                              value={prompt.id}
                              disabled={readOnly}
                              onChange={(event) => updateSamPrompt(index, { id: event.target.value })}
                            />
                          </label>
                          <label>
                            <span>阈值</span>
                            <input
                              type="number"
                              min="0"
                              max="1"
                              step="0.01"
                              value={prompt.confidence_threshold}
                              disabled={readOnly}
                              onChange={(event) =>
                                updateSamPrompt(index, {
                                  confidence_threshold: normalizedThreshold(event.target.value, prompt.confidence_threshold)
                                })
                              }
                            />
                          </label>
                        </div>
                        <label>
                          <span>文本</span>
                          <input
                            value={prompt.text}
                            disabled={readOnly}
                            onChange={(event) => updateSamPrompt(index, { text: event.target.value })}
                          />
                        </label>
                        <button type="button" disabled={readOnly || selectedSamPrompts.length <= 1} onClick={() => removeSamPrompt(index)}>
                          删除 Prompt
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="workflow-inspector-section">
                    <p className="workflow-muted">这个解析器当前没有可调 prompt 参数。</p>
                  </div>
                )}
              </div>
            )}

            {selectedNode.node_type === "agent" && (
              <div className="workflow-agent-editor">
                <div className="workflow-inspector-section workflow-agent-runtime">
                  <div className="workflow-section-title">
                    <span>运行设置</span>
                  </div>
                  <div className="workflow-agent-runtime-grid">
                    <label>
                      <span>执行提供方</span>
                      <select
                        value={defaultAgentProvider(selectedNode)}
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
                    <label>
                      <span>模型</span>
                      <input
                        value={String(selectedNode.config.model || "")}
                        disabled={readOnly}
                        placeholder="默认"
                        onChange={(event) => updateSelectedNodeConfig({ model: event.target.value })}
                      />
                    </label>
                    <label>
                      <span>Profile</span>
                      <input
                        value={String(selectedNode.config.profile || "")}
                        disabled={readOnly}
                        placeholder="默认"
                        onChange={(event) => updateSelectedNodeConfig({ profile: event.target.value })}
                      />
                    </label>
                    <label>
                      <span>推理强度</span>
                      <select
                        value={String(selectedNode.config.reasoning_effort || "")}
                        disabled={readOnly}
                        onChange={(event) => updateSelectedNodeConfig({ reasoning_effort: event.target.value })}
                      >
                        <option value="">默认</option>
                        <option value="none">none</option>
                        <option value="minimal">minimal</option>
                        <option value="low">low</option>
                        <option value="medium">medium</option>
                        <option value="high">high</option>
                        <option value="xhigh">xhigh</option>
                      </select>
                    </label>
                    <label>
                      <span>超时秒数</span>
                      <input
                        type="number"
                        min="1"
                        step="1"
                        value={String(selectedNode.config.timeout_seconds || "")}
                        disabled={readOnly}
                        placeholder="默认"
                        onChange={(event) => updateSelectedNodeConfig({ timeout_seconds: event.target.value ? Number(event.target.value) : "" })}
                      />
                    </label>
                  </div>
                </div>

                <div className="workflow-inspector-section">
                  <div className="workflow-section-title">
                    <span>输入文件</span>
                    <strong>{selectedAgentInputs.length}</strong>
                  </div>
                  {selectedAgentInputs.map((input) => {
                    const override = inputOverrideFor(selectedNode, input);
                    const included = override.include !== false;
                    return (
                      <div className="workflow-agent-input" key={inputOverrideKey(input)}>
                        <label className="workflow-agent-input-source">
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
                    <span>输出声明</span>
                    <button type="button" disabled={readOnly} onClick={addAgentOutput}>添加</button>
                  </div>
                  {selectedAgentOutputs.map((output, index) => (
                    <div className="workflow-agent-output" key={`${output.port_id}-${index}`}>
                      <div className="workflow-output-grid">
                        <label>
                          <span>输出端口名</span>
                          <input value={output.port_id} disabled={readOnly} onChange={(event) => updateAgentOutput(index, { port_id: event.target.value })} />
                        </label>
                        <label>
                          <span>数据类型</span>
                          <input value={output.type} disabled={readOnly} onChange={(event) => updateAgentOutput(index, { type: event.target.value })} />
                        </label>
                        <label>
                          <span>文件格式</span>
                          <select value={output.format_id} disabled={readOnly} onChange={(event) => updateAgentOutputFormat(index, event.target.value)}>
                            {WORKFLOW_FORMAT_OPTIONS.map((option) => (
                              <option value={option.format_id} key={option.format_id}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label>
                          <span>输出路径</span>
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
                  <span>任务提示词</span>
                  <textarea
                    rows={5}
                    disabled={readOnly}
                    value={agentTaskText(selectedNode)}
                    onChange={(event) => updateSelectedNodeConfig({ task: event.target.value, prompt_fragments: "", prompt_role: "" })}
                  />
                </label>
                <label className="workflow-field">
                  <span>运行约束</span>
                  <textarea
                    rows={4}
                    disabled={readOnly}
                    value={agentConstraintsText(selectedNode)}
                    onChange={(event) => updateSelectedNodeConfig({ constraints: constraintsFromText(event.target.value) })}
                  />
                </label>
                <div className="workflow-prompt-preview">
                  <div>
                    <span>最终 Prompt</span>
                    <strong>{String(selectedNode.config.provider_id || defaultAgentProvider(selectedNode))}</strong>
                  </div>
                  <pre>{selectedAgentPromptText}</pre>
                </div>
              </div>
            )}

            {selectedNode.node_type === "human_review" && (
              <div className="workflow-inspector-section">
                <div className="workflow-section-title">
                  <span>人工确认界面</span>
                </div>
                <label className="workflow-field">
                  <span>界面</span>
                  <select
                    value={String(selectedNode.config.review_surface || "assets")}
                    disabled={readOnly}
                    onChange={(event) => updateSelectedNodeConfig({ review_surface: event.target.value })}
                  >
                    <option value="assets">资产画布/表格</option>
                    <option value="output">输出可视化</option>
                  </select>
                </label>
                <label className="workflow-field">
                  <span>结果路径</span>
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
                <span>连接端口</span>
              </div>
              {[
                ...selectedNode.inputs.map((portItem) => ({ portItem, direction: "输入" })),
                ...selectedNode.outputs.map((portItem) => ({ portItem, direction: "输出" }))
              ].map(({ portItem, direction }) => (
                <div className="workflow-port-row" key={`${direction}-${portItem.port_id}`}>
                  <span><small>{direction}</small>{portItem.port_id}</span>
                  <em>{portItem.types.join(" / ") || "control"}</em>
                </div>
              ))}
            </div>
            <div className="workflow-node-actions">
              <button type="button" className="danger" disabled={readOnly} onClick={deleteSelectedNode}>
                删除节点
              </button>
            </div>
          </>
        ) : selectedEdge ? (
          <div className="workflow-edge-inspector">
            <div className="workflow-panel-head">
              <div>
                <span>连线</span>
                <strong>{selectedEdge.edge_id}</strong>
              </div>
              <button type="button" title="关闭详情" onClick={() => setInspectorOpen(false)}>×</button>
            </div>
            <dl className="workflow-node-meta">
              <div><dt>来源</dt><dd>{selectedEdge.source_node_id}.{selectedEdge.source_port_id}</dd></div>
              <div><dt>目标</dt><dd>{selectedEdge.target_node_id}.{selectedEdge.target_port_id}</dd></div>
              <div><dt>类型</dt><dd>{selectedEdge.enabled_types.join(" / ") || "自动"}</dd></div>
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
          <g key={edge.edge_id}>
            <path
              className="workflow-edge-hit"
              d={d}
              onClick={(event) => {
                event.stopPropagation();
                onSelectEdge(edge.edge_id);
              }}
              onMouseEnter={() => setHoveredEdgeId(edge.edge_id)}
              onMouseLeave={() => setHoveredEdgeId((current) => (current === edge.edge_id ? "" : current))}
            />
            <path className={`workflow-edge-line ${edge.edge_id === selectedEdgeId ? "selected" : ""}`} d={d} />
          </g>
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
          <PlusIcon />
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

function WorkflowLibraryDialog({
  mode,
  folderName,
  workflowName,
  selectedCopyTemplateId,
  builtinTemplates,
  busy,
  onClose,
  onFolderNameChange,
  onWorkflowNameChange,
  onSelectCopyTemplate,
  onCreateFolder,
  onCopyWorkflow,
  onCreateBlankWorkflow
}: {
  mode: Exclude<WorkflowDialogMode, null>;
  folderName: string;
  workflowName: string;
  selectedCopyTemplateId: string;
  builtinTemplates: WorkflowTemplate[];
  busy: string;
  onClose: () => void;
  onFolderNameChange: (value: string) => void;
  onWorkflowNameChange: (value: string) => void;
  onSelectCopyTemplate: (templateId: string) => void;
  onCreateFolder: () => void;
  onCopyWorkflow: () => void;
  onCreateBlankWorkflow: () => void;
}) {
  if (mode === "folder") {
    return (
      <div className="workflow-modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
        <form
          className="workflow-modal workflow-folder-modal"
          role="dialog"
          aria-modal="true"
          aria-label="新建工作流类型"
          onSubmit={(event) => {
            event.preventDefault();
            onCreateFolder();
          }}
        >
          <div className="workflow-modal-head">
            <div>
              <span>工作流类型</span>
              <strong>新建文件夹</strong>
            </div>
            <button type="button" aria-label="关闭" onClick={onClose}>×</button>
          </div>
          <label className="workflow-modal-field">
            <span>名称</span>
            <input value={folderName} autoFocus placeholder="例如：实验工作流" onChange={(event) => onFolderNameChange(event.target.value)} />
          </label>
          <div className="workflow-modal-actions">
            <button type="button" onClick={onClose}>取消</button>
            <button type="submit" className="primary" disabled={!folderName.trim()}>创建</button>
          </div>
        </form>
      </div>
    );
  }

  return (
    <div className="workflow-modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="workflow-modal workflow-template-modal" role="dialog" aria-modal="true" aria-label="新建工作流">
        <div className="workflow-modal-head">
          <div>
            <span>工作流</span>
            <strong>新建工作流</strong>
          </div>
          <button type="button" aria-label="关闭" onClick={onClose}>×</button>
        </div>
        <label className="workflow-modal-field">
          <span>名称</span>
          <input value={workflowName} autoFocus placeholder="留空则使用默认名称" onChange={(event) => onWorkflowNameChange(event.target.value)} />
        </label>
        <div className="workflow-template-source-list" aria-label="默认工作流">
          {builtinTemplates.map((template) => {
            const stats = workflowNodeStats(template);
            const selected = selectedCopyTemplateId === template.template_id;
            return (
              <button
                type="button"
                key={template.template_id}
                className={selected ? "selected" : ""}
                aria-pressed={selected}
                onClick={() => onSelectCopyTemplate(selected ? "" : template.template_id)}
              >
                <div className="workflow-template-source-preview">
                  <WorkflowTemplatePreview template={template} />
                </div>
                <div>
                  <strong>{template.name}</strong>
                  <span>{template.description || "DrawAI workflow"}</span>
                  <em>{template.nodes.length} 节点 · {template.edges.length} 连线 · {stats.agent} Agent</em>
                </div>
              </button>
            );
          })}
          {builtinTemplates.length === 0 && <p>没有可复制的默认工作流。</p>}
        </div>
        <div className="workflow-modal-actions workflow-template-modal-actions">
          <button type="button" disabled={!selectedCopyTemplateId || busy === "copy"} onClick={onCopyWorkflow}>
            复制工作流
          </button>
          <button type="button" className="primary" onClick={onCreateBlankWorkflow}>
            新建工作流
          </button>
        </div>
      </section>
    </div>
  );
}

function nodePickerItems(template: WorkflowTemplate, picker: NodePickerState): NodePickerItem[] {
  const source = template.nodes.find((node) => node.node_id === picker.sourceNodeId);
  const sourcePort = source?.outputs.find((portItem) => portItem.port_id === picker.sourcePortId);
  const target = template.nodes.find((node) => node.node_id === picker.targetNodeId);
  const targetPort = target?.inputs.find((portItem) => portItem.port_id === picker.targetPortId);
  const query = picker.query.trim().toLowerCase();
  return NODE_PRESETS
    .filter((preset) => {
      if (preset.node_type === "input") return false;
      if (!query) return true;
      return [preset.title, preset.node_type, preset.description, nodePresetGroup(preset)].some((value) => value.toLowerCase().includes(query));
    })
    .map((preset) => ({
      preset,
      compatible: Boolean(
        sourcePort
        && bestInputForPreset(sourcePort, preset)
        && (!picker.insertEdgeId || presetCanOutputToTarget(preset, targetPort))
      ),
      group: nodePresetGroup(preset)
    }));
}

function nodePickerGroups(items: NodePickerItem[]): NodePickerGroup[] {
  const grouped = new Map<string, NodePickerItem[]>();
  items.forEach((item) => {
    grouped.set(item.group, [...(grouped.get(item.group) || []), item]);
  });
  return [...grouped.entries()]
    .sort(([left], [right]) => nodePickerGroupRank(left) - nodePickerGroupRank(right))
    .map(([group, groupItems]) => ({ group, items: groupItems }));
}

function nodePickerGroupRank(group: string): number {
  const index = NODE_PICKER_GROUP_ORDER.indexOf(group);
  return index === -1 ? NODE_PICKER_GROUP_ORDER.length : index;
}

function nodePresetGroup(preset: NodePreset): string {
  if (preset.node_type === "parser") return "Parser";
  if (preset.node_type === "agent") return "Agent";
  if (preset.node_type === "processor") return "Processor";
  if (preset.node_type === "fusion") return "Fusion";
  if (preset.node_type === "human_review") return "Review";
  if (preset.node_type === "export" || preset.node_type === "output") return "Export";
  return "Other";
}

function isSamParserNode(node: WorkflowNode): boolean {
  return node.node_type === "parser" && String(node.config.parser_id || "") === "sam3_structure_parser";
}

function samPromptsForNode(node: WorkflowNode): SamPromptConfig[] {
  const raw = node.config.prompts;
  if (!Array.isArray(raw)) return cloneJson(DEFAULT_SAM_PROMPTS);
  const prompts = raw
    .filter((item) => item && typeof item === "object")
    .map((item, index) => {
      const data = item as Record<string, unknown>;
      return {
        id: String(data.id || `prompt_${index + 1}`),
        text: String(data.text || ""),
        confidence_threshold: normalizedThreshold(data.confidence_threshold, 0.3)
      };
    })
    .filter((item) => item.id.trim() || item.text.trim());
  return prompts.length > 0 ? prompts : cloneJson(DEFAULT_SAM_PROMPTS);
}

function uniqueSamPromptId(prompts: SamPromptConfig[], base: string): string {
  const existing = new Set(prompts.map((prompt) => prompt.id));
  let candidate = base;
  let index = prompts.length + 1;
  while (existing.has(candidate)) {
    candidate = `${base}_${index}`;
    index += 1;
  }
  return candidate;
}

function normalizedThreshold(value: unknown, fallback: number): number {
  const numberValue = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numberValue)) return fallback;
  return clamp(numberValue, 0, 1);
}

function agentPresetId(node: WorkflowNode): string {
  return String(node.config.preset_id || "custom_agent");
}

function defaultAgentProvider(node: WorkflowNode): string {
  return String(node.config.provider_id || "codex_sdk");
}

function agentTaskText(node: WorkflowNode): string {
  const raw =
    configText(node.config.task)
    || configText(node.config.prompt_role)
    || configText(node.config.prompt_fragments)
    || configText(node.config.user_prompt);
  return raw || AGENT_DEFAULT_TASKS[agentPresetId(node)] || "";
}

function agentConstraints(node: WorkflowNode): string[] {
  const raw = node.config.constraints;
  if (raw === undefined) return [];
  if (Array.isArray(raw)) return raw.filter((item) => typeof item === "string").map((item) => item.trim()).filter(Boolean);
  if (typeof raw === "string") return constraintsFromText(raw);
  return [];
}

function agentConstraintsText(node: WorkflowNode): string {
  return agentConstraints(node).join("\n");
}

function constraintsFromText(text: string): string[] {
  return text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
}

function configText(value: unknown): string {
  if (Array.isArray(value)) return value.filter((item) => typeof item === "string").join("\n\n").trim();
  return typeof value === "string" ? value.trim() : "";
}

function selectedInputsForPrompt(node: WorkflowNode, inputs: AgentInputPreview[]): AgentInputPreview[] {
  const selected: AgentInputPreview[] = [];
  inputs.forEach((input) => {
    const override = inputOverrideFor(node, input);
    if (override.include === false) return;
    selected.push({
      ...input,
      description: typeof override.description === "string" ? override.description : input.description
    });
  });
  return selected;
}

function agentRuntimeOptionsForNode(node: WorkflowNode): Array<[string, string]> {
  return (["model", "profile", "timeout_seconds", "reasoning_effort"] as const)
    .map((key): [string, string] | null => {
      const value = node.config[key];
      if (value === undefined || value === null || value === "") return null;
      return [key, String(value)];
    })
    .filter((item): item is [string, string] => Boolean(item));
}

function workflowAgentPromptText(node: WorkflowNode, inputs: AgentInputPreview[]): string {
  const providerId = defaultAgentProvider(node);
  const selectedInputs = selectedInputsForPrompt(node, inputs);
  const outputs = agentOutputsForNode(node);
  const constraints = agentConstraints(node);
  const options = agentRuntimeOptionsForNode(node);
  const lines = [
    "## Agent Runtime Settings",
    `- Provider: ${providerId}`,
    "- Workflow run root: <workflow_run_root>",
    `- Current node workdir: <workflow_run_root>/nodes/${node.node_id}/runs/<attempt_id>`,
    `- Agent process cwd: <workflow_run_root>/nodes/${node.node_id}/runs/<attempt_id>`,
    "- Repository root: <repository_root>",
    "- Input manifest path: input_manifest.json",
    "- Node run manifest path: node_run.json",
    ...options.map(([key, value]) => `- ${key}: ${value}`),
    "",
    "## Task",
    agentTaskText(node),
    "",
    "## Connected Input Files",
    "The DrawAI harness records every connected input in input_manifest.json inside the current node workdir. Use the node-workdir-relative path when opening files from the Agent process."
  ];

  if (selectedInputs.length > 0) {
    selectedInputs.forEach((input) => {
      lines.push(
        `- Source: ${inputSourceLabel(input)}`,
        `  Format: ${String(input.format_id || "unspecified")}`,
        `  Type: ${String(input.type || "unspecified")}`,
        `  Run-root path: ${String(input.path || "")}`,
        `  Absolute path: ${inputAbsolutePath(String(input.path || ""))}`,
        `  From Agent cwd: ${inputPathFromNodeWorkdir(String(input.path || ""))}`,
        `  Description: ${String(input.description || "No description supplied.")}`
      );
    });
  } else {
    lines.push("- No connected input files were provided.");
  }

  lines.push(
    "",
    "## Declared Output Files",
    "Write exactly these files relative to the Agent process cwd. The harness resolves and records them in node_run.json after the run."
  );
  outputs.forEach((output) => {
    lines.push(
      `- Port: ${output.port_id}`,
      `  Format: ${output.format_id}`,
      `  Type: ${output.type}`,
      `  Write path from Agent cwd: ${output.path}`,
      `  Final run-root path: ${outputPathFromRunRoot(node.node_id, output.path)}`,
      `  Final absolute path: ${outputAbsolutePath(node.node_id, output.path)}`,
      `  Description: ${output.description}`
    );
  });

  const scripts = agentScriptsForNode(node);
  if (scripts.length > 0) {
    lines.push(
      "",
      "## Built-in Script Files",
      "These scripts are explicitly available to this Agent node. Use them only when they help produce the declared outputs, and keep all generated files inside the current node workdir unless an output declaration says otherwise."
    );
    scripts.forEach((script) => {
      const path = String(script.path || "");
      const usage = String(script.usage || "").replace("{script}", path);
      lines.push(
        `- Script: ${String(script.script_id || script.id || "script")}`,
        `  Repository path: ${path}`,
        `  From Agent cwd: ${path}`,
        `  Description: ${String(script.description || "No description supplied.")}`
      );
      if (usage) lines.push(`  Usage: ${usage}`);
    });
  }

  lines.push("", "## Type And Format Contracts");
  orderedUnique([
    ...selectedInputs.map((input) => String(input.type || "")),
    ...outputs.map((output) => output.type)
  ]).forEach((typeName) => {
    lines.push(`- Type \`${typeName}\`: ${WORKFLOW_TYPE_CONTRACTS[typeName] || "No built-in type description is registered. Follow the node description and connected file contents."}`);
  });
  orderedUnique([
    ...selectedInputs.map((input) => String(input.format_id || "")),
    ...outputs.map((output) => output.format_id)
  ]).forEach((formatId) => {
    lines.push(`- Format \`${formatId}\`: ${WORKFLOW_FORMAT_CONTRACTS[formatId] || "No built-in format description is registered. Follow the node declaration and validate the file before returning."}`);
  });

  if (constraints.length > 0) {
    lines.push("", "## Constraints");
    constraints.forEach((constraint) => lines.push(`- ${constraint}`));
  }

  return `${lines.join("\n").trim()}\n`;
}

function agentScriptsForNode(node: WorkflowNode): Array<Record<string, unknown>> {
  const raw = node.config.scripts;
  if (!Array.isArray(raw)) return [];
  return raw.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object");
}

function inputPathFromNodeWorkdir(path: string): string {
  if (!path) return "";
  if (path.startsWith("/")) return path;
  return `../../../${stripCurrentDirPrefix(path)}`;
}

function inputAbsolutePath(path: string): string {
  if (!path) return "";
  if (path.startsWith("/")) return path;
  return `<workflow_run_root>/${stripCurrentDirPrefix(path)}`;
}

function outputPathFromRunRoot(nodeId: string, path: string): string {
  if (!path) return "";
  if (path.startsWith("/")) return path;
  return `nodes/${nodeId}/runs/<attempt_id>/${stripCurrentDirPrefix(path)}`;
}

function outputAbsolutePath(nodeId: string, path: string): string {
  if (!path) return "";
  if (path.startsWith("/")) return path;
  return `<workflow_run_root>/${outputPathFromRunRoot(nodeId, path)}`;
}

function stripCurrentDirPrefix(path: string): string {
  return path.startsWith("./") ? path.slice(2) : path;
}

function orderedUnique(values: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  values.forEach((value) => {
    const clean = value.trim();
    if (!clean || seen.has(clean)) return;
    seen.add(clean);
    result.push(clean);
  });
  return result;
}

function inputSourceLabel(input: AgentInputPreview): string {
  const sourceNode = String(input.source_node_id || "");
  const sourcePort = String(input.source_port_id || "");
  if (sourceNode && sourcePort) return `${sourceNode}.${sourcePort}`;
  return sourceNode || "connected input";
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

function nodeTypeLabel(nodeType: string): string {
  const labels: Record<string, string> = {
    input: "输入",
    parser: "解析器",
    fusion: "融合",
    agent: "智能体",
    processor: "处理器",
    human_review: "人工确认",
    export: "导出",
    output: "输出"
  };
  return labels[nodeType] || nodeType;
}

function PlusIcon() {
  return (
    <svg className="plus-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

function WorkflowTemplatePreview({ template }: { template: WorkflowTemplate }) {
  const layout = buildWorkflowPreviewLayout(template, {
    nodeWidth: 128,
    nodeHeight: 50,
    columnGap: 46,
    rowGap: 66,
    nodeGap: 18,
    paddingX: 18,
    paddingY: 16
  });
  return (
    <div className="workflow-template-preview" aria-hidden="true">
      <svg viewBox={`0 0 ${layout.width} ${layout.height}`} preserveAspectRatio="xMidYMid meet">
        {layout.edges.map((edgeLayout) => (
          <path key={edgeLayout.edge.edge_id} d={edgeLayout.d} />
        ))}
        {layout.nodes.map((nodeLayout) => (
          <rect
            key={nodeLayout.node.node_id}
            className={`node-${nodeLayout.node.node_type}`}
            x={nodeLayout.x}
            y={nodeLayout.y}
            width={nodeLayout.width}
            height={nodeLayout.height}
            rx="8"
          />
        ))}
      </svg>
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

function blankWorkflowTemplate(templateId: string, name: string, folderId: string): WorkflowTemplate {
  return {
    schema: WORKFLOW_TEMPLATE_SCHEMA,
    template_id: templateId,
    name,
    description: "Blank workflow with a source image input.",
    version: 1,
    nodes: [
      {
        node_id: "input",
        node_type: "input",
        title: "Input",
        inputs: [],
        outputs: [port("image", "Image", ["image"], "drawai.image.v1", false)],
        config: {},
        position: { x: 0, y: 160 },
        description: "Source image input."
      }
    ],
    edges: [],
    defaults: {
      builtin: false,
      read_only: false,
      folder_id: folderId
    }
  };
}

function uniqueTemplateId(templates: WorkflowTemplate[], base: string): string {
  const existing = new Set(templates.map((template) => template.template_id));
  const seed = `${base}_${Date.now().toString(36)}`;
  let candidate = seed;
  let index = 2;
  while (existing.has(candidate)) {
    candidate = `${seed}_${index}`;
    index += 1;
  }
  return candidate;
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
    const columnX = 92 + layerIndex * NODE_COLUMN_SPACING;
    const startY = Math.max(92, 260 - Math.round((nodes.length - 1) * (NODE_ROW_SPACING / 2)));
    nodes.forEach((node, rowIndex) => {
      positionByNodeId.set(node.node_id, { x: columnX, y: startY + rowIndex * NODE_ROW_SPACING });
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

function presetCanOutputToTarget(preset: NodePreset, targetPort?: WorkflowPort): boolean {
  if (!targetPort) return false;
  return Boolean(bestOutputForTarget(preset, targetPort) || (isCustomAgentPreset(preset) && targetPort.types.length > 0));
}

function isCustomAgentPreset(preset: NodePreset): boolean {
  return preset.key === "custom-agent" || preset.config?.preset_id === "custom_agent";
}

function isCustomAgentNode(node: WorkflowNode): boolean {
  return node.node_type === "agent" && node.config.preset_id === "custom_agent";
}

function outputPortForTarget(targetPort: WorkflowPort): WorkflowPort {
  const firstType = targetPort.types[0] || "image";
  const option = workflowFormatOptionForType(firstType);
  return port(
    safePortId(option.type || targetPort.port_id || "output"),
    option.label,
    [option.type],
    option.format_id,
    false,
    "single",
    option.description
  );
}

function customizeCustomAgentNode(node: WorkflowNode, replacementOutput?: WorkflowPort | null): WorkflowNode {
  if (!isCustomAgentNode(node)) return node;
  const outputs = replacementOutput ? [replacementOutput] : node.outputs;
  return {
    ...node,
    outputs,
    config: {
      ...node.config,
      outputs: outputs.map((output) => agentOutputConfigForPort(output))
    }
  };
}

function inheritedCustomAgentInputEdges(
  template: WorkflowTemplate,
  source: WorkflowNode,
  target: WorkflowNode,
  targetPort: WorkflowPort,
  reservedEdgeIds: Set<string>
): WorkflowEdge[] {
  if (!isCustomAgentNode(target)) return [];
  const seenConnections = new Set<string>();
  return template.edges
    .filter((edge) => edge.target_node_id === source.node_id)
    .flatMap((edge) => {
      const upstream = template.nodes.find((node) => node.node_id === edge.source_node_id);
      const upstreamPort = upstream?.outputs.find((portItem) => portItem.port_id === edge.source_port_id);
      if (!upstream || !upstreamPort) return [];
      const overlap = compatibleTypes(upstreamPort, targetPort);
      if (overlap.length === 0) return [];
      const connectionKey = `${upstream.node_id}:${upstreamPort.port_id}->${target.node_id}:${targetPort.port_id}`;
      if (seenConnections.has(connectionKey)) return [];
      seenConnections.add(connectionKey);
      return [
        {
          edge_id: uniqueEdgeIdFromSet(reservedEdgeIds, connectionKey),
          source_node_id: upstream.node_id,
          source_port_id: upstreamPort.port_id,
          target_node_id: target.node_id,
          target_port_id: targetPort.port_id,
          enabled_types: overlap
        }
      ];
    });
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
  const defaultPosition = { x: 100 + (index % 4) * NODE_DEFAULT_GRID_X, y: 100 + Math.floor(index / 4) * NODE_DEFAULT_GRID_Y };
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
  const baseX = (source.position.x || 0) + NODE_COLUMN_SPACING;
  const sourceY = source.position.y || 0;
  const occupied = new Set(template.nodes.map((node) => `${Math.round((node.position.x || 0) / 20)}:${Math.round((node.position.y || 0) / 20)}`));
  for (let offset = 0; offset < 8; offset += 1) {
    const y = Math.max(16, sourceY + offset * NODE_ROW_SPACING);
    const key = `${Math.round(baseX / 20)}:${Math.round(y / 20)}`;
    if (!occupied.has(key)) return { x: baseX, y };
  }
  return { x: baseX, y: sourceY + NODE_ROW_SPACING };
}

function workflowInsertionLayout(
  template: WorkflowTemplate,
  source: WorkflowNode,
  target: WorkflowNode
): { nodes: WorkflowNode[]; target: WorkflowNode; position: { x: number; y: number } } {
  const sourceX = source.position.x || 0;
  const targetX = target.position.x || 0;
  const minimumTargetX = sourceX + NODE_COLUMN_SPACING * 2;
  const shiftX = Math.max(0, minimumTargetX - targetX);
  const nodes = shiftX > 0 ? shiftWorkflowBranchNodes(template.nodes, template.edges, target.node_id, shiftX) : template.nodes;
  const shiftedTarget = nodes.find((node) => node.node_id === target.node_id) || target;
  return {
    nodes,
    target: shiftedTarget,
    position: suggestedInsertedNodePosition({ ...template, nodes }, source, shiftedTarget)
  };
}

function shiftWorkflowBranchNodes(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[],
  rootNodeId: string,
  shiftX: number
): WorkflowNode[] {
  const branchNodeIds = downstreamNodeIds(edges, rootNodeId);
  return nodes.map((node) =>
    branchNodeIds.has(node.node_id)
      ? { ...node, position: { ...node.position, x: Math.max(0, (node.position.x || 0) + shiftX) } }
      : node
  );
}

function downstreamNodeIds(edges: WorkflowEdge[], rootNodeId: string): Set<string> {
  const outgoing = new Map<string, string[]>();
  edges.forEach((edge) => {
    outgoing.set(edge.source_node_id, [...(outgoing.get(edge.source_node_id) || []), edge.target_node_id]);
  });
  const seen = new Set<string>();
  const queue = [rootNodeId];
  for (let cursor = 0; cursor < queue.length; cursor += 1) {
    const nodeId = queue[cursor];
    if (seen.has(nodeId)) continue;
    seen.add(nodeId);
    (outgoing.get(nodeId) || []).forEach((targetId) => {
      if (!seen.has(targetId)) queue.push(targetId);
    });
  }
  return seen;
}

function suggestedInsertedNodePosition(
  template: WorkflowTemplate,
  source: WorkflowNode,
  target: WorkflowNode
): { x: number; y: number } {
  const baseX = Math.max(0, Math.round(((source.position.x || 0) + (target.position.x || 0)) / 2));
  const baseY = Math.max(0, Math.round(((source.position.y || 0) + (target.position.y || 0)) / 2));
  const occupied = new Set(
    template.nodes
      .filter((n) => n.node_id !== source.node_id && n.node_id !== target.node_id)
      .map((n) => `${Math.round((n.position.x || 0) / 20)}:${Math.round((n.position.y || 0) / 20)}`)
  );
  for (let offset = 0; offset < 12; offset += 1) {
    const y = Math.max(16, baseY + (offset % 2 === 0 ? 1 : -1) * Math.ceil(offset / 2) * NODE_INSERT_COLLISION_STEP);
    const key = `${Math.round(baseX / 20)}:${Math.round(y / 20)}`;
    if (!occupied.has(key)) return { x: baseX, y };
  }
  return { x: baseX, y: baseY + NODE_INSERT_COLLISION_STEP };
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
  return uniqueEdgeIdFromSet(new Set(template.edges.map((edge) => edge.edge_id)), base);
}

function uniqueEdgeIdFromSet(existing: Set<string>, base: string): string {
  let candidate = base;
  let index = 2;
  while (existing.has(candidate)) {
    candidate = `${base}#${index}`;
    index += 1;
  }
  existing.add(candidate);
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

function defaultOutputPathForPort(portId: string, formatId: string): string {
  return `output/${portId}.${fileExtensionForFormat(formatId)}`;
}

function agentOutputConfigForPort(output: WorkflowPort): AgentOutputConfig {
  const formatId = output.formats[0] || workflowFormatOptionForType(output.types[0] || "image").format_id;
  const option = workflowFormatOption(formatId);
  return {
    port_id: output.port_id,
    path: defaultOutputPathForPort(output.port_id, option.format_id),
    format_id: option.format_id,
    type: output.types[0] || option.type,
    description: output.description || option.description
  };
}

function workflowFormatOption(formatId: string): WorkflowFormatOption {
  return WORKFLOW_FORMAT_OPTIONS.find((option) => option.format_id === formatId) || WORKFLOW_FORMAT_OPTIONS[0];
}

function workflowFormatOptionForType(type: string): WorkflowFormatOption {
  return WORKFLOW_FORMAT_OPTIONS.find((option) => option.type === type) || WORKFLOW_FORMAT_OPTIONS[0];
}

function safePortId(value: string): string {
  return value.trim().toLowerCase().replace(/[^a-z0-9_]+/g, "_").replace(/^_+|_+$/g, "") || "output";
}

function fileExtensionForFormat(formatId: string): string {
  if (formatId.includes("svg")) return "svg";
  if (formatId.includes("pptx")) return "pptx";
  if (formatId.includes("image")) return "png";
  return "json";
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
