import { useState } from "react";
import MathPreview from "./MathPreview";
import { latexToDocx } from "../api";

const EXAMPLE = `\\section{Bài toán mẫu}
Cho phương trình $ax^2 + bx + c = 0$ với $a \\ne 0$. Nghiệm:
\\[ x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a} \\]`;

export default function LatexToEquationTab() {
  const [latex, setLatex] = useState(EXAMPLE);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleDownload = async () => {
    setError("");
    setLoading(true);
    try {
      const blob = await latexToDocx(latex);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "output.docx";
      a.click();
      URL.revokeObjectURL(url);
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
        <label className="block text-sm font-semibold text-[#f0dfa0] mb-2">
          Nội dung LaTeX{" "}
          <span className="text-gold-700 font-normal">(có thể chứa văn bản + công thức)</span>
        </label>
        <textarea
          value={latex}
          onChange={(e) => setLatex(e.target.value)}
          rows={12}
          className="w-full rounded-xl border border-[#3d3018] bg-[#1f1b0e]/80 p-4 font-mono text-sm text-[#f0dfa0]
            placeholder-gold-800 focus:border-gold-400 focus:outline-none focus:ring-1 focus:ring-gold-400/30 resize-none"
          placeholder="Nhập nội dung LaTeX..."
        />
      </div>

      {/* Action */}
      <div className="flex flex-wrap items-center gap-4">
        <button
          onClick={handleDownload}
          disabled={loading || !latex.trim()}
          className="flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white
            hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-emerald-600/25"
        >
          {loading ? (
            <>
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Đang tạo...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Tải về .docx
            </>
          )}
        </button>
        <p className="text-sm text-gold-700">
          File .docx mở trong Word, công thức là OMML native (Equation Editor).
        </p>
      </div>

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
        <h4 className="text-sm font-semibold text-gold-600 uppercase tracking-wide mb-2">Preview (rendered)</h4>
        <div className="rounded-xl border border-[#3d3018] bg-white p-4 min-h-20 text-sm whitespace-pre-wrap">
          <MathPreview latex={latex} />
        </div>
      </div>
    </div>
  );
}
