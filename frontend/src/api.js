import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8571",
  withCredentials: true,
});

export async function login(email, password) {
  const res = await api.post("/auth/login", { email, password });
  return res.data;
}

export async function logout() {
  await api.post("/auth/logout");
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
