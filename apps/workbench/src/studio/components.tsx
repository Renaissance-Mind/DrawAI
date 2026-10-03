import { useEffect, useRef, useState, type ReactNode } from "react";
import type { StudioRuntime } from "./runtime";
import type { StudioAsset } from "./types";

export function Icon({ name, size = 18, className }: { name: string; size?: number; className?: string }) {
  const shapes: Record<string, ReactNode> = {
    plus: <path d="M12 5v14M5 12h14" />,
    close: <path d="m6 6 12 12M18 6 6 18" />,
    grid: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </>
    ),
    image: (
      <>
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <circle cx="8" cy="9" r="1.5" />
        <path d="m3 17 5-5 4 4 4-6 5 7" />
      </>
    ),
    slides: (
      <>
        <rect x="3" y="3" width="18" height="14" rx="2" />
        <path d="M12 17v4m-5 0h10M7 8h10M7 12h6" />
      </>
    ),
    clock: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 6v6l4 2" />
      </>
    ),
    upload: (
      <>
        <path d="M12 16V3m-5 5 5-5 5 5M4 15v5h16v-5" />
      </>
    ),
    download: <path d="M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4" />,
    sparkle: (
      <>
        <path d="m12 3 2.6 6.4L21 12l-6.4 2.6L12 21l-2.6-6.4L3 12l6.4-2.6L12 3Z" />
        <path d="M20 2v4m-2-2h4" />
      </>
    ),
    file: (
      <>
        <path d="M14 3H5v18h14V8l-5-5Zm0 0v5h5M8 12h8M8 16h6" />
      </>
    ),
    trash: (
      <>
        <path d="M3 6h18M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7m4-7v7" />
      </>
    ),
    copy: (
      <>
        <rect x="8" y="8" width="12" height="13" rx="2" />
        <path d="M16 8V3H3v13h5" />
      </>
    ),
    search: (
      <>
        <circle cx="10.5" cy="10.5" r="6.5" />
        <path d="m16 16 5 5" />
      </>
    ),
    arrowUp: <path d="M12 20V4m-6 6 6-6 6 6" />,
    arrowDown: <path d="M12 4v16m-6-6 6 6 6-6" />,
    settings: (
      <>
        <path d="M4 7h16M4 17h16" />
        <circle cx="9" cy="7" r="3" />
        <circle cx="15" cy="17" r="3" />
      </>
    ),
    check: <path d="m4 12 5 5L20 6" />,
    send: <path d="m3 3 18 9-18 9 4-9-4-9Zm4 9h14" />,
    refresh: (
      <>
        <path d="M20 9a8 8 0 1 0 0 6M20 3v6h-6" />
      </>
    ),
    crop: <path d="M7 3v14h14M3 7h14v14M7 7h10v10" />,
    compare: (
      <>
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <path d="M12 4v16m-6-7 3-3m-3 3 3 3m9-3-3-3m3 3-3 3" />
      </>
    ),
    menu: <path d="M4 6h16M4 12h16M4 18h16" />,
  };
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.65"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {shapes[name] || shapes.file}
    </svg>
  );
}
export function IconButton({
  title,
  icon,
  onClick,
  disabled = false,
}: {
  title: string;
  icon: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      className="studio-icon-button"
      title={title}
      aria-label={title}
      onClick={onClick}
      disabled={disabled}
    >
      <Icon name={icon} />
    </button>
  );
}

const assetImages = new Map<string, Promise<string>>();
export function AssetImage({
  runtime,
  projectId,
  assetId,
  alt,
  className = "",
  onLoad,
}: {
  runtime: StudioRuntime;
  projectId: string;
  assetId: string;
  alt: string;
  className?: string;
  onLoad?: () => void;
}) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setUrl("");
    setError("");
    const key = `${projectId}/${assetId}`;
    let value = assetImages.get(key);
    if (!value) {
      value = runtime
        .call<{
          asset: StudioAsset;
          data_base64: string;
        }>("drawai_artifact", {
          action: "read",
          project_id: projectId,
          asset_id: assetId,
        })
        .then(
          (data) => `data:${data.asset.mime_type};base64,${data.data_base64}`,
        );
      assetImages.set(key, value);
    }
    value
      .then((result) => {
        if (active) setUrl(result);
      })
      .catch((err) => {
        assetImages.delete(key);
        if (active) setError(String(err.message));
      });
    return () => {
      active = false;
    };
  }, [runtime, projectId, assetId]);
  if (error)
    return (
      <div className="studio-image-error" title={error}>
        图片读取失败
      </div>
    );
  return url ? (
    <img src={url} alt={alt} className={className} onLoad={onLoad} />
  ) : (
    <span className="studio-image-loading" aria-label="图片读取中">
      <span className="button-spinner" />
    </span>
  );
}

export function Dialog({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const panel = useRef<HTMLElement>(null);
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const focusable = () =>
      Array.from(
        panel.current?.querySelectorAll<HTMLElement>(
          'button:not(:disabled), input:not(:disabled), textarea:not(:disabled), select:not(:disabled), a[href], [tabindex="0"]',
        ) || [],
      ).filter((element) => element.offsetParent !== null);
    if (!panel.current?.contains(document.activeElement))
      focusable()[0]?.focus();
    const handle = (event: KeyboardEvent) => {
      if (event.key === "Escape") close.current();
      if (event.key === "Tab") {
        const items = focusable();
        const first = items[0];
        const last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    window.addEventListener("keydown", handle);
    return () => {
      window.removeEventListener("keydown", handle);
      if (previous && document.contains(previous)) previous.focus();
    };
  }, []);
  return (
    <div
      className="studio-dialog-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <section
        ref={panel}
        className={`studio-dialog ${wide ? "wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header>
          <h2>{title}</h2>
          <IconButton title="关闭" icon="close" onClick={onClose} />
        </header>
        {children}
      </section>
    </div>
  );
}
