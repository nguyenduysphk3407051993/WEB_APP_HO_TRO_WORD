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
    <div className="space-y-6">
      <Dropzone
        onFile={handleFile}
        accept={{
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
        }}
        hint="File Word .docx có chứa công thức Equation hoặc MathType"
      />

      {loading && (
        <div className="flex items-center gap-3 text-indigo-600">
          <span className="animate-spin h-5 w-5 border-2 border-indigo-600 border-t-transparent rounded-full" />
          Đang phân tích file...
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-md text-sm">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          {result.warning && (
            <div className="p-3 bg-amber-50 border border-amber-200 text-amber-900 rounded-md text-sm">
              ⚠ {result.warning}
            </div>
          )}

          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-slate-700">LaTeX output</h4>
            <CopyButton text={result.latex} />
          </div>
          <pre className="bg-slate-900 text-emerald-300 p-3 rounded-md text-xs overflow-x-auto whitespace-pre-wrap max-h-96">
            {result.latex}
          </pre>

          <h4 className="text-sm font-semibold text-slate-700">Preview</h4>
          <MathPreview latex={result.latex} />
        </div>
      )}
    </div>
  );
}
