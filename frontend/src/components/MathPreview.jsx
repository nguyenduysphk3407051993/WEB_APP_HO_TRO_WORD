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
  if (!latex?.trim()) {
    return <p className="italic text-slate-400">Chua co cong thuc de preview...</p>;
  }

  const source = latex.trim();
  let wrapped;
  if (display) {
    const dollarBlock = source.match(/^\$\$([\s\S]+)\$\$$/);
    const inlineMath = source.match(
      /^(?:\$([^$]+)\$|\\\(([\s\S]+)\\\))$/,
    );
    const body = dollarBlock
      ? dollarBlock[1].trim()
      : inlineMath
        ? (inlineMath[1] || inlineMath[2]).trim()
        : source;
    wrapped =
      source.startsWith("\\[") && source.endsWith("\\]")
        ? source
        : `\\[${body}\\]`;
  } else {
    wrapped =
      (source.startsWith("$") && source.endsWith("$")) ||
      (source.startsWith("\\(") && source.endsWith("\\)"))
        ? source
        : `$${source}$`;
  }
  return (
    <MathJaxContext config={config}>
      <div className="min-h-[60px] overflow-x-auto rounded-md border bg-white p-4">
        <MathJax dynamic>{wrapped}</MathJax>
      </div>
    </MathJaxContext>
  );
}
