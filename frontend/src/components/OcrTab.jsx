import { useState } from "react";
import Dropzone from "./Dropzone";
import MathPreview from "./MathPreview";
import CopyButton from "./CopyButton";
import {
  downloadOcrDocx,
  ocrImage,
  ocrImageToDocx,
  ocrPdf,
  ocrPdfToDocx,
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
        setResult({
          type: "word",
          data: payload,
        });
        return;
      }

      const data =
        mode === "image"
          ? await ocrImage(file, ocrMode)
          : await ocrPdf(file, { mode: "page", maxConcurrent });
      setResult({ type: "latex", data });
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
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
        Luong OCR nay tao file Word voi cong thuc o dang LaTeX text, san sang de
        MathType xu ly hang loat bang Toggle TeX.
      </div>

      <div className="flex flex-wrap gap-2">
        {["image", "pdf"].map((value) => (
          <button
            key={value}
            onClick={() => setMode(value)}
            className={`rounded-md px-4 py-2 text-sm font-medium transition ${
              mode === value
                ? "bg-indigo-600 text-white"
                : "bg-slate-200 text-slate-700 hover:bg-slate-300"
            }`}
          >
            {value === "image" ? "Anh" : "PDF"}
          </button>
        ))}
      </div>

      <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <span className="font-medium text-slate-700">Dau ra:</span>
          {[
            { id: "word", label: "Word + Toggle TeX" },
            { id: "latex", label: "LaTeX" },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => setOutputTarget(item.id)}
              className={`rounded-full px-3 py-1.5 transition ${
                outputTarget === item.id
                  ? "bg-emerald-600 text-white"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {mode === "image" && (
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <label className="font-medium text-slate-700">Che do OCR:</label>
            <select
              value={ocrMode}
              onChange={(e) => setOcrMode(e.target.value)}
              className="rounded border border-slate-300 px-2 py-1"
            >
              <option value="single">1 cong thuc / vung nho</option>
              <option value="page">Ca trang / giu cau truc</option>
            </select>
          </div>
        )}

        {mode === "pdf" && (
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <label className="font-medium text-slate-700">Trang xu ly song song:</label>
            <input
              type="number"
              min={1}
              max={20}
              value={maxConcurrent}
              onChange={(e) => setMaxConcurrent(Number(e.target.value))}
              className="w-20 rounded border border-slate-300 px-2 py-1"
            />
            <span className="text-slate-500">
              Tang toc OCR PDF khi co nhieu key Gemini trong pool.
            </span>
          </div>
        )}
      </div>

      <Dropzone
        onFile={handleFile}
        accept={accept}
        hint={
          mode === "image"
            ? outputTarget === "word"
              ? "Tai anh de tao Word voi cong thuc LaTeX cho MathType Toggle TeX."
              : "PNG, JPG, JPEG, BMP, TIFF, WEBP (<= 50MB)"
            : outputTarget === "word"
              ? "Tai PDF de OCR sang Word, giu cong thuc LaTeX cho Toggle TeX."
              : "PDF nhieu trang - tra ket qua LaTeX theo tung trang."
        }
      />

      {loading && (
        <div className="flex items-center gap-3 text-indigo-600">
          <span className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
          {outputTarget === "word"
            ? "Dang OCR, tao Word va sinh MathML..."
            : "Dang goi Gemini API..."}
        </div>
      )}

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {result?.type === "word" && (
        <WordResultBlock result={result.data} onDownloadAgain={triggerDownload} />
      )}

      {result?.type === "latex" && result.data?.latex !== undefined && (
        <LatexResultBlock latex={result.data.latex} />
      )}

      {result?.type === "latex" &&
        result.data?.pages?.map((page) => (
          <div key={page.page} className="space-y-2">
            <h3 className="font-semibold">
              Trang {page.page}
              {page.error && (
                <span className="ml-2 text-xs text-red-600">(loi: {page.error})</span>
              )}
            </h3>
            {page.latex && <LatexResultBlock latex={page.latex} />}
          </div>
        ))}
    </div>
  );
}

function WordResultBlock({ result, onDownloadAgain }) {
  return (
    <div className="space-y-5">
      <div className="space-y-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="font-semibold text-emerald-900">Da tao xong file Word</h3>
            <p className="text-sm text-emerald-800">
              Ten file: <span className="font-medium">{result.filename}</span>
            </p>
          </div>
          <button
            onClick={() => onDownloadAgain(result)}
            className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800"
          >
            Tai lai .docx
          </button>
        </div>

        <div className="grid gap-3 text-sm text-emerald-900 md:grid-cols-4">
          <SummaryItem label="Loai nguon" value={result.source_type === "pdf" ? "PDF" : "Anh"} />
          <SummaryItem label="Tong cong thuc" value={String(result.total_formulas)} />
          <SummaryItem label="Dinh dang CT" value="Toggle TeX" />
          <SummaryItem label="Trang loi OCR" value={String(result.errors)} />
        </div>
      </div>

      <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-4">
        <h4 className="text-sm font-semibold text-slate-700">Tong hop theo trang</h4>
        <div className="grid gap-3 md:grid-cols-2">
          {result.pages?.map((page) => (
            <div
              key={page.page}
              className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm"
            >
              <div className="font-medium text-slate-800">Trang {page.page}</div>
              <div className="mt-1 text-slate-600">
                So cong thuc: <span className="font-medium">{page.formula_count}</span>
              </div>
              {page.error && (
                <div className="mt-2 text-red-600">Loi OCR: {page.error}</div>
              )}
            </div>
          ))}
        </div>
      </div>

      <LatexOutputPanel latexOutput={result.latex_output} />

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-slate-700">
            Danh sach cong thuc LaTeX / MathML
          </h4>
          <span className="text-sm text-slate-500">{result.total_formulas} cong thuc</span>
        </div>

        {!result.formulas?.length && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            Chua tach duoc cong thuc nao tu noi dung OCR. File Word van da duoc tao.
          </div>
        )}

        {result.formulas?.map((formula) => (
          <FormulaCard key={formula.id} formula={formula} />
        ))}
      </div>
    </div>
  );
}

function LatexOutputPanel({ latexOutput }) {
  return (
    <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h4 className="text-sm font-semibold text-slate-700">LaTeX cho Toggle TeX</h4>
          <p className="text-sm text-slate-500">
            Day cung la dang cong thuc duoc giu trong file Word de MathType xu ly hang loat.
          </p>
        </div>
        <CopyButton text={latexOutput || ""} label="Copy tat ca LaTeX" />
      </div>

      {latexOutput ? (
        <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-md bg-slate-950 p-3 text-sm text-emerald-300">
          {latexOutput}
        </pre>
      ) : (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          Chua co cong thuc LaTeX de xuat sang Toggle TeX.
        </div>
      )}
    </div>
  );
}

function SummaryItem({ label, value }) {
  return (
    <div className="rounded-lg bg-white/70 px-3 py-2">
      <div className="text-xs uppercase tracking-wide text-emerald-700">{label}</div>
      <div className="mt-1 font-semibold">{value}</div>
    </div>
  );
}

function FormulaCard({ formula }) {
  return (
    <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h5 className="font-semibold text-slate-800">
            Cong thuc #{formula.id}
            {formula.page ? ` - Trang ${formula.page}` : ""}
          </h5>
          <p className="text-sm text-slate-500">
            {formula.display ? "Display math" : "Inline math"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <CopyButton text={formula.latex_source || formula.latex} label="Copy LaTeX" />
          <CopyButton text={formula.raw_latex || formula.latex} label="Copy OCR goc" />
          <CopyButton text={formula.mathml || ""} label="Copy MathML" />
        </div>
      </div>

      {formula.raw_latex && formula.raw_latex !== formula.latex && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          Cong thuc nay da duoc lam sach tieng Viet/Unicode trong vung TeX de MathType Toggle
          TeX xu ly on dinh hon.
        </div>
      )}

      <div className="space-y-2">
        <div className="text-sm font-semibold text-slate-700">LaTeX cho Toggle TeX</div>
        <pre className="overflow-x-auto whitespace-pre-wrap rounded-md bg-slate-900 p-3 text-sm text-emerald-300">
          {formula.latex_source || formula.latex}
        </pre>
      </div>

      <div className="space-y-2">
        <div className="text-sm font-semibold text-slate-700">Preview</div>
        <MathPreview latex={formula.latex} display={formula.display} />
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold text-slate-700">MathML</div>
          {!formula.mathml && formula.mathml_error && (
            <span className="text-xs text-red-600">Khong sinh duoc MathML</span>
          )}
        </div>
        {formula.mathml ? (
          <pre className="overflow-x-auto whitespace-pre-wrap rounded-md bg-slate-900 p-3 text-xs text-amber-300">
            {formula.mathml}
          </pre>
        ) : (
          <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {formula.mathml_error || "Khong chuyen duoc sang MathML."}
          </div>
        )}
      </div>
    </div>
  );
}

function LatexResultBlock({ latex }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-slate-700">LaTeX</h4>
        <CopyButton text={latex} />
      </div>
      <pre className="overflow-x-auto whitespace-pre-wrap rounded-md bg-slate-900 p-3 text-sm text-emerald-300">
        {latex}
      </pre>
      <h4 className="text-sm font-semibold text-slate-700">Preview</h4>
      <MathPreview latex={latex} display />
    </div>
  );
}
