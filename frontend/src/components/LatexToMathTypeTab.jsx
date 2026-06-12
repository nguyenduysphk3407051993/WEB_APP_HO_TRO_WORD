import { useState } from "react";
import MathPreview from "./MathPreview";
import CopyButton from "./CopyButton";
import { latexToMathtype } from "../api";

const EXAMPLE = "E = mc^2 \\quad \\Rightarrow \\quad \\int_0^{\\infty} e^{-x^2}\\,dx = \\frac{\\sqrt{\\pi}}{2}";

export default function LatexToMathTypeTab() {
  const [latex, setLatex] = useState(EXAMPLE);
  const [mathml, setMathml] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleConvert = async () => {
    setError("");
    setMathml("");
    setLoading(true);
    try {
      const data = await latexToMathtype(latex);
      setMathml(data.mathml);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Input */}
      <div>
        <label className="block text-sm font-semibold text-slate-300 mb-2">
          Mã LaTeX
        </label>
        <textarea
          value={latex}
          onChange={(e) => setLatex(e.target.value)}
          rows={5}
          className="w-full rounded-xl border border-slate-700 bg-slate-800/80 p-4 font-mono text-sm text-slate-200
            placeholder-slate-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 resize-none"
          placeholder="Nhập công thức LaTeX..."
        />
      </div>

      {/* Action */}
      <button
        onClick={handleConvert}
        disabled={loading || !latex.trim()}
        className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white
          hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-indigo-600/25 transition-all"
      >
        {loading ? (
          <>
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            Đang xử lý...
          </>
        ) : (
          <>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Chuyển sang MathType
          </>
        )}
      </button>

      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-red-500/20 bg-red-500/10 p-4">
          <svg className="w-4 h-4 mt-0.5 shrink-0 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      {/* Preview */}
      <div>
        <h4 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-2">Preview</h4>
        <div className="rounded-xl border border-slate-700 bg-white p-4 min-h-14">
          <MathPreview latex={latex} />
        </div>
      </div>

      {/* MathML result */}
      {mathml && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-slate-300">MathML (dán vào MathType)</h4>
            <CopyButton text={mathml} label="Copy MathML" />
          </div>
          <pre className="rounded-xl bg-slate-950 border border-slate-800 text-amber-400 p-4 text-xs overflow-x-auto whitespace-pre-wrap max-h-64">
            {mathml}
          </pre>

          <div className="rounded-xl border border-sky-500/20 bg-sky-500/10 p-4 text-sm text-sky-300">
            <p className="font-semibold mb-2">📋 Hướng dẫn dán vào MathType:</p>
            <ol className="list-decimal ml-5 space-y-1 text-sky-300/80">
              <li>Bấm "Copy MathML" ở trên.</li>
              <li>Mở MathType (7+), bấm <em>Edit → Paste</em>.</li>
              <li>MathType tự nhận diện MathML và chuyển thành công thức có thể chỉnh sửa.</li>
              <li>Nếu chèn vào Word: Insert &gt; Object &gt; MathType Equation, paste vào đó.</li>
            </ol>
          </div>
        </div>
      )}
    </div>
  );
}
