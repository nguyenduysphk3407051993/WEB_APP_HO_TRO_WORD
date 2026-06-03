import { useState } from "react";
import OcrTab from "./components/OcrTab";
import LatexToMathTypeTab from "./components/LatexToMathTypeTab";
import LatexToEquationTab from "./components/LatexToEquationTab";
import DocxToLatexTab from "./components/DocxToLatexTab";
import KeyStatsPanel from "./components/KeyStatsPanel";

const TABS = [
  { id: "ocr", label: "PDF / Ảnh → LaTeX", component: OcrTab },
  { id: "mathtype", label: "LaTeX → MathType", component: LatexToMathTypeTab },
  { id: "equation", label: "LaTeX → Word Equation", component: LatexToEquationTab },
  { id: "docx2tex", label: "Word/MathType → LaTeX", component: DocxToLatexTab },
  { id: "keys", label: "Trạng thái API Keys", component: KeyStatsPanel },
];

export default function App() {
  const [active, setActive] = useState("ocr");
  const ActiveComp = TABS.find((t) => t.id === active).component;

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-gradient-to-r from-indigo-600 to-blue-600 text-white shadow">
        <div className="max-w-6xl mx-auto px-6 py-5">
          <h1 className="text-2xl font-bold">Bộ chuyển đổi tài liệu</h1>
          <p className="text-indigo-100 text-sm mt-1">
            PDF / Ảnh ↔ LaTeX ↔ MathType ↔ Word Equation — tự host bằng Docker
          </p>
        </div>
      </header>

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">
        <nav className="flex flex-wrap gap-2 border-b border-slate-200 mb-6">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setActive(t.id)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                active === t.id
                  ? "border-indigo-600 text-indigo-700"
                  : "border-transparent text-slate-600 hover:text-slate-900"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>

        <section className="bg-slate-50 rounded-xl p-6 shadow-sm border border-slate-200">
          <ActiveComp />
        </section>
      </main>

      <footer className="text-center text-xs text-slate-500 py-4">
        Stack: FastAPI · pix2tex · pandoc · React · Tailwind. Docker-ready.
      </footer>
    </div>
  );
}
