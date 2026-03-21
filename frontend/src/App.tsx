import { useState, useEffect } from "react";
import "./App.css";
import * as pdfjsLib from "pdfjs-dist";
import pdfWorker from "pdfjs-dist/build/pdf.worker?url";

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorker;

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrls, setPreviewUrls] = useState<string[]>([]);
  const [processedPreview, setProcessedPreview] = useState<string[]>([]);

  const [size, setSize] = useState("4x6");
  const [output, setOutput] = useState("separate");
  const [zip, setZip] = useState(true);

  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);

  const API_URL = import.meta.env.VITE_API_URL;

  // ================= ORIGINAL PREVIEW =================
  const generatePreview = async (file: File) => {
    const pdf = await pdfjsLib.getDocument(await file.arrayBuffer()).promise;

    const urls: string[] = [];

    for (let i = 1; i <= Math.min(2, pdf.numPages); i++) {
      const page = await pdf.getPage(i);
      const viewport = page.getViewport({ scale: 1 });

      const canvas = document.createElement("canvas");
      const context = canvas.getContext("2d")!;

      canvas.width = viewport.width;
      canvas.height = viewport.height;

      await page.render({ canvasContext: context, viewport, canvas }).promise;

      urls.push(canvas.toDataURL());
    }

    setPreviewUrls(urls);
  };

  // ================= PROCESSED PREVIEW =================
  const fetchPreview = async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("size", size);
    formData.append("output", output);

    const res = await fetch(`${API_URL}/preview`, {
      method: "POST",
      body: formData,
    });

    const data = await res.json();

    setProcessedPreview(
      data.images.map((img: string) => `data:image/png;base64,${img}`)
    );
  };

  const handleFile = (f: File) => {
    setFile(f);
    generatePreview(f);
    fetchPreview(f);
  };

  useEffect(() => {
    if (file) fetchPreview(file);
  }, [size, output]);

  // ================= UPLOAD =================
  const upload = () => {
    if (!file) return alert("Upload file");

    setLoading(true);
    setProgress(0);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("size", size);
    formData.append("output", output);
    formData.append("zip_enabled", zip ? "1" : "0");

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}/process`);
    xhr.responseType = "blob";

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        setProgress(Math.round((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = async () => {
      if (xhr.status !== 200) {
        const text = await xhr.response.text();
        console.error("Backend error:", text);
        alert("Backend error: " + text);
        setLoading(false);
        return;
      }

      const blob = xhr.response;

      if (!blob || blob.size < 100) {
        alert("Invalid file ❌");
        setLoading(false);
        return;
      }

      const url = window.URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = zip ? "output.zip" : "output.pdf";
      a.click();

      setLoading(false);
    };

    xhr.onerror = () => {
      alert("Network error");
      setLoading(false);
    };

    xhr.send(formData);
  };

  return (
    <div className="container">
      <h1>📦 Label Processor</h1>

      <input
        type="file"
        accept="application/pdf"
        onChange={(e) => e.target.files && handleFile(e.target.files[0])}
      />

      <div className="options">
        <div className="toggle">
          <button className={size === "3x5" ? "active" : ""} onClick={() => setSize("3x5")}>3x5</button>
          <button className={size === "4x6" ? "active" : ""} onClick={() => setSize("4x6")}>4x6</button>
        </div>

        <div className="toggle">
          <button className={output === "separate" ? "active" : ""} onClick={() => setOutput("separate")}>Separate</button>
          <button className={output === "combined" ? "active" : ""} onClick={() => setOutput("combined")}>Combined</button>
        </div>

        <div className="toggle">
          <button className={zip ? "active" : ""} onClick={() => setZip(true)}>ZIP</button>
          <button className={!zip ? "active" : ""} onClick={() => setZip(false)}>PDF</button>
        </div>
      </div>

      <div className="preview-container">
        <div className="preview-box">
          <h3>Original</h3>
          {previewUrls.map((url, i) => <img key={i} src={url} />)}
        </div>

        <div className="preview-box">
          <h3>Processed</h3>
          {processedPreview.map((url, i) => <img key={i} src={url} />)}
        </div>
      </div>

      {loading && (
        <div className="progress">
          <div style={{ width: `${progress}%` }} />
        </div>
      )}

      <button onClick={upload}>
        {loading ? `${progress}%` : "🚀 Process"}
      </button>
    </div>
  );
}

export default App;