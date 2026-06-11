import { useState, useCallback, useRef } from "react";
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

// ─── helpers ────────────────────────────────────────────────────────────────

const saveBlob = (blob, filename) => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  window.URL.revokeObjectURL(url);
};

const triggerDownload = async (payload) => {
  const blob = await downloadOcrDocx(payload.download_url);
  saveBlob(blob, payload.filename);
};

async function withConcurrency(items, limit, fn) {
  const running = new Set();
  for (const item of items) {
    const p = fn(item).finally(() => running.delete(p));
    running.add(p);
    if (running.size >= limit) await Promise.race(running);
  }
  await Promise.all(running);
}

let _uid = 0;
const uid = () => String(++_uid);

// ─── component ──────────────────────────────────────────────────────────────

export default function OcrTab() {
  const [mode, setMode] = useState("image");
  const [outputTarget, setOutputTarget] = useState("word");
  const [ocrMode, setOcrMode] = useState("page");
  const [maxConcurrent, setMaxConcurrent] = useState(5);

  // Image batch queue
  const [queue, setQueue] = useState([]);

  // PDF single result
  const [pdfResult, setPdfResult] = useState(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState("");

  const updateItem = useCallback(
    (id, patch) => setQueue((prev) => prev.map((it) => (it.id === id ? { ...it, ...patch } : it))),
    []
  );

  const processItem = useCallback(
    async (item, target, oMode) => {
      updateItem(item.id, { status: "running" });
      try {
        let result;
        if (target === "word") {
          const payload = await ocrImageToDocx(item.file, oMode);
          await triggerDownload(payload);
          result = { type: "word", data: payload };
        } else if (target === "examlatex") {
          const data = await ocrImageToExamLatex(item.file, oMode);
          result = { type: "examlatex", data };
        } else {
          const payload = await ocrImageToEquation(item.file, oMode);
          await triggerDownload(payload);
          result = { type: "equation", data: payload };
        }
        updateItem(item.id, { status: "done", result });
      } catch (e) {
        updateItem(item.id, { status: "error", error: e.response?.data?.detail ?? e.message });
      }
    },
    [updateItem]
  );

  const handleImageFiles = useCallback(
    (files) => {
      const items = Array.from(files).map((file) => ({
        id: uid(),
        file,
        name: file.name || "clipboard.png",
        status: "pending",
        result: null,
        error: null,
      }));
      setQueue((prev) => [...prev, ...items]);

      const target = outputTarget;
      const oMode = ocrMode;
      const conc = maxConcurrent;
      withConcurrency(items, conc, (it) => processItem(it, target, oMode));
    },
    [outputTarget, ocrMode, maxConcurrent, processItem]
  );

  const handlePdfFile = useCallback(
    async (file) => {
      setPdfError("");
      setPdfResult(null);
      setPdfLoading(true);
      try {
        const opts = { mode: "page", maxConcurrent };
        if (outputTarget === "word") {
          const payload = await ocrPdfToDocx(file, opts);
          await triggerDownload(payload);
          setPdfResult({ type: "word", data: payload });
        } else if (outputTarget === "examlatex") {
          const data = await ocrPdfToExamLatex(file, opts);
          setPdfResult({ type: "examlatex", data });
        } else {
          const payload = await ocrPdfToEquation(file, opts);
          await triggerDownload(payload);
          setPdfResult({ type: "equation", data: payload });
        }
      } catch (e) {
        setPdfError(e.response?.data?.detail ?? e.message);
      } finally {
        setPdfLoading(false);
      }
    },
    [outputTarget, maxConcurrent]
  );

  const qStats = {
    total:   queue.length,
    running: queue.filter((q) => q.status === "running").length,
    done:    queue.filter((q) => q.status === "done").length,
    errors:  queue.filter((q) => q.status === "error").length,
    pending: queue.filter((q) => q.status === "pending").length,
  };

  const hints = {
    word:      { image: "Kéo nhiều ảnh, dán clipboard hoặc chọn thư mục để xử lý hàng loạt.", pdf: "Tải PDF → Word giữ công thức Toggle TeX." },
    examlatex: { image: "Hàng loạt ảnh → LaTeX \\begin{ex}...\\end{ex}.", pdf: "PDF đề thi → LaTeX từng trang." },
    equation:  { image: "Hàng loạt ảnh → Word OMML Equation.", pdf: "PDF → Word Equation OMML." },
  };

  const loadingMsg = { word: "Đang tạo Word + Toggle TeX...", examlatex: "Đang OCR sang Exam LaTeX...", equation: "Đang tạo Word Equation..." };

  const imageAccept = { "image/*": [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"] };
  const pdfAccept   = { "application/pdf": [".pdf"] };

  return (
    <div className="space-y-5">
      {/* Info */}
      <div className="flex items-start gap-3 rounded-xl border border-indigo-500/20 bg-indigo-500/10 px-4 py-3">
        <InfoIcon />
        <p className="text-sm text-indigo-300">
          <strong>Word + Toggle TeX</strong> · <strong>Exam LaTeX</strong> · <strong>Equation (OMML)</strong>
          <br />
          <span className="text-indigo-400 text-xs">
            Chế độ ảnh: kéo nhiều file, chọn thư mục, hoặc dán Ctrl+V từ clipboard.
          </span>
        </p>
      </div>

      {/* Source mode */}
      <div className="flex gap-2">
        {["image", "pdf"].map((v) => (
          <button
            key={v}
            onClick={() => { setMode(v); setQueue([]); setPdfResult(null); setPdfError(""); }}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-all ${
              mode === v
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/25"
                : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200 border border-slate-700"
            }`}
          >
            {v === "image" ? <ImageIcon /> : <PdfIcon />}
            {v === "image" ? "Ảnh (batch)" : "PDF"}
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

        <div className="flex flex-wrap items-center gap-3 text-sm">
          <label className="font-semibold text-slate-300">
            {mode === "image" ? "Xử lý song song (ảnh):" : "Trang song song (PDF):"}
          </label>
          <input
            type="number" min={1} max={20} value={maxConcurrent}
            onChange={(e) => setMaxConcurrent(Number(e.target.value))}
            className="w-20 rounded-lg border border-slate-600 bg-slate-700 px-3 py-1.5 text-slate-200 focus:border-indigo-500 focus:outline-none"
          />
        </div>
      </div>

      {/* ── IMAGE MODE ── */}
      {mode === "image" && (
        <>
          <Dropzone
            onFiles={handleImageFiles}
            accept={imageAccept}
            hint={hints[outputTarget].image}
            multiple
            allowFolder
            allowPaste
          />

          {/* Queue panel */}
          {queue.length > 0 && (
            <div className="rounded-xl border border-slate-700 bg-slate-800/60 overflow-hidden">
              <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-slate-700">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="font-semibold text-slate-200">{qStats.total} ảnh</span>
                  {qStats.running > 0 && <Badge color="indigo">{qStats.running} đang xử lý</Badge>}
                  {qStats.pending > 0 && <Badge color="slate">{qStats.pending} chờ</Badge>}
                  {qStats.done    > 0 && <Badge color="emerald">{qStats.done} xong</Badge>}
                  {qStats.errors  > 0 && <Badge color="red">{qStats.errors} lỗi</Badge>}
                </div>
                <button onClick={() => setQueue([])} className="text-xs text-slate-500 hover:text-slate-300 transition">
                  Xóa tất cả
                </button>
              </div>
              <ul className="max-h-64 overflow-y-auto divide-y divide-slate-700/60">
                {queue.map((item) => (
                  <QueueItem
                    key={item.id}
                    item={item}
                    onRemove={() => setQueue((p) => p.filter((q) => q.id !== item.id))}
                    onDownload={
                      item.status === "done" && item.result?.type !== "examlatex"
                        ? () => triggerDownload(item.result.data)
                        : null
                    }
                  />
                ))}
              </ul>
            </div>
          )}

          {/* Exam LaTeX results */}
          {outputTarget === "examlatex" && queue.some((q) => q.status === "done") && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-slate-200">Kết quả Exam LaTeX</h3>
                <CopyButton
                  text={queue
                    .filter((q) => q.status === "done" && q.result?.data?.latex)
                    .map((q) => q.result.data.latex)
                    .join("\n\n")}
                  label="Copy tất cả"
                />
              </div>
              {queue
                .filter((q) => q.status === "done" && q.result?.data?.latex)
                .map((q) => (
                  <div key={q.id} className="space-y-1">
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-medium text-slate-400 truncate">{q.name}</p>
                      <CopyButton text={q.result.data.latex} />
                    </div>
                    <ExamLatexBlock latex={q.result.data.latex} />
                  </div>
                ))}
            </div>
          )}

          {/* Word / Equation download list */}
          {(outputTarget === "word" || outputTarget === "equation") &&
            queue.some((q) => q.status === "done") && (
              <div className="space-y-2">
                <h3 className="font-semibold text-slate-200">File đã tạo</h3>
                {queue
                  .filter((q) => q.status === "done")
                  .map((q) => (
                    <WordResultRow
                      key={q.id}
                      name={q.name}
                      payload={q.result.data}
                      onDownload={() => triggerDownload(q.result.data)}
                    />
                  ))}
              </div>
            )}
        </>
      )}

      {/* ── PDF MODE ── */}
      {mode === "pdf" && (
        <>
          <Dropzone onFile={handlePdfFile} accept={pdfAccept} hint={hints[outputTarget].pdf} />

          {pdfLoading && (
            <div className="flex items-center gap-3 rounded-xl border border-indigo-500/20 bg-indigo-500/10 p-4 text-indigo-300">
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-400 border-t-transparent shrink-0" />
              <span className="text-sm">{loadingMsg[outputTarget]}</span>
            </div>
          )}

          {pdfError && (
            <div className="flex items-start gap-3 rounded-xl border border-red-500/20 bg-red-500/10 p-4">
              <ErrIcon />
              <p className="text-sm text-red-300">{pdfError}</p>
            </div>
          )}

          {(pdfResult?.type === "word" || pdfResult?.type === "equation") && (
            <WordResultBlock
              result={pdfResult.data}
              onDownloadAgain={() => triggerDownload(pdfResult.data)}
              isEquation={pdfResult.type === "equation"}
            />
          )}

          {pdfResult?.type === "examlatex" && pdfResult.data?.latex !== undefined && (
            <ExamLatexBlock latex={pdfResult.data.latex} />
          )}

          {pdfResult?.type === "examlatex" &&
            pdfResult.data?.pages?.map((page) => (
              <div key={page.page} className="space-y-2">
                <h3 className="font-semibold text-slate-200">
                  Trang {page.page}
                  {page.error && <span className="ml-2 text-xs text-red-400">(lỗi: {page.error})</span>}
                </h3>
                {page.latex && <ExamLatexBlock latex={page.latex} />}
              </div>
            ))}
        </>
      )}
    </div>
  );
}

// ─── sub-components ──────────────────────────────────────────────────────────

function Badge({ color, children }) {
  const cls = { indigo: "bg-indigo-500/20 text-indigo-300", emerald: "bg-emerald-500/20 text-emerald-300", red: "bg-red-500/20 text-red-300", slate: "bg-slate-600/60 text-slate-400" };
  return <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${cls[color] ?? cls.slate}`}>{children}</span>;
}

function QueueItem({ item, onRemove, onDownload }) {
  const icon = {
    pending: <span className="h-4 w-4 rounded-full border-2 border-slate-600 inline-block shrink-0" />,
    running: <span className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-400 border-t-transparent inline-block shrink-0" />,
    done:    <svg className="w-4 h-4 shrink-0 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>,
    error:   <svg className="w-4 h-4 shrink-0 text-red-400"     fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>,
  };

  return (
    <li className="flex items-center gap-3 px-4 py-2.5 text-sm">
      {icon[item.status]}
      <span className="flex-1 truncate text-slate-300" title={item.name}>{item.name}</span>
      {item.error && <span className="shrink-0 text-xs text-red-400 max-w-[180px] truncate" title={item.error}>{item.error}</span>}
      {onDownload && (
        <button onClick={onDownload} title="Tải lại" className="shrink-0 text-emerald-400 hover:text-emerald-300 transition">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
        </button>
      )}
      {item.status !== "running" && (
        <button onClick={onRemove} title="Xóa" className="shrink-0 text-slate-600 hover:text-slate-400 transition">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </li>
  );
}

function WordResultRow({ name, payload, onDownload }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-700 bg-slate-800 px-4 py-3 text-sm">
      <div>
        <p className="font-medium text-slate-200">{name}</p>
        <p className="text-xs text-slate-500 mt-0.5">{payload.filename} · {payload.total_formulas} công thức</p>
      </div>
      <button
        onClick={onDownload}
        className="flex items-center gap-1.5 rounded-lg bg-emerald-700/40 hover:bg-emerald-600/50 px-3 py-1.5 text-xs font-semibold text-emerald-300 transition"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Tải lại
      </button>
    </div>
  );
}

function ExamLatexBlock({ latex }) {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-slate-500">
          Định dạng <code className="text-slate-400">\begin&#123;ex&#125;...\choice...\end&#123;ex&#125;</code>
        </p>
        <CopyButton text={latex} />
      </div>
      <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-4 text-sm text-emerald-400 border border-slate-800 leading-relaxed">
        {latex}
      </pre>
    </div>
  );
}

function WordResultBlock({ result, onDownloadAgain, isEquation = false }) {
  const label = isEquation ? "Equation (.docx)" : "Word + Toggle TeX";
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
            <h3 className="font-semibold text-emerald-300">Đã tạo file {label}</h3>
            <p className="text-sm text-emerald-400/70">File: <span className="font-medium">{result.filename}</span></p>
          </div>
        </div>
        <button
          onClick={onDownloadAgain}
          className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 shadow-lg shadow-emerald-600/25"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Tải lại .docx
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <SummaryItem label="Nguồn" value={result.source_type === "pdf" ? "PDF" : "Ảnh"} />
        <SummaryItem label="Công thức" value={String(result.total_formulas)} />
        <SummaryItem label="Định dạng CT" value={isEquation ? "OMML" : "Toggle TeX"} />
        <SummaryItem label="Trang lỗi" value={String(result.errors)} />
      </div>

      {result.pages?.length > 0 && (
        <div className="rounded-xl border border-slate-700 bg-slate-800/60 p-4">
          <h4 className="text-sm font-semibold text-slate-300 mb-3">Tổng hợp theo trang</h4>
          <div className="grid gap-2 sm:grid-cols-2">
            {result.pages.map((page) => (
              <div key={page.page} className="rounded-lg border border-slate-700 bg-slate-800 p-3 text-sm">
                <div className="font-medium text-slate-200">Trang {page.page}</div>
                <div className="mt-1 text-slate-400">Công thức: <span className="font-medium text-slate-300">{page.formula_count}</span></div>
                {page.error && <div className="mt-1.5 text-xs text-red-400">Lỗi OCR: {page.error}</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      {!isEquation && result.latex_output && (
        <div className="space-y-3 rounded-xl border border-slate-700 bg-slate-800/60 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h4 className="text-sm font-semibold text-slate-200">LaTeX cho Toggle TeX</h4>
            <CopyButton text={result.latex_output} label="Copy tất cả" />
          </div>
          <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-4 text-sm text-emerald-400 border border-slate-800">
            {result.latex_output}
          </pre>
        </div>
      )}

      {result.formulas?.map((formula) => (
        <FormulaCard key={formula.id} formula={formula} isEquation={isEquation} />
      ))}
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
            Công thức #{formula.id}{formula.page ? ` — Trang ${formula.page}` : ""}
          </h5>
          <p className="text-xs text-slate-500 mt-0.5">{formula.display ? "Display math" : "Inline math"}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <CopyButton text={formula.latex_source || formula.latex} label="LaTeX" />
          <CopyButton text={formula.mathml || ""} label="MathML" />
        </div>
      </div>

      <div className="space-y-2">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide">LaTeX</div>
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

      {formula.mathml && (
        <div className="space-y-2">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide">MathML</div>
          <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-3 text-xs text-amber-400 border border-slate-800">
            {formula.mathml}
          </pre>
        </div>
      )}
    </div>
  );
}

// ─── icons ───────────────────────────────────────────────────────────────────

function InfoIcon() {
  return (
    <svg className="w-4 h-4 mt-0.5 shrink-0 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

function ErrIcon() {
  return (
    <svg className="w-4 h-4 mt-0.5 shrink-0 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

function ImageIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  );
}

function PdfIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
    </svg>
  );
}
