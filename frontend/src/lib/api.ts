import axios from "axios";
import { useAuthStore } from "@/store/authStore";
import type { UserPreferences } from "@/store/appearanceStore";

type AuthResponse = { access_token: string; must_change_password: boolean; must_set_name: boolean; preferences: UserPreferences };

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
    const noRetry = original.url === "/auth/refresh" || original.url === "/auth/login" || original.url === "/auth/logout";
    if (error.response?.status === 401 && !original._retried && !noRetry) {
      original._retried = true;

      if (!refreshing) {
        refreshing = api
          .post<AuthResponse>("/auth/refresh")
          .then((r) => {
            useAuthStore.getState().setAccessToken(r.data.access_token, r.data.must_change_password, r.data.must_set_name, r.data.preferences);
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

// Proactive token refresh — reuses the same deduplication promise as the 401 interceptor
export function silentRefresh(): Promise<string | null> {
  if (!refreshing) {
    refreshing = api
      .post<AuthResponse>("/auth/refresh")
      .then((r) => {
        useAuthStore.getState().setAccessToken(r.data.access_token, r.data.must_change_password, r.data.must_set_name, r.data.preferences);
        return r.data.access_token;
      })
      .catch(() => {
        useAuthStore.getState().logout();
        return null;
      })
      .finally(() => { refreshing = null; });
  }
  return refreshing;
}

// Typed helpers
export const authApi = {
  login: (username: string, password: string) =>
    api.post<AuthResponse>("/auth/login", { username, password }),
  register: (username: string, password: string, full_name: string, email?: string, invitation_code?: string) =>
    api.post<AuthResponse>("/auth/register", { username, password, full_name, email, invitation_code }),
  logout: () => api.post("/auth/logout"),
  changePassword: (data: { new_password: string; current_password?: string }) =>
    api.post("/auth/change-password", data),
  setupAccount: (data: { full_name?: string; new_password?: string }) =>
    api.post("/auth/setup-account", data),
  heartbeat: () => api.post("/auth/heartbeat"),
  me: () => api.get<{ uuid: string; username: string; email: string | null; full_name: string | null; role: string; is_test: boolean; created_at: string | null }>("/auth/me"),
};

export const preferencesApi = {
  get: () => api.get<UserPreferences>("/auth/preferences"),
  save: (prefs: UserPreferences) => api.put("/auth/preferences", prefs),
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
  renderBlob: (imageUuid: string, wl?: number, ww?: number) => {
    const params: Record<string, string> = {};
    if (wl != null) params.wl = String(wl);
    if (ww != null) params.ww = String(ww);
    return api.get(`/images/${imageUuid}/render`, { params, responseType: "blob" });
  },
};

export const annotationSessionsApi = {
  open: (imageSetUuid: string) =>
    api.post("/annotation-sessions/", { image_set_uuid: imageSetUuid }),
  get: (uuid: string) => api.get(`/annotation-sessions/${uuid}`),
  mine: (submitted_only = false) =>
    api.get("/annotation-sessions/mine", { params: { submitted_only } }),
  myHistory: () => api.get("/annotation-sessions/my-history"),
};

export const evaluationsApi = {
  submit: (payload: object) => api.post("/evaluations/submit", payload),
  saveDraft: (payload: object) => api.post("/evaluations/draft", payload),
  saveAutoDraft: (payload: object) => api.post("/evaluations/auto-draft", payload),
  getDraftByImageSet: (imageSetUuid: string) =>
    api.get(`/evaluations/draft/by-image-set/${imageSetUuid}`),
  getSubmissionByImageSet: (imageSetUuid: string) =>
    api.get(`/evaluations/submission/by-image-set/${imageSetUuid}`),
  listMyDrafts: () => api.get("/evaluations/drafts/mine"),
  deleteDraftByImageSet: (imageSetUuid: string) =>
    api.delete(`/evaluations/draft/by-image-set/${imageSetUuid}`),
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
  listAllDrafts: () => api.get("/admin/drafts"),
  adminDeleteDraft: (annotationSessionUuid: string) =>
    api.delete(`/admin/drafts/${annotationSessionUuid}`),
  listSubmissions: (datasetUuid?: string) =>
    api.get("/admin/submissions", { params: datasetUuid ? { dataset_uuid: datasetUuid } : {} }),
  getSubmissionByImageSetAdmin: (imageSetUuid: string, doctorUuid: string) =>
    api.get(`/admin/submission/by-image-set/${imageSetUuid}`, { params: { doctor_uuid: doctorUuid } }),
};

export const aboutApi = {
  get: () => api.get("/about"),
  getDev: () => api.get("/about/dev"),
};

export const bugReportApi = {
  submit: (data: {
    type: "bug" | "feature";
    text: string;
    page: string;
    context?: {
      annotation_session_uuid?: string | null;
      image_set_uuid?: string | null;
      image_set_name?: string | null;
      image_index?: number | null;
    } | null;
  }) => api.post("/bug-reports", data),
};

export const exportApi = {
  download: (format: "xlsx" | "csv", datasetUuid?: string) => {
    const params = new URLSearchParams({ format });
    if (datasetUuid) params.set("dataset_uuid", datasetUuid);
    return `/api/export/annotations?${params.toString()}`;
  },
};
