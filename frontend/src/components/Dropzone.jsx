import { useCallback, useEffect, useRef } from "react";
import { useDropzone } from "react-dropzone";

/**
 * Props:
 *   onFiles(File[])   – batch callback (preferred)
 *   onFile(File)      – single-file backward compat
 *   accept            – react-dropzone accept map
 *   hint              – hint text
 *   multiple          – allow multiple files (default false)
 *   allowFolder       – show "Chọn thư mục" button (default false)
 *   allowPaste        – enable Ctrl+V clipboard paste (default false)
 */
export default function Dropzone({
  onFiles,
  onFile,
  accept,
  hint,
  multiple = false,
  allowFolder = false,
  allowPaste = false,
}) {
  const folderRef = useRef(null);

  const emit = useCallback(
    (files) => {
      if (!files.length) return;
      if (onFiles) onFiles(files);
      else if (onFile) onFile(files[0]);
    },
    [onFiles, onFile]
  );

  // Clipboard paste
  useEffect(() => {
    if (!allowPaste) return;
    const handler = (e) => {
      const items = Array.from(e.clipboardData?.items ?? []);
      const imgs = items
        .filter((it) => it.type.startsWith("image/"))
        .map((it) => it.getAsFile())
        .filter(Boolean);
      if (imgs.length) {
        e.preventDefault();
        emit(imgs);
      }
    };
    document.addEventListener("paste", handler);
    return () => document.removeEventListener("paste", handler);
  }, [allowPaste, emit]);

  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    accept,
    multiple,
    onDrop: (files) => emit(files),
  });

  const displayFiles = acceptedFiles;
  const hasFiles = displayFiles.length > 0;

  return (
    <div className="space-y-2">
      <div
        {...getRootProps()}
        className={`relative overflow-hidden rounded-xl border-2 border-dashed p-8 text-center cursor-pointer transition-all duration-200
          ${isDragActive
            ? "border-gold-400 bg-gold-400/10 scale-[1.01]"
            : hasFiles
            ? "border-emerald-500/50 bg-emerald-500/5"
            : "border-[#43372d] hover:border-gold-600/60 hover:bg-gold-400/5 bg-[#261e18]/50"
          }`}
      >
        {isDragActive && (
          <div className="absolute inset-0 bg-gold-400/5 animate-pulse pointer-events-none" />
        )}
        <input {...getInputProps()} />

        <div className="flex flex-col items-center gap-3">
          {isDragActive ? (
            <>
              <DropIcon />
              <p className="text-gold-400 font-semibold">Thả file vào đây...</p>
            </>
          ) : hasFiles ? (
            <>
              <CheckIcon />
              {displayFiles.length === 1 ? (
                <div>
                  <p className="font-semibold text-emerald-400 text-sm">{displayFiles[0].name}</p>
                  <p className="text-xs text-gold-700 mt-1">
                    {(displayFiles[0].size / 1024 / 1024).toFixed(2)} MB — Click để đổi file
                  </p>
                </div>
              ) : (
                <div>
                  <p className="font-semibold text-emerald-400 text-sm">
                    {displayFiles.length} file đã chọn
                  </p>
                  <p className="text-xs text-gold-700 mt-1">
                    {displayFiles
                      .slice(0, 3)
                      .map((f) => f.name)
                      .join(", ")}
                    {displayFiles.length > 3 ? ` và ${displayFiles.length - 3} file khác` : ""}
                  </p>
                  <p className="text-xs text-gold-800 mt-0.5">Click để thay đổi</p>
                </div>
              )}
            </>
          ) : (
            <>
              <UploadIcon />
              <div>
                <p className="text-[#ece3d7] font-medium text-sm">
                  Kéo & thả {multiple ? "file(s)" : "file"} hoặc{" "}
                  <span className="text-gold-400 underline underline-offset-2">click để chọn</span>
                </p>
                {allowPaste && (
                  <p className="text-xs text-gold-700 mt-1">
                    Hoặc nhấn{" "}
                    <kbd className="px-1.5 py-0.5 rounded bg-[#2f2620] text-gold-300 text-[11px] font-mono border border-[#43372d]">
                      Ctrl+V
                    </kbd>{" "}
                    để dán từ clipboard
                  </p>
                )}
                {hint && <p className="text-xs text-gold-700 mt-1.5">{hint}</p>}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Folder / paste buttons */}
      {(allowFolder || allowPaste) && (
        <div className="flex flex-wrap gap-2">
          {allowFolder && (
            <>
              <input
                ref={folderRef}
                type="file"
                webkitdirectory=""
                multiple
                className="hidden"
                onChange={(e) => {
                  const files = Array.from(e.target.files).filter((f) =>
                    f.type.startsWith("image/")
                  );
                  if (files.length) emit(files);
                  e.target.value = "";
                }}
              />
              <button
                type="button"
                onClick={() => folderRef.current?.click()}
                className="flex items-center gap-2 rounded-lg border border-[#43372d] bg-[#261e18] px-3 py-2 text-xs font-medium text-gold-300 hover:bg-[#2f2620] hover:text-[#f6f1ea] transition"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                    d="M3 7a2 2 0 012-2h3.586a1 1 0 01.707.293L10.707 6.7A1 1 0 0011.414 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" />
                </svg>
                Chọn thư mục
              </button>
            </>
          )}
          {allowPaste && (
            <button
              type="button"
              onClick={async () => {
                try {
                  const items = await navigator.clipboard.read();
                  const imgs = [];
                  for (const item of items) {
                    for (const type of item.types) {
                      if (type.startsWith("image/")) {
                        const blob = await item.getType(type);
                        imgs.push(new File([blob], `clipboard.${type.split("/")[1]}`, { type }));
                      }
                    }
                  }
                  if (imgs.length) emit(imgs);
                } catch {
                  // fallback: user can just Ctrl+V
                }
              }}
              className="flex items-center gap-2 rounded-lg border border-[#43372d] bg-[#261e18] px-3 py-2 text-xs font-medium text-gold-300 hover:bg-[#2f2620] hover:text-[#f6f1ea] transition"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              Dán từ clipboard
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function UploadIcon() {
  return (
    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#2f2620] text-gold-600">
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
          d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
      </svg>
    </div>
  );
}

function DropIcon() {
  return (
    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gold-400/20 text-gold-400">
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
      </svg>
    </div>
  );
}

function CheckIcon() {
  return (
    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-400">
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    </div>
  );
}
