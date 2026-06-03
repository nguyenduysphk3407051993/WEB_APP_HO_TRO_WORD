import { useDropzone } from "react-dropzone";

export default function Dropzone({ onFile, accept, hint }) {
  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    accept,
    multiple: false,
    onDrop: (files) => files[0] && onFile(files[0]),
  });

  const file = acceptedFiles[0];

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition ${
        isDragActive
          ? "border-indigo-500 bg-indigo-50"
          : "border-slate-300 hover:border-slate-400 bg-white"
      }`}
    >
      <input {...getInputProps()} />
      <p className="text-slate-700">
        {file ? (
          <span className="font-medium">{file.name}</span>
        ) : isDragActive ? (
          "Thả file vào đây..."
        ) : (
          "Kéo & thả file hoặc click để chọn"
        )}
      </p>
      {hint && <p className="text-sm text-slate-500 mt-2">{hint}</p>}
    </div>
  );
}
