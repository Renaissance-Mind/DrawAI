import {
  mkdir,
  readFile,
  writeFile,
  rename,
  rm,
  stat,
  realpath,
} from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import { randomUUID, createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { unzipSync, zipSync, strToU8 } from "fflate";
import { findTemplate } from "./catalog.mjs";

const ROOT = path.resolve(fileURLToPath(new URL("../../..", import.meta.url)));
const now = () => new Date().toISOString();
const uid = (prefix) =>
  `${prefix}_${randomUUID().replaceAll("-", "").slice(0, 16)}`;
const digest = (bytes) => createHash("sha256").update(bytes).digest("hex");
const ACTIVE = new Set(["draft", "submitted", "running"]);
const ROLES = new Set(["content", "structure", "style", "ppt_template"]);
const TASK_KINDS = new Set([
  "generate",
  "edit_image",
  "convert",
  "prepare_reference",
  "export_deck",
]);
const MIME = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".svg": "image/svg+xml",
  ".pdf": "application/pdf",
  ".pptx":
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  ".json": "application/json",
  ".md": "text/markdown",
  ".txt": "text/plain",
  ".zip": "application/zip",
};

function required(value, label) {
  if (typeof value !== "string" || !value.trim())
    throw new Error(`${label} is required`);
  return value.trim();
}
function lookup(items, id, label) {
  const value = items.find((item) => item.id === id);
  if (!value) throw new Error(`${label} not found: ${id}`);
  return value;
}
function clone(value) {
  return structuredClone(value);
}
function fileInfo(bytes, name) {
  const ext = path.extname(name).toLowerCase();
  if (!MIME[ext]) throw new Error(`Unsupported file type: ${ext}`);
  if (!bytes.length || bytes.length > 48 * 1024 * 1024)
    throw new Error("File must be between 1 byte and 48 MB");
  if (
    ext === ".png" &&
    !bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))
  )
    throw new Error("Invalid PNG file");
  if ([".jpg", ".jpeg"].includes(ext) && bytes.readUInt16BE(0) !== 0xffd8)
    throw new Error("Invalid JPEG file");
  if (ext === ".pdf" && !bytes.subarray(0, 5).equals(Buffer.from("%PDF-")))
    throw new Error("Invalid PDF file");
  if (ext === ".svg" && !/<svg[\s>]/i.test(bytes.toString("utf8")))
    throw new Error("Invalid SVG file");
  if (ext === ".pptx") {
    const entries = unzipSync(bytes);
    if (!entries["ppt/presentation.xml"])
      throw new Error("File is not a PowerPoint presentation");
  }
  return { mime_type: MIME[ext], size: bytes.length, sha256: digest(bytes) };
}
function slide(title = "新页面") {
  return {
    id: uid("slide"),
    title,
    content: "",
    notes: "",
    reference_ids: [],
    current_image_id: null,
    current_pptx_id: null,
    revision: 1,
  };
}

export class StudioStore {
  constructor(
    root = process.env.DRAWAI_STUDIO_HOME ||
      path.join(os.homedir(), ".local/share/drawai/studio"),
  ) {
    this.root = path.resolve(root);
  }
  async ready() {
    await mkdir(this.root, { recursive: true });
  }
  projectPath(id) {
    if (!/^project_[a-f0-9]{16}$/.test(id))
      throw new Error("Invalid project id");
    return path.join(this.root, id);
  }
  async read(id) {
    return JSON.parse(
      await readFile(path.join(this.projectPath(id), "project.json"), "utf8"),
    );
  }
  async write(project) {
    const folder = this.projectPath(project.id);
    await mkdir(folder, { recursive: true });
    const temp = path.join(folder, `project.${randomUUID()}.tmp`);
    await writeFile(temp, `${JSON.stringify(project, null, 2)}\n`);
    await rename(temp, path.join(folder, "project.json"));
  }
  async mutate(id, callback) {
    const folder = this.projectPath(id);
    const lock = path.join(folder, ".write-lock");
    const deadline = Date.now() + 8000;
    for (;;) {
      try {
        await mkdir(lock);
        break;
      } catch (error) {
        if (error.code !== "EEXIST" || Date.now() > deadline) throw error;
        await new Promise((resolve) => setTimeout(resolve, 35));
      }
    }
    try {
      const project = await this.read(id);
      const result = await callback(project);
      project.updated_at = now();
      project.revision++;
      await this.write(project);
      return { project, ...result };
    } finally {
      await rm(lock, { recursive: true });
    }
  }
  async list() {
    await this.ready();
    const { readdir } = await import("node:fs/promises");
    const entries = await readdir(this.root, { withFileTypes: true });
    const projects = await Promise.all(
      entries
        .filter(
          (entry) =>
            entry.isDirectory() && /^project_[a-f0-9]{16}$/.test(entry.name),
        )
        .map((entry) => this.read(entry.name)),
    );
    return {
      projects: projects
        .sort((a, b) => b.updated_at.localeCompare(a.updated_at))
        .map((p) => ({
          id: p.id,
          title: p.title,
          updated_at: p.updated_at,
          slide_count: p.slides.length,
          task_count: p.tasks.filter((t) => ACTIVE.has(t.status)).length,
        })),
    };
  }
  async create({ title, source_directory = "" }) {
    await this.ready();
    const project = {
      schema: "drawai.studio.project.v1",
      id: uid("project"),
      title: required(title, "Project title"),
      brief: "",
      language: "zh",
      aspect_ratio: "16:9",
      style_notes: "",
      source_directory,
      revision: 1,
      input_revision: 1,
      created_at: now(),
      updated_at: now(),
      slides: [slide("封面")],
      references: [],
      assets: [],
      tasks: [],
    };
    await this.write(project);
    return { project };
  }
  async projectAction(args) {
    const { action, project_id } = args;
    if (action === "list") return this.list();
    if (action === "create") return this.create(args);
    if (action === "get") return { project: await this.read(project_id) };
    if (action === "delete") {
      const project = await this.read(project_id);
      if (project.tasks.some((t) => ACTIVE.has(t.status)))
        throw new Error("Cancel active tasks before deleting this project");
      await mkdir(path.join(this.root, ".trash"), { recursive: true });
      await rename(
        this.projectPath(project_id),
        path.join(this.root, ".trash", `${project_id}-${Date.now()}`),
      );
      return { deleted: project_id };
    }
    return this.mutate(project_id, async (p) => {
      if (action === "update") {
        const before = JSON.stringify([
          p.brief,
          p.language,
          p.aspect_ratio,
          p.style_notes,
        ]);
        for (const key of [
          "title",
          "brief",
          "language",
          "aspect_ratio",
          "style_notes",
        ])
          if (args[key] !== undefined) p[key] = String(args[key]);
        required(p.title, "Project title");
        if (!["16:9", "4:3", "3:2"].includes(p.aspect_ratio))
          throw new Error("Unsupported slide size");
        if (
          JSON.stringify([
            p.brief,
            p.language,
            p.aspect_ratio,
            p.style_notes,
          ]) !== before
        ) {
          p.input_revision = (p.input_revision || 1) + 1;
          p.slides.forEach((page) => {
            if (page.current_image_id) page.content_changed = true;
          });
        }
      } else if (action === "add_slide") {
        const page = slide(args.title || `第 ${p.slides.length + 1} 页`);
        if (args.content) page.content = String(args.content);
        p.slides.push(page);
        return { slide_id: page.id };
      } else if (action === "update_slide") {
        const page = lookup(p.slides, args.slide_id, "Slide");
        if (
          args.expected_revision !== undefined &&
          page.revision !== args.expected_revision
        )
          throw new Error(
            "This slide changed in another window. Refresh before saving.",
          );
        let changed = false;
        for (const key of ["title", "content", "notes"])
          if (args[key] !== undefined && page[key] !== args[key]) {
            page[key] = String(args[key]);
            changed = true;
          }
        if (changed) {
          page.revision++;
          page.content_changed = Boolean(page.current_image_id);
        }
      } else if (action === "duplicate_slide") {
        const original = lookup(p.slides, args.slide_id, "Slide");
        const page = {
          ...clone(original),
          id: uid("slide"),
          title: `${original.title} · 副本`,
          current_image_id: null,
          current_pptx_id: null,
          revision: 1,
        };
        const originalPptx = p.assets.find(
          (a) => a.id === original.current_pptx_id,
        );
        const sources = p.assets.filter(
          (a) =>
            a.id === original.current_image_id ||
            a.id === original.current_pptx_id ||
            (a.slide_id === original.id &&
              originalPptx &&
              a.task_id === originalPptx.task_id &&
              ["preview", "svg", "document"].includes(a.kind)),
        );
        const imageIds = new Map();
        for (const source of sources.sort(
          (a, b) => Number(b.kind === "image") - Number(a.kind === "image"),
        )) {
          const copied = await this.persistAsset(
            p,
            await readFile(await this.assetPath(p, source.id)),
            source.filename,
            {
              kind: source.kind,
              slide_id: page.id,
              task_id: null,
              copied_from: source.id,
              source_image_id: imageIds.get(source.source_image_id) || null,
            },
          );
          if (source.kind === "image") {
            page.current_image_id = copied.id;
            imageIds.set(source.id, copied.id);
          }
          if (source.kind === "pptx") page.current_pptx_id = copied.id;
        }
        p.references.forEach((ref) => {
          if (ref.slide_ids.includes(original.id)) ref.slide_ids.push(page.id);
        });
        p.slides.splice(p.slides.indexOf(original) + 1, 0, page);
        return { slide_id: page.id };
      } else if (action === "delete_slide") {
        lookup(p.slides, args.slide_id, "Slide");
        if (
          p.tasks.some(
            (t) => ACTIVE.has(t.status) && t.slide_ids.includes(args.slide_id),
          )
        )
          throw new Error("Cancel this slide’s active tasks first");
        p.slides = p.slides.filter((s) => s.id !== args.slide_id);
      } else if (action === "reorder") {
        if (
          !Array.isArray(args.slide_ids) ||
          args.slide_ids.length !== p.slides.length ||
          new Set(args.slide_ids).size !== p.slides.length
        )
          throw new Error("Provide every slide id exactly once");
        p.slides = args.slide_ids.map((id) => lookup(p.slides, id, "Slide"));
      } else throw new Error(`Unknown project action: ${action}`);
      return {};
    });
  }
  async persistAsset(project, bytes, filename, fields = {}) {
    const name = path
      .basename(required(filename, "Filename"))
      .replace(/[\x00-\x1f]/g, "_");
    const info = fileInfo(bytes, name);
    const asset = {
      id: uid("asset"),
      filename: name,
      ...info,
      created_at: now(),
      ...fields,
    };
    asset.relative_path = path.join(
      "assets",
      `${asset.id}${path.extname(name).toLowerCase()}`,
    );
    await mkdir(path.join(this.projectPath(project.id), "assets"), {
      recursive: true,
    });
    await writeFile(
      path.join(this.projectPath(project.id), asset.relative_path),
      bytes,
    );
    project.assets.push(asset);
    return asset;
  }
  async assetPath(project, id) {
    const asset = lookup(project.assets, id, "Asset");
    const resolved = await realpath(
      path.join(this.projectPath(project.id), asset.relative_path),
    );
    const root = await realpath(this.projectPath(project.id));
    if (!resolved.startsWith(root + path.sep))
      throw new Error("Asset resolves outside this project");
    return resolved;
  }
  async readAsset(projectId, assetId) {
    const project = await this.read(projectId);
    const asset = lookup(project.assets, assetId, "Asset");
    const bytes = await readFile(await this.assetPath(project, assetId));
    return { asset, data_base64: bytes.toString("base64") };
  }
  async referenceAction(args) {
    return this.mutate(args.project_id, async (p) => {
      p.input_revision = (p.input_revision || 1) + 1;
      if (args.action === "remove") {
        lookup(p.references, args.reference_id, "Reference");
        p.references = p.references.filter((r) => r.id !== args.reference_id);
        p.slides.forEach((s) => {
          s.reference_ids = s.reference_ids.filter(
            (id) => id !== args.reference_id,
          );
        });
        return {};
      }
      if (args.action === "update") {
        const ref = lookup(p.references, args.reference_id, "Reference");
        if (args.role && !ROLES.has(args.role))
          throw new Error("Invalid reference role");
        if (args.role) ref.role = args.role;
        if (args.notes !== undefined) ref.notes = String(args.notes);
        if (args.slide_ids !== undefined)
          ref.slide_ids = args.slide_ids.map(
            (id) => lookup(p.slides, id, "Slide").id,
          );
        return {};
      }
      const role = args.role || "content";
      if (!ROLES.has(role)) throw new Error("Invalid reference role");
      const ref = {
        id: uid("ref"),
        role,
        notes: "",
        slide_ids: args.slide_ids || [],
        asset_ids: [],
        created_at: now(),
      };
      ref.slide_ids.forEach((id) => lookup(p.slides, id, "Slide"));
      if (args.action === "template") {
        const template = await findTemplate(
          required(args.template_id, "Template id"),
        );
        if (
          p.references.some(
            (r) => r.template_id === template.id && r.role === role,
          )
        )
          throw new Error("This template is already selected for that role");
        Object.assign(ref, {
          name: template.name,
          template_id: template.id,
          recipe: template.prompt_recipe,
          template,
        });
      } else if (args.action === "upload") {
        const bytes = Buffer.from(
          required(args.data_base64, "File data"),
          "base64",
        );
        const asset = await this.persistAsset(p, bytes, args.filename, {
          kind: "reference",
        });
        ref.name = asset.filename;
        ref.asset_ids.push(asset.id);
        if (asset.filename.toLowerCase().endsWith(".pptx")) {
          const entries = unzipSync(bytes);
          const key = Object.keys(entries).find((key) =>
            /^docProps\/thumbnail\.(png|jpe?g)$/i.test(key),
          );
          if (key) {
            const preview = await this.persistAsset(
              p,
              Buffer.from(entries[key]),
              path.basename(key),
              { kind: "reference_preview", parent_asset_id: asset.id },
            );
            ref.preview_asset_id = preview.id;
          }
        } else if (asset.mime_type.startsWith("image/"))
          ref.preview_asset_id = asset.id;
      } else throw new Error(`Unknown reference action: ${args.action}`);
      p.references.push(ref);
      return { reference_id: ref.id };
    });
  }
  async materializeReferences(project, references) {
    for (const ref of references) {
      if (!ref.template) continue;
      for (const source of ref.template.assets) {
        const existing = project.assets.find(
          (a) => a.sha256 === source.sha256 && a.kind === "reference",
        );
        if (existing) {
          if (!ref.asset_ids.includes(existing.id))
            ref.asset_ids.push(existing.id);
          continue;
        }
        const url = new URL(source.original_url);
        if (
          url.protocol !== "https:" ||
          url.hostname !== "assets.visualize.renaissancemind.ai"
        )
          throw new Error("Unexpected template asset host");
        const response = await fetch(url, {
          signal: AbortSignal.timeout(45000),
          redirect: "error",
        });
        if (!response.ok)
          throw new Error(`Template download failed: HTTP ${response.status}`);
        const bytes = Buffer.from(await response.arrayBuffer());
        if (digest(bytes) !== source.sha256)
          throw new Error("Template image checksum mismatch");
        const asset = await this.persistAsset(project, bytes, source.filename, {
          kind: "reference",
          source_url: source.original_url,
        });
        ref.asset_ids.push(asset.id);
        ref.preview_asset_id ??= asset.id;
      }
    }
  }
  async createTask(args) {
    return this.mutate(args.project_id, async (p) => {
      if (!TASK_KINDS.has(args.kind)) throw new Error("Invalid task kind");
      const ids = args.slide_ids || [];
      const pages = ids.map((id) => lookup(p.slides, id, "Slide"));
      if (!pages.length && args.kind !== "prepare_reference")
        throw new Error("Choose at least one slide");
      if (new Set(ids).size !== ids.length)
        throw new Error("Duplicate slide ids");
      if (
        ["edit_image", "convert", "export_deck"].includes(args.kind) &&
        pages.some((s) => !s.current_image_id)
      )
        throw new Error("Every selected page needs an image first");
      if (
        p.tasks.some(
          (t) =>
            ACTIVE.has(t.status) &&
            t.kind === args.kind &&
            t.slide_ids.some((id) => ids.includes(id)),
        )
      )
        throw new Error("These pages already have an active task of this kind");
      const refs = p.references.filter(
        (r) =>
          args.kind === "prepare_reference" ||
          !r.slide_ids.length ||
          r.slide_ids.some((id) => ids.includes(id)),
      );
      await this.materializeReferences(p, refs);
      const task = {
        id: uid("task"),
        kind: args.kind,
        status: "draft",
        slide_ids: ids,
        instruction: String(args.instruction || ""),
        project_input_revision: p.input_revision || 1,
        created_at: now(),
        updated_at: now(),
        message: "等待发送到当前会话",
        artifact_ids: [],
        slide_revisions: Object.fromEntries(
          pages.map((s) => [s.id, s.revision]),
        ),
        source_image_ids: Object.fromEntries(
          pages.map((s) => [s.id, s.current_image_id]),
        ),
        events: [],
      };
      const taskDir = path.join(this.projectPath(p.id), "tasks", task.id);
      await mkdir(taskDir, { recursive: true });
      const references = await Promise.all(
        refs.map(async (r) => ({
          id: r.id,
          name: r.name,
          role: r.role,
          notes: r.notes,
          slide_ids: r.slide_ids,
          recipe: r.recipe || "",
          files: await Promise.all(
            r.asset_ids.map((id) => this.assetPath(p, id)),
          ),
        })),
      );
      const snapshots = await Promise.all(
        pages.map(async (s) => {
          const pptx = p.assets.find((asset) => asset.id === s.current_pptx_id);
          const document =
            pptx &&
            p.assets
              .slice()
              .reverse()
              .find(
                (asset) =>
                  asset.slide_id === s.id &&
                  asset.kind === "document" &&
                  asset.task_id === pptx.task_id,
              );
          return {
            ...clone(s),
            source_image_path: s.current_image_id
              ? await this.assetPath(p, s.current_image_id)
              : null,
            editable_pptx_path: pptx ? await this.assetPath(p, pptx.id) : null,
            editable_document_path: document
              ? await this.assetPath(p, document.id)
              : null,
          };
        }),
      );
      const request = {
        schema: "drawai.studio.task.v1",
        project_id: p.id,
        task_id: task.id,
        kind: task.kind,
        instruction: task.instruction,
        project: {
          title: p.title,
          brief: p.brief,
          aspect_ratio: p.aspect_ratio,
          language: p.language,
          style_notes: p.style_notes,
          source_directory: p.source_directory,
        },
        slides: snapshots,
        references,
        output_directory: path.join(taskDir, "outputs"),
        skills: {
          studio: path.join(ROOT, "skills/drawai-studio/SKILL.md"),
          reconstruction: path.join(ROOT, "skills/drawai-simple/SKILL.md"),
          ppt: path.join(ROOT, "skills/drawai-ppt/SKILL.md"),
        },
      };
      await mkdir(request.output_directory, { recursive: true });
      task.request_path = path.join(taskDir, "request.json");
      await writeFile(
        task.request_path,
        `${JSON.stringify(request, null, 2)}\n`,
      );
      task.prompt = `请执行 DrawAI 工作台任务 ${task.id}。先读取 ${request.skills.studio}，再读取任务文件 ${task.request_path}。在当前会话完成 ${task.kind}，使用任务内真实参考与材料；生成使用当前会话的图像生成工具，转可编辑 PPT 使用现有 drawai-simple 与 drawai-ppt skill。通过 DrawAI 工具或配套 CLI 更新进度、登记真实产物并完成检查。`;
      p.tasks.unshift(task);
      return { task, request };
    });
  }
  async taskAction(args) {
    if (args.action === "create") return this.createTask(args);
    if (args.action === "get") {
      const p = await this.read(args.project_id);
      const task = lookup(p.tasks, args.task_id, "Task");
      return {
        task,
        request: JSON.parse(await readFile(task.request_path, "utf8")),
      };
    }
    return this.mutate(args.project_id, async (p) => {
      const task = lookup(p.tasks, args.task_id, "Task");
      if (args.action === "cancel") {
        if (["completed", "failed", "cancelled"].includes(task.status))
          return { task };
        task.status = "cancelled";
        task.message = "已取消；当前会话中的执行请同时停止";
      } else if (args.action === "update") {
        const status = args.status || task.status;
        // A host can start work before acknowledging the UI message. Never regress
        // a running or completed task to submitted when that acknowledgment arrives.
        if (status === "submitted" && task.status !== "draft") return { task };
        if (
          ![
            "draft",
            "submitted",
            "running",
            "completed",
            "failed",
            "cancelled",
          ].includes(status)
        )
          throw new Error("Invalid task status");
        if (
          ["cancelled", "completed"].includes(task.status) &&
          status !== task.status
        )
          throw new Error("This task is already finished");
        if (status === "completed") {
          const assets = p.assets.filter((a) =>
            task.artifact_ids.includes(a.id),
          );
          const expectedKind = ["generate", "edit_image"].includes(task.kind)
            ? "image"
            : "pptx";
          if (task.kind === "export_deck") {
            if (!assets.some((a) => a.kind === "pptx"))
              throw new Error("Register the exported deck before completing");
          } else if (task.kind === "prepare_reference") {
            if (!assets.some((a) => a.kind === "reference_preview"))
              throw new Error(
                "Register reference preview images before completing",
              );
          } else if (
            task.slide_ids.some(
              (id) =>
                !assets.some(
                  (a) => a.slide_id === id && a.kind === expectedKind,
                ),
            )
          )
            throw new Error("Some selected pages have no verified result");
          for (const asset of assets) {
            const bytes = await readFile(await this.assetPath(p, asset.id));
            if (digest(bytes) !== asset.sha256)
              throw new Error("A registered artifact changed on disk");
          }
        }
        task.status = status;
        task.message = String(args.message || task.message);
      } else throw new Error(`Unknown task action: ${args.action}`);
      task.updated_at = now();
      task.events.push({
        at: now(),
        status: task.status,
        message: task.message,
      });
      return { task };
    });
  }
  async artifactAction(args) {
    if (args.action === "read")
      return this.readAsset(args.project_id, args.asset_id);
    if (args.action === "archive") {
      const p = await this.read(args.project_id);
      const files = { "project.json": strToU8(JSON.stringify(p, null, 2)) };
      for (const asset of p.assets)
        files[asset.relative_path] = new Uint8Array(
          await readFile(await this.assetPath(p, asset.id)),
        );
      for (const task of p.tasks) {
        files[`tasks/${task.id}/request.json`] = new Uint8Array(
          await readFile(
            path.join(this.projectPath(p.id), "tasks", task.id, "request.json"),
          ),
        );
      }
      const bytes = zipSync(files, { level: 1 });
      return {
        filename: `${p.title.replace(/[^\p{L}\p{N}._-]/gu, "_")}.drawai.zip`,
        mime_type: MIME[".zip"],
        data_base64: Buffer.from(bytes).toString("base64"),
      };
    }
    return this.mutate(args.project_id, async (p) => {
      if (args.action === "select") {
        const asset = lookup(p.assets, args.asset_id, "Asset");
        const page = lookup(p.slides, args.slide_id, "Slide");
        if (asset.slide_id !== page.id || asset.kind !== "image")
          throw new Error("Choose an image belonging to this page");
        if (page.current_image_id === asset.id) return {};
        const converted = p.assets
          .slice()
          .reverse()
          .find(
            (a) =>
              a.kind === "pptx" &&
              a.slide_id === page.id &&
              a.source_image_id === asset.id &&
              (a.source_slide_revision ??
                p.tasks.find((t) => t.id === a.task_id)?.slide_revisions[
                  page.id
                ]) === page.revision,
          );
        page.current_image_id = asset.id;
        page.current_pptx_id = converted?.id || null;
        page.content_changed = false;
        return {};
      }
      if (args.action === "import_image") {
        const page = lookup(p.slides, args.slide_id, "Slide");
        const asset = await this.persistAsset(
          p,
          Buffer.from(required(args.data_base64, "Image data"), "base64"),
          args.filename,
          {
            kind: "image",
            slide_id: page.id,
            task_id: null,
            source: "uploaded",
          },
        );
        if (!asset.mime_type.startsWith("image/"))
          throw new Error("Upload an image for this page");
        page.current_image_id = asset.id;
        page.current_pptx_id = null;
        page.content_changed = false;
        return { asset };
      }
      if (args.action !== "register")
        throw new Error(`Unknown artifact action: ${args.action}`);
      const task = lookup(p.tasks, args.task_id, "Task");
      if (["cancelled", "completed"].includes(task.status))
        throw new Error("Cannot attach results to a finished task");
      const kind = args.kind;
      if (
        ![
          "image",
          "svg",
          "pptx",
          "preview",
          "reference_preview",
          "document",
          "report",
        ].includes(kind)
      )
        throw new Error("Invalid artifact kind");
      const source = path.resolve(required(args.source_path, "Artifact path"));
      const info = await stat(source);
      if (!info.isFile()) throw new Error("Artifact must be a regular file");
      const bytes = await readFile(source);
      if (kind === "pptx" && path.extname(source).toLowerCase() !== ".pptx")
        throw new Error("PPTX result must be a .pptx file");
      if (kind === "svg" && path.extname(source).toLowerCase() !== ".svg")
        throw new Error("SVG result must be an .svg file");
      if (
        ["image", "preview", "reference_preview"].includes(kind) &&
        ![".png", ".jpg", ".jpeg", ".webp"].includes(
          path.extname(source).toLowerCase(),
        )
      )
        throw new Error(
          "Image results and previews must be raster image files",
        );
      let page;
      if (args.slide_id) {
        if (!task.slide_ids.includes(args.slide_id))
          throw new Error("Slide is not part of this task");
        page = lookup(p.slides, args.slide_id, "Slide");
      }
      if (
        ["image", "pptx"].includes(kind) &&
        task.kind !== "export_deck" &&
        !page
      )
        throw new Error("A page result needs slide_id");
      if (kind === "pptx") {
        const entries = unzipSync(bytes);
        const slides = Object.entries(entries).filter(([name]) =>
          /^ppt\/slides\/slide\d+\.xml$/.test(name),
        );
        const expectedPages =
          task.kind === "export_deck" ? task.slide_ids.length : 1;
        if (slides.length !== expectedPages)
          throw new Error(
            `PPTX contains ${slides.length} pages; this task requires ${expectedPages}`,
          );
        if (
          !slides.length ||
          !slides.some(([, xml]) =>
            /<(?:p:sp|p:cxnSp|a:tbl|c:chart)\b/.test(
              Buffer.from(xml).toString(),
            ),
          )
        )
          throw new Error(
            "The PPTX needs native editable objects; an image-only deck is not a conversion result",
          );
      }
      const asset = await this.persistAsset(
        p,
        bytes,
        args.filename || path.basename(source),
        {
          kind,
          task_id: task.id,
          slide_id: args.slide_id || null,
          source_image_id: page ? task.source_image_ids[page.id] : null,
          source_slide_revision: page ? task.slide_revisions[page.id] : null,
          description: String(args.description || ""),
        },
      );
      task.artifact_ids.push(asset.id);
      task.updated_at = now();
      const stillCurrent =
        page &&
        page.revision === task.slide_revisions[page.id] &&
        (p.input_revision || 1) === (task.project_input_revision || 1);
      if (
        kind === "image" &&
        stillCurrent &&
        page.current_image_id === task.source_image_ids[page.id]
      ) {
        page.current_image_id = asset.id;
        page.current_pptx_id = null;
        page.content_changed = false;
      }
      if (
        kind === "pptx" &&
        stillCurrent &&
        page.current_image_id === task.source_image_ids[page.id]
      )
        page.current_pptx_id = asset.id;
      if (kind === "reference_preview" && args.reference_id) {
        const ref = lookup(p.references, args.reference_id, "Reference");
        ref.asset_ids.push(asset.id);
        ref.preview_asset_id = asset.id;
      }
      return {
        asset,
        file_path: path.join(this.projectPath(p.id), asset.relative_path),
      };
    });
  }
}
