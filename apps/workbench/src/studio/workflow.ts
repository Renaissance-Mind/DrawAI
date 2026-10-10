import type { StudioAsset, StudioProject, StudioTask, TaskKind } from "./types";

const activeStates = new Set(["draft", "submitted", "running"]);

export function taskSlideIds(
  kind: TaskKind,
  project: StudioProject,
  chosen: string[],
  explicit?: string[],
): string[] {
  if (explicit !== undefined) return explicit;
  if (kind === "prepare_reference") return [];
  if (kind === "export_deck") return project.slides.map((page) => page.id);
  return chosen;
}

export function currentDeck(project: StudioProject): StudioAsset | undefined {
  return project.assets
    .slice()
    .reverse()
    .find((asset) => {
      if (asset.kind !== "pptx" || asset.slide_id) return false;
      const task = project.tasks.find((item) => item.id === asset.task_id);
      return Boolean(
        task?.kind === "export_deck" &&
          task.status === "completed" &&
          (task.project_input_revision || 1) ===
            (project.input_revision || 1) &&
          task.slide_ids.length === project.slides.length &&
          project.slides.every(
            (page, index) =>
              task.slide_ids[index] === page.id &&
              !page.content_changed &&
              page.current_image_id &&
              task.source_image_ids?.[page.id] === page.current_image_id &&
              task.slide_revisions?.[page.id] === page.revision,
          ),
      );
    });
}

export type PrimaryAction =
  | {
      kind: "generate" | "convert" | "export_deck";
      label: string;
      description: string;
      slideIds: string[];
      disabled: boolean;
    }
  | {
      kind: "download";
      label: string;
      description: string;
      asset: StudioAsset;
      disabled: false;
    }
  | {
      kind: "busy";
      label: string;
      description: string;
      task: StudioTask;
      disabled: false;
    };

export function primaryAction(
  project: StudioProject,
  activeId: string,
  selectedIds: string[],
  content: string,
  instruction: string,
  needsGeneration = false,
): PrimaryAction {
  const page = project.slides.find((item) => item.id === activeId);
  const selected = project.slides.filter((item) =>
    selectedIds.includes(item.id),
  );
  const targets = selected.length ? selected : page ? [page] : [];
  const task = project.tasks.find(
    (item) =>
      activeStates.has(item.status) &&
      item.slide_ids.some((id) => targets.some((target) => target.id === id)),
  );
  if (task)
    return {
      kind: "busy",
      label: task.status === "draft" ? "查看待发送请求" : "查看制作进度",
      description: task.message || "任务正在当前会话中执行。",
      task,
      disabled: false,
    };
  const hasDirection = Boolean(
    targets.some((target) =>
      (target.id === activeId ? content : target.content).trim(),
    ) ||
      instruction.trim() ||
      project.brief.trim() ||
      project.references.some((reference) => reference.role === "content"),
  );
  if (
    selected.length ||
    !page?.current_image_id ||
    page.content_changed ||
    needsGeneration
  )
    return {
      kind: "generate",
      label: selected.length
        ? `生成所选 ${selected.length} 页`
        : page?.content_changed || needsGeneration
          ? "更新当前页图片"
          : "生成当前页",
      description: hasDirection
        ? selected.length
          ? "根据每页内容和参考，生成所选页面的图片。"
          : "根据这页的内容和参考，生成 PPT 图片。"
        : "先填写这页的内容，或展开补充要求说明制作任务。",
      slideIds: targets.map((item) => item.id),
      disabled: !targets.length || !hasDirection,
    };
  const deck = currentDeck(project);
  if (deck)
    return {
      kind: "download",
      label: "下载整套 PPT",
      description: "整套可编辑 PPT 已完成。",
      asset: deck,
      disabled: false,
    };
  if (
    project.slides.length > 1 &&
    project.slides.every(
      (item) => item.current_image_id && !item.content_changed,
    )
  )
    return {
      kind: "export_deck",
      label: "制作整套可编辑 PPT",
      description: `${project.slides.length} 页图片已就绪，下一步制作可编辑的整套 PPT。`,
      slideIds: project.slides.map((item) => item.id),
      disabled: false,
    };
  const pptx = project.assets.find(
    (item) => item.id === page.current_pptx_id && item.kind === "pptx",
  );
  if (pptx)
    return {
      kind: "download",
      label: "下载当前页 PPTX",
      description: "当前页的可编辑 PPT 已完成。",
      asset: pptx,
      disabled: false,
    };
  return {
    kind: "convert",
    label: "转为可编辑 PPT",
    description: "图片满意后，将当前页转成可编辑的 PowerPoint。",
    slideIds: [page.id],
    disabled: false,
  };
}
