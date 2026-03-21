const API = import.meta.env.VITE_API_URL;

export const processPDF = (formData: FormData, onProgress: any) => {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.open("POST", `${API}/process`);
    xhr.responseType = "blob";

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status !== 200) {
        reject("Backend error");
        return;
      }
      resolve(xhr.response);
    };

    xhr.onerror = () => reject("Network error");

    xhr.send(formData);
  });
};