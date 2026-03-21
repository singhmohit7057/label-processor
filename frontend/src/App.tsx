import { useState, useEffect } from "react";
import "./App.css";

function App() {
  const API_URL = import.meta.env.VITE_API_URL;

  const [file, setFile] = useState<File | null>(null);
  const [originalUrl, setOriginalUrl] = useState<string>("");
  const [processedPreview, setProcessedPreview] = useState<string[]>([]);

  const [size, setSize] = useState("4x6");
  const [output, setOutput] = useState("separate");
  const [zip, setZip] = useState(true);

  const [loading, setLoading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [progress, setProgress] = useState(0);

  // Clean up memory when previews change
  useEffect(() => {
    return () => {
      if (originalUrl) URL.revokeObjectURL(originalUrl);
    };
  }, [originalUrl]);

  const fetchPreview = async (targetFile: File) => {
    setPreviewLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", targetFile);
      formData.append("size", size);

      const res = await fetch(`${API_URL}/preview`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (data.images) {
        setProcessedPreview(data.images.map((img: string) => `data:image/png;base64,${img}`));
      }
    } catch (err) {
      console.error("Preview failed", err);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) {
      setFile(f);
      setOriginalUrl(URL.createObjectURL(f));
      fetchPreview(f);
    }
  };

  useEffect(() => {
    if (file) fetchPreview(file);
  }, [size]);

  const handleUpload = () => {
    if (!file) return;
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
      if (e.lengthComputable) setProgress(Math.round((e.loaded / e.total) * 100));
    };

    xhr.onload = () => {
      if (xhr.status === 200) {
        const url = window.URL.createObjectURL(xhr.response);
        const a = document.createElement("a");
        a.href = url;
        a.download = zip ? "labels.zip" : "label.pdf";
        a.click();
      } else {
        alert("Processing failed. Check backend logs.");
      }
      setLoading(false);
    };

    xhr.send(formData);
  };

  return (
    <div className="container">
      <h1>📦 Label Processor</h1>
      <p className="subtitle">Flipkart Label & Invoice Splitter</p>

      <div className="dropzone">
        <input type="file" accept=".pdf" onChange={handleFileChange} />
        <p>{file ? file.name : "Click to upload Label PDF"}</p>
      </div>

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
          {originalUrl && <embed src={originalUrl} width="100%" height="200px" type="application/pdf" />}
        </div>
        <div className="preview-box">
          <h3>Processed</h3>
          {previewLoading ? <p>Processing...</p> : (
            processedPreview.map((src, i) => <img key={i} src={src} alt="preview" />)
          )}
        </div>
      </div>

      {loading && <div className="progress"><div style={{ width: `${progress}%` }} /></div>}
      
      <button disabled={loading || !file} onClick={handleUpload}>
        {loading ? `Processing ${progress}%` : "🚀 Download Processed Labels"}
      </button>
    </div>
  );
}

export default App;