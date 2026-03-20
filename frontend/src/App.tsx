import { useState } from "react";
import "./App.css";

import * as pdfjsLib from "pdfjs-dist";
import pdfWorker from "pdfjs-dist/build/pdf.worker?url";

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorker;

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);

  const [size, setSize] = useState("4x6");
  const [output, setOutput] = useState("separate");

  const [previewUrls, setPreviewUrls] = useState<string[]>([]);

  const API_URL = import.meta.env.VITE_API_URL;

  // =========================
  // 📄 PDF PREVIEW
  // =========================
  const generatePreview = async (file: File) => {
  const arrayBuffer = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

  const urls: string[] = [];

  for (let i = 1; i <= Math.min(pdf.numPages, 2); i++) {
    const page = await pdf.getPage(i);
    const viewport = page.getViewport({ scale: 1 });

    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d")!;

    canvas.width = viewport.width;
    canvas.height = viewport.height;

    await page.render({
      canvasContext: context,
      viewport,
      canvas: canvas,
    }).promise;

    urls.push(canvas.toDataURL());
  }

  setPreviewUrls(urls);
};

  // =========================
  // 📤 UPLOAD WITH PROGRESS
  // =========================
  const upload = async () => {
    if (!file) return alert("Upload a PDF first");

    setLoading(true);
    setProgress(0);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("size", size);
    formData.append("output", output);

    const xhr = new XMLHttpRequest();

    xhr.open("POST", `${API_URL}/process`);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const percent = (e.loaded / e.total) * 100;
        setProgress(Math.round(percent));
      }
    };

    xhr.onload = () => {
      const blob = new Blob([xhr.response], { type: "application/zip" });

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "output.zip";
      a.click();

      setLoading(false);
      setProgress(0);
    };

    xhr.responseType = "blob";
    xhr.send(formData);
  };

  // =========================
  // 📂 FILE SELECT
  // =========================
  const handleFile = (f: File) => {
    setFile(f);
    generatePreview(f);
  };

  return (
    <div className="container">
      <h1>📦 Label Processor</h1>
      <p className="subtitle">
        {output === "combined"
          ? "Preview: Combined Label"
          : "Preview: Shipping + Invoice"}
      </p>

      {/* DROPZONE */}
      <div
        className={`dropzone ${dragActive ? "active" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
        }}
        onClick={() => document.getElementById("fileInput")?.click()}
      >
        {file ? <p>📄 {file.name}</p> : <p>Drag & drop PDF or click</p>}

        <input
          id="fileInput"
          type="file"
          hidden
          accept="application/pdf"
          onChange={(e) =>
            e.target.files?.[0] && handleFile(e.target.files[0])
          }
        />
      </div>

      {/* OPTIONS */}
      <div className="options">
        <div>
          <label>Size</label>
          <select value={size} onChange={(e) => setSize(e.target.value)}>
            <option value="3x5">3x5</option>
            <option value="4x6">4x6</option>
          </select>
        </div>

        <div>
          <label>Output</label>
          <select value={output} onChange={(e) => setOutput(e.target.value)}>
            <option value="separate">Separate</option>
            <option value="combined">Combined</option>
          </select>
        </div>
      </div>

      {/* PREVIEW */}
      {previewUrls.length > 0 && (
        <div className="preview">
          {previewUrls.map((url, i) => (
            <img key={i} src={url} alt="preview" />
          ))}
        </div>
      )}

      {/* PROGRESS */}
      {loading && (
        <div className="progress">
          <div style={{ width: `${progress}%` }} />
        </div>
      )}

      {/* BUTTON */}
      <button onClick={upload} disabled={loading}>
        {loading ? `Uploading... ${progress}%` : "🚀 Process PDF"}
      </button>
    </div>
  );
}

export default App;