export type SelectedUploadFile = { file: File; relativePath: string };
export type UploadPreviewImage = { name: string; source: string; kind: "image" | "zip" };
export type UploadConfirmation = {
  files: SelectedUploadFile[];
  images: UploadPreviewImage[];
  zipErrors: string[];
  title: string;
};

type BrowserFileSystemEntry = {
  isFile: boolean;
  isDirectory: boolean;
  name: string;
  fullPath?: string;
};

type BrowserFileSystemFileEntry = BrowserFileSystemEntry & {
  file: (success: (file: File) => void, failure?: (error: DOMException) => void) => void;
};

type BrowserFileSystemDirectoryEntry = BrowserFileSystemEntry & {
  createReader: () => {
    readEntries: (success: (entries: BrowserFileSystemEntry[]) => void, failure?: (error: DOMException) => void) => void;
  };
};

type BrowserDataTransferItem = DataTransferItem & {
  webkitGetAsEntry?: () => BrowserFileSystemEntry | null;
};

type UploadDropEvent = {
  dataTransfer: DataTransfer;
};

const SUPPORTED_UPLOAD_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp", ".zip"];

export async function buildUploadConfirmation(files: SelectedUploadFile[]): Promise<UploadConfirmation> {
  const images: UploadPreviewImage[] = [];
  const zipErrors: string[] = [];
  for (const item of files) {
    const source = cleanBrowserEntryPath(item.relativePath || item.file.name);
    if (isZipUpload(item.file)) {
      try {
        const names = await listZipImageNames(item.file);
        if (names.length === 0) {
          zipErrors.push(`${source} 中没有支持的图片。`);
        }
        images.push(...names.map((name) => ({ name, source, kind: "zip" as const })));
      } catch (err) {
        zipErrors.push(`${source} 无法解析：${err instanceof Error ? err.message : String(err)}`);
      }
      continue;
    }
    if (isSupportedImageUpload(item.file)) {
      images.push({ name: source, source, kind: "image" });
    }
  }
  return {
    files,
    images,
    zipErrors,
    title: uploadBatchTitleFromFiles(files)
  };
}

export function selectedUploadFilesFromFileList(files: FileList | null): SelectedUploadFile[] {
  return Array.from(files || []).map((file) => ({
    file,
    relativePath: uploadRelativePath(file)
  }));
}

export async function selectedUploadFilesFromDrop(event: UploadDropEvent): Promise<SelectedUploadFile[]> {
  const items = Array.from(event.dataTransfer.items || []) as BrowserDataTransferItem[];
  const filesFromFileList = selectedUploadFilesFromFileList(event.dataTransfer.files);
  if (items.length === 0) return filesFromFileList;

  const collected: SelectedUploadFile[] = [];
  for (const item of items) {
    if (item.kind !== "file") continue;
    const entry = item.webkitGetAsEntry?.();
    if (entry) {
      collected.push(...await selectedUploadFilesFromEntry(entry));
      continue;
    }
    const file = item.getAsFile();
    if (file) collected.push({ file, relativePath: uploadRelativePath(file) });
  }

  if (filesFromFileList.length <= collected.length) return collected;
  return mergeFallbackFileList(collected, filesFromFileList);
}

async function selectedUploadFilesFromEntry(entry: BrowserFileSystemEntry): Promise<SelectedUploadFile[]> {
  if (entry.isFile) {
    const file = await fileFromEntry(entry as BrowserFileSystemFileEntry);
    return [{ file, relativePath: cleanBrowserEntryPath(entry.fullPath || file.name) }];
  }
  if (!entry.isDirectory) return [];
  const children = await entriesFromDirectory(entry as BrowserFileSystemDirectoryEntry);
  const nested: SelectedUploadFile[] = [];
  for (const child of children) {
    nested.push(...await selectedUploadFilesFromEntry(child));
  }
  return nested;
}

function mergeFallbackFileList(collected: SelectedUploadFile[], filesFromFileList: SelectedUploadFile[]): SelectedUploadFile[] {
  const next = [...collected];
  const seen = new Set(collected.map((item) => uploadFileFingerprint(item.file)));
  for (const item of filesFromFileList) {
    const fingerprint = uploadFileFingerprint(item.file);
    if (seen.has(fingerprint)) continue;
    seen.add(fingerprint);
    next.push(item);
  }
  return next;
}

function uploadFileFingerprint(file: File): string {
  const size = typeof file.size === "number" ? file.size : "";
  const modified = typeof file.lastModified === "number" ? file.lastModified : "";
  return `${file.name}\0${size}\0${modified}`;
}

function fileFromEntry(entry: BrowserFileSystemFileEntry): Promise<File> {
  return new Promise((resolve, reject) => entry.file(resolve, reject));
}

async function entriesFromDirectory(entry: BrowserFileSystemDirectoryEntry): Promise<BrowserFileSystemEntry[]> {
  const reader = entry.createReader();
  const entries: BrowserFileSystemEntry[] = [];
  while (true) {
    const batch = await new Promise<BrowserFileSystemEntry[]>((resolve, reject) => reader.readEntries(resolve, reject));
    if (batch.length === 0) break;
    entries.push(...batch);
  }
  return entries;
}

function uploadBatchTitleFromFiles(files: SelectedUploadFile[]): string {
  const paths = files.map((item) => cleanBrowserEntryPath(item.relativePath || item.file.name)).filter(Boolean);
  if (paths.length === 0) return "DrawAI 任务";
  const segments = paths.map((path) => path.split("/").filter(Boolean));
  const roots = new Set(segments.map((parts) => parts[0]).filter(Boolean));
  if (paths.length > 1 && roots.size === 1 && segments.some((parts) => parts.length > 1)) {
    return [...roots][0];
  }
  const firstParts = segments[0] || [];
  return firstParts[firstParts.length - 1] || paths[0];
}

function uploadRelativePath(file: File): string {
  return cleanBrowserEntryPath((file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name);
}

function cleanBrowserEntryPath(value: string): string {
  return value.replace(/\\/g, "/").replace(/^\/+/, "") || "upload.png";
}

export function isSupportedUpload(file: File): boolean {
  return isSupportedImageUpload(file) || isZipUpload(file);
}

function isSupportedImageUpload(file: File): boolean {
  const lower = file.name.toLowerCase();
  return SUPPORTED_UPLOAD_EXTENSIONS.some((extension) => extension !== ".zip" && lower.endsWith(extension));
}

function isZipUpload(file: File): boolean {
  const lower = file.name.toLowerCase();
  return lower.endsWith(".zip") || file.type === "application/zip" || file.type === "application/x-zip-compressed";
}

async function listZipImageNames(file: File): Promise<string[]> {
  const buffer = await file.arrayBuffer();
  if (buffer.byteLength < 22) throw new Error("不是有效 ZIP 文件");
  const view = new DataView(buffer);
  const eocdOffset = findZipEndOfCentralDirectory(view);
  if (eocdOffset < 0) throw new Error("没有找到 ZIP 目录");
  const entryCount = view.getUint16(eocdOffset + 10, true);
  const centralDirectorySize = view.getUint32(eocdOffset + 12, true);
  const centralDirectoryOffset = view.getUint32(eocdOffset + 16, true);
  if (centralDirectoryOffset <= 0 || centralDirectoryOffset >= buffer.byteLength) {
    throw new Error("ZIP 目录位置异常");
  }
  const names: string[] = [];
  let offset = centralDirectoryOffset;
  const end = Math.min(buffer.byteLength, centralDirectoryOffset + centralDirectorySize);
  for (let index = 0; index < entryCount && offset + 46 <= end; index += 1) {
    if (view.getUint32(offset, true) !== 0x02014b50) break;
    const flags = view.getUint16(offset + 8, true);
    const nameLength = view.getUint16(offset + 28, true);
    const extraLength = view.getUint16(offset + 30, true);
    const commentLength = view.getUint16(offset + 32, true);
    const nameStart = offset + 46;
    const nameEnd = nameStart + nameLength;
    if (nameEnd > buffer.byteLength) break;
    const nameBytes = new Uint8Array(buffer, nameStart, nameLength);
    const rawName = decodeZipFilename(nameBytes, Boolean(flags & 0x0800));
    const name = cleanBrowserEntryPath(rawName);
    if (name && isSupportedImagePath(name) && !isHiddenZipEntry(name)) names.push(name);
    offset = nameEnd + extraLength + commentLength;
  }
  return names;
}

function findZipEndOfCentralDirectory(view: DataView): number {
  const minOffset = Math.max(0, view.byteLength - 65_557);
  for (let offset = view.byteLength - 22; offset >= minOffset; offset -= 1) {
    if (view.getUint32(offset, true) === 0x06054b50) return offset;
  }
  return -1;
}

function decodeZipFilename(bytes: Uint8Array, utf8: boolean): string {
  let decoder: TextDecoder;
  try {
    decoder = new TextDecoder(utf8 ? "utf-8" : "gb18030", { fatal: false });
  } catch {
    decoder = new TextDecoder("utf-8", { fatal: false });
  }
  return decoder.decode(bytes);
}

function isSupportedImagePath(path: string): boolean {
  const lower = path.toLowerCase();
  return [".png", ".jpg", ".jpeg", ".webp"].some((extension) => lower.endsWith(extension));
}

function isHiddenZipEntry(path: string): boolean {
  return path.split("/").some((part) => part === "__MACOSX" || part.startsWith("._"));
}
