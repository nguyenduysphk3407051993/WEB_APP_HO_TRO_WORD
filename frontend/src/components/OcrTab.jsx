import { useState } from "react";
import Dropzone from "./Dropzone";
import MathPreview from "./MathPreview";
import CopyButton from "./CopyButton";
import {
  downloadOcrDocx,
  ocrImageToDocx,
  ocrPdfToDocx,
  ocrImageToExamLatex,
  ocrPdfToExamLatex,
  ocrImageToEquation,
  ocrPdfToEquation,
} from "../api";

const saveBlob = (blob, filename) => {
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.URL.revokeObjectURL(url);
};

export default function OcrTab() {
  const [mode, setMode] = useState("image");
  const [outputTarget, setOutputTarget] = useState("word");
  const [ocrMode, setOcrMode] = useState("page");
  const [maxConcurrent, setMaxConcurrent] = useState(10);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const triggerDownload = async (payload) => {
    const blob = await downloadOcrDocx(payload.download_url);
    saveBlob(blob, payload.filename);
  };

  const handleFile = async (file) => {
    setError("");
    setResult(null);
    setLoading(true);

    try {
      if (outputTarget === "word") {
        const payload =
          mode === "image"
            ? await ocrImageToDocx(file, ocrMode)
            : await ocrPdfToDocx(file, { mode: "page", maxConcurrent });
        await triggerDownload(payload);
        setResult({ type: "word", data: payload });
        return;
      }

      if (outputTarget === "examlatex") {
        const data =
          mode === "image"
            ? await ocrImageToExamLatex(file, ocrMode)
            : await ocrPdfToExamLatex(file, { mode: "page", maxConcurrent });
        setResult({ type: "examlatex", data });
        return;
      }

      if (outputTarget === "equation") {
        const payload =
          mode === "image"
            ? await ocrImageToEquation(file, ocrMode)
            : await ocrPdfToEquation(file, { mode: "page", maxConcurrent });
        await triggerDownload(payload);
        setResult({ type: "equation", data: payload });
        return;
      }
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

  const hints = {
    word: {
      image: "Tải ảnh để tạo Word với công thức LaTeX cho MathType Toggle TeX.",
      pdf: "Tải PDF để OCR sang Word, giữ công thức LaTeX cho Toggle TeX.",
    },
    examlatex: {
      image: "Tải ảnh đề thi để trích xuất thành LaTeX chuẩn \\begin{ex}...\\end{ex}.",
      pdf: "Tải PDF đề thi — kết quả LaTeX từng trang theo chuẩn exam-latex-creator.",
    },
    equation: {
      image: "Tải ảnh để tạo Word với công thức OMML (equation thực sự, không cần MathType).",
      pdf: "Tải PDF — tạo Word với công thức OMML hiển thị ngay trong Word.",
    },
  };

  const loadingMsg = {
    word: "Đang OCR, tạo Word và sinh MathML...",
    examlatex: "Đang OCR, chuyển sang LaTeX thi cử...",
    equation: "Đang OCR, tạo Word Equation...",
  };

  return (
    <div className="space-y-5">
      {/* Info banner */}
      <div className="flex items-start gap-3 rounded-xl border border-indigo-500/20 bg-indigo-500/10 px-4 py-3">
        <svg className="w-4 h-4 mt-0.5 shrink-0 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p className="text-sm text-indigo-300">
          Chọn <strong>Word + Toggle TeX</strong> để tạo file Word cho MathType ·{" "}
          <strong>Exam LaTeX</strong> để xuất đề thi dạng <code>\begin&#123;ex&#125;</code> ·{" "}
          <strong>Equation</strong> để tạo Word với công thức OMML hiển thị ngay.
        </p>
      </div>

      {/* Mode selector */}
      <div className="flex gap-2">
        {["image", "pdf"].map((value) => (
          <button
            key={value}
            onClick={() => setMode(value)}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-all ${
              mode === value
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/25"
                : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200 border border-slate-700"
            }`}
          >
            {value === "image" ? (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                Ảnh
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                PDF
              </>
            )}
          </button>
        ))}
      </div>

      {/* Options */}
      <div className="space-y-3 rounded-xl border border-slate-700 bg-slate-800/60 p-4">
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <span className="font-semibold text-slate-300">Đầu ra:</span>
          {[
            { id: "word",      label: "Word + Toggle TeX" },
            { id: "examlatex", label: "Exam LaTeX" },
            { id: "equation",  label: "Equation" },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => setOutputTarget(item.id)}
              className={`rounded-full px-3 py-1.5 text-sm font-medium transition ${
                outputTarget === item.id
                  ? "bg-emerald-600 text-white shadow-lg shadow-emerald-600/25"
                  : "bg-slate-700 text-slate-400 hover:bg-slate-600 hover:text-slate-200"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {mode === "image" && (
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <label className="font-semibold text-slate-300">Chế độ OCR:</label>
            <select
              value={ocrMode}
              onChange={(e) => setOcrMode(e.target.value)}
              className="rounded-lg border border-slate-600 bg-slate-700 px-3 py-1.5 text-slate-200 focus:border-indigo-500 focus:outline-none"
            >
              <option value="single">1 công thức / vùng nhỏ</option>
              <option value="page">Cả trang / giữ cấu trúc</option>
            </select>
          </div>
        )}

        {mode === "pdf" && (
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <label className="font-semibold text-slate-300">Trang xử lý song song:</label>
            <input
              type="number"
              min={1}
              max={20}
              value={maxConcurrent}
              onChange={(e) => setMaxConcurrent(Number(e.target.value))}
              className="w-20 rounded-lg border border-slate-600 bg-slate-700 px-3 py-1.5 text-slate-200 focus:border-indigo-500 focus:outline-none"
            />
            <span className="text-slate-500 text-xs">
              Tăng tốc OCR PDF khi có nhiều key trong pool.
            </span>
          </div>
        )}
      </div>

      <Dropzone
        onFile={handleFile}
        accept={accept}
        hint={hints[outputTarget]?.[mode] ?? ""}
      />

      {loading && (
        <div className="flex items-center gap-3 rounded-xl border border-indigo-500/20 bg-indigo-500/10 p-4 text-indigo-300">
          <span className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-400 border-t-transparent shrink-0" />
          <span className="text-sm">{loadingMsg[outputTarget]}</span>
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

      {(result?.type === "word" || result?.type === "equation") && (
        <WordResultBlock
          result={result.data}
          onDownloadAgain={triggerDownload}
          isEquation={result.type === "equation"}
        />
      )}

      {result?.type === "examlatex" && result.data?.latex !== undefined && (
        <ExamLatexResultBlock latex={result.data.latex} />
      )}

      {result?.type === "examlatex" &&
        result.data?.pages?.map((page) => (
          <div key={page.page} className="space-y-2">
            <h3 className="font-semibold text-slate-200">
              Trang {page.page}
              {page.error && (
                <span className="ml-2 text-xs text-red-400">(lỗi: {page.error})</span>
              )}
            </h3>
            {page.latex && <ExamLatexResultBlock latex={page.latex} />}
          </div>
        ))}
    </div>
  );
}

function WordResultBlock({ result, onDownloadAgain, isEquation = false }) {
  const label = isEquation ? "Equation (.docx)" : "Word + Toggle TeX";
  const formatLabel = isEquation ? "OMML Equation" : "Toggle TeX";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/20 text-emerald-400">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-emerald-300">Đã tạo xong file {label}</h3>
            <p className="text-sm text-emerald-400/70">
              File: <span className="font-medium">{result.filename}</span>
            </p>
          </div>
        </div>
        <button
          onClick={() => onDownloadAgain(result)}
          className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 shadow-lg shadow-emerald-600/25"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Tải lại .docx
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <SummaryItem label="Loại nguồn" value={result.source_type === "pdf" ? "PDF" : "Ảnh"} />
        <SummaryItem label="Tổng công thức" value={String(result.total_formulas)} />
        <SummaryItem label="Định dạng CT" value={formatLabel} />
        <SummaryItem label="Trang lỗi OCR" value={String(result.errors)} />
      </div>

      {result.pages?.length > 0 && (
        <div className="rounded-xl border border-slate-700 bg-slate-800/60 p-4">
          <h4 className="text-sm font-semibold text-slate-300 mb-3">Tổng hợp theo trang</h4>
          <div className="grid gap-2 sm:grid-cols-2">
            {result.pages.map((page) => (
              <div key={page.page} className="rounded-lg border border-slate-700 bg-slate-800 p-3 text-sm">
                <div className="font-medium text-slate-200">Trang {page.page}</div>
                <div className="mt-1 text-slate-400">
                  Công thức: <span className="font-medium text-slate-300">{page.formula_count}</span>
                </div>
                {page.error && (
                  <div className="mt-1.5 text-xs text-red-400">Lỗi OCR: {page.error}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {!isEquation && <LatexOutputPanel latexOutput={result.latex_output} />}

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-slate-300">Danh sách công thức LaTeX / MathML</h4>
          <span className="text-xs text-slate-500">{result.total_formulas} công thức</span>
        </div>

        {!result.formulas?.length && (
          <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-300">
            Chưa tách được công thức nào từ nội dung OCR. File Word vẫn đã được tạo.
          </div>
        )}

        {result.formulas?.map((formula) => (
          <FormulaCard key={formula.id} formula={formula} isEquation={isEquation} />
        ))}
      </div>
    </div>
  );
}

function LatexOutputPanel({ latexOutput }) {
  return (
    <div className="space-y-3 rounded-xl border border-slate-700 bg-slate-800/60 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h4 className="text-sm font-semibold text-slate-200">LaTeX cho Toggle TeX</h4>
          <p className="text-xs text-slate-500 mt-0.5">
            Dạng công thức được giữ trong file Word để MathType xử lý hàng loạt.
          </p>
        </div>
        <CopyButton text={latexOutput || ""} label="Copy tất cả LaTeX" />
      </div>
      {latexOutput ? (
        <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-4 text-sm text-emerald-400 border border-slate-800">
          {latexOutput}
        </pre>
      ) : (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 text-sm text-amber-300">
          Chưa có công thức LaTeX để xuất sang Toggle TeX.
        </div>
      )}
    </div>
  );
}

function SummaryItem({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800 px-3 py-3">
      <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">{label}</div>
      <div className="mt-1 font-bold text-slate-200">{value}</div>
    </div>
  );
}

function FormulaCard({ formula, isEquation = false }) {
  return (
    <div className="space-y-4 rounded-xl border border-slate-700 bg-slate-800/50 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h5 className="font-semibold text-slate-200">
            Công thức #{formula.id}
            {formula.page ? ` — Trang ${formula.page}` : ""}
          </h5>
          <p className="text-xs text-slate-500 mt-0.5">
            {formula.display ? "Display math" : "Inline math"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <CopyButton text={formula.latex_source || formula.latex} label="LaTeX" />
          {!isEquation && <CopyButton text={formula.raw_latex || formula.latex} label="OCR gốc" />}
          <CopyButton text={formula.mathml || ""} label="MathML" />
        </div>
      </div>

      {!isEquation && formula.raw_latex && formula.raw_latex !== formula.latex && (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 text-xs text-amber-300">
          Công thức đã được làm sạch tiếng Việt/Unicode trong vùng TeX để MathType Toggle TeX xử lý ổn định hơn.
        </div>
      )}

      <div className="space-y-2">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
          {isEquation ? "LaTeX" : "LaTeX cho Toggle TeX"}
        </div>
        <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-3 text-sm text-emerald-400 border border-slate-800">
          {formula.latex_source || formula.latex}
        </pre>
      </div>

      <div className="space-y-2">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Preview</div>
        <div className="rounded-lg border border-slate-700 bg-white p-3">
          <MathPreview latex={formula.latex} display={formula.display} />
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide">MathML</div>
          {!formula.mathml && formula.mathml_error && (
            <span className="text-xs text-red-400">Không sinh được MathML</span>
          )}
        </div>
        {formula.mathml ? (
          <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-3 text-xs text-amber-400 border border-slate-800">
            {formula.mathml}
          </pre>
        ) : (
          <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-300">
            {formula.mathml_error || "Không chuyển được sang MathML."}
          </div>
        )}
      </div>
    </div>
  );
}

function ExamLatexResultBlock({ latex }) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h4 className="text-sm font-semibold text-slate-300">Exam LaTeX</h4>
          <p className="text-xs text-slate-500 mt-0.5">
            Định dạng <code className="text-slate-400">\begin&#123;ex&#125;...\choice...\end&#123;ex&#125;</code> — tương thích exam-latex-creator
          </p>
        </div>
        <CopyButton text={latex} />
      </div>
      <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-4 text-sm text-emerald-400 border border-slate-800 leading-relaxed">
        {latex}
      </pre>
    </div>
  );
}
