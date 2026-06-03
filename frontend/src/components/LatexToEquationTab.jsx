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
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-semibold text-slate-700 mb-2">
          Nội dung LaTeX (có thể chứa văn bản + công thức)
        </label>
        <textarea
          value={latex}
          onChange={(e) => setLatex(e.target.value)}
          rows={10}
          className="w-full p-3 border border-slate-300 rounded-md font-mono text-sm focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      <div className="flex gap-3 items-center">
        <button
          onClick={handleDownload}
          disabled={loading || !latex.trim()}
          className="px-5 py-2 bg-emerald-600 text-white rounded-md hover:bg-emerald-700 disabled:opacity-50"
        >
          {loading ? "Đang tạo..." : "Tải về .docx (Word Equation)"}
        </button>
        <span className="text-sm text-slate-500">
          File .docx mở trong Word, công thức là OMML native (chỉnh sửa được bằng Equation Editor).
        </span>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-md text-sm">
          {error}
        </div>
      )}

      <div>
        <h4 className="text-sm font-semibold text-slate-700 mb-2">Preview (rendered)</h4>
        <div className="bg-white p-4 border rounded-md text-sm whitespace-pre-wrap">
          <MathPreview latex={latex} />
        </div>
      </div>
    </div>
  );
}
