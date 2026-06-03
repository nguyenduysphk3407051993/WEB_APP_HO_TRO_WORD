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
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-semibold text-slate-700 mb-2">
          Mã LaTeX
        </label>
        <textarea
          value={latex}
          onChange={(e) => setLatex(e.target.value)}
          rows={5}
          className="w-full p-3 border border-slate-300 rounded-md font-mono text-sm focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      <div className="flex gap-3">
        <button
          onClick={handleConvert}
          disabled={loading || !latex.trim()}
          className="px-5 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? "Đang xử lý..." : "Chuyển sang MathType"}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-md text-sm">
          {error}
        </div>
      )}

      <div>
        <h4 className="text-sm font-semibold text-slate-700 mb-2">Preview</h4>
        <MathPreview latex={latex} />
      </div>

      {mathml && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-slate-700">
              MathML (dán vào MathType)
            </h4>
            <CopyButton text={mathml} label="Copy MathML" />
          </div>
          <pre className="bg-slate-900 text-amber-300 p-3 rounded-md text-xs overflow-x-auto whitespace-pre-wrap">
            {mathml}
          </pre>

          <div className="bg-amber-50 border border-amber-200 p-4 rounded-md text-sm text-amber-900">
            <strong>Hướng dẫn dán vào MathType:</strong>
            <ol className="list-decimal ml-5 mt-1 space-y-1">
              <li>Bấm "Copy MathML" ở trên.</li>
              <li>Mở MathType (đảm bảo MathType 7+), bấm <em>Edit → Paste</em>.</li>
              <li>MathType tự nhận diện MathML và chuyển thành công thức có thể chỉnh sửa.</li>
              <li>Nếu chèn vào Word: bấm Insert &gt; Object &gt; MathType Equation, paste vào đó.</li>
            </ol>
          </div>
        </div>
      )}
    </div>
  );
}
