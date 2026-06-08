import { useState } from "react";
import OcrTab from "./components/OcrTab";
import LatexToMathTypeTab from "./components/LatexToMathTypeTab";
import LatexToEquationTab from "./components/LatexToEquationTab";
import DocxToLatexTab from "./components/DocxToLatexTab";
import AdminKeysTab from "./components/AdminKeysTab";

// SVG Icons
const Icons = {
  ocr: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  mathtype: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
        d="M4.5 12h15m-7.5-7.5v15M3 7l3-3 3 3M15 17l3 3 3-3" />
    </svg>
  ),
  equation: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
        d="M9 7h6M9 12h6m-6 5h6M5 3h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2z" />
    </svg>
  ),
  docx2tex: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
        d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
    </svg>
  ),
  admin: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
        d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
    </svg>
  ),
  menu: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  ),
  close: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
};

const TABS = [
  {
    id: "ocr",
    label: "PDF / Ảnh → Word",
    badge: "OCR",
    badgeColor: "bg-violet-500/20 text-violet-300",
    icon: Icons.ocr,
    component: OcrTab,
    desc: "Nhận dạng tài liệu, giữ công thức LaTeX",
  },
  {
    id: "mathtype",
    label: "LaTeX → MathType",
    badge: "MathML",
    badgeColor: "bg-sky-500/20 text-sky-300",
    icon: Icons.mathtype,
    component: LatexToMathTypeTab,
    desc: "Chuyển đổi sang định dạng MathType",
  },
  {
    id: "equation",
    label: "LaTeX → Word Equation",
    badge: "OMML",
    badgeColor: "bg-emerald-500/20 text-emerald-300",
    icon: Icons.equation,
    component: LatexToEquationTab,
    desc: "Tạo file Word với Equation Editor",
  },
  {
    id: "docx2tex",
    label: "Word / MathType → LaTeX",
    badge: "TeX",
    badgeColor: "bg-amber-500/20 text-amber-300",
    icon: Icons.docx2tex,
    component: DocxToLatexTab,
    desc: "Trích xuất công thức từ Word",
  },
  {
    id: "admin",
    label: "Quản lý API Keys",
    badge: "Admin",
    badgeColor: "bg-rose-500/20 text-rose-300",
    icon: Icons.admin,
    component: AdminKeysTab,
    desc: "Cấu hình kết nối 9router",
  },
];

export default function App() {
  const [active, setActive] = useState("ocr");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const activeTab = TABS.find((tab) => tab.id === active);
  const ActiveComp = activeTab.component;

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950">
      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ===== SIDEBAR ===== */}
      <aside
        className={`fixed inset-y-0 left-0 z-30 flex w-64 flex-col bg-slate-900 border-r border-slate-800 transform transition-transform duration-300 ease-in-out
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full"} lg:relative lg:translate-x-0`}
      >
        {/* Logo */}
        <div className="flex items-center justify-between px-5 py-5 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-sky-500 shadow-lg shadow-indigo-500/30">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <div>
              <div className="text-sm font-bold text-white leading-tight">DocTools</div>
              <div className="text-[10px] text-slate-400 leading-tight">Bộ chuyển đổi tài liệu</div>
            </div>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
          >
            {Icons.close}
          </button>
        </div>

        {/* Nav items */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          <div className="px-2 pb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            Công cụ
          </div>
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => { setActive(tab.id); setSidebarOpen(false); }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left group
                ${active === tab.id
                  ? "bg-indigo-500/15 text-indigo-300 border border-indigo-500/30"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-transparent"
                }`}
            >
              <span className={`shrink-0 ${active === tab.id ? "text-indigo-400" : "text-slate-500 group-hover:text-slate-300"}`}>
                {tab.icon}
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium truncate">{tab.label}</div>
                <div className="text-[10px] text-slate-500 truncate mt-0.5">{tab.desc}</div>
              </div>
              <span className={`shrink-0 text-[10px] font-semibold px-1.5 py-0.5 rounded-md ${tab.badgeColor}`}>
                {tab.badge}
              </span>
            </button>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-4 py-4 border-t border-slate-800">
          <div className="text-[10px] text-slate-600 leading-relaxed">
            FastAPI + React + Tailwind
            <br />
            OCR via 9router HTTP API
          </div>
        </div>
      </aside>

      {/* ===== MAIN CONTENT ===== */}
      <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="flex items-center gap-4 px-6 py-4 bg-slate-900/80 backdrop-blur border-b border-slate-800 shrink-0">
          {/* Mobile menu button */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
          >
            {Icons.menu}
          </button>

          <div className="flex items-center gap-3 min-w-0">
            <span className={`shrink-0 p-2 rounded-lg ${
              active === "ocr" ? "bg-violet-500/15 text-violet-400" :
              active === "mathtype" ? "bg-sky-500/15 text-sky-400" :
              active === "equation" ? "bg-emerald-500/15 text-emerald-400" :
              active === "docx2tex" ? "bg-amber-500/15 text-amber-400" :
              "bg-rose-500/15 text-rose-400"
            }`}>
              {activeTab.icon}
            </span>
            <div>
              <h1 className="text-base font-semibold text-white">{activeTab.label}</h1>
              <p className="text-xs text-slate-400">{activeTab.desc}</p>
            </div>
          </div>

          <div className="ml-auto flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" title="Online" />
            <span className="text-xs text-slate-500 hidden sm:block">API Online</span>
          </div>
        </header>

        {/* Tab content */}
        <main className="flex-1 overflow-y-auto p-6 bg-slate-950">
          <div className="mx-auto max-w-4xl">
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl shadow-black/50">
              <ActiveComp />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
