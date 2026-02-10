import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const client = axios.create({
  baseURL: API_BASE_URL
});

export const listTemplates = () => client.get("/api/templates");
export const getSystemInfo = () => client.get("/api/system/info");
export const listPapers = () => client.get("/api/papers");
export const getPaperById = (paperId) => client.get(`/api/papers/${paperId}`);
export const getPaperContent = (paperId, kind) => client.get(`/api/papers/${paperId}/content/${kind}`);
export const askPaper = (paperId, payload) => client.post(`/api/papers/${paperId}/chat`, payload);

export const uploadPaper = (file, targetLanguage, summaryTemplate) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("target_language", targetLanguage);
  formData.append("summary_template", summaryTemplate);
  return client.post("/api/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data"
    }
  });
};
