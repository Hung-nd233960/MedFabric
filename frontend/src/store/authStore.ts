import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { DoctorRole } from "@/lib/types";
import { useAppearanceStore, type UserPreferences } from "@/store/appearanceStore";

interface AuthState {
  accessToken: string | null;
  role: DoctorRole | null;
  doctorUuid: string | null;
  username: string | null;
  fullName: string | null;
  isTest: boolean;
  mustChangePassword: boolean;
  mustSetName: boolean;
  setAuth: (token: string, mustChangePassword?: boolean, mustSetName?: boolean, preferences?: UserPreferences) => void;
  setAccessToken: (token: string, mustChangePassword?: boolean, mustSetName?: boolean, preferences?: UserPreferences) => void;
  setMustChangePassword: (v: boolean) => void;
  setMustSetName: (v: boolean) => void;
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
      fullName: null,
      isTest: false,
      mustChangePassword: false,
      mustSetName: false,

      setAuth: (token, mustChangePassword = false, mustSetName = false, preferences) => {
        const payload = parseJwtPayload(token);
        if (preferences) useAppearanceStore.getState().hydrate(preferences);
        set({
          accessToken: token,
          doctorUuid: payload.sub as string,
          role: (payload.role as DoctorRole) ?? "Doctor",
          username: (payload.username as string) ?? null,
          fullName: (payload.full_name as string) || null,
          isTest: (payload.is_test as boolean) ?? false,
          mustChangePassword,
          mustSetName,
        });
      },

      setAccessToken: (token, mustChangePassword = false, mustSetName = false, preferences) => {
        const payload = parseJwtPayload(token);
        if (preferences) useAppearanceStore.getState().hydrate(preferences);
        set({
          accessToken: token,
          doctorUuid: payload.sub as string,
          role: (payload.role as DoctorRole) ?? "Doctor",
          username: (payload.username as string) ?? null,
          fullName: (payload.full_name as string) || null,
          isTest: (payload.is_test as boolean) ?? false,
          mustChangePassword,
          mustSetName,
        });
      },

      setMustChangePassword: (v) => set({ mustChangePassword: v }),
      setMustSetName: (v) => set({ mustSetName: v }),

      logout: () => {
        set({
          accessToken: null,
          role: null,
          doctorUuid: null,
          username: null,
          isTest: false,
          mustChangePassword: false,
          mustSetName: false,
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
        fullName: s.fullName,
        isTest: s.isTest,
        mustChangePassword: s.mustChangePassword,
        mustSetName: s.mustSetName,
      }),
    }
  )
);
