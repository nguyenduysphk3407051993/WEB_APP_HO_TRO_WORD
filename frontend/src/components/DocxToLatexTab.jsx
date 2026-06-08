import { useState } from "react";
import Dropzone from "./Dropzone";
import CopyButton from "./CopyButton";
import MathPreview from "./MathPreview";
import { docxToLatex } from "../api";

export default function DocxToLatexTab() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const handleFile = async (file) => {
    setError("");
    setResult(null);
    setLoading(true);
    try {
      const data = await docxToLatex(file);
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      <Dropzone
        onFile={handleFile}
        accept={{
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
        }}
        hint="File Word .docx có chứa công thức Equation hoặc MathType"
      />

      {loading && (
        <div className="flex items-center gap-3 rounded-xl border border-indigo-500/20 bg-indigo-500/10 p-4 text-indigo-300">
          <span className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-400 border-t-transparent shrink-0" />
          <span className="text-sm">Đang phân tích file...</span>
        </div>
      )}

      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-red-500/20 bg-red-500/10 p-4">
          <svg className="w-4 h-4 mt-0.5 shrink-0 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      {result && (
        <div className="space-y-4">
          {result.warning && (
            <div className="flex items-start gap-3 rounded-xl border border-amber-500/20 bg-amber-500/10 p-4">
              <svg className="w-4 h-4 mt-0.5 shrink-0 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <p className="text-sm text-amber-300">{result.warning}</p>
            </div>
          )}

          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-slate-300">LaTeX output</h4>
            <CopyButton text={result.latex} />
          </div>
          <pre className="rounded-xl bg-slate-950 border border-slate-800 text-emerald-400 p-4 text-xs overflow-x-auto whitespace-pre-wrap max-h-96">
            {result.latex}
          </pre>

          <h4 className="text-sm font-semibold text-slate-400 uppercase tracking-wide">Preview</h4>
          <div className="rounded-xl border border-slate-700 bg-white p-4">
            <MathPreview latex={result.latex} />
          </div>
        </div>
      )}
    </div>
  );
}
