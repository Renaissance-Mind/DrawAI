import type {
  ArtifactRecord,
  ApiPresetsResponse,
  ApiPreset,
  AssetPlan,
  AssetProcessingResponse,
  BatchDetail,
  CaseRecord,
  CaseDetail,
  CaseProgress,
  HealthResponse,
  ImageEditRequest,
  ImageGenerationRequest,
  ImageGenerationResponse,
  ProcessorSettingsResponse,
  SlideTemplateCardsResponse,
  SlideTemplateGalleryResponse,
  SvgSourceResponse,
  V2AssetPackage,
  V2Compatibility,
  V2ElementPlan,
  V2RunPackage,
  WorkbenchAgentSettings,
  WorkbenchAgentSettingsResponse,
  WorkbenchStatusOverviewResponse,
  WorkflowNodeViewer
} from "./types";

const LOCAL_API_ORIGIN = "http://127.0.0.1:8890";

export type WorkbenchRerunStage =
  | "analysis"
  | "asset_analyze"
  | "materialize"
  | "svg"
  | "prepare"
  | "parse_elements"
  | "fuse_elements"
  | "refine_elements"
  | "plan_assets"
  | "process_assets"
  | "compose"
  | "compose_svg"
  | "export"
  | "package_run";

export class DrawAiApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "DrawAiApiError";
    this.status = status;
  }
}

export function isDrawAiApiStatus(error: unknown, status: number): boolean {
  return error instanceof DrawAiApiError && error.status === status;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    return await fetchJson<T>(path, init);
  } catch (error) {
    if (isNetworkError(error) && shouldRetryLocalApi(path)) {
      try {
        return await fetchJson<T>(`${localApiOrigin()}${path}`, init);
      } catch (fallbackError) {
        throw drawAiNetworkError(path, fallbackError);
      }
    }
    if (isNetworkError(error)) {
      throw drawAiNetworkError(path, error);
    }
    throw error;
  }
}

async function requestBlob(path: string, init?: RequestInit): Promise<Blob> {
  try {
    return await fetchBlob(path, init);
  } catch (error) {
    if (isNetworkError(error) && shouldRetryLocalApi(path)) {
      try {
        return await fetchBlob(`${localApiOrigin()}${path}`, init);
      } catch (fallbackError) {
        throw drawAiNetworkError(path, fallbackError);
      }
    }
    if (isNetworkError(error)) {
      throw drawAiNetworkError(path, error);
    }
    throw error;
  }
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init
  });
  if (!response.ok) {
    throw new DrawAiApiError(response.status, await responseErrorMessage(response));
  }
  return (await response.json()) as T;
}

async function fetchBlob(path: string, init?: RequestInit): Promise<Blob> {
  const response = await fetch(path, init);
  if (!response.ok) {
    throw new DrawAiApiError(response.status, await responseErrorMessage(response));
  }
  return response.blob();
}

async function responseErrorMessage(response: Response): Promise<string> {
  let message = `${response.status} ${response.statusText}`;
  const clone = response.clone();
  try {
    const payload = await clone.json();
    message = payload.detail || message;
  } catch {
    const text = await response.text();
    if (text) message = text;
  }
  return message;
}

function shouldRetryLocalApi(path: string): boolean {
  if (!path.startsWith("/api")) return false;
  if (typeof window === "undefined") return false;
  const { hostname, port } = window.location;
  return (hostname === "127.0.0.1" || hostname === "localhost") && port !== "";
}

function localApiOrigin(): string {
  const configured = (import.meta.env.VITE_DRAWAI_API_URL || "").trim().replace(/\/$/, "");
  return configured || LOCAL_API_ORIGIN;
}

function isNetworkError(error: unknown): boolean {
  return error instanceof TypeError && /fetch|network|load failed/i.test(error.message);
}

function drawAiNetworkError(path: string, error: unknown): Error {
  const detail = error instanceof Error ? error.message : String(error);
  return new Error(`无法连接 DrawAI 后端（${path}）：${detail}`);
}

export function getHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/api/health");
}

export function workbenchAgentSettingsPath(includeAgents = true, refreshAgents = false): string {
  const params = new URLSearchParams();
  if (!includeAgents) {
    params.set("include_agents", "false");
  } else if (refreshAgents) {
    params.set("refresh_agents", "true");
  }
  const query = params.toString();
  return `/api/workbench/agent-settings${query ? `?${query}` : ""}`;
}

export function getWorkbenchAgentSettings(includeAgents = true, refreshAgents = false): Promise<WorkbenchAgentSettingsResponse> {
  return requestJson<WorkbenchAgentSettingsResponse>(workbenchAgentSettingsPath(includeAgents, refreshAgents));
}

export function saveWorkbenchAgentSettings(
  settings: WorkbenchAgentSettings,
  includeAgents = true
): Promise<WorkbenchAgentSettingsResponse> {
  return requestJson<WorkbenchAgentSettingsResponse>(workbenchAgentSettingsPath(includeAgents), {
    method: "PUT",
    body: JSON.stringify(settings)
  });
}

export function getApiPresets(): Promise<ApiPresetsResponse> {
  return requestJson<ApiPresetsResponse>("/api/workbench/api-presets");
}

export function saveApiPresets(presets: ApiPreset[]): Promise<ApiPresetsResponse> {
  return requestJson<ApiPresetsResponse>("/api/workbench/api-presets", {
    method: "PUT",
    body: JSON.stringify({ presets })
  });
}

export function getProcessorSettings(): Promise<ProcessorSettingsResponse> {
  return requestJson<ProcessorSettingsResponse>("/api/workbench/processor-settings");
}

export function getWorkbenchStatusOverview(): Promise<WorkbenchStatusOverviewResponse> {
  return requestJson<WorkbenchStatusOverviewResponse>("/api/workbench/status-overview");
}

export function saveProcessorSettings(processors: ProcessorSettingsResponse["settings"]["processors"]): Promise<ProcessorSettingsResponse> {
  return requestJson<ProcessorSettingsResponse>("/api/workbench/processor-settings", {
    method: "PUT",
    body: JSON.stringify({ processors })
  });
}

export function listBatches(): Promise<{ batches: BatchDetail["batch"][] }> {
  return requestJson<{ batches: BatchDetail["batch"][] }>("/api/batches");
}

export function createUploadBatch(form: FormData): Promise<BatchDetail> {
  return requestJson<BatchDetail>("/api/batches", {
    method: "POST",
    body: form
  });
}

export function getBatch(batchId: string): Promise<BatchDetail> {
  return requestJson<BatchDetail>(`/api/batches/${batchId}`);
}

export function downloadBatchPptx(batchId: string): Promise<Blob> {
  return requestBlob(`/api/batches/${batchId}/pptx`);
}

export function renameBatch(batchId: string, name: string): Promise<BatchDetail> {
  return requestJson<BatchDetail>(`/api/batches/${batchId}`, {
    method: "PATCH",
    body: JSON.stringify({ name })
  });
}

export function deleteBatch(batchId: string): Promise<{ batch_id: string }> {
  return requestJson<{ batch_id: string }>(`/api/batches/${batchId}`, {
    method: "DELETE"
  });
}

export function runBatch(batchId: string): Promise<BatchDetail> {
  return requestJson<BatchDetail>(`/api/batches/${batchId}/run`, {
    method: "POST"
  });
}

export function runCaseStage(caseId: string, stage: WorkbenchRerunStage): Promise<{ case: CaseDetail["case"] }> {
  return requestJson<{ case: CaseDetail["case"] }>(`/api/cases/${caseId}/run-stage`, {
    method: "POST",
    body: JSON.stringify({ stage })
  });
}

export function setWorkflowBreakpoint(caseId: string, nodeId: string): Promise<{ case: CaseDetail["case"] }> {
  return requestJson<{ case: CaseDetail["case"] }>(`/api/cases/${caseId}/workflow/breakpoint`, {
    method: "POST",
    body: JSON.stringify({ node_id: nodeId })
  });
}

export function clearWorkflowBreakpoint(caseId: string): Promise<{ case: CaseDetail["case"] }> {
  return requestJson<{ case: CaseDetail["case"] }>(`/api/cases/${caseId}/workflow/breakpoint`, {
    method: "DELETE"
  });
}

export function continueWorkflowCase(caseId: string): Promise<{ case: CaseDetail["case"] }> {
  return requestJson<{ case: CaseDetail["case"] }>(`/api/cases/${caseId}/workflow/continue`, {
    method: "POST"
  });
}

export function cancelCase(caseId: string): Promise<{ case: CaseDetail["case"] }> {
  return requestJson<{ case: CaseDetail["case"] }>(`/api/cases/${caseId}/cancel`, {
    method: "POST"
  });
}

export function getCase(caseId: string): Promise<CaseDetail> {
  return requestJson<CaseDetail>(`/api/cases/${caseId}`);
}

export function getCaseArtifacts(caseId: string): Promise<{ artifacts: ArtifactRecord[] }> {
  return requestJson<{ artifacts: ArtifactRecord[] }>(`/api/cases/${caseId}/artifacts`);
}

export function getCaseProgress(caseId: string): Promise<CaseProgress> {
  return requestJson<CaseProgress>(`/api/cases/${caseId}/progress`);
}

export function getAssets(caseId: string): Promise<{ asset_plan: AssetPlan }> {
  return requestJson<{ asset_plan: AssetPlan }>(`/api/cases/${caseId}/assets`);
}

export function getRunPackage(caseId: string): Promise<{ compatibility: V2Compatibility; package: V2RunPackage }> {
  return requestJson<{ compatibility: V2Compatibility; package: V2RunPackage }>(`/api/cases/${caseId}/package`);
}

export function getElements(caseId: string): Promise<{ compatibility: V2Compatibility; elements: V2ElementPlan[] }> {
  return requestJson<{ compatibility: V2Compatibility; elements: V2ElementPlan[] }>(`/api/cases/${caseId}/elements`);
}

export function getAssetPackage(caseId: string, elementId: string): Promise<{ compatibility: V2Compatibility; asset_package: V2AssetPackage }> {
  return requestJson<{ compatibility: V2Compatibility; asset_package: V2AssetPackage }>(
    `/api/cases/${caseId}/elements/${encodeURIComponent(elementId)}/asset-package`
  );
}

export function getWorkflowNodeViewer(caseId: string, nodeId: string): Promise<WorkflowNodeViewer> {
  return requestJson<WorkflowNodeViewer>(`/api/cases/${caseId}/workflow/nodes/${encodeURIComponent(nodeId)}/viewer`);
}

export function processV2Asset(
  caseId: string,
  elementId: string,
  processor: string,
  payload: Record<string, unknown> = {}
): Promise<{ asset_package: V2AssetPackage; case: CaseRecord }> {
  return requestJson<{ asset_package: V2AssetPackage; case: CaseRecord }>(
    `/api/cases/${caseId}/elements/${encodeURIComponent(elementId)}/process`,
    {
      method: "POST",
      body: JSON.stringify({ ...payload, processor })
    }
  );
}

export function setActiveAssetResult(
  caseId: string,
  elementId: string,
  resultId: string
): Promise<{ asset_package: V2AssetPackage; case: CaseRecord }> {
  return requestJson<{ asset_package: V2AssetPackage; case: CaseRecord }>(
    `/api/cases/${caseId}/elements/${encodeURIComponent(elementId)}/active-result`,
    {
      method: "POST",
      body: JSON.stringify({ result_id: resultId })
    }
  );
}

export function composeV2Case(caseId: string): Promise<{ case: CaseRecord }> {
  return requestJson<{ case: CaseRecord }>(`/api/cases/${caseId}/compose`, {
    method: "POST"
  });
}

export function exportV2Case(caseId: string): Promise<{ case: CaseRecord }> {
  return requestJson<{ case: CaseRecord }>(`/api/cases/${caseId}/export`, {
    method: "POST"
  });
}

export function forkV2FromSource(caseId: string): Promise<{ case: CaseRecord }> {
  return requestJson<{ case: CaseRecord }>(`/api/cases/${caseId}/fork-v2-from-source`, {
    method: "POST"
  });
}

export function getSvgSource(caseId: string): Promise<SvgSourceResponse> {
  return requestJson<SvgSourceResponse>(`/api/cases/${caseId}/svg-source`);
}

export function saveSvgSource(caseId: string, svg: string): Promise<SvgSourceResponse> {
  return requestJson<SvgSourceResponse>(`/api/cases/${caseId}/svg-source`, {
    method: "PATCH",
    body: JSON.stringify({ svg })
  });
}

export function saveAssetDraft(caseId: string, assetPlan: AssetPlan): Promise<{ asset_plan: AssetPlan }> {
  return requestJson<{ asset_plan: AssetPlan }>(`/api/cases/${caseId}/asset-draft`, {
    method: "PATCH",
    body: JSON.stringify(assetPlan)
  });
}

export function processAssetElements(caseId: string, assetPlan: AssetPlan, assetIds: string[]): Promise<AssetProcessingResponse> {
  return requestJson<AssetProcessingResponse>(`/api/cases/${caseId}/asset-processing`, {
    method: "POST",
    body: JSON.stringify({ asset_plan: assetPlan, asset_ids: assetIds })
  });
}

export function approveAssets(caseId: string, runSvg: boolean): Promise<{ asset_plan: AssetPlan; case: CaseRecord }> {
  return requestJson<{ asset_plan: AssetPlan; case: CaseRecord }>(`/api/cases/${caseId}/approve-assets`, {
    method: "POST",
    body: JSON.stringify({ run_svg: runSvg })
  });
}

export function generateImages(payload: ImageGenerationRequest): Promise<ImageGenerationResponse> {
  return requestJson<ImageGenerationResponse>("/api/imagegen/generations", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function editImage(payload: ImageEditRequest): Promise<ImageGenerationResponse> {
  return requestJson<ImageGenerationResponse>("/api/imagegen/edits", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function listSlideTemplateCards(): Promise<SlideTemplateCardsResponse> {
  return requestJson<SlideTemplateCardsResponse>("/api/slide-template-cards");
}

export function listSlideTemplateGallery(): Promise<SlideTemplateGalleryResponse> {
  return requestJson<SlideTemplateGalleryResponse>("/api/slide-template-gallery");
}
