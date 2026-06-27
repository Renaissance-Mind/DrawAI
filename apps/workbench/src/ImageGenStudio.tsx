import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createUploadBatch, generateImages, listSlideTemplateCards, listSlideTemplateGallery } from "./api";
import {
  imageGenPanelActions,
  imageGenVisibleTiles,
  type ImageGenerationTask,
  type ImageGenerationTaskImage,
  type ImageGenSelectionMode,
  type ImageGenTile
} from "./imageGenState";
import { agentProviderIconForId } from "./agentProviderPresentation";
import { API_PRESET_TEMPLATES } from "./apiPresetTemplates";
import type { ImageGenConnectionSettings, ImageGenMethodCard } from "./imageGenSettings";
import type {
  BatchDetail,
  BatchExecutionMode,
  ImageGenerationProvider,
  ImageGenerationRequest,
  ImageGenerationResponse,
  SlideTemplateCard,
  SlideTemplateGalleryItem
} from "./types";
import { listWorkflowTemplates } from "./workflowApi";
import type { WorkflowTemplate } from "./workflowTypes";

/**
 * Generation studio for OpenAI-compatible Images API and Codex built-in image generation.
 *
 * API provider request shape (POST /v1/images/generations):
 *   model, prompt, size, quality, background, moderation,
 *   output_format, n
 *
 * Codex provider request shape (POST /api/imagegen/generations):
 *   provider, model, prompt, size, quality, background, output_format, n,
 *   language, template_id, template_card_id, rendering_mode
 */

const DEFAULT_MODEL = "gpt-image-2";
const DEFAULT_MODERATION = "auto";
const DEFAULT_OUTPUT_FORMAT = "png";

type Resolution = "1k" | "2k" | "4k";
type Quality = "auto" | "low" | "medium" | "high";
type Background = "auto" | "opaque" | "transparent";
type OutputFormat = "png";
type GalleryLightbox = {
  item: SlideTemplateGalleryItem;
  imageUrl: string;
  title: string;
};
type TemplateLibraryMode = "all" | string;
type ImageGenMethodIcon = {
  accent_color: string;
  icon_url: string;
};

const SIZE_PRESETS = [
  "auto",
  "1:1",
  "3:2",
  "2:3",
  "4:3",
  "3:4",
  "5:4",
  "4:5",
  "16:9",
  "9:16",
  "2:1",
  "1:2",
  "3:1",
  "1:3",
  "21:9",
  "9:21"
] as const;

const OPENAI_SIZE_BY_RATIO: Record<Resolution, Record<string, string>> = {
  "1k": {
    auto: "auto",
    "1:1": "1024x1024",
    "3:2": "1536x1024",
    "2:3": "1024x1536",
    "4:3": "1024x768",
    "3:4": "768x1024",
    "5:4": "1280x1024",
    "4:5": "1024x1280",
    "16:9": "1536x864",
    "9:16": "864x1536",
    "2:1": "2048x1024",
    "1:2": "1024x2048",
    "3:1": "1536x512",
    "1:3": "512x1536",
    "21:9": "2016x864",
    "9:21": "864x2016"
  },
  "2k": {
    auto: "auto",
    "1:1": "2048x2048",
    "3:2": "2048x1360",
    "2:3": "1360x2048",
    "4:3": "2048x1536",
    "3:4": "1536x2048",
    "5:4": "2560x2048",
    "4:5": "2048x2560",
    "16:9": "2048x1152",
    "9:16": "1152x2048",
    "2:1": "2688x1344",
    "1:2": "1344x2688",
    "3:1": "3072x1024",
    "1:3": "1024x3072",
    "21:9": "2688x1152",
    "9:21": "1152x2688"
  },
  "4k": {
    auto: "auto",
    "1:1": "2880x2880",
    "3:2": "3520x2336",
    "2:3": "2336x3520",
    "4:3": "3312x2480",
    "3:4": "2480x3312",
    "5:4": "3216x2576",
    "4:5": "2576x3216",
    "16:9": "3840x2160",
    "9:16": "2160x3840",
    "2:1": "3840x1920",
    "1:2": "1920x3840",
    "3:1": "3840x1280",
    "1:3": "1280x3840",
    "21:9": "3840x1648",
    "9:21": "1648x3840"
  }
};

const RESOLUTIONS: Array<{ value: Resolution; label: string; hint: string }> = [
  { value: "1k", label: "1K", hint: "1024" },
  { value: "2k", label: "2K", hint: "2048" },
  { value: "4k", label: "4K", hint: "3840" }
];

const QUALITIES: Array<{ value: Quality; label: string }> = [
  { value: "auto", label: "自动" },
  { value: "low", label: "低" },
  { value: "medium", label: "中" },
  { value: "high", label: "高" }
];

const BACKGROUNDS: Array<{ value: Background; label: string }> = [
  { value: "auto", label: "自动" },
  { value: "opaque", label: "不透明" },
  { value: "transparent", label: "透明" }
];

type PPTTemplateOption = { value: string; label: string; sub: string };

const PPT_TEMPLATE_GROUPS: Array<{ group: string; options: PPTTemplateOption[] }> = [
  {
    group: "自动",
    options: [{ value: "auto", label: "自动选择", sub: "按意图路由" }]
  },
  {
    group: "专业商务 / 咨询",
    options: [
      { value: "consulting_report", label: "咨询报告", sub: "战略、对比、决策页" },
      { value: "mckinsey_boardroom", label: "董事会咨询页", sub: "结论先行、议题树、路线图" },
      { value: "bcg_strategy_map", label: "战略地图", sub: "组合矩阵、能力地图、机会评估" },
      { value: "investment_memo", label: "投资备忘录", sub: "投资假设、风险、尽调问题" },
      { value: "vc_pitch_deck", label: "VC 路演", sub: "问题-方案-市场-产品叙事" },
      { value: "annual_report", label: "年度报告", sub: "公司总结、ESG、经营亮点" }
    ]
  },
  {
    group: "科技 / AI 产品",
    options: [
      { value: "product_launch", label: "产品发布", sub: "能力发布、路线图" },
      { value: "dark_tech", label: "暗色科技", sub: "AI、Agent、系统架构" },
      { value: "openai_minimal", label: "AI 极简发布", sub: "模型能力、原则、系统概览" },
      { value: "apple_keynote", label: "Keynote 产品页", sub: "高质感英雄视觉、功能亮点" },
      { value: "linear_product_dark", label: "暗色产品系统", sub: "SaaS 工作流、产品运营" },
      { value: "vercel_gradient", label: "开发平台渐变", sub: "部署、云平台、前端 AI" },
      { value: "stripe_saas", label: "SaaS 商业产品", sub: "API、平台经济、增长飞轮" },
      { value: "developer_docs", label: "开发者文档", sub: "API、SDK、技术上手" },
      { value: "cyberpunk_infra", label: "赛博基础设施", sub: "网络、安全、控制平面" }
    ]
  },
  {
    group: "数据 / 媒体",
    options: [
      { value: "data_journalism", label: "数据新闻", sub: "证据、图表、指标叙事" },
      { value: "economist_data_story", label: "经济数据故事", sub: "图表主导、政策/宏观解释" },
      { value: "bloomberg_terminal", label: "终端仪表盘", sub: "金融监控、风险、多指标" },
      { value: "nyt_scrollytelling", label: "滚动叙事报道", sub: "公共议题、时间线、注释场景" },
      { value: "financial_times_report", label: "金融时报报告", sub: "严肃分析、表格、市场简报" },
      { value: "infographic_dashboard", label: "信息图仪表盘", sub: "KPI、状态、运营概览" }
    ]
  },
  {
    group: "学术 / 教学",
    options: [
      { value: "academic_technical", label: "学术技术", sub: "论文、模型、方法讲解" },
      { value: "nature_paper_briefing", label: "论文精读简报", sub: "论点、证据、贡献、局限" },
      { value: "neurips_poster", label: "会议海报", sub: "架构、实验、消融、结果" },
      { value: "lab_meeting", label: "组会汇报", sub: "问题、进展、证据、下一步" },
      { value: "notebooklm_briefing", label: "资料简报", sub: "文档到幻灯片、读书笔记" },
      { value: "notebooklm_cards", label: "资料卡片", sub: "来源卡、问题卡、综合卡" },
      { value: "teaching_explainer", label: "教学讲解", sub: "课程、培训、分步解释" },
      { value: "teaching_whiteboard", label: "白板教学", sub: "概念、例题、推导、纠错" },
      { value: "courseware_explainer", label: "课件讲解", sub: "学习目标、例子、检查点" }
    ]
  },
  {
    group: "潮流视觉",
    options: [
      { value: "magazine_editorial", label: "杂志叙事", sub: "观点、故事、公共解释" },
      { value: "creative_zine", label: "创意海报", sub: "活动、概念、年轻化表达" },
      { value: "swiss_grid", label: "瑞士网格", sub: "严谨网格、现代报告" },
      { value: "bauhaus_geometric", label: "包豪斯几何", sub: "几何结构、设计教育" },
      { value: "memphis_playful", label: "孟菲斯趣味", sub: "年轻化、活动、创意课件" },
      { value: "brutalist_poster", label: "野兽派海报", sub: "强观点、警示、宣言页" },
      { value: "glassmorphism", label: "玻璃拟态", sub: "未来感、层叠面板、仪表盘" },
      { value: "claymorphism", label: "黏土拟态", sub: "友好产品、入门解释" },
      { value: "bento_grid", label: "Bento 网格", sub: "功能总览、能力地图" },
      { value: "isometric_3d", label: "等距 3D", sub: "系统、流程、空间隐喻" },
      { value: "retro_futurism", label: "复古未来", sub: "未来场景、技术史、愿景" },
      { value: "pixel_art", label: "像素风", sub: "游戏化、开发者文化、趣味教学" }
    ]
  },
  {
    group: "卡通 / 原创教学风格",
    options: [
      { value: "blue_robot_learning", label: "蓝白圆润机器人学习风", sub: "泛化机器猫氛围，不复刻角色" },
      { value: "soft_storybook_anime", label: "柔和绘本动漫", sub: "原创角色、温和故事教学" },
      { value: "collectible_creature_cards", label: "原创收集卡", sub: "分类、对比、能力卡片" },
      { value: "toy_block_diagram", label: "玩具积木图解", sub: "模块、架构、拼装流程" },
      { value: "retro_platform_game", label: "复古平台游戏", sub: "关卡、检查点、挑战路径" },
      { value: "comic_manga_classroom", label: "漫画课堂", sub: "分镜、对话、课堂讲解" }
    ]
  }
];

const LANGUAGE_OPTIONS: Array<{ value: string; label: string; sub: string }> = [
  { value: "auto", label: "自动", sub: "跟随提示词" },
  { value: "zh", label: "中文", sub: "中文优先" },
  { value: "en", label: "English", sub: "英文输出" }
];

const TEMPLATE_STRATEGY_CARD_LINKS: Record<string, string> = {
  mckinsey_boardroom: "corporate_strategy_cinematic",
  bcg_strategy_map: "comparison_matrix_template",
  openai_minimal: "minimalist_clean",
  developer_docs: "design_blueprint",
  economist_data_story: "modern_newspaper",
  infographic_dashboard: "data_dashboard_template",
  nature_paper_briefing: "seminar_minimal_photo",
  courseware_explainer: "course_clay",
  swiss_grid: "swiss_international",
  bento_grid: "bento_grid_showcase",
  blue_robot_learning: "manga_safe_learning",
  comic_manga_classroom: "manga_safe_learning"
};

interface GeneratedImage extends ImageGenerationTaskImage {
  size: string;
  resolution: Resolution;
  quality: Quality;
  format: OutputFormat;
  transparent: boolean;
  provider: ImageGenerationProvider;
}

export default function ImageGenStudio({
  connection,
  methodCards,
  onSelectMethod,
  onOpenSettings,
  onCreated,
  onError
}: {
  connection: ImageGenConnectionSettings;
  methodCards: ImageGenMethodCard[];
  onSelectMethod?: (method: ImageGenMethodCard) => void;
  onOpenSettings?: () => void;
  onCreated: (detail: BatchDetail) => void | Promise<void>;
  onError: (message: string) => void;
}) {
  const provider: ImageGenerationProvider = connection.provider || "api";
  const [prompt, setPrompt] = useState("");
  const [size, setSize] = useState<string>("16:9");
  const [resolution, setResolution] = useState<Resolution>("2k");
  const [quality, setQuality] = useState<Quality>("high");
  const [background, setBackground] = useState<Background>("auto");
  const [count, setCount] = useState(1);
  const [language, setLanguage] = useState("auto");
  const [templateId, setTemplateId] = useState("auto");
  const [templateCardId, setTemplateCardId] = useState("");
  const [templateCards, setTemplateCards] = useState<SlideTemplateCard[]>([]);
  const [templateCardsError, setTemplateCardsError] = useState("");
  const [templateGallery, setTemplateGallery] = useState<SlideTemplateGalleryItem[]>([]);
  const [templateGalleryError, setTemplateGalleryError] = useState("");
  const [galleryLightbox, setGalleryLightbox] = useState<GalleryLightbox | null>(null);
  const [templateLibraryOpen, setTemplateLibraryOpen] = useState(false);
  const [templateLibraryCategory, setTemplateLibraryCategory] = useState<TemplateLibraryMode>("all");
  const [templateLibraryQuery, setTemplateLibraryQuery] = useState("");
  const [templateLibraryFocusId, setTemplateLibraryFocusId] = useState("");
  const [referenceImagePathInput, setReferenceImagePathInput] = useState("");

  const [tasks, setTasks] = useState<ImageGenerationTask[]>([]);
  const [activeTaskId, setActiveTaskId] = useState("");
  const [composerOpen, setComposerOpen] = useState(false);
  const [generationError, setGenerationError] = useState("");
  const [selectionMode, setSelectionMode] = useState<ImageGenSelectionMode>("off");
  const [selectedImageIds, setSelectedImageIds] = useState<string[]>([]);
  const [submitDialogOpen, setSubmitDialogOpen] = useState(false);

  const taskCounterRef = useRef(0);

  const effectiveSize = openAiSizeFromPreset(size, resolution);

  useEffect(() => {
    let cancelled = false;
    listSlideTemplateCards()
      .then((payload) => {
        if (cancelled) return;
        setTemplateCards(payload.cards || []);
        setTemplateCardsError("");
      })
      .catch((error) => {
        if (cancelled) return;
        setTemplateCards([]);
        setTemplateCardsError(error instanceof Error ? error.message : String(error));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    listSlideTemplateGallery()
      .then((payload) => {
        if (cancelled) return;
        setTemplateGallery(payload.templates || []);
        setTemplateGalleryError(payload.status === "missing" ? payload.message || "No gallery outputs yet" : "");
      })
      .catch((error) => {
        if (cancelled) return;
        setTemplateGallery([]);
        setTemplateGalleryError(error instanceof Error ? error.message : String(error));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const templateGalleryGroups = useMemo(() => groupTemplateGallery(templateGallery), [templateGallery]);
  const selectedTemplateOption = useMemo(() => findTemplateOption(templateId), [templateId]);
  const selectedGalleryItem = useMemo(
    () => templateGallery.find((item) => item.template_id === templateId),
    [templateGallery, templateId]
  );
  const focusedGalleryItem = useMemo(
    () =>
      templateGallery.find((item) => item.template_id === templateLibraryFocusId)
      || selectedGalleryItem
      || templateGallery[0],
    [selectedGalleryItem, templateGallery, templateLibraryFocusId]
  );
  const linkedTemplateCardId = useMemo(
    () => findLinkedTemplateCardId(templateId, templateCards),
    [templateId, templateCards]
  );
  const activeTemplateCard = useMemo(
    () => templateCards.find((card) => card.id === (templateCardId || linkedTemplateCardId)),
    [linkedTemplateCardId, templateCardId, templateCards]
  );
  const syncTemplateSelection = useCallback((nextTemplateId: string) => {
    setTemplateId(nextTemplateId);
    setTemplateCardId(findLinkedTemplateCardId(nextTemplateId, templateCards));
  }, [templateCards]);
  const selectGalleryTemplate = useCallback((item: SlideTemplateGalleryItem) => {
    syncTemplateSelection(item.template_id || "auto");
  }, [syncTemplateSelection]);
  const useGalleryTemplate = useCallback((item: SlideTemplateGalleryItem) => {
    selectGalleryTemplate(item);
    setTemplateLibraryOpen(false);
  }, [selectGalleryTemplate]);
  const openTemplateLibrary = useCallback(() => {
    setTemplateLibraryFocusId(selectedGalleryItem?.template_id || templateGallery[0]?.template_id || "");
    setTemplateLibraryCategory(selectedGalleryItem?.category || "all");
    setTemplateLibraryOpen(true);
  }, [selectedGalleryItem, templateGallery]);
  const selectAutoTemplate = useCallback(() => {
    syncTemplateSelection("auto");
    setTemplateLibraryFocusId("");
  }, [syncTemplateSelection]);
  const openGalleryLightbox = useCallback((item: SlideTemplateGalleryItem, imageUrl?: string, title?: string) => {
    const nextImageUrl = imageUrl || item.contact_sheet_url;
    if (!nextImageUrl) return;
    setGalleryLightbox({
      item,
      imageUrl: nextImageUrl,
      title: title || item.template_name || item.template_id
    });
  }, []);

  useEffect(() => {
    if (templateId === "auto") return;
    const linked = findLinkedTemplateCardId(templateId, templateCards);
    if (linked && templateCardId !== linked) {
      setTemplateCardId(linked);
    }
  }, [templateCardId, templateCards, templateId]);

  useEffect(() => {
    if (!galleryLightbox) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setGalleryLightbox(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [galleryLightbox]);

  useEffect(() => {
    if (!templateLibraryOpen || galleryLightbox) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setTemplateLibraryOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [galleryLightbox, templateLibraryOpen]);

  const request = useMemo<ImageGenerationRequest>(() => {
    const model = imageModelForProvider(provider, connection.model);
    const body: ImageGenerationRequest = {
      provider,
      model,
      prompt,
      size: effectiveSize,
      quality,
      background,
      moderation: DEFAULT_MODERATION,
      output_format: DEFAULT_OUTPUT_FORMAT,
      n: count
    };
    const apiBaseUrl = connection.baseUrl.trim();
    const apiKey = connection.apiKey.trim();
    if (apiBaseUrl) body.api_base_url = apiBaseUrl;
    if (apiKey) body.api_key = apiKey;
    if (templateId !== "auto") {
      body.template_id = templateId;
    }
    if (templateCardId) {
      body.template_card_id = templateCardId;
    }
    if (provider === "codex") {
      body.rendering_mode = "baked_text";
      if (language !== "auto") {
        body.language = language;
        body.output_language = language;
      }
      const referenceImagePath = referenceImagePathInput.trim();
      if (referenceImagePath) {
        body.source_image_path = referenceImagePath;
        body.reference_image_path = referenceImagePath;
      }
    }
    return body;
  }, [
    provider,
    prompt,
    effectiveSize,
    quality,
    background,
    count,
    language,
    templateId,
    templateCardId,
    referenceImagePathInput,
    connection.apiKey,
    connection.baseUrl,
    connection.model
  ]);

  const visibleTasks = useMemo(
    () => (activeTaskId ? tasks.filter((task) => task.id === activeTaskId) : tasks),
    [activeTaskId, tasks]
  );
  const visibleTiles = useMemo(() => imageGenVisibleTiles(visibleTasks), [visibleTasks]);
  const actionState = useMemo(
    () => imageGenPanelActions(visibleTasks, selectionMode, selectedImageIds),
    [selectionMode, selectedImageIds, visibleTasks]
  );
  const hasAnyRunningTask = tasks.some((task) => task.status === "running");
  const selectedImageIdsSet = useMemo(() => new Set(selectedImageIds), [selectedImageIds]);
  const imageById = useMemo(() => {
    const entries = imageGenVisibleTiles(tasks)
      .filter((tile) => tile.status === "completed")
      .map((tile) => [tile.id, tile as GeneratedImage] as const);
    return new Map(entries);
  }, [tasks]);
  const selectedImagesForSubmit = useMemo(
    () => actionState.submitImageIds.map((id) => imageById.get(id)).filter((image): image is GeneratedImage => Boolean(image)),
    [actionState.submitImageIds, imageById]
  );
  const completedVisibleCount = visibleTiles.filter((tile) => tile.status === "completed").length;
  const activeTask = activeTaskId ? tasks.find((task) => task.id === activeTaskId) || null : null;
  const canSubmitVisibleImages = actionState.canSubmit && !hasAnyRunningTask;
  const generationMethodCards = methodCards.length > 0 ? methodCards : [imageGenConnectionFallbackCard(connection)];

  useEffect(() => {
    const completedIds = new Set(imageGenVisibleTiles(tasks).filter((tile) => tile.status === "completed").map((tile) => tile.id));
    setSelectedImageIds((items) => items.filter((id) => completedIds.has(id)));
  }, [tasks]);

  const startGeneration = useCallback((
    submittedRequest: ImageGenerationRequest,
    submittedResolution: Resolution,
    titleSeed: string,
    expectedCount: number
  ) => {
    const taskIndex = taskCounterRef.current + 1;
    taskCounterRef.current = taskIndex;
    const taskId = `gen-${Date.now()}-${taskIndex}`;
    const task: ImageGenerationTask = {
      id: taskId,
      status: "running",
      title: generationTaskTitle(titleSeed, taskIndex),
      prompt: submittedRequest.prompt,
      expectedCount,
      images: [],
      error: "",
      createdAt: new Date().toISOString()
    };
    setTasks((items) => [task, ...items]);
    setActiveTaskId(taskId);
    setComposerOpen(false);
    setGenerationError("");
    setSelectionMode("off");
    setSelectedImageIds([]);

    void generateImages(submittedRequest)
      .then((payload) => {
        const next = imagesFromResponse(payload, submittedRequest, submittedResolution, taskId);
        if (next.length === 0) {
          throw new Error(imageGenerationEmptyMessage(payload));
        }
        setTasks((items) => items.map((item) => (
          item.id === taskId
            ? { ...item, status: "completed", images: next, error: "" }
            : item
        )));
      })
      .catch((error) => {
        const message = error instanceof Error ? error.message : String(error);
        setGenerationError(message);
        setTasks((items) => items.map((item) => (
          item.id === taskId
            ? { ...item, status: "failed", error: message }
            : item
        )));
      });
  }, []);

  const generate = useCallback(() => {
    const cleanPrompt = prompt.trim();
    if (!cleanPrompt) return;
    startGeneration({ ...request, prompt: cleanPrompt }, resolution, cleanPrompt, count);
  }, [count, prompt, request, resolution, startGeneration]);

  const toggleTileSelection = useCallback((imageId: string) => {
    setSelectedImageIds((items) => (
      items.includes(imageId)
        ? items.filter((item) => item !== imageId)
        : [...items, imageId]
    ));
  }, []);

  const regenerateSelectedImages = useCallback(() => {
    if (!actionState.canRegenerate || selectedImagesForSubmit.length === 0) return;
    const regeneratePrompt = selectedImagesForSubmit[0]?.prompt || prompt.trim();
    if (!regeneratePrompt) return;
    startGeneration(
      { ...request, prompt: regeneratePrompt, n: selectedImagesForSubmit.length },
      resolution,
      `重新生成 ${selectedImagesForSubmit.length} 张`,
      selectedImagesForSubmit.length
    );
  }, [actionState.canRegenerate, prompt, request, resolution, selectedImagesForSubmit, startGeneration]);

  return (
    <div className="gen-root gen-task-root">
      <aside className="gen-task-rail">
        <div className="gen-task-head">
          <div>
            <span>生成任务</span>
            <strong>{tasks.length} 个任务</strong>
          </div>
          <button
            type="button"
            className="gen-task-add"
            title="添加生成任务"
            aria-label="添加生成任务"
            onClick={() => {
              setComposerOpen(true);
              setActiveTaskId("");
              setSelectionMode("off");
              setSelectedImageIds([]);
            }}
          >
            <PlusMiniIcon />
          </button>
        </div>
        <div className="gen-task-list" role="list">
          {tasks.map((task) => (
            <button
              type="button"
              role="listitem"
              key={task.id}
              className={`gen-task-item ${task.status}${activeTaskId === task.id && !composerOpen ? " active" : ""}`}
              onClick={() => {
                setComposerOpen(false);
                setActiveTaskId(task.id);
                setSelectionMode("off");
                setSelectedImageIds([]);
              }}
            >
              <span>{task.title}</span>
              <strong>{task.status === "running" ? "生成中" : task.status === "failed" ? "失败" : `${task.images.length} 张`}</strong>
              <em>{task.prompt}</em>
            </button>
          ))}
        </div>
      </aside>

      <section className={`gen-panel ${composerOpen ? "composer" : "thumbnails"}`}>
        {composerOpen ? (
          <div className="gen-settings-panel">
            <div className="gen-form gen-settings-form">
              <Field className="gen-method-field" label="生成方式" hint={`${generationMethodCards.length} 个方式`}>
                <div className="gen-method-card-grid" role="radiogroup" aria-label="生成方式">
                  {generationMethodCards.map((method) => (
                    <GenerationMethodCard
                      key={method.id}
                      method={method}
                      methodIcon={imageGenMethodIcon(method)}
                      onSelect={() => onSelectMethod?.(method)}
                    />
                  ))}
                  {onOpenSettings && (
                    <button type="button" className="gen-method-card gen-method-manage-card" onClick={onOpenSettings}>
                      <span className="gen-method-glyph manage settings-provider-logo-custom" aria-hidden="true">
                        <SettingsSlidersIcon />
                      </span>
                      <span className="gen-method-card-copy">
                        <strong>管理方式</strong>
                        <em>添加或编辑连接</em>
                      </span>
                      <span className="gen-method-status">设置</span>
                    </button>
                  )}
                </div>
              </Field>

              <div className="gen-settings-column">
                <Field label="尺寸 / 比例" hint={effectiveSize}>
                  <div className="gen-ratio-grid">
                    {SIZE_PRESETS.map((preset) => {
                      const active = size === preset;
                      return (
                        <button
                          key={preset}
                          type="button"
                          className={`gen-ratio${active ? " active" : ""}`}
                          onClick={() => setSize(preset)}
                        >
                          <RatioGlyph ratio={preset} />
                          <span className="gen-ratio-label">{sizePresetLabel(preset)}</span>
                        </button>
                      );
                    })}
                  </div>
                </Field>

                <Field label="模板选择" hint={linkedTemplateCardId ? `联动 ${linkedTemplateCardId}` : "可选"}>
                  <div className="gen-template-picker-summary">
                    <div className="gen-template-picker-current">
                      <span className="gen-template-picker-kicker">
                        {templateId === "auto" ? "OPTIONAL" : selectedGalleryItem?.category || selectedTemplateOption?.group || "TEMPLATE"}
                      </span>
                      <strong>
                        {templateId === "auto"
                          ? "不选择模板"
                          : selectedGalleryItem?.template_name || selectedTemplateOption?.label || templateId}
                      </strong>
                      <p>
                        {templateId === "auto"
                          ? "不套用模板；只按主提示词生成。"
                          : selectedGalleryItem?.reason || selectedTemplateOption?.sub || "使用选中的模板作为普通视觉参考。"}
                      </p>
                    </div>
                    <div className="gen-template-picker-actions">
                      <button type="button" className="gen-template-library-open" onClick={openTemplateLibrary}>
                        打开模板库
                      </button>
                      {templateId !== "auto" && (
                        <button type="button" className="gen-template-auto" onClick={selectAutoTemplate}>
                          自动
                        </button>
                      )}
                    </div>
                  </div>
                  {templateCardsError && <p className="gen-inline-error">{templateCardsError}</p>}
                  {activeTemplateCard && (
                    <div className="gen-template-card-preview">
                      <div className="gen-template-card-title">
                        <span>{activeTemplateCard.name}</span>
                        <em>{activeTemplateCard.category}</em>
                      </div>
                      <p>{activeTemplateCard.prompt_recipe}</p>
                      <div className="gen-template-card-tags">
                        {activeTemplateCard.visual_tags.slice(0, 5).map((tag) => (
                          <span key={tag}>{tag}</span>
                        ))}
                      </div>
                      <div className="gen-template-card-meta">
                        <span>{activeTemplateCard.layout_archetypes.slice(0, 2).join(" / ")}</span>
                        <span>{provenanceLabel(activeTemplateCard)}</span>
                      </div>
                    </div>
                  )}
                </Field>
              </div>

              <div className="gen-settings-column">
                <div className="gen-settings-inline">
                  <Field label="像素等级" hint="输出尺寸">
                    <ChoiceCards
                      options={RESOLUTIONS.map((r) => ({
                        value: r.value,
                        label: r.label,
                        sub: r.hint,
                        icon: <ResolutionGlyph resolution={r.value} />
                      }))}
                      value={resolution}
                      onChange={(v) => setResolution(v as Resolution)}
                    />
                  </Field>
                  <Field label="生成数量" hint="1-10">
                    <Stepper value={count} min={1} max={10} onChange={setCount} />
                  </Field>
                </div>

                <Field label="质量" hint="生成质量">
                  <ChoiceCards
                    options={QUALITIES.map((q) => ({
                      value: q.value,
                      label: q.label,
                      icon: <QualityGlyph quality={q.value} />
                    }))}
                    value={quality}
                    onChange={(v) => setQuality(v as Quality)}
                  />
                </Field>

                <Field label="背景" hint="背景模式">
                  <BackgroundChoiceCards value={background} onChange={(v) => setBackground(v as Background)} />
                </Field>

                {provider === "codex" && (
                  <>
                    <Field label="输出语言" hint="默认自动">
                      <ChoiceCards
                        options={LANGUAGE_OPTIONS.map((option) => ({
                          value: option.value,
                          label: option.label,
                          sub: option.sub
                        }))}
                        value={language}
                        onChange={setLanguage}
                      />
                    </Field>

                    <Field label="参考图路径" hint="Image as context">
                      <input
                        className="gen-input"
                        value={referenceImagePathInput}
                        onChange={(e) => setReferenceImagePathInput(e.target.value)}
                        placeholder="C:\\Users\\...\\reference.png；填写后 Codex 会把图片作为视觉上下文"
                      />
                    </Field>
                  </>
                )}
              </div>

              <div className="gen-prompt-block gen-prompt-wide gen-prompt-bottom">
                <span className="gen-field-label">提示词</span>
                <textarea
                  className="gen-prompt"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="描述你想要生成的画面，例如：赛博朋克风格的城市夜景，霓虹灯倒映在湿润的街道上…"
                  rows={6}
                />
              </div>
            </div>

            <footer className="gen-settings-footer">
              {generationError && <p className="gen-error">{generationError}</p>}
              <button
                type="button"
                className="primary gen-generate"
                onClick={generate}
                disabled={!prompt.trim()}
              >
                生成
              </button>
            </footer>
          </div>
        ) : (
          <GeneratedThumbnailPanel
            activeTask={activeTask}
            completedCount={completedVisibleCount}
            tiles={visibleTiles}
            selectedIds={selectedImageIdsSet}
            selectionMode={selectionMode}
            canSubmit={canSubmitVisibleImages}
            canRegenerate={actionState.canRegenerate}
            selectedCount={selectedImagesForSubmit.length}
            hasRunningTasks={hasAnyRunningTask}
            onToggleSelection={toggleTileSelection}
            onToggleSelectionMode={() => {
              setSelectionMode((mode) => (mode === "selecting" ? "off" : "selecting"));
              setSelectedImageIds([]);
            }}
            onRegenerate={regenerateSelectedImages}
            onSubmit={() => setSubmitDialogOpen(true)}
            onOpenComposer={() => {
              setComposerOpen(true);
              setActiveTaskId("");
              setSelectionMode("off");
              setSelectedImageIds([]);
            }}
          />
        )}
      </section>
      {submitDialogOpen && (
        <GeneratedBatchSubmitDialog
          images={selectedImagesForSubmit}
          defaultName={generatedBatchTitle(selectedImagesForSubmit)}
          onClose={() => setSubmitDialogOpen(false)}
          onCreated={async (detail) => {
            setSubmitDialogOpen(false);
            setSelectionMode("off");
            setSelectedImageIds([]);
            await onCreated(detail);
          }}
          onError={onError}
        />
      )}
      {templateLibraryOpen && (
        <TemplateLibraryOverlay
          items={templateGallery}
          groups={templateGalleryGroups}
          selectedTemplateId={templateId}
          focusedItem={focusedGalleryItem}
          category={templateLibraryCategory}
          query={templateLibraryQuery}
          error={templateGalleryError}
          onCategoryChange={setTemplateLibraryCategory}
          onQueryChange={setTemplateLibraryQuery}
          onClose={() => setTemplateLibraryOpen(false)}
          onFocusTemplate={setTemplateLibraryFocusId}
          onPreview={openGalleryLightbox}
          onSelect={useGalleryTemplate}
        />
      )}
      {galleryLightbox && (
        <div
          className="gen-gallery-lightbox"
          role="dialog"
          aria-modal="true"
          aria-label="模板效果大图"
          onClick={() => setGalleryLightbox(null)}
        >
          <div className="gen-gallery-lightbox-panel" onClick={(event) => event.stopPropagation()}>
            <header className="gen-gallery-lightbox-head">
              <div>
                <strong>{galleryLightbox.title}</strong>
                <span>{galleryLightbox.item.category} · {galleryLightbox.item.ok_count}/{galleryLightbox.item.page_count} pages</span>
              </div>
              <div className="gen-gallery-lightbox-actions">
                <button
                  type="button"
                  onClick={() => {
                    selectGalleryTemplate(galleryLightbox.item);
                    setGalleryLightbox(null);
                  }}
                >
                  使用模板
                </button>
                <button type="button" aria-label="关闭" onClick={() => setGalleryLightbox(null)}>
                  ×
                </button>
              </div>
            </header>
            <div className="gen-gallery-lightbox-stage">
              <img src={galleryLightbox.imageUrl} alt={galleryLightbox.title} />
            </div>
            <div className="gen-gallery-lightbox-strip">
              {galleryLightbox.item.contact_sheet_url && (
                <button
                  type="button"
                  className={galleryLightbox.imageUrl === galleryLightbox.item.contact_sheet_url ? "active" : ""}
                  onClick={() => openGalleryLightbox(galleryLightbox.item)}
                >
                  <img src={galleryLightbox.item.contact_sheet_url} alt="contact sheet" />
                  <span>总览</span>
                </button>
              )}
              {galleryLightbox.item.pages.map((page) => (
                page.image_url ? (
                  <button
                    key={page.page_id}
                    type="button"
                    className={galleryLightbox.imageUrl === page.image_url ? "active" : ""}
                    onClick={() => openGalleryLightbox(galleryLightbox.item, page.image_url, page.page_title || page.page_id)}
                  >
                    <img src={page.image_url} alt={page.page_title} />
                    <span>{page.page_title || page.page_id}</span>
                  </button>
                ) : null
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Field({
  className,
  label,
  hint,
  children
}: {
  className?: string;
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`gen-field${className ? ` ${className}` : ""}`}>
      <span className="gen-field-head">
        <span className="gen-field-label">{label}</span>
        {hint && <span className="gen-field-hint">{hint}</span>}
      </span>
      {children}
    </div>
  );
}

function GenerationMethodCard({
  method,
  methodIcon,
  onSelect
}: {
  method: ImageGenMethodCard;
  methodIcon: ImageGenMethodIcon | null;
  onSelect: () => void;
}) {
  const disabled = !method.available && !method.selected;
  const iconStyle = methodIcon
    ? ({ "--provider-color": methodIcon.accent_color } as React.CSSProperties)
    : undefined;
  return (
    <button
      type="button"
      role="radio"
      aria-checked={method.selected}
      className={`gen-method-card${method.selected ? " active" : ""}${method.available ? "" : " missing"}`}
      disabled={disabled}
      onClick={onSelect}
    >
      <span
        className={`gen-method-glyph ${method.kind}${methodIcon ? " settings-provider-logo-mini" : ""}`}
        style={iconStyle}
        aria-hidden="true"
      >
        {methodIcon ? <img src={methodIcon.icon_url} alt="" /> : <GenerationMethodGlyph kind={method.kind} />}
      </span>
      <span className="gen-method-card-copy">
        <strong>{method.label}</strong>
        <em>{methodTypeLabel(method)}</em>
      </span>
      <span className={`gen-method-status ${method.available ? "ok" : "missing"}`}>
        {method.selected ? "当前" : method.available ? "可用" : "缺失"}
      </span>
      <span className="gen-method-card-detail">{method.model || method.detail || "默认模型"}</span>
      <span className="gen-method-card-detail muted">{method.detail || method.baseUrl || "内置连接"}</span>
    </button>
  );
}

function ChoiceCards({
  options,
  value,
  onChange
}: {
  options: Array<{ value: string; label: string; sub?: string; icon?: React.ReactNode }>;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="gen-choice-card-grid" role="radiogroup">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={value === option.value}
          className={`gen-choice-card${value === option.value ? " active" : ""}`}
          onClick={() => onChange(option.value)}
        >
          {option.icon && <span className="gen-choice-card-icon" aria-hidden="true">{option.icon}</span>}
          <span className="gen-choice-card-copy">
            <strong>{option.label}</strong>
            {option.sub && <em>{option.sub}</em>}
          </span>
        </button>
      ))}
    </div>
  );
}

function BackgroundChoiceCards({ value, onChange }: { value: Background; onChange: (value: Background) => void }) {
  return (
    <div className="gen-choice-card-grid gen-background-card-grid" role="radiogroup" aria-label="背景">
      {BACKGROUNDS.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={value === option.value}
          className={`gen-choice-card gen-background-choice${value === option.value ? " active" : ""}`}
          onClick={() => onChange(option.value)}
        >
          <BackgroundGlyph background={option.value} />
          <span className="gen-choice-card-copy">
            <strong>{option.label}</strong>
            <em>{backgroundOptionHint(option.value)}</em>
          </span>
        </button>
      ))}
    </div>
  );
}

function GeneratedThumbnailPanel({
  activeTask,
  completedCount,
  tiles,
  selectedIds,
  selectionMode,
  canSubmit,
  canRegenerate,
  selectedCount,
  hasRunningTasks,
  onToggleSelection,
  onToggleSelectionMode,
  onRegenerate,
  onSubmit,
  onOpenComposer
}: {
  activeTask: ImageGenerationTask | null;
  completedCount: number;
  tiles: ImageGenTile[];
  selectedIds: Set<string>;
  selectionMode: ImageGenSelectionMode;
  canSubmit: boolean;
  canRegenerate: boolean;
  selectedCount: number;
  hasRunningTasks: boolean;
  onToggleSelection: (imageId: string) => void;
  onToggleSelectionMode: () => void;
  onRegenerate: () => void;
  onSubmit: () => void;
  onOpenComposer: () => void;
}) {
  return (
    <div className="gen-thumb-panel">
      <header className="gen-thumb-panel-head">
        <div>
          <span>{activeTask ? activeTask.title : "生成结果"}</span>
          <strong>{completedCount} 张图片</strong>
        </div>
        <em>{hasRunningTasks ? "还有任务生成中" : tiles.length > 0 ? "可提交到可编辑化任务" : "等待生成"}</em>
      </header>
      <div className={`gen-result-grid${tiles.length === 0 ? " empty" : ""}`} aria-label="生成结果缩略图">
        {tiles.length > 0 ? (
          tiles.map((tile, index) => (
            <GeneratedTileCard
              key={tile.id}
              tile={tile}
              index={index}
              selected={selectedIds.has(tile.id)}
              selectionMode={selectionMode}
              onToggleSelection={onToggleSelection}
            />
          ))
        ) : (
          <div className="gen-result-empty">
            <button type="button" className="gen-result-empty-action" onClick={onOpenComposer}>
              <span className="gen-result-empty-plus" aria-hidden="true">
                <PlusMiniIcon />
              </span>
              <strong>点击添加生成任务</strong>
            </button>
          </div>
        )}
      </div>
      <div className={`gen-corner-actions${selectionMode === "selecting" ? " selecting" : ""}`}>
        {selectionMode === "selecting" && (
          <button
            type="button"
            className="gen-corner-action regenerate"
            title={canRegenerate ? `重新生成 ${selectedCount} 张` : "选择图片后可重新生成"}
            aria-label={canRegenerate ? `重新生成 ${selectedCount} 张` : "选择图片后可重新生成"}
            disabled={!canRegenerate}
            onClick={onRegenerate}
          >
            <RegenerateIcon />
          </button>
        )}
        <button
          type="button"
          className="gen-corner-action select"
          title={selectionMode === "selecting" ? "退出多选" : "多选图片"}
          aria-label={selectionMode === "selecting" ? "退出多选" : "多选图片"}
          onClick={onToggleSelectionMode}
        >
          {selectionMode === "selecting" ? <CloseMiniIcon /> : <SelectManyIcon />}
        </button>
        <button
          type="button"
          className="gen-corner-action submit"
          title={canSubmit ? `提交 ${selectedCount} 张到可编辑化任务` : "生成完成并选择图片后可提交"}
          aria-label={canSubmit ? `提交 ${selectedCount} 张到可编辑化任务` : "生成完成并选择图片后可提交"}
          disabled={!canSubmit}
          onClick={onSubmit}
        >
          <RunMiniIcon />
        </button>
      </div>
    </div>
  );
}

function GeneratedTileCard({
  tile,
  index,
  selected,
  selectionMode,
  onToggleSelection
}: {
  tile: ImageGenTile;
  index: number;
  selected: boolean;
  selectionMode: ImageGenSelectionMode;
  onToggleSelection: (imageId: string) => void;
}) {
  const completed = tile.status === "completed";
  return (
    <button
      type="button"
      className={`gen-result-card ${tile.status}${tile.transparent ? " checker" : ""}${selected ? " selected" : ""}`}
      disabled={!completed && selectionMode === "selecting"}
      onClick={() => {
        if (selectionMode === "selecting" && completed) onToggleSelection(tile.id);
      }}
      aria-pressed={selectionMode === "selecting" ? selected : undefined}
    >
      {completed ? (
        <img src={tile.url} alt={tile.prompt || "生成图"} loading={index < 6 ? "eager" : "lazy"} />
      ) : tile.status === "running" ? (
        <span className="gen-result-placeholder"><span className="button-spinner" /></span>
      ) : (
        <span className="gen-result-failed">{tile.error || "生成失败"}</span>
      )}
      <span className="gen-result-index">{index + 1}</span>
      {selectionMode === "selecting" && completed && <span className="gen-result-check" aria-hidden="true" />}
    </button>
  );
}

function GeneratedBatchSubmitDialog({
  images,
  defaultName,
  onClose,
  onCreated,
  onError
}: {
  images: GeneratedImage[];
  defaultName: string;
  onClose: () => void;
  onCreated: (detail: BatchDetail) => void | Promise<void>;
  onError: (message: string) => void;
}) {
  const [name, setName] = useState(defaultName);
  const [manualAssetReview, setManualAssetReview] = useState(false);
  const [workflowTemplates, setWorkflowTemplates] = useState<WorkflowTemplate[]>([]);
  const [selectedWorkflowTemplateId, setSelectedWorkflowTemplateId] = useState("default_drawai_dag");
  const [selectedExecutionMode, setSelectedExecutionMode] = useState<BatchExecutionMode>("default");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  useEffect(() => {
    let canceled = false;
    listWorkflowTemplates()
      .then((response) => {
        if (canceled) return;
        setWorkflowTemplates(response.templates);
        if (!response.templates.some((template) => template.template_id === selectedWorkflowTemplateId)) {
          setSelectedWorkflowTemplateId(response.templates[0]?.template_id || "default_drawai_dag");
        }
      })
      .catch((error) => {
        if (canceled) return;
        const message = error instanceof Error ? error.message : String(error);
        setSubmitError(message);
        onError(message);
      });
    return () => {
      canceled = true;
    };
  }, []);

  async function submit() {
    if (submitting || images.length === 0) return;
    setSubmitting(true);
    setSubmitError("");
    try {
      const executionMode: BatchExecutionMode = selectedExecutionMode === "llm" ? "default" : selectedExecutionMode;
      const form = new FormData();
      form.set("name", name.trim() || defaultName || "生成图");
      form.set("input_mode", "upload");
      form.set("max_concurrent_cases", "10");
      form.set("auto_run_svg_after_analysis", manualAssetReview ? "false" : "true");
      form.set("workflow_template_id", selectedWorkflowTemplateId);
      form.set("execution_mode", executionMode);
      for (const [index, image] of images.entries()) {
        await appendGeneratedImageToForm(form, image, index);
      }
      const detail = await createUploadBatch(form);
      await onCreated(detail);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setSubmitError(message);
      onError(message);
      setSubmitting(false);
    }
  }

  return (
    <div className="gen-submit-dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="gen-submit-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="提交到可编辑化任务"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="gen-submit-dialog-head">
          <div>
            <span>可编辑化任务</span>
            <strong>提交 {images.length} 张生成图</strong>
          </div>
          <button type="button" aria-label="关闭" onClick={onClose} disabled={submitting}>
            <CloseMiniIcon />
          </button>
        </header>
        <div className="gen-submit-dialog-body">
          <label className="gen-submit-field">
            <span>任务名称</span>
            <input value={name} disabled={submitting} onChange={(event) => setName(event.currentTarget.value)} />
          </label>
          <label className="gen-submit-field">
            <span>Workflow</span>
            <select
              value={selectedWorkflowTemplateId}
              disabled={submitting || workflowTemplates.length === 0}
              onChange={(event) => setSelectedWorkflowTemplateId(event.currentTarget.value)}
            >
              {workflowTemplates.map((template) => (
                <option value={template.template_id} key={template.template_id}>{template.name}</option>
              ))}
            </select>
          </label>
          <div className="gen-submit-field">
            <span>运行方式</span>
            <div className="gen-submit-segmented" role="radiogroup" aria-label="运行方式">
              {(["default", "agent"] as const).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  role="radio"
                  aria-checked={selectedExecutionMode === mode}
                  className={selectedExecutionMode === mode ? "active" : ""}
                  disabled={submitting}
                  onClick={() => setSelectedExecutionMode(mode)}
                >
                  {mode === "default" ? "默认" : "Agent"}
                </button>
              ))}
              <button type="button" role="radio" aria-checked={false} disabled>LLM</button>
            </div>
          </div>
          <label className="gen-submit-review-toggle">
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
          <div className="gen-submit-preview-strip" aria-label="将提交的生成图">
            {images.slice(0, 8).map((image) => (
              <img key={image.id} src={image.url} alt="" />
            ))}
            {images.length > 8 && <span>+{images.length - 8}</span>}
          </div>
          {submitError && <p className="gen-submit-error">{submitError}</p>}
        </div>
        <footer className="gen-submit-dialog-actions">
          <button type="button" disabled={submitting} onClick={onClose}>取消</button>
          <button type="button" className="primary" disabled={submitting || images.length === 0} onClick={() => void submit()}>
            {submitting && <span className="button-spinner" />}
            {submitting ? "提交中" : manualAssetReview ? "提交并手动确认" : "提交并自动运行"}
          </button>
        </footer>
      </section>
    </div>
  );
}

function groupTemplateGallery(items: SlideTemplateGalleryItem[]): Array<{ category: string; items: SlideTemplateGalleryItem[] }> {
  const groups = new Map<string, SlideTemplateGalleryItem[]>();
  for (const item of items) {
    const category = item.category || "uncategorized";
    groups.set(category, [...(groups.get(category) || []), item]);
  }
  return Array.from(groups.entries()).map(([category, groupItems]) => ({ category, items: groupItems }));
}

function findTemplateOption(templateId: string): (PPTTemplateOption & { group: string }) | null {
  for (const group of PPT_TEMPLATE_GROUPS) {
    const option = group.options.find((item) => item.value === templateId);
    if (option) return { ...option, group: group.group };
  }
  return null;
}

function TemplateLibraryOverlay({
  items,
  groups,
  selectedTemplateId,
  focusedItem,
  category,
  query,
  error,
  onCategoryChange,
  onQueryChange,
  onClose,
  onFocusTemplate,
  onPreview,
  onSelect
}: {
  items: SlideTemplateGalleryItem[];
  groups: Array<{ category: string; items: SlideTemplateGalleryItem[] }>;
  selectedTemplateId: string;
  focusedItem?: SlideTemplateGalleryItem;
  category: TemplateLibraryMode;
  query: string;
  error: string;
  onCategoryChange: (category: TemplateLibraryMode) => void;
  onQueryChange: (query: string) => void;
  onClose: () => void;
  onFocusTemplate: (templateId: string) => void;
  onPreview: (item: SlideTemplateGalleryItem, imageUrl?: string, title?: string) => void;
  onSelect: (item: SlideTemplateGalleryItem) => void;
}) {
  const normalizedQuery = query.trim().toLowerCase();
  const filteredItems = items.filter((item) => {
    const matchesCategory = category === "all" || item.category === category;
    if (!matchesCategory) return false;
    if (!normalizedQuery) return true;
    return [
      item.template_id,
      item.template_name,
      item.category,
      item.reason,
      ...item.pages.map((page) => page.page_title || page.page_id)
    ]
      .join(" ")
      .toLowerCase()
      .includes(normalizedQuery);
  });
  const categoryTabs = [
    { category: "all", label: "全部模板", count: items.length },
    ...groups.map((group) => ({ category: group.category, label: group.category, count: group.items.length }))
  ];
  const detailItem = focusedItem && filteredItems.some((item) => item.template_id === focusedItem.template_id)
    ? focusedItem
    : filteredItems[0] || focusedItem;

  return (
    <div className="gen-template-library" role="dialog" aria-modal="true" aria-label="模板库">
      <div className="gen-template-library-shell">
        <header className="gen-template-library-head">
          <div>
            <span>DrawAI Template Library</span>
            <h2>选择一个 PPT 视觉系统</h2>
          </div>
          <div className="gen-template-library-search">
            <input
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder="搜索模板、场景或页面"
              autoFocus
            />
            <button type="button" aria-label="关闭模板库" onClick={onClose}>
              ×
            </button>
          </div>
        </header>

        <div className="gen-template-library-layout">
          <nav className="gen-template-library-nav" aria-label="模板分类">
            {categoryTabs.map((tab) => (
              <button
                key={tab.category}
                type="button"
                className={category === tab.category ? "active" : ""}
                onClick={() => onCategoryChange(tab.category)}
              >
                <span>{tab.label}</span>
                <em>{tab.count}</em>
              </button>
            ))}
          </nav>

          <main className="gen-template-library-main">
            {error && <p className="gen-inline-error">{error}</p>}
            {!error && items.length === 0 && (
              <div className="gen-template-library-empty">还没有可展示的真实模板样例。</div>
            )}
            {items.length > 0 && filteredItems.length === 0 && (
              <div className="gen-template-library-empty">没有匹配的模板。</div>
            )}
            <div className="gen-template-showcase">
              {filteredItems.map((item, index) => {
                const active = item.template_id === selectedTemplateId;
                const focused = detailItem?.template_id === item.template_id;
                return (
                  <article
                    key={item.template_id}
                    className={`gen-template-showcase-item${active ? " active" : ""}${focused ? " focused" : ""}`}
                    onMouseEnter={() => onFocusTemplate(item.template_id)}
                  >
                    <button
                      type="button"
                      className="gen-template-showcase-preview"
                      onClick={() => onFocusTemplate(item.template_id)}
                    >
                      {item.contact_sheet_url ? (
                        <img src={item.contact_sheet_url} alt={`${item.template_name} preview`} loading={index < 4 ? "eager" : "lazy"} />
                      ) : (
                        <span>No preview</span>
                      )}
                    </button>
                    <div className="gen-template-showcase-copy">
                      <span>{item.category}</span>
                      <strong>{item.template_name || item.template_id}</strong>
                      <p>{item.reason}</p>
                      <div className="gen-template-showcase-meta">
                        <em>{item.ok_count}/{item.page_count} pages</em>
                        {active && <em>已选中</em>}
                      </div>
                    </div>
                    <div className="gen-template-showcase-actions">
                      <button type="button" onClick={() => onSelect(item)}>
                        使用模板
                      </button>
                      <button type="button" disabled={!item.contact_sheet_url} onClick={() => onPreview(item)}>
                        预览大图
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          </main>

          <aside className="gen-template-library-detail">
            {detailItem ? (
              <>
                <div className="gen-template-detail-hero">
                  {detailItem.contact_sheet_url ? (
                    <button type="button" onClick={() => onPreview(detailItem)}>
                      <img src={detailItem.contact_sheet_url} alt={`${detailItem.template_name} contact sheet`} />
                    </button>
                  ) : (
                    <span>No preview</span>
                  )}
                </div>
                <div className="gen-template-detail-copy">
                  <span>{detailItem.category}</span>
                  <h3>{detailItem.template_name || detailItem.template_id}</h3>
                  <p>{detailItem.reason}</p>
                </div>
                <div className="gen-template-detail-pages">
                  {detailItem.pages.map((page) => (
                    <button
                      key={page.page_id}
                      type="button"
                      disabled={!page.image_url}
                      onClick={() => onPreview(detailItem, page.image_url, page.page_title || page.page_id)}
                    >
                      {page.image_url && <img src={page.image_url} alt={page.page_title || page.page_id} loading="lazy" />}
                      <span>{page.page_title || page.page_id}</span>
                    </button>
                  ))}
                </div>
                <button type="button" className="gen-template-detail-use" onClick={() => onSelect(detailItem)}>
                  使用这个模板
                </button>
              </>
            ) : (
              <div className="gen-template-library-empty">选择一个模板查看详情。</div>
            )}
          </aside>
        </div>
      </div>
    </div>
  );
}

function findLinkedTemplateCardId(templateId: string, cards: SlideTemplateCard[]): string {
  if (!templateId || templateId === "auto") return "";
  if (cards.some((card) => card.id === templateId)) return templateId;
  const mapped = TEMPLATE_STRATEGY_CARD_LINKS[templateId] || "";
  return mapped && cards.some((card) => card.id === mapped) ? mapped : "";
}

function provenanceLabel(card: SlideTemplateCard): string {
  const sources = card.provenance
    .map((item) => item.source)
    .filter((value): value is string => typeof value === "string" && Boolean(value));
  return sources[0] || "DrawAI";
}

function imageGenConnectionFallbackCard(connection: ImageGenConnectionSettings): ImageGenMethodCard {
  const provider = connection.provider || "api";
  const codex = provider === "codex";
  return {
    id: connection.methodId || (codex ? "codex_builtin" : "custom"),
    kind: codex ? "codex_builtin" : "custom",
    provider,
    label: connection.label || (codex ? "Codex 内置" : "自定义 Images API"),
    detail: codex ? "Codex SDK 图像生成" : connection.baseUrl || "自定义 Images API",
    model: connection.model || DEFAULT_MODEL,
    selected: true,
    available: true,
    apiPresetId: connection.apiPresetId || "",
    baseUrl: connection.baseUrl || ""
  };
}

function methodTypeLabel(method: ImageGenMethodCard): string {
  if (method.kind === "codex_builtin") return "Codex SDK";
  if (method.kind === "api_preset") return "Images API 预设";
  return "自定义 API";
}

function imageGenMethodIcon(method: ImageGenMethodCard): ImageGenMethodIcon | null {
  if (method.kind === "codex_builtin") return agentProviderIconForId("codex_sdk");
  const normalizedPresetId = method.apiPresetId.replace(/_\d+$/, "");
  return (
    API_PRESET_TEMPLATES.find(
      (template) =>
        template.id === method.apiPresetId ||
        template.id === normalizedPresetId ||
        (template.base_url === method.baseUrl && template.model === method.model)
    ) || null
  );
}

function backgroundOptionHint(background: Background): string {
  if (background === "transparent") return "前景透明";
  if (background === "opaque") return "白底输出";
  return "按提示词判断";
}

function GenerationMethodGlyph({ kind }: { kind: ImageGenMethodCard["kind"] }) {
  if (kind === "codex_builtin") {
    return (
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M12 3.5 18.7 7.4v7.2L12 20.5l-6.7-5.9V7.4L12 3.5Z" strokeLinejoin="round" />
        <path d="m8.2 9.2 3.8-2.1 3.8 2.1M8.2 14.8l3.8 2.1 3.8-2.1M12 7.1v9.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  if (kind === "api_preset") {
    return (
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="4" y="5" width="16" height="14" rx="3" />
        <path d="M8 9h8M8 13h5" strokeLinecap="round" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M5 12h14M12 5v14" strokeLinecap="round" />
      <circle cx="12" cy="12" r="8" />
    </svg>
  );
}

function SettingsSlidersIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M4 7h10M18 7h2M4 17h2M10 17h10" strokeLinecap="round" />
      <circle cx="16" cy="7" r="2" />
      <circle cx="8" cy="17" r="2" />
    </svg>
  );
}

function ResolutionGlyph({ resolution }: { resolution: Resolution }) {
  return (
    <span className={`gen-resolution-glyph r-${resolution}`}>
      <span />
      <span />
      <span />
    </span>
  );
}

function QualityGlyph({ quality }: { quality: Quality }) {
  const level = quality === "low" ? 1 : quality === "medium" ? 2 : quality === "high" ? 3 : 0;
  return (
    <span className={`gen-quality-glyph ${quality}`} aria-hidden="true">
      {[1, 2, 3].map((item) => (
        <span key={item} className={level === 0 || item <= level ? "lit" : ""} />
      ))}
    </span>
  );
}

function BackgroundGlyph({ background }: { background: Background }) {
  return (
    <span className={`gen-background-icon ${background}`} aria-hidden="true">
      {background === "transparent" && <span className="gen-background-object" />}
      {background === "auto" && <span className="gen-background-auto" />}
    </span>
  );
}

function Stepper({
  value,
  min,
  max,
  onChange
}: {
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
}) {
  return (
    <div className="gen-stepper">
      <button type="button" disabled={value <= min} onClick={() => onChange(value - 1)}>
        −
      </button>
      <span>{value}</span>
      <button type="button" disabled={value >= max} onClick={() => onChange(value + 1)}>
        +
      </button>
    </div>
  );
}

function RatioGlyph({ ratio }: { ratio: string }) {
  const { w, h } = ratioDims(ratio);
  if (ratio === "auto") {
    return <span className="gen-ratio-glyph gen-ratio-auto">自</span>;
  }
  return (
    <span className="gen-ratio-glyph">
      <span style={{ width: w, height: h }} />
    </span>
  );
}

function PlusMiniIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

function RunMiniIcon() {
  return (
    <svg viewBox="0 0 24 24" width="19" height="19" fill="currentColor" aria-hidden="true">
      <path d="M8 5.4v13.2c0 .7.78 1.12 1.36.73l9.7-6.6a.88.88 0 0 0 0-1.46l-9.7-6.6A.88.88 0 0 0 8 5.4Z" />
    </svg>
  );
}

function SelectManyIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8">
      <rect x="4" y="4" width="7" height="7" rx="1.5" />
      <rect x="13" y="4" width="7" height="7" rx="1.5" />
      <rect x="4" y="13" width="7" height="7" rx="1.5" />
      <path d="m14 16 2 2 4-5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function RegenerateIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M20 12a8 8 0 0 1-13.3 6" strokeLinecap="round" />
      <path d="M4 12A8 8 0 0 1 17.3 6" strokeLinecap="round" />
      <path d="M17 2v4h4M7 22v-4H3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CloseMiniIcon() {
  return (
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="m6 6 12 12M18 6 6 18" strokeLinecap="round" />
    </svg>
  );
}

function ratioDims(ratio: string, max = 26): { w: number; h: number } {
  if (ratio === "auto") return { w: max, h: max };
  const [a, b] = ratio.split(":").map(Number);
  if (!a || !b) return { w: max, h: max };
  if (a >= b) return { w: max, h: Math.max(8, Math.round((max * b) / a)) };
  return { w: Math.max(8, Math.round((max * a) / b)), h: max };
}

function sizePresetLabel(preset: string): string {
  return preset === "auto" ? "自动" : preset;
}

function openAiSizeFromPreset(ratio: string, resolution: Resolution): string {
  return OPENAI_SIZE_BY_RATIO[resolution]?.[ratio] || "1024x1024";
}

function imageModelForProvider(provider: ImageGenerationProvider, configuredModel: string): string {
  const model = configuredModel.trim();
  if (provider === "codex" && model === DEFAULT_MODEL) return "";
  return model || DEFAULT_MODEL;
}

function generationTaskTitle(seed: string, index: number): string {
  const clean = seed.trim().replace(/\s+/g, " ");
  if (clean.startsWith("重新生成")) return clean;
  return clean ? `生成 ${index} · ${clean.slice(0, 18)}` : `生成 ${index}`;
}

function generatedBatchTitle(images: GeneratedImage[]): string {
  const prompt = images[0]?.prompt.trim().replace(/\s+/g, " ") || "";
  const prefix = prompt ? `生成图 - ${prompt.slice(0, 24)}` : "生成图";
  return images.length > 1 ? `${prefix} (${images.length} 张)` : prefix;
}

async function appendGeneratedImageToForm(form: FormData, image: GeneratedImage, index: number): Promise<void> {
  const filename = `generated-${String(index + 1).padStart(3, "0")}.${extensionFromGeneratedImage(image)}`;
  try {
    const response = await fetch(image.url);
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    const blob = await response.blob();
    if (!blob.type.startsWith("image/")) throw new Error(`not an image: ${blob.type || "unknown"}`);
    form.append("files", new File([blob], filename, { type: blob.type }), filename);
  } catch {
    form.append("generated_image_urls", image.url);
  }
}

function extensionFromGeneratedImage(image: GeneratedImage): string {
  return "png";
}

function imagesFromResponse(
  payload: ImageGenerationResponse,
  request: ImageGenerationRequest,
  resolution: Resolution,
  taskId: string
): GeneratedImage[] {
  const candidates = imageCandidates(payload);
  const responseProvider = imageGenerationProviderFromResponse(payload, request.provider);
  return candidates.flatMap((item, index) => {
    const urls = imageUrlsFromCandidate(item, request.output_format);
    if (!urls.length) return [];
    const record = objectRecord(item);
    return urls.map((url, urlIndex) => ({
      id: String(record.id || record.image_id || record.created || `image-${Date.now()}-${index + 1}-${urlIndex + 1}`),
      taskId,
      status: "completed",
      url,
      size: String(record.size || request.size),
      resolution,
      quality: request.quality as Quality,
      format: request.output_format as OutputFormat,
      transparent: request.background === "transparent",
      provider: imageGenerationProviderFromResponse(item, responseProvider),
      prompt: request.prompt
    }));
  });
}

function imageGenerationProviderFromResponse(
  value: unknown,
  fallback: ImageGenerationProvider | undefined
): ImageGenerationProvider {
  const provider = objectRecord(value).provider;
  return provider === "codex" ? "codex" : fallback === "codex" ? "codex" : "api";
}

function imageCandidates(payload: unknown): unknown[] {
  const candidates: unknown[] = [];
  collectImageCandidates(payload, candidates, 0);
  return candidates;
}

function collectImageCandidates(value: unknown, candidates: unknown[], depth: number): void {
  if (depth > 8 || value == null) return;
  if (Array.isArray(value)) {
    value.forEach((item) => collectImageCandidates(item, candidates, depth + 1));
    return;
  }
  const record = objectRecord(value);
  if (hasImagePayload(record)) {
    candidates.push(value);
    return;
  }
  for (const key of ["data", "result", "images", "output", "results"]) {
    collectImageCandidates(record[key], candidates, depth + 1);
  }
}

function hasImagePayload(record: Record<string, unknown>): boolean {
  return Boolean(record.url || record.urls || record.b64_json || record.base64 || record.image_base64 || record.image_url || record.output_url || record.uri);
}

function imageUrlsFromCandidate(item: unknown, format: string): string[] {
  if (typeof item === "string") return [item];
  const record = objectRecord(item);
  const direct = record.url || record.image_url || record.output_url || record.uri;
  const directUrls = stringList(direct);
  if (directUrls.length) return directUrls;
  const urls = stringList(record.urls);
  if (urls.length) return urls;
  const b64 = record.b64_json || record.base64 || record.image_base64;
  if (typeof b64 === "string" && b64) {
    const mime = format === "jpeg" ? "image/jpeg" : format === "webp" ? "image/webp" : "image/png";
    const normalized = b64.startsWith("data:") ? b64 : `data:${mime};base64,${b64}`;
    return [normalized];
  }
  return [];
}

function imageGenerationEmptyMessage(payload: ImageGenerationResponse): string {
  const { task, status } = imageGenerationStatusInfo(payload, 0);
  if (task || status) {
    return `图像生成请求还没有返回图片${task ? `（任务：${task}）` : ""}${status ? `，状态：${status}` : ""}。`;
  }
  return "图像生成响应里没有图片 URL 或 base64 内容。";
}

function imageGenerationStatusInfo(value: unknown, depth: number): { task: string; status: string } {
  if (depth > 8 || value == null) return { task: "", status: "" };
  if (Array.isArray(value)) {
    for (const item of value) {
      const info = imageGenerationStatusInfo(item, depth + 1);
      if (info.task || info.status) return info;
    }
    return { task: "", status: "" };
  }
  const record = objectRecord(value);
  const task = record.task_id || record.id || record.request_id;
  const status = record.status || record.state;
  if (task || status) {
    return {
      task: typeof task === "string" ? task : "",
      status: typeof status === "string" ? status : ""
    };
  }
  for (const key of ["data", "result", "images", "output", "results"]) {
    const info = imageGenerationStatusInfo(record[key], depth + 1);
    if (info.task || info.status) return info;
  }
  return { task: "", status: "" };
}

function stringList(value: unknown): string[] {
  if (typeof value === "string" && value) return [value];
  if (Array.isArray(value)) return value.filter((item): item is string => typeof item === "string" && Boolean(item));
  return [];
}

function objectRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? value as Record<string, unknown> : {};
}
