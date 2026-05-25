import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { DoctorRole } from "@/lib/types";

interface AuthState {
  accessToken: string | null;
  role: DoctorRole | null;
  doctorUuid: string | null;
  username: string | null;
  setAuth: (token: string) => void;
  setAccessToken: (token: string) => void;
  logout: () => void;
}

function parseJwtPayload(token: string): Record<string, unknown> {
  try {
    return JSON.parse(atob(token.split(".")[1]));
  } catch {
    return {};
  }
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      role: null,
      doctorUuid: null,
      username: null,

      setAuth: (token: string) => {
        const payload = parseJwtPayload(token);
        set({
          accessToken: token,
          doctorUuid: payload.sub as string,
          role: (payload.role as DoctorRole) ?? "Doctor",
        });
      },

      setAccessToken: (token: string) => {
        const payload = parseJwtPayload(token);
        set({
          accessToken: token,
          doctorUuid: payload.sub as string,
          role: (payload.role as DoctorRole) ?? "Doctor",
        });
      },

      logout: () => {
        set({ accessToken: null, role: null, doctorUuid: null, username: null });
      },
    }),
    {
      name: "medfabric-auth",
      partialize: (s) => ({
        accessToken: s.accessToken,
        role: s.role,
        doctorUuid: s.doctorUuid,
        username: s.username,
      }),
    }
  )
);
