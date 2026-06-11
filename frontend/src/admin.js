import axios from "axios";

const STORAGE_KEY = "doc_converter_admin_pw";

export const getAdminPassword = () => sessionStorage.getItem(STORAGE_KEY) || "";
export const setAdminPassword = (pw) => sessionStorage.setItem(STORAGE_KEY, pw);
export const clearAdminPassword = () => sessionStorage.removeItem(STORAGE_KEY);

const adminApi = axios.create({
  baseURL: "/api/admin",
  timeout: 120000,
});

adminApi.interceptors.request.use((cfg) => {
  cfg.headers["X-Admin-Password"] = getAdminPassword();
  return cfg;
});

export const authCheck = () => adminApi.get("/auth-check").then((r) => r.data);

// Provider config
export const fetchProvider = () => adminApi.get("/provider").then((r) => r.data);
export const updateProvider = (provider, model) =>
  adminApi.put("/provider", { provider, model }).then((r) => r.data);

// 9router keys
export const fetchStats = () => adminApi.get("/keys/stats").then((r) => r.data);
export const replaceKeys = (keys) => adminApi.post("/keys", { keys }).then((r) => r.data);
export const addKey = (key) => adminApi.post("/keys/add", { key }).then((r) => r.data);
export const removeKey = (index) => adminApi.delete(`/keys/${index}`).then((r) => r.data);
export const resetKey = (index) => adminApi.post(`/keys/${index}/reset`).then((r) => r.data);
export const testKeys = (keys) => adminApi.post("/keys/test", { keys }).then((r) => r.data);

// Gemini keys
export const fetchGeminiStats = () => adminApi.get("/gemini/keys/stats").then((r) => r.data);
export const replaceGeminiKeys = (keys) => adminApi.post("/gemini/keys", { keys }).then((r) => r.data);
export const addGeminiKey = (key) => adminApi.post("/gemini/keys/add", { key }).then((r) => r.data);
export const removeGeminiKey = (index) => adminApi.delete(`/gemini/keys/${index}`).then((r) => r.data);
export const resetGeminiKey = (index) => adminApi.post(`/gemini/keys/${index}/reset`).then((r) => r.data);
export const testGeminiKeys = (keys) => adminApi.post("/gemini/keys/test", { keys }).then((r) => r.data);
