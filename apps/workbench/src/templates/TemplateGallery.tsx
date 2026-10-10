import { useEffect, useRef, useState } from "react";
import logo from "/drawai_image.png?inline";
import { connectTemplates, selectionPrompt, selectionRequest, type TemplateRuntime } from "./runtime";
import { categoryName } from "./labels";
import type { CatalogResult, TemplateFilters, TemplateSelection, TemplateView, VisualTemplate } from "./types";
import "./templates.css";

function Mark({ name }: { name: "search" | "check" | "close" | "arrow" | "copy" }) {
  const paths = { search: "M15.5 15.5 21 21M18 10.5a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0", check: "m4 12 5 5L20 6", close: "m6 6 12 12M18 6 6 18", arrow: "M4 12h16m-6-6 6 6-6 6", copy: "M8 8h12v13H8zM16 8V3H3v13h5" };
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>;
}

function TemplateDetail({ template, selected, onChoose, onClose }: {
  template: VisualTemplate; selected?: TemplateSelection;
  onChoose: (role: TemplateSelection["role"]) => void; onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [role, setRole] = useState<TemplateSelection["role"]>(selected?.role || "structure");
  useEffect(() => { dialog.current?.showModal(); }, []);
  return <dialog className="template-dialog" ref={dialog} onCancel={(event) => { event.preventDefault(); onClose(); }} aria-labelledby="template-detail-title">
    <header><span>{categoryName(template.category)}</span><button className="template-icon" aria-label="关闭模板详情" onClick={onClose} autoFocus><Mark name="close" /></button></header>
    {template.assets[0] && <img className="template-detail-image" src={template.assets[0].image_urls?.modal || template.assets[0].original_url} alt={template.name} />}
    <div className="template-detail-copy">
      <h2 id="template-detail-title">{template.name}</h2>
      <div className="template-tags">{template.layout_archetypes.map((tag) => <span key={tag}>{tag}</span>)}</div>
      <h3>设计配方</h3><p>{template.prompt_recipe}</p>
      {template.source_policy && <p className="template-source-policy">{template.source_policy}</p>}
      <details><summary>来源与使用说明</summary>{template.provenance?.map((source, index) => <div key={index}>
        {source.source_url ? <a href={source.source_url} target="_blank" rel="noreferrer">{source.source_name || source.source || "来源"}</a> : <strong>{source.source_name || source.source}</strong>}
        <p>{source.license_note}</p>
      </div>)}</details>
    </div>
    <footer><label>参考用途<select aria-label="参考用途" value={role} onChange={(event) => setRole(event.target.value as TemplateSelection["role"])}><option value="structure">信息结构</option><option value="style">视觉风格</option></select></label>
      <button className="template-primary" onClick={() => { onChoose(role); onClose(); }}><Mark name="check" />{selected ? "更新参考用途" : "选为参考"}</button></footer>
  </dialog>;
}

export default function TemplateGallery() {
  const [runtime, setRuntime] = useState<TemplateRuntime>();
  const [filters, setFilters] = useState<TemplateFilters>({ query: "", category: "", with_images: true, offset: 0, limit: 12 });
  const [result, setResult] = useState<CatalogResult>();
  const [selected, setSelected] = useState<TemplateSelection[]>([]);
  const [detail, setDetail] = useState<VisualTemplate>();
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [copyText, setCopyText] = useState("");
  useEffect(() => {
    let active = true;
    let unsubscribe: (() => void) | undefined;
    connectTemplates().then((value) => {
      if (!active) return;
      setRuntime(value);
      const apply = (view: TemplateView) => {
        if (view.view) setFilters({ with_images: true, offset: 0, limit: value.mode === "codex" ? 6 : 12, ...view.view });
        if (view.result) setResult(view.result);
      };
      apply(value.initialView || { view: {} });
      unsubscribe = value.onView(apply);
    }).catch((reason) => { if (active) { setError(reason.message); setLoading(false); } });
    return () => { active = false; unsubscribe?.(); };
  }, []);
  useEffect(() => {
    if (!runtime) return;
    let active = true;
    setLoading(true);
    setError("");
    const timer = setTimeout(() => {
      runtime.search(filters).then((data) => { if (active) setResult(data); })
        .catch((reason) => { if (active) setError(reason.message); })
        .finally(() => { if (active) setLoading(false); });
    }, 160);
    return () => { active = false; clearTimeout(timer); };
  }, [runtime, filters]);
  function filter(values: Partial<TemplateFilters>) { setFilters((current) => ({ ...current, ...values, offset: 0 })); }
  function choose(template: VisualTemplate, role: TemplateSelection["role"] = "structure") {
    setSelected((current) => [...current.filter((item) => item.template.id !== template.id), { template, role }]);
    setNotice("");
  }
  function toggle(template: VisualTemplate) {
    if (selected.some((item) => item.template.id === template.id)) setSelected((current) => current.filter((item) => item.template.id !== template.id));
    else choose(template);
  }
  async function copy() {
    const prompt = selectionPrompt(selected);
    if (!navigator.clipboard?.writeText) { setCopyText(prompt); return; }
    try { await navigator.clipboard.writeText(prompt); setNotice("已复制，粘贴到 Codex 后继续当前任务。"); }
    catch { setCopyText(prompt); }
  }
  async function send() {
    if (!runtime) return;
    setSending(true); setError("");
    try {
      await runtime.selection(selectionRequest(selected));
      await runtime.send(selectionPrompt(selected));
      setNotice("已将模板参考发送到当前对话。");
    } catch (reason) { setError((reason as Error).message); }
    finally { setSending(false); }
  }
  const offset = filters.offset || 0;
  const limit = filters.limit || 12;
  return <main className={`drawai-templates ${runtime?.mode === "codex" ? "is-inline" : "is-website"}`}>
    <header className="template-header"><div className="template-brand"><img src={logo} alt="" /><strong>DrawAI</strong><span>模板参考</span></div>
      <span className="template-library-count">{result ? `${result.library_count} 个参考` : "模板库"}</span></header>
    <section className="template-intro"><span className="template-kicker">给内容一个合适的呈现方式</span><h1>选好参考，再做 PPT。</h1><p>浏览版式与视觉风格，选择适合当前内容的参考。</p></section>
    <div className="template-filters"><label className="template-search"><Mark name="search" /><input aria-label="搜索模板" placeholder="搜索用途、结构或风格" value={filters.query || ""} onChange={(event) => filter({ query: event.target.value, template_ids: undefined })} /></label>
      <select aria-label="模板分类" value={filters.category || ""} onChange={(event) => filter({ category: event.target.value, template_ids: undefined })}><option value="">全部分类</option>{result?.categories.map((key) => <option key={key} value={key}>{categoryName(key)}</option>)}</select>
      <label className="template-checkbox"><input type="checkbox" checked={Boolean(filters.with_images)} onChange={(event) => filter({ with_images: event.target.checked })} />有参考图片</label></div>
    <div className="template-results-line"><span>{loading ? "正在读取模板…" : `找到 ${result?.total ?? 0} 个参考`}</span>
      {filters.template_ids && <button className="template-text-button" onClick={() => filter({ template_ids: undefined, query: "", category: "" })}>浏览全部模板</button>}
      <span>示例内容仅作呈现参考</span></div>
    {error && <p className="template-error" role="alert">{error}</p>}
    <section className="template-grid" aria-label="模板列表" aria-busy={loading}>
      {result?.templates.map((template) => {
        const chosen = selected.find((item) => item.template.id === template.id);
        return <article className={`template-card ${chosen ? "is-selected" : ""}`} key={template.id}>
          <button className="template-preview" onClick={() => setDetail(template)} aria-label={`查看模板 ${template.name}`}>
            {template.assets[0] ? <img src={template.assets[0].image_urls?.card || template.assets[0].original_url} alt={template.name} loading="lazy" /> : <div className="template-recipe"><span>{categoryName(template.category)}</span><strong>{template.layout_archetypes[0] || template.name}</strong><small>设计配方</small></div>}
          </button>
          <div className="template-card-copy"><span>{categoryName(template.category)}</span><h2><button onClick={() => setDetail(template)}>{template.name}</button></h2><p>{template.layout_archetypes.slice(0, 2).join(" · ")}</p>
            <button className="template-select" aria-label={`${chosen ? "取消选择" : "选择模板"} ${template.name}`} aria-pressed={Boolean(chosen)} onClick={() => toggle(template)}>{chosen ? <><Mark name="check" />{chosen.role === "style" ? "已选 · 视觉风格" : "已选 · 信息结构"}</> : "选为参考"}</button></div>
        </article>;
      })}
    </section>
    {!loading && !error && !result?.total && <div className="template-empty"><Mark name="search" /><h2>没有匹配的参考</h2><p>试试其他关键词，或调整分类。</p></div>}
    <nav className="template-pagination" aria-label="模板分页"><button disabled={!offset || loading} onClick={() => setFilters((current) => ({ ...current, offset: Math.max(0, offset - limit) }))}>上一页</button><span>{Math.floor(offset / limit) + 1} / {Math.max(1, Math.ceil((result?.total || 0) / limit))}</span><button disabled={offset + limit >= (result?.total || 0) || loading} onClick={() => setFilters((current) => ({ ...current, offset: offset + limit }))}>下一页</button></nav>
    <footer className="template-selection-bar"><div><strong>{selected.length ? `已选 ${selected.length} 个参考` : "选择一个或多个参考"}</strong><p>{selected.length ? selected.map((item) => item.template.name).join(" · ") : "模板可以分别用于信息结构或视觉风格。"}</p></div>
      <div className="template-selection-actions"><button disabled={!selected.length} onClick={() => void copy()}><Mark name="copy" />复制选择说明</button>
        {runtime?.canSend && <button className="template-primary" disabled={!selected.length || sending} onClick={() => void send()}>{sending ? "正在发送…" : "用于当前任务"}<Mark name="arrow" /></button>}</div>
      {notice && <p className="template-notice" role="status">{notice}</p>}
    </footer>
    {copyText && <div className="template-copy-fallback"><label>将以下说明复制到 Codex<textarea aria-label="模板选择说明" readOnly value={copyText} onFocus={(event) => event.target.select()} /></label><button onClick={() => setCopyText("")}>关闭说明</button></div>}
    {detail && <TemplateDetail key={detail.id} template={detail} selected={selected.find((item) => item.template.id === detail.id)} onChoose={(role) => choose(detail, role)} onClose={() => setDetail(undefined)} />}
  </main>;
}
