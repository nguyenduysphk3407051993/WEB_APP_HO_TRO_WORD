import { useState } from "react";
import OcrTab from "./components/OcrTab";
import LatexToMathTypeTab from "./components/LatexToMathTypeTab";
import LatexToEquationTab from "./components/LatexToEquationTab";
import DocxToLatexTab from "./components/DocxToLatexTab";
import AdminKeysTab from "./components/AdminKeysTab";

const TABS = [
  { id: "ocr", label: "PDF / Anh -> Word", component: OcrTab },
  { id: "mathtype", label: "LaTeX -> MathType", component: LatexToMathTypeTab },
  { id: "equation", label: "LaTeX -> Word Equation", component: LatexToEquationTab },
  { id: "docx2tex", label: "Word/MathType -> LaTeX", component: DocxToLatexTab },
  { id: "admin", label: "Quan ly API Keys", component: AdminKeysTab },
];

export default function App() {
  const [active, setActive] = useState("ocr");
  const ActiveComp = TABS.find((tab) => tab.id === active).component;

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-gradient-to-r from-emerald-600 to-cyan-600 text-white shadow">
        <div className="mx-auto max-w-6xl px-6 py-5">
          <h1 className="text-2xl font-bold">Bo chuyen doi tai lieu</h1>
          <p className="mt-1 text-sm text-emerald-100">
            PDF / Anh -&gt; Word la luong uu tien, cong thuc van giu duoc cho Word Equation
            khi OCR nhan dien tot.
          </p>
        </div>
      </header>

      <main className="mx-auto flex-1 w-full max-w-6xl px-6 py-8">
        <nav className="mb-6 flex flex-wrap gap-2 border-b border-slate-200">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActive(tab.id)}
              className={`border-b-2 px-4 py-2 text-sm font-medium transition ${
                active === tab.id
                  ? "border-emerald-600 text-emerald-700"
                  : "border-transparent text-slate-600 hover:text-slate-900"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        <section className="rounded-xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
          <ActiveComp />
        </section>
      </main>

      <footer className="py-4 text-center text-xs text-slate-500">
        FastAPI + Gemini Pool | React + Tailwind | Traefik
      </footer>
    </div>
  );
}
