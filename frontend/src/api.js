import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8571",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function login(username, password) {
  const form = new URLSearchParams({ username, password });
  const res = await api.post("/auth/login", form);
  localStorage.setItem("token", res.data.access_token);
  return me();
}

export function logout() {
  localStorage.removeItem("token");
}

export async function me() {
  const res = await api.get("/auth/me");
  return res.data;
}

export async function fetchSuppliers() {
  const res = await api.get("/api/suppliers", { params: { page_size: 200 } });
  return res.data;
}

export default api;
