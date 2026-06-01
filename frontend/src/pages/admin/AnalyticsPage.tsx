import { useEffect, useState } from "react";
import { toast } from "sonner";
import { FlaskConical } from "lucide-react";
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { adminApi, datasetsApi } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import type { DataSet } from "@/lib/types";

// ── Types ────────────────────────────────────────────────────────────────────

interface Analytics {
  dataset: { name: string; total_image_sets: number };
  global: {
    annotated_sets: number;
    unannotated_sets: number;
    contributors: { doctor_uuid: string; username: string; full_name: string | null; unique_sets: number }[];
    usability_counts: { IschemicAssessable: number; HemorrhagicPresent: number; Anomaly: number; Irrelevant: number };
  };
  per_doctor: {
    doctor_uuid: string;
    username: string;
    full_name: string | null;
    is_test: boolean;
    annotated_count: number;
    last_annotation: string | null;
    usability_counts: Record<string, number>;
  }[];
}

// ── Chart palette ─────────────────────────────────────────────────────────────

const CONTRIBUTOR_COLORS = [
  "#7287fd", "#89b4fa", "#89dceb", "#a6e3a1", "#f9e2af",
  "#fab387", "#f38ba8", "#cba6f7", "#74c7ec", "#94e2d5",
];

const USABILITY_COLORS: Record<string, string> = {
  IschemicAssessable:  "#89b4fa",   // blue — ASPECTS-applicable
  IschemicLowQuality:  "#74c7ec",   // sky — ischemic but low quality
  HemorrhagicPresent:  "#f38ba8",   // red
  Anomaly:             "#f9e2af",   // yellow
  Irrelevant:          "#cba6f7",   // lavender
};

const USABILITY_LABELS: Record<string, string> = {
  IschemicAssessable:  "Ischemic (ASPECTS)",
  IschemicLowQuality:  "Ischemic (Low Quality)",
  HemorrhagicPresent:  "Hemorrhagic",
  Anomaly:             "Anomaly",
  Irrelevant:          "Irrelevant",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: "medium", timeZone: "Asia/Ho_Chi_Minh" });
}

// Show percentage label; suppress for slices < 4% to avoid clutter
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const pctLabel = (entry: any) =>
  entry.percent > 0.04 ? `${(entry.percent * 100).toFixed(0)}%` : "";

function PieCard({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border bg-card p-4 flex flex-col gap-2">
      <div>
        <p className="text-sm font-semibold">{title}</p>
        {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const [datasets, setDatasets] = useState<DataSet[]>([]);
  const [selectedDataset, setSelectedDataset] = useState("");
  const [data, setData] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    datasetsApi.list(false).then(r => {
      setDatasets(r.data);
      if (r.data.length > 0) setSelectedDataset(r.data[0].dataset_uuid);
    }).catch(() => toast.error("Failed to load datasets"));
  }, []);

  useEffect(() => {
    if (!selectedDataset) return;
    setLoading(true);
    setData(null);
    adminApi.getAnalytics(selectedDataset)
      .then(r => setData(r.data))
      .catch(() => toast.error("Failed to load analytics"))
      .finally(() => setLoading(false));
  }, [selectedDataset]);

  // ── Derived chart data ────────────────────────────────────────────────────

  const completionData = data
    ? [
        { name: "Annotated", value: data.global.annotated_sets },
        { name: "Not yet", value: data.global.unannotated_sets },
      ].filter(d => d.value > 0)
    : [];

  const contributorData = data?.global.contributors.map(c => ({
    name: c.full_name ?? c.username,
    value: c.unique_sets,
  })) ?? [];

  const usabilityData = data
    ? Object.entries(data.global.usability_counts)
        .filter(([, v]) => v > 0)
        .map(([k, v]) => ({ name: USABILITY_LABELS[k] ?? k, key: k, value: v }))
    : [];

  const totalSubmissions = usabilityData.reduce((s, d) => s + d.value, 0);

  return (
    <div className="p-6 space-y-6">
      {/* Header + dataset selector */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Analytics</h1>
          {data && (
            <p className="text-sm text-muted-foreground mt-0.5">
              {data.dataset.name} · {data.dataset.total_image_sets} image sets
            </p>
          )}
        </div>
        <select
          className="h-8 rounded-md border border-input bg-transparent px-3 text-sm"
          value={selectedDataset}
          onChange={e => setSelectedDataset(e.target.value)}
        >
          {datasets.map(d => <option key={d.dataset_uuid} value={d.dataset_uuid}>{d.name}</option>)}
        </select>
      </div>

      {loading && <p className="text-muted-foreground text-sm">Loading…</p>}

      {data && (
        <>
          {/* ── Section A: Global stats (non-test) ── */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-3">
              Global Statistics · non-test accounts only
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

              {/* (a) Completion */}
              <PieCard
                title="Completion"
                subtitle={`${data.global.annotated_sets} of ${data.dataset.total_image_sets} sets annotated`}
              >
                {completionData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                      <Pie data={completionData} cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={3} dataKey="value" label={pctLabel} labelLine={false}>
                        <Cell fill="#a6e3a1" />
                        <Cell fill="#45475a" />
                      </Pie>
                      <Tooltip formatter={(v) => `${v} sets`} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-xs text-muted-foreground py-8 text-center">No data yet</p>
                )}
              </PieCard>

              {/* (b) Contributors */}
              <PieCard
                title="Contributors"
                subtitle="Unique sets annotated per doctor"
              >
                {contributorData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                      <Pie data={contributorData} cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={3} dataKey="value" label={pctLabel} labelLine={false}>
                        {contributorData.map((_, i) => (
                          <Cell key={i} fill={CONTRIBUTOR_COLORS[i % CONTRIBUTOR_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v) => `${v} sets`} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-xs text-muted-foreground py-8 text-center">No annotations yet</p>
                )}
              </PieCard>

              {/* (c) Usability distribution */}
              <PieCard
                title="Usability Distribution"
                subtitle={`${totalSubmissions} evaluations total`}
              >
                {usabilityData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                      <Pie data={usabilityData} cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={3} dataKey="value" label={pctLabel} labelLine={false}>
                        {usabilityData.map((d) => (
                          <Cell key={d.key} fill={USABILITY_COLORS[d.key] ?? "#89b4fa"} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v) => `${v} (${totalSubmissions > 0 ? Math.round(Number(v) / totalSubmissions * 100) : 0}%)`} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-xs text-muted-foreground py-8 text-center">No evaluations yet</p>
                )}
              </PieCard>

            </div>
          </div>

          {/* ── Section B: Per-doctor breakdown (all accounts) ── */}
          {data.per_doctor.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-3">
                Per-Doctor Breakdown · all accounts including test
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {data.per_doctor.map(doc => {
                  const usabilityTotal = Object.values(doc.usability_counts).reduce((s, v) => s + v, 0);
                  return (
                    <div key={doc.doctor_uuid} className="rounded-lg border bg-card p-4 space-y-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="font-medium text-sm truncate">{doc.full_name ?? doc.username}</p>
                          {doc.full_name && <p className="text-xs text-muted-foreground font-mono">{doc.username}</p>}
                        </div>
                        {doc.is_test && (
                          <Badge variant="outline" className="text-purple-500 border-purple-500/50 shrink-0 text-[10px] px-1.5 py-0.5">
                            <FlaskConical className="h-2.5 w-2.5 mr-0.5" />Test
                          </Badge>
                        )}
                      </div>

                      <div className="flex items-baseline gap-1.5">
                        <span className="text-2xl font-bold tabular-nums">{doc.annotated_count}</span>
                        <span className="text-xs text-muted-foreground">sets annotated</span>
                      </div>

                      {/* Usability bar */}
                      {usabilityTotal > 0 && (
                        <div className="space-y-1">
                          <div className="flex h-2 rounded-full overflow-hidden gap-px">
                            {Object.entries(doc.usability_counts).map(([k, v]) =>
                              v > 0 ? (
                                <div
                                  key={k}
                                  style={{ width: `${(v / usabilityTotal) * 100}%`, background: USABILITY_COLORS[k] ?? "#89b4fa" }}
                                  title={`${USABILITY_LABELS[k] ?? k}: ${v}`}
                                />
                              ) : null
                            )}
                          </div>
                          <div className="flex flex-wrap gap-x-2 gap-y-0.5">
                            {Object.entries(doc.usability_counts).map(([k, v]) =>
                              v > 0 ? (
                                <span key={k} className="text-[10px] text-muted-foreground flex items-center gap-0.5">
                                  <span className="h-1.5 w-1.5 rounded-full shrink-0" style={{ background: USABILITY_COLORS[k] ?? "#89b4fa" }} />
                                  {USABILITY_LABELS[k] ?? k} {v}
                                </span>
                              ) : null
                            )}
                          </div>
                        </div>
                      )}

                      {doc.last_annotation && (
                        <p className="text-[10px] text-muted-foreground">Last: {formatDate(doc.last_annotation)}</p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {data.per_doctor.length === 0 && (
            <p className="text-sm text-muted-foreground">No annotations found for this dataset.</p>
          )}
        </>
      )}
    </div>
  );
}
