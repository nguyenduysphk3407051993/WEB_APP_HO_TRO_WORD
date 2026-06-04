import { MathJax, MathJaxContext } from "better-react-mathjax";

const config = {
  loader: { load: ["input/tex", "output/svg"] },
  tex: {
    inlineMath: [["$", "$"], ["\\(", "\\)"]],
    displayMath: [["$$", "$$"], ["\\[", "\\]"]],
  },
  svg: { fontCache: "global" },
};

export default function MathPreview({ latex, display = true }) {
  if (!latex) {
    return <p className="italic text-slate-400">Chua co cong thuc de preview...</p>;
  }

  const wrapped = display ? `$$${latex}$$` : `$${latex}$`;
  return (
    <MathJaxContext config={config}>
      <div className="min-h-[60px] overflow-x-auto rounded-md border bg-white p-4">
        <MathJax dynamic>{wrapped}</MathJax>
      </div>
    </MathJaxContext>
  );
}
