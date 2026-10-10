import { useEffect, useState } from "react";
import type { StudioRuntime } from "./runtime";
import type { CatalogResult, ReferenceRole, VisualTemplate } from "./types";
import { categoryName, roleLabels } from "./labels";
import { Icon, Dialog } from "./components";

export default function TemplateLibrary({
  runtime,
  onUse,
  canUse,
  selectedIds,
}: {
  runtime: StudioRuntime;
  onUse: (template: VisualTemplate, role: ReferenceRole) => Promise<void>;
  canUse: boolean;
  selectedIds: string[];
}) {
  const [result, setResult] = useState<CatalogResult>();
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [withImages, setWithImages] = useState(true);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [detail, setDetail] = useState<VisualTemplate>();
  const [role, setRole] = useState<ReferenceRole>("structure");
  const [adding, setAdding] = useState(false);
  useEffect(() => {
    let active = true;
    const timer = setTimeout(() => {
      setLoading(true);
      setError("");
      runtime
        .call<CatalogResult>("drawai_templates", {
          action: "search",
          query,
          category,
          with_images: withImages,
          offset,
          limit: 36,
        })
        .then((value) => {
          if (active) setResult(value);
        })
        .catch((err) => {
          if (active) setError(err.message);
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    }, 180);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [runtime, query, category, withImages, offset]);
  async function choose() {
    if (!detail) return;
    setAdding(true);
    setError("");
    try {
      await onUse(detail, role);
      setDetail(undefined);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setAdding(false);
    }
  }
  return (
    <div className="studio-library">
      <div className="studio-library-heading">
        <div>
          <span className="studio-eyebrow">VISUAL REFERENCES</span>
          <h1>视觉参考模板库</h1>
          <p>选择信息结构与视觉风格，与自己的 PPT 格式模板一起使用。</p>
        </div>
        <span className="studio-count">
          {result?.library_count ?? "—"} 张配方 · {result?.image_count ?? "—"}{" "}
          张图片参考
        </span>
      </div>
      <div className="studio-library-tools">
        <label className="studio-search">
          <Icon name="search" />
          <input
            aria-label="搜索模板"
            placeholder="搜索用途、结构或风格，如 ablation、流程"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setOffset(0);
            }}
          />
        </label>
        <select
          aria-label="模板分类"
          value={category}
          onChange={(e) => {
            setCategory(e.target.value);
            setOffset(0);
          }}
        >
          <option value="">全部分类</option>
          {result?.categories.map((key) => (
            <option value={key} key={key}>
              {categoryName(key)}
            </option>
          ))}
        </select>
        <label className="studio-checkbox">
          <input
            type="checkbox"
            checked={withImages}
            onChange={(e) => {
              setWithImages(e.target.checked);
              setOffset(0);
            }}
          />
          有参考图片
        </label>
      </div>
      {error && (
        <div role="alert" className="studio-notice error">
          {error}
        </div>
      )}
      <div className="studio-library-summary">
        <span>
          {loading ? "正在读取模板…" : `找到 ${result?.total ?? 0} 张模板`}
        </span>
        <span>示例中的内容仅作呈现参考</span>
      </div>
      <div className="studio-template-grid" aria-busy={loading}>
        {result?.templates.map((card) => (
          <button
            type="button"
            className="studio-template-card"
            key={card.id}
            onClick={() => setDetail(card)}
          >
            <div className="studio-template-image">
              {card.assets[0] ? (
                <img
                  src={
                    card.assets[0].image_urls?.card ||
                    card.assets[0].original_url
                  }
                  alt={card.name}
                  loading="lazy"
                />
              ) : (
                <div className="studio-recipe-cover">
                  <Icon name="file" size={28} />
                  <span>配方模板</span>
                </div>
              )}
              {selectedIds.includes(card.id) && (
                <span className="studio-selected-mark">
                  <Icon name="check" size={13} />
                  已选用
                </span>
              )}
            </div>
            <div className="studio-template-copy">
              <small>{categoryName(card.category)}</small>
              <strong>{card.name}</strong>
              <span>{card.layout_archetypes.slice(0, 2).join(" · ")}</span>
            </div>
          </button>
        ))}
      </div>
      {!loading && result?.total === 0 && (
        <div className="studio-empty compact">
          <Icon name="search" size={32} />
          <h3>没有匹配的模板</h3>
          <p>尝试调整关键词或分类。</p>
        </div>
      )}
      <div className="studio-pagination">
        <button
          disabled={!offset || loading}
          onClick={() => setOffset(Math.max(0, offset - 36))}
        >
          上一页
        </button>
        <span>
          {Math.floor(offset / 36) + 1} /{" "}
          {Math.max(1, Math.ceil((result?.total || 0) / 36))}
        </span>
        <button
          disabled={offset + 36 >= (result?.total || 0) || loading}
          onClick={() => setOffset(offset + 36)}
        >
          下一页
        </button>
      </div>
      {detail && (
        <Dialog title={detail.name} onClose={() => setDetail(undefined)} wide>
          <div className="studio-template-detail">
            {detail.assets[0] && (
              <img
                className="studio-template-full"
                src={
                  detail.assets[0].image_urls?.modal ||
                  detail.assets[0].original_url
                }
                alt={detail.name}
              />
            )}
            <div className="studio-detail-body">
              <span className="studio-tag">
                {categoryName(detail.category)}
              </span>
              <h3>呈现配方</h3>
              <p>{detail.prompt_recipe}</p>
              <div className="studio-tags">
                {detail.layout_archetypes.map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
              <details>
                <summary>查看来源与使用说明</summary>
                {detail.provenance?.map((source, i) => (
                  <p key={i}>
                    {source.source_url ? (
                      <a
                        href={source.source_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {source.source_name || source.source || "来源"}
                      </a>
                    ) : (
                      source.source_name || source.source
                    )}
                    <small>{source.license_note}</small>
                  </p>
                ))}
              </details>
            </div>
          </div>
          <footer>
            <label>
              参考用途
              <select
                aria-label="模板参考用途"
                value={role}
                onChange={(e) => setRole(e.target.value as ReferenceRole)}
              >
                <option value="structure">{roleLabels.structure}</option>
                <option value="style">{roleLabels.style}</option>
              </select>
            </label>
            <button
              className="primary"
              disabled={!canUse || adding}
              onClick={() => void choose()}
            >
              <Icon name="plus" />
              {adding
                ? "正在添加…"
                : canUse
                  ? "加入当前项目"
                  : "先创建 PPT 项目"}
            </button>
          </footer>
        </Dialog>
      )}
    </div>
  );
}
