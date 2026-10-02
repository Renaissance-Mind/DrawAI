import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import { connectStudio, fileBase64, type StudioRuntime } from "./runtime";
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
import { Icon, IconButton, Dialog, AssetImage } from "./components";
import TemplateLibrary from "./TemplateLibrary";
import "./studio.css";

type Tab = "project" | "templates" | "tasks";
const activeStates = ["draft", "submitted", "running"];

export default function StudioWorkspace() {
  const [runtime, setRuntime] = useState<StudioRuntime>();
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [project, setProject] = useState<StudioProject>();
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
  const [pending, setPending] = useState("");
  const [newProjectOpen, setNewProjectOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [request, setRequest] = useState<StudioTask>();
  const [instruction, setInstruction] = useState("");
  const [compare, setCompare] = useState(false);
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
  const [mobilePanel, setMobilePanel] = useState<"pages" | "details" | "">("");
  const page = project?.slides.find((s) => s.id === activeId);
  const images =
    project?.assets.filter(
      (a) => a.slide_id === activeId && a.kind === "image",
    ) || [];
  const currentImage = project?.assets.find(
    (a) => a.id === page?.current_image_id,
  );
  const pptx = project?.assets.find((a) => a.id === page?.current_pptx_id);
  const editablePreview = project?.assets
    .slice()
    .reverse()
    .find(
      (a) =>
        a.kind === "preview" &&
        a.slide_id === activeId &&
        a.task_id === pptx?.task_id,
    );
  const tasks = project?.tasks || [];
  const chosenPages = selected.length ? selected : activeId ? [activeId] : [];
  const activeTaskCount = tasks.filter((t) =>
    activeStates.includes(t.status),
  ).length;

  const accept = useCallback((data: ToolResult) => {
    if (data.project) {
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
        data.projects[0]?.id;
      if (id) {
        const data = await rt.call<ToolResult>("drawai_project", {
          action: "get",
          project_id: id,
        });
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
    if (!page || dirty.current) return;
    setDraft({ title: page.title, content: page.content, notes: page.notes });
    draftRevision.current = page.revision;
  }, [page?.id, page?.revision]);
  useEffect(() => {
    if (!dirty.current || !page) return;
    const timer = setTimeout(() => {
      void savePage().catch((err) => setError(err.message));
    }, 600);
    return () => clearTimeout(timer);
  }, [draft.title, draft.content, draft.notes, page?.id]);
  useEffect(() => {
    if (!runtime || !project) return;
    const timer = setInterval(
      () => {
        runtime
          .call<ToolResult>("drawai_project", {
            action: "get",
            project_id: project.id,
          })
          .then(accept)
          .catch((err) => setError(err.message));
      },
      activeTaskCount ? 2500 : 8000,
    );
    return () => clearInterval(timer);
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
    setMobilePanel("");
  }
  async function selectProject(id: string) {
    await savePage();
    const data = await call("drawai_project", {
      action: "get",
      project_id: id,
    });
    dirty.current = false;
    setActiveId(data.project?.slides[0]?.id || "");
    setSelected([]);
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
    const data = await runtime!.call<{
      asset: StudioAsset;
      data_base64: string;
    }>("drawai_artifact", {
      action: "read",
      project_id: project!.id,
      asset_id: asset.id,
    });
    await runtime!.download(asset.filename, asset.mime_type, data.data_base64, {
      project_id: project!.id,
      asset_id: asset.id,
    });
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
  async function startTask(kind: TaskKind) {
    await savePage();
    let requestInstruction = instruction;
    if (kind === "edit_image" && region)
      requestInstruction += `\n修改区域（相对整页，0–1 坐标）：${JSON.stringify(region)}。保持区域外其他内容。`;
    const ids =
      kind === "prepare_reference"
        ? []
        : kind === "export_deck"
          ? project!.slides.map((s) => s.id)
          : chosenPages;
    const data = await call("drawai_task", {
      action: "create",
      kind,
      slide_ids: ids,
      instruction: requestInstruction,
    });
    setRequest(data.task);
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
  const priorImage = images
    .slice()
    .reverse()
    .find((image) => image.id !== currentImage?.id);

  return (
    <div className="studio-app app-root">
      <header className="app-topbar studio-topbar">
        <div className="brand-row">
          <span className="studio-logo">
            <Icon name="slides" size={22} />
          </span>
          <div className="brand-copy">
            <strong>DrawAI</strong>
            <span>视觉制作工作台</span>
          </div>
        </div>
        <nav className="board-mode-switch" aria-label="工作台导航">
          {(
            [
              { id: "project", icon: "slides", label: "PPT 项目" },
              { id: "templates", icon: "grid", label: "模板库" },
              { id: "tasks", icon: "clock", label: "任务" },
            ] as const
          ).map((item) => (
            <button
              key={item.id}
              className={tab === item.id ? "active" : ""}
              aria-current={tab === item.id ? "page" : undefined}
              onClick={() => {
                void perform("save", async () => {
                  await savePage();
                  setTab(item.id);
                });
              }}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
              {item.id === "tasks" && activeTaskCount > 0 && (
                <b className="studio-nav-count">{activeTaskCount}</b>
              )}
            </button>
          ))}
        </nav>
        <div className="studio-connection">
          <span
            className={`studio-status-dot ${runtime?.canSend ? "online" : ""}`}
          />
          <span>
            {runtime?.canSend
              ? "当前 Codex 会话"
              : runtime
                ? "浏览器工作台"
                : "正在连接"}
          </span>
          <IconButton
            icon="refresh"
            title="刷新项目"
            onClick={() => void perform("refresh", boot)}
          />
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
              .map((r) => r.template_id)
              .filter((v): v is string => Boolean(v)) || []
          }
        />
      ) : !project ? (
        <main className="studio-welcome">
          <div className="studio-welcome-mark">
            <Icon name="slides" size={36} />
          </div>
          <span className="studio-eyebrow">DRAWAI WORKBENCH</span>
          <h1>从视觉参考，到可编辑的 PPT</h1>
          <p>
            整理内容，组合模板，让 Codex 生成页面，
            <br />
            再将选定图片转成可继续编辑的 PowerPoint。
          </p>
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
              <Icon name="grid" />
              浏览模板库
            </button>
          </div>
          <div className="studio-welcome-steps">
            <span>
              01 <b>内容与参考</b>
            </span>
            <span>
              02 <b>生成与修改</b>
            </span>
            <span>
              03 <b>可编辑 PPT</b>
            </span>
          </div>
        </main>
      ) : (
        <>
          <div className="studio-projectbar">
            <div className="studio-project-choice">
              <select
                aria-label="选择 PPT 项目"
                value={project.id}
                onChange={(e) =>
                  void perform("switch", () => selectProject(e.target.value))
                }
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title}
                  </option>
                ))}
              </select>
              <IconButton
                title="创建 PPT 项目"
                icon="plus"
                onClick={() => setNewProjectOpen(true)}
              />
              <IconButton
                title="项目设置"
                icon="settings"
                onClick={() => setSettingsOpen(true)}
              />
            </div>
            <span className="studio-project-meta">
              {project.slides.length} 页 · {project.aspect_ratio} ·{" "}
              {project.language === "zh" ? "中文" : "English"}
            </span>
            <div className="studio-project-actions">
              <button
                disabled={Boolean(pending)}
                onClick={() =>
                  void perform("archive", async () => {
                    const data = await call("drawai_artifact", {
                      action: "archive",
                    });
                    await runtime!.download(
                      data.filename!,
                      data.mime_type!,
                      data.data_base64!,
                      { project_id: project.id },
                    );
                  })
                }
              >
                <Icon name="download" />
                项目
              </button>
              <button
                className="primary"
                disabled={
                  Boolean(pending) ||
                  !project.slides.length ||
                  project.slides.some((s) => !s.current_image_id)
                }
                onClick={() =>
                  void perform("export", () => startTask("export_deck"))
                }
              >
                <Icon name="slides" />
                导出整套 PPT
              </button>
            </div>
          </div>
          {tab === "tasks" ? (
            <main className="studio-tasks-page">
              <div className="studio-section-heading">
                <div>
                  <h1>制作任务</h1>
                  <p>查看会话执行进度、结果和需要处理的问题。</p>
                </div>
                <button onClick={() => setTab("project")}>返回页面</button>
              </div>
              {!tasks.length && (
                <div className="studio-empty">
                  <Icon name="clock" size={36} />
                  <h3>还没有制作任务</h3>
                  <p>为页面填写内容、添加参考后，即可开始生成。</p>
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
                              project.slides.find((s) => s.id === id)?.title ||
                              "已移除页面",
                          )
                          .join("、") || "项目参考文件"}
                      </p>
                      <span className="studio-task-message">
                        {task.message}
                      </span>
                      <small>
                        {timeLabel(task.created_at)} ·{" "}
                        {task.artifact_ids.length} 个产物
                      </small>
                      {task.artifact_ids.length > 0 && (
                        <div className="studio-artifact-links">
                          {task.artifact_ids
                            .map((id) =>
                              project.assets.find((a) => a.id === id),
                            )
                            .filter((a): a is StudioAsset => Boolean(a))
                            .map((a) => (
                              <button
                                key={a.id}
                                onClick={() =>
                                  void perform("download", () => download(a))
                                }
                              >
                                <Icon name="download" size={13} />
                                {a.filename}
                              </button>
                            ))}
                        </div>
                      )}
                      {task.events.length > 0 && (
                        <details>
                          <summary>查看进度记录</summary>
                          <ol>
                            {task.events.map((event, i) => (
                              <li key={i}>
                                <time>{timeLabel(event.at)}</time>{" "}
                                {event.message}
                              </li>
                            ))}
                          </ol>
                        </details>
                      )}
                    </div>
                    <div className="studio-task-actions">
                      <button onClick={() => setRequest(task)}>任务请求</button>
                      {activeStates.includes(task.status) && (
                        <button
                          className="danger"
                          disabled={Boolean(pending)}
                          onClick={() =>
                            void perform("cancel", async () => {
                              await call("drawai_task", {
                                action: "cancel",
                                task_id: task.id,
                              });
                            })
                          }
                        >
                          取消
                        </button>
                      )}
                      {["failed", "cancelled"].includes(task.status) && (
                        <button
                          onClick={() =>
                            void perform("retry", async () => {
                              const data = await call("drawai_task", {
                                action: "create",
                                kind: task.kind,
                                slide_ids: task.slide_ids,
                                instruction: task.instruction,
                              });
                              setRequest(data.task);
                              if (runtime!.canSend) await sendTask(data.task!);
                            })
                          }
                        >
                          重新提交
                        </button>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            </main>
          ) : (
            <>
              <div className="studio-mobile-tools">
                <button
                  onClick={() =>
                    setMobilePanel(mobilePanel === "pages" ? "" : "pages")
                  }
                >
                  <Icon name="slides" />
                  页面
                </button>
                <button
                  onClick={() =>
                    setMobilePanel(mobilePanel === "details" ? "" : "details")
                  }
                >
                  <Icon name="settings" />
                  内容与参考
                </button>
              </div>
              <div
                className={`studio-layout ${mobilePanel ? `show-${mobilePanel}` : ""}`}
              >
                <aside className="studio-pages">
                  <div className="studio-panel-head">
                    <strong>页面</strong>
                    <button
                      onClick={() =>
                        setSelected(
                          selected.length === project.slides.length
                            ? []
                            : project.slides.map((s) => s.id),
                        )
                      }
                    >
                      {selected.length ? "取消选择" : "全选"}
                    </button>
                  </div>
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
                              aspectRatio: project.aspect_ratio.replace(
                                ":",
                                "/",
                              ),
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
                                <span>
                                  {String(index + 1).padStart(2, "0")}
                                </span>
                                <b>{item.title}</b>
                              </div>
                            )}
                          </div>
                          <div className="studio-page-label">
                            <span>{String(index + 1).padStart(2, "0")}</span>
                            <strong>{item.title}</strong>
                            {item.current_pptx_id && (
                              <span
                                className="studio-page-ready"
                                title="已有可编辑 PPT"
                              >
                                <Icon name="check" size={13} />
                              </span>
                            )}
                          </div>
                        </button>
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
                        <div className="studio-segment">
                          <button
                            className={
                              previewMode === "image" ? "selected" : ""
                            }
                            onClick={() => setPreviewMode("image")}
                          >
                            页面图片
                          </button>
                          <button
                            className={
                              previewMode === "editable" ? "selected" : ""
                            }
                            disabled={!pptx}
                            onClick={() => setPreviewMode("editable")}
                          >
                            可编辑结果
                          </button>
                        </div>
                        <div className="studio-canvas-tools">
                          <button
                            className={compare ? "selected" : ""}
                            disabled={!priorImage || !currentImage}
                            onClick={() => setCompare(!compare)}
                          >
                            <Icon name="compare" />
                            对比版本
                          </button>
                          <button
                            className={marking ? "selected" : ""}
                            disabled={!currentImage || previewMode !== "image"}
                            onClick={() => {
                              setMarking(!marking);
                              setRegion(undefined);
                            }}
                          >
                            <Icon name="crop" />
                            标记区域
                          </button>
                          {pptx && previewMode === "editable" && (
                            <button
                              onClick={() =>
                                void perform("download", () => download(pptx))
                              }
                            >
                              <Icon name="download" />
                              下载 PPTX
                            </button>
                          )}
                          {output && (
                            <IconButton
                              title="下载预览图片"
                              icon="download"
                              onClick={() =>
                                void perform("download", () => download(output))
                              }
                            />
                          )}
                        </div>
                      </div>
                      <div className="studio-canvas-area">
                        {page.content_changed && (
                          <div className="studio-stale-note">
                            页面内容已修改，可重新生成以更新图片。
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
                              aspectRatio: project.aspect_ratio.replace(
                                ":",
                                "/",
                              ),
                            }}
                            onPointerDown={(e) => {
                              if (!marking) return;
                              const rect =
                                e.currentTarget.getBoundingClientRect();
                              markStart.current = {
                                x: (e.clientX - rect.left) / rect.width,
                                y: (e.clientY - rect.top) / rect.height,
                              };
                              e.currentTarget.setPointerCapture(e.pointerId);
                            }}
                            onPointerMove={(e) => {
                              if (!markStart.current) return;
                              const rect =
                                e.currentTarget.getBoundingClientRect();
                              const x = Math.max(
                                0,
                                Math.min(
                                  1,
                                  (e.clientX - rect.left) / rect.width,
                                ),
                              );
                              const y = Math.max(
                                0,
                                Math.min(
                                  1,
                                  (e.clientY - rect.top) / rect.height,
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
                                    previewMode === "editable"
                                      ? "slides"
                                      : "image"
                                  }
                                  size={40}
                                />
                                <h3>
                                  {previewMode === "editable"
                                    ? "可编辑文件已生成"
                                    : "这一页，准备表达什么？"}
                                </h3>
                                <p>
                                  {previewMode === "editable"
                                    ? "可以下载 PPTX；渲染预览登记后会显示在这里。"
                                    : "填写内容与参考，交给当前 Codex 会话生成。"}
                                </p>
                                {previewMode === "image" && (
                                  <button
                                    onClick={() => imageRef.current?.click()}
                                  >
                                    <Icon name="upload" />
                                    导入已有图片
                                  </button>
                                )}
                                {previewMode === "editable" && pptx && (
                                  <button
                                    onClick={() =>
                                      void perform("download", () =>
                                        download(pptx),
                                      )
                                    }
                                  >
                                    下载 PPTX
                                  </button>
                                )}
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
                              ? "PowerPoint 原生可编辑对象"
                              : currentImage
                                ? `${images.length} 个图片版本`
                                : project.aspect_ratio}
                          </span>
                        </div>
                      </div>
                      {images.length > 0 && (
                        <div className="studio-versions">
                          <span>图片版本</span>
                          {images.map((asset, i) => (
                            <button
                              key={asset.id}
                              title={`使用版本 ${i + 1}`}
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
                                alt={`版本 ${i + 1}`}
                              />
                              <span>V{i + 1}</span>
                            </button>
                          ))}
                        </div>
                      )}
                      <div className="studio-action-composer">
                        <label htmlFor="studio-instruction">
                          {region ? "描述标记区域的修改" : "补充制作要求"}
                        </label>
                        <textarea
                          id="studio-instruction"
                          value={instruction}
                          onChange={(e) => setInstruction(e.target.value)}
                          placeholder="例如：沿用模板的配色，把方法分成三个步骤；文字使用中文。"
                          rows={2}
                        />
                        <div className="studio-action-row">
                          <span>
                            {selected.length
                              ? `已选 ${selected.length} 页`
                              : "当前页面"}
                            {region && (
                              <button onClick={() => setRegion(undefined)}>
                                清除区域
                              </button>
                            )}
                          </span>
                          <div>
                            <button
                              disabled={
                                Boolean(pending) ||
                                !currentImage ||
                                !instruction.trim()
                              }
                              onClick={() =>
                                void perform("edit", () =>
                                  startTask("edit_image"),
                                )
                              }
                            >
                              <Icon name="image" />
                              修改图片
                            </button>
                            <button
                              disabled={
                                Boolean(pending) ||
                                !chosenPages.length ||
                                chosenPages.some(
                                  (id) =>
                                    !project.slides.find((s) => s.id === id)
                                      ?.current_image_id,
                                )
                              }
                              onClick={() =>
                                void perform("convert", () =>
                                  startTask("convert"),
                                )
                              }
                            >
                              <Icon name="slides" />
                              转可编辑 PPT
                            </button>
                            <button
                              className="primary"
                              disabled={Boolean(pending) || !chosenPages.length}
                              onClick={() =>
                                void perform("generate", () =>
                                  startTask("generate"),
                                )
                              }
                            >
                              <Icon name="sparkle" />
                              {pending === "generate"
                                ? "准备任务…"
                                : "生成图片"}
                            </button>
                          </div>
                        </div>
                      </div>
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
                    <strong>内容与参考</strong>
                    {page && (
                      <span className="studio-inspector-tools">
                        <IconButton
                          title="上移页面"
                          icon="arrowUp"
                          disabled={Boolean(pending)}
                          onClick={() =>
                            void perform("move", () => movePage(-1))
                          }
                        />
                        <IconButton
                          title="下移页面"
                          icon="arrowDown"
                          disabled={Boolean(pending)}
                          onClick={() =>
                            void perform("move", () => movePage(1))
                          }
                        />
                        <IconButton
                          title="复制页面"
                          icon="copy"
                          onClick={() =>
                            void perform("duplicate", async () => {
                              await savePage();
                              const d = await call("drawai_project", {
                                action: "duplicate_slide",
                                slide_id: page.id,
                              });
                              dirty.current = false;
                              setActiveId(d.slide_id!);
                            })
                          }
                        />
                        <IconButton
                          title="删除页面"
                          icon="trash"
                          onClick={() => setDeleteTarget("slide")}
                        />
                      </span>
                    )}
                  </div>
                  <div className="studio-inspector-scroll">
                    {page && (
                      <section className="studio-inspector-section">
                        <label>
                          页面标题
                          <input
                            value={draft.title}
                            onChange={(e) =>
                              updateDraft("title", e.target.value)
                            }
                            onBlur={() => void perform("save", savePage)}
                          />
                        </label>
                        <label>
                          页面内容
                          <textarea
                            rows={7}
                            value={draft.content}
                            onChange={(e) =>
                              updateDraft("content", e.target.value)
                            }
                            onBlur={() => void perform("save", savePage)}
                            placeholder="写下这一页的核心观点、准确文字和数据。"
                          />
                        </label>
                        <label>
                          页面备注
                          <textarea
                            rows={2}
                            value={draft.notes}
                            onChange={(e) =>
                              updateDraft("notes", e.target.value)
                            }
                            onBlur={() => void perform("save", savePage)}
                            placeholder="听众、讲解重点或排版要求"
                          />
                        </label>
                      </section>
                    )}
                    <section className="studio-inspector-section">
                      <div className="studio-section-label">
                        <strong>参考与材料</strong>
                        <span>{project.references.length}</span>
                      </div>
                      <div className="studio-reference-actions">
                        <button
                          onClick={() => {
                            void perform("save", async () => {
                              await savePage();
                              setTab("templates");
                            });
                          }}
                        >
                          <Icon name="grid" />
                          选择模板
                        </button>
                        <button onClick={() => upload("content")}>
                          <Icon name="upload" />
                          上传材料
                        </button>
                        <button onClick={() => upload("ppt_template")}>
                          <Icon name="slides" />
                          上传 PPT 模板
                        </button>
                      </div>
                      {!project.references.length && (
                        <p className="studio-muted">
                          可以同时使用库中的结构参考、视觉风格和自己的 PPT
                          模板。
                        </p>
                      )}
                      <div className="studio-reference-list">
                        {project.references.map((ref) => (
                          <article className="studio-reference" key={ref.id}>
                            <div className="studio-reference-head">
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
                                      ref.template.assets[0].image_urls
                                        ?.thumb ||
                                      ref.template.assets[0].original_url
                                    }
                                    alt={ref.name}
                                  />
                                ) : (
                                  <Icon name="file" size={23} />
                                )}
                              </div>
                              <strong title={ref.name}>{ref.name}</strong>
                              <IconButton
                                title={`移除参考 ${ref.name}`}
                                icon="close"
                                onClick={() =>
                                  void perform("remove-ref", async () => {
                                    await call("drawai_reference", {
                                      action: "remove",
                                      reference_id: ref.id,
                                    });
                                  })
                                }
                              />
                            </div>
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
                                {Object.entries(roleLabels).map(
                                  ([key, text]) => (
                                    <option key={key} value={key}>
                                      {text}
                                    </option>
                                  ),
                                )}
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
                              <small>
                                用于：
                                {ref.slide_ids
                                  .map(
                                    (id) =>
                                      project.slides.find((s) => s.id === id)
                                        ?.title,
                                  )
                                  .join("、")}
                              </small>
                            )}
                          </article>
                        ))}
                      </div>
                      {project.references.some(
                        (r) => r.role === "ppt_template",
                      ) && (
                        <button
                          className="studio-text-button"
                          disabled={Boolean(pending)}
                          onClick={() =>
                            void perform("prepare", () =>
                              startTask("prepare_reference"),
                            )
                          }
                        >
                          让 Codex 解析 PPT 模板并生成参考预览
                        </button>
                      )}
                    </section>
                    <section className="studio-inspector-section">
                      <div className="studio-section-label">
                        <strong>近期任务</strong>
                        <button onClick={() => setTab("tasks")}>全部</button>
                      </div>
                      {tasks.slice(0, 3).map((task) => (
                        <button
                          className="studio-recent-task"
                          key={task.id}
                          onClick={() => setRequest(task)}
                        >
                          <Icon name="clock" size={15} />
                          <span>{taskLabels[task.kind]}</span>
                          <small className={task.status}>
                            {statusLabels[task.status]}
                          </small>
                        </button>
                      ))}
                      {!tasks.length && (
                        <p className="studio-muted">
                          生成和转换进度会显示在这里。
                        </p>
                      )}
                    </section>
                  </div>
                </aside>
              </div>
            </>
          )}
        </>
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
            onSubmit={(e) => {
              e.preventDefault();
              const values = Object.fromEntries(new FormData(e.currentTarget));
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
            {!runtime?.canSend && (
              <div className="studio-notice">
                在 Codex
                插件内可直接发送。当前浏览器视图可复制任务请求到会话执行。
              </div>
            )}
            <label>
              会话任务请求
              <textarea readOnly value={request.prompt} rows={7} />
            </label>
            <p className="studio-muted">
              任务已保存，生成和转换的真实结果会回到本项目。
            </p>
          </div>
          <footer>
            <button
              onClick={() =>
                void perform("copy", async () => {
                  await navigator.clipboard.writeText(request.prompt);
                  setNotice("任务请求已复制");
                })
              }
            >
              <Icon name="copy" />
              复制请求
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
                  await call("drawai_project", {
                    action:
                      deleteTarget === "project" ? "delete" : "delete_slide",
                    slide_id: activeId,
                  });
                  dirty.current = false;
                  setDeleteTarget(undefined);
                  if (deleteTarget === "project") {
                    setProject(undefined);
                    setActiveId("");
                    await boot();
                  } else {
                    setActiveId("");
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
