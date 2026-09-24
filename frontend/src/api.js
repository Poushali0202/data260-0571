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

export async function fetchNotices() {
  const res = await api.get("/api/notices");
  return res.data;
}

export async function fetchNotice(id) {
  const res = await api.get(`/api/notices/${id}`);
  return res.data;
}

export async function createNotice(data) {
  const res = await api.post("/api/notices", data);
  return res.data;
}

export async function updateNotice(id, data) {
  const res = await api.put(`/api/notices/${id}`, data);
  return res.data;
}

export async function deleteNotice(id) {
  await api.delete(`/api/notices/${id}`);
}
