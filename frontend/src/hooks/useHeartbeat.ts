import { useEffect } from "react";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";

const INTERVAL_MS = 60_000; // ping every 60 s

export function useHeartbeat() {
  const token = useAuthStore((s) => s.accessToken);

  useEffect(() => {
    if (!token) return;

    // Ping immediately on mount so last_seen is fresh right away
    authApi.heartbeat().catch(() => {});

    const id = setInterval(() => {
      authApi.heartbeat().catch(() => {});
    }, INTERVAL_MS);

    return () => clearInterval(id);
  }, [token]);
}
