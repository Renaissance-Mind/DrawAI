import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import {
  connectStudio,
  fileBase64,
  type StudioRuntime,
  type DownloadReceipt,
} from "./runtime";
import type {
  StudioProject,
  StudioTask,
  StudioAsset,
  ProjectSummary,
  ToolResult,
  TaskKind,
  ReferenceRole,
  VisualTemplate,
} from "./types";
import { roleLabels, statusLabels, taskLabels, timeLabel } from "./labels";
import { Icon, Dialog, AssetImage, ActionMenu } from "./components";
import {
  currentDeck,
  primaryAction as resolvePrimaryAction,
  taskSlideIds,
} from "./workflow";
import TemplateLibrary from "./TemplateLibrary";
import DrawAiBrand from "../components/DrawAiBrand";
import "./studio.css";

type Tab = "project" | "templates" | "tasks";
const activeStates = ["draft", "submitted", "running"];

export default function StudioWorkspace() {
  const [runtime, setRuntime] = useState<StudioRuntime>();
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [project, setProject] = useState<StudioProject>();
  const currentProject = useRef<StudioProject | undefined>(undefined);
  const openSequence = useRef(0);
  const saveCurrentPage = useRef<() => Promise<void>>(async () => {});
  const [tab, setTab] = useState<Tab>("project");
  const [activeId, setActiveId] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [draft, setDraft] = useState({ title: "", content: "", notes: "" });
  const dirty = useRef(false);
  const draftRevision = useRef(1);
  const saving = useRef<Promise<void> | null>(null);
  const draftValue = useRef(draft);
  draftValue.current = draft;
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [downloadReceipt, setDownloadReceipt] = useState<DownloadReceipt>();
  const [pending, setPending] = useState("");
  const [newProjectOpen, setNewProjectOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [request, setRequest] = useState<StudioTask>();
  const [instruction, setInstruction] = useState("");
  const [generationDirty, setGenerationDirty] = useState(false);
  const [generationTaskId, setGenerationTaskId] = useState<string>();
  const [compare, setCompare] = useState(false);
  const [showVersions, setShowVersions] = useState(false);
  const [batchSelection, setBatchSelection] = useState(false);
  const [pagesOpen, setPagesOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editInstruction, setEditInstruction] = useState("");
  const [previewMode, setPreviewMode] = useState<"image" | "editable">("image");
  const [marking, setMarking] = useState(false);
  const [region, setRegion] = useState<{
    x: number;
    y: number;
    width: number;
    height: number;
  }>();
  const markStart = useRef<{ x: number; y: number } | undefined>(undefined);
  const uploadRef = useRef<HTMLInputElement>(null);
  const imageRef = useRef<HTMLInputElement>(null);
  const [uploadRole, setUploadRole] = useState<ReferenceRole>("content");
  const [deleteTarget, setDeleteTarget] = useState<"project" | "slide">();
  const page = project?.slides.find((s) => s.id === activeId);
  const images =
    project?.assets.filter(
      (a) => a.slide_id === activeId && a.kind === "image",
    ) || [];
  const currentImage = project?.assets.find(
    (a) => a.id === page?.current_image_id,
  );
  const pptx = project?.assets.find((a) => a.id === page?.current_pptx_id);
  const deck = project ? currentDeck(project) : undefined;
  const displayPptx = pptx || deck;
  const editablePreview = project?.assets
    .slice()
    .reverse()
    .find(
      (a) =>
        a.kind === "preview" &&
        a.slide_id === activeId &&
        a.task_id === displayPptx?.task_id,
    );
  const tasks = project?.tasks || [];
  const chosenPages = selected.length ? selected : activeId ? [activeId] : [];
  const activeTaskCount = tasks.filter((t) =>
    activeStates.includes(t.status),
  ).length;
  const nextAction = project
    ? resolvePrimaryAction(
        project,
        activeId,
        selected,
        dirty.current ? draft.content : page?.content || "",
        instruction,
        dirty.current || generationDirty,
      )
    : undefined;

  const accept = useCallback((data: ToolResult) => {
    if (data.project) {
      if (
        !currentProject.current ||
        currentProject.current.id !== data.project.id ||
        data.project.revision >= currentProject.current.revision
      )
        currentProject.current = data.project;
      setProject((old) =>
        !old ||
        old.id !== data.project!.id ||
        data.project!.revision >= old.revision
          ? data.project
          : old,
      );
      setRequest((current) =>
        current
          ? data.project!.tasks.find((task) => task.id === current.id) ||
            current
          : undefined,
      );
      setProjects((items) => {
        const p = data.project!;
        const summary = {
          id: p.id,
          title: p.title,
          updated_at: p.updated_at,
          slide_count: p.slides.length,
          task_count: p.tasks.filter((t) => activeStates.includes(t.status))
            .length,
        };
        return [summary, ...items.filter((item) => item.id !== p.id)];
      });
    }
    return data;
  }, []);
  const perform = useCallback(
    async (label: string, fn: () => Promise<void>) => {
      setPending(label);
      setError("");
      try {
        await fn();
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setPending("");
      }
    },
    [],
  );
  async function boot() {
    setError("");
    dirty.current = false;
    const sequence = ++openSequence.current;
    try {
      const rt = await connectStudio();
      setRuntime(rt);
      const data = await rt.call<{ projects: ProjectSummary[] }>(
        "drawai_project",
        { action: "list" },
      );
      setProjects(data.projects);
      const id =
        new URLSearchParams(window.location.search).get("project") ||
        currentProject.current?.id ||
        rt.initialProjectId() ||
        data.projects[0]?.id;
      if (id) {
        const data = await rt.call<ToolResult>("drawai_project", {
          action: "get",
          project_id: id,
        });
        if (sequence !== openSequence.current) return;
        accept(data);
        setActiveId(data.project?.slides[0]?.id || "");
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }
  useEffect(() => {
    void boot();
  }, []);
  useEffect(() => {
    if (!runtime) return;
    return runtime.onOpenProject((id) => {
      if (currentProject.current?.id === id) return;
      const sequence = ++openSequence.current;
      void (async () => {
        await saveCurrentPage.current();
        const data = await runtime.call<ToolResult>("drawai_project", {
          action: "get",
          project_id: id,
        });
        if (sequence !== openSequence.current) return;
        dirty.current = false;
        accept(data);
        setActiveId(data.project?.slides[0]?.id || "");
        setSelected([]);
        setTab("project");
      })().catch((err) => setError(err.message));
    });
  }, [runtime, accept]);
  useEffect(() => {
    if (!page || dirty.current) return;
    setDraft({ title: page.title, content: page.content, notes: page.notes });
    draftRevision.current = page.revision;
  }, [page?.id, page?.revision]);
  useEffect(() => {
    setRegion(undefined);
    markStart.current = undefined;
    setMarking(false);
    setCompare(false);
    setShowVersions(false);
    setEditOpen(false);
    setEditInstruction("");
    setPreviewMode("image");
    setInstruction("");
    setGenerationDirty(false);
    setGenerationTaskId(undefined);
  }, [activeId, project?.id]);
  useEffect(() => {
    if (!dirty.current || !page) return;
    const timer = setTimeout(() => {
      void savePage().catch((err) => setError(err.message));
    }, 600);
    return () => clearTimeout(timer);
  }, [draft.title, draft.content, draft.notes, page?.id]);
  useEffect(() => {
    if (!runtime || !project) return;
    let active = true;
    const timer = setInterval(
      () => {
        runtime
          .call<ToolResult>("drawai_project", {
            action: "get",
            project_id: project.id,
          })
          .then((data) => {
            if (active && currentProject.current?.id === project.id)
              accept(data);
          })
          .catch((err) => setError(err.message));
      },
      activeTaskCount ? 2500 : 8000,
    );
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [runtime, project?.id, activeTaskCount, accept]);
  useEffect(() => {
    if (!runtime || !project) return;
    void runtime
      .context({
        project_id: project.id,
        title: project.title,
        selected_slide_ids: chosenPages,
        active_slide_id: activeId,
      })
      .catch((err) => setError(err.message));
  }, [runtime, project?.id, activeId, selected.join(",")]);
  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(() => setNotice(""), 4500);
    return () => clearTimeout(t);
  }, [notice]);
  useEffect(() => {
    const task = tasks.find((item) => item.id === generationTaskId);
    if (task?.status === "completed") {
      if (task.instruction === instruction) setGenerationDirty(false);
      setGenerationTaskId(undefined);
    }
  }, [generationTaskId, project?.revision, instruction]);

  async function call(
    name: string,
    args: Record<string, unknown>,
  ): Promise<ToolResult> {
    if (!runtime) throw new Error("工作台尚未连接");
    return accept(
      await runtime.call<ToolResult>(name, {
        project_id: project?.id,
        ...args,
      }),
    );
  }
  async function savePage() {
    if (saving.current) await saving.current;
    if (!page || !dirty.current) return;
    const snapshot = { ...draftValue.current };
    saving.current = (async () => {
      const data = await call("drawai_project", {
        action: "update_slide",
        slide_id: page.id,
        expected_revision: draftRevision.current,
        ...snapshot,
      });
      dirty.current =
        JSON.stringify(snapshot) !== JSON.stringify(draftValue.current);
      const saved = data.project?.slides.find((s) => s.id === page.id);
      if (saved) draftRevision.current = saved.revision;
    })();
    try {
      await saving.current;
    } finally {
      saving.current = null;
    }
    if (dirty.current) await savePage();
  }
  function updateDraft(key: "title" | "content" | "notes", value: string) {
    dirty.current = true;
    setDraft((state) => ({ ...state, [key]: value }));
  }
  async function selectPage(id: string) {
    await savePage();
    dirty.current = false;
    setActiveId(id);
    setRegion(undefined);
    setPreviewMode("image");
    setCompare(false);
    setShowVersions(false);
    setPagesOpen(false);
    setMarking(false);
    setEditOpen(false);
    setInstruction("");
    setGenerationDirty(false);
    setGenerationTaskId(undefined);
  }
  async function selectProject(id: string) {
    ++openSequence.current;
    await savePage();
    const data = await call("drawai_project", {
      action: "get",
      project_id: id,
    });
    dirty.current = false;
    setActiveId(data.project?.slides[0]?.id || "");
    setSelected([]);
    setBatchSelection(false);
    setShowVersions(false);
    setEditOpen(false);
    setMarking(false);
    setInstruction("");
    setGenerationDirty(false);
    setGenerationTaskId(undefined);
    setRegion(undefined);
    setTab("project");
  }
  async function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    await perform("create", async () => {
      const data = await call("drawai_project", {
        action: "create",
        title: values.get("title"),
      });
      dirty.current = false;
      setActiveId(data.project!.slides[0].id);
      setSelected([]);
      setNewProjectOpen(false);
      setTab("project");
    });
  }
  async function addSlide() {
    await savePage();
    const data = await call("drawai_project", { action: "add_slide" });
    dirty.current = false;
    setActiveId(data.slide_id!);
    setTab("project");
  }
  async function movePage(delta: number) {
    if (!project || !page) return;
    const index = project.slides.indexOf(page);
    const target = index + delta;
    if (target < 0 || target >= project.slides.length) return;
    const ids = project.slides.map((s) => s.id);
    [ids[index], ids[target]] = [ids[target], ids[index]];
    await call("drawai_project", { action: "reorder", slide_ids: ids });
  }
  async function addTemplate(template: VisualTemplate, role: ReferenceRole) {
    await call("drawai_reference", {
      action: "template",
      template_id: template.id,
      role,
    });
    setNotice(`已加入 ${template.name}`);
    setTab("project");
  }
  async function uploadFiles(files: FileList | null, asPage = false) {
    if (!files?.length) return;
    await perform("upload", async () => {
      for (const file of Array.from(files))
        await call(asPage ? "drawai_artifact" : "drawai_reference", {
          action: asPage ? "import_image" : "upload",
          slide_id: activeId,
          filename: file.name,
          role: uploadRole,
          data_base64: await fileBase64(file),
        });
      setNotice(asPage ? "图片已加入当前页面" : "参考文件已保存");
    });
  }
  async function download(asset: StudioAsset) {
    const receipt = await runtime!.download({
      project_id: project!.id,
      asset_id: asset.id,
    });
    if (receipt) setDownloadReceipt(receipt);
  }
  async function sendTask(task: StudioTask) {
    await runtime!.send(task.prompt);
    await call("drawai_task", {
      action: "update",
      task_id: task.id,
      status: "submitted",
      message: "已交给当前 Codex 会话",
    });
    setRequest(undefined);
    setNotice("任务已发送到当前会话");
  }
  async function cancelTask(task: StudioTask) {
    const result = await call("drawai_task", {
      action: "cancel",
      task_id: task.id,
    });
    if (result.task?.status !== "cancelled") {
      setNotice("任务已结束，无需取消");
      return;
    }
    if (runtime!.canSend) {
      await runtime!.send(
        `用户已在 DrawAI 工作台取消任务 ${task.id}（项目 ${project!.id}）。请检查已记录的 cancelled 状态，停止该任务的后续步骤与产物登记。`,
      );
    }
    setNotice(
      runtime!.canSend
        ? "已取消，并通知当前会话停止此任务"
        : "已记录取消；执行中的会话也需要停止此任务",
    );
  }
  async function startTask(
    kind: TaskKind,
    text = instruction,
    targetIds?: string[],
  ) {
    await savePage();
    let requestInstruction = text;
    if (kind === "edit_image" && region)
      requestInstruction += `\n修改区域（相对整页，0–1 坐标）：${JSON.stringify(region)}。保持区域外其他内容。`;
    const ids = taskSlideIds(kind, project!, chosenPages, targetIds);
    const data = await call("drawai_task", {
      action: "create",
      kind,
      slide_ids: ids,
      instruction: requestInstruction,
    });
    setRequest(data.task);
    if (kind === "generate") setGenerationTaskId(data.task!.id);
    if (runtime!.canSend) await sendTask(data.task!);
  }
  function upload(role: ReferenceRole) {
    setUploadRole(role);
    if (uploadRef.current) {
      uploadRef.current.value = "";
      uploadRef.current.click();
    }
  }
  const output = previewMode === "editable" ? editablePreview : currentImage;
  saveCurrentPage.current = savePage;
  const priorImage = images
    .slice()
    .reverse()
    .find((image) => image.id !== currentImage?.id);
  function openEdit(mark = false) {
    setPreviewMode("image");
    setCompare(false);
    setEditInstruction("");
    setRegion(undefined);
    setMarking(mark);
    setEditOpen(!mark);
  }
  function runPrimary() {
    if (marking) {
      setMarking(false);
      setEditOpen(true);
    } else if (nextAction?.kind === "busy") {
      setRequest(nextAction.task);
    } else if (nextAction?.kind === "download") {
      void perform("download", () => download(nextAction.asset));
    } else if (nextAction) {
      void perform(nextAction.kind, () =>
        startTask(nextAction.kind, instruction, nextAction.slideIds),
      );
    }
  }

  return (
    <div className="studio-app app-root" data-studio-revision="6">
      <header className="app-topbar studio-topbar studio-single-header">
        <DrawAiBrand />
        <div className="studio-project-choice">
          {project ? (
            <select
              aria-label="选择 PPT 项目"
              disabled={Boolean(pending)}
              value={project.id}
              onChange={(e) =>
                void perform("switch", () => selectProject(e.target.value))
              }
            >
              {projects.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.title}
                </option>
              ))}
            </select>
          ) : (
            <span className="studio-muted">PPT 工作台</span>
          )}
        </div>
        <div className="topbar-links">
          {tab !== "project" && (
            <button
              className="studio-back-to-page"
              aria-label="返回制作"
              title="返回制作"
              onClick={() => setTab("project")}
            >
              <Icon name="arrowLeft" />
              <span>返回制作</span>
            </button>
          )}
          <ActionMenu label="更多项目操作">
            <div className="studio-menu-context">
              <span
                className={`studio-status-dot ${runtime?.canSend ? "online" : ""}`}
              />
              {runtime?.canSend
                ? "当前 Codex 会话"
                : runtime
                  ? "浏览器工作台"
                  : "正在连接"}
              {project && (
                <small>
                  {project.slides.length} 页 · {project.aspect_ratio}
                </small>
              )}
            </div>
            <button
              disabled={!runtime || Boolean(pending)}
              onClick={() => setNewProjectOpen(true)}
            >
              <Icon name="plus" />
              新建 PPT 项目
            </button>
            {project && (
              <button onClick={() => setSettingsOpen(true)}>
                <Icon name="settings" />
                项目设置
              </button>
            )}
            <button
              disabled={!runtime || Boolean(pending)}
              onClick={() =>
                void perform("save", async () => {
                  await savePage();
                  setTab("templates");
                })
              }
            >
              <Icon name="grid" />
              浏览参考模板
            </button>
            {project && (
              <button onClick={() => setTab("tasks")}>
                <Icon name="clock" />
                制作记录
                {activeTaskCount > 0 && (
                  <span className="studio-nav-count">{activeTaskCount}</span>
                )}
              </button>
            )}
            {project && (
              <button
                disabled={
                  Boolean(pending) ||
                  project.slides.some((item) => !item.current_image_id) ||
                  !project.slides.length
                }
                onClick={() =>
                  void perform("export", () => startTask("export_deck"))
                }
              >
                <Icon name="slides" />
                制作整套可编辑 PPT
              </button>
            )}
            {project && (
              <button
                disabled={Boolean(pending)}
                onClick={() =>
                  void perform("archive", async () => {
                    const receipt = await runtime!.download({
                      project_id: project.id,
                    });
                    if (receipt) setDownloadReceipt(receipt);
                  })
                }
              >
                <Icon name="download" />
                下载项目文件
              </button>
            )}
            <button
              disabled={Boolean(pending)}
              onClick={() => void perform("refresh", boot)}
            >
              <Icon name="refresh" />
              刷新项目
            </button>
          </ActionMenu>
        </div>
      </header>
      {error && (
        <div className="studio-notice error" role="alert">
          <span>{error}</span>
          <button onClick={() => setError("")} aria-label="关闭错误">
            <Icon name="close" size={15} />
          </button>
        </div>
      )}
      {notice && (
        <div className="studio-toast" role="status">
          <Icon name="check" />
          {notice}
        </div>
      )}
      {downloadReceipt && (
        <div className="studio-notice" role="status">
          <div>
            已保存：{downloadReceipt.filename}
            <div className="studio-download-path">
              {downloadReceipt.saved_path}
            </div>
          </div>
          <button
            onClick={() => setDownloadReceipt(undefined)}
            aria-label="关闭下载提示"
          >
            <Icon name="close" size={15} />
          </button>
        </div>
      )}
      <input
        ref={uploadRef}
        type="file"
        hidden
        multiple
        accept=".png,.jpg,.jpeg,.webp,.svg,.pdf,.pptx,.txt,.md,.json"
        onChange={(e) => void uploadFiles(e.target.files)}
      />
      <input
        ref={imageRef}
        type="file"
        hidden
        accept=".png,.jpg,.jpeg,.webp"
        onChange={(e) => void uploadFiles(e.target.files, true)}
      />

      {runtime && tab === "templates" ? (
        <TemplateLibrary
          runtime={runtime}
          canUse={Boolean(project)}
          onUse={addTemplate}
          selectedIds={
            project?.references
              .map((ref) => ref.template_id)
              .filter((id): id is string => Boolean(id)) || []
          }
        />
      ) : !project ? (
        <main className="studio-welcome">
          <div className="studio-welcome-mark">
            <Icon name="slides" size={36} />
          </div>
          <h1>开始制作一份 PPT</h1>
          <p>创建项目，整理内容与参考，再让当前会话生成页面。</p>
          <div className="studio-welcome-actions">
            <button
              className="primary"
              disabled={!runtime}
              onClick={() => setNewProjectOpen(true)}
            >
              <Icon name="plus" />
              创建 PPT 项目
            </button>
            <button disabled={!runtime} onClick={() => setTab("templates")}>
              先看看参考模板
            </button>
          </div>
        </main>
      ) : tab === "tasks" ? (
        <main className="studio-tasks-page">
          <div className="studio-section-heading">
            <div>
              <h1>制作记录</h1>
              <p>查看执行进度、文件和需要处理的问题。</p>
            </div>
          </div>
          {!tasks.length && (
            <div className="studio-empty">
              <Icon name="clock" size={36} />
              <h3>还没有制作任务</h3>
              <p>填写页面内容并添加参考后，即可开始生成。</p>
            </div>
          )}
          <div className="studio-task-list">
            {tasks.map((task) => (
              <article key={task.id} className="studio-task-card">
                <div className={`studio-task-icon ${task.status}`}>
                  <Icon
                    name={
                      task.kind === "convert" || task.kind === "export_deck"
                        ? "slides"
                        : "image"
                    }
                  />
                </div>
                <div className="studio-task-body">
                  <div className="studio-task-title">
                    <strong>{taskLabels[task.kind]}</strong>
                    <span className={`studio-badge ${task.status}`}>
                      {statusLabels[task.status]}
                    </span>
                  </div>
                  <p>
                    {task.slide_ids
                      .map(
                        (id) =>
                          project.slides.find((item) => item.id === id)
                            ?.title || "已移除页面",
                      )
                      .join("、") || "项目参考文件"}
                  </p>
                  <span className="studio-task-message">{task.message}</span>
                  <small>
                    {timeLabel(task.created_at)} · {task.artifact_ids.length}{" "}
                    个产物
                  </small>
                  {task.artifact_ids.length > 0 && (
                    <details className="studio-detail-disclosure">
                      <summary>查看产物（{task.artifact_ids.length}）</summary>
                      <div className="studio-artifact-links">
                        {task.artifact_ids
                          .map((id) =>
                            project.assets.find((asset) => asset.id === id),
                          )
                          .filter((asset): asset is StudioAsset =>
                            Boolean(asset),
                          )
                          .map((asset) => (
                            <button
                              key={asset.id}
                              onClick={() =>
                                void perform("download", () => download(asset))
                              }
                            >
                              <Icon name="download" size={14} />
                              {asset.filename}
                            </button>
                          ))}
                      </div>
                    </details>
                  )}
                </div>
                <div className="studio-task-actions">
                  <button onClick={() => setRequest(task)}>查看详情</button>
                  {task.status === "draft" && runtime?.canSend && (
                    <button
                      disabled={Boolean(pending)}
                      onClick={() => void perform("send", () => sendTask(task))}
                    >
                      发送请求
                    </button>
                  )}
                  {activeStates.includes(task.status) && (
                    <button
                      disabled={Boolean(pending)}
                      onClick={() =>
                        void perform("cancel", () => cancelTask(task))
                      }
                    >
                      取消任务
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        </main>
      ) : (
        <>
          <div className="studio-layout">
            <aside className="studio-pages">
              <div className="studio-panel-head">
                <strong>
                  页面{" "}
                  <span className="studio-muted">{project.slides.length}</span>
                </strong>
                <ActionMenu label="更多页面操作">
                  <button
                    onClick={() => {
                      setBatchSelection(!batchSelection);
                      setSelected([]);
                    }}
                  >
                    {batchSelection ? "结束批量选择" : "批量选择页面"}
                  </button>
                  {page && (
                    <>
                      <button
                        disabled={
                          Boolean(pending) || project.slides[0]?.id === activeId
                        }
                        onClick={() => void perform("move", () => movePage(-1))}
                      >
                        <Icon name="arrowUp" />
                        上移当前页
                      </button>
                      <button
                        disabled={
                          Boolean(pending) ||
                          project.slides[project.slides.length - 1]?.id ===
                            activeId
                        }
                        onClick={() => void perform("move", () => movePage(1))}
                      >
                        <Icon name="arrowDown" />
                        下移当前页
                      </button>
                      <button
                        disabled={Boolean(pending)}
                        onClick={() =>
                          void perform("duplicate", async () => {
                            await savePage();
                            const data = await call("drawai_project", {
                              action: "duplicate_slide",
                              slide_id: page.id,
                            });
                            dirty.current = false;
                            setActiveId(data.slide_id!);
                            setSelected([]);
                          })
                        }
                      >
                        <Icon name="copy" />
                        复制当前页
                      </button>
                      <button
                        className="studio-menu-danger"
                        onClick={() => setDeleteTarget("slide")}
                      >
                        <Icon name="trash" />
                        删除当前页
                      </button>
                    </>
                  )}
                </ActionMenu>
              </div>
              {batchSelection && (
                <div className="studio-batch-selection">
                  <span>已选 {selected.length} 页</span>
                  <button
                    onClick={() =>
                      setSelected(
                        selected.length === project.slides.length
                          ? []
                          : project.slides.map((item) => item.id),
                      )
                    }
                  >
                    {selected.length === project.slides.length
                      ? "取消全选"
                      : "全选"}
                  </button>
                </div>
              )}
              <div className="studio-page-list">
                {project.slides.map((item, index) => (
                  <div
                    key={item.id}
                    className={`studio-page-card ${activeId === item.id ? "active" : ""}`}
                  >
                    <button
                      className="studio-page-open"
                      aria-label={`打开第 ${index + 1} 页：${item.title}`}
                      onClick={() =>
                        void perform("select", () => selectPage(item.id))
                      }
                    >
                      <div
                        className="studio-page-thumbnail"
                        style={{
                          aspectRatio: project.aspect_ratio.replace(":", "/"),
                        }}
                      >
                        {item.current_image_id ? (
                          <AssetImage
                            runtime={runtime!}
                            projectId={project.id}
                            assetId={item.current_image_id}
                            alt={item.title}
                          />
                        ) : (
                          <div className="studio-page-text">
                            <span>{String(index + 1).padStart(2, "0")}</span>
                            <b>{item.title}</b>
                          </div>
                        )}
                      </div>
                      <div className="studio-page-label">
                        <span>{String(index + 1).padStart(2, "0")}</span>
                        <strong>{item.title}</strong>
                        {item.content_changed ? (
                          <span
                            className="studio-page-outdated"
                            title="内容已修改，图片待更新"
                          >
                            ·
                          </span>
                        ) : (
                          item.current_pptx_id && (
                            <span
                              className="studio-page-ready"
                              title="可编辑 PPT 已完成"
                            >
                              <Icon name="check" size={13} />
                            </span>
                          )
                        )}
                      </div>
                    </button>
                    {batchSelection && (
                      <input
                        className="studio-page-select"
                        type="checkbox"
                        aria-label={`选择第 ${index + 1} 页`}
                        checked={selected.includes(item.id)}
                        onChange={(e) =>
                          setSelected((ids) =>
                            e.target.checked
                              ? [...ids, item.id]
                              : ids.filter((id) => id !== item.id),
                          )
                        }
                      />
                    )}
                  </div>
                ))}
              </div>
              <button
                className="studio-add-page"
                disabled={Boolean(pending)}
                onClick={() => void perform("add", addSlide)}
              >
                <Icon name="plus" />
                添加页面
              </button>
            </aside>
            <main className="studio-editor">
              {page ? (
                <>
                  <div className="studio-canvas-toolbar">
                    <button
                      className="studio-page-switch"
                      onClick={() => setPagesOpen(true)}
                    >
                      <Icon name="slides" />第{" "}
                      {project.slides.findIndex(
                        (item) => item.id === activeId,
                      ) + 1}{" "}
                      / {project.slides.length} 页
                    </button>
                    {displayPptx ? (
                      <div className="studio-segment">
                        <button
                          className={previewMode === "image" ? "selected" : ""}
                          onClick={() => setPreviewMode("image")}
                        >
                          页面图片
                        </button>
                        <button
                          className={
                            previewMode === "editable" ? "selected" : ""
                          }
                          onClick={() => setPreviewMode("editable")}
                        >
                          PPT 预览
                        </button>
                      </div>
                    ) : (
                      <span className="studio-preview-label">页面预览</span>
                    )}
                    <ActionMenu label="更多图片操作">
                      <button onClick={() => imageRef.current?.click()}>
                        <Icon name="upload" />
                        导入已有图片
                      </button>
                      {currentImage && (
                        <>
                          <button
                            disabled={
                              Boolean(pending) || nextAction?.kind === "busy"
                            }
                            onClick={() =>
                              void perform("generate", () =>
                                startTask("generate", instruction, [activeId]),
                              )
                            }
                          >
                            <Icon name="sparkle" />
                            重新生成当前页
                          </button>
                          <button
                            disabled={
                              Boolean(pending) || nextAction?.kind === "busy"
                            }
                            onClick={() => openEdit(true)}
                          >
                            <Icon name="crop" />
                            标记区域并修改
                          </button>
                          <button
                            disabled={
                              Boolean(pending) || nextAction?.kind === "busy"
                            }
                            onClick={() =>
                              void perform("convert", () =>
                                startTask("convert", instruction, [activeId]),
                              )
                            }
                          >
                            <Icon name="slides" />
                            只转换当前页
                          </button>
                        </>
                      )}
                      {images.length > 1 && (
                        <>
                          <button
                            onClick={() => setShowVersions(!showVersions)}
                          >
                            <Icon name="clock" />
                            {showVersions
                              ? "收起历史版本"
                              : `查看 ${images.length} 个图片版本`}
                          </button>
                          <button
                            onClick={() => {
                              setCompare(!compare);
                              setPreviewMode("image");
                            }}
                          >
                            <Icon name="compare" />
                            {compare ? "结束版本比较" : "比较图片版本"}
                          </button>
                        </>
                      )}
                      {output && (
                        <button
                          disabled={Boolean(pending)}
                          onClick={() =>
                            void perform("download", () => download(output))
                          }
                        >
                          <Icon name="download" />
                          下载预览图片
                        </button>
                      )}
                      {selected.length > 0 && (
                        <button
                          disabled={
                            Boolean(pending) ||
                            nextAction?.kind === "busy" ||
                            chosenPages.some(
                              (id) =>
                                !project.slides.find((item) => item.id === id)
                                  ?.current_image_id,
                            )
                          }
                          onClick={() =>
                            void perform("convert", () => startTask("convert"))
                          }
                        >
                          转换所选 {selected.length} 页
                        </button>
                      )}
                    </ActionMenu>
                  </div>
                  {marking && (
                    <div className="studio-marking-hint">
                      <Icon name="crop" size={15} />
                      拖动框选需要修改的区域，然后点击底部“填写修改要求”。
                    </div>
                  )}
                  <div className="studio-canvas-area">
                    {page.content_changed && (
                      <div className="studio-stale-note">
                        内容或参考已更新，下一步更新这页图片。
                      </div>
                    )}
                    <div
                      className={`studio-canvas-comparison ${compare && priorImage ? "split" : ""}`}
                    >
                      {compare && priorImage && (
                        <figure>
                          <AssetImage
                            runtime={runtime!}
                            projectId={project.id}
                            assetId={priorImage.id}
                            alt="上一版本"
                          />
                          <figcaption>上一版本</figcaption>
                        </figure>
                      )}
                      <div
                        className={`studio-canvas ${marking ? "marking" : ""}`}
                        style={{
                          aspectRatio: project.aspect_ratio.replace(":", "/"),
                        }}
                        onPointerDown={(event) => {
                          if (!marking) return;
                          const rect =
                            event.currentTarget.getBoundingClientRect();
                          markStart.current = {
                            x: (event.clientX - rect.left) / rect.width,
                            y: (event.clientY - rect.top) / rect.height,
                          };
                          event.currentTarget.setPointerCapture(
                            event.pointerId,
                          );
                        }}
                        onPointerMove={(event) => {
                          if (!markStart.current) return;
                          const rect =
                            event.currentTarget.getBoundingClientRect();
                          const x = Math.max(
                            0,
                            Math.min(
                              1,
                              (event.clientX - rect.left) / rect.width,
                            ),
                          );
                          const y = Math.max(
                            0,
                            Math.min(
                              1,
                              (event.clientY - rect.top) / rect.height,
                            ),
                          );
                          const start = markStart.current;
                          setRegion({
                            x: +Math.min(x, start.x).toFixed(3),
                            y: +Math.min(y, start.y).toFixed(3),
                            width: +Math.abs(x - start.x).toFixed(3),
                            height: +Math.abs(y - start.y).toFixed(3),
                          });
                        }}
                        onPointerUp={() => {
                          markStart.current = undefined;
                        }}
                      >
                        {output ? (
                          <AssetImage
                            runtime={runtime!}
                            projectId={project.id}
                            assetId={output.id}
                            alt={page.title}
                          />
                        ) : (
                          <div className="studio-canvas-empty">
                            <Icon
                              name={
                                previewMode === "editable" ? "slides" : "image"
                              }
                              size={40}
                            />
                            <h3>
                              {previewMode === "editable"
                                ? "可编辑 PPT 已完成"
                                : "这里会显示生成的页面"}
                            </h3>
                            <p>
                              {previewMode === "editable"
                                ? "文件已就绪，下载后即可查看与编辑。"
                                : "填写页面内容并添加参考，然后点击底部的生成按钮。"}
                            </p>
                          </div>
                        )}
                        {region && (
                          <div
                            className="studio-region"
                            style={{
                              left: `${region.x * 100}%`,
                              top: `${region.y * 100}%`,
                              width: `${region.width * 100}%`,
                              height: `${region.height * 100}%`,
                            }}
                          />
                        )}
                      </div>
                    </div>
                    <div className="studio-canvas-caption">
                      <span>{page.title}</span>
                      <span>
                        {previewMode === "editable"
                          ? "可编辑 PPT"
                          : project.aspect_ratio}
                      </span>
                    </div>
                  </div>
                  {showVersions && images.length > 1 && (
                    <div className="studio-versions">
                      <span>选择图片版本</span>
                      {images.map((asset, index) => (
                        <button
                          key={asset.id}
                          title={`使用版本 ${index + 1}`}
                          className={
                            asset.id === currentImage?.id ? "active" : ""
                          }
                          onClick={() =>
                            void perform("version", async () => {
                              await call("drawai_artifact", {
                                action: "select",
                                slide_id: page.id,
                                asset_id: asset.id,
                              });
                            })
                          }
                        >
                          <AssetImage
                            runtime={runtime!}
                            projectId={project.id}
                            assetId={asset.id}
                            alt={`版本 ${index + 1}`}
                          />
                          <span>V{index + 1}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <div className="studio-empty">
                  <Icon name="slides" size={36} />
                  <h3>添加第一张页面</h3>
                  <button
                    className="primary"
                    onClick={() => void perform("add", addSlide)}
                  >
                    添加页面
                  </button>
                </div>
              )}
            </main>
            <aside className="studio-inspector">
              <div className="studio-panel-head">
                <strong>编辑当前页</strong>
                <small className="studio-muted">自动保存</small>
              </div>
              <div className="studio-inspector-scroll">
                {page && (
                  <section className="studio-inspector-section">
                    <label>
                      标题
                      <input
                        value={draft.title}
                        onChange={(e) => updateDraft("title", e.target.value)}
                        onBlur={() =>
                          void savePage().catch((err) => setError(err.message))
                        }
                      />
                    </label>
                    <label>
                      这页要展示的内容
                      <textarea
                        rows={7}
                        value={draft.content}
                        onChange={(e) => updateDraft("content", e.target.value)}
                        onBlur={() =>
                          void savePage().catch((err) => setError(err.message))
                        }
                        placeholder="写下核心观点、准确文字和数据。"
                      />
                    </label>
                  </section>
                )}
                <section className="studio-inspector-section">
                  <div className="studio-section-label">
                    <strong>参考与材料</strong>
                    <span>{project.references.length}</span>
                  </div>
                  <ActionMenu label="添加参考" icon="plus" inline>
                    <button
                      onClick={() =>
                        void perform("save", async () => {
                          await savePage();
                          setTab("templates");
                        })
                      }
                    >
                      <Icon name="grid" />
                      选择图像模板
                    </button>
                    <button onClick={() => upload("content")}>
                      <Icon name="file" />
                      上传内容材料
                    </button>
                    <button onClick={() => upload("style")}>
                      <Icon name="image" />
                      上传风格图片
                    </button>
                    <button onClick={() => upload("ppt_template")}>
                      <Icon name="slides" />
                      上传 PPT 格式模板
                    </button>
                  </ActionMenu>
                  {!project.references.length && (
                    <p className="studio-muted">
                      可以组合图像参考与 PPT 格式模板。
                    </p>
                  )}
                  <div className="studio-reference-list">
                    {project.references.map((ref) => (
                      <details
                        className="studio-reference studio-reference-disclosure"
                        key={ref.id}
                      >
                        <summary className="studio-reference-head">
                          <div className="studio-reference-thumb">
                            {ref.preview_asset_id ? (
                              <AssetImage
                                runtime={runtime!}
                                projectId={project.id}
                                assetId={ref.preview_asset_id}
                                alt={ref.name}
                              />
                            ) : ref.template?.assets[0] ? (
                              <img
                                src={
                                  ref.template.assets[0].image_urls?.thumb ||
                                  ref.template.assets[0].original_url
                                }
                                alt={ref.name}
                              />
                            ) : (
                              <Icon name="file" size={23} />
                            )}
                          </div>
                          <div className="studio-reference-summary">
                            <strong title={ref.name}>{ref.name}</strong>
                            <small>
                              {roleLabels[ref.role]} ·{" "}
                              {ref.slide_ids.length
                                ? ref.slide_ids.includes(activeId)
                                  ? "用于当前页"
                                  : "用于其他页面"
                                : "整份 PPT"}
                            </small>
                          </div>
                        </summary>
                        <div className="studio-reference-options">
                          <div className="studio-reference-fields">
                            <select
                              aria-label={`${ref.name} 的参考用途`}
                              value={ref.role}
                              onChange={(e) =>
                                void perform("role", async () => {
                                  await call("drawai_reference", {
                                    action: "update",
                                    reference_id: ref.id,
                                    role: e.target.value,
                                  });
                                })
                              }
                            >
                              {Object.entries(roleLabels).map(([key, text]) => (
                                <option key={key} value={key}>
                                  {text}
                                </option>
                              ))}
                            </select>
                            <select
                              aria-label={`${ref.name} 的应用范围`}
                              value={ref.slide_ids.length ? "page" : "deck"}
                              onChange={(e) =>
                                void perform("scope", async () => {
                                  await call("drawai_reference", {
                                    action: "update",
                                    reference_id: ref.id,
                                    slide_ids:
                                      e.target.value === "deck"
                                        ? []
                                        : [activeId],
                                  });
                                })
                              }
                            >
                              <option value="deck">整份 PPT</option>
                              <option value="page" disabled={!activeId}>
                                指定页面
                              </option>
                            </select>
                          </div>
                          {ref.slide_ids.length > 0 && (
                            <small className="studio-muted">
                              用于：
                              {ref.slide_ids
                                .map(
                                  (id) =>
                                    project.slides.find(
                                      (item) => item.id === id,
                                    )?.title,
                                )
                                .join("、")}
                            </small>
                          )}
                          {ref.role === "ppt_template" && (
                            <button
                              className="studio-text-button"
                              disabled={Boolean(pending)}
                              onClick={() =>
                                void perform("prepare", () =>
                                  startTask("prepare_reference"),
                                )
                              }
                            >
                              解析模板并生成预览
                            </button>
                          )}
                          <button
                            className="studio-text-button"
                            disabled={Boolean(pending)}
                            onClick={() =>
                              void perform("remove-ref", async () => {
                                await call("drawai_reference", {
                                  action: "remove",
                                  reference_id: ref.id,
                                });
                              })
                            }
                          >
                            移除这个参考
                          </button>
                        </div>
                      </details>
                    ))}
                  </div>
                </section>
                {page && (
                  <section className="studio-inspector-section">
                    <details className="studio-detail-disclosure">
                      <summary>补充要求与备注（可选）</summary>
                      <label>
                        制作要求
                        <textarea
                          value={instruction}
                          onChange={(e) => {
                            setInstruction(e.target.value);
                            setGenerationDirty(true);
                          }}
                          placeholder="布局、视觉风格，或想交给会话完成的制作任务。"
                          rows={3}
                        />
                      </label>
                      <label>
                        讲述备注
                        <textarea
                          rows={3}
                          value={draft.notes}
                          onChange={(e) => updateDraft("notes", e.target.value)}
                          onBlur={() =>
                            void savePage().catch((err) =>
                              setError(err.message),
                            )
                          }
                          placeholder="听众、讲解重点或来源说明"
                        />
                      </label>
                    </details>
                  </section>
                )}
              </div>
            </aside>
          </div>
          {page && nextAction && (
            <footer className="studio-workflow-bar">
              <div className="studio-workflow-copy">
                <strong>{marking ? "区域修改" : "下一步"}</strong>
                <span>
                  {marking
                    ? "标记完成后，填写你想修改的内容。"
                    : nextAction.description}
                </span>
              </div>
              <div className="studio-workflow-actions">
                {currentImage &&
                  !marking &&
                  nextAction.kind !== "busy" &&
                  !selected.length && (
                    <button
                      disabled={Boolean(pending)}
                      onClick={() => openEdit()}
                    >
                      修改图片
                    </button>
                  )}
                <button
                  className="primary"
                  disabled={
                    Boolean(pending) || (!marking && nextAction.disabled)
                  }
                  onClick={runPrimary}
                >
                  <Icon
                    name={
                      marking
                        ? "image"
                        : nextAction.kind === "download"
                          ? "download"
                          : nextAction.kind === "busy"
                            ? "clock"
                            : nextAction.kind === "generate"
                              ? "sparkle"
                              : "slides"
                    }
                  />
                  {pending
                    ? "正在准备…"
                    : marking
                      ? "填写修改要求"
                      : nextAction.label}
                </button>
              </div>
            </footer>
          )}
        </>
      )}

      {pagesOpen && project && (
        <Dialog title="选择页面" onClose={() => setPagesOpen(false)}>
          <div className="studio-page-picker">
            {project.slides.map((item, index) => (
              <button
                key={item.id}
                className={activeId === item.id ? "selected" : ""}
                onClick={() =>
                  void perform("select", () => selectPage(item.id))
                }
              >
                {item.current_image_id && (
                  <AssetImage
                    runtime={runtime!}
                    projectId={project.id}
                    assetId={item.current_image_id}
                    alt={item.title}
                  />
                )}
                <span>
                  {index + 1}. {item.title}
                </span>
              </button>
            ))}
            <button
              disabled={Boolean(pending)}
              onClick={() =>
                void perform("add", async () => {
                  await addSlide();
                  setPagesOpen(false);
                })
              }
            >
              <Icon name="plus" />
              添加页面
            </button>
          </div>
        </Dialog>
      )}
      {editOpen && page && (
        <Dialog title="修改当前页图片" onClose={() => setEditOpen(false)}>
          <div className="studio-form-body">
            <label>
              你想修改什么？
              <textarea
                autoFocus
                rows={4}
                value={editInstruction}
                onChange={(e) => setEditInstruction(e.target.value)}
                placeholder="例如：减少文字、放大关键数字，其他部分保持原样。"
              />
            </label>
            <div className="studio-edit-region">
              <span>
                {region ? "已标记修改区域" : "可以针对整张图片描述修改。"}
              </span>
              <button
                onClick={() => {
                  setEditOpen(false);
                  setMarking(true);
                  setPreviewMode("image");
                }}
              >
                {region ? "重新标记区域" : "在图片上标记区域"}
              </button>
              {region && (
                <button onClick={() => setRegion(undefined)}>清除区域</button>
              )}
            </div>
          </div>
          <footer>
            <button onClick={() => setEditOpen(false)}>取消</button>
            <button
              className="primary"
              disabled={Boolean(pending) || !editInstruction.trim()}
              onClick={() =>
                void perform("edit", async () => {
                  await startTask("edit_image", editInstruction, [activeId]);
                  setEditOpen(false);
                  setMarking(false);
                  setRegion(undefined);
                })
              }
            >
              发送修改要求
            </button>
          </footer>
        </Dialog>
      )}
      {newProjectOpen && (
        <Dialog title="创建 PPT 项目" onClose={() => setNewProjectOpen(false)}>
          <form onSubmit={createProject}>
            <div className="studio-form-body">
              <label>
                项目名称
                <input
                  name="title"
                  required
                  autoFocus
                  placeholder="例如：论文组会汇报"
                  maxLength={180}
                />
              </label>
            </div>
            <footer>
              <button type="button" onClick={() => setNewProjectOpen(false)}>
                取消
              </button>
              <button className="primary" disabled={Boolean(pending)}>
                创建项目
              </button>
            </footer>
          </form>
        </Dialog>
      )}
      {settingsOpen && project && (
        <Dialog title="项目设置" onClose={() => setSettingsOpen(false)}>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              const values = Object.fromEntries(
                new FormData(event.currentTarget),
              );
              void perform("settings", async () => {
                await call("drawai_project", { action: "update", ...values });
                setSettingsOpen(false);
              });
            }}
          >
            <div className="studio-form-body">
              <label>
                项目名称
                <input name="title" defaultValue={project.title} required />
              </label>
              <label>
                整份 PPT 的目标
                <textarea
                  name="brief"
                  defaultValue={project.brief}
                  rows={3}
                  placeholder="主题、听众、时长与重点"
                />
              </label>
              <div className="studio-form-grid">
                <label>
                  页面比例
                  <select
                    name="aspect_ratio"
                    defaultValue={project.aspect_ratio}
                  >
                    <option>16:9</option>
                    <option>4:3</option>
                    <option>3:2</option>
                  </select>
                </label>
                <label>
                  主要语言
                  <select name="language" defaultValue={project.language}>
                    <option value="zh">中文</option>
                    <option value="en">English</option>
                  </select>
                </label>
              </div>
              <label>
                全局风格要求
                <textarea
                  name="style_notes"
                  defaultValue={project.style_notes}
                  rows={3}
                  placeholder="配色、字体、信息密度、需要保留的格式"
                />
              </label>
              <button
                className="danger"
                type="button"
                onClick={() => {
                  setSettingsOpen(false);
                  setDeleteTarget("project");
                }}
              >
                <Icon name="trash" />
                删除项目
              </button>
            </div>
            <footer>
              <button type="button" onClick={() => setSettingsOpen(false)}>
                取消
              </button>
              <button className="primary" disabled={Boolean(pending)}>
                保存设置
              </button>
            </footer>
          </form>
        </Dialog>
      )}
      {request && (
        <Dialog
          title={taskLabels[request.kind]}
          onClose={() => setRequest(undefined)}
        >
          <div className="studio-form-body">
            <span className={`studio-badge ${request.status}`}>
              {statusLabels[request.status]}
            </span>
            <p>{request.message}</p>
            {!runtime?.canSend && request.status === "draft" && (
              <div className="studio-notice">
                复制任务请求，粘贴到 Codex 会话中执行，结果会回到本项目。
              </div>
            )}
            {request.artifact_ids.length > 0 && (
              <div className="studio-artifact-links">
                {request.artifact_ids
                  .map((id) => project?.assets.find((asset) => asset.id === id))
                  .filter((asset): asset is StudioAsset => Boolean(asset))
                  .map((asset) => (
                    <button
                      key={asset.id}
                      onClick={() =>
                        void perform("download", () => download(asset))
                      }
                    >
                      <Icon name="download" size={14} />
                      {asset.filename}
                    </button>
                  ))}
              </div>
            )}
            <details className="studio-detail-disclosure">
              <summary>查看会话任务请求</summary>
              <textarea readOnly value={request.prompt} rows={7} />
            </details>
          </div>
          <footer>
            {activeStates.includes(request.status) && (
              <button
                disabled={Boolean(pending)}
                onClick={() =>
                  void perform("cancel", () => cancelTask(request))
                }
              >
                取消任务
              </button>
            )}
            <button
              onClick={() =>
                void perform("copy", async () => {
                  await navigator.clipboard.writeText(request.prompt);
                  setNotice("任务请求已复制");
                })
              }
            >
              <Icon name="copy" />
              复制任务请求
            </button>
            {runtime?.canSend && request.status === "draft" && (
              <button
                className="primary"
                disabled={Boolean(pending)}
                onClick={() => void perform("send", () => sendTask(request))}
              >
                <Icon name="send" />
                发送到当前会话
              </button>
            )}
          </footer>
        </Dialog>
      )}
      {deleteTarget && (
        <Dialog
          title={deleteTarget === "project" ? "删除项目" : "删除页面"}
          onClose={() => setDeleteTarget(undefined)}
        >
          <div className="studio-form-body">
            <p>
              {deleteTarget === "project"
                ? `删除“${project?.title}”及其工作台记录？项目文件会移入本地回收目录。`
                : `删除“${page?.title}”？已有产物会保留在项目中。`}
            </p>
          </div>
          <footer>
            <button onClick={() => setDeleteTarget(undefined)}>取消</button>
            <button
              className="danger"
              disabled={Boolean(pending)}
              onClick={() =>
                void perform("delete", async () => {
                  const deletingProject = deleteTarget === "project";
                  const result = await call("drawai_project", {
                    action: deletingProject ? "delete" : "delete_slide",
                    slide_id: activeId,
                  });
                  dirty.current = false;
                  setDeleteTarget(undefined);
                  if (deletingProject) {
                    setProject(undefined);
                    currentProject.current = undefined;
                    setActiveId("");
                    await boot();
                  } else {
                    setActiveId(result.project?.slides[0]?.id || "");
                    setSelected((ids) => ids.filter((id) => id !== activeId));
                  }
                })
              }
            >
              确认删除
            </button>
          </footer>
        </Dialog>
      )}
    </div>
  );
}
