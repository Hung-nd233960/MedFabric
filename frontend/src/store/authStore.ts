import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { DoctorRole } from "@/lib/types";

interface AuthState {
  accessToken: string | null;
  role: DoctorRole | null;
  doctorUuid: string | null;
  username: string | null;
  mustChangePassword: boolean;
  setAuth: (token: string, mustChangePassword?: boolean) => void;
  setAccessToken: (token: string, mustChangePassword?: boolean) => void;
  setMustChangePassword: (v: boolean) => void;
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
      mustChangePassword: false,

      setAuth: (token: string, mustChangePassword = false) => {
        const payload = parseJwtPayload(token);
        set({
          accessToken: token,
          doctorUuid: payload.sub as string,
          role: (payload.role as DoctorRole) ?? "Doctor",
          username: (payload.username as string) ?? null,
          mustChangePassword,
        });
      },

      setAccessToken: (token: string, mustChangePassword = false) => {
        const payload = parseJwtPayload(token);
        set({
          accessToken: token,
          doctorUuid: payload.sub as string,
          role: (payload.role as DoctorRole) ?? "Doctor",
          username: (payload.username as string) ?? null,
          mustChangePassword,
        });
      },

      setMustChangePassword: (v: boolean) => set({ mustChangePassword: v }),

      logout: () => {
        set({
          accessToken: null,
          role: null,
          doctorUuid: null,
          username: null,
          mustChangePassword: false,
        });
      },
    }),
    {
      name: "medfabric-auth",
      partialize: (s) => ({
        accessToken: s.accessToken,
        role: s.role,
        doctorUuid: s.doctorUuid,
        username: s.username,
        mustChangePassword: s.mustChangePassword,
      }),
    }
  )
);
