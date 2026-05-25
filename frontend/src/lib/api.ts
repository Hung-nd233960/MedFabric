import axios from "axios";
import { useAuthStore } from "@/store/authStore";

export const api = axios.create({
  baseURL: "/api",
  withCredentials: true, // send httpOnly refresh cookie
});

// Attach access token to every request
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On 401: try silent refresh, then retry once
let refreshing: Promise<string | null> | null = null;

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retried) {
      original._retried = true;

      if (!refreshing) {
        refreshing = api
          .post<{ access_token: string }>("/auth/refresh")
          .then((r) => {
            useAuthStore.getState().setAccessToken(r.data.access_token);
            return r.data.access_token;
          })
          .catch(() => {
            useAuthStore.getState().logout();
            return null;
          })
          .finally(() => {
            refreshing = null;
          });
      }

      const newToken = await refreshing;
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      }
    }
    return Promise.reject(error);
  }
);

// Typed helpers
export const authApi = {
  login: (username: string, password: string) =>
    api.post<{ access_token: string }>("/auth/login", { username, password }),
  register: (username: string, password: string, email?: string) =>
    api.post<{ access_token: string }>("/auth/register", { username, password, email }),
  logout: () => api.post("/auth/logout"),
};

export const dashboardApi = {
  stats: () => api.get("/dashboard/"),
};

export const datasetsApi = {
  list: (active_only = true) => api.get("/datasets/", { params: { active_only } }),
  create: (data: { name: string; description?: string }) => api.post("/datasets/", data),
  update: (uuid: string, data: object) => api.patch(`/datasets/${uuid}`, data),
};

export const patientsApi = {
  listByDataset: (datasetUuid: string) =>
    api.get(`/patients/by-dataset/${datasetUuid}`),
  create: (data: object) => api.post("/patients/", data),
  update: (uuid: string, data: object) => api.patch(`/patients/${uuid}`, data),
};

export const imageSetsApi = {
  listByDataset: (datasetUuid: string) =>
    api.get(`/image-sets/by-dataset/${datasetUuid}`),
  create: (data: object) => api.post("/image-sets/", data),
  get: (uuid: string) => api.get(`/image-sets/${uuid}`),
  update: (uuid: string, data: object) => api.patch(`/image-sets/${uuid}`, data),
};

export const imagesApi = {
  listByImageSet: (imageSetUuid: string) =>
    api.get(`/images/by-image-set/${imageSetUuid}`),
  renderUrl: (imageUuid: string, wl?: number, ww?: number) => {
    const params = new URLSearchParams();
    if (wl != null) params.set("wl", String(wl));
    if (ww != null) params.set("ww", String(ww));
    const qs = params.toString();
    return `/api/images/${imageUuid}/render${qs ? `?${qs}` : ""}`;
  },
};

export const annotationSessionsApi = {
  open: (imageSetUuid: string) =>
    api.post("/annotation-sessions/", { image_set_uuid: imageSetUuid }),
  get: (uuid: string) => api.get(`/annotation-sessions/${uuid}`),
  mine: (submitted_only = false) =>
    api.get("/annotation-sessions/mine", { params: { submitted_only } }),
};

export const evaluationsApi = {
  submit: (payload: object) => api.post("/evaluations/submit", payload),
};

export const adminApi = {
  listDoctors: (include_inactive = false) =>
    api.get("/admin/doctors", { params: { include_inactive } }),
  createDoctor: (data: object) => api.post("/admin/doctors", data),
  updateDoctor: (uuid: string, data: object) => api.patch(`/admin/doctors/${uuid}`, data),
  assign: (data: { doctor_uuid: string; dataset_uuid: string }) =>
    api.post("/admin/assignments", data),
  getAssignment: (doctorUuid: string) => api.get(`/admin/assignments/${doctorUuid}`),
  revokeAssignment: (id: number) => api.delete(`/admin/assignments/${id}`),
  auditLog: (limit = 200, offset = 0) =>
    api.get("/admin/audit-log", { params: { limit, offset } }),
};

export const exportApi = {
  download: (format: "xlsx" | "csv", datasetUuid?: string) => {
    const params = new URLSearchParams({ format });
    if (datasetUuid) params.set("dataset_uuid", datasetUuid);
    return `/api/export/annotations?${params.toString()}`;
  },
};
