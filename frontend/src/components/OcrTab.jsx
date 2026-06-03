import { useState } from "react";
import Dropzone from "./Dropzone";
import MathPreview from "./MathPreview";
import CopyButton from "./CopyButton";
import { ocrImage, ocrPdf } from "../api";

export default function OcrTab() {
  const [mode, setMode] = useState("image");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const handleFile = async (file) => {
    setError("");
    setResult(null);
    setLoading(true);
    try {
      const data = mode === "image" ? await ocrImage(file) : await ocrPdf(file);
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

      <Dropzone
        onFile={handleFile}
        accept={accept}
        hint={
          mode === "image"
            ? "PNG, JPG, JPEG, BMP, TIFF, WEBP (≤ 50MB)"
            : "PDF nhiều trang — mỗi trang sẽ được OCR riêng"
        }
      />

      {loading && (
        <div className="flex items-center gap-3 text-indigo-600">
          <span className="animate-spin h-5 w-5 border-2 border-indigo-600 border-t-transparent rounded-full" />
          Đang OCR... (lần đầu sẽ tải model ~80MB)
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-md text-sm">
          {error}
        </div>
      )}

      {result?.latex !== undefined && (
        <ResultBlock latex={result.latex} />
      )}

      {result?.pages?.map((p) => (
        <div key={p.page} className="space-y-2">
          <h3 className="font-semibold">Trang {p.page}</h3>
          <ResultBlock latex={p.latex} />
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
