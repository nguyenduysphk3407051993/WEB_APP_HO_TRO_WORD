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
export const fetchStats = () => adminApi.get("/keys/stats").then((r) => r.data);
export const fetchProvider = () => adminApi.get("/provider").then((r) => r.data);
export const updateProvider = (model) =>
  adminApi.put("/provider", { model }).then((r) => r.data);
export const replaceKeys = (keys) => adminApi.post("/keys", { keys }).then((r) => r.data);
export const addKey = (key) => adminApi.post("/keys/add", { key }).then((r) => r.data);
export const removeKey = (index) => adminApi.delete(`/keys/${index}`).then((r) => r.data);
export const resetKey = (index) => adminApi.post(`/keys/${index}/reset`).then((r) => r.data);
export const testKeys = (keys) => adminApi.post("/keys/test", { keys }).then((r) => r.data);
