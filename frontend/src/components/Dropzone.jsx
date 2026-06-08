import { useDropzone } from "react-dropzone";

export default function Dropzone({ onFile, accept, hint }) {
  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    accept,
    multiple: false,
    onDrop: (files) => files[0] && onFile(files[0]),
  });

  const file = acceptedFiles[0];

  return (
    <div
      {...getRootProps()}
      className={`relative overflow-hidden rounded-xl border-2 border-dashed p-10 text-center cursor-pointer transition-all duration-200
        ${isDragActive
          ? "border-indigo-500 bg-indigo-500/10 scale-[1.01]"
          : file
          ? "border-emerald-500/50 bg-emerald-500/5"
          : "border-slate-700 hover:border-indigo-500/50 hover:bg-indigo-500/5 bg-slate-800/50"
        }`}
    >
      {/* Background glow when drag active */}
      {isDragActive && (
        <div className="absolute inset-0 bg-indigo-500/5 animate-pulse pointer-events-none" />
      )}

      <input {...getInputProps()} />

      <div className="flex flex-col items-center gap-3">
        {file ? (
          <>
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-400">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <p className="font-semibold text-emerald-400 text-sm">{file.name}</p>
              <p className="text-xs text-slate-500 mt-1">
                {(file.size / 1024 / 1024).toFixed(2)} MB — Click để đổi file
              </p>
            </div>
          </>
        ) : isDragActive ? (
          <>
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-500/20 text-indigo-400">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <p className="text-indigo-400 font-semibold">Thả file vào đây...</p>
          </>
        ) : (
          <>
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-700/80 text-slate-400">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <div>
              <p className="text-slate-300 font-medium text-sm">
                Kéo & thả file hoặc{" "}
                <span className="text-indigo-400 underline underline-offset-2">click để chọn</span>
              </p>
              {hint && <p className="text-xs text-slate-500 mt-1.5">{hint}</p>}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
