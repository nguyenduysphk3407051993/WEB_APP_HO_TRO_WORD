import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 120000,
});

export const ocrImage = async (file) => {
  const fd = new FormData();
  fd.append("file", file);
  const { data } = await api.post("/ocr/image", fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const ocrPdf = async (file, dpi = 200) => {
  const fd = new FormData();
  fd.append("file", file);
  const { data } = await api.post(`/ocr/pdf?dpi=${dpi}`, fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const latexToMathml = async (latex, display = true) => {
  const { data } = await api.post("/convert/latex-to-mathml", { latex, display });
  return data;
};

export const latexToMathtype = async (latex, display = true) => {
  const { data } = await api.post("/convert/latex-to-mathtype", { latex, display });
  return data;
};

export const mathmlToLatex = async (mathml) => {
  const { data } = await api.post("/convert/mathml-to-latex", { mathml });
  return data;
};

export const latexToDocx = async (latex) => {
  const resp = await api.post(
    "/convert/latex-to-docx",
    { latex, display: true },
    { responseType: "blob" }
  );
  return resp.data;
};

export const docxToLatex = async (file) => {
  const fd = new FormData();
  fd.append("file", file);
  const { data } = await api.post("/convert/docx-to-latex", fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const docxExtractEquations = async (file) => {
  const fd = new FormData();
  fd.append("file", file);
  const { data } = await api.post("/convert/docx-extract-equations", fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};
