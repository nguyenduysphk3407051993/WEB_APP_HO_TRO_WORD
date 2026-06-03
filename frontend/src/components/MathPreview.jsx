import { MathJax, MathJaxContext } from "better-react-mathjax";

const config = {
  loader: { load: ["input/tex", "output/svg"] },
  tex: { inlineMath: [["$", "$"], ["\\(", "\\)"]], displayMath: [["$$", "$$"], ["\\[", "\\]"]] },
  svg: { fontCache: "global" },
};

export default function MathPreview({ latex, display = true }) {
  if (!latex) {
    return <p className="text-slate-400 italic">Chưa có công thức để preview...</p>;
  }
  const wrapped = display ? `$$${latex}$$` : `$${latex}$`;
  return (
    <MathJaxContext config={config}>
      <div className="bg-white p-4 rounded-md border min-h-[60px] overflow-x-auto">
        <MathJax dynamic>{wrapped}</MathJax>
      </div>
    </MathJaxContext>
  );
}
