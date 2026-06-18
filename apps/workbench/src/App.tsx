import { DragEvent, MouseEvent, PointerEvent, WheelEvent, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  approveAssets,
  composeV2Case,
  createUploadBatch,
  deleteBatch,
  downloadBatchPptx,
  forkV2FromSource,
  getAssetPackage,
  getAssets,
  getBatch,
  getCase,
  getCaseArtifacts,
  getCaseProgress,
  getElements,
  getHealth,
  getRunPackage,
  getSvgSource,
  isDrawAiApiStatus,
  listBatches,
  processAssetElements,
  processV2Asset,
  renameBatch,
  runCaseStage,
  runBatch,
  saveAssetDraft,
  setActiveAssetResult,
  type WorkbenchRerunStage,
} from "./api";
import ImageGenStudio, { type ImageGenConnectionSettings } from "./ImageGenStudio";
import type {
  ArtifactRecord,
  AssetElement,
  AssetGeometry,
  AssetPlan,
  BatchDetail,
  BatchRecord,
  CaseDetail,
  CaseRecord,
  CaseProgress,
  HealthResponse,
  RuntimeActivityStatus,
  RuntimeServiceStatus,
  SourceStrategy,
  StageRunRecord,
  RunCompatibilityMode,
  V2AssetPackage,
  V2AssetResult,
  V2AssetStatus,
  V2ElementPlan,
  V2RunPackage
} from "./types";

type AppView = "board" | "editor" | "svg";
type BoardMode = "generate" | "process";
type CanvasMode = "select" | "add" | "polygon";
type AssetEditorView = "extraction" | "processing";
type PipelineNodeState = "waiting" | "running" | "done" | "failed" | "review" | "stale";
type AssetPlanChangeOptions = { track?: boolean };
type V2ProcessorType = "crop" | "crop_nobg" | "image_generate" | "image_edit" | "chart_rebuild_reserved";
type SvgEditableElement = { path: string; tag: string; label: string; detail: string; text: string; textEditable: boolean };
type SvgDragState =
  | { kind: "move"; path: string; baseText: string; startClientX: number; startClientY: number; scaleX: number; scaleY: number }
  | { kind: "resize"; path: string; baseText: string; center: { x: number; y: number } | null; startClientX: number; startClientY: number; startDistance: number };
type SvgPreviewModel = { svg: string; elements: SvgEditableElement[]; error: string };
type SvgSelectionOverlay = { left: number; top: number; width: number; height: number; centerClientX: number; centerClientY: number };
type TaskContextMenuState = { caseId: string; caseName: string; x: number; y: number };
type BatchContextMenuState = { batchId: string; batchName: string; caseCount: number; running: boolean; x: number; y: number };
type TaskDialogTarget = { batchId: string; name: string };
type DragState =
  | { kind: "move"; id: string; startX: number; startY: number; bbox: [number, number, number, number]; geometry?: AssetGeometry }
  | { kind: "resize"; id: string; handle: string; startX: number; startY: number; bbox: [number, number, number, number]; geometry?: AssetGeometry }
  | { kind: "add"; startX: number; startY: number; currentX: number; currentY: number };
type RuntimeStatusRow = {
  key: string;
  label: string;
  online: boolean;
  statusLabel: string;
  detail: string;
  activity: RuntimeActivityStatus;
};
type SelectedUploadFile = { file: File; relativePath: string };
type UploadPreviewImage = { name: string; source: string; kind: "image" | "zip" };
type UploadConfirmation = {
  files: SelectedUploadFile[];
  images: UploadPreviewImage[];
  zipErrors: string[];
  title: string;
};
type BrowserFileSystemEntry = {
  isFile: boolean;
  isDirectory: boolean;
  name: string;
  fullPath?: string;
};
type BrowserFileSystemFileEntry = BrowserFileSystemEntry & {
  file: (success: (file: File) => void, failure?: (error: DOMException) => void) => void;
};
type BrowserFileSystemDirectoryEntry = BrowserFileSystemEntry & {
  createReader: () => {
    readEntries: (success: (entries: BrowserFileSystemEntry[]) => void, failure?: (error: DOMException) => void) => void;
  };
};
type BrowserDataTransferItem = DataTransferItem & {
  webkitGetAsEntry?: () => BrowserFileSystemEntry | null;
};

const IMAGEGEN_SETTINGS_STORAGE_KEY = "drawai.imagegen.connection";
const PPTX_EXPORT_POLL_INTERVAL_MS = 1000;
const PPTX_EXPORT_TIMEOUT_MS = 180_000;
const DEFAULT_IMAGEGEN_CONNECTION: ImageGenConnectionSettings = {
  provider: "api",
  baseUrl: "",
  apiKey: "",
  model: "gpt-image-2"
};

const strategyLabels: Record<SourceStrategy, string> = {
  svg_self_draw: "SVG",
  crop: "保留背景",
  crop_nobg: "去背景"
};

const strategyClass: Record<SourceStrategy, string> = {
  svg_self_draw: "strategy-svg",
  crop: "strategy-crop",
  crop_nobg: "strategy-nobg"
};

const EDITOR_SOURCE_STRATEGIES = ["crop", "crop_nobg"] as const;
type EditorSourceStrategy = (typeof EDITOR_SOURCE_STRATEGIES)[number];
type AssetProcessingMode = EditorSourceStrategy | "gen";

const ASSET_PROCESSING_MODES: Array<{ mode: AssetProcessingMode; label: string; disabled?: boolean }> = [
  { mode: "crop", label: "保留背景" },
  { mode: "crop_nobg", label: "去背景" },
  { mode: "gen", label: "生成", disabled: true }
];
const V2_PROCESSABLE_PROCESSORS: V2ProcessorType[] = ["crop", "crop_nobg", "image_generate", "image_edit"];
const SUPPORTED_UPLOAD_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp", ".zip"];
const WORKBENCH_PROCESSING_APPLIED_REASON = "工作台处理结果为";
const WORKBENCH_PROCESSING_MODE_REASON = "工作台处理模式设为";

const PIPELINE_GROUPS = [
  {
    title: "元素解析",
    subtitle: "统一输入并融合解析器结果",
    nodes: [
      { stage: "prepare", title: "准备输入", detail: "统一画布", description: "归一化源图像和画布尺寸，生成 v2 run 的基础运行上下文。" },
      { stage: "parse_elements", title: "元素解析", detail: "SAM / OCR", description: "调用一个或多个解析器，输出统一格式的候选元素。" },
      { stage: "fuse_elements", title: "候选融合", detail: "优先级 / NMS", description: "按融合规则合并候选框，保留来源、置信度和几何信息。" }
    ]
  },
  {
    title: "Assets 规划",
    subtitle: "校正类型并生成资产计划",
    nodes: [
      { stage: "refine_elements", title: "Agent 校验", detail: "可选 refine", description: "可选地用 Agent 校正元素位置、大小和类型。" },
      { stage: "plan_assets", title: "资产计划", detail: "处理意图", description: "为每个元素写入处理类型和资产初始状态。" },
      { stage: "process_assets", title: "资产处理", detail: "裁剪 / 去背景 / 生成", description: "按元素级处理器写入可追踪结果，单个资产失败不会吞掉错误。" }
    ]
  },
  {
    title: "可编辑输出",
    subtitle: "组合、导出并封装运行包",
    nodes: [
      { stage: "compose_svg", title: "SVG 组合", detail: "可编辑重建", description: "基于 active asset result 组合可编辑 SVG 与预览图。" },
      { stage: "export", title: "PPT 导出", detail: "PPTX", description: "将 SVG 输出为 PPTX；默认拒绝 failed / unsupported 资产。" },
      { stage: "package_run", title: "运行包封装", detail: "完整数据包", description: "保留最终渲染结果、资产记录和后续可修改的运行上下文。" }
    ]
  }
] as const;

const PIPELINE_STAGE_ORDER = [
  "prepare",
  "parse_elements",
  "fuse_elements",
  "refine_elements",
  "plan_assets",
  "process_assets",
  "compose_svg",
  "export",
  "package_run"
] as const;

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState("");
  const [batches, setBatches] = useState<BatchRecord[]>([]);
  const [activeBatch, setActiveBatch] = useState<BatchDetail | null>(null);
  const [activeCase, setActiveCase] = useState<CaseDetail | null>(null);
  const [caseProgress, setCaseProgress] = useState<CaseProgress | null>(null);
  const [assetPlan, setAssetPlan] = useState<AssetPlan | null>(null);
  const [undoStack, setUndoStack] = useState<AssetPlan[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState("");
  const [runPackage, setRunPackage] = useState<V2RunPackage | null>(null);
  const [runCompatibility, setRunCompatibility] = useState<RunCompatibilityMode>("none");
  const [canForkV2FromSource, setCanForkV2FromSource] = useState(false);
  const [v2Elements, setV2Elements] = useState<V2ElementPlan[]>([]);
  const [selectedV2ElementId, setSelectedV2ElementId] = useState("");
  const [selectedAssetPackage, setSelectedAssetPackage] = useState<V2AssetPackage | null>(null);
  const [v2PackageError, setV2PackageError] = useState("");
  const [v2AssetLoadingElementId, setV2AssetLoadingElementId] = useState("");
  const [v2ActionPending, setV2ActionPending] = useState("");
  const [activeView, setActiveView] = useState<AppView>("board");
  const [boardMode, setBoardMode] = useState<BoardMode>("process");
  const [submitOpen, setSubmitOpen] = useState(false);
  const [imageGenSettingsOpen, setImageGenSettingsOpen] = useState(false);
  const [imageGenConnection, setImageGenConnection] = useState<ImageGenConnectionSettings>(() => loadImageGenConnectionSettings());
  const [error, setError] = useState("");
  const [assetsRunPendingCaseId, setAssetsRunPendingCaseId] = useState("");
  const [pptxExportPendingCaseId, setPptxExportPendingCaseId] = useState("");
  const [batchPptxDownloadPendingId, setBatchPptxDownloadPendingId] = useState("");
  const [batchRunPendingId, setBatchRunPendingId] = useState("");
  const [taskRenameTarget, setTaskRenameTarget] = useState<TaskDialogTarget | null>(null);
  const [taskDeleteTarget, setTaskDeleteTarget] = useState<TaskDialogTarget | null>(null);
  const autoSelectedBatchId = useRef("");

  async function refreshBatches(): Promise<BatchRecord[]> {
    const response = await listBatches();
    setBatches(response.batches);
    return response.batches;
  }

  async function refreshHealth() {
    try {
      const response = await getHealth();
      setHealth(response);
      setHealthError("");
    } catch (err) {
      setHealth(null);
      setHealthError(err instanceof Error ? err.message : String(err));
    }
  }

  async function selectBatch(batchId: string): Promise<BatchDetail> {
    const detail = await getBatch(batchId);
    setActiveBatch(detail);
    if (detail.cases.length > 0 && !detail.cases.some((item) => item.case_id === activeCase?.case.case_id)) {
      await selectCase(detail.cases[0].case_id);
    }
    return detail;
  }

  function applyAssetPlan(plan: AssetPlan, preferredAssetId = "") {
    setAssetPlan(plan);
    setSelectedAssetId(
      preferredAssetId && plan.elements.some((element) => element.box_id === preferredAssetId)
        ? preferredAssetId
        : plan.elements.find((element) => isEditorSourceStrategy(element.source_strategy))?.box_id || plan.elements[0]?.box_id || ""
    );
  }

  function mergeCaseStatus(caseRecord: CaseRecord) {
    setActiveCase((current) => {
      if (!current || current.case.case_id !== caseRecord.case_id) return current;
      return { ...current, case: { ...current.case, ...caseRecord } };
    });
    setCaseProgress((current) => {
      if (!current || current.case.case_id !== caseRecord.case_id) return current;
      return { ...current, case: { ...current.case, ...caseRecord } };
    });
    setActiveBatch((current) => {
      if (!current || current.batch.batch_id !== caseRecord.batch_id) return current;
      return {
        ...current,
        cases: current.cases.map((item) => (item.case_id === caseRecord.case_id ? { ...item, ...caseRecord } : item))
      };
    });
  }

  async function loadAssetsForCase(caseId: string, preferredAssetId = ""): Promise<AssetPlan> {
    const assets = await getAssets(caseId);
    applyAssetPlan(assets.asset_plan, preferredAssetId);
    return assets.asset_plan;
  }

  function clearV2PackageState() {
    setRunPackage(null);
    setRunCompatibility("none");
    setCanForkV2FromSource(false);
    setV2Elements([]);
    setSelectedV2ElementId("");
    setSelectedAssetPackage(null);
    setV2PackageError("");
    setV2AssetLoadingElementId("");
  }

  function clearAssetEditingState() {
    setAssetPlan(null);
    setSelectedAssetId("");
    setUndoStack([]);
    clearV2PackageState();
  }

  function applyLegacyCompatibility(detail: CaseDetail) {
    setRunPackage(null);
    setRunCompatibility("legacy_readonly");
    setCanForkV2FromSource(Boolean(detail.case.can_fork_from_source));
    setV2Elements([]);
    setSelectedV2ElementId("");
    setSelectedAssetPackage(null);
    setV2PackageError("");
  }

  async function loadV2PackageForCase(caseId: string, preferredElementId = "", options: { quiet?: boolean } = {}): Promise<boolean> {
    try {
      const packagePayload = await getRunPackage(caseId);
      const elementsPayload = await getElements(caseId);
      const elements = elementsPayload.elements.length > 0 ? elementsPayload.elements : packagePayload.package.elements || [];
      const nextElementId = preferredElementId && elements.some((element) => element.element_id === preferredElementId)
        ? preferredElementId
        : elements[0]?.element_id || "";
      const packageFromRun = nextElementId ? assetPackageFromRunPackage(packagePayload.package, nextElementId) : null;
      let nextAssetPackage = packageFromRun;
      if (nextElementId) {
        setV2AssetLoadingElementId(nextElementId);
        try {
          nextAssetPackage = (await getAssetPackage(caseId, nextElementId)).asset_package;
        } finally {
          setV2AssetLoadingElementId((current) => (current === nextElementId ? "" : current));
        }
      }
      setRunPackage(packagePayload.package);
      setRunCompatibility(packagePayload.compatibility.mode === "v2" ? "v2" : packagePayload.compatibility.mode);
      setCanForkV2FromSource(packagePayload.compatibility.can_fork_from_source);
      setV2Elements(elements);
      setSelectedV2ElementId(nextElementId);
      setSelectedAssetPackage(nextAssetPackage);
      setV2PackageError("");
      return true;
    } catch (err) {
      setV2AssetLoadingElementId("");
      if (isDrawAiApiStatus(err, 404)) {
        return false;
      }
      const message = err instanceof Error ? err.message : String(err);
      setV2PackageError(message);
      if (!options.quiet) throw err;
      return false;
    }
  }

  async function selectV2Element(elementId: string) {
    if (!activeCase || !runPackage) return;
    setSelectedV2ElementId(elementId);
    setV2PackageError("");
    setV2AssetLoadingElementId(elementId);
    try {
      const response = await getAssetPackage(activeCase.case.case_id, elementId);
      setSelectedAssetPackage(response.asset_package);
    } catch (err) {
      if (isDrawAiApiStatus(err, 404)) {
        setSelectedAssetPackage(assetPackageFromRunPackage(runPackage, elementId));
        return;
      }
      const message = err instanceof Error ? err.message : String(err);
      setV2PackageError(message);
      throw err;
    } finally {
      setV2AssetLoadingElementId((current) => (current === elementId ? "" : current));
    }
  }

  async function selectCase(caseId: string): Promise<{ detail: CaseDetail; hasAssetPlan: boolean; compatibility: RunCompatibilityMode }> {
    const detail = await getCase(caseId);
    setActiveCase(detail);
    setCaseProgress(await getCaseProgress(caseId));
    clearAssetEditingState();
    const hasV2Package = await loadV2PackageForCase(caseId);
    if (hasV2Package) {
      return { detail, hasAssetPlan: false, compatibility: "v2" };
    }
    if (detail.case.compatibility_mode === "legacy_readonly" || caseHasLegacyArtifacts(detail)) {
      applyLegacyCompatibility(detail);
      return { detail, hasAssetPlan: false, compatibility: "legacy_readonly" };
    }
    try {
      await loadAssetsForCase(caseId);
      return { detail, hasAssetPlan: true, compatibility: "none" };
    } catch {
      setAssetPlan(null);
      return { detail, hasAssetPlan: false, compatibility: "none" };
    }
  }

  useEffect(() => {
    refreshHealth();
    refreshBatches().catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (activeCase) return;
    const preferredBatch = batches.find((batch) => caseCountTotal(batch.case_counts) > 0) || batches[0];
    if (!preferredBatch || activeBatch?.batch.batch_id === preferredBatch.batch_id || autoSelectedBatchId.current === preferredBatch.batch_id) return;
    autoSelectedBatchId.current = preferredBatch.batch_id;
    selectBatch(preferredBatch.batch_id).catch((err) => setError(err.message));
  }, [batches, activeBatch, activeCase]);

  useEffect(() => {
    const timer = window.setInterval(async () => {
      await refreshHealth();
      try {
        await refreshBatches();
        if (activeBatch) {
          const detail = await getBatch(activeBatch.batch.batch_id);
          setActiveBatch(detail);
        }
        if (activeCase) {
          const detail = await getCase(activeCase.case.case_id);
          setActiveCase(detail);
          setCaseProgress(await getCaseProgress(activeCase.case.case_id));
          if (detail.case.compatibility_mode === "v2" || runCompatibility === "v2") {
            await loadV2PackageForCase(activeCase.case.case_id, selectedV2ElementId, { quiet: true });
          } else if (detail.case.compatibility_mode === "legacy_readonly" && runCompatibility !== "legacy_readonly") {
            applyLegacyCompatibility(detail);
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    }, 2500);
    return () => window.clearInterval(timer);
  }, [activeBatch?.batch.batch_id, activeCase?.case.case_id, runCompatibility, selectedV2ElementId]);

  const activeAssetPlan = activeCase && assetPlan?.case_id === activeCase.case.case_id ? assetPlan : null;
  const activeRunPackage = activeCase && runPackage?.run_id === activeCase.case.case_id ? runPackage : null;
  const legacyReadOnly = runCompatibility === "legacy_readonly";
  const v2PackageReady = Boolean(activeCase && activeRunPackage && runCompatibility === "v2");
  const selectedAsset = activeAssetPlan?.elements.find((item) => item.box_id === selectedAssetId) || null;
  const figureArtifact = latestArtifact(activeCase?.artifacts || [], "figure");
  const renderedArtifact = latestArtifact(activeCase?.artifacts || [], "rendered_png");
  const activeBatchCase = activeBatch?.cases.find((item) => item.case_id === activeCase?.case.case_id) || null;
  const activeCaseRunning = Boolean(
    activeCase &&
      (isCaseActivelyRunning(activeCase, caseProgress) ||
        assetsRunPendingCaseId === activeCase.case.case_id ||
        Boolean(v2ActionPending))
  );
  const assetsReady = Boolean(
    activeCase &&
      !legacyReadOnly &&
      (v2PackageReady ||
        activeAssetPlan ||
        activeBatchCase?.editor_ready ||
        latestProgressFile(caseProgress, "asset_draft")?.exists ||
        latestArtifact(activeCase.artifacts, "asset_draft"))
  );
  const canvasReady = Boolean(activeCase && caseCanOpenCanvas(activeCase, caseProgress) && !activeCaseRunning);
  const canRunFromAssets = Boolean(activeCase && assetsReady && !activeCaseRunning && !legacyReadOnly);

  useEffect(() => {
    if (!activeCase || activeAssetPlan || !assetsReady || activeCaseRunning || runCompatibility !== "none") return;
    let canceled = false;
    getAssets(activeCase.case.case_id)
      .then((assets) => {
        if (canceled) return;
        applyAssetPlan(assets.asset_plan, selectedAssetId);
      })
      .catch((err) => {
        if (!canceled && activeView === "editor") {
          setError(err instanceof Error ? err.message : String(err));
        }
      });
    return () => {
      canceled = true;
    };
  }, [activeCase?.case.case_id, activeAssetPlan, activeCaseRunning, activeView, assetsReady, runCompatibility, selectedAssetId]);

  const deleteSelectedAsset = useCallback(() => {
    if (!activeAssetPlan || !selectedAsset) return;
    setUndoStack((items) => [...items.slice(-49), cloneAssetPlan(activeAssetPlan)]);
    const next = { ...activeAssetPlan, elements: activeAssetPlan.elements.filter((item) => item.box_id !== selectedAsset.box_id) };
    setAssetPlan(next);
    setSelectedAssetId(next.elements[0]?.box_id || "");
  }, [activeAssetPlan, selectedAsset]);

  const recordUndoSnapshot = useCallback(() => {
    if (!activeAssetPlan) return;
    setUndoStack((items) => [...items.slice(-49), cloneAssetPlan(activeAssetPlan)]);
  }, [activeAssetPlan]);

  const undoAssetPlan = useCallback(() => {
    setUndoStack((items) => {
      const previous = items[items.length - 1];
      if (!previous) return items;
      setAssetPlan(previous);
      setSelectedAssetId((current) => (previous.elements.some((element) => element.box_id === current) ? current : previous.elements[0]?.box_id || ""));
      return items.slice(0, -1);
    });
  }, []);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (isEditableTarget(event.target)) return;
      if ((event.metaKey || event.ctrlKey) && !event.shiftKey && event.key.toLowerCase() === "z") {
        event.preventDefault();
        undoAssetPlan();
        return;
      }
      if (activeView === "editor" && (event.key === "Backspace" || event.key === "Delete") && selectedAsset) {
        event.preventDefault();
        deleteSelectedAsset();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeView, deleteSelectedAsset, selectedAsset, undoAssetPlan]);

  async function updateAssetPlan(nextPlan: AssetPlan, options: AssetPlanChangeOptions = {}) {
    if (options.track !== false && activeAssetPlan) {
      setUndoStack((items) => [...items.slice(-49), cloneAssetPlan(activeAssetPlan)]);
    }
    setAssetPlan(nextPlan);
  }

  async function processAssetPlanItems(assetIds: string[], plan: AssetPlan): Promise<AssetPlan> {
    if (!activeCase) return plan;
    const response = await processAssetElements(activeCase.case.case_id, plan, assetIds);
    setAssetPlan(response.asset_plan);
    return response.asset_plan;
  }

  async function refreshCaseAfterV2Mutation(caseId: string, preferredElementId = selectedV2ElementId) {
    const detail = await getCase(caseId);
    setActiveCase(detail);
    setCaseProgress(await getCaseProgress(caseId));
    if (activeBatch?.batch.batch_id === detail.case.batch_id) {
      setActiveBatch(await getBatch(detail.case.batch_id));
    }
    await refreshBatches();
    await loadV2PackageForCase(caseId, preferredElementId, { quiet: true });
    return detail;
  }

  async function processSelectedV2Asset(processor: V2ProcessorType, elementId = selectedV2ElementId) {
    if (!activeCase || !elementId || processor === "chart_rebuild_reserved") return;
    const caseId = activeCase.case.case_id;
    setSelectedV2ElementId(elementId);
    setV2ActionPending(`process:${elementId}:${processor}`);
    setV2PackageError("");
    try {
      const response = await processV2Asset(caseId, elementId, processor);
      setSelectedAssetPackage(response.asset_package);
      mergeCaseStatus(response.case);
      await refreshCaseAfterV2Mutation(caseId, elementId);
    } catch (err) {
      await loadV2PackageForCase(caseId, elementId, { quiet: true });
      const message = err instanceof Error ? err.message : String(err);
      setV2PackageError(message);
      throw err;
    } finally {
      setV2ActionPending("");
    }
  }

  async function activateV2AssetResult(resultId: string) {
    if (!activeCase || !selectedV2ElementId) return;
    const caseId = activeCase.case.case_id;
    setV2ActionPending(`active:${resultId}`);
    setV2PackageError("");
    try {
      const response = await setActiveAssetResult(caseId, selectedV2ElementId, resultId);
      setSelectedAssetPackage(response.asset_package);
      mergeCaseStatus(response.case);
      await refreshCaseAfterV2Mutation(caseId, selectedV2ElementId);
    } finally {
      setV2ActionPending("");
    }
  }

  async function composeActiveV2Case() {
    if (!activeCase || runCompatibility !== "v2") return;
    const caseId = activeCase.case.case_id;
    setV2ActionPending("compose");
    setAssetsRunPendingCaseId(caseId);
    setV2PackageError("");
    try {
      const response = await composeV2Case(caseId);
      mergeCaseStatus(response.case);
      await refreshCaseAfterV2Mutation(caseId, selectedV2ElementId);
    } finally {
      setV2ActionPending("");
      setAssetsRunPendingCaseId((current) => (current === caseId ? "" : current));
    }
  }

  async function forkActiveCaseToV2() {
    if (!activeCase || !canForkV2FromSource) return;
    const currentCase = activeCase.case;
    setV2ActionPending("fork");
    setV2PackageError("");
    try {
      const response = await forkV2FromSource(currentCase.case_id);
      const batchDetail = await getBatch(response.case.batch_id);
      setActiveBatch(batchDetail);
      await refreshBatches();
      await selectCase(response.case.case_id);
      setActiveView("board");
    } finally {
      setV2ActionPending("");
    }
  }

  async function runFromAssets() {
    if (!activeCase) return;
    if (activeCaseRunning) {
      setError("这张图正在运行。");
      return;
    }
    if (runCompatibility === "legacy_readonly") {
      setError("这是历史只读结果。请先从源图创建 v2 run，再进行处理。");
      return;
    }
    if (runCompatibility === "v2") {
      await composeActiveV2Case();
      return;
    }
    if (!assetsReady) {
      setError("素材还没准备好。");
      return;
    }
    const caseId = activeCase.case.case_id;
    const batchId = activeCase.case.batch_id;
    setAssetsRunPendingCaseId(caseId);
    try {
      let plan = activeAssetPlan;
      if (!plan) {
        const loaded = await getAssets(caseId);
        plan = loaded.asset_plan;
        setAssetPlan(plan);
      }
      const saved = await saveAssetDraft(caseId, plan);
      setAssetPlan(saved.asset_plan);
      const approved = await approveAssets(caseId, true);
      setAssetPlan(approved.asset_plan);
      mergeCaseStatus(approved.case);
      setUndoStack([]);
      setActiveView("board");
      await selectCase(caseId);
      await selectBatch(batchId);
      await refreshBatches();
    } finally {
      setAssetsRunPendingCaseId((current) => (current === caseId ? "" : current));
    }
  }

  function runFromEditor() {
    setActiveView("board");
    runFromAssets().catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }

  async function openAssetsEditorForCase(caseId: string) {
    const selected = activeCase?.case.case_id === caseId;
    const selection = selected
      ? { hasAssetPlan: Boolean(activeAssetPlan), compatibility: runCompatibility }
      : await selectCase(caseId);
    if (selection.compatibility === "legacy_readonly") {
      setError("这是历史只读结果，不能继续编辑素材。");
      return;
    }
    if (selection.compatibility === "v2") {
      setActiveView("editor");
      return;
    }
    if (selected && !activeAssetPlan) {
      await loadAssetsForCase(caseId, selectedAssetId);
    } else if (!selected && !selection.hasAssetPlan) {
      setError("素材还没准备好。");
      return;
    }
    setActiveView("editor");
  }

  async function renameTaskBatch(batchId: string, name: string) {
    const cleanName = name.trim();
    if (!cleanName) {
      setError("任务名称不能为空。");
      return;
    }
    const detail = await renameBatch(batchId, cleanName);
    setBatches((items) => items.map((item) => (item.batch_id === detail.batch.batch_id ? detail.batch : item)));
    if (activeBatch?.batch.batch_id === batchId) {
      setActiveBatch(detail);
    }
    setTaskRenameTarget(null);
  }

  async function deleteTaskBatch(batchId: string) {
    await deleteBatch(batchId);
    const nextBatches = await refreshBatches();
    setTaskDeleteTarget(null);
    if (activeBatch?.batch.batch_id !== batchId) return;
    const nextBatch = nextBatches.find((batch) => caseCountTotal(batch.case_counts) > 0) || nextBatches[0];
    if (nextBatch) {
      await selectBatch(nextBatch.batch_id);
      return;
    }
    setActiveBatch(null);
    setActiveCase(null);
    setCaseProgress(null);
    clearAssetEditingState();
  }

  async function runTaskBatch(batchId: string) {
    if (batchRunPendingId) return;
    setBatchRunPendingId(batchId);
    try {
      const detail = await runBatch(batchId);
      setActiveBatch(detail);
      if (detail.cases.length > 0) {
        const nextCase = detail.cases.find((item) => item.case_id === activeCase?.case.case_id) || detail.cases[0];
        await selectCase(nextCase.case_id);
      }
      await refreshBatches();
      setActiveView("board");
    } finally {
      setBatchRunPendingId((current) => (current === batchId ? "" : current));
    }
  }

  async function retryFailedCase(item: CaseRecord) {
    if (assetsRunPendingCaseId) return;
    const stage = retryStageForCase(item);
    setAssetsRunPendingCaseId(item.case_id);
    try {
      await runCaseStage(item.case_id, stage);
      await selectBatch(item.batch_id);
      await selectCase(item.case_id);
      await refreshBatches();
      setActiveView("board");
    } finally {
      setAssetsRunPendingCaseId((current) => (current === item.case_id ? "" : current));
    }
  }

  async function exportPptxForCase(caseId: string): Promise<ArtifactRecord[]> {
    if (pptxExportPendingCaseId) return [];
    setPptxExportPendingCaseId(caseId);
    try {
      const beforeDetail = await getCase(caseId);
      const previousExportRunCount = exportStageRunCount(beforeDetail);
      await runCaseStage(caseId, "export");
      const detail = await waitForPptxExport(caseId, previousExportRunCount);
      const progress = await getCaseProgress(caseId);
      if (activeCase?.case.case_id === caseId) setActiveCase(detail);
      if (activeCase?.case.case_id === caseId) setCaseProgress(progress);
      if (activeBatch?.batch.batch_id === detail.case.batch_id) {
        setActiveBatch(await getBatch(detail.case.batch_id));
      }
      await refreshBatches();
      const pptx = latestArtifact(detail.artifacts, "pptx");
      if (!pptx) {
        throw new Error("PPTX 导出完成，但没有找到可下载的 PPTX artifact。");
      }
      await downloadPptxArtifactForCase(caseId, pptx, progress);
      return detail.artifacts;
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      throw err;
    } finally {
      setPptxExportPendingCaseId((current) => (current === caseId ? "" : current));
    }
  }

  async function downloadBatchPptxForBatch(batchId: string) {
    if (batchPptxDownloadPendingId) return;
    const batch = activeBatch?.batch.batch_id === batchId ? activeBatch.batch : batches.find((item) => item.batch_id === batchId);
    setBatchPptxDownloadPendingId(batchId);
    try {
      const blob = await downloadBatchPptx(batchId);
      downloadBlob(blob, `${safeDownloadStem(batch?.name || "drawai_batch")}.pptx`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBatchPptxDownloadPendingId((current) => (current === batchId ? "" : current));
    }
  }

  async function waitForPptxExport(caseId: string, previousExportRunCount: number): Promise<CaseDetail> {
    const deadline = Date.now() + PPTX_EXPORT_TIMEOUT_MS;
    let detail = await getCase(caseId);
    while (Date.now() <= deadline) {
      if (latestArtifact(detail.artifacts, "pptx")) return detail;
      if (hasNewFailedExportRun(detail, previousExportRunCount)) {
        throw new Error(detail.case.error_message || "PPTX 导出失败。");
      }
      await delay(PPTX_EXPORT_POLL_INTERVAL_MS);
      detail = await getCase(caseId);
    }
    throw new Error("PPTX 导出超时，请稍后刷新任务状态后重试下载。");
  }

  async function downloadPptxArtifactForCase(
    caseId: string,
    artifact: ArtifactRecord,
    knownProgress?: CaseProgress
  ): Promise<void> {
    const progress = knownProgress || (await getCaseProgress(caseId));
    if (activeCase?.case.case_id === caseId) setCaseProgress(progress);
    downloadArtifact(artifact);
  }

  async function openCaseFromTask(caseId: string) {
    await selectCase(caseId);
  }

  async function activateCreatedBatch(detail: BatchDetail) {
    setActiveView("board");
    setBoardMode("process");
    autoSelectedBatchId.current = detail.batch.batch_id;
    setBatches((items) => [detail.batch, ...items.filter((item) => item.batch_id !== detail.batch.batch_id)]);
    setActiveBatch(detail);
    const firstCase = detail.cases[0];
    if (firstCase) {
      await selectCase(firstCase.case_id);
    } else {
      setActiveCase(null);
      setCaseProgress(null);
      clearAssetEditingState();
    }
  }

  return (
    <div className={activeView === "board" ? "app-root" : "app-root editor-mode"}>
      <header className={activeView === "board" ? "app-topbar board-topbar" : "app-topbar"}>
        <div className="brand-row">
          <img className="brand-logo" src="/drawai_image.png" alt="" />
          <div className="brand-copy">
            <h1>DrawAI</h1>
          </div>
          {activeView === "board" && (
            <div className={`board-mode-switch is-${boardMode}`} role="tablist" aria-label="工作模式">
              <span className="board-mode-switch__thumb" aria-hidden="true" />
              <button
                type="button"
                role="tab"
                aria-selected={boardMode === "generate"}
                className={boardMode === "generate" ? "active" : ""}
                onClick={() => setBoardMode("generate")}
              >
                生成
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={boardMode === "process"}
                className={boardMode === "process" ? "active" : ""}
                onClick={() => setBoardMode("process")}
              >
                处理
              </button>
            </div>
          )}
        </div>
        <div id="drawai-view-controls" className="topbar-view-controls" />
        <div className="topbar-links">
          {activeView === "board" && boardMode === "generate" && (
            <button
              type="button"
              className="topbar-icon-button"
              title="生成 API 设置"
              aria-label="生成 API 设置"
              onClick={() => setImageGenSettingsOpen(true)}
            >
              <SettingsIcon />
            </button>
          )}
          <BackendStatusIndicator health={health} healthError={healthError} />
          <a
            className="github-link"
            href="https://github.com/Renaissance-Mind/DrawAI"
            target="_blank"
            rel="noreferrer"
            aria-label="在 GitHub 打开 DrawAI"
            title="GitHub"
          >
            <svg className="github-icon" viewBox="0 0 24 24" aria-hidden="true">
              <path
                fillRule="evenodd"
                clipRule="evenodd"
                d="M12 2.25c-5.38 0-9.75 4.37-9.75 9.75 0 4.3 2.79 7.95 6.66 9.24.49.09.67-.21.67-.47v-1.66c-2.71.59-3.28-1.31-3.28-1.31-.44-1.13-1.08-1.43-1.08-1.43-.88-.6.07-.59.07-.59.98.07 1.5 1.01 1.5 1.01.87 1.49 2.28 1.06 2.84.81.09-.63.34-1.06.62-1.31-2.16-.25-4.43-1.08-4.43-4.82 0-1.07.38-1.94 1-2.62-.1-.25-.43-1.24.1-2.58 0 0 .82-.26 2.68 1a9.32 9.32 0 0 1 4.88 0c1.86-1.26 2.68-1 2.68-1 .53 1.34.2 2.33.1 2.58.62.68 1 1.55 1 2.62 0 3.75-2.28 4.57-4.45 4.81.35.3.66.89.66 1.8v2.67c0 .26.18.56.67.47A9.76 9.76 0 0 0 21.75 12c0-5.38-4.37-9.75-9.75-9.75Z"
              />
            </svg>
          </a>
        </div>
      </header>

      {error && (
        <div className="error-bar">
          <span>{error}</span>
          <button onClick={() => setError("")}>关闭</button>
        </div>
      )}

      {activeView === "board" ? (
        boardMode === "generate" ? (
          <main className="board-workspace board-generate-workspace">
            <ImageGenStudio
              connection={imageGenConnection}
              onConnectionChange={(nextConnection) => {
                setImageGenConnection(nextConnection);
                saveImageGenConnectionSettings(nextConnection);
              }}
              onCreated={activateCreatedBatch}
              onError={setError}
            />
          </main>
        ) : (
        <BoardWorkspace
          batches={batches}
          activeBatch={activeBatch}
          activeCase={activeCase}
          caseProgress={caseProgress}
          assetsReady={assetsReady}
          canvasReady={canvasReady}
          runInProgress={activeCaseRunning}
          canRunFromAssets={canRunFromAssets}
          runCompatibility={runCompatibility}
          runPackage={activeRunPackage}
          v2Elements={v2Elements}
          selectedV2ElementId={selectedV2ElementId}
          selectedAssetPackage={selectedAssetPackage}
          v2PackageError={v2PackageError}
          v2AssetLoadingElementId={v2AssetLoadingElementId}
          v2ActionPending={v2ActionPending}
          canForkV2FromSource={canForkV2FromSource}
          caseActionPendingId={assetsRunPendingCaseId}
          pptxExportPendingCaseId={pptxExportPendingCaseId}
          batchPptxDownloadPendingId={batchPptxDownloadPendingId}
          batchRunPendingId={batchRunPendingId}
          onOpenSubmit={() => setSubmitOpen(true)}
          onOpenCaseAssets={(caseId) => openAssetsEditorForCase(caseId).catch((err) => setError(err instanceof Error ? err.message : String(err)))}
          onOpenSvgEditor={() => setActiveView("svg")}
          onRenameBatch={(batch) => setTaskRenameTarget({ batchId: batch.batch_id, name: batch.name })}
          onDeleteBatch={(batch) => setTaskDeleteTarget({ batchId: batch.batch_id, name: batch.name })}
          onRunBatch={(batchId) => runTaskBatch(batchId).catch((err) => setError(err instanceof Error ? err.message : String(err)))}
          onSelectBatch={(batchId) => selectBatch(batchId).catch((err) => setError(err.message))}
          onFocusCase={(caseId) => selectCase(caseId).then(() => undefined).catch((err) => setError(err.message))}
          onSelectCase={(caseId) => openCaseFromTask(caseId).catch((err) => setError(err.message))}
          onRunFromAssets={() => runFromAssets().catch((err) => setError(err instanceof Error ? err.message : String(err)))}
          onRetryCase={(item) => retryFailedCase(item).catch((err) => setError(err instanceof Error ? err.message : String(err)))}
          onExportPptx={(caseId) => exportPptxForCase(caseId)}
          onDownloadPptx={(caseId, artifact) => downloadPptxArtifactForCase(caseId, artifact).catch((err) => setError(err instanceof Error ? err.message : String(err)))}
          onDownloadBatchPptx={(batchId) => downloadBatchPptxForBatch(batchId)}
          onSelectV2Element={(elementId) => selectV2Element(elementId).catch((err) => setError(err instanceof Error ? err.message : String(err)))}
          onProcessV2Asset={(processor, elementId) => processSelectedV2Asset(processor, elementId).catch((err) => setError(err instanceof Error ? err.message : String(err)))}
          onSetActiveV2Result={(resultId) => activateV2AssetResult(resultId).catch((err) => setError(err instanceof Error ? err.message : String(err)))}
          onForkV2FromSource={() => forkActiveCaseToV2().catch((err) => setError(err instanceof Error ? err.message : String(err)))}
        />
        )
      ) : activeView === "editor" && runCompatibility === "v2" ? (
        <V2AssetsWorkspace
          activeCase={activeCase}
          runPackage={activeRunPackage}
          elements={v2Elements}
          selectedElementId={selectedV2ElementId}
          selectedAssetPackage={selectedAssetPackage}
          packageError={v2PackageError}
          loadingElementId={v2AssetLoadingElementId}
          actionPending={v2ActionPending}
          figureUrl={figureArtifact?.url || activeCase?.case.preview_url || ""}
          runInProgress={activeCaseRunning}
          onBackToBoard={() => setActiveView("board")}
          onSelectElement={(elementId) => selectV2Element(elementId).catch((err) => setError(err instanceof Error ? err.message : String(err)))}
          onProcessAsset={(processor, elementId) => processSelectedV2Asset(processor, elementId).catch((err) => setError(err instanceof Error ? err.message : String(err)))}
          onSetActiveResult={(resultId) => activateV2AssetResult(resultId).catch((err) => setError(err instanceof Error ? err.message : String(err)))}
          onRun={runFromEditor}
        />
      ) : activeView === "editor" ? (
        <EditorWorkspace
          activeCase={activeCase}
          assetPlan={activeAssetPlan}
          selectedAssetId={selectedAssetId}
          figureUrl={figureArtifact?.url || ""}
          canUndo={undoStack.length > 0}
          onBackToBoard={() => setActiveView("board")}
          onSelectAsset={setSelectedAssetId}
          onChangeAssetPlan={updateAssetPlan}
          onBeginAssetEdit={recordUndoSnapshot}
          onUndo={undoAssetPlan}
          onNext={runFromEditor}
          onProcessAssets={(assetIds, plan) => processAssetPlanItems(assetIds, plan)}
          onDelete={deleteSelectedAsset}
          runInProgress={activeCaseRunning}
        />
      ) : (
        <SvgWorkspace
          activeCase={activeCase}
          progress={caseProgress}
          onBackToBoard={() => setActiveView("board")}
          onError={setError}
          onExportPptx={(caseId) => exportPptxForCase(caseId)}
          onDownloadPptx={(caseId, artifact) => downloadPptxArtifactForCase(caseId, artifact)}
          pptxExporting={Boolean(activeCase && pptxExportPendingCaseId === activeCase.case.case_id)}
          canRunFromAssets={canRunFromAssets}
          runInProgress={activeCaseRunning}
          onRunFromAssets={() => runFromAssets().catch((err) => setError(err instanceof Error ? err.message : String(err)))}
          readOnly={legacyReadOnly}
        />
      )}
      {submitOpen && (
        <SubmitDialog
          onSubmitted={() => setSubmitOpen(false)}
          onClose={() => setSubmitOpen(false)}
          onCreated={async (detail) => {
            setSubmitOpen(false);
            await activateCreatedBatch(detail);
          }}
          onError={setError}
        />
      )}
      {imageGenSettingsOpen && (
        <ImageGenSettingsDialog
          connection={imageGenConnection}
          onClose={() => setImageGenSettingsOpen(false)}
          onSave={(nextConnection) => {
            setImageGenConnection(nextConnection);
            saveImageGenConnectionSettings(nextConnection);
            setImageGenSettingsOpen(false);
          }}
        />
      )}
      {taskRenameTarget && (
        <TaskRenameDialog
          target={taskRenameTarget}
          onClose={() => setTaskRenameTarget(null)}
          onSave={(name) => renameTaskBatch(taskRenameTarget.batchId, name).catch((err) => setError(err instanceof Error ? err.message : String(err)))}
        />
      )}
      {taskDeleteTarget && (
        <TaskDeleteDialog
          target={taskDeleteTarget}
          onClose={() => setTaskDeleteTarget(null)}
          onDelete={() => deleteTaskBatch(taskDeleteTarget.batchId).catch((err) => setError(err instanceof Error ? err.message : String(err)))}
        />
      )}
    </div>
  );
}

function BoardWorkspace({
  batches,
  activeBatch,
  activeCase,
  caseProgress,
  assetsReady,
  canvasReady,
  runInProgress,
  canRunFromAssets,
  runCompatibility,
  runPackage,
  v2Elements,
  selectedV2ElementId,
  selectedAssetPackage,
  v2PackageError,
  v2AssetLoadingElementId,
  v2ActionPending,
  canForkV2FromSource,
  caseActionPendingId,
  pptxExportPendingCaseId,
  batchPptxDownloadPendingId,
  batchRunPendingId,
  onOpenSubmit,
  onOpenCaseAssets,
  onOpenSvgEditor,
  onRenameBatch,
  onDeleteBatch,
  onRunBatch,
  onSelectBatch,
  onFocusCase,
  onSelectCase,
  onRunFromAssets,
  onRetryCase,
  onExportPptx,
  onDownloadPptx,
  onDownloadBatchPptx,
  onSelectV2Element,
  onProcessV2Asset,
  onSetActiveV2Result,
  onForkV2FromSource
}: {
  batches: BatchRecord[];
  activeBatch: BatchDetail | null;
  activeCase: CaseDetail | null;
  caseProgress: CaseProgress | null;
  assetsReady: boolean;
  canvasReady: boolean;
  runInProgress: boolean;
  canRunFromAssets: boolean;
  runCompatibility: RunCompatibilityMode;
  runPackage: V2RunPackage | null;
  v2Elements: V2ElementPlan[];
  selectedV2ElementId: string;
  selectedAssetPackage: V2AssetPackage | null;
  v2PackageError: string;
  v2AssetLoadingElementId: string;
  v2ActionPending: string;
  canForkV2FromSource: boolean;
  caseActionPendingId: string;
  pptxExportPendingCaseId: string;
  batchPptxDownloadPendingId: string;
  batchRunPendingId: string;
  onOpenSubmit: () => void;
  onOpenCaseAssets: (caseId: string) => void;
  onOpenSvgEditor: () => void;
  onRenameBatch: (batch: BatchRecord) => void;
  onDeleteBatch: (batch: BatchRecord) => void;
  onRunBatch: (batchId: string) => void;
  onSelectBatch: (batchId: string) => void;
  onFocusCase: (caseId: string) => void | Promise<void>;
  onSelectCase: (caseId: string) => void;
  onRunFromAssets: () => void;
  onRetryCase: (item: CaseRecord) => void;
  onExportPptx: (caseId: string) => Promise<ArtifactRecord[]>;
  onDownloadPptx: (caseId: string, artifact: ArtifactRecord) => void | Promise<void>;
  onDownloadBatchPptx: (batchId: string) => void | Promise<void>;
  onSelectV2Element: (elementId: string) => void;
  onProcessV2Asset: (processor: V2ProcessorType, elementId?: string) => void;
  onSetActiveV2Result: (resultId: string) => void;
  onForkV2FromSource: () => void;
}) {
  return (
    <main className="board-workspace">
      <div className="board-grid">
        <TaskSelectionWorkspace
          batches={batches}
          activeBatch={activeBatch}
          activeCase={activeCase}
          assetsReady={assetsReady}
          canvasReady={canvasReady}
          runInProgress={runInProgress}
          canRunFromAssets={canRunFromAssets}
          runCompatibility={runCompatibility}
          caseActionPendingId={caseActionPendingId}
          pptxExportPendingCaseId={pptxExportPendingCaseId}
          batchPptxDownloadPendingId={batchPptxDownloadPendingId}
          batchRunPendingId={batchRunPendingId}
          onOpenSubmit={onOpenSubmit}
          onOpenCaseAssets={onOpenCaseAssets}
          onOpenSvgEditor={onOpenSvgEditor}
          onRenameBatch={onRenameBatch}
          onDeleteBatch={onDeleteBatch}
          onRunBatch={onRunBatch}
          onSelectBatch={onSelectBatch}
          onFocusCase={onFocusCase}
          onSelectCase={onSelectCase}
          onRunFromAssets={onRunFromAssets}
          onRetryCase={onRetryCase}
          onExportPptx={onExportPptx}
          onDownloadPptx={onDownloadPptx}
          onDownloadBatchPptx={onDownloadBatchPptx}
        />
        <TaskDetailPanel
          caseDetail={activeCase}
          progress={caseProgress}
          runCompatibility={runCompatibility}
          runPackage={runPackage}
          v2Elements={v2Elements}
          selectedV2ElementId={selectedV2ElementId}
          selectedAssetPackage={selectedAssetPackage}
          v2PackageError={v2PackageError}
          v2AssetLoadingElementId={v2AssetLoadingElementId}
          v2ActionPending={v2ActionPending}
          canForkV2FromSource={canForkV2FromSource}
          onSelectV2Element={onSelectV2Element}
          onProcessV2Asset={onProcessV2Asset}
          onSetActiveV2Result={onSetActiveV2Result}
          onForkV2FromSource={onForkV2FromSource}
        />
      </div>
    </main>
  );
}

function SubmitDialog({
  onSubmitted,
  onClose,
  onCreated,
  onError
}: {
  onSubmitted: () => void;
  onClose: () => void;
  onCreated: (detail: BatchDetail) => void | Promise<void>;
  onError: (message: string) => void;
}) {
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="submit-dialog submit-dialog-drop-only" role="dialog" aria-modal="true" aria-label="提交任务" onMouseDown={(event) => event.stopPropagation()}>
        <NewBatchForm onSubmitted={onSubmitted} onCreated={onCreated} onError={onError} />
      </section>
    </div>
  );
}

function ImageGenSettingsDialog({
  connection,
  onClose,
  onSave
}: {
  connection: ImageGenConnectionSettings;
  onClose: () => void;
  onSave: (connection: ImageGenConnectionSettings) => void;
}) {
  const [draft, setDraft] = useState<ImageGenConnectionSettings>(connection);
  const save = () => {
    onSave({
      provider: draft.provider || DEFAULT_IMAGEGEN_CONNECTION.provider,
      baseUrl: draft.baseUrl.trim(),
      apiKey: draft.apiKey.trim(),
      model: draft.model.trim() || DEFAULT_IMAGEGEN_CONNECTION.model
    });
  };
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="settings-dialog imagegen-settings-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="生成 API 设置"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="settings-dialog-head">
          <div>
            <span>生成 API</span>
            <strong>连接设置</strong>
          </div>
          <button type="button" className="settings-close" aria-label="关闭" onClick={onClose}>
            ×
          </button>
        </header>
        <div className="settings-form">
          <label className="settings-field">
            <span>接口地址</span>
            <input
              value={draft.baseUrl}
              onChange={(event) => setDraft((current) => ({ ...current, baseUrl: event.target.value }))}
              placeholder="https://api.openai.com"
            />
          </label>
          <label className="settings-field">
            <span>模型</span>
            <input
              value={draft.model}
              onChange={(event) => setDraft((current) => ({ ...current, model: event.target.value }))}
              placeholder="gpt-image-2"
              autoComplete="off"
            />
          </label>
          <label className="settings-field">
            <span>API 密钥</span>
            <input
              type="password"
              value={draft.apiKey}
              onChange={(event) => setDraft((current) => ({ ...current, apiKey: event.target.value }))}
              placeholder="留空则使用后端环境变量"
              autoComplete="off"
            />
          </label>
        </div>
        <footer className="settings-actions">
          <button type="button" onClick={() => setDraft(DEFAULT_IMAGEGEN_CONNECTION)}>
            清空
          </button>
          <button type="button" onClick={onClose}>
            取消
          </button>
          <button type="button" className="primary" onClick={save}>
            保存
          </button>
        </footer>
      </section>
    </div>
  );
}

function TaskRenameDialog({
  target,
  onClose,
  onSave
}: {
  target: TaskDialogTarget;
  onClose: () => void;
  onSave: (name: string) => void | Promise<void>;
}) {
  const [draft, setDraft] = useState(target.name);
  const [saving, setSaving] = useState(false);

  async function submit() {
    setSaving(true);
    try {
      await onSave(draft);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="settings-dialog task-action-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="重命名任务"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="settings-dialog-head">
          <div>
            <span>任务</span>
            <strong>重命名</strong>
          </div>
          <button type="button" className="settings-close" aria-label="关闭" onClick={onClose}>
            ×
          </button>
        </header>
        <form
          className="settings-form"
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          <label className="settings-field">
            <span>名称</span>
            <input
              value={draft}
              autoFocus
              onChange={(event) => setDraft(event.target.value)}
            />
          </label>
        </form>
        <footer className="settings-actions">
          <button type="button" onClick={onClose}>
            取消
          </button>
          <button type="button" className="primary" disabled={saving || !draft.trim()} onClick={() => void submit()}>
            {saving ? "保存中" : "保存"}
          </button>
        </footer>
      </section>
    </div>
  );
}

function TaskDeleteDialog({
  target,
  onClose,
  onDelete
}: {
  target: TaskDialogTarget;
  onClose: () => void;
  onDelete: () => void | Promise<void>;
}) {
  const [deleting, setDeleting] = useState(false);

  async function submit() {
    setDeleting(true);
    try {
      await onDelete();
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="settings-dialog task-action-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="删除任务"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="settings-dialog-head">
          <div>
            <span>任务</span>
            <strong>删除</strong>
          </div>
          <button type="button" className="settings-close" aria-label="关闭" onClick={onClose}>
            ×
          </button>
        </header>
        <div className="settings-form">
          <p className="task-action-copy">
            删除 <strong>{target.name}</strong> 会移除这个任务的记录和本地运行文件。
          </p>
        </div>
        <footer className="settings-actions">
          <button type="button" onClick={onClose}>
            取消
          </button>
          <button type="button" className="danger" disabled={deleting} onClick={() => void submit()}>
            {deleting ? "删除中" : "删除"}
          </button>
        </footer>
      </section>
    </div>
  );
}

function TaskDetailPanel({
  caseDetail,
  progress,
  runCompatibility,
  runPackage,
  v2Elements,
  selectedV2ElementId,
  selectedAssetPackage,
  v2PackageError,
  v2AssetLoadingElementId,
  v2ActionPending,
  canForkV2FromSource,
  onSelectV2Element,
  onProcessV2Asset,
  onSetActiveV2Result,
  onForkV2FromSource
}: {
  caseDetail: CaseDetail | null;
  progress: CaseProgress | null;
  runCompatibility: RunCompatibilityMode;
  runPackage: V2RunPackage | null;
  v2Elements: V2ElementPlan[];
  selectedV2ElementId: string;
  selectedAssetPackage: V2AssetPackage | null;
  v2PackageError: string;
  v2AssetLoadingElementId: string;
  v2ActionPending: string;
  canForkV2FromSource: boolean;
  onSelectV2Element: (elementId: string) => void;
  onProcessV2Asset: (processor: V2ProcessorType, elementId?: string) => void;
  onSetActiveV2Result: (resultId: string) => void;
  onForkV2FromSource: () => void;
}) {
  if (!caseDetail) {
    return (
      <aside className="task-detail-panel">
        <EmptyState label="从任务里选择一张图" />
      </aside>
    );
  }
  return (
    <aside className="task-detail-panel">
      <PipelineProgressPanel caseDetail={caseDetail} progress={progress} />
      {runCompatibility === "legacy_readonly" && (
        <LegacyReadOnlyBanner
          canForkV2FromSource={canForkV2FromSource}
          actionPending={v2ActionPending === "fork"}
          onForkV2FromSource={onForkV2FromSource}
        />
      )}
      {runCompatibility === "v2" && (
        <V2AssetPackagePanel
          activeCase={caseDetail}
          runPackage={runPackage}
          elements={v2Elements}
          selectedElementId={selectedV2ElementId}
          selectedAssetPackage={selectedAssetPackage}
          loadingElementId={v2AssetLoadingElementId}
          packageError={v2PackageError}
          actionPending={v2ActionPending}
          onSelectElement={onSelectV2Element}
          onProcessAsset={onProcessV2Asset}
          onSetActiveResult={onSetActiveV2Result}
        />
      )}
      {caseDetail.case.error_message && <p className="detail-error">{shortenError(caseDetail.case.error_message)}</p>}
    </aside>
  );
}

function LegacyReadOnlyBanner({
  canForkV2FromSource,
  actionPending,
  onForkV2FromSource
}: {
  canForkV2FromSource: boolean;
  actionPending: boolean;
  onForkV2FromSource: () => void;
}) {
  return (
    <section className="legacy-readonly-banner">
      <div>
        <strong>历史结果只读</strong>
        <span>可以继续预览和下载已有 SVG / PPTX，但素材处理、SVG 编辑、重新组合和导出已关闭。</span>
      </div>
      {canForkV2FromSource ? (
        <button type="button" className={actionPending ? "running" : ""} disabled={actionPending} onClick={onForkV2FromSource}>
          {actionPending && <ButtonSpinner />}
          {actionPending ? "创建中" : "从源图创建 v2 run"}
        </button>
      ) : (
        <em>源图不可用，无法创建 v2 run</em>
      )}
    </section>
  );
}

function V2AssetPackagePanel({
  activeCase,
  runPackage,
  elements,
  selectedElementId,
  selectedAssetPackage,
  loadingElementId,
  packageError,
  actionPending,
  onSelectElement,
  onProcessAsset,
  onSetActiveResult
}: {
  activeCase: CaseDetail | null;
  runPackage: V2RunPackage | null;
  elements: V2ElementPlan[];
  selectedElementId: string;
  selectedAssetPackage: V2AssetPackage | null;
  loadingElementId: string;
  packageError: string;
  actionPending: string;
  onSelectElement: (elementId: string) => void;
  onProcessAsset: (processor: V2ProcessorType, elementId?: string) => void;
  onSetActiveResult: (resultId: string) => void;
}) {
  const selectedElement = elements.find((element) => element.element_id === selectedElementId) || null;
  const packageByElementId = useMemo(() => {
    const items = new Map<string, V2AssetPackage>();
    (runPackage?.asset_packages || []).forEach((assetPackage) => {
      items.set(assetPackage.element_id, assetPackage);
    });
    if (selectedAssetPackage) {
      items.set(selectedAssetPackage.element_id, selectedAssetPackage);
    }
    return items;
  }, [runPackage, selectedAssetPackage]);
  const selectedPackage = selectedElement ? packageByElementId.get(selectedElement.element_id) || null : null;
  const packageStatus = selectedPackage?.status || "pending";
  const packageStatusClass = v2AssetStatusClass(packageStatus);
  const activeResultId = selectedPackage?.active_result?.result_id || "";
  const activeResultUrl = v2AssetResultUrl(activeCase, selectedPackage?.active_result || null);
  const processedCount = elements.filter((element) => packageByElementId.get(element.element_id)?.status === "ok").length;
  const pendingCount = elements.filter((element) => {
    const status = packageByElementId.get(element.element_id)?.status || "pending";
    return status === "pending" || status === "running";
  }).length;
  const canProcess = Boolean(selectedElement && !actionPending);
  const activeProcessAction = (elementId: string, processor: V2ProcessorType) => actionPending === `process:${elementId}:${processor}`;
  const activeAction = (prefix: string) => actionPending.startsWith(prefix);

  return (
    <section className="v2-package-panel">
      <header className="v2-package-head">
        <div>
          <span>Assets 处理</span>
          <strong>{elements.length} 个元素 · {processedCount} 已处理 · {pendingCount} 待处理</strong>
        </div>
      </header>

      {packageError && <p className="detail-error">{shortenError(packageError)}</p>}

      <div className="v2-asset-table-wrap" aria-label="v2 assets 表格">
        {elements.length > 0 ? (
          <table className="v2-asset-table">
            <thead>
              <tr>
                <th>Asset</th>
                <th>类型</th>
                <th>处理</th>
                <th>状态</th>
                <th>结果</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {elements.map((element) => {
                const assetPackage = packageByElementId.get(element.element_id) || null;
                const status = assetPackage?.status || "pending";
                const plannedProcessor = v2PlannedProcessor(element);
                const activeResult = assetPackage?.active_result || null;
                const rowPending = plannedProcessor ? activeProcessAction(element.element_id, plannedProcessor) : false;
                const rowSelected = element.element_id === selectedElementId;
                const rowLoading = loadingElementId === element.element_id;
                return (
                  <tr
                    key={element.element_id}
                    className={rowSelected ? "active" : ""}
                    onClick={() => onSelectElement(element.element_id)}
                  >
                    <td>
                      <strong>{element.element_id}</strong>
                      <span>{bboxText(element.bbox)}</span>
                    </td>
                    <td>{humanize(element.element_type)}</td>
                    <td>{humanize(element.processing_intent.processing_type)}</td>
                    <td>
                      <span className={`v2-asset-status-pill ${v2AssetStatusClass(status)}`}>{rowLoading ? "加载中" : humanize(status)}</span>
                    </td>
                    <td>
                      <span>{activeResult ? v2ResultLabel(activeResult) : "未生成"}</span>
                    </td>
                    <td>
                      {plannedProcessor ? (
                        <button
                          type="button"
                          className={rowPending ? "running" : ""}
                          disabled={Boolean(actionPending)}
                          onClick={(event) => {
                            event.stopPropagation();
                            onProcessAsset(plannedProcessor, element.element_id);
                          }}
                        >
                          {rowPending && <ButtonSpinner />}
                          处理
                        </button>
                      ) : element.processing_intent.processing_type === "chart_rebuild_reserved" ? (
                        <button type="button" disabled title="图表 Agent 接口已预留，当前版本不执行">
                          预留
                        </button>
                      ) : (
                        <button type="button" disabled>
                          自绘
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          <EmptyState label="还没有 v2 元素" />
        )}
      </div>

      <div className="v2-asset-drawer">
        {selectedElement ? (
          <>
            <div className="v2-asset-summary">
              <div>
                <span>类型</span>
                <strong>{humanize(selectedElement.element_type)}</strong>
              </div>
              <div>
                <span>XYWH</span>
                <strong>{bboxText(selectedElement.bbox)}</strong>
              </div>
              <div>
                <span>处理</span>
                <strong>{humanize(selectedElement.processing_intent.processing_type)}</strong>
              </div>
              <div className={packageStatusClass}>
                <span>状态</span>
                <strong>{humanize(packageStatus)}</strong>
              </div>
            </div>
            <div className={activeResultUrl ? "v2-result-preview" : "v2-result-preview is-empty"}>
              {activeResultUrl ? (
                <a href={activeResultUrl} target="_blank" rel="noreferrer">
                  <img src={activeResultUrl} alt="" />
                </a>
              ) : (
                <span>还没有 active result</span>
              )}
            </div>
            <div className="v2-asset-intent">
              <span>{selectedElement.processing_intent.object_type}</span>
              <code>{compactJson(selectedElement.processing_intent.parameters)}</code>
            </div>

            <div className="v2-processor-toolbar" aria-label="v2 资产处理器">
              {V2_PROCESSABLE_PROCESSORS.map((processor) => (
                <button
                  type="button"
                  key={processor}
                  disabled={!canProcess || activeAction("process:")}
                  onClick={() => onProcessAsset(processor, selectedElement.element_id)}
                >
                  {activeProcessAction(selectedElement.element_id, processor) && <ButtonSpinner />}
                  {v2ProcessorLabel(processor)}
                </button>
              ))}
              <button type="button" className="asset-status-unsupported" disabled title="图表 Agent 接口已预留，当前版本不执行">
                Chart Agent
              </button>
            </div>

            {selectedPackage?.failure && (
              <p className="asset-status-failed">{shortenError(selectedPackage.failure)}</p>
            )}

            <div className="v2-result-list">
              <div className="v2-subhead">
                <span>处理结果</span>
                <strong>{activeResultId || "未设置"}</strong>
              </div>
              {(selectedPackage?.all_results || []).map((result) => {
                const resultUrl = v2AssetResultUrl(activeCase, result);
                return (
                  <div className="v2-result-row" key={result.result_id}>
                    <div>
                      <strong>{result.result_id}</strong>
                      <span>{humanize(result.processor_type)} · {humanize(result.kind)}{result.path ? ` · ${result.path}` : ""}</span>
                    </div>
                    <div className="v2-result-actions">
                      {resultUrl && <a href={resultUrl} target="_blank" rel="noreferrer">查看</a>}
                      {result.result_id === activeResultId ? (
                        <em>Active</em>
                      ) : (
                        <button type="button" disabled={Boolean(actionPending)} onClick={() => onSetActiveResult(result.result_id)}>
                          {actionPending === `active:${result.result_id}` && <ButtonSpinner />}
                          设为 Active
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
              {(!selectedPackage || selectedPackage.all_results.length === 0) && <EmptyState label="还没有处理结果" />}
            </div>

            <div className="v2-processor-history">
              <div className="v2-subhead">
                <span>处理历史</span>
                <strong>{selectedPackage?.processor_runs.length || 0}</strong>
              </div>
              {(selectedPackage?.processor_runs || []).slice().reverse().map((run, index) => (
                <div className="v2-history-row" key={`${run.processor_type}-${run.started_at}-${index}`}>
                  <div>
                    <strong>{humanize(run.processor_type)}</strong>
                    <span>{durationText(run.started_at, run.ended_at)}</span>
                  </div>
                  <em className={run.status === "failed" ? "asset-status-failed" : run.status === "unsupported" ? "asset-status-unsupported" : ""}>
                    {humanize(run.status)}
                  </em>
                </div>
              ))}
              {(!selectedPackage || selectedPackage.processor_runs.length === 0) && <EmptyState label="还没有处理历史" />}
            </div>
          </>
        ) : (
          <EmptyState label="选择一个 v2 元素" />
        )}
      </div>
    </section>
  );
}

function V2AssetsWorkspace({
  activeCase,
  runPackage,
  elements,
  selectedElementId,
  selectedAssetPackage,
  packageError,
  loadingElementId,
  actionPending,
  figureUrl,
  runInProgress,
  onBackToBoard,
  onSelectElement,
  onProcessAsset,
  onSetActiveResult,
  onRun
}: {
  activeCase: CaseDetail | null;
  runPackage: V2RunPackage | null;
  elements: V2ElementPlan[];
  selectedElementId: string;
  selectedAssetPackage: V2AssetPackage | null;
  packageError: string;
  loadingElementId: string;
  actionPending: string;
  figureUrl: string;
  runInProgress: boolean;
  onBackToBoard: () => void;
  onSelectElement: (elementId: string) => void;
  onProcessAsset: (processor: V2ProcessorType, elementId?: string) => void;
  onSetActiveResult: (resultId: string) => void;
  onRun: () => void;
}) {
  const editorRef = useRef<HTMLElement | null>(null);
  const [zoom, setZoom] = useState(0.72);
  const runPending = runInProgress || actionPending === "compose";
  const canRun = Boolean(runPackage && !runPending && !actionPending && !hasBlockingAssetPackage(runPackage));

  const changeZoom = useCallback((delta: number) => {
    setZoom((value) => clamp(Number((value + delta).toFixed(2)), 0.25, 2.5));
  }, []);

  useEffect(() => {
    const root = editorRef.current;
    if (!root) return;

    function handleWheel(event: globalThis.WheelEvent) {
      if (!event.ctrlKey && !event.metaKey) return;
      event.preventDefault();
      if (event.target instanceof Element && event.target.closest(".canvas-stage")) {
        changeZoom(event.deltaY < 0 ? 0.03 : -0.03);
      }
    }

    root.addEventListener("wheel", handleWheel, { passive: false, capture: true });
    return () => root.removeEventListener("wheel", handleWheel, { capture: true });
  }, [changeZoom]);

  const topbarTarget = typeof document !== "undefined" ? document.getElementById("drawai-view-controls") : null;
  const topbarPortal = topbarTarget
    ? createPortal(
        <div className="editor-banner-controls assets-banner-controls">
          <button className="home-button" title="返回任务" aria-label="返回任务" onClick={onBackToBoard}>
            <HomeIcon />
          </button>
          <div className="editor-title">
            <div>
              <strong>{activeCase?.case.name || "未选择图片"}</strong>
              <span>{humanize(activeCase?.case.status || "idle")} · {humanize(activeCase?.case.stage || "select a case")}</span>
            </div>
          </div>
          <div className="toolbar-note">
            Assets · {elements.length}
          </div>
          <div className="editor-toolbar">
            <div className="tool-group">
              <button className="icon-button" title="缩小" onClick={() => changeZoom(-0.1)}>−</button>
              <span className="zoom-readout">{Math.round(zoom * 100)}%</span>
              <button className="icon-button" title="放大" onClick={() => changeZoom(0.1)}>+</button>
            </div>
          </div>
          <div className="editor-actions">
            <button
              type="button"
              className={runPending ? "primary run-button running" : "primary run-button"}
              disabled={!canRun}
              onClick={onRun}
            >
              {runPending && <ButtonSpinner />}
              {runPending ? "运行中" : "运行"}
            </button>
          </div>
        </div>,
        topbarTarget
      )
    : null;

  return (
    <>
      {topbarPortal}
      <main ref={editorRef} className="editor-workspace v2-assets-workspace">
        <div className="asset-stage v2-assets-stage" data-asset-view="extraction">
          <div className="v2-assets-workspace-grid">
            <V2AssetCanvas
              activeCase={activeCase}
              runPackage={runPackage}
              elements={elements}
              selectedElementId={selectedElementId}
              selectedAssetPackage={selectedAssetPackage}
              figureUrl={figureUrl}
              zoom={zoom}
              onSelectElement={onSelectElement}
            />
            <aside className="v2-assets-workspace-panel">
              <V2AssetPackagePanel
                activeCase={activeCase}
                runPackage={runPackage}
                elements={elements}
                selectedElementId={selectedElementId}
                selectedAssetPackage={selectedAssetPackage}
                loadingElementId={loadingElementId}
                packageError={packageError}
                actionPending={actionPending}
                onSelectElement={onSelectElement}
                onProcessAsset={onProcessAsset}
                onSetActiveResult={onSetActiveResult}
              />
            </aside>
          </div>
        </div>
      </main>
    </>
  );
}

function V2AssetCanvas({
  activeCase,
  runPackage,
  elements,
  selectedElementId,
  selectedAssetPackage,
  figureUrl,
  zoom,
  onSelectElement
}: {
  activeCase: CaseDetail | null;
  runPackage: V2RunPackage | null;
  elements: V2ElementPlan[];
  selectedElementId: string;
  selectedAssetPackage: V2AssetPackage | null;
  figureUrl: string;
  zoom: number;
  onSelectElement: (elementId: string) => void;
}) {
  const imageRef = useRef<HTMLImageElement | null>(null);
  const [naturalSize, setNaturalSize] = useState({ width: 1, height: 1 });
  const [hoveredElementId, setHoveredElementId] = useState("");
  const selectedElement = elements.find((element) => element.element_id === selectedElementId) || null;
  const canvasWidth = naturalSize.width > 1 ? Math.max(320, Math.round(naturalSize.width * zoom)) : undefined;
  const packageByElementId = useMemo(() => {
    const items = new Map<string, V2AssetPackage>();
    (runPackage?.asset_packages || []).forEach((assetPackage) => {
      items.set(assetPackage.element_id, assetPackage);
    });
    if (selectedAssetPackage) {
      items.set(selectedAssetPackage.element_id, selectedAssetPackage);
    }
    return items;
  }, [runPackage, selectedAssetPackage]);
  const visibleElements = elements
    .map((element, originalIndex) => ({ element, originalIndex, area: v2BBoxArea(element.bbox) }))
    .sort((left, right) => right.area - left.area || left.originalIndex - right.originalIndex);
  const hoveredElement = visibleElements.find(({ element }) => element.element_id === hoveredElementId)?.element || null;
  const selectedStatus = selectedElement ? packageByElementId.get(selectedElement.element_id)?.status || "pending" : "";
  const activeResultId = selectedElement ? packageByElementId.get(selectedElement.element_id)?.active_result?.result_id || "" : "";

  return (
    <section className="canvas-layout v2-assets-layout">
      <div className="canvas-stage v2-assets-canvas">
        {figureUrl ? (
          <div className="image-overlay-wrap v2-image-overlay-wrap" style={canvasWidth ? { width: `${canvasWidth}px` } : undefined}>
            <img
              ref={imageRef}
              src={figureUrl}
              alt=""
              draggable={false}
              onLoad={(event) => setNaturalSize({ width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight })}
            />
            {visibleElements.map(({ element }, layerIndex) => {
              const assetPackage = packageByElementId.get(element.element_id);
              return (
                <V2ElementBox
                  key={element.element_id}
                  element={element}
                  naturalSize={naturalSize}
                  selected={element.element_id === selectedElementId}
                  status={assetPackage?.status || "pending"}
                  zIndex={layerIndex + 1}
                  onSelect={() => onSelectElement(element.element_id)}
                  onHover={() => setHoveredElementId(element.element_id)}
                  onLeave={() => setHoveredElementId((id) => (id === element.element_id ? "" : id))}
                />
              );
            })}
            {hoveredElement && <V2ElementTooltip element={hoveredElement} naturalSize={naturalSize} status={packageByElementId.get(hoveredElement.element_id)?.status || "pending"} />}
          </div>
        ) : (
          <EmptyState label="原图还没准备好" />
        )}
      </div>
      {selectedElement && (
        <div className="selection-bar v2-selection-bar">
          <strong>{selectedElement.element_id}</strong>
          <span>{humanize(selectedElement.element_type)} · {humanize(selectedElement.processing_intent.processing_type)}</span>
          <em className={selectedStatus === "failed" ? "asset-status-failed" : selectedStatus === "unsupported" ? "asset-status-unsupported" : ""}>
            {humanize(selectedStatus)}
          </em>
          {activeResultId && <code>{activeResultId}</code>}
        </div>
      )}
      {!activeCase && <EmptyState label="请选择一张图" />}
    </section>
  );
}

function V2ElementBox({
  element,
  naturalSize,
  selected,
  status,
  zIndex,
  onSelect,
  onHover,
  onLeave
}: {
  element: V2ElementPlan;
  naturalSize: { width: number; height: number };
  selected: boolean;
  status: V2AssetStatus;
  zIndex: number;
  onSelect: () => void;
  onHover: () => void;
  onLeave: () => void;
}) {
  const style = { ...v2BBoxStyle(element.bbox, naturalSize), zIndex };
  const statusClass = status === "failed" ? "v2-asset-box-failed" : status === "unsupported" ? "v2-asset-box-unsupported" : "";
  return (
    <div
      className={`asset-box v2-asset-box ${v2ElementProcessingClass(element)} ${statusClass} ${selected ? "selected" : ""}`}
      data-asset-id={element.element_id}
      role="button"
      tabIndex={0}
      style={style}
      onPointerDown={(event) => {
        event.stopPropagation();
        onSelect();
      }}
      onPointerEnter={onHover}
      onPointerLeave={onLeave}
      onMouseEnter={onHover}
      onMouseLeave={onLeave}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect();
        }
      }}
    >
      <span className="asset-badge">
        {element.element_id} · {humanize(element.element_type)} · {humanize(element.processing_intent.processing_type)}
      </span>
      <span className="v2-asset-status-chip">{humanize(status)}</span>
    </div>
  );
}

function V2ElementTooltip({
  element,
  naturalSize,
  status
}: {
  element: V2ElementPlan;
  naturalSize: { width: number; height: number };
  status: V2AssetStatus;
}) {
  return (
    <div className={`canvas-tooltip ${v2ElementProcessingClass(element)}`} style={v2TooltipStyle(element.bbox, naturalSize)}>
      <strong>{element.element_id}</strong>
      <em>{humanize(element.element_type)} · {humanize(element.processing_intent.object_type)}</em>
      <small>{humanize(element.processing_intent.processing_type)} · {humanize(status)} · {element.confidence}</small>
      <p>{element.change_reason || bboxText(element.bbox)}</p>
    </div>
  );
}

function SvgWorkspace({
  activeCase,
  progress,
  onBackToBoard,
  onError,
  onExportPptx,
  onDownloadPptx,
  pptxExporting,
  canRunFromAssets,
  runInProgress,
  onRunFromAssets,
  readOnly
}: {
  activeCase: CaseDetail | null;
  progress: CaseProgress | null;
  onBackToBoard: () => void;
  onError: (message: string) => void;
  onExportPptx: (caseId: string) => Promise<ArtifactRecord[]>;
  onDownloadPptx: (caseId: string, artifact: ArtifactRecord) => void | Promise<void>;
  pptxExporting: boolean;
  canRunFromAssets: boolean;
  runInProgress: boolean;
  onRunFromAssets: () => void;
  readOnly: boolean;
}) {
  return (
    <main className="svg-workspace">
      {activeCase ? (
        <SvgResultStudio
          caseDetail={activeCase}
          progress={progress}
          onBackToBoard={onBackToBoard}
          onError={onError}
          onExportPptx={onExportPptx}
          onDownloadPptx={onDownloadPptx}
          pptxExporting={pptxExporting}
          canRunFromAssets={canRunFromAssets}
          runInProgress={runInProgress}
          onRunFromAssets={onRunFromAssets}
          readOnly={readOnly}
          standalone
        />
      ) : (
        <>
          <section className="svg-canvas-workspace">
          <EmptyState label="请选择已有 SVG 结果的图片" />
          </section>
        </>
      )}
    </main>
  );
}

function SvgResultStudio({
  caseDetail,
  progress,
  onBackToBoard,
  onError,
  onExportPptx,
  onDownloadPptx,
  pptxExporting,
  canRunFromAssets,
  runInProgress,
  onRunFromAssets,
  readOnly,
  standalone = false
}: {
  caseDetail: CaseDetail;
  progress: CaseProgress | null;
  onBackToBoard: () => void;
  onError: (message: string) => void;
  onExportPptx: (caseId: string) => Promise<ArtifactRecord[]>;
  onDownloadPptx: (caseId: string, artifact: ArtifactRecord) => void | Promise<void>;
  pptxExporting: boolean;
  canRunFromAssets: boolean;
  runInProgress: boolean;
  onRunFromAssets: () => void;
  readOnly: boolean;
  standalone?: boolean;
}) {
  const caseId = caseDetail.case.case_id;
  const semanticArtifact = latestArtifact(caseDetail.artifacts, "semantic_svg");
  const semanticFile = latestProgressFile(progress, "semantic_svg");
  const figureArtifact = latestArtifact(caseDetail.artifacts, "figure");
  const pptxArtifact = latestArtifact(caseDetail.artifacts, "pptx");
  const svgUrl = semanticArtifact?.url || semanticFile?.url || "";
  const originalImageUrl = figureArtifact?.url || "";
  const [sourceText, setSourceText] = useState("");
  const [draftText, setDraftText] = useState("");
  const [selectedPath, setSelectedPath] = useState("");
  const [zoom, setZoom] = useState(1);
  const [showOriginalCompare, setShowOriginalCompare] = useState(false);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const [undoStack, setUndoStack] = useState<string[]>([]);
  const [selectionOverlay, setSelectionOverlay] = useState<SvgSelectionOverlay | null>(null);
  const surfaceRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<SvgDragState | null>(null);
  const previousCaseId = useRef(caseId);

  useEffect(() => {
    const caseChanged = previousCaseId.current !== caseId;
    previousCaseId.current = caseId;
    setSourceText("");
    setDraftText("");
    setSelectedPath("");
    setShowOriginalCompare(false);
    if (caseChanged) setStatus("");
    setUndoStack([]);
    if (!svgUrl) return;
    let alive = true;
    getSvgSource(caseId)
      .then((response) => {
        if (!alive) return;
        setSourceText(response.svg);
        setDraftText(response.svg);
      })
      .catch((err) => {
        if (alive) onError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      alive = false;
    };
  }, [caseId, svgUrl, onError]);

  const model = useMemo(() => buildSvgPreviewModel(draftText, caseId, selectedPath), [draftText, caseId, selectedPath]);
  const dirty = Boolean(sourceText) && draftText !== sourceText;
  const selectedElement = model.elements.find((element) => element.path === selectedPath) || null;
  const syncSelectionOverlay = useCallback(() => {
    setSelectionOverlay(svgSelectionOverlay(surfaceRef.current, selectedPath));
  }, [selectedPath]);

  useLayoutEffect(() => {
    if (showOriginalCompare) {
      setSelectionOverlay(null);
      return;
    }
    syncSelectionOverlay();
  }, [model.svg, selectedPath, showOriginalCompare, zoom, syncSelectionOverlay]);

  useEffect(() => {
    if (!originalImageUrl) setShowOriginalCompare(false);
  }, [originalImageUrl]);

  useEffect(() => {
    const shell = surfaceRef.current;
    if (!shell) return;
    shell.addEventListener("scroll", syncSelectionOverlay, { passive: true });
    window.addEventListener("resize", syncSelectionOverlay);
    return () => {
      shell.removeEventListener("scroll", syncSelectionOverlay);
      window.removeEventListener("resize", syncSelectionOverlay);
    };
  }, [syncSelectionOverlay]);

  function recordSvgUndo() {
    if (!draftText) return;
    setUndoStack((items) => (items[items.length - 1] === draftText ? items : [...items.slice(-39), draftText]));
  }

  function undoSvgEdit() {
    setUndoStack((items) => {
      const previous = items[items.length - 1];
      if (!previous) return items;
      setDraftText(previous);
      return items.slice(0, -1);
    });
  }

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (isEditableTarget(event.target)) return;
      if (readOnly) return;
      if ((event.metaKey || event.ctrlKey) && !event.shiftKey && event.key.toLowerCase() === "z") {
        event.preventDefault();
        undoSvgEdit();
        return;
      }
      if ((event.key === "Backspace" || event.key === "Delete") && selectedPath) {
        event.preventDefault();
        deleteSvgElement(selectedPath);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [draftText, readOnly, selectedPath]);

  function changeCanvasZoom(delta: number) {
    setZoom((value) => clamp(Number((value + delta).toFixed(2)), 0.3, 4));
  }

  function onCanvasWheel(event: WheelEvent<HTMLDivElement>) {
    if (!event.ctrlKey && !event.metaKey) return;
    event.preventDefault();
    changeCanvasZoom(event.deltaY > 0 ? -0.08 : 0.08);
  }

  function beginOriginalCompare(event: PointerEvent<HTMLButtonElement>) {
    if (!originalImageUrl) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    setShowOriginalCompare(true);
  }

  function endOriginalCompare(event: PointerEvent<HTMLButtonElement>) {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    setShowOriginalCompare(false);
  }

  function beginSvgDrag(event: PointerEvent<HTMLDivElement>) {
    if (readOnly || !draftText || model.error || showOriginalCompare) return;
    if (event.target instanceof Element && event.target.closest(".svg-resize-handle, .svg-inline-text-editor")) return;
    const target = event.target instanceof Element ? event.target.closest("[data-drawai-path]") : null;
    if (!target) {
      setSelectedPath("");
      return;
    }
    const path = target.getAttribute("data-drawai-path") || "";
    if (!path) return;
    event.preventDefault();
    setSelectedPath(path);
    recordSvgUndo();
    const svgElement = surfaceRef.current?.querySelector("svg");
    const rect = svgElement?.getBoundingClientRect();
    if (!rect) return;
    const viewBox = parseSvgViewBox(svgElement?.getAttribute("viewBox") || "") || fallbackSvgViewport(svgElement, rect);
    dragRef.current = {
      kind: "move",
      path,
      baseText: draftText,
      startClientX: event.clientX,
      startClientY: event.clientY,
      scaleX: viewBox.width / Math.max(1, rect.width),
      scaleY: viewBox.height / Math.max(1, rect.height)
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function beginSvgResize(event: PointerEvent<HTMLButtonElement>) {
    if (readOnly || !selectedPath || !draftText || model.error) return;
    event.preventDefault();
    event.stopPropagation();
    recordSvgUndo();
    const center = selectedSvgElementCenter(surfaceRef.current, selectedPath);
    const startDistance = selectionOverlay
      ? Math.hypot(event.clientX - selectionOverlay.centerClientX, event.clientY - selectionOverlay.centerClientY)
      : 1;
    dragRef.current = {
      kind: "resize",
      path: selectedPath,
      baseText: draftText,
      center,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startDistance: Math.max(1, startDistance)
    };
  }

  function moveSvgDrag(event: PointerEvent<HTMLDivElement>) {
    const drag = dragRef.current;
    if (!drag) return;
    if (drag.kind === "move") {
      const dx = (event.clientX - drag.startClientX) * drag.scaleX;
      const dy = (event.clientY - drag.startClientY) * drag.scaleY;
      setDraftText(translateSvgElement(drag.baseText, drag.path, dx, dy));
      return;
    }
    const centerClient = selectionOverlay
      ? { x: selectionOverlay.centerClientX, y: selectionOverlay.centerClientY }
      : { x: drag.startClientX, y: drag.startClientY };
    const distance = Math.hypot(event.clientX - centerClient.x, event.clientY - centerClient.y);
    const factor = clamp(distance / drag.startDistance, 0.08, 12);
    setDraftText(scaleSvgElement(drag.baseText, drag.path, factor, drag.center));
  }

  function endSvgDrag(event: PointerEvent<HTMLDivElement>) {
    if (!dragRef.current) return;
    dragRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function updateSelectedText(value: string) {
    if (readOnly || !selectedPath || !draftText || model.error) return;
    setDraftText(updateSvgElementText(draftText, selectedPath, value));
  }

  function deleteSvgElement(path = selectedPath) {
    if (readOnly || !path || !draftText || model.error) return;
    recordSvgUndo();
    setDraftText(removeSvgElement(draftText, path));
    setSelectedPath("");
    setSelectionOverlay(null);
  }

  function onSvgContextMenu(event: MouseEvent<HTMLDivElement>) {
    if (readOnly) return;
    const target = event.target instanceof Element ? event.target.closest("[data-drawai-path]") : null;
    if (!target) return;
    const path = target.getAttribute("data-drawai-path") || "";
    if (!path) return;
    event.preventDefault();
    setSelectedPath(path);
    deleteSvgElement(path);
  }

  async function savePng() {
    if (!draftText || model.error) return;
    setSaving(true);
    setStatus("正在准备 PNG...");
    try {
      const renderedSvg = surfaceRef.current?.querySelector(".svg-artboard svg") as SVGSVGElement | null;
      await exportSvgPng(model.svg, `${caseDetail.case.name.replace(/[^a-z0-9._-]+/gi, "_") || "drawai"}.png`, caseId, renderedSvg);
      setStatus("PNG 已导出。");
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
      setStatus("");
    } finally {
      setSaving(false);
    }
  }

  async function exportPptx() {
    if (pptxArtifact || pptxExporting || !svgUrl) return;
    setStatus("正在导出 PPTX...");
    try {
      await onExportPptx(caseId);
      setStatus("PPTX 已导出。");
    } catch {
      setStatus("");
    }
  }

  async function downloadExistingPptx() {
    if (!pptxArtifact) return;
    setStatus("正在准备 PPTX...");
    try {
      await onDownloadPptx(caseId, pptxArtifact);
      setStatus("");
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
      setStatus("");
    }
  }

  const topbarTarget = typeof document !== "undefined" ? document.getElementById("drawai-view-controls") : null;
  const topbarPortal = topbarTarget
    ? createPortal(
        <div className="editor-banner-controls svg-banner-controls">
          <button className="home-button" title="返回任务" aria-label="返回任务" onClick={onBackToBoard}>
            <HomeIcon />
          </button>
          <div className="editor-title">
            <strong>{caseDetail.case.name}</strong>
            <span>{readOnly ? "历史只读结果" : dirty ? "有未保存的本地修改" : `${humanize(caseDetail.case.status)} · ${humanize(caseDetail.case.phase)} / ${humanize(caseDetail.case.stage)}`}</span>
          </div>
          {svgUrl ? (
            <div className="editor-toolbar" aria-label="SVG 画布工具">
              <div className="tool-group">
                <button className="icon-button" title="缩小" disabled={zoom <= 0.3} onClick={() => changeCanvasZoom(-0.1)}>-</button>
                <span className="zoom-readout">{Math.round(zoom * 100)}%</span>
                <button className="icon-button" title="放大" disabled={zoom >= 4} onClick={() => changeCanvasZoom(0.1)}>+</button>
                {!readOnly && (
                  <button className="icon-button" title="撤销 Command+Z" disabled={undoStack.length === 0} onClick={undoSvgEdit} aria-label="撤销">
                    <UndoToolIcon />
                  </button>
                )}
                <button
                  className="compare-preview-button"
                  title={originalImageUrl ? "按住显示原图，松开恢复 SVG" : "原图还没准备好"}
                  disabled={!originalImageUrl}
                  aria-pressed={showOriginalCompare}
                  onPointerDown={beginOriginalCompare}
                  onPointerUp={endOriginalCompare}
                  onPointerCancel={endOriginalCompare}
                  onKeyDown={(event) => {
                    if (!originalImageUrl || (event.key !== " " && event.key !== "Enter")) return;
                    event.preventDefault();
                    setShowOriginalCompare(true);
                  }}
                  onKeyUp={(event) => {
                    if (event.key !== " " && event.key !== "Enter") return;
                    event.preventDefault();
                    setShowOriginalCompare(false);
                  }}
                  onBlur={() => setShowOriginalCompare(false)}
                >
                  {showOriginalCompare ? "原图" : "对比"}
                </button>
              </div>
            </div>
          ) : (
            <div className="toolbar-note">SVG 结果还没准备好</div>
          )}
          {readOnly ? (
            <div className="toolbar-note">历史结果只读，可在任务卡下载已有文件</div>
          ) : (
          <div className="editor-actions">
            <button className={runInProgress ? "running" : ""} disabled={!canRunFromAssets} onClick={onRunFromAssets}>
              {runInProgress && <ButtonSpinner />}
              {runInProgress ? "运行中" : "运行"}
            </button>
            <div className="export-menu">
              <button className="primary export-menu-button" disabled={!draftText || Boolean(model.error) || saving}>
                {saving ? "导出中" : "导出"}
              </button>
              <div className="export-menu-options" role="menu" aria-label="导出格式">
                <button type="button" disabled={!draftText || Boolean(model.error) || saving} onClick={savePng} role="menuitem">
                  PNG
                </button>
                {pptxArtifact ? (
                  <button type="button" onClick={() => void downloadExistingPptx()} role="menuitem">PPTX</button>
                ) : (
                  <button type="button" disabled={pptxExporting || !svgUrl} onClick={() => void exportPptx()} role="menuitem">
                    {pptxExporting ? "导出中" : "PPTX"}
                  </button>
                )}
                <span className="disabled psd-disabled" role="menuitem" aria-disabled="true" title="后续支持中">PSD</span>
              </div>
            </div>
          </div>
          )}
        </div>,
        topbarTarget
      )
    : null;

  if (!svgUrl) {
    return (
      <>
        {topbarPortal}
        <section className={standalone ? "svg-studio svg-studio-standalone" : "svg-studio"}>
          <EmptyState label="SVG 结果还没准备好" />
        </section>
      </>
    );
  }

  return (
    <>
      {topbarPortal}
      <section className={standalone ? "svg-studio svg-studio-standalone" : "svg-studio"}>
        {model.error ? (
          <p className="svg-studio-error">{model.error}</p>
        ) : (
          <div className="svg-studio-body">
          <div
            className="svg-canvas-shell"
            ref={surfaceRef}
            onPointerDown={beginSvgDrag}
            onPointerMove={moveSvgDrag}
            onPointerUp={endSvgDrag}
            onPointerCancel={endSvgDrag}
            onWheel={onCanvasWheel}
            onContextMenu={onSvgContextMenu}
          >
            <div className="svg-artboard" style={{ width: `${zoom * 100}%` }}>
              {showOriginalCompare && originalImageUrl ? (
                <img className="svg-compare-image" src={originalImageUrl} alt="用户上传的原始图" draggable={false} />
              ) : (
                <div dangerouslySetInnerHTML={{ __html: model.svg }} />
              )}
              {!readOnly && !showOriginalCompare && selectedElement && selectionOverlay && (
                <>
                  <div className="svg-selection-box" style={svgOverlayStyle(selectionOverlay)}>
                    {["nw", "ne", "sw", "se"].map((handle) => (
                      <button key={handle} className={`svg-resize-handle ${handle}`} aria-label={`调整大小 ${handle}`} onPointerDown={beginSvgResize} />
                    ))}
                  </div>
                  {selectedElement.textEditable && (
                    <input
                      className="svg-inline-text-editor"
                      style={svgTextEditorStyle(selectionOverlay)}
                      value={selectedElement.text}
                      spellCheck={false}
                      onPointerDown={(event) => event.stopPropagation()}
                      onFocus={recordSvgUndo}
                      onChange={(event) => updateSelectedText(event.target.value)}
                    />
                  )}
                </>
              )}
            </div>
          </div>
          </div>
        )}
        {status && <p className="svg-studio-status">{status}</p>}
      </section>
    </>
  );
}

function PipelineProgressPanel({ caseDetail, progress }: { caseDetail: CaseDetail; progress: CaseProgress | null }) {
  const stageRuns = progress?.stage_runs || caseDetail.stage_runs;
  const files = progress?.files || [];
  return (
    <section className="pipeline-card">
      <div className="pipeline-timeline">
        {PIPELINE_GROUPS.map((group, index) => (
          <div className="pipeline-group" key={group.title}>
            <div className="pipeline-group-title">
              <span className="pipeline-step">第 {index + 1} 步</span>
              <strong>{group.title}</strong>
              <span>{group.subtitle}</span>
            </div>
            {group.nodes.map((node) => {
              const status = pipelineNodeState(node, caseDetail, stageRuns, files, caseDetail.artifacts);
              return <PipelineNodeRow key={node.stage} node={status} />;
            })}
          </div>
        ))}
      </div>
    </section>
  );
}

function PipelineNodeRow({
  node
}: {
  node: ReturnType<typeof pipelineNodeState>;
}) {
  return (
    <div className={`pipeline-node ${node.state}`}>
      <span className="pipeline-signal" aria-hidden="true" />
      <div>
        <strong>{node.title}</strong>
        <span>{node.meta}</span>
        {node.error && <p>{shortenError(node.error)}</p>}
      </div>
      <em>{stateLabel(node.state)}</em>
      {node.description && <div className="pipeline-node-tip" role="tooltip">{node.description}</div>}
    </div>
  );
}

function TaskSelectionWorkspace({
  batches,
  activeBatch,
  activeCase,
  assetsReady,
  canvasReady,
  runInProgress,
  canRunFromAssets,
  runCompatibility,
  caseActionPendingId,
  pptxExportPendingCaseId,
  batchPptxDownloadPendingId,
  batchRunPendingId,
  onOpenSubmit,
  onOpenCaseAssets,
  onOpenSvgEditor,
  onRenameBatch,
  onDeleteBatch,
  onRunBatch,
  onSelectBatch,
  onFocusCase,
  onSelectCase,
  onRunFromAssets,
  onRetryCase,
  onExportPptx,
  onDownloadPptx,
  onDownloadBatchPptx
}: {
  batches: BatchRecord[];
  activeBatch: BatchDetail | null;
  activeCase: CaseDetail | null;
  assetsReady: boolean;
  canvasReady: boolean;
  runInProgress: boolean;
  canRunFromAssets: boolean;
  runCompatibility: RunCompatibilityMode;
  caseActionPendingId: string;
  pptxExportPendingCaseId: string;
  batchPptxDownloadPendingId: string;
  batchRunPendingId: string;
  onOpenSubmit: () => void;
  onOpenCaseAssets: (caseId: string) => void;
  onOpenSvgEditor: () => void;
  onRenameBatch: (batch: BatchRecord) => void;
  onDeleteBatch: (batch: BatchRecord) => void;
  onRunBatch: (batchId: string) => void;
  onSelectBatch: (batchId: string) => void;
  onFocusCase: (caseId: string) => void | Promise<void>;
  onSelectCase: (caseId: string) => void;
  onRunFromAssets: () => void;
  onRetryCase: (item: CaseRecord) => void;
  onExportPptx: (caseId: string) => Promise<ArtifactRecord[]>;
  onDownloadPptx: (caseId: string, artifact: ArtifactRecord) => void | Promise<void>;
  onDownloadBatchPptx: (batchId: string) => void | Promise<void>;
}) {
  const cases = activeBatch?.cases || [];
  const [contextMenu, setContextMenu] = useState<TaskContextMenuState | null>(null);
  const [batchContextMenu, setBatchContextMenu] = useState<BatchContextMenuState | null>(null);
  const [caseArtifacts, setCaseArtifacts] = useState<Record<string, ArtifactRecord[]>>({});
  const [artifactLoading, setArtifactLoading] = useState<Record<string, boolean>>({});
  const contextCase = contextMenu ? cases.find((item) => item.case_id === contextMenu.caseId) || null : null;
  const contextSelected = Boolean(contextCase && activeCase?.case.case_id === contextCase.case_id);
  const contextCompatibility = contextSelected ? runCompatibility : contextCase?.compatibility_mode || "none";
  const contextReadOnly = contextCompatibility === "legacy_readonly";
  const contextAssetsReady = Boolean(
    contextCase &&
      !contextReadOnly &&
      (contextCompatibility === "v2"
        ? contextCase.editor_ready
        : contextSelected
          ? assetsReady
          : contextCase.editor_ready)
  );
  const contextCanvasReady = contextSelected && canvasReady;
  const contextRunReady = contextSelected && canRunFromAssets && !contextReadOnly;
  const batchContextBusy = Boolean(batchContextMenu && (batchContextMenu.running || batchRunPendingId === batchContextMenu.batchId));
  const batchDownloadReady = Boolean(activeBatch && cases.length > 0 && cases.every((item) => item.status === "completed"));
  const batchDownloadPending = Boolean(activeBatch && batchPptxDownloadPendingId === activeBatch.batch.batch_id);

  useEffect(() => {
    if (!contextMenu && !batchContextMenu) return;
    function closeContextMenu() {
      setContextMenu(null);
      setBatchContextMenu(null);
    }
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") closeContextMenu();
    }
    window.addEventListener("click", closeContextMenu);
    window.addEventListener("resize", closeContextMenu);
    window.addEventListener("scroll", closeContextMenu, true);
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      window.removeEventListener("click", closeContextMenu);
      window.removeEventListener("resize", closeContextMenu);
      window.removeEventListener("scroll", closeContextMenu, true);
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [contextMenu, batchContextMenu]);

  async function openTaskContextMenu(event: MouseEvent<HTMLElement>, item: CaseRecord) {
    event.preventDefault();
    event.stopPropagation();
    const menuWidth = 218;
    const menuHeight = 184;
    setBatchContextMenu(null);
    setContextMenu({
      caseId: item.case_id,
      caseName: item.name,
      x: Math.max(8, Math.min(event.clientX, window.innerWidth - menuWidth - 8)),
      y: Math.max(8, Math.min(event.clientY, window.innerHeight - menuHeight - 8))
    });
    if (activeCase?.case.case_id !== item.case_id) {
      await onFocusCase(item.case_id);
    }
  }

  async function ensureCaseArtifacts(caseId: string) {
    if (caseArtifacts[caseId] || artifactLoading[caseId]) return;
    setArtifactLoading((current) => ({ ...current, [caseId]: true }));
    try {
      const response = await getCaseArtifacts(caseId);
      setCaseArtifacts((current) => ({ ...current, [caseId]: response.artifacts }));
    } catch {
      setCaseArtifacts((current) => ({ ...current, [caseId]: [] }));
    } finally {
      setArtifactLoading((current) => ({ ...current, [caseId]: false }));
    }
  }

  async function exportTaskPptx(item: CaseRecord) {
    if (pptxExportPendingCaseId) return;
    try {
      const nextArtifacts = await onExportPptx(item.case_id);
      if (nextArtifacts.length > 0) {
        setCaseArtifacts((current) => ({ ...current, [item.case_id]: nextArtifacts }));
      }
    } catch {
      // The parent surfaces the error banner; keep the menu interaction quiet.
    }
  }

  async function openBatchContextMenu(event: MouseEvent<HTMLElement>, batch: BatchRecord) {
    event.preventDefault();
    event.stopPropagation();
    const menuWidth = 218;
    const menuHeight = 174;
    setContextMenu(null);
    setBatchContextMenu({
      batchId: batch.batch_id,
      batchName: batch.name,
      caseCount: caseCountTotal(batch.case_counts || {}),
      running: batch.status === "running",
      x: Math.max(8, Math.min(event.clientX, window.innerWidth - menuWidth - 8)),
      y: Math.max(8, Math.min(event.clientY, window.innerHeight - menuHeight - 8))
    });
  }

  async function runContextAction(action: "assets" | "canvas" | "run") {
    if (!contextCase) return;
    if (action === "assets") {
      setContextMenu(null);
      onOpenCaseAssets(contextCase.case_id);
      return;
    }
    if (activeCase?.case.case_id !== contextCase.case_id) {
      await onFocusCase(contextCase.case_id);
    }
    setContextMenu(null);
    if (action === "canvas") {
      onOpenSvgEditor();
      return;
    }
    onRunFromAssets();
  }

  function runBatchContextAction(action: "rename" | "delete" | "run") {
    if (!batchContextMenu) return;
    const batch = batches.find((item) => item.batch_id === batchContextMenu.batchId);
    if (!batch) return;
    setBatchContextMenu(null);
    if (action === "rename") {
      onRenameBatch(batch);
      return;
    }
    if (action === "delete") {
      onDeleteBatch(batch);
      return;
    }
    onRunBatch(batch.batch_id);
  }

  return (
    <main className="task-selection-workspace">
      <section className="batch-rail">
        <div className="board-panel-head">
          <div>
            <span>任务</span>
            <strong>{batches.length} 个任务</strong>
          </div>
          <button className="task-submit-button" title="提交任务" aria-label="提交任务" onClick={onOpenSubmit}>
            <PlusIcon />
          </button>
        </div>
        <div className="batch-list-modern">
          {batches.map((batch) => {
            const totalCases = caseCountTotal(batch.case_counts || {});
            return (
              <article
                key={batch.batch_id}
                className={`batch-row ${activeBatch?.batch.batch_id === batch.batch_id ? "active" : ""} ${batch.status === "failed" ? "failed" : ""}`}
                role="button"
                tabIndex={0}
                onClick={() => onSelectBatch(batch.batch_id)}
                onContextMenu={(event) => {
                  void openBatchContextMenu(event, batch);
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelectBatch(batch.batch_id);
                  }
                }}
              >
                <div className="batch-row-top">
                  <time dateTime={batch.created_at} title={batch.created_at}>{submittedTimeText(batch.created_at)}</time>
                  <span className={`status-pill status-${batch.status}`}>{humanize(batch.status)}</span>
                </div>
                <div className="batch-row-main">
                  <strong>{batch.name}</strong>
                </div>
                <div className="batch-row-bottom">
                  <em>{totalCases} 张图</em>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="case-lane">
        <div className="task-list">
          {cases.map((item) => {
            const selected = activeCase?.case.case_id === item.case_id;
            const rowPreviewUrl = item.preview_url || "";
            const editorReady = Boolean(item.editor_ready);
            const actionsEnabled = selected;
            const artifacts = selected && activeCase ? activeCase.artifacts : caseArtifacts[item.case_id] || [];
            const svgArtifact = latestArtifact(artifacts, "semantic_svg");
            const pptxArtifact = latestArtifact(artifacts, "pptx");
            const artifactsLoading = Boolean(artifactLoading[item.case_id]);
            const pptxExporting = pptxExportPendingCaseId === item.case_id;
            const pptxExportBlocked = Boolean(pptxExportPendingCaseId);
            const itemCompatibility = selected ? runCompatibility : item.compatibility_mode || "none";
            const itemReadOnly = itemCompatibility === "legacy_readonly";
            const itemV2 = itemCompatibility === "v2";
            const pptxExportable = !itemReadOnly && Boolean(svgArtifact || item.status === "completed");
            const failed = item.status === "failed";
            const needsAssetReview = item.status === "assets_review" && item.stage !== "approved_asset_plan";
            const retryStage = retryStageForCase(item);
            const taskActionRunning = caseActionPendingId === item.case_id || pptxExporting || (selected && runInProgress);
            const taskActionEnabled = failed ? !taskActionRunning && !itemReadOnly : actionsEnabled && canRunFromAssets && !itemReadOnly;
            const taskActionLabel = taskActionRunning ? "运行中" : failed ? `重试（从 ${humanize(retryStage)} 开始）` : "运行";
            const taskAssetsEnabled = itemV2 ? editorReady && !itemReadOnly : actionsEnabled && assetsReady && !itemReadOnly;
            return (
              <article
                key={item.case_id}
                className={`task-row ${selected ? "active" : ""} ${item.status === "failed" ? "failed" : ""} ${editorReady ? "editor-ready" : "not-editor-ready"}`}
                role="button"
                tabIndex={0}
                onClick={() => onSelectCase(item.case_id)}
                onContextMenu={(event) => {
                  void openTaskContextMenu(event, item);
                }}
                onKeyDown={(event) => {
                  if (event.target !== event.currentTarget) return;
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelectCase(item.case_id);
                  }
                }}
              >
                <div className="task-row-top">
                  <span className={`status-pill status-${item.status}`}>{humanize(item.status)}</span>
                  <em>{humanize(item.stage || item.phase)}</em>
                </div>
                <div className="task-thumb">
                  {rowPreviewUrl ? <img src={rowPreviewUrl} alt="" /> : <span>{caseInitials(item.name)}</span>}
                  {needsAssetReview && <span className="task-review-dot" title="等待素材确认" aria-label="等待素材确认" />}
                  <div className="task-thumb-shade" aria-hidden="true" />
                  <div
                    className="task-thumb-actions"
                    onClick={(event) => event.stopPropagation()}
                    onPointerDown={(event) => event.stopPropagation()}
                  >
                    <button
                      className={needsAssetReview ? "task-thumb-action needs-review" : "task-thumb-action"}
                      disabled={!taskAssetsEnabled}
                      onClick={() => {
                        onOpenCaseAssets(item.case_id);
                      }}
                    >
                      <span className="task-thumb-action__zh">{itemV2 ? "Assets" : "素材"}</span>
                      <span className="task-thumb-action__en">{itemV2 ? "查看" : "编辑"}</span>
                    </button>
                    <button className="task-thumb-action" disabled={!actionsEnabled || !canvasReady} onClick={onOpenSvgEditor}>
                      <span className="task-thumb-action__zh">结果</span>
                      <span className="task-thumb-action__en">画布</span>
                    </button>
                  </div>
                </div>
                <div className="task-bottom">
                  <div className="task-info">
                    <div className="task-main">
                      <strong>{item.name}</strong>
                      <span>{humanize(item.phase)} / {humanize(item.stage)}</span>
                      {item.error_message && <em>{shortenError(item.error_message)}</em>}
                    </div>
                    <div className="task-meta">
                      {item.stale_from_stage ? <em>需从 {humanize(item.stale_from_stage)} 重新运行</em> : <em>{editorReady ? "素材已准备" : "等待中"}</em>}
                    </div>
                  </div>
                  <div
                    className="task-card-actions"
                    onMouseEnter={() => void ensureCaseArtifacts(item.case_id)}
                    onFocus={() => void ensureCaseArtifacts(item.case_id)}
                    onClick={(event) => event.stopPropagation()}
                    onPointerDown={(event) => event.stopPropagation()}
                  >
                    <div className="task-download-menu">
                      <button className="task-download-button" title="下载" aria-label="下载">
                        <DownloadIcon />
                      </button>
                      <div className="task-download-options" role="menu" aria-label="下载格式">
                        {svgArtifact ? (
                          <a href={svgArtifact.url} download role="menuitem">SVG</a>
                        ) : (
                          <span className="disabled" role="menuitem" aria-disabled="true">{artifactsLoading ? "加载中" : "SVG"}</span>
                        )}
                        {pptxArtifact ? (
                          <button type="button" onClick={() => void onDownloadPptx(item.case_id, pptxArtifact)} role="menuitem">PPTX</button>
                        ) : pptxExportable ? (
                          <button type="button" disabled={pptxExportBlocked} onClick={() => void exportTaskPptx(item)} role="menuitem">
                            {pptxExporting ? "导出中" : "PPTX"}
                          </button>
                        ) : (
                          <span className="disabled" role="menuitem" aria-disabled="true">{artifactsLoading ? "加载中" : "PPTX"}</span>
                        )}
                        <span className="disabled psd-disabled" role="menuitem" aria-disabled="true" title="后续支持中">PSD</span>
                      </div>
                    </div>
                    <button
                      className={`task-run-button ${failed ? "retry" : ""} ${taskActionRunning ? "running" : ""}`}
                      title={taskActionLabel}
                      aria-label={taskActionLabel}
                      disabled={!taskActionEnabled}
                      onClick={(event) => {
                        event.stopPropagation();
                        if (failed) {
                          onRetryCase(item);
                          return;
                        }
                        onRunFromAssets();
                      }}
                    >
                      {taskActionRunning ? <ButtonSpinner /> : failed ? <RetryIcon /> : <PlayIcon />}
                    </button>
                  </div>
                </div>
              </article>
            );
          })}
          {!activeBatch && <EmptyState label="选择一个任务" />}
          {activeBatch && cases.length === 0 && <EmptyState label="这个任务里还没有图片" />}
        </div>
        <button
          type="button"
          className={`batch-download-floating${batchDownloadReady ? " ready" : ""}${batchDownloadPending ? " running" : ""}`}
          title={batchDownloadReady ? "下载合并 PPTX" : "全部完成后可批量下载 PPTX"}
          aria-label={batchDownloadReady ? "下载合并 PPTX" : "全部完成后可批量下载 PPTX"}
          disabled={!activeBatch || !batchDownloadReady || batchDownloadPending}
          onClick={() => {
            if (!activeBatch) return;
            void onDownloadBatchPptx(activeBatch.batch.batch_id);
          }}
        >
          {batchDownloadPending ? <ButtonSpinner /> : <DownloadIcon />}
        </button>
      </section>
      {batchContextMenu && (
        <div
          className="task-context-menu batch-context-menu"
          data-testid="task-batch-context-menu"
          style={{ left: batchContextMenu.x, top: batchContextMenu.y }}
          role="menu"
          aria-label={`${batchContextMenu.batchName} 任务操作`}
          onClick={(event) => event.stopPropagation()}
          onContextMenu={(event) => event.preventDefault()}
        >
          <div className="task-context-menu-head">
            <span>任务</span>
            <strong>{batchContextMenu.batchName}</strong>
          </div>
          <button
            type="button"
            role="menuitem"
            data-testid="task-batch-rename"
            onClick={() => runBatchContextAction("rename")}
          >
            <span>重命名</span>
            <em>修改名称</em>
          </button>
          <button
            type="button"
            role="menuitem"
            className="danger"
            data-testid="task-batch-delete"
            disabled={batchContextBusy}
            onClick={() => runBatchContextAction("delete")}
          >
            <span>删除</span>
            <em>{batchContextBusy ? "运行中" : "移除任务"}</em>
          </button>
          <button
            type="button"
            role="menuitem"
            data-testid="task-batch-run-all"
            disabled={batchContextBusy || batchContextMenu.caseCount === 0}
            onClick={() => runBatchContextAction("run")}
          >
            {batchRunPendingId === batchContextMenu.batchId ? <ButtonSpinner /> : <PlayIcon />}
            <span>{batchContextBusy ? "运行中" : "一键运行"}</span>
            <em>{batchContextMenu.caseCount} 张图</em>
          </button>
        </div>
      )}
      {contextMenu && (
        <div
          className="task-context-menu"
          data-testid="task-context-menu"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          role="menu"
          aria-label={`${contextMenu.caseName} 图片操作`}
          onClick={(event) => event.stopPropagation()}
          onContextMenu={(event) => event.preventDefault()}
        >
          <div className="task-context-menu-head">
            <span>图片</span>
            <strong>{contextMenu.caseName}</strong>
          </div>
          <button
            type="button"
            role="menuitem"
            data-testid="task-context-assets"
            disabled={!contextAssetsReady}
            onClick={() => {
              void runContextAction("assets");
            }}
          >
            <span>{contextCompatibility === "v2" ? "Assets" : "素材"}</span>
            <em>{contextReadOnly ? "历史只读" : contextCompatibility === "v2" ? "打开画布" : contextSelected ? "编辑素材" : "正在选择"}</em>
          </button>
          <button
            type="button"
            role="menuitem"
            data-testid="task-context-canvas"
            disabled={!contextCanvasReady}
            onClick={() => {
              void runContextAction("canvas");
            }}
          >
            <span>结果</span>
            <em>{contextSelected ? "打开画布" : "正在选择"}</em>
          </button>
          <button
            type="button"
            role="menuitem"
            data-testid="task-context-run"
            disabled={!contextRunReady}
            onClick={() => {
              void runContextAction("run");
            }}
          >
            <PlayIcon />
            <span>{runInProgress && contextSelected ? "运行中" : "运行"}</span>
            <em>{contextReadOnly ? "历史只读" : contextSelected ? "从素材继续" : "正在选择"}</em>
          </button>
        </div>
      )}
    </main>
  );
}

function EditorWorkspace({
  activeCase,
  assetPlan,
  selectedAssetId,
  figureUrl,
  canUndo,
  onBackToBoard,
  onSelectAsset,
  onChangeAssetPlan,
  onBeginAssetEdit,
  onUndo,
  onNext,
  onProcessAssets,
  onDelete,
  runInProgress
}: {
  activeCase: CaseDetail | null;
  assetPlan: AssetPlan | null;
  selectedAssetId: string;
  figureUrl: string;
  canUndo: boolean;
  onBackToBoard: () => void;
  onSelectAsset: (id: string) => void;
  onChangeAssetPlan: (plan: AssetPlan, options?: AssetPlanChangeOptions) => void;
  onBeginAssetEdit: () => void;
  onUndo: () => void;
  onNext: () => void;
  onProcessAssets: (assetIds: string[], plan: AssetPlan) => Promise<AssetPlan>;
  onDelete: () => void;
  runInProgress: boolean;
}) {
  const editorRef = useRef<HTMLElement | null>(null);
  const [mode, setMode] = useState<CanvasMode>("select");
  const [zoom, setZoom] = useState(0.72);
  const [assetView, setAssetView] = useState<AssetEditorView>("extraction");

  const changeZoom = useCallback((delta: number) => {
    setZoom((value) => clamp(Number((value + delta).toFixed(2)), 0.25, 2.5));
  }, []);

  useEffect(() => {
    const root = editorRef.current;
    if (!root) return;

    function handleWheel(event: globalThis.WheelEvent) {
      if (!event.ctrlKey && !event.metaKey) return;
      event.preventDefault();
      if (event.target instanceof Element && event.target.closest(".canvas-stage")) {
        changeZoom(event.deltaY < 0 ? 0.03 : -0.03);
      }
    }

    root.addEventListener("wheel", handleWheel, { passive: false, capture: true });
    return () => root.removeEventListener("wheel", handleWheel, { capture: true });
  }, [changeZoom]);

  const topbarTarget = typeof document !== "undefined" ? document.getElementById("drawai-view-controls") : null;
  const topbarPortal = topbarTarget
    ? createPortal(
        <div className="editor-banner-controls assets-banner-controls">
          <button className="home-button" title="返回任务" aria-label="返回任务" onClick={onBackToBoard}>
            <HomeIcon />
          </button>
          <div className="editor-title">
            <div>
              <strong>{activeCase?.case.name || "未选择图片"}</strong>
              <span>{humanize(activeCase?.case.status || "idle")} · {humanize(activeCase?.case.stage || "select a case")}</span>
            </div>
          </div>
          <div className={`asset-type-switch is-${assetView}`} role="tablist" aria-label="素材编辑模式">
            <span className="asset-type-switch__thumb" aria-hidden="true" />
            <button
              type="button"
              role="tab"
              aria-selected={assetView === "extraction"}
              className={assetView === "extraction" ? "active" : ""}
              onClick={() => setAssetView("extraction")}
            >
              <span className="asset-type-switch__index">1</span>
              提取
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={assetView === "processing"}
              className={assetView === "processing" ? "active" : ""}
              onClick={() => setAssetView("processing")}
            >
              <span className="asset-type-switch__index">2</span>
              处理
            </button>
          </div>
          <div className="editor-toolbar">
            {assetView === "extraction" ? (
              <>
                <div className="tool-group">
                  <button className={mode === "select" ? "active icon-button" : "icon-button"} title="选择" disabled={!assetPlan} onClick={() => setMode("select")} aria-label="选择">
                    <SelectToolIcon />
                  </button>
                  <button className={mode === "add" ? "active icon-button" : "icon-button"} title="新增矩形框" disabled={!assetPlan} onClick={() => setMode("add")} aria-label="新增矩形框">
                    <AddBoxToolIcon />
                  </button>
                  <button className={mode === "polygon" ? "active icon-button" : "icon-button"} title="多边形框选" disabled={!assetPlan} onClick={() => setMode("polygon")} aria-label="多边形框选">
                    <PolygonToolIcon />
                  </button>
                  <button className="icon-button" title="Mask（SAM 分割，敬请期待）" disabled aria-label="Mask">
                    <MaskToolIcon />
                  </button>
                  <button className="icon-button" title="提示词分割（敬请期待）" disabled aria-label="提示词分割">
                    <TextToolIcon />
                  </button>
                  <button className="icon-button" title="撤销 Command+Z" disabled={!canUndo} onClick={onUndo} aria-label="撤销">
                    <UndoToolIcon />
                  </button>
                </div>
                <div className="tool-group">
                  <button className="icon-button" title="缩小" onClick={() => changeZoom(-0.1)}>−</button>
                  <span className="zoom-readout">{Math.round(zoom * 100)}%</span>
                  <button className="icon-button" title="放大" onClick={() => changeZoom(0.1)}>+</button>
                </div>
              </>
            ) : (
              <div className="toolbar-note">按每个素材的处理模式执行</div>
            )}
          </div>
          <div className="editor-actions">
            <button
              className={runInProgress ? "primary run-button running" : "primary run-button"}
              disabled={!assetPlan || runInProgress}
              onClick={onNext}
            >
              {runInProgress && <ButtonSpinner />}
              {runInProgress ? "运行中" : "运行"}
            </button>
          </div>
        </div>,
        topbarTarget
      )
    : null;

  return (
    <>
      {topbarPortal}
      <main ref={editorRef} className="editor-workspace">
        <div className="asset-stage" key={assetView} data-asset-view={assetView}>
        {assetView === "extraction" ? (
          <CanvasEditor
            assetPlan={assetPlan}
            selectedAssetId={selectedAssetId}
            figureUrl={figureUrl}
            mode={mode}
            zoom={zoom}
            onSelect={onSelectAsset}
            onChange={onChangeAssetPlan}
            onBeginEdit={onBeginAssetEdit}
            onDelete={onDelete}
          />
        ) : (
          <AssetProcessingPanel
            assetPlan={assetPlan}
            selectedAssetId={selectedAssetId}
            figureUrl={figureUrl}
            onSelect={onSelectAsset}
            onChange={onChangeAssetPlan}
            onBeginEdit={onBeginAssetEdit}
            onProcessAssets={onProcessAssets}
            onEditExtraction={(id, nextMode = "select") => {
              onSelectAsset(id);
              setMode(nextMode);
              setAssetView("extraction");
            }}
          />
        )}
        </div>
      </main>
    </>
  );
}

function NewBatchForm({
  onSubmitted,
  onCreated,
  onError
}: {
  onSubmitted: () => void;
  onCreated: (detail: BatchDetail) => void | Promise<void>;
  onError: (message: string) => void;
}) {
  const [dragActive, setDragActive] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [preparingUpload, setPreparingUpload] = useState(false);
  const [pendingUpload, setPendingUpload] = useState<UploadConfirmation | null>(null);
  const [manualAssetReview, setManualAssetReview] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleDrop(event: DragEvent<HTMLElement>) {
    event.preventDefault();
    event.stopPropagation();
    setDragActive(false);
    const dropped = await selectedUploadFilesFromDrop(event);
    await submitFiles(dropped);
  }

  async function submitFiles(droppedFiles: SelectedUploadFile[]) {
    const supported = droppedFiles.filter((item) => isSupportedUpload(item.file));
    if (droppedFiles.length === 0 || supported.length === 0) {
      setUploadError("请拖入图片、ZIP 文件，或包含图片的文件夹。");
      return;
    }
    if (submitting || preparingUpload) return;
    try {
      setPreparingUpload(true);
      setUploadError("");
      const confirmation = await buildUploadConfirmation(supported);
      if (confirmation.images.length === 0) {
        setUploadError("没有解析到支持的图片。请上传 PNG、JPG、WEBP，或包含这些图片的 ZIP。");
        return;
      }
      setPendingUpload(confirmation);
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
    } finally {
      setPreparingUpload(false);
    }
  }

  async function confirmUpload() {
    if (!pendingUpload || submitting) return;
    try {
      setSubmitting(true);
      setUploadError("");
      const form = new FormData();
      form.set("name", pendingUpload.title);
      form.set("input_mode", "upload");
      form.set("max_concurrent_cases", "10");
      form.set("auto_run_svg_after_analysis", manualAssetReview ? "false" : "true");
      pendingUpload.files.forEach((item) => form.append("files", item.file, item.relativePath));
      const detail = await createUploadBatch(form);
      await onCreated(detail);
      onSubmitted();
    } catch (err) {
      setSubmitting(false);
      onError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <section className="new-batch">
      <div className="new-batch-source">
        {pendingUpload ? (
          <div className="upload-confirmation">
            <div className="upload-confirmation-head">
              <div>
                <span>上传确认</span>
                <strong>解析到 {pendingUpload.images.length} 张图片</strong>
              </div>
              <button type="button" className="upload-reset-button" disabled={submitting} onClick={() => setPendingUpload(null)}>
                重新选择
              </button>
            </div>
            <div className="upload-image-list" role="list" aria-label="已解析图片">
              {pendingUpload.images.map((image, index) => (
                <div className="upload-image-row" role="listitem" key={`${image.kind}-${image.source}-${image.name}-${index}`}>
                  <span>{index + 1}</span>
                  <strong>{image.name}</strong>
                  <em>{image.kind === "zip" ? `来自 ${image.source}` : "直接上传"}</em>
                </div>
              ))}
            </div>
            {pendingUpload.zipErrors.length > 0 && (
              <div className="upload-zip-warnings">
                {pendingUpload.zipErrors.map((warning) => <span key={warning}>{warning}</span>)}
              </div>
            )}
            <label className="upload-review-toggle">
              <input
                type="checkbox"
                checked={manualAssetReview}
                disabled={submitting}
                onChange={(event) => setManualAssetReview(event.currentTarget.checked)}
              />
              <span>
                <strong>手动确认素材</strong>
                <em>{manualAssetReview ? "预处理后停在素材确认环节。" : "系统会从预处理一直执行到最终导出。"}</em>
              </span>
            </label>
            <div className="upload-confirmation-actions">
              <button type="button" disabled={submitting} onClick={() => setPendingUpload(null)}>取消</button>
              <button type="button" className="primary" disabled={submitting} onClick={() => void confirmUpload()}>
                {submitting && <ButtonSpinner />}
                {submitting ? "提交中" : manualAssetReview ? "提交并手动确认" : "提交并自动运行"}
              </button>
            </div>
          </div>
        ) : (
          <div
            className={`${dragActive ? "upload-dropzone active" : "upload-dropzone"} ${preparingUpload ? "submitting" : ""}`}
            onDragEnter={(event) => {
              event.preventDefault();
              if (preparingUpload) return;
              setDragActive(true);
            }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={(event) => {
              event.preventDefault();
              if (event.currentTarget === event.target) setDragActive(false);
            }}
            onDrop={handleDrop}
          >
            <div className="upload-mark" aria-hidden="true">
              {preparingUpload ? <ButtonSpinner /> : <UploadIcon />}
            </div>
            <strong>{preparingUpload ? "解析中..." : "拖入图片、ZIP 或文件夹"}</strong>
            <span>支持一次选择多张 PNG、JPG、WEBP，也可以拖入 ZIP 或文件夹</span>
            <button
              type="button"
              className="upload-select-button"
              disabled={preparingUpload}
              onClick={() => fileInputRef.current?.click()}
            >
              选择图片
            </button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".png,.jpg,.jpeg,.webp,.zip,image/png,image/jpeg,image/webp,application/zip"
              disabled={preparingUpload}
              onChange={(event) => {
                const files = selectedUploadFilesFromFileList(event.currentTarget.files);
                event.currentTarget.value = "";
                void submitFiles(files);
              }}
            />
            {uploadError && <p className="upload-error">{uploadError}</p>}
          </div>
        )}
      </div>
    </section>
  );
}

function BackendStatusIndicator({ health, healthError }: { health: HealthResponse | null; healthError: string }) {
  const services = Object.entries(health?.runtime_services || {});
  const runtimeRows = runtimeStatusRows(health);
  const allModelsOnline = Boolean(health && services.length > 0 && services.every(([, service]) => service.status === "online"));
  const connected = Boolean(health && health.status === "ok" && allModelsOnline);
  const offlineServices = services.filter(([, service]) => service.status !== "online");
  const onlineCount = services.filter(([, service]) => service.status === "online").length;
  const serviceTotal = services.length;
  const onlinePercent = serviceTotal > 0 ? Math.round((onlineCount / serviceTotal) * 100) : 0;
  const summary = backendStatusSummary(health, healthError, offlineServices);
  return (
    <div
      className={connected ? "backend-status connected" : "backend-status disconnected"}
      tabIndex={0}
      aria-label={summary}
    >
      <span className="backend-lamp" aria-hidden="true" />
      <div className="backend-status-popover" role="status">
        <div className="backend-popover-head">
          <div>
            <span>运行状态</span>
            <strong>{connected ? "后端已连接" : "后端异常"}</strong>
            <p>{summary}</p>
          </div>
          <div className={connected ? "backend-score online" : "backend-score offline"}>
            <strong>{serviceTotal > 0 ? `${onlineCount}/${serviceTotal}` : "0"}</strong>
            <span>在线</span>
          </div>
        </div>
        <div className="backend-health-bar" aria-hidden="true">
          <span style={{ width: `${onlinePercent}%` }} />
        </div>
        {runtimeRows.length > 0 ? (
          <div className="backend-runtime-map">
            <div className={health?.status === "ok" ? "backend-api-node online" : "backend-api-node offline"}>
              <span>API</span>
              <strong>{health?.status === "ok" ? "正常" : "离线"}</strong>
            </div>
            <div className="backend-service-links" aria-hidden="true">
              {runtimeRows.map((row) => (
                <span key={row.key} className={row.online ? "online" : "offline"} />
              ))}
            </div>
            <div className="backend-service-grid">
              {runtimeRows.map((row) => (
                <article key={row.key} className={row.online ? "backend-service-card online" : "backend-service-card offline"}>
                  <div className="backend-service-card-head">
                    <span aria-hidden="true" />
                    <strong>{row.label}</strong>
                    <em>{row.statusLabel}</em>
                  </div>
                  <p title={row.detail}>
                    {row.detail}
                  </p>
                  <div className="backend-service-activity" aria-label={`${row.label} 当前状态`}>
                    <span>
                      <strong>{row.activity.queued}</strong>
                      <small>排队</small>
                    </span>
                    <span>
                      <strong>{row.activity.running}</strong>
                      <small>Running</small>
                    </span>
                  </div>
                </article>
              ))}
            </div>
          </div>
        ) : (
          <div className="backend-empty-state">
            <span aria-hidden="true" />
            <small>{healthError || "暂无运行服务状态。"}</small>
          </div>
        )}
      </div>
    </div>
  );
}

function backendStatusSummary(
  health: HealthResponse | null,
  healthError: string,
  offlineServices: Array<[string, { status: string; error?: string }]>
): string {
  if (!health) return healthError ? `后端 API 无法连接：${healthError}` : "后端 API 无法连接。";
  if (offlineServices.length === 0 && health.status === "ok") return "后端和模型服务都在线。";
  if (offlineServices.length === 0) return "后端已响应，但模型状态不完整。";
  return `离线模型：${offlineServices.map(([key]) => runtimeServiceLabel(key)).join("、")}。`;
}

function runtimeStatusRows(health: HealthResponse | null): RuntimeStatusRow[] {
  if (!health) return [];
  const services = health.runtime_services || {};
  const activity = health.runtime_activity || {};
  const preferredKeys = ["sam3", "ocr", "rmbg", "codex"];
  const keys = [...preferredKeys, ...Object.keys(services)].filter(uniqueRuntimeKey);
  return keys
    .filter((key) => services[key] || activity[key])
    .map((key) => runtimeStatusRow(key, services[key], activity[key]));
}

function uniqueRuntimeKey(key: string, index: number, keys: string[]): boolean {
  return keys.indexOf(key) === index;
}

function runtimeStatusRow(
  key: string,
  service: RuntimeServiceStatus | undefined,
  activity: RuntimeActivityStatus | undefined
): RuntimeStatusRow {
  const normalizedActivity = activity || { limit: 0, queued: 0, running: 0 };
  const online = service ? service.status === "online" : true;
  return {
    key,
    label: runtimeServiceLabel(key),
    online,
    statusLabel: runtimeStatusLabel(service, normalizedActivity),
    detail: runtimeStatusDetail(key, service, normalizedActivity),
    activity: normalizedActivity
  };
}

function runtimeStatusLabel(service: RuntimeServiceStatus | undefined, activity: RuntimeActivityStatus): string {
  if (activity.running > 0) return "运行中";
  if (activity.queued > 0) return "排队中";
  if (service && service.status !== "online") return "离线";
  return service ? "在线" : "待命";
}

function runtimeStatusDetail(
  key: string,
  service: RuntimeServiceStatus | undefined,
  activity: RuntimeActivityStatus
): string {
  const capacity = activity.limit > 0 ? `并发 ${activity.limit}` : "并发未配置";
  if (!service) return `${runtimeServiceLabel(key)} 本地执行队列 · ${capacity}`;
  if (service.status !== "online") return service.error || "离线";
  return `${service.base_url || "本地服务"} · ${capacity}`;
}

function runtimeServiceLabel(key: string): string {
  if (key === "sam3") return "SAM3";
  if (key === "ocr") return "OCR";
  if (key === "rmbg") return "RMBG";
  if (key === "codex") return "Codex";
  return key.toUpperCase();
}

function AssetProcessingPanel({
  assetPlan,
  selectedAssetId,
  figureUrl,
  onSelect,
  onChange,
  onBeginEdit,
  onProcessAssets,
  onEditExtraction
}: {
  assetPlan: AssetPlan | null;
  selectedAssetId: string;
  figureUrl: string;
  onSelect: (id: string) => void;
  onChange: (plan: AssetPlan, options?: AssetPlanChangeOptions) => void;
  onBeginEdit: () => void;
  onProcessAssets: (assetIds: string[], plan: AssetPlan) => Promise<AssetPlan>;
  onEditExtraction: (id: string, mode?: CanvasMode) => void;
}) {
  const [checkedIds, setCheckedIds] = useState<string[]>([]);
  const [naturalSize, setNaturalSize] = useState({ width: 1, height: 1 });
  const [processingIds, setProcessingIds] = useState<string[]>([]);
  const [processingError, setProcessingError] = useState("");
  const [zoomElement, setZoomElement] = useState<AssetElement | null>(null);
  const rows = useMemo(
    () => (assetPlan?.elements || []).filter((element) => isEditorSourceStrategy(element.source_strategy)),
    [assetPlan]
  );
  const checkedSet = useMemo(() => new Set(checkedIds), [checkedIds]);
  const activeIds = checkedIds.filter((id) => rows.some((row) => row.box_id === id));
  const allChecked = rows.length > 0 && rows.every((row) => checkedSet.has(row.box_id));

  useEffect(() => {
    setCheckedIds((ids) => ids.filter((id) => rows.some((row) => row.box_id === id)));
  }, [rows]);

  function toggleRow(id: string) {
    setCheckedIds((ids) => (ids.includes(id) ? ids.filter((item) => item !== id) : [...ids, id]));
  }

  function toggleAll() {
    setCheckedIds(allChecked ? [] : rows.map((row) => row.box_id));
  }

  function setProcessingMode(id: string, strategy: EditorSourceStrategy) {
    if (!assetPlan) return;
    onBeginEdit();
    onChange({
      ...assetPlan,
      elements: assetPlan.elements.map((element) => (
        element.box_id === id
          ? {
              ...element,
              source_strategy: strategy,
              current_pipeline_method: strategy,
              recommended_asset_source: strategyLabels[strategy],
              processed_asset_relative_path: undefined,
              processed_asset_source_strategy: undefined,
              processed_asset_updated_at: undefined,
              processed_asset_width: undefined,
              processed_asset_height: undefined,
              processing_status: "pending",
              processing_error: "",
              rmbg_elapsed_ms: undefined,
              rmbg_artifacts: undefined,
              reason: updateAssetReason(
                clearWorkbenchProcessingReasons(element.reason, { clearApplied: true, clearMode: true }),
                `${WORKBENCH_PROCESSING_MODE_REASON} ${strategyLabels[strategy]}.`
              )
            }
          : element
      ))
    });
  }

  async function processAssets(ids: string[]) {
    if (!assetPlan || ids.length === 0) return;
    setProcessingError("");
    onBeginEdit();
    setProcessingIds(ids);
    try {
      const nextPlan = await onProcessAssets(ids, assetPlan);
      onChange(nextPlan, { track: false });
    } catch (err) {
      setProcessingError(err instanceof Error ? err.message : String(err));
    } finally {
      setProcessingIds([]);
    }
  }

  if (!assetPlan) return <EmptyState label="素材还没准备好" />;

  return (
    <section className="asset-processing-workspace">
      {figureUrl && (
        <img
          className="asset-processing-probe"
          src={figureUrl}
          alt=""
          onLoad={(event) => setNaturalSize({ width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight })}
        />
      )}
      <div className="asset-processing-head">
        <div>
          <span>素材处理</span>
          <strong>裁剪 / 去背景</strong>
        </div>
        <div className="asset-processing-actions" aria-label="批量处理素材">
          <button disabled={activeIds.length === 0 || processingIds.length > 0} onClick={() => processAssets(activeIds)}>
            {processingIds.length > 0 ? "处理中" : "批量处理"}
          </button>
        </div>
      </div>
      {processingError && <div className="asset-processing-error">{processingError}</div>}
      <div className="asset-processing-table-wrap">
        <table className="asset-processing-table">
          <thead>
            <tr>
              <th>
                <input type="checkbox" checked={allChecked} disabled={rows.length === 0} onChange={toggleAll} aria-label="全选素材" />
              </th>
              <th>素材</th>
              <th>类型</th>
              <th>处理模式</th>
              <th>处理结果</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((element) => {
              const selected = element.box_id === selectedAssetId;
              const checked = checkedSet.has(element.box_id);
              const processing = processingIds.includes(element.box_id);
              const processedUrl = assetProcessedUrl(element, assetPlan.case_id);
              const geometryPreviewUrl = assetGeometryPreviewUrl(element, assetPlan.case_id);
              const sourcePreviewUrl = geometryPreviewUrl || "";
              const hasProcessedPreview = Boolean(processedUrl);
              const alphaPreview = isAlphaGeometry(element);
              return (
                <tr key={element.box_id} className={selected ? "selected" : ""} onClick={() => onSelect(element.box_id)}>
                  <td>
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleRow(element.box_id)}
                      onClick={(event) => event.stopPropagation()}
                      aria-label={`选择 ${element.box_id}`}
                    />
                  </td>
                  <td>
                    <div className="asset-processing-asset">
                      <button
                        type="button"
                        className={`asset-crop-preview ${sourcePreviewUrl ? "has-geometry-preview checker" : ""}`}
                        style={sourcePreviewUrl ? undefined : assetCropPreviewStyle(element, figureUrl, naturalSize)}
                        title="点击放大"
                        aria-label={`放大 ${element.box_id}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          setZoomElement(element);
                        }}
                      >
                        {sourcePreviewUrl && <img src={sourcePreviewUrl} alt="" />}
                      </button>
                      <div>
                        <strong>{element.box_id}</strong>
                        <span>{bboxText(element.bbox)}</span>
                      </div>
                    </div>
                  </td>
                  <td>
                    <div className="asset-type-cell">
                      <strong>{element.type || "未知"}</strong>
                      <span>{element.visual_role || element.confidence}</span>
                    </div>
                  </td>
                  <td>
                    <div className="processing-mode-group" data-active={element.source_strategy}>
                      <span className="processing-mode-thumb" aria-hidden="true" />
                      {ASSET_PROCESSING_MODES.map((item) => (
                        <button
                          key={item.mode}
                          className={element.source_strategy === item.mode ? "active" : ""}
                          disabled={item.disabled}
                          title={item.disabled ? "生成暂不可用" : ""}
                          onClick={(event) => {
                            event.stopPropagation();
                            if (!item.disabled && item.mode !== "gen") setProcessingMode(element.box_id, item.mode);
                          }}
                        >
                          {item.label}
                        </button>
                      ))}
                    </div>
                  </td>
                  <td>
                    <div className={`asset-result-cell ${hasProcessedPreview && (element.source_strategy === "crop_nobg" || alphaPreview) ? "checker" : ""}`}>
                      <div
                        className={hasProcessedPreview ? "asset-result-preview has-image" : "asset-result-preview"}
                        style={hasProcessedPreview ? undefined : assetCropPreviewStyle(element, figureUrl, naturalSize)}
                      >
                        {hasProcessedPreview && <img src={processedUrl} alt="" />}
                      </div>
                      <span>{assetProcessingResultText(element)}</span>
                    </div>
                  </td>
                  <td>
                    <div className="asset-row-actions">
                      <button disabled={processingIds.length > 0} onClick={(event) => {
                        event.stopPropagation();
                        processAssets([element.box_id]);
                      }}>
                        {processing ? "处理中" : "处理"}
                      </button>
                      <button disabled={processingIds.length > 0} onClick={(event) => {
                        event.stopPropagation();
                        onEditExtraction(element.box_id);
                      }}>
                        重新框选
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6}>
                  <EmptyState label="暂无需要处理的裁剪素材" />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {zoomElement && figureUrl && (
        <AssetZoomOverlay
          element={zoomElement}
          caseId={assetPlan.case_id}
          figureUrl={figureUrl}
          naturalSize={naturalSize}
          onClose={() => setZoomElement(null)}
        />
      )}
    </section>
  );
}

function AssetZoomOverlay({
  element,
  caseId,
  figureUrl,
  naturalSize,
  onClose
}: {
  element: AssetElement;
  caseId: string;
  figureUrl: string;
  naturalSize: { width: number; height: number };
  onClose: () => void;
}) {
  const [scale, setScale] = useState(1);
  const previewUrl = assetGeometryPreviewUrl(element, caseId);
  const cropStyle = assetCropPreviewStyle(element, figureUrl, naturalSize);
  const [x1, y1, x2, y2] = normalizeBBox(element.bbox);
  const ratio = clamp(Math.max(1, x2 - x1) / Math.max(1, y2 - y1), 0.25, 4);

  const changeScale = useCallback((delta: number) => {
    setScale((value) => clamp(Number((value + delta).toFixed(2)), 0.5, 6));
  }, []);

  useEffect(() => {
    function handleKey(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  return createPortal(
    <div
      className="asset-zoom-backdrop"
      onClick={onClose}
      onWheel={(event) => changeScale(event.deltaY < 0 ? 0.2 : -0.2)}
    >
      <div className="asset-zoom-stage" onClick={(event) => event.stopPropagation()}>
        <div className={`asset-zoom-frame ${previewUrl ? "checker" : ""}`} style={{ aspectRatio: String(ratio), transform: `scale(${scale})` }}>
          {previewUrl ? <img className="asset-zoom-image direct-image" src={previewUrl} alt="" /> : <div className="asset-zoom-image" style={cropStyle} />}
        </div>
      </div>
      <div className="asset-zoom-toolbar" onClick={(event) => event.stopPropagation()}>
        <span className="asset-zoom-name">{element.box_id}</span>
        <button type="button" onClick={() => changeScale(-0.2)} aria-label="缩小">−</button>
        <span className="asset-zoom-readout">{Math.round(scale * 100)}%</span>
        <button type="button" onClick={() => changeScale(0.2)} aria-label="放大">+</button>
        <button type="button" className="asset-zoom-close" onClick={onClose}>关闭</button>
      </div>
    </div>,
    document.body
  );
}

function CanvasEditor({
  assetPlan,
  selectedAssetId,
  figureUrl,
  mode,
  zoom,
  onSelect,
  onChange,
  onBeginEdit,
  onDelete
}: {
  assetPlan: AssetPlan | null;
  selectedAssetId: string;
  figureUrl: string;
  mode: CanvasMode;
  zoom: number;
  onSelect: (id: string) => void;
  onChange: (plan: AssetPlan, options?: AssetPlanChangeOptions) => void;
  onBeginEdit: () => void;
  onDelete: () => void;
}) {
  const imageRef = useRef<HTMLImageElement | null>(null);
  const [naturalSize, setNaturalSize] = useState({ width: 1, height: 1 });
  const [drag, setDrag] = useState<DragState | null>(null);
  const [hoveredAssetId, setHoveredAssetId] = useState("");
  const [guidanceVisible, setGuidanceVisible] = useState(true);
  const [polygonPoints, setPolygonPoints] = useState<Array<[number, number]>>([]);
  const [polygonCursor, setPolygonCursor] = useState<{ x: number; y: number } | null>(null);

  const selectedCandidate = assetPlan?.elements.find((item) => item.box_id === selectedAssetId) || null;
  const selected = selectedCandidate && isEditorSourceStrategy(selectedCandidate.source_strategy) ? selectedCandidate : null;

  function pointFromEvent(event: PointerEvent): { x: number; y: number } {
    const rect = imageRef.current?.getBoundingClientRect();
    if (!rect) return { x: 0, y: 0 };
    return {
      x: clamp(((event.clientX - rect.left) / rect.width) * naturalSize.width, 0, naturalSize.width),
      y: clamp(((event.clientY - rect.top) / rect.height) * naturalSize.height, 0, naturalSize.height)
    };
  }

  function updateElement(id: string, patch: Partial<AssetElement>, options: AssetPlanChangeOptions = {}) {
    if (!assetPlan) return;
    onChange({
      ...assetPlan,
      elements: assetPlan.elements.map((item) => (item.box_id === id ? { ...item, ...patch } : item))
    }, options);
  }

  function cancelPolygon() {
    setPolygonPoints([]);
    setPolygonCursor(null);
  }

  function closePolygon(points: Array<[number, number]>) {
    if (!assetPlan || points.length < 3) return;
    const xs = points.map((p) => p[0]);
    const ys = points.map((p) => p[1]);
    const bbox = normalizeBBox([Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]);
    if (bbox[2] - bbox[0] <= 2 || bbox[3] - bbox[1] <= 2) {
      cancelPolygon();
      return;
    }
    const id = nextNewId(assetPlan.elements);
    onChange({
      ...assetPlan,
      elements: [
        ...assetPlan.elements,
        {
          box_id: id,
          source_candidate_ids: [],
          refinement_action: "added",
          bbox,
          geometry: {
            kind: "polygon",
            points: points.map((point) => [point[0], point[1]]),
            bbox,
            coordinate_system: "figure_image_pixels"
          },
          source_strategy: "crop",
          visual_role: "多边形区域",
          type: "未知",
          confidence: "medium",
          reason: "在 DrawAI 工作台中新增的多边形区域。",
          evidence: []
        }
      ]
    });
    onSelect(id);
    cancelPolygon();
  }

  useEffect(() => {
    if (mode !== "polygon") {
      cancelPolygon();
    }
  }, [mode]);

  useEffect(() => {
    if (mode !== "polygon") return;
    function handleKey(event: globalThis.KeyboardEvent) {
      if (event.key === "Enter") {
        event.preventDefault();
        closePolygon(polygonPoints);
      } else if (event.key === "Escape") {
        cancelPolygon();
      }
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  });

  function onCanvasPointerDown(event: PointerEvent) {
    if (!assetPlan) return;
    if (mode === "polygon") {
      const point = pointFromEvent(event);
      if (polygonPoints.length >= 3) {
        const [fx, fy] = polygonPoints[0];
        const closeThreshold = Math.max(6, Math.min(naturalSize.width, naturalSize.height) * 0.02);
        if (Math.hypot(point.x - fx, point.y - fy) <= closeThreshold) {
          closePolygon(polygonPoints);
          return;
        }
      }
      setPolygonPoints((points) => [...points, [point.x, point.y]]);
      setPolygonCursor(point);
      return;
    }
    if (mode === "select") {
      onSelect("");
      return;
    }
    const point = pointFromEvent(event);
    setDrag({ kind: "add", startX: point.x, startY: point.y, currentX: point.x, currentY: point.y });
  }

  function onPointerMove(event: PointerEvent) {
    if (mode === "polygon") {
      if (polygonPoints.length > 0) setPolygonCursor(pointFromEvent(event));
      return;
    }
    if (!drag || !assetPlan) return;
    const point = pointFromEvent(event);
    if (drag.kind === "move") {
      const dx = point.x - drag.startX;
      const dy = point.y - drag.startY;
      const [x1, y1, x2, y2] = drag.bbox;
      const bbox = normalizeBBox([x1 + dx, y1 + dy, x2 + dx, y2 + dy]);
      updateElement(drag.id, { bbox, geometry: transformGeometryForBBox(drag.geometry, drag.bbox, bbox) }, { track: false });
    } else if (drag.kind === "resize") {
      const bbox = resizeBBox(drag.bbox, drag.handle, point.x - drag.startX, point.y - drag.startY);
      updateElement(drag.id, { bbox, geometry: transformGeometryForBBox(drag.geometry, drag.bbox, bbox) }, { track: false });
    } else {
      setDrag({ ...drag, currentX: point.x, currentY: point.y });
    }
  }

  function onPointerUp() {
    if (drag?.kind === "add" && assetPlan) {
      const bbox = normalizeBBox([drag.startX, drag.startY, drag.currentX, drag.currentY]);
      if (bbox[2] - bbox[0] > 2 && bbox[3] - bbox[1] > 2) {
        const id = nextNewId(assetPlan.elements);
        onChange({
          ...assetPlan,
          elements: [
            ...assetPlan.elements,
            {
              box_id: id,
              source_candidate_ids: [],
              refinement_action: "added",
              bbox,
              source_strategy: "crop",
              visual_role: "新增素材",
              type: "未知",
              confidence: "medium",
              reason: "在 DrawAI 工作台中新增。",
              evidence: []
            }
          ]
        });
        onSelect(id);
      }
    }
    setDrag(null);
  }

  if (!assetPlan) return <EmptyState label="素材还没准备好" />;
  const canvasWidth = naturalSize.width > 1 ? Math.max(320, Math.round(naturalSize.width * zoom)) : undefined;
  const visibleElements = assetPlan.elements
    .filter((element) => isEditorSourceStrategy(element.source_strategy))
    .map((element, originalIndex) => ({ element, originalIndex, area: bboxArea(element.bbox) }))
    .sort((left, right) => right.area - left.area || left.originalIndex - right.originalIndex);
  const hoveredAsset = visibleElements.find(({ element }) => element.box_id === hoveredAssetId)?.element || null;
  return (
    <section className="canvas-layout">
      <div
        className={`canvas-stage ${mode === "add" ? "adding" : ""} ${mode === "polygon" ? "polygon" : ""}`}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerUp}
        onPointerDown={onCanvasPointerDown}
      >
        {figureUrl ? (
          <div className="image-overlay-wrap" style={canvasWidth ? { width: `${canvasWidth}px` } : undefined}>
            <img
              ref={imageRef}
              src={figureUrl}
              onLoad={(event) => setNaturalSize({ width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight })}
            />
            {visibleElements.map(({ element }, layerIndex) => (
              <AssetBox
                key={element.box_id}
                caseId={assetPlan.case_id}
                element={element}
                naturalSize={naturalSize}
                selected={element.box_id === selected?.box_id}
                zIndex={layerIndex + 1}
                onSelect={() => onSelect(element.box_id)}
                onHover={() => setHoveredAssetId(element.box_id)}
                onLeave={() => setHoveredAssetId((id) => (id === element.box_id ? "" : id))}
                onMoveStart={(event) => {
                  event.stopPropagation();
                  const point = pointFromEvent(event);
                  onSelect(element.box_id);
                  onBeginEdit();
                  setDrag({ kind: "move", id: element.box_id, startX: point.x, startY: point.y, bbox: [...element.bbox], geometry: cloneAssetGeometry(element.geometry) });
                }}
                onResizeStart={(event, handle) => {
                  event.stopPropagation();
                  const point = pointFromEvent(event);
                  onSelect(element.box_id);
                  onBeginEdit();
                  setDrag({ kind: "resize", id: element.box_id, handle, startX: point.x, startY: point.y, bbox: [...element.bbox], geometry: cloneAssetGeometry(element.geometry) });
                }}
                onDelete={() => {
                  onSelect(element.box_id);
                  onBeginEdit();
                  onChange({ ...assetPlan, elements: assetPlan.elements.filter((item) => item.box_id !== element.box_id) }, { track: false });
                }}
              />
            ))}
            {hoveredAsset && <AssetTooltip element={hoveredAsset} naturalSize={naturalSize} />}
            {drag?.kind === "add" && <DraftBox bbox={normalizeBBox([drag.startX, drag.startY, drag.currentX, drag.currentY])} naturalSize={naturalSize} />}
            <svg
              className="polygon-overlay"
              viewBox={`0 0 ${naturalSize.width} ${naturalSize.height}`}
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              {visibleElements.map(({ element }) => {
                const points = element.geometry?.kind === "polygon" ? element.geometry.points : null;
                if (!points || points.length < 3) return null;
                return <polygon key={element.box_id} className="polygon-region" points={points.map((p) => p.join(",")).join(" ")} />;
              })}
              {mode === "polygon" && polygonPoints.length > 0 && (
                <polyline
                  className="polygon-draft"
                  points={[...polygonPoints, ...(polygonCursor ? [[polygonCursor.x, polygonCursor.y]] : [])]
                    .map((p) => p.join(","))
                    .join(" ")}
                />
              )}
            </svg>
            {mode === "polygon" &&
              polygonPoints.map((point, index) => (
                <span
                  key={index}
                  className={`polygon-vertex ${index === 0 ? "first" : ""}`}
                  style={{ left: `${(point[0] / naturalSize.width) * 100}%`, top: `${(point[1] / naturalSize.height) * 100}%` }}
                />
              ))}
            {mode === "polygon" && (
              <div className="polygon-hint">
                {polygonPoints.length === 0
                  ? "点击放置多边形顶点"
                  : polygonPoints.length < 3
                  ? "继续放置顶点（至少 3 个）"
                  : "点击起点或按 Enter 闭合 · Esc 取消"}
              </div>
            )}
          </div>
        ) : (
          <EmptyState label="原图还没准备好" />
        )}
      </div>
      {selected && (
        <div className="selection-bar">
          <strong>{selected.box_id}</strong>
          <span>{selected.visual_role || selected.type}</span>
          <div className="selection-strategies">
            {EDITOR_SOURCE_STRATEGIES.map((strategy) => (
              <button key={strategy} className={selected.source_strategy === strategy ? "active" : ""} onClick={() => updateElement(selected.box_id, { source_strategy: strategy })}>
                {strategyLabels[strategy]}
              </button>
            ))}
          </div>
          <button className="danger subtle" onClick={onDelete}>删除</button>
        </div>
      )}
      {guidanceVisible && (
        <aside className="asset-guidance-panel">
          <button className="asset-guidance-close" type="button" aria-label="关闭提示" onClick={() => setGuidanceVisible(false)}>
            ×
          </button>
          <span>当前阶段</span>
          <strong>框选需要像素级保留的元素</strong>
          <p>请只标记需要从原图精确抠图并贴回的区域，例如照片、截图、复杂图标、纹理、热力图或很难用 SVG 忠实重画的局部。</p>
          <p>文本、箭头、表格线、坐标轴和简单几何图形通常留给后续 SVG 阶段重建。</p>
          <div className="asset-guidance-options">
            <em className="strategy-crop">保留背景</em>
            <small>裁剪区域和局部背景一起保留。</small>
            <em className="strategy-nobg">去背景</em>
            <small>只保留前景主体，背景由 SVG 重新铺回。</small>
          </div>
        </aside>
      )}
    </section>
  );
}

function AssetBox({
  caseId,
  element,
  naturalSize,
  selected,
  zIndex,
  onSelect,
  onHover,
  onLeave,
  onMoveStart,
  onResizeStart,
  onDelete
}: {
  caseId: string;
  element: AssetElement;
  naturalSize: { width: number; height: number };
  selected: boolean;
  zIndex: number;
  onSelect: () => void;
  onHover: () => void;
  onLeave: () => void;
  onMoveStart: (event: PointerEvent) => void;
  onResizeStart: (event: PointerEvent, handle: string) => void;
  onDelete: () => void;
}) {
  const style = { ...bboxStyle(element.bbox, naturalSize), zIndex };
  const geometryLabelText = geometryLabel(element);
  const geometryPreviewUrl = assetGeometryPreviewUrl(element, caseId);
  return (
    <div
      className={`asset-box ${strategyClass[element.source_strategy]} ${geometryClass(element)} ${selected ? "selected" : ""}`}
      data-asset-id={element.box_id}
      style={style}
      onPointerDown={onMoveStart}
      onPointerEnter={onHover}
      onPointerLeave={onLeave}
      onMouseEnter={onHover}
      onMouseLeave={onLeave}
      onClick={onSelect}
      onContextMenu={(event) => {
        event.preventDefault();
        event.stopPropagation();
        onDelete();
      }}
    >
      {geometryPreviewUrl && <img className="asset-mask-preview" src={geometryPreviewUrl} alt="" draggable={false} />}
      <span className="asset-badge">
        {element.box_id} · {strategyLabels[element.source_strategy]}
        {geometryLabelText ? ` · ${geometryLabelText}` : ""}
      </span>
      {selected &&
        ["nw", "ne", "sw", "se"].map((handle) => (
          <button key={handle} className={`resize-handle ${handle}`} onPointerDown={(event) => onResizeStart(event, handle)} aria-label={`resize ${handle}`} />
        ))}
    </div>
  );
}

function AssetTooltip({ element, naturalSize }: { element: AssetElement; naturalSize: { width: number; height: number } }) {
  const label = geometryLabel(element);
  return (
    <div className={`canvas-tooltip ${strategyClass[element.source_strategy]}`} style={tooltipStyle(element.bbox, naturalSize)}>
      <strong>{element.box_id}</strong>
      <em>{element.visual_role || element.type}</em>
      <small>{strategyLabels[element.source_strategy]} · {element.confidence}{label ? ` · ${label}` : ""}</small>
      <p>{element.reason || "暂无说明"}</p>
    </div>
  );
}

function DraftBox({ bbox, naturalSize }: { bbox: [number, number, number, number]; naturalSize: { width: number; height: number } }) {
  return <div className="draft-box" style={{ ...bboxStyle(bbox, naturalSize), zIndex: 1_000_000 }} />;
}

function SelectToolIcon() {
  return (
    <svg className="tool-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path d="M6.2 3.8L15.4 10l-4.1 1.2 2.2 4-2.1 1.1-2.2-4-3 3.3V3.8z" />
    </svg>
  );
}

function AddBoxToolIcon() {
  return (
    <svg className="tool-icon box-tool-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path d="M4 7V4h3" />
      <path d="M13 4h3v3" />
      <path d="M16 13v3h-3" />
      <path d="M7 16H4v-3" />
      <path d="M8 4h4" />
      <path d="M16 8v4" />
      <path d="M12 16H8" />
      <path d="M4 12V8" />
      <path className="box-tool-plus" d="M10 7.2v5.6M7.2 10h5.6" />
    </svg>
  );
}

function UndoToolIcon() {
  return (
    <svg className="tool-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path d="M8 5L4.8 8.2 8 11.4" />
      <path d="M5.2 8.2h6.1c2.5 0 4.5 1.8 4.5 4.2 0 1.6-.8 2.9-2.1 3.6" />
    </svg>
  );
}

function PolygonToolIcon() {
  return (
    <svg className="tool-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path d="M10 3.2 16.6 8.1 14 15.8H6L3.4 8.1Z" />
      <circle cx="10" cy="3.2" r="1.5" />
      <circle cx="16.6" cy="8.1" r="1.5" />
      <circle cx="3.4" cy="8.1" r="1.5" />
    </svg>
  );
}

function MaskToolIcon() {
  return (
    <svg className="tool-icon mask-tool-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path d="M6 5.4c1.4-1.6 4-1.9 6-0.8 2.4 1.3 3.6 3.4 2.7 6.1-0.7 2.2-2 4-4.8 4.2-3 0.2-5.3-1.1-6-3.6-0.5-1.9 0.5-3.5 0.4-5.1 0-0.3 0.6-0.5 1.7-0.8Z" />
    </svg>
  );
}

function TextToolIcon() {
  return (
    <svg className="tool-icon text-tool-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path d="M5 5.2h10" />
      <path d="M10 5.2v9.6" />
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg className="tool-icon settings-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path d="M10 7.2a2.8 2.8 0 1 0 0 5.6 2.8 2.8 0 0 0 0-5.6Z" />
      <path d="m10.6 2.6.7 1.7c.4.1.8.3 1.2.5l1.7-.7 1.3 1.3-.8 1.7c.2.4.4.8.5 1.2l1.7.7v2l-1.7.7c-.1.4-.3.8-.5 1.2l.8 1.7-1.3 1.3-1.7-.7c-.4.2-.8.4-1.2.5l-.7 1.7H9.4l-.7-1.7c-.4-.1-.8-.3-1.2-.5l-1.7.7-1.3-1.3.8-1.7c-.2-.4-.4-.8-.5-1.2L3.1 11V9l1.7-.7c.1-.4.3-.8.5-1.2l-.8-1.7 1.3-1.3 1.7.7c.4-.2.8-.4 1.2-.5l.7-1.7h1.2Z" />
    </svg>
  );
}

function HomeIcon() {
  return (
    <svg className="tool-icon home-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path d="M3.7 9.1 10 3.7l6.3 5.4" />
      <path d="M5.2 8.4v7.1h3.3v-4.2h3v4.2h3.3V8.4" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg className="plus-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path d="M10 4.6v10.8M4.6 10h10.8" />
    </svg>
  );
}

function PlayIcon() {
  return (
    <svg className="play-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path d="M7 4.8v10.4L15 10 7 4.8Z" />
    </svg>
  );
}

function RetryIcon() {
  return (
    <svg className="retry-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path d="M15.7 8.2a5.6 5.6 0 1 0 1.1 3.3" />
      <path d="M15.8 4.7v3.5h-3.5" />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg className="download-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path d="M10 3.8v7.3" />
      <path d="M6.8 8.3 10 11.5l3.2-3.2" />
      <path d="M4.6 15.8h10.8" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg className="upload-icon" viewBox="0 0 28 28" aria-hidden="true">
      <path d="M8.4 18.7H7.1a4.3 4.3 0 0 1-.6-8.6 7 7 0 0 1 13.1-1.7 5.1 5.1 0 0 1 1.2 10.1h-1.4" />
      <path d="M14 20.7V10.9" />
      <path d="M10.5 14.2 14 10.7l3.5 3.5" />
    </svg>
  );
}

function ButtonSpinner() {
  return <span className="button-spinner" aria-hidden="true" />;
}

function ProgressView({ progress, caseDetail }: { progress: CaseProgress | null; caseDetail: CaseDetail | null }) {
  if (!caseDetail) return <EmptyState label="请选择一张图" />;
  const stageRuns = progress?.stage_runs || caseDetail.stage_runs;
  const running = latestStageRun(stageRuns, (stage) => stage.status === "running");
  const semanticFile = latestProgressFile(progress, "semantic_svg");
  const hasSvgOk = stageRuns.some((stage) => stageMatchesNode(stage.stage_name, "compose_svg") && stage.status === "ok");
  return (
    <div className="progress-view">
      <section className="progress-hero">
        <div>
          <span>当前图片</span>
          <strong>{caseDetail.case.name}</strong>
          <em>{humanize(caseDetail.case.status)} · {humanize(caseDetail.case.phase)} / {humanize(caseDetail.case.stage)}</em>
        </div>
        <div>
          <span>运行目录</span>
          <code>{caseDetail.case.run_root}</code>
        </div>
      </section>

      {hasSvgOk && !semanticFile?.exists && (
        <section className="progress-warning">
          <strong>SVG 阶段之前成功过，但当前最终 SVG 文件暂不可用。</strong>
          <span>可能是后续 SVG 尝试仍在运行，或输出目录已被重建。只有 `svg/semantic.svg` 再次生成后，SVG 画布才能显示结果。</span>
        </section>
      )}

      <SvgStatusPanel caseDetail={caseDetail} stageRuns={stageRuns} />
      <PptxExportStatusPanel exportProgress={progress?.pptx_export} />

      <section className="progress-grid">
        <div className="progress-panel">
          <h2>阶段运行记录</h2>
          {stageRuns.slice().reverse().map((stage) => (
            <StageRunRow key={stage.stage_run_id} stage={stage} highlighted={stage.stage_run_id === running?.stage_run_id} />
          ))}
        </div>
      </section>
    </div>
  );
}

function SvgStatusPanel({
  caseDetail,
  stageRuns
}: {
  caseDetail: CaseDetail;
  stageRuns: StageRunRecord[];
}) {
  const runningSvg = latestStageRun(stageRuns, (stage) => stageMatchesNode(stage.stage_name, "compose_svg") && stage.status === "running");
  const latestSvg = latestStageRun(stageRuns, (stage) => stageMatchesNode(stage.stage_name, "compose_svg"));
  const latestFailedSvg = latestStageRun(stageRuns, (stage) => stageMatchesNode(stage.stage_name, "compose_svg") && stage.status === "failed");
  const status = runningSvg ? "running" : latestSvg?.status === "failed" ? "failed" : latestSvg?.status || caseDetail.case.status;
  const title = runningSvg
    ? "SVG 运行中"
    : latestSvg
      ? `SVG ${humanize(latestSvg.status)}`
      : "SVG 尚未开始";
  const subtitle = runningSvg
    ? durationText(runningSvg.started_at, "")
    : latestSvg
      ? durationText(latestSvg.started_at, latestSvg.ended_at)
      : "等待中";
  const failure = runningSvg ? "" : latestSvg?.status === "failed" ? latestSvg.error_message : latestFailedSvg?.error_message;

  return (
    <section className={`svg-status-card ${status}`}>
      <div className="svg-status-main">
        <span>SVG 状态</span>
        <strong>{title}</strong>
        <em>{subtitle}</em>
      </div>
      {failure && (
        <div className="svg-status-detail">
          <span>失败原因</span>
          <p className="stage-failure">{failure}</p>
        </div>
      )}
    </section>
  );
}


function PptxExportStatusPanel({ exportProgress }: { exportProgress: CaseProgress["pptx_export"] | undefined }) {
  if (!exportProgress || exportProgress.status === "missing") return null;
  const mode = pptxExportModeLabel(exportProgress.effective_export_mode || exportProgress.export_mode);
  const surface = pptxEditableSurfaceLabel(exportProgress.editable_surface);
  const status = exportProgress.status === "ok" ? "done" : exportProgress.status || "waiting";
  return (
    <section className={`svg-status-card ${status}`}>
      <div className="svg-status-main">
        <span>PPTX 导出</span>
        <strong>{mode}</strong>
        <em>{exportProgress.export_backend || "export backend"}</em>
      </div>
      <div className="svg-status-detail">
        <span>编辑面</span>
        <p>{surface || exportProgress.editable_surface || "未知"}</p>
      </div>
    </section>
  );
}


function pptxExportModeLabel(mode: string): string {
  if (mode === "native_shapes") return "原生形状";
  return mode || "未知";
}


function pptxEditableSurfaceLabel(surface: string): string {
  if (surface === "native_shapes") return "拆分元素";
  return surface;
}


function StageRunRow({ stage, highlighted }: { stage: StageRunRecord; highlighted: boolean }) {
  return (
    <div className={`stage-run-row ${stage.status} ${highlighted ? "highlighted" : ""}`}>
      <div>
        <b>{humanize(stage.stage_name)}</b>
        <span>{humanize(stage.status)}</span>
      </div>
      <em>{durationText(stage.started_at, stage.ended_at)}</em>
      {stage.error_message && <p>{stage.error_message}</p>}
    </div>
  );
}

type PipelineNodeSpec = (typeof PIPELINE_GROUPS)[number]["nodes"][number];

type PipelineNodeView = {
  stage: string;
  title: string;
  detail: string;
  description: string;
  state: PipelineNodeState;
  meta: string;
  error: string;
};

function pipelineNodeState(
  node: PipelineNodeSpec,
  caseDetail: CaseDetail,
  stageRuns: StageRunRecord[],
  files: CaseProgress["files"],
  artifacts: ArtifactRecord[]
): PipelineNodeView {
  const latest = latestStageRun(stageRuns, (stage) => stageMatchesNode(stage.stage_name, node.stage));
  const current = caseDetail.case;
  let state: PipelineNodeState = "waiting";
  let meta: string = node.detail;
  let error = "";

  if (node.stage === "plan_assets") {
    const planned = artifactOrFileReady(["asset_manifest", "approved_asset_plan", "asset_draft"], files, artifacts);
    if (planned || current.stage === "process_assets" || current.stage === "compose_svg" || current.stage === "export" || current.stage === "completed" || current.status === "completed") {
      state = "done";
      meta = planned ? "资产计划已写入" : "已计划";
    } else if (current.status === "assets_review") {
      state = "review";
      meta = "等待资产确认";
    }
  } else if (node.stage === "process_assets") {
    const planned = artifactOrFileReady(["asset_manifest", "approved_asset_plan"], files, artifacts);
    if (!planned) {
      meta = "等待资产计划";
    } else if (latest) {
      if (latest.status === "ok") {
        state = "done";
        meta = durationText(latest.started_at, latest.ended_at);
      } else if (latest.status === "running") {
        state = "running";
        meta = durationText(latest.started_at, "");
      } else if (latest.status === "failed") {
        state = "failed";
        meta = "失败";
        error = latest.error_message;
      }
    } else if (current.stage === "compose_svg" || current.stage === "export" || current.status === "completed") {
      state = "done";
      meta = "素材已处理";
    } else if (stageMatchesNode(current.stage, node.stage)) {
      if (current.status === "failed") {
        state = "failed";
        meta = "失败";
        error = current.error_message;
      } else if (current.status === "analysis_running" || current.status === "svg_running") {
        state = "running";
        meta = "正在运行";
      }
    }
  } else if (latest) {
    if (latest.status === "ok") {
      state = "done";
      meta = durationText(latest.started_at, latest.ended_at);
    } else if (latest.status === "running") {
      state = "running";
      meta = durationText(latest.started_at, "");
    } else if (latest.status === "failed") {
      state = "failed";
      meta = "失败";
      error = latest.error_message;
    }
  } else if (artifactOrFileReady(stageReadyLabels(node.stage), files, artifacts)) {
    state = "done";
    meta = "输出文件已准备";
  } else if (current.status === "completed") {
    state = "done";
    meta = "已完成";
  } else if (stageMatchesNode(current.stage, node.stage)) {
    if (current.status === "failed") {
      state = "failed";
      meta = "失败";
      error = current.error_message;
    } else if (current.status === "analysis_running" || current.status === "svg_running") {
      state = "running";
      meta = "正在运行";
    }
  }

  if (state === "done" && isStaleStage(current.stale_from_stage, node.stage)) {
    state = "stale";
    meta = "需重新运行";
  }

  return {
    stage: node.stage,
    title: node.title,
    detail: node.detail,
    description: node.description,
    state,
    meta,
    error
  };
}

function stageReadyLabels(stage: string): string[] {
  if (stage === "prepare") return ["figure"];
  if (stage === "parse_elements") return ["raw_regions", "ocr_boxes", "parser_outputs"];
  if (stage === "fuse_elements") return ["box_ir", "fusion_trace"];
  if (stage === "refine_elements") return ["element_analysis", "refine_trace", "asset_draft"];
  if (stage === "plan_assets") return ["asset_manifest", "approved_asset_plan"];
  if (stage === "process_assets") return ["processor_trace"];
  if (stage === "compose_svg") return ["semantic_svg", "rendered_png", "svg_validation_report"];
  if (stage === "export") return ["pptx", "pptx_export_report"];
  return [];
}

function artifactOrFileReady(labels: string[], files: CaseProgress["files"], artifacts: ArtifactRecord[]): boolean {
  return labels.some(
    (label) => files.some((file) => file.label === label && file.exists) || artifacts.some((artifact) => artifact.label === label)
  );
}

function isStaleStage(staleFromStage: string, stage: string): boolean {
  if (!staleFromStage) return false;
  const stageOrder = PIPELINE_STAGE_ORDER as readonly string[];
  const staleIndex = stageOrder.indexOf(canonicalPipelineStage(staleFromStage));
  const stageIndex = stageOrder.indexOf(canonicalPipelineStage(stage));
  return staleIndex >= 0 && stageIndex >= staleIndex;
}

function canonicalPipelineStage(stage: string): (typeof PIPELINE_STAGE_ORDER)[number] | "" {
  const aliases: Record<string, (typeof PIPELINE_STAGE_ORDER)[number]> = {
    analysis: "prepare",
    detect_structure: "parse_elements",
    detect_text: "parse_elements",
    assemble_boxir: "fuse_elements",
    asset_analyze: "refine_elements",
    asset_plan: "plan_assets",
    approved_asset_plan: "plan_assets",
    materialize: "process_assets",
    asset_materialize: "process_assets",
    asset_processing: "process_assets",
    svg: "compose_svg",
    compose: "compose_svg",
    svg_edit: "compose_svg",
    package: "package_run"
  };
  if ((PIPELINE_STAGE_ORDER as readonly string[]).includes(stage)) {
    return stage as (typeof PIPELINE_STAGE_ORDER)[number];
  }
  return aliases[stage] || "";
}

function stageMatchesNode(stageName: string, nodeStage: string): boolean {
  return canonicalPipelineStage(stageName) === canonicalPipelineStage(nodeStage);
}

function stateLabel(state: PipelineNodeState): string {
  const labels: Record<PipelineNodeState, string> = {
    waiting: "等待中",
    running: "运行中",
    done: "完成",
    failed: "失败",
    review: "待确认",
    stale: "需更新"
  };
  return labels[state];
}

function EmptyState({ label }: { label: string }) {
  return <div className="empty-state">{label}</div>;
}

function assetPackageFromRunPackage(runPackage: V2RunPackage | null, elementId: string): V2AssetPackage | null {
  return (runPackage?.asset_packages || []).find((assetPackage) => assetPackage.element_id === elementId) || null;
}

function hasBlockingAssetPackage(runPackage: V2RunPackage): boolean {
  return (runPackage.asset_packages || []).some((assetPackage) => assetPackage.status === "failed" || assetPackage.status === "unsupported");
}

function v2PlannedProcessor(element: V2ElementPlan): V2ProcessorType | null {
  const processor = element.processing_intent.processing_type as V2ProcessorType;
  return V2_PROCESSABLE_PROCESSORS.includes(processor) ? processor : null;
}

function v2ProcessorLabel(processor: V2ProcessorType): string {
  const labels: Record<V2ProcessorType, string> = {
    crop: "Crop",
    crop_nobg: "No BG",
    image_generate: "Generate",
    image_edit: "Edit",
    chart_rebuild_reserved: "Chart Agent"
  };
  return labels[processor];
}

function v2AssetStatusClass(status: string): string {
  if (status === "failed") return "asset-status-failed";
  if (status === "unsupported") return "asset-status-unsupported";
  if (status === "ok") return "asset-status-ok";
  if (status === "running") return "asset-status-running";
  return "";
}

function v2AssetResultUrl(activeCase: CaseDetail | null, result: V2AssetResult | null): string {
  if (!result?.path) return "";
  if (/^https?:\/\//i.test(result.path)) return result.path;
  if (!activeCase) return "";
  return caseFileUrl(activeCase.case.case_id, result.path, result.created_at || result.result_id);
}

function v2ResultLabel(result: V2AssetResult): string {
  if (result.path) {
    const parts = result.path.split("/");
    return parts[parts.length - 1] || result.result_id;
  }
  return result.result_id;
}

function v2ElementProcessingClass(element: V2ElementPlan): string {
  const processing = element.processing_intent.processing_type;
  if (processing === "crop_nobg") return "strategy-nobg";
  if (processing === "crop") return "strategy-crop";
  return "strategy-svg";
}

function caseHasLegacyArtifacts(detail: CaseDetail): boolean {
  if (detail.case.compatibility_mode === "legacy_readonly") return true;
  const legacyLabels = new Set(["asset_draft", "approved_asset_plan", "asset_manifest", "semantic_svg", "rendered_png", "pptx"]);
  return detail.artifacts.some((artifact) => legacyLabels.has(artifact.label));
}

function compactJson(value: Record<string, unknown>): string {
  const keys = Object.keys(value || {});
  if (keys.length === 0) return "{}";
  return JSON.stringify(value);
}

function shortenError(value: string): string {
  return value.length > 180 ? `${value.slice(0, 180)}...` : value;
}

function humanize(value: string): string {
  const labels: Record<string, string> = {
    idle: "空闲",
    "select a case": "请选择图片",
    queued: "排队中",
    running: "运行中",
    waiting: "等待中",
    waiting_review: "待确认",
    assets_review: "素材确认",
    completed: "已完成",
    failed: "失败",
    canceled: "已取消",
    stale: "需更新",
    review: "待确认",
    done: "完成",
    ok: "完成",
    analysis: "分析",
    reconstruction: "重建",
    prepare: "图像预处理",
    parse_elements: "元素解析",
    fuse_elements: "候选融合",
    refine_elements: "Agent 校验",
    plan_assets: "资产计划",
    process_assets: "资产处理",
    compose: "SVG 组合",
    compose_svg: "SVG 组合",
    package_run: "运行包封装",
    detect_structure: "提取结构（SAM）",
    detect_text: "OCR解析",
    assemble_boxir: "素材合并",
    asset_plan: "素材规划",
    asset_materialize: "素材处理",
    asset_analyze: "素材调整",
    asset_draft: "素材草稿",
    asset_processing: "素材处理",
    materialize: "素材处理",
    approved_asset_plan: "素材确认",
    svg: "SVG生成",
    svg_edit: "SVG 编辑",
    export: "导出",
    crop: "裁剪",
    crop_nobg: "去背景",
    svg_self_draw: "SVG 自绘",
    image_generate: "生成图",
    image_edit: "编辑图",
    chart_rebuild_reserved: "图表 Agent",
    picture: "图片",
    icon: "图标",
    chart: "图表",
    table: "表格",
    text: "文本",
    frame: "框架",
    pending: "待处理",
    unsupported: "暂不支持",
    analysis_running: "分析中",
    svg_running: "SVG生成中"
  };
  return labels[value] || value.replace(/_/g, " ");
}

function caseInitials(value: string): string {
  return value
    .split(/[\s._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((item) => item[0]?.toUpperCase())
    .join("") || "D";
}

function caseCountTotal(counts: Record<string, number>): number {
  return Object.values(counts || {}).reduce((total, value) => total + value, 0);
}

function loadImageGenConnectionSettings(): ImageGenConnectionSettings {
  if (typeof window === "undefined") return DEFAULT_IMAGEGEN_CONNECTION;
  const raw = window.localStorage.getItem(IMAGEGEN_SETTINGS_STORAGE_KEY);
  if (!raw) return DEFAULT_IMAGEGEN_CONNECTION;
  try {
    const parsed = JSON.parse(raw) as Partial<ImageGenConnectionSettings>;
    return {
      provider: parsed.provider === "codex" ? "codex" : "api",
      baseUrl: typeof parsed.baseUrl === "string" ? parsed.baseUrl : "",
      apiKey: typeof parsed.apiKey === "string" ? parsed.apiKey : "",
      model: typeof parsed.model === "string" && parsed.model.trim() ? parsed.model : DEFAULT_IMAGEGEN_CONNECTION.model
    };
  } catch {
    return DEFAULT_IMAGEGEN_CONNECTION;
  }
}

function saveImageGenConnectionSettings(connection: ImageGenConnectionSettings): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(IMAGEGEN_SETTINGS_STORAGE_KEY, JSON.stringify(connection));
}

function submittedTimeText(value: string): string {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "-";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

const EDITABLE_SVG_TAGS = new Set(["g", "path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "text", "tspan", "image", "use"]);
const TEXT_EDITABLE_SVG_TAGS = new Set(["text", "tspan"]);
const UNSAFE_INLINE_SVG_TAGS = new Set(["script", "foreignObject", "iframe", "object", "embed"]);

function buildSvgPreviewModel(svgText: string, caseId: string, selectedPath: string): SvgPreviewModel {
  if (!svgText.trim()) return { svg: "", elements: [], error: "" };
  const doc = new DOMParser().parseFromString(svgText, "image/svg+xml");
  const parseError = doc.querySelector("parsererror");
  if (parseError) {
    return { svg: "", elements: [], error: parseError.textContent?.trim() || "SVG 源码不是有效的 XML。" };
  }
  const root = doc.documentElement;
  if (!root || root.localName !== "svg") {
    return { svg: "", elements: [], error: "SVG 源码必须以 <svg> 根节点开始。" };
  }
  sanitizePreviewSvg(root);
  rewritePreviewSvgLinks(root, caseId);
  const elements: SvgEditableElement[] = [];
  for (const element of Array.from(root.querySelectorAll("*"))) {
    if (!isEditableSvgElement(element)) continue;
    const path = svgElementPath(root, element);
    if (!path) continue;
    element.setAttribute("data-drawai-editable", "true");
    element.setAttribute("data-drawai-path", path);
    if (path === selectedPath) element.setAttribute("data-drawai-selected", "true");
    elements.push({
      path,
      tag: element.localName,
      label: svgElementLabel(element),
      detail: svgElementDetail(element),
      text: svgElementTextValue(element),
      textEditable: TEXT_EDITABLE_SVG_TAGS.has(element.localName)
    });
  }
  return { svg: new XMLSerializer().serializeToString(root), elements, error: "" };
}

function sanitizePreviewSvg(root: Element) {
  for (const element of Array.from(root.querySelectorAll("*"))) {
    if (UNSAFE_INLINE_SVG_TAGS.has(element.localName)) {
      element.remove();
      continue;
    }
    for (const attribute of Array.from(element.attributes)) {
      const name = attribute.name.toLowerCase();
      const value = attribute.value.trim().toLowerCase();
      if (name.startsWith("on") || ((name === "href" || name.endsWith(":href") || name === "src") && value.startsWith("javascript:"))) {
        element.removeAttribute(attribute.name);
      }
    }
  }
}

function rewritePreviewSvgLinks(root: Element, caseId: string) {
  for (const element of Array.from(root.querySelectorAll("*"))) {
    for (const attributeName of ["href", "xlink:href"]) {
      const value = element.getAttribute(attributeName);
      if (!value || !shouldRewriteSvgHref(value)) continue;
      element.setAttribute(attributeName, `/api/cases/${caseId}/files/${encodeSvgPath(resolveSvgHrefRelativeToSvgDir(value))}`);
    }
  }
}

function shouldRewriteSvgHref(value: string): boolean {
  const trimmed = value.trim();
  return Boolean(trimmed) && !trimmed.startsWith("#") && !trimmed.startsWith("/") && !/^[a-z][a-z0-9+.-]*:/i.test(trimmed);
}

function resolveSvgHrefRelativeToSvgDir(value: string): string {
  const parts: string[] = [];
  for (const segment of `svg/${value}`.split("/")) {
    if (!segment || segment === ".") continue;
    if (segment === "..") {
      parts.pop();
    } else {
      parts.push(segment);
    }
  }
  return parts.join("/");
}

function encodeSvgPath(value: string): string {
  return value.split("/").map((part) => encodeURIComponent(part)).join("/");
}

function isEditableSvgElement(element: Element): boolean {
  return EDITABLE_SVG_TAGS.has(element.localName);
}

function svgElementPath(root: Element, element: Element): string {
  const parts: string[] = [];
  let current: Element | null = element;
  while (current && current !== root) {
    const parent: Element | null = current.parentElement;
    if (!parent) return "";
    const siblings = Array.from(parent.children);
    parts.unshift(String(siblings.indexOf(current)));
    current = parent;
  }
  return parts.join(".");
}

function svgElementByPath(root: Element, path: string): Element | null {
  let current: Element = root;
  for (const part of path.split(".")) {
    const index = Number(part);
    if (!Number.isInteger(index) || index < 0) return null;
    const next = current.children.item(index);
    if (!(next instanceof Element)) return null;
    current = next;
  }
  return current;
}

function svgElementLabel(element: Element): string {
  const explicit = element.getAttribute("id") || element.getAttribute("data-pb-role") || element.getAttribute("aria-label");
  if (explicit) return truncateInline(explicit, 34);
  const text = element.textContent?.replace(/\s+/g, " ").trim();
  return truncateInline(text || "可编辑元素", 34);
}

function svgElementDetail(element: Element): string {
  const attrs = ["x", "y", "cx", "cy", "x1", "y1", "x2", "y2", "width", "height", "transform"]
    .map((name) => {
      const value = element.getAttribute(name);
      return value ? `${name}=${truncateInline(value, 28)}` : "";
    })
    .filter(Boolean);
  return attrs.length ? attrs.join(" · ") : svgElementLabel(element);
}

function svgElementTextValue(element: Element): string {
  return TEXT_EDITABLE_SVG_TAGS.has(element.localName) ? element.textContent || "" : "";
}

function selectedSvgElementCenter(surface: HTMLDivElement | null, path: string): { x: number; y: number } | null {
  const svgElement = surface?.querySelector("svg") as SVGSVGElement | null;
  const target = surface?.querySelector(`[data-drawai-path="${cssAttributeValue(path)}"]`) as SVGGraphicsElement | null;
  if (!svgElement || !target) return null;
  const rect = target.getBoundingClientRect();
  const point = svgElement.createSVGPoint();
  point.x = rect.left + rect.width / 2;
  point.y = rect.top + rect.height / 2;
  const matrix = svgElement.getScreenCTM();
  if (!matrix) return null;
  const transformed = point.matrixTransform(matrix.inverse());
  return { x: transformed.x, y: transformed.y };
}

function cssAttributeValue(value: string): string {
  return value.replace(/\\/g, "\\\\").replace(/"/g, "\\\"");
}

function translateSvgElement(svgText: string, path: string, dx: number, dy: number): string {
  const doc = new DOMParser().parseFromString(svgText, "image/svg+xml");
  const root = doc.documentElement;
  const element = root?.localName === "svg" ? svgElementByPath(root, path) : null;
  if (!element) return svgText;
  applySvgTranslation(element, dx, dy);
  return new XMLSerializer().serializeToString(root);
}

function scaleSvgElement(svgText: string, path: string, factor: number, center: { x: number; y: number } | null): string {
  const doc = new DOMParser().parseFromString(svgText, "image/svg+xml");
  const root = doc.documentElement;
  const element = root?.localName === "svg" ? svgElementByPath(root, path) : null;
  if (!element) return svgText;
  applySvgScale(element, factor, center);
  return new XMLSerializer().serializeToString(root);
}

function updateSvgElementText(svgText: string, path: string, value: string): string {
  const doc = new DOMParser().parseFromString(svgText, "image/svg+xml");
  const root = doc.documentElement;
  const element = root?.localName === "svg" ? svgElementByPath(root, path) : null;
  if (!element || !TEXT_EDITABLE_SVG_TAGS.has(element.localName)) return svgText;
  element.textContent = value;
  return new XMLSerializer().serializeToString(root);
}

function removeSvgElement(svgText: string, path: string): string {
  const doc = new DOMParser().parseFromString(svgText, "image/svg+xml");
  const root = doc.documentElement;
  const element = root?.localName === "svg" ? svgElementByPath(root, path) : null;
  if (!element || element === root) return svgText;
  element.remove();
  return new XMLSerializer().serializeToString(root);
}

function svgSelectionOverlay(surface: HTMLDivElement | null, path: string): SvgSelectionOverlay | null {
  if (!surface || !path) return null;
  const artboard = surface.querySelector(".svg-artboard") as HTMLElement | null;
  const target = surface.querySelector(`[data-drawai-path="${cssAttributeValue(path)}"]`) as SVGGraphicsElement | null;
  if (!artboard || !target) return null;
  const artboardRect = artboard.getBoundingClientRect();
  const targetRect = target.getBoundingClientRect();
  if (!Number.isFinite(targetRect.width) || !Number.isFinite(targetRect.height) || targetRect.width <= 0 || targetRect.height <= 0) return null;
  return {
    left: targetRect.left - artboardRect.left,
    top: targetRect.top - artboardRect.top,
    width: targetRect.width,
    height: targetRect.height,
    centerClientX: targetRect.left + targetRect.width / 2,
    centerClientY: targetRect.top + targetRect.height / 2
  };
}

function svgOverlayStyle(overlay: SvgSelectionOverlay) {
  return {
    left: `${overlay.left}px`,
    top: `${overlay.top}px`,
    width: `${overlay.width}px`,
    height: `${overlay.height}px`
  };
}

function svgTextEditorStyle(overlay: SvgSelectionOverlay) {
  const top = overlay.top > 44 ? overlay.top - 42 : overlay.top + overlay.height + 10;
  return {
    left: `${overlay.left}px`,
    top: `${top}px`,
    minWidth: `${Math.max(180, overlay.width)}px`
  };
}

function applySvgTranslation(element: Element, dx: number, dy: number) {
  const tag = element.localName;
  if (tag === "line") {
    const moved = ["x1", "x2"].map((attr) => translateSvgNumberAttr(element, attr, dx)).some(Boolean);
    const movedY = ["y1", "y2"].map((attr) => translateSvgNumberAttr(element, attr, dy)).some(Boolean);
    if (moved || movedY) return;
  }
  if (tag === "polyline" || tag === "polygon") {
    if (translateSvgPoints(element, dx, dy)) return;
  }
  const movedX = translateSvgNumberAttr(element, "x", dx) || translateSvgNumberAttr(element, "cx", dx);
  const movedY = translateSvgNumberAttr(element, "y", dy) || translateSvgNumberAttr(element, "cy", dy);
  if (movedX || movedY) return;
  const existing = element.getAttribute("transform") || "";
  element.setAttribute("transform", `translate(${formatSvgNumber(dx)} ${formatSvgNumber(dy)})${existing ? ` ${existing}` : ""}`);
}

function applySvgScale(element: Element, factor: number, center: { x: number; y: number } | null) {
  const safeFactor = clamp(factor, 0.1, 10);
  const existing = element.getAttribute("transform") || "";
  if (center) {
    const transform = `translate(${formatSvgNumber(center.x)} ${formatSvgNumber(center.y)}) scale(${formatSvgNumber(safeFactor)}) translate(${formatSvgNumber(-center.x)} ${formatSvgNumber(-center.y)})`;
    element.setAttribute("transform", existing ? `${transform} ${existing}` : transform);
    return;
  }
  element.setAttribute("transform", existing ? `scale(${formatSvgNumber(safeFactor)}) ${existing}` : `scale(${formatSvgNumber(safeFactor)})`);
}

function translateSvgNumberAttr(element: Element, attr: string, delta: number): boolean {
  const raw = element.getAttribute(attr);
  if (raw === null) return false;
  const numeric = Number.parseFloat(raw);
  if (!Number.isFinite(numeric)) return false;
  element.setAttribute(attr, formatSvgNumber(numeric + delta));
  return true;
}

function translateSvgPoints(element: Element, dx: number, dy: number): boolean {
  const raw = element.getAttribute("points");
  if (!raw) return false;
  const next = raw
    .trim()
    .split(/\s+/)
    .map((point) => {
      const [xRaw, yRaw] = point.split(",");
      const x = Number.parseFloat(xRaw);
      const y = Number.parseFloat(yRaw);
      return Number.isFinite(x) && Number.isFinite(y) ? `${formatSvgNumber(x + dx)},${formatSvgNumber(y + dy)}` : point;
    })
    .join(" ");
  element.setAttribute("points", next);
  return next !== raw;
}

function parseSvgViewBox(value: string): { x: number; y: number; width: number; height: number } | null {
  const parts = value.trim().split(/[\s,]+/).map(Number);
  if (parts.length !== 4 || parts.some((part) => !Number.isFinite(part))) return null;
  return { x: parts[0], y: parts[1], width: parts[2], height: parts[3] };
}

function fallbackSvgViewport(svgElement: Element | null | undefined, rect: DOMRect): { x: number; y: number; width: number; height: number } {
  const width = Number.parseFloat(svgElement?.getAttribute("width") || "") || rect.width;
  const height = Number.parseFloat(svgElement?.getAttribute("height") || "") || rect.height;
  return { x: 0, y: 0, width, height };
}

async function exportSvgPng(svgText: string, filename: string, caseId: string, renderedSvg: SVGSVGElement | null = null) {
  const root = exportSvgRoot(svgText, renderedSvg);
  if (!root || root.localName !== "svg") throw new Error("SVG 源码无效，无法导出 PNG。");
  prepareSvgForPngExport(root, renderedSvg);
  absolutizeSvgLinks(root);
  await inlineSvgRasterImages(root, caseId);
  const size = svgRootSize(root);
  root.setAttribute("width", String(size.width));
  root.setAttribute("height", String(size.height));
  paintSvgExportBackground(root, size);
  const blobUrl = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(root)], { type: "image/svg+xml;charset=utf-8" }));
  let image: HTMLImageElement;
  try {
    image = await loadImage(blobUrl);
  } finally {
    URL.revokeObjectURL(blobUrl);
  }
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.ceil(size.width));
  canvas.height = Math.max(1, Math.ceil(size.height));
  const context = canvas.getContext("2d");
  if (!context) throw new Error("浏览器画布不可用。");
  context.drawImage(image, 0, 0, canvas.width, canvas.height);
  const link = document.createElement("a");
  link.href = canvas.toDataURL("image/png");
  link.download = filename;
  link.click();
}

function exportSvgRoot(svgText: string, renderedSvg: SVGSVGElement | null): Element {
  if (renderedSvg) {
    return renderedSvg.cloneNode(true) as Element;
  }
  const doc = new DOMParser().parseFromString(svgText, "image/svg+xml");
  return doc.documentElement;
}

function prepareSvgForPngExport(root: Element, renderedSvg: SVGSVGElement | null) {
  root.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  if (root.querySelector("[xlink\\:href]")) {
    root.setAttribute("xmlns:xlink", "http://www.w3.org/1999/xlink");
  }
  if (renderedSvg) {
    const computed = window.getComputedStyle(renderedSvg);
    if (computed.fontFamily && !root.getAttribute("font-family")) root.setAttribute("font-family", computed.fontFamily);
    if (computed.color && !root.getAttribute("color")) root.setAttribute("color", computed.color);
    inlineRenderedSvgTextStyles(root, renderedSvg);
  }
  stripEditorSvgAttributes(root);
}

function stripEditorSvgAttributes(root: Element) {
  for (const element of [root, ...Array.from(root.querySelectorAll("*"))]) {
    for (const attribute of Array.from(element.attributes)) {
      if (attribute.name.startsWith("data-drawai-")) element.removeAttribute(attribute.name);
    }
  }
}

function inlineRenderedSvgTextStyles(root: Element, renderedSvg: SVGSVGElement) {
  const clonedElements = Array.from(root.querySelectorAll("*"));
  const renderedElements = Array.from(renderedSvg.querySelectorAll("*"));
  for (const [index, cloned] of clonedElements.entries()) {
    const rendered = renderedElements[index];
    if (!(rendered instanceof Element) || !isSvgTextLikeElement(cloned)) continue;
    const computed = window.getComputedStyle(rendered);
    applyComputedSvgTextStyle(cloned, computed);
  }
}

function isSvgTextLikeElement(element: Element): boolean {
  const localName = element.localName.toLowerCase();
  return localName === "text" || localName === "tspan" || localName === "textpath";
}

function applyComputedSvgTextStyle(element: Element, computed: CSSStyleDeclaration) {
  const properties = [
    "font-family",
    "font-size",
    "font-weight",
    "font-style",
    "font-stretch",
    "font-variant",
    "letter-spacing",
    "word-spacing",
    "text-anchor",
    "dominant-baseline",
    "baseline-shift",
    "alignment-baseline",
    "direction",
    "unicode-bidi",
    "white-space",
    "fill",
    "fill-opacity",
    "stroke",
    "stroke-width",
    "stroke-opacity",
    "opacity",
    "paint-order"
  ];
  for (const property of properties) {
    const value = computed.getPropertyValue(property).trim();
    if (!shouldInlineComputedSvgStyle(property, value)) continue;
    element.setAttribute(property, value);
  }
}

function shouldInlineComputedSvgStyle(property: string, value: string): boolean {
  if (!value) return false;
  if (value === "normal" && property !== "font-style" && property !== "font-weight") return false;
  if (value === "none" && property !== "stroke") return false;
  if (value === "auto") return false;
  return true;
}

async function inlineSvgRasterImages(root: Element, caseId: string) {
  const cache = new Map<string, Promise<string>>();
  const rewrites: Promise<void>[] = [];
  const imageElements = Array.from(root.querySelectorAll("*")).filter((element) => {
    const localName = element.localName.toLowerCase();
    return localName === "image" || localName === "feimage";
  });
  for (const element of imageElements) {
    for (const attributeName of ["href", "xlink:href"]) {
      const value = element.getAttribute(attributeName);
      if (!value || !shouldInlineSvgImageHref(value)) continue;
      const url = resolveSvgImageHrefForExport(value, caseId);
      const key = url.href;
      let dataUrl = cache.get(key);
      if (!dataUrl) {
        dataUrl = fetchImageAsDataUrl(url);
        cache.set(key, dataUrl);
      }
      rewrites.push(dataUrl.then((resolved) => element.setAttribute(attributeName, resolved)));
    }
  }
  await Promise.all(rewrites);
}

function shouldInlineSvgImageHref(value: string): boolean {
  const trimmed = value.trim();
  return Boolean(trimmed) && !trimmed.startsWith("#") && !trimmed.toLowerCase().startsWith("data:");
}

function resolveSvgImageHrefForExport(value: string, caseId: string): URL {
  if (shouldRewriteSvgHref(value)) {
    return new URL(`/api/cases/${caseId}/files/${encodeSvgPath(resolveSvgHrefRelativeToSvgDir(value))}`, window.location.origin);
  }
  return new URL(value, window.location.href);
}

async function fetchImageAsDataUrl(url: URL): Promise<string> {
  const response = await fetch(url.href);
  if (!response.ok) {
    throw new Error(`PNG 导出时无法加载 SVG 图片素材：${url.pathname} (${response.status})`);
  }
  return blobToDataUrl(await response.blob());
}

function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        resolve(reader.result);
      } else {
        reject(new Error("PNG 导出时无法编码 SVG 图片素材。"));
      }
    };
    reader.onerror = () => reject(new Error("PNG 导出时无法读取 SVG 图片素材。"));
    reader.readAsDataURL(blob);
  });
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("PNG 导出前无法渲染 SVG。"));
    image.src = src;
  });
}

function absolutizeSvgLinks(root: Element) {
  for (const element of Array.from(root.querySelectorAll("*"))) {
    for (const attributeName of ["href", "xlink:href"]) {
      const value = element.getAttribute(attributeName);
      if (value?.startsWith("/")) {
        element.setAttribute(attributeName, `${window.location.origin}${value}`);
      }
    }
  }
}

function paintSvgExportBackground(root: Element, size: { width: number; height: number }) {
  const doc = root.ownerDocument;
  const background = doc.createElementNS("http://www.w3.org/2000/svg", "rect");
  const viewBox = parseSvgViewBox(root.getAttribute("viewBox") || "");
  background.setAttribute("x", String(viewBox?.x || 0));
  background.setAttribute("y", String(viewBox?.y || 0));
  background.setAttribute("width", String(viewBox?.width || size.width));
  background.setAttribute("height", String(viewBox?.height || size.height));
  background.setAttribute("fill", "#ffffff");
  background.setAttribute("data-drawai-export-background", "true");
  let before = root.firstChild;
  while (before instanceof Element && ["title", "desc", "defs"].includes(before.localName)) {
    before = before.nextSibling;
  }
  root.insertBefore(background, before);
}

function svgRootSize(root: Element): { width: number; height: number } {
  const viewBox = parseSvgViewBox(root.getAttribute("viewBox") || "");
  const width = svgLengthNumber(root.getAttribute("width")) || viewBox?.width || 1200;
  const height = svgLengthNumber(root.getAttribute("height")) || viewBox?.height || 800;
  return { width, height };
}

function svgLengthNumber(value: string | null): number {
  const trimmed = value?.trim();
  if (!trimmed) return 0;
  const match = trimmed.match(/^([+-]?(?:\d+\.?\d*|\.\d+))(px|in|cm|mm|pt|pc)?$/i);
  if (!match) return 0;
  const numeric = Number.parseFloat(match[1]);
  if (!Number.isFinite(numeric) || numeric <= 0) return 0;
  const unit = (match[2] || "px").toLowerCase();
  const unitScale: Record<string, number> = {
    px: 1,
    in: 96,
    cm: 96 / 2.54,
    mm: 96 / 25.4,
    pt: 96 / 72,
    pc: 16
  };
  return numeric * unitScale[unit];
}

function formatSvgNumber(value: number): string {
  return String(Number(value.toFixed(2)));
}

function truncateInline(value: string, limit: number): string {
  return value.length <= limit ? value : `${value.slice(0, limit - 1)}…`;
}

function latestArtifact(artifacts: ArtifactRecord[], label: string): ArtifactRecord | undefined {
  return artifacts.slice().reverse().find((artifact) => artifact.label === label);
}

function downloadArtifact(artifact: ArtifactRecord) {
  const link = document.createElement("a");
  link.href = artifact.url;
  link.download = "";
  document.body.appendChild(link);
  link.click();
  link.remove();
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

function safeDownloadStem(value: string): string {
  return value.replace(/[^A-Za-z0-9_.-]+/g, "_").replace(/^[._]+|[._]+$/g, "") || "drawai_batch";
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function exportStageRunCount(detail: CaseDetail): number {
  return detail.stage_runs.filter((stage) => stage.stage_name === "export").length;
}

function hasNewFailedExportRun(detail: CaseDetail, previousExportRunCount: number): boolean {
  const exportRuns = detail.stage_runs.filter((stage) => stage.stage_name === "export");
  return exportRuns.length > previousExportRunCount && exportRuns[exportRuns.length - 1]?.status === "failed";
}

function caseHasSemanticSvg(detail: CaseDetail | null): boolean {
  return Boolean(detail && latestArtifact(detail.artifacts, "semantic_svg"));
}

function caseCanOpenCanvas(detail: CaseDetail | null, progress: CaseProgress | null): boolean {
  return Boolean(detail && detail.case.status === "completed" && caseHasSemanticSvg(detail) && !isCaseActivelyRunning(detail, progress));
}

function isCaseActivelyRunning(detail: CaseDetail | null, progress: CaseProgress | null): boolean {
  const status = progress?.case.status || detail?.case.status || "";
  return status === "queued" || status === "analysis_running" || status === "svg_running" || (progress?.stage_runs || detail?.stage_runs || []).some((stage) => stage.status === "running");
}

function retryStageForCase(item: Pick<CaseRecord, "phase" | "stage" | "stale_from_stage">): WorkbenchRerunStage {
  const stage = (item.stale_from_stage || item.stage || item.phase || "").toLowerCase();
  const canonical = canonicalPipelineStage(stage);
  if (canonical) return canonical;
  return "analysis";
}

function latestProgressFile(progress: CaseProgress | null, label: string) {
  return progress?.files.find((file) => file.label === label && file.exists);
}

function latestStageRun(stageRuns: StageRunRecord[], predicate: (stage: StageRunRecord) => boolean = () => true): StageRunRecord | null {
  return stageRuns.slice().reverse().find(predicate) || null;
}

function isEditorSourceStrategy(strategy: SourceStrategy): strategy is EditorSourceStrategy {
  return (EDITOR_SOURCE_STRATEGIES as readonly SourceStrategy[]).includes(strategy);
}

function durationText(startedAt: string, endedAt: string): string {
  const start = Date.parse(startedAt);
  if (!Number.isFinite(start)) return "-";
  const end = endedAt ? Date.parse(endedAt) : Date.now();
  if (!Number.isFinite(end)) return "-";
  const seconds = Math.max(0, Math.round((end - start) / 1000));
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  if (minutes < 60) return `${minutes}m ${rest}s`;
  const hours = Math.floor(minutes / 60);
  const minuteRest = minutes % 60;
  return `${hours}h ${minuteRest}m`;
}

function cloneAssetPlan(plan: AssetPlan): AssetPlan {
  return {
    ...plan,
    elements: plan.elements.map((element) => ({
      ...element,
      bbox: [...element.bbox],
      geometry: cloneAssetGeometry(element.geometry),
      source_candidate_ids: [...element.source_candidate_ids],
      evidence: [...element.evidence]
    })),
    categories: plan.categories ? { ...plan.categories } : undefined
  };
}

function cloneAssetGeometry(geometry: AssetGeometry | undefined): AssetGeometry | undefined {
  if (!geometry) return undefined;
  if (geometry.kind === "polygon") {
    return {
      ...geometry,
      bbox: geometry.bbox ? [...geometry.bbox] : undefined,
      points: geometry.points.map((point) => [point[0], point[1]])
    };
  }
  if (geometry.kind === "mask") {
    return { ...geometry, bbox: [...geometry.bbox] };
  }
  return { ...geometry, bbox: [...geometry.bbox] };
}

function transformGeometryForBBox(
  geometry: AssetGeometry | undefined,
  fromBBox: [number, number, number, number],
  toBBox: [number, number, number, number]
): AssetGeometry | undefined {
  if (!geometry) return undefined;
  if (geometry.kind === "polygon") {
    const fromWidth = Math.max(1e-6, fromBBox[2] - fromBBox[0]);
    const fromHeight = Math.max(1e-6, fromBBox[3] - fromBBox[1]);
    const toWidth = toBBox[2] - toBBox[0];
    const toHeight = toBBox[3] - toBBox[1];
    return {
      ...geometry,
      bbox: [...toBBox],
      points: geometry.points.map((point) => [
        toBBox[0] + ((point[0] - fromBBox[0]) / fromWidth) * toWidth,
        toBBox[1] + ((point[1] - fromBBox[1]) / fromHeight) * toHeight
      ])
    };
  }
  if (geometry.kind === "mask") {
    return { ...geometry, bbox: [...toBBox] };
  }
  return { ...geometry, bbox: [...toBBox] };
}

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  if (target.isContentEditable) return true;
  return ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}

function bboxStyle(bbox: [number, number, number, number], size: { width: number; height: number }) {
  const [x1, y1, x2, y2] = bbox;
  return {
    left: `${(x1 / size.width) * 100}%`,
    top: `${(y1 / size.height) * 100}%`,
    width: `${((x2 - x1) / size.width) * 100}%`,
    height: `${((y2 - y1) / size.height) * 100}%`
  };
}

function v2BBoxStyle(bbox: [number, number, number, number], size: { width: number; height: number }) {
  const [left, top, width, height] = bbox;
  return {
    left: `${(left / size.width) * 100}%`,
    top: `${(top / size.height) * 100}%`,
    width: `${(width / size.width) * 100}%`,
    height: `${(height / size.height) * 100}%`
  };
}

function bboxArea(bbox: [number, number, number, number]) {
  return Math.max(0, bbox[2] - bbox[0]) * Math.max(0, bbox[3] - bbox[1]);
}

function v2BBoxArea(bbox: [number, number, number, number]) {
  return Math.max(0, bbox[2]) * Math.max(0, bbox[3]);
}

function bboxText(bbox: [number, number, number, number]): string {
  return bbox.map((value) => Math.round(value)).join(", ");
}

function assetCropPreviewStyle(element: AssetElement, figureUrl: string, size: { width: number; height: number }) {
  if (!figureUrl || size.width <= 1 || size.height <= 1) return {};
  const [x1, y1, x2, y2] = normalizeBBox(element.bbox);
  const width = Math.max(1, x2 - x1);
  const height = Math.max(1, y2 - y1);
  const positionX = size.width === width ? 0 : (x1 / Math.max(1, size.width - width)) * 100;
  const positionY = size.height === height ? 0 : (y1 / Math.max(1, size.height - height)) * 100;
  return {
    backgroundImage: `url("${figureUrl}")`,
    backgroundSize: `${(size.width / width) * 100}% ${(size.height / height) * 100}%`,
    backgroundPosition: `${positionX}% ${positionY}%`
  };
}

function updateAssetReason(current: string, addition: string): string {
  const trimmed = current.trim();
  if (!trimmed) return addition;
  if (trimmed.includes(addition)) return trimmed;
  return `${trimmed} ${addition}`;
}

function clearWorkbenchProcessingReasons(
  current: string,
  options: { clearApplied?: boolean; clearMode?: boolean } = {}
): string {
  let next = current;
  if (options.clearApplied) {
    next = next.replace(/(?:Workbench processing applied as|工作台处理结果为) (保留背景|去背景)\./g, "");
  }
  if (options.clearMode) {
    next = next.replace(/(?:Workbench processing mode set to|工作台处理模式设为) (保留背景|去背景)\./g, "");
  }
  return next.replace(/\s+/g, " ").trim();
}

function assetProcessingResultText(element: AssetElement): string {
  const label = isEditorSourceStrategy(element.source_strategy) ? strategyLabels[element.source_strategy] : "未处理";
  const geometry = geometryLabel(element);
  const matchesCurrentMode = element.processed_asset_source_strategy === element.source_strategy;
  const processed = element.processing_status === "processed" && matchesCurrentMode && Boolean(element.processed_asset_relative_path);
  const legacyProcessed = element.reason.includes(WORKBENCH_PROCESSING_APPLIED_REASON);
  if (processed || legacyProcessed) {
    const elapsed = element.source_strategy === "crop_nobg" && typeof element.rmbg_elapsed_ms === "number"
      ? ` · ${Math.round(element.rmbg_elapsed_ms)}ms`
      : "";
    return `已处理 · ${label}${geometry ? ` · ${geometry}` : ""}${elapsed}`;
  }
  return `待处理 · ${label}${geometry ? ` · ${geometry}` : ""}`;
}

function assetProcessedUrl(element: AssetElement, caseId: string): string {
  if (!caseId || !element.processed_asset_relative_path || element.processed_asset_source_strategy !== element.source_strategy) return "";
  return caseFileUrl(caseId, element.processed_asset_relative_path, element.processed_asset_updated_at);
}

function assetGeometryPreviewUrl(element: AssetElement, caseId: string): string {
  const relativePath = element.geometry_preview_relative_path || element.mask_preview || "";
  if (!caseId || !relativePath) return "";
  return caseFileUrl(caseId, relativePath);
}

function caseFileUrl(caseId: string, relativePath: string, cacheKey = ""): string {
  if (!caseId || !relativePath) return "";
  const encoded = relativePath.split("/").map(encodeURIComponent).join("/");
  const suffix = cacheKey ? `?t=${encodeURIComponent(cacheKey)}` : "";
  return `/api/cases/${caseId}/files/${encoded}${suffix}`;
}

function geometryKind(element: AssetElement): string {
  return String(element.geometry?.kind || element.geometry_kind || "").toLowerCase();
}

function geometryLabel(element: AssetElement): string {
  const kind = geometryKind(element);
  if (kind === "mask") return "MASK";
  if (kind === "polygon") return "POLY";
  return "";
}

function geometryClass(element: AssetElement): string {
  const kind = geometryKind(element);
  if (kind === "mask") return "geometry-mask";
  if (kind === "polygon") return "geometry-polygon";
  return "";
}

function isAlphaGeometry(element: AssetElement): boolean {
  return ["mask", "polygon"].includes(geometryKind(element));
}

async function buildUploadConfirmation(files: SelectedUploadFile[]): Promise<UploadConfirmation> {
  const images: UploadPreviewImage[] = [];
  const zipErrors: string[] = [];
  for (const item of files) {
    const source = cleanBrowserEntryPath(item.relativePath || item.file.name);
    if (isZipUpload(item.file)) {
      try {
        const names = await listZipImageNames(item.file);
        if (names.length === 0) {
          zipErrors.push(`${source} 中没有支持的图片。`);
        }
        images.push(...names.map((name) => ({ name, source, kind: "zip" as const })));
      } catch (err) {
        zipErrors.push(`${source} 无法解析：${err instanceof Error ? err.message : String(err)}`);
      }
      continue;
    }
    if (isSupportedImageUpload(item.file)) {
      images.push({ name: source, source, kind: "image" });
    }
  }
  return {
    files,
    images,
    zipErrors,
    title: uploadBatchTitleFromFiles(files)
  };
}

function selectedUploadFilesFromFileList(files: FileList | null): SelectedUploadFile[] {
  return Array.from(files || []).map((file) => ({
    file,
    relativePath: uploadRelativePath(file)
  }));
}

async function selectedUploadFilesFromDrop(event: DragEvent<HTMLElement>): Promise<SelectedUploadFile[]> {
  const items = Array.from(event.dataTransfer.items || []) as BrowserDataTransferItem[];
  if (items.length === 0) return selectedUploadFilesFromFileList(event.dataTransfer.files);
  const collected: SelectedUploadFile[] = [];
  for (const item of items) {
    if (item.kind !== "file") continue;
    const entry = item.webkitGetAsEntry?.();
    if (entry) {
      collected.push(...await selectedUploadFilesFromEntry(entry));
      continue;
    }
    const file = item.getAsFile();
    if (file) collected.push({ file, relativePath: uploadRelativePath(file) });
  }
  return collected;
}

async function selectedUploadFilesFromEntry(entry: BrowserFileSystemEntry): Promise<SelectedUploadFile[]> {
  if (entry.isFile) {
    const file = await fileFromEntry(entry as BrowserFileSystemFileEntry);
    return [{ file, relativePath: cleanBrowserEntryPath(entry.fullPath || file.name) }];
  }
  if (!entry.isDirectory) return [];
  const children = await entriesFromDirectory(entry as BrowserFileSystemDirectoryEntry);
  const nested: SelectedUploadFile[] = [];
  for (const child of children) {
    nested.push(...await selectedUploadFilesFromEntry(child));
  }
  return nested;
}

function fileFromEntry(entry: BrowserFileSystemFileEntry): Promise<File> {
  return new Promise((resolve, reject) => entry.file(resolve, reject));
}

async function entriesFromDirectory(entry: BrowserFileSystemDirectoryEntry): Promise<BrowserFileSystemEntry[]> {
  const reader = entry.createReader();
  const entries: BrowserFileSystemEntry[] = [];
  while (true) {
    const batch = await new Promise<BrowserFileSystemEntry[]>((resolve, reject) => reader.readEntries(resolve, reject));
    if (batch.length === 0) break;
    entries.push(...batch);
  }
  return entries;
}

function uploadBatchTitleFromFiles(files: SelectedUploadFile[]): string {
  const paths = files.map((item) => cleanBrowserEntryPath(item.relativePath || item.file.name)).filter(Boolean);
  if (paths.length === 0) return "DrawAI 任务";
  const segments = paths.map((path) => path.split("/").filter(Boolean));
  const roots = new Set(segments.map((parts) => parts[0]).filter(Boolean));
  if (paths.length > 1 && roots.size === 1 && segments.some((parts) => parts.length > 1)) {
    return [...roots][0];
  }
  const firstParts = segments[0] || [];
  return firstParts[firstParts.length - 1] || paths[0];
}

function uploadRelativePath(file: File): string {
  return cleanBrowserEntryPath((file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name);
}

function cleanBrowserEntryPath(value: string): string {
  return value.replace(/\\/g, "/").replace(/^\/+/, "") || "upload.png";
}

function isSupportedUpload(file: File): boolean {
  return isSupportedImageUpload(file) || isZipUpload(file);
}

function isSupportedImageUpload(file: File): boolean {
  const lower = file.name.toLowerCase();
  return SUPPORTED_UPLOAD_EXTENSIONS.some((extension) => extension !== ".zip" && lower.endsWith(extension));
}

function isZipUpload(file: File): boolean {
  const lower = file.name.toLowerCase();
  return lower.endsWith(".zip") || file.type === "application/zip" || file.type === "application/x-zip-compressed";
}

async function listZipImageNames(file: File): Promise<string[]> {
  const buffer = await file.arrayBuffer();
  if (buffer.byteLength < 22) throw new Error("不是有效 ZIP 文件");
  const view = new DataView(buffer);
  const eocdOffset = findZipEndOfCentralDirectory(view);
  if (eocdOffset < 0) throw new Error("没有找到 ZIP 目录");
  const entryCount = view.getUint16(eocdOffset + 10, true);
  const centralDirectorySize = view.getUint32(eocdOffset + 12, true);
  const centralDirectoryOffset = view.getUint32(eocdOffset + 16, true);
  if (centralDirectoryOffset <= 0 || centralDirectoryOffset >= buffer.byteLength) {
    throw new Error("ZIP 目录位置异常");
  }
  const names: string[] = [];
  let offset = centralDirectoryOffset;
  const end = Math.min(buffer.byteLength, centralDirectoryOffset + centralDirectorySize);
  for (let index = 0; index < entryCount && offset + 46 <= end; index += 1) {
    if (view.getUint32(offset, true) !== 0x02014b50) break;
    const flags = view.getUint16(offset + 8, true);
    const nameLength = view.getUint16(offset + 28, true);
    const extraLength = view.getUint16(offset + 30, true);
    const commentLength = view.getUint16(offset + 32, true);
    const nameStart = offset + 46;
    const nameEnd = nameStart + nameLength;
    if (nameEnd > buffer.byteLength) break;
    const nameBytes = new Uint8Array(buffer, nameStart, nameLength);
    const rawName = decodeZipFilename(nameBytes, Boolean(flags & 0x0800));
    const name = cleanBrowserEntryPath(rawName);
    if (name && isSupportedImagePath(name) && !isHiddenZipEntry(name)) names.push(name);
    offset = nameEnd + extraLength + commentLength;
  }
  return names;
}

function findZipEndOfCentralDirectory(view: DataView): number {
  const minOffset = Math.max(0, view.byteLength - 65_557);
  for (let offset = view.byteLength - 22; offset >= minOffset; offset -= 1) {
    if (view.getUint32(offset, true) === 0x06054b50) return offset;
  }
  return -1;
}

function decodeZipFilename(bytes: Uint8Array, utf8: boolean): string {
  let decoder: TextDecoder;
  try {
    decoder = new TextDecoder(utf8 ? "utf-8" : "gb18030", { fatal: false });
  } catch {
    decoder = new TextDecoder("utf-8", { fatal: false });
  }
  return decoder.decode(bytes);
}

function isSupportedImagePath(path: string): boolean {
  const lower = path.toLowerCase();
  return [".png", ".jpg", ".jpeg", ".webp"].some((extension) => lower.endsWith(extension));
}

function isHiddenZipEntry(path: string): boolean {
  return path.split("/").some((part) => part === "__MACOSX" || part.startsWith("._"));
}

function tooltipStyle(bbox: [number, number, number, number], size: { width: number; height: number }) {
  const [x1, y1, x2, y2] = bbox;
  const horizontal =
    x1 / size.width > 0.65
      ? { right: `${((size.width - x2) / size.width) * 100}%` }
      : { left: `${(x1 / size.width) * 100}%` };
  const vertical =
    y2 / size.height > 0.72
      ? { bottom: `${((size.height - y1) / size.height) * 100}%`, transform: "translateY(-8px)" }
      : { top: `${(y2 / size.height) * 100}%`, transform: "translateY(8px)" };
  return { ...horizontal, ...vertical };
}

function v2TooltipStyle(bbox: [number, number, number, number], size: { width: number; height: number }) {
  const [left, top, width, height] = bbox;
  const right = left + width;
  const bottom = top + height;
  const horizontal =
    left / size.width > 0.65
      ? { right: `${((size.width - right) / size.width) * 100}%` }
      : { left: `${(left / size.width) * 100}%` };
  const vertical =
    bottom / size.height > 0.72
      ? { bottom: `${((size.height - top) / size.height) * 100}%`, transform: "translateY(-8px)" }
      : { top: `${(bottom / size.height) * 100}%`, transform: "translateY(8px)" };
  return { ...horizontal, ...vertical };
}

function normalizeBBox(value: number[]): [number, number, number, number] {
  const left = Math.min(value[0], value[2]);
  const right = Math.max(value[0], value[2]);
  const top = Math.min(value[1], value[3]);
  const bottom = Math.max(value[1], value[3]);
  return [left, top, right, bottom];
}

function resizeBBox(bbox: [number, number, number, number], handle: string, dx: number, dy: number): [number, number, number, number] {
  const next = [...bbox] as [number, number, number, number];
  if (handle.includes("n")) next[1] += dy;
  if (handle.includes("s")) next[3] += dy;
  if (handle.includes("w")) next[0] += dx;
  if (handle.includes("e")) next[2] += dx;
  return normalizeBBox(next);
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function nextNewId(elements: AssetElement[]) {
  let index = 1;
  const existing = new Set(elements.map((item) => item.box_id));
  while (existing.has(`N${String(index).padStart(3, "0")}`)) index += 1;
  return `N${String(index).padStart(3, "0")}`;
}
