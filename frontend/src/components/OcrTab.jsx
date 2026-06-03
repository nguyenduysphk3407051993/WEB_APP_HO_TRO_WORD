import { useState } from "react";
import Dropzone from "./Dropzone";
import MathPreview from "./MathPreview";
import CopyButton from "./CopyButton";
import { ocrImage, ocrPdf } from "../api";

export default function OcrTab() {
  const [mode, setMode] = useState("image");
  const [ocrMode, setOcrMode] = useState("single");
  const [maxConcurrent, setMaxConcurrent] = useState(10);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const handleFile = async (file) => {
    setError("");
    setResult(null);
    setLoading(true);
    try {
      const data =
        mode === "image"
          ? await ocrImage(file, ocrMode)
          : await ocrPdf(file, { mode: "page", maxConcurrent });
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const accept =
    mode === "image"
      ? { "image/*": [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"] }
      : { "application/pdf": [".pdf"] };

  return (
    <div className="space-y-6">
      <div className="flex gap-2">
        {["image", "pdf"].map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition ${
              mode === m
                ? "bg-indigo-600 text-white"
                : "bg-slate-200 text-slate-700 hover:bg-slate-300"
            }`}
          >
            {m === "image" ? "Ảnh" : "PDF"}
          </button>
        ))}
      </div>

      {mode === "image" && (
        <div className="flex items-center gap-3 text-sm">
          <label className="font-medium text-slate-700">Chế độ:</label>
          <select
            value={ocrMode}
            onChange={(e) => setOcrMode(e.target.value)}
            className="border border-slate-300 rounded px-2 py-1"
          >
            <option value="single">Chỉ 1 công thức (trả LaTeX thuần)</option>
            <option value="page">Cả trang (giữ cấu trúc văn bản + công thức)</option>
          </select>
        </div>
      )}

      {mode === "pdf" && (
        <div className="flex items-center gap-3 text-sm">
          <label className="font-medium text-slate-700">Trang xử lý song song:</label>
          <input
            type="number"
            min={1}
            max={20}
            value={maxConcurrent}
            onChange={(e) => setMaxConcurrent(Number(e.target.value))}
            className="border border-slate-300 rounded px-2 py-1 w-20"
          />
          <span className="text-slate-500">
            (mỗi key Gemini gánh ~3 req đồng thời, có 10 key → max ~30)
          </span>
        </div>
      )}

      <Dropzone
        onFile={handleFile}
        accept={accept}
        hint={
          mode === "image"
            ? "PNG, JPG, JPEG, BMP, TIFF, WEBP (≤ 50MB)"
            : "PDF nhiều trang — các trang được dispatch song song lên Gemini key pool"
        }
      />

      {loading && (
        <div className="flex items-center gap-3 text-indigo-600">
          <span className="animate-spin h-5 w-5 border-2 border-indigo-600 border-t-transparent rounded-full" />
          Đang gọi Gemini API...
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-md text-sm">
          {error}
        </div>
      )}

      {result?.latex !== undefined && <ResultBlock latex={result.latex} />}

      {result?.pages?.map((p) => (
        <div key={p.page} className="space-y-2">
          <h3 className="font-semibold">
            Trang {p.page}
            {p.error && (
              <span className="ml-2 text-xs text-red-600">(lỗi: {p.error})</span>
            )}
          </h3>
          {p.latex && <ResultBlock latex={p.latex} />}
        </div>
      ))}
    </div>
  );
}

function ResultBlock({ latex }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-slate-700">LaTeX</h4>
        <CopyButton text={latex} />
      </div>
      <pre className="bg-slate-900 text-emerald-300 p-3 rounded-md text-sm overflow-x-auto whitespace-pre-wrap">
        {latex}
      </pre>
      <h4 className="text-sm font-semibold text-slate-700">Preview</h4>
      <MathPreview latex={latex} display />
    </div>
  );
}
