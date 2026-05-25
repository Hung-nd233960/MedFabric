import { create } from "zustand";

interface NavGuardStore {
  interceptor: ((destination: string) => void) | null;
  setInterceptor: (fn: ((destination: string) => void) | null) => void;
}

export const useNavGuardStore = create<NavGuardStore>((set) => ({
  interceptor: null,
  setInterceptor: (fn) => set({ interceptor: fn }),
}));
