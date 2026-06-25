export type ImageGenerationTaskStatus = "running" | "completed" | "failed";
export type ImageGenSelectionMode = "off" | "selecting";

export interface ImageGenerationTaskImage {
  id: string;
  taskId: string;
  status: "completed";
  url: string;
  size: string;
  resolution: string;
  quality: string;
  format: string;
  transparent: boolean;
  provider: string;
  prompt: string;
}

export interface ImageGenerationTask {
  id: string;
  status: ImageGenerationTaskStatus;
  title: string;
  prompt: string;
  expectedCount: number;
  images: ImageGenerationTaskImage[];
  error: string;
  createdAt: string;
}

export type ImageGenTile =
  | (ImageGenerationTaskImage & { taskStatus: ImageGenerationTaskStatus; placeholderIndex?: never; error?: never })
  | {
      id: string;
      taskId: string;
      taskStatus: ImageGenerationTaskStatus;
      status: "running" | "failed";
      placeholderIndex: number;
      error: string;
      url: "";
      prompt: string;
      size: "";
      resolution: "";
      quality: "";
      format: "";
      transparent: false;
      provider: "";
    };

export interface ImageGenPanelActions {
  submitImageIds: string[];
  canSubmit: boolean;
  canRegenerate: boolean;
  selectIcon: "select" | "x";
  submitCount: number;
  hasRunningTasks: boolean;
}

export function imageGenVisibleTiles(tasks: ImageGenerationTask[]): ImageGenTile[] {
  return tasks.flatMap((task) => {
    if (task.images.length > 0) {
      return task.images.map((image) => ({ ...image, taskStatus: task.status }));
    }
    if (task.status === "running") {
      return Array.from({ length: Math.max(1, task.expectedCount) }, (_, index) => placeholderTile(task, "running", index));
    }
    if (task.status === "failed") {
      return [placeholderTile(task, "failed", 0)];
    }
    return [];
  });
}

export function imageGenPanelActions(
  tasks: ImageGenerationTask[],
  selectionMode: ImageGenSelectionMode,
  selectedImageIds: string[]
): ImageGenPanelActions {
  const completedIds = imageGenVisibleTiles(tasks)
    .filter((tile): tile is ImageGenerationTaskImage & { taskStatus: ImageGenerationTaskStatus } => tile.status === "completed")
    .map((tile) => tile.id);
  const completedIdSet = new Set(completedIds);
  const selectedCompletedIds = selectedImageIds.filter((id) => completedIdSet.has(id));
  const hasRunningTasks = tasks.some((task) => task.status === "running");
  const submitImageIds = selectionMode === "selecting" ? selectedCompletedIds : completedIds;

  return {
    submitImageIds,
    canSubmit: submitImageIds.length > 0 && !hasRunningTasks,
    canRegenerate: selectionMode === "selecting" && selectedCompletedIds.length > 0,
    selectIcon: selectionMode === "selecting" ? "x" : "select",
    submitCount: submitImageIds.length,
    hasRunningTasks
  };
}

function placeholderTile(task: ImageGenerationTask, status: "running" | "failed", index: number): ImageGenTile {
  return {
    id: `${task.id}:${status}:${index}`,
    taskId: task.id,
    taskStatus: task.status,
    status,
    placeholderIndex: index,
    error: status === "failed" ? task.error : "",
    url: "",
    prompt: task.prompt,
    size: "",
    resolution: "",
    quality: "",
    format: "",
    transparent: false,
    provider: ""
  };
}
