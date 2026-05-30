import { useEffect } from "react";
import { authApi, silentRefresh } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";

const HEARTBEAT_MS = 60_000;
const REFRESH_BEFORE_MS = 60_000; // refresh 60 s before the token expires

function tokenExpiryMs(token: string): number | null {
  try {
    const exp = JSON.parse(atob(token.split(".")[1])).exp;
    return typeof exp === "number" ? exp * 1000 : null;
  } catch {
    return null;
  }
}

export function useHeartbeat() {
  const token = useAuthStore((s) => s.accessToken);

  useEffect(() => {
    if (!token) return;

    // Heartbeat interval — token is always valid by the time this fires
    authApi.heartbeat().catch(() => {});
    const heartbeatId = setInterval(() => {
      authApi.heartbeat().catch(() => {});
    }, HEARTBEAT_MS);

    // Proactive refresh — fire before the token expires so heartbeat never sees a 401
    const expiry = tokenExpiryMs(token);
    let refreshId: ReturnType<typeof setTimeout> | null = null;
    if (expiry !== null) {
      const delay = expiry - Date.now() - REFRESH_BEFORE_MS;
      if (delay > 0) {
        refreshId = setTimeout(() => silentRefresh(), delay);
      } else {
        // Token already close to expiry or past — refresh immediately
        silentRefresh();
      }
    }

    return () => {
      clearInterval(heartbeatId);
      if (refreshId !== null) clearTimeout(refreshId);
    };
  }, [token]);
}
