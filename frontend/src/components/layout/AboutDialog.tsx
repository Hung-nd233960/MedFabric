import { useState, useEffect } from "react";
import * as React from "react";
import { Mail, ExternalLink, Wrench } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { aboutApi } from "@/lib/api";

const REACT_VERSION = React.version;

interface AboutInfo {
  name?: string;
  version?: string;
  description?: string;
  creator?: string;
  institution?: string;
  contact_email?: string;
  project_url?: string;
}

interface DevInfo {
  python_version?: string;
  fastapi_version?: string;
  sqlalchemy_version?: string;
  postgres_version?: string;
  startup_time?: string;
  uptime_seconds?: number;
  docker_version?: string | null;
}

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  return `${m}m ${s}s`;
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "medium", timeZone: "Asia/Bangkok" });
}

export default function AboutDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const [info, setInfo] = useState<AboutInfo | null>(null);
  const [devInfo, setDevInfo] = useState<DevInfo | null>(null);
  const [loadingAbout, setLoadingAbout] = useState(false);
  const [loadingDev, setLoadingDev] = useState(false);
  const [showDev, setShowDev] = useState(false);
  const [uptimeSecs, setUptimeSecs] = useState<number | null>(null);

  useEffect(() => {
    if (!open) { setShowDev(false); return; }
    if (info) return;
    setLoadingAbout(true);
    aboutApi.get().then((res) => setInfo(res.data)).catch(() => setInfo({})).finally(() => setLoadingAbout(false));
  }, [open, info]);

  useEffect(() => {
    if (!devInfo?.startup_time) return;
    const origin = new Date(devInfo.startup_time).getTime();
    const tick = () => setUptimeSecs(Math.floor((Date.now() - origin) / 1000));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [devInfo?.startup_time]);

  const toggleDev = async () => {
    const next = !showDev;
    setShowDev(next);
    if (next && !devInfo) {
      setLoadingDev(true);
      try {
        const res = await aboutApi.getDev();
        setDevInfo(res.data);
      } catch {
        setDevInfo({});
      } finally {
        setLoadingDev(false);
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className={`transition-all duration-300 ${showDev ? "max-w-2xl" : "max-w-sm"}`}
        onKeyDown={(e) => { if (e.key === "Tab") { e.preventDefault(); e.nativeEvent.stopPropagation(); toggleDev(); } }}
      >
        <button
          onClick={toggleDev}
          title="Developer information"
          className={`absolute right-12 top-4 rounded-sm opacity-70 transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring ${showDev ? "opacity-100 text-primary" : ""}`}
        >
          <Wrench className="h-4 w-4" />
        </button>

        <DialogHeader className="pr-16">
          <DialogTitle className="flex items-center gap-2 text-lg">
            <span className="text-primary font-bold">{info?.name ?? "MedFabric"}</span>
            {info?.version && (
              <span className="text-muted-foreground text-sm font-normal">v{info.version}</span>
            )}
          </DialogTitle>
        </DialogHeader>

        {loadingAbout ? (
          <p className="text-sm text-muted-foreground py-4 text-center">Loading…</p>
        ) : (
          <div className={`flex gap-6 text-sm ${showDev ? "items-start" : ""}`}>
            <div className="flex-1 min-w-0 space-y-4">
              {info?.description && (
                <p className="text-muted-foreground">{info.description}</p>
              )}
              <div className="space-y-2">
                {info?.version     && <Row label="Version"     value={info.version} />}
                {info?.creator     && <Row label="Creator"     value={info.creator} />}
                {info?.institution && <Row label="Institution" value={info.institution} />}
              </div>
              <div className="flex flex-col gap-2 pt-1">
                {info?.contact_email && (
                  <a
                    href={`mailto:${info.contact_email}`}
                    className="flex items-center gap-2 text-primary hover:underline underline-offset-4"
                  >
                    <Mail className="h-4 w-4 shrink-0" />
                    {info.contact_email}
                  </a>
                )}
                {info?.project_url && (
                  <a
                    href={info.project_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-2 text-primary hover:underline underline-offset-4"
                  >
                    <ExternalLink className="h-4 w-4 shrink-0" />
                    Project page
                  </a>
                )}
              </div>
              <p className="text-xs text-muted-foreground border-t border-border pt-3">
                For issues or questions, contact the creator via email above.
              </p>
            </div>

            {showDev && (
              <>
                <div className="w-px self-stretch bg-border shrink-0" />
                <div className="flex-1 min-w-0 space-y-4">
                  <p className="font-medium text-muted-foreground text-xs uppercase tracking-wide">
                    Developer Information
                  </p>
                  {loadingDev ? (
                    <p className="text-muted-foreground">Loading…</p>
                  ) : (
                    <>
                      <div className="space-y-2">
                        {devInfo?.startup_time && (
                          <Row label="Last init" value={formatDateTime(devInfo.startup_time)} mono />
                        )}
                        {uptimeSecs != null && (
                          <Row label="Uptime" value={formatUptime(uptimeSecs)} mono />
                        )}
                      </div>
                      <div className="border-t border-border pt-3 space-y-2">
                        {devInfo?.python_version   && <Row label="Python"     value={devInfo.python_version} mono />}
                        {devInfo?.fastapi_version     && <Row label="FastAPI"     value={devInfo.fastapi_version} mono />}
                        {devInfo?.sqlalchemy_version  && <Row label="SQLAlchemy"  value={devInfo.sqlalchemy_version} mono />}
                        <Row label="React"       value={REACT_VERSION} mono />
                        {devInfo?.postgres_version && <Row label="PostgreSQL" value={devInfo.postgres_version} mono />}
                        {devInfo?.docker_version   && <Row label="Docker"     value={devInfo.docker_version} mono />}
                      </div>
                    </>
                  )}
                </div>
              </>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-start gap-2">
      <span className="text-muted-foreground w-24 shrink-0">{label}</span>
      <span className={`font-medium ${mono ? "font-mono text-xs leading-5" : ""}`}>{value}</span>
    </div>
  );
}
