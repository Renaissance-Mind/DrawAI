import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createUploadBatch, generateImages, listSlideTemplateCards, listSlideTemplateGallery } from "./api";
import type {
  BatchDetail,
  ImageGenerationProvider,
  ImageGenerationRequest,
  ImageGenerationResponse,
  ReferenceMode,
  SlideTemplateCard,
  SlideTemplateGalleryItem
} from "./types";

/**
 * Generation studio for OpenAI-compatible Images API and Codex built-in image generation.
 *
 * API provider request shape (POST /v1/images/generations):
 *   model, prompt, size, quality, background, moderation,
 *   output_format, n
 *
 * Codex provider request shape (POST /api/imagegen/generations):
 *   provider, model, prompt, size, quality, background, output_format, n,
 *   language, template_id, source_mode, text_density, visible_text_blocks,
 *   sources, claims, data_sources, visual_style
 */

const DEFAULT_MODEL = "gpt-image-2";
const DEFAULT_MODERATION = "auto";
const DEFAULT_OUTPUT_FORMAT = "png";

type Resolution = "1k" | "2k" | "4k";
type Quality = "auto" | "low" | "medium" | "high";
type Background = "auto" | "opaque" | "transparent";
type OutputFormat = "png";
type RightMode = "stage" | "grid";
type StyleCandidateSlot = "auto" | "1" | "2" | "3";
type IpSafetyMode = "off" | "generic" | "strict";
type GalleryLightbox = {
  item: SlideTemplateGalleryItem;
  imageUrl: string;
  title: string;
};
type TemplateLibraryMode = "all" | string;

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

const PROVIDERS: Array<{ value: ImageGenerationProvider; label: string; sub: string }> = [
  { value: "api", label: "API", sub: "参数直连" },
  { value: "codex", label: "Codex", sub: "内置工具" }
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
    group: "卡通 / IP 安全氛围",
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

const SOURCE_MODES: Array<{ value: string; label: string; sub: string }> = [
  { value: "prompt_only", label: "仅提示词", sub: "不补事实" },
  { value: "source_grounded", label: "资料约束", sub: "按来源生成" },
  { value: "data_driven", label: "数据驱动", sub: "按表格/指标画图" },
  { value: "brand_template", label: "品牌模板", sub: "按参考风格" },
  { value: "web_research", label: "联网研究后", sub: "先研究再生成" }
];

const LANGUAGE_OPTIONS: Array<{ value: string; label: string; sub: string }> = [
  { value: "zh", label: "中文", sub: "中文优先" },
  { value: "auto", label: "自动", sub: "跟随提示词" },
  { value: "en", label: "English", sub: "英文输出" }
];

const TEXT_DENSITIES: Array<{ value: string; label: string; sub: string }> = [
  { value: "medium", label: "中等", sub: "标题+少量说明" },
  { value: "medium-high", label: "中高", sub: "技术页推荐" },
  { value: "high", label: "高", sub: "报告/资料页" },
  { value: "low-medium", label: "偏低", sub: "海报/发布页" }
];

const STYLE_CANDIDATE_SLOTS: Array<{ value: StyleCandidateSlot; label: string; sub: string }> = [
  { value: "auto", label: "自动", sub: "多图轮换" },
  { value: "1", label: "1", sub: "候选一" },
  { value: "2", label: "2", sub: "候选二" },
  { value: "3", label: "3", sub: "候选三" }
];

const IP_SAFETY_MODES: Array<{ value: IpSafetyMode; label: string; sub: string }> = [
  { value: "off", label: "Off", sub: "default" },
  { value: "generic", label: "Generic", sub: "broad" },
  { value: "strict", label: "Strict", sub: "strong" }
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

const REFERENCE_MODES: Array<{ value: ReferenceMode; label: string; sub: string }> = [
  { value: "reference_context", label: "Context", sub: "image as context" },
  { value: "reference_tokens_only", label: "Tokens", sub: "extract tokens only" },
  { value: "reference_edit_low", label: "Edit low", sub: "loose edit" },
  { value: "reference_edit_high", label: "Edit high", sub: "strong edit" },
  { value: "content_edit", label: "Content edit", sub: "edit target" }
];

interface GeneratedImage {
  id: string;
  url: string;
  size: string;
  resolution: Resolution;
  quality: Quality;
  format: OutputFormat;
  transparent: boolean;
  provider: ImageGenerationProvider;
  prompt: string;
}

export interface ImageGenConnectionSettings {
  provider: ImageGenerationProvider;
  baseUrl: string;
  apiKey: string;
  model: string;
}

export default function ImageGenStudio({
  connection,
  onConnectionChange,
  onCreated,
  onError
}: {
  connection: ImageGenConnectionSettings;
  onConnectionChange?: (connection: ImageGenConnectionSettings) => void;
  onCreated: (detail: BatchDetail) => void | Promise<void>;
  onError: (message: string) => void;
}) {
  const [provider, setProvider] = useState<ImageGenerationProvider>(connection.provider || "api");
  const [prompt, setPrompt] = useState("");
  const [size, setSize] = useState<string>("16:9");
  const [resolution, setResolution] = useState<Resolution>("2k");
  const [quality, setQuality] = useState<Quality>("high");
  const [background, setBackground] = useState<Background>("auto");
  const [count, setCount] = useState(1);
  const [language, setLanguage] = useState("zh");
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
  const [sourceMode, setSourceMode] = useState("prompt_only");
  const [textDensity, setTextDensity] = useState("medium-high");
  const [styleCandidateCount, setStyleCandidateCount] = useState(3);
  const [styleCandidateSlot, setStyleCandidateSlot] = useState<StyleCandidateSlot>("auto");
  const [visibleTextInput, setVisibleTextInput] = useState("");
  const [sourcesInput, setSourcesInput] = useState("");
  const [claimsInput, setClaimsInput] = useState("");
  const [dataSourcesInput, setDataSourcesInput] = useState("");
  const [styleNotesInput, setStyleNotesInput] = useState("");
  const [referenceImagePathInput, setReferenceImagePathInput] = useState("");
  const [referenceMode, setReferenceMode] = useState<ReferenceMode>("reference_context");
  const [ipSafetyMode, setIpSafetyMode] = useState<IpSafetyMode>("off");
  const [specGuidedEnabled, setSpecGuidedEnabled] = useState(false);
  const [templateSpecInput, setTemplateSpecInput] = useState("");
  const [slotSchemaInput, setSlotSchemaInput] = useState("");
  const [referenceStyleSpecInput, setReferenceStyleSpecInput] = useState("");
  const [designTokensInput, setDesignTokensInput] = useState("");
  const [specLockInput, setSpecLockInput] = useState("");
  const [referenceRolesInput, setReferenceRolesInput] = useState("");

  const [images, setImages] = useState<GeneratedImage[]>([]);
  const [selected, setSelected] = useState(0);
  const [rightMode, setRightMode] = useState<RightMode>("stage");
  const [generating, setGenerating] = useState(false);
  const [generationError, setGenerationError] = useState("");
  const [multiSelect, setMultiSelect] = useState(false);
  const [selectedForSubmit, setSelectedForSubmit] = useState<number[]>([]);
  const [submittingSelection, setSubmittingSelection] = useState(false);
  const [submitError, setSubmitError] = useState("");

  const stripRef = useRef<HTMLDivElement>(null);

  const effectiveSize = openAiSizeFromPreset(size, resolution);

  useEffect(() => {
    setProvider(connection.provider || "api");
  }, [connection.provider]);

  useEffect(() => {
    let cancelled = false;
    if (provider !== "codex") return;
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
  }, [provider]);

  useEffect(() => {
    let cancelled = false;
    if (provider !== "codex") return;
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
  }, [provider]);

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
    if (provider !== "codex" || templateId === "auto") return;
    const linked = findLinkedTemplateCardId(templateId, templateCards);
    if (linked && templateCardId !== linked) {
      setTemplateCardId(linked);
    }
  }, [provider, templateCardId, templateCards, templateId]);

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
    if (provider === "codex") {
      const effectiveSourceMode = sourceMode === "prompt_only" && dataSourcesInput.trim()
        ? "data_driven"
        : sourceMode === "prompt_only" && (sourcesInput.trim() || claimsInput.trim())
          ? "source_grounded"
          : sourceMode;
      body.rendering_mode = "baked_text";
      body.ip_safety_mode = ipSafetyMode;
      body.source_mode = effectiveSourceMode;
      body.text_density = textDensity;
      body.style_candidate_count = styleCandidateCount;
      if (language !== "auto") {
        body.language = language;
        body.output_language = language;
      }
      if (templateId !== "auto") {
        body.template_id = templateId;
      }
      if (templateCardId) {
        body.template_card_id = templateCardId;
      }
      if (styleCandidateSlot !== "auto") {
        body.style_candidate_index = Number(styleCandidateSlot);
      }
      const visibleText = parseVisibleTextInput(visibleTextInput);
      if (visibleText.visible_text_blocks !== undefined) {
        body.visible_text_blocks = visibleText.visible_text_blocks;
      }
      if (visibleText.locked_visible_text !== undefined) {
        body.locked_visible_text = visibleText.locked_visible_text;
      }
      const sources = parseSourcesInput(sourcesInput);
      if (sources !== undefined) {
        body.sources = sources;
      }
      const claims = parseClaimsInput(claimsInput);
      if (claims !== undefined) {
        body.claims = claims;
      }
      const dataSources = parseJsonOrRawText(dataSourcesInput);
      if (dataSources !== undefined) {
        body.data_sources = dataSources;
      }
      const styleNotes = styleNotesInput.trim();
      if (styleNotes) {
        body.visual_style = styleNotes;
        body.composition_guidance = inputLines(styleNotes);
      }
      const referenceImagePath = referenceImagePathInput.trim();
      if (referenceImagePath) {
        body.reference_mode = referenceMode;
        body.source_image_path = referenceImagePath;
        body.reference_image_path = referenceImagePath;
      }
      if (specGuidedEnabled) {
        body.spec_guided_enabled = true;
        const templateSpec = parseJsonOrRawText(templateSpecInput);
        if (templateSpec !== undefined) body.template_spec = templateSpec;
        const slotSchema = parseJsonOrRawText(slotSchemaInput);
        if (slotSchema !== undefined) body.slot_schema = slotSchema;
        const referenceStyleSpec = parseJsonOrRawText(referenceStyleSpecInput);
        if (referenceStyleSpec !== undefined) body.reference_style_spec = referenceStyleSpec;
        const designTokens = parseJsonOrRawText(designTokensInput);
        if (designTokens !== undefined) body.design_tokens = designTokens;
        const specLock = parseJsonOrRawText(specLockInput);
        if (specLock !== undefined) body.spec_lock = specLock;
        const referenceRoles = parseReferenceRolesInput(referenceRolesInput);
        if (referenceRoles !== undefined) body.reference_roles = referenceRoles;
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
    sourceMode,
    textDensity,
    styleCandidateCount,
    styleCandidateSlot,
    visibleTextInput,
    sourcesInput,
    claimsInput,
    dataSourcesInput,
    styleNotesInput,
    referenceImagePathInput,
    referenceMode,
    ipSafetyMode,
    specGuidedEnabled,
    templateSpecInput,
    slotSchemaInput,
    referenceStyleSpecInput,
    designTokensInput,
    specLockInput,
    referenceRolesInput,
    connection.apiKey,
    connection.baseUrl,
    connection.model
  ]);

  const changeProvider = useCallback((nextProvider: ImageGenerationProvider) => {
    setProvider(nextProvider);
    onConnectionChange?.({ ...connection, provider: nextProvider });
  }, [connection, onConnectionChange]);

  // Keep the selected thumbnail centered in the filmstrip. Clamping to the
  // scroll bounds means the first image rests at the left edge and the last at
  // the right edge automatically.
  useEffect(() => {
    if (rightMode !== "stage") return;
    const strip = stripRef.current;
    if (!strip) return;
    const thumb = strip.querySelector<HTMLElement>(`[data-thumb="${selected}"]`);
    if (!thumb) return;
    const target = thumb.offsetLeft - (strip.clientWidth - thumb.clientWidth) / 2;
    const max = strip.scrollWidth - strip.clientWidth;
    strip.scrollTo({ left: Math.max(0, Math.min(target, max)), behavior: "smooth" });
  }, [selected, rightMode, images.length]);

  // Arrow keys move the selection while in stage mode.
  useEffect(() => {
    if (rightMode !== "stage") return;
    function onKey(event: KeyboardEvent) {
      const tag = (event.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (event.key === "ArrowRight") setSelected((i) => Math.min(i + 1, images.length - 1));
      if (event.key === "ArrowLeft") setSelected((i) => Math.max(i - 1, 0));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [rightMode, images.length]);

  useEffect(() => {
    setSelectedForSubmit((items) => items.filter((index) => index >= 0 && index < images.length));
  }, [images.length]);

  const generate = useCallback(async () => {
    if (!prompt.trim()) return;
    setGenerating(true);
    setGenerationError("");
    try {
      const payload = await generateImages(request);
      const next = imagesFromResponse(payload, request, resolution);
      if (next.length === 0) {
        throw new Error(imageGenerationEmptyMessage(payload));
      }
      setImages(next);
      setSelected(0);
      setRightMode("stage");
      setMultiSelect(false);
      setSelectedForSubmit([]);
      setSubmitError("");
    } catch (error) {
      setGenerationError(error instanceof Error ? error.message : String(error));
    } finally {
      setGenerating(false);
    }
  }, [prompt, request, resolution]);

  const selectFromGrid = useCallback((index: number) => {
    setSelected(index);
    setRightMode("stage");
  }, []);

  const selectedForSubmitSet = useMemo(() => new Set(selectedForSubmit), [selectedForSubmit]);
  const selectedImagesForSubmit = useMemo(
    () => selectedForSubmit.map((index) => images[index]).filter((image): image is GeneratedImage => Boolean(image)),
    [images, selectedForSubmit]
  );

  const toggleGridSelection = useCallback((index: number) => {
    setSelectedForSubmit((items) => (
      items.includes(index)
        ? items.filter((item) => item !== index)
        : [...items, index].sort((a, b) => a - b)
    ));
  }, []);

  const submitSelectedImages = useCallback(async () => {
    if (selectedImagesForSubmit.length === 0 || submittingSelection) return;
    setSubmittingSelection(true);
    setSubmitError("");
    try {
      const form = new FormData();
      form.set("name", generatedBatchTitle(selectedImagesForSubmit));
      form.set("input_mode", "upload");
      form.set("max_concurrent_cases", "10");
      form.set("auto_run_svg_after_analysis", "false");
      for (const [index, image] of selectedImagesForSubmit.entries()) {
        await appendGeneratedImageToForm(form, image, index);
      }
      const detail = await createUploadBatch(form);
      setMultiSelect(false);
      setSelectedForSubmit([]);
      await onCreated(detail);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setSubmitError(message);
      onError(message);
    } finally {
      setSubmittingSelection(false);
    }
  }, [onCreated, onError, selectedImagesForSubmit, submittingSelection]);

  const current = images[selected];

  return (
    <div className="gen-root">
      <aside className="gen-controls">
        <div className="gen-form">
          <div className="gen-prompt-block">
            <textarea
              className="gen-prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="描述你想要生成的画面，例如：赛博朋克风格的城市夜景，霓虹灯倒映在湿润的街道上…"
              rows={5}
            />
          </div>

          <Field label="生成方式" hint={provider === "codex" ? "Codex SDK" : "Images API"}>
            <Segmented
              options={PROVIDERS}
              value={provider}
              onChange={(v) => changeProvider(v as ImageGenerationProvider)}
            />
          </Field>

          {provider === "codex" && (
            <div className="gen-codex-panel">
              <div className="gen-panel-head">
                <span className="gen-panel-title">PPT 图像策略</span>
                <span className="gen-panel-sub">模板、风格、来源和可见文字都会进入 Codex 提示词</span>
              </div>

              <Field label="模板选择 / 策略说明" hint={linkedTemplateCardId ? `联动 ${linkedTemplateCardId}` : "视觉系统"}>
                <div className="gen-template-picker-summary">
                  <div className="gen-template-picker-current">
                    <span className="gen-template-picker-kicker">
                      {templateId === "auto" ? "AUTO ROUTING" : selectedGalleryItem?.category || selectedTemplateOption?.group || "TEMPLATE"}
                    </span>
                    <strong>
                      {templateId === "auto"
                        ? "自动选择视觉系统"
                        : selectedGalleryItem?.template_name || selectedTemplateOption?.label || templateId}
                    </strong>
                    <p>
                      {templateId === "auto"
                        ? "后端会按 prompt 意图自动挑选候选模板。"
                        : selectedGalleryItem?.reason || selectedTemplateOption?.sub || "使用选中的模板策略拼接 Codex 提示词。"}
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

              <div className="gen-two-col">
                <Field label="来源模式" hint="事实策略">
                  <select className="gen-select" value={sourceMode} onChange={(e) => setSourceMode(e.target.value)}>
                    {SOURCE_MODES.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label} - {option.sub}
                      </option>
                    ))}
                  </select>
                </Field>

                <Field label="输出语言" hint="中文优先">
                  <select className="gen-select" value={language} onChange={(e) => setLanguage(e.target.value)}>
                    {LANGUAGE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label} - {option.sub}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>

              <div className="gen-two-col">
                <Field label="文字密度" hint="PPT 文本量">
                  <select className="gen-select" value={textDensity} onChange={(e) => setTextDensity(e.target.value)}>
                    {TEXT_DENSITIES.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label} - {option.sub}
                      </option>
                    ))}
                  </select>
                </Field>

                <Field label="候选数量" hint="模板候选池">
                  <Stepper value={styleCandidateCount} min={1} max={3} onChange={setStyleCandidateCount} />
                </Field>
              </div>

              <Field label="风格候选" hint={styleCandidateSlot === "auto" ? "多图时自动轮换候选" : "固定使用一个候选"}>
                <Segmented
                  options={STYLE_CANDIDATE_SLOTS}
                  value={styleCandidateSlot}
                  onChange={(v) => setStyleCandidateSlot(v as StyleCandidateSlot)}
                />
              </Field>

              <Field label="必须出现的文字" hint="JSON 或逐行">
                <textarea
                  className="gen-structured-textarea"
                  value={visibleTextInput}
                  onChange={(e) => setVisibleTextInput(e.target.value)}
                  placeholder={'例如：\n{"title":"Kimi 系列模型技术路线","takeaway":"MoE 扩展、训练优化与 Agent 能力是主线","labels":["MoE 架构","长上下文","工具调用"]}\n或逐行写必须出现的标题、栏目和标签'}
                  rows={5}
                />
              </Field>

              <Field label="事实来源" hint="URL、摘录或 JSON">
                <textarea
                  className="gen-structured-textarea"
                  value={sourcesInput}
                  onChange={(e) => setSourcesInput(e.target.value)}
                  placeholder="逐行粘贴来源 URL、官方资料摘录、论文 DOI，或直接粘贴 sources JSON。没有来源时不要让模型编数字、日期、排名。"
                  rows={4}
                />
              </Field>

              <Field label="事实清单" hint="逐行一个 claim">
                <textarea
                  className="gen-structured-textarea"
                  value={claimsInput}
                  onChange={(e) => setClaimsInput(e.target.value)}
                  placeholder="例如：Kimi K2 是 MoE 模型。\n例如：不要编造 benchmark 分数，只展示已提供的结论。"
                  rows={3}
                />
              </Field>

              <Field label="数据源" hint="表格、CSV 摘要或 JSON">
                <textarea
                  className="gen-structured-textarea"
                  value={dataSourcesInput}
                  onChange={(e) => setDataSourcesInput(e.target.value)}
                  placeholder="粘贴表格、CSV 摘要、指标说明或 data_sources JSON。图表和数字只应来自这里。"
                  rows={3}
                />
              </Field>

              <Field label="风格备注" hint="品牌、参考、禁忌">
                <textarea
                  className="gen-structured-textarea"
                  value={styleNotesInput}
                  onChange={(e) => setStyleNotesInput(e.target.value)}
                  placeholder="例如：偏黑色科技发布会风格，中文标题要大，避免纯卡片布局，避免英文通用标题。"
                  rows={3}
                />
              </Field>

              <Field label="IP 安全策略" hint="默认关闭">
                <Segmented
                  options={IP_SAFETY_MODES}
                  value={ipSafetyMode}
                  onChange={(v) => setIpSafetyMode(v as IpSafetyMode)}
                />
              </Field>

              <Field label="Spec-guided / Design lock" hint={specGuidedEnabled ? "已启用" : "关闭"}>
                <label className="gen-checkbox-row">
                  <input
                    type="checkbox"
                    checked={specGuidedEnabled}
                    onChange={(e) => setSpecGuidedEnabled(e.target.checked)}
                  />
                  <span>把 template_spec / slot_schema / reference_style_spec 作为结构化约束传给后端</span>
                </label>
              </Field>

              {specGuidedEnabled && (
                <div className="gen-spec-panel">
                  <Field label="template_spec" hint="JSON">
                    <textarea
                      className="gen-structured-textarea"
                      value={templateSpecInput}
                      onChange={(e) => setTemplateSpecInput(e.target.value)}
                      placeholder='{"schema":"drawai.ppt_template_spec.v1","slide_size":{"width_in":13.333,"height_in":7.5},"layouts":[...]}'
                      rows={4}
                    />
                  </Field>
                  <Field label="slot_schema" hint="JSON">
                    <textarea
                      className="gen-structured-textarea"
                      value={slotSchemaInput}
                      onChange={(e) => setSlotSchemaInput(e.target.value)}
                      placeholder='{"slots":[{"id":"title","role":"headline"},{"id":"main_flow","role":"process"}]}'
                      rows={3}
                    />
                  </Field>
                  <Field label="reference_style_spec" hint="JSON">
                    <textarea
                      className="gen-structured-textarea"
                      value={referenceStyleSpecInput}
                      onChange={(e) => setReferenceStyleSpecInput(e.target.value)}
                      placeholder='{"reference_roles":[{"role":"layout_reference"},{"role":"color_reference"}],"design_tokens":{...}}'
                      rows={4}
                    />
                  </Field>
                  <div className="gen-two-col">
                    <Field label="design_tokens" hint="JSON">
                      <textarea
                        className="gen-structured-textarea"
                        value={designTokensInput}
                        onChange={(e) => setDesignTokensInput(e.target.value)}
                        placeholder='{"palette":["yellow","white","charcoal"],"typography":"dense Chinese slide labels"}'
                        rows={3}
                      />
                    </Field>
                    <Field label="spec_lock" hint="JSON">
                      <textarea
                        className="gen-structured-textarea"
                        value={specLockInput}
                        onChange={(e) => setSpecLockInput(e.target.value)}
                        placeholder='{"lock_canvas":true,"lock_layout_roles":true}'
                        rows={3}
                      />
                    </Field>
                  </div>
                  <Field label="reference_roles" hint="JSON 或逐行">
                    <textarea
                      className="gen-structured-textarea"
                      value={referenceRolesInput}
                      onChange={(e) => setReferenceRolesInput(e.target.value)}
                      placeholder={"layout_reference\nstyle_reference\ncolor_reference\ntypography_reference"}
                      rows={4}
                    />
                  </Field>
                </div>
              )}

              <Field label="参考图模式" hint={referenceImagePathInput.trim() ? referenceMode : "填参考图路径后生效"}>
                <select className="gen-select" value={referenceMode} onChange={(e) => setReferenceMode(e.target.value as ReferenceMode)}>
                  {REFERENCE_MODES.map((mode) => (
                    <option key={mode.value} value={mode.value}>
                      {mode.label} - {mode.sub}
                    </option>
                  ))}
                </select>
              </Field>

              <Field label="参考图路径" hint="Codex edit / LocalImageInput">
                <input
                  className="gen-input"
                  value={referenceImagePathInput}
                  onChange={(e) => setReferenceImagePathInput(e.target.value)}
                  placeholder="C:\\Users\\...\\reference.png；填写后 Codex 使用真实 image edit 路径"
                />
              </Field>
            </div>
          )}

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

          <Field label="质量" hint="生成质量">
            <Segmented
              options={QUALITIES.map((q) => ({ value: q.value, label: q.label }))}
              value={quality}
              onChange={(v) => setQuality(v as Quality)}
            />
          </Field>

          <Field label="背景" hint="背景模式">
            <Segmented
              options={BACKGROUNDS.map((b) => ({ value: b.value, label: b.label }))}
              value={background}
              onChange={(v) => setBackground(v as Background)}
            />
          </Field>
        </div>

        <footer className="gen-controls-foot">
          <div className="gen-generate-row">
            <div className="gen-resolution-compact">
              <span className="gen-field-label">像素等级</span>
              <Segmented
                options={RESOLUTIONS.map((r) => ({ value: r.value, label: r.label }))}
                value={resolution}
                onChange={(v) => setResolution(v as Resolution)}
              />
            </div>
            <div className="gen-count-compact" aria-label="生成数量">
              <Stepper value={count} min={1} max={10} onChange={setCount} />
            </div>
            <button
              type="button"
              className={`primary gen-generate${generating ? " running" : ""}`}
              onClick={generate}
              disabled={generating || !prompt.trim()}
            >
              {generating ? <span className="button-spinner" /> : null}
              {generating ? "生成中…" : "生成"}
            </button>
          </div>
          {generationError && <p className="gen-error">{generationError}</p>}
        </footer>
      </aside>

      <section className={`gen-display ${rightMode}`}>
        {rightMode === "stage" ? (
          <>
            <div className="gen-stage">
              {current ? (
                <figure className={`gen-stage-figure${current.transparent ? " checker" : ""}`}>
                  <img src={current.url} alt={current.prompt || "生成图"} />
                </figure>
              ) : (
                <div className="gen-empty">还没有图片，填写提示词后点击生成</div>
              )}
              {current && (
                <div className="gen-stage-meta">
                  <span className="gen-meta-chip">{current.size}</span>
                  <span className="gen-meta-chip">{current.resolution.toUpperCase()}</span>
                  <span className="gen-meta-chip">{current.format.toUpperCase()}</span>
                  <span className="gen-meta-chip">{current.provider === "codex" ? "Codex" : "API"}</span>
                  <span className="gen-meta-chip">质量 {optionLabel(QUALITIES, current.quality)}</span>
                  <span className="gen-meta-index">
                    {selected + 1} / {images.length}
                  </span>
                  <a className="gen-meta-download" href={current.url} download={`${current.id}.${current.format}`}>
                    下载
                  </a>
                </div>
              )}
            </div>

            <div className="gen-filmstrip-wrap">
              <div className="gen-filmstrip" ref={stripRef}>
                {images.map((img, i) => (
                  <button
                    key={img.id}
                    type="button"
                    data-thumb={i}
                    className={`gen-thumb${i === selected ? " active" : ""}${
                      img.transparent ? " checker" : ""
                    }`}
                    onClick={() => setSelected(i)}
                  >
                    <img src={img.url} alt="" />
                  </button>
                ))}
              </div>
              <button
                type="button"
                className="gen-expand"
                title="全屏缩略图预览"
                onClick={() => setRightMode("grid")}
              >
                <ExpandIcon />
              </button>
            </div>
          </>
        ) : (
          <div className="gen-grid-mode">
            <div className="gen-grid-head">
              <div className="gen-grid-title">
                <span className="gen-grid-count">{images.length} 张图片</span>
                {multiSelect && <span className="gen-grid-selected">{selectedForSubmit.length} 张已选</span>}
              </div>
              <div className="gen-grid-actions">
                <button
                  type="button"
                  className={`gen-multi-toggle${multiSelect ? " active" : ""}`}
                  onClick={() => {
                    setMultiSelect((value) => !value);
                    setSelectedForSubmit([]);
                    setSubmitError("");
                  }}
                >
                  {multiSelect ? "取消多选" : "多选"}
                </button>
                <button
                  type="button"
                  className={`gen-submit-selection${submittingSelection ? " running" : ""}`}
                  disabled={!multiSelect || selectedImagesForSubmit.length === 0 || submittingSelection}
                  onClick={() => void submitSelectedImages()}
                >
                  {submittingSelection ? <span className="button-spinner" /> : null}
                  {submittingSelection ? "提交中" : "提交"}
                </button>
                <button type="button" className="gen-collapse" onClick={() => setRightMode("stage")}>
                  <CollapseIcon />
                  <span>退出</span>
                </button>
              </div>
            </div>
            {submitError && <p className="gen-submit-error">{submitError}</p>}
            <div className="gen-grid">
              {images.map((img, i) => (
                <button
                  key={img.id}
                  type="button"
                  className={`gen-grid-cell${i === selected ? " active" : ""}${selectedForSubmitSet.has(i) ? " selected" : ""}${
                    img.transparent ? " checker" : ""
                  }`}
                  onClick={() => {
                    if (multiSelect) {
                      toggleGridSelection(i);
                      return;
                    }
                    selectFromGrid(i);
                  }}
                  aria-pressed={multiSelect ? selectedForSubmitSet.has(i) : undefined}
                >
                  <img src={img.url} alt="" />
                  <span className="gen-grid-index">{i + 1}</span>
                  {multiSelect && (
                    <span className="gen-grid-check" aria-hidden="true" />
                  )}
                </button>
              ))}
            </div>
          </div>
        )}
      </section>
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

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="gen-field">
      <span className="gen-field-head">
        <span className="gen-field-label">{label}</span>
        {hint && <span className="gen-field-hint">{hint}</span>}
      </span>
      {children}
    </label>
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

function Segmented({
  options,
  value,
  onChange
}: {
  options: Array<{ value: string; label: string; sub?: string }>;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="gen-segmented" role="group">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          className={value === opt.value ? "active" : ""}
          onClick={() => onChange(opt.value)}
        >
          <span>{opt.label}</span>
          {opt.sub && <em>{opt.sub}</em>}
        </button>
      ))}
    </div>
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

function ExpandIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M9 3H3v6M15 3h6v6M9 21H3v-6M15 21h6v-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CollapseIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M4 10h6V4M20 10h-6V4M4 14h6v6M20 14h-6v6" strokeLinecap="round" strokeLinejoin="round" />
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

function optionLabel<T extends string>(options: Array<{ value: T; label: string }>, value: T): string {
  return options.find((option) => option.value === value)?.label || value;
}

function openAiSizeFromPreset(ratio: string, resolution: Resolution): string {
  return OPENAI_SIZE_BY_RATIO[resolution]?.[ratio] || "1024x1024";
}

function parseVisibleTextInput(value: string): { visible_text_blocks?: unknown; locked_visible_text?: string[] } {
  const parsed = parseJsonInput(value);
  if (parsed !== undefined) {
    return { visible_text_blocks: parsed };
  }
  const lines = inputLines(value);
  return lines.length ? { locked_visible_text: lines } : {};
}

function parseSourcesInput(value: string): unknown | undefined {
  const parsed = parseJsonInput(value);
  if (parsed !== undefined) return parsed;
  const lines = inputLines(value);
  if (!lines.length) return undefined;
  return lines.map((line, index) => {
    const url = line.match(/https?:\/\/\S+/)?.[0] || "";
    return {
      title: url || `source-${index + 1}`,
      url,
      evidence: line
    };
  });
}

function parseClaimsInput(value: string): unknown | undefined {
  const parsed = parseJsonInput(value);
  if (parsed !== undefined) return parsed;
  const lines = inputLines(value);
  return lines.length ? lines.map((claim) => ({ claim })) : undefined;
}

function parseJsonOrRawText(value: string): unknown | undefined {
  const parsed = parseJsonInput(value);
  if (parsed !== undefined) return parsed;
  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
}

function parseReferenceRolesInput(value: string): unknown | undefined {
  const parsed = parseJsonInput(value);
  if (parsed !== undefined) return parsed;
  const lines = inputLines(value);
  return lines.length ? lines.map((role) => ({ role })) : undefined;
}

function parseJsonInput(value: string): unknown | undefined {
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) return undefined;
  try {
    return JSON.parse(trimmed);
  } catch {
    return undefined;
  }
}

function inputLines(value: string): string[] {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function imageModelForProvider(provider: ImageGenerationProvider, configuredModel: string): string {
  const model = configuredModel.trim();
  if (provider === "codex" && model === DEFAULT_MODEL) return "";
  return model || DEFAULT_MODEL;
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
  resolution: Resolution
): GeneratedImage[] {
  const candidates = imageCandidates(payload);
  const responseProvider = imageGenerationProviderFromResponse(payload, request.provider);
  return candidates.flatMap((item, index) => {
    const urls = imageUrlsFromCandidate(item, request.output_format);
    if (!urls.length) return [];
    const record = objectRecord(item);
    return urls.map((url, urlIndex) => ({
      id: String(record.id || record.image_id || record.created || `image-${Date.now()}-${index + 1}-${urlIndex + 1}`),
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
