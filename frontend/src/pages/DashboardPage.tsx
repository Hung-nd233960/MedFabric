import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Stethoscope, CheckCircle2, Globe, Layers, PlayCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { dashboardApi, imageSetsApi, annotationSessionsApi } from "@/lib/api";
import type { DashboardStats, ImageSetWithProgress } from "@/lib/types";

function StatCard({
  icon: Icon,
  label,
  value,
  pct,
  sub,
}: {
  icon: React.ElementType;
  label: string;
  value: number;
  pct?: number;
  sub?: string;
}) {
  return (
    <Card>
      <CardHeader className="pb-2 flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-2">
          <div className="text-2xl font-bold">{value}</div>
          {pct !== undefined && (
            <div className="text-sm font-medium text-muted-foreground">{pct}%</div>
          )}
        </div>
        {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [imageSets, setImageSets] = useState<ImageSetWithProgress[]>([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  useEffect(() => {
    const load = async () => {
      try {
        const statsRes = await dashboardApi.stats();
        const s: DashboardStats = statsRes.data;
        setStats(s);
        if (s.assigned_dataset) {
          const setsRes = await imageSetsApi.listByDataset(s.assigned_dataset.dataset_uuid);
          setImageSets(setsRes.data);
        }
      } catch {
        toast.error("Failed to load dashboard");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const toggleSelect = (uuid: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(uuid)) next.delete(uuid);
      else next.add(uuid);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === imageSets.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(imageSets.map((s) => s.uuid)));
    }
  };

  const handleAnnotateSelected = async () => {
    const selectedSets = imageSets.filter((s) => selected.has(s.uuid));
    const target = selectedSets.find((s) => !s.evaluated_by_me) ?? selectedSets[0];
    if (!target) return;

    setStarting(true);
    try {
      const res = await annotationSessionsApi.open(target.uuid);
      navigate(`/label/${target.uuid}?session=${res.data.annotation_session_uuid}`);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to start annotation";
      toast.error(msg);
    } finally {
      setStarting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        Loading…
      </div>
    );
  }

  const selectedSets = imageSets.filter((s) => selected.has(s.uuid));
  const selectedIndices = [...selectedSets]
    .sort((a, b) => a.dataset_index - b.dataset_index)
    .map((s) => s.dataset_index);

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        {stats?.assigned_dataset ? (
          <p className="text-muted-foreground text-sm mt-1">
            Assigned dataset:{" "}
            <span className="text-foreground font-medium">{stats.assigned_dataset.name}</span>
          </p>
        ) : (
          <p className="text-muted-foreground text-sm mt-1">
            No dataset assigned — contact an admin.
          </p>
        )}
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard icon={Layers} label="Total Image Sets" value={stats.total_image_sets} />
          <StatCard
            icon={Stethoscope}
            label="My Progress"
            value={stats.my_progress}
            pct={stats.total_image_sets > 0 ? Math.round(stats.my_progress / stats.total_image_sets * 100) : 0}
            sub="sets evaluated by you"
          />
          <StatCard
            icon={Globe}
            label="Global Progress"
            value={stats.global_progress}
            pct={stats.total_image_sets > 0 ? Math.round(stats.global_progress / stats.total_image_sets * 100) : 0}
            sub="unique sets with ≥1 evaluation"
          />
          <StatCard icon={CheckCircle2} label="Remaining" value={Math.max(0, stats.total_image_sets - stats.my_progress)} sub="sets you haven't evaluated" />
        </div>
      )}

      {/* Image set table */}
      {stats?.assigned_dataset && (
        <div className="space-y-3">
          <h2 className="text-lg font-medium">Image Sets</h2>

          {/* Selection box */}
          <div className={`rounded-lg border px-4 py-3 text-sm flex items-center justify-between gap-4 transition-colors ${
            selected.size > 0 ? "border-primary bg-primary/5" : "border-border bg-muted/30"
          }`}>
            {selected.size === 0 ? (
              <span className="text-muted-foreground">Please choose image sets to annotate</span>
            ) : (
              <>
                <span>
                  You have chosen sets:{" "}
                  <span className="font-mono font-medium">{selectedIndices.join(", ")}</span>
                </span>
                <Button
                  size="sm"
                  className="gap-1.5 shrink-0"
                  disabled={starting}
                  onClick={handleAnnotateSelected}
                >
                  <PlayCircle className="h-4 w-4" />
                  {starting ? "Starting…" : "Annotate"}
                </Button>
              </>
            )}
          </div>

          {imageSets.length === 0 ? (
            <p className="text-muted-foreground text-sm">No image sets found in this dataset.</p>
          ) : (
            <div className="rounded-lg border overflow-hidden">
              <table className="w-full text-sm table-fixed">
                <colgroup>
                  <col className="w-[10%]" />
                  <col className="w-[25%]" />
                  <col className="w-[25%]" />
                  <col className="w-[10%]" />
                  <col className="w-[5%]" />
                  <col className="w-[5%]" />
                  <col className="w-[10%]" />
                  <col className="w-[10%]" />
                </colgroup>
                <thead className="bg-muted/50">
                  <tr>
                    {["Index", "Image Set Name", "Patient ID", "ICD", "Slices", "Evaluators", "Status"].map((h) => (
                      <th key={h} className="text-left px-3 py-3 font-medium truncate">{h}</th>
                    ))}
                    <th className="px-3 py-3 text-right font-medium">
                      <input
                        type="checkbox"
                        checked={selected.size === imageSets.length && imageSets.length > 0}
                        onChange={toggleAll}
                        className="rounded cursor-pointer"
                      />
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {imageSets.map((s) => (
                    <tr
                      key={s.uuid}
                      className={`transition-colors cursor-pointer ${
                        selected.has(s.uuid) ? "bg-primary/5" : "hover:bg-muted/30"
                      }`}
                      onClick={() => toggleSelect(s.uuid)}
                    >
                      <td className="px-3 py-3 font-mono text-muted-foreground overflow-hidden"><span className="block truncate">{s.dataset_index}</span></td>
                      <td className="px-3 py-3 font-medium overflow-hidden"><span className="block truncate" title={s.image_set_name}>{s.image_set_name}</span></td>
                      <td className="px-3 py-3 text-muted-foreground overflow-hidden"><span className="block truncate font-mono text-xs" title={s.patient_id ?? ""}>{s.patient_id ?? "—"}</span></td>
                      <td className="px-3 py-3 text-muted-foreground overflow-hidden"><span className="block truncate" title={s.icd_code ?? ""}>{s.icd_code ?? "—"}</span></td>
                      <td className="px-3 py-3 overflow-hidden"><span className="block truncate">{s.num_images}</span></td>
                      <td className="px-3 py-3 overflow-hidden"><span className="block truncate">{s.total_evaluators}</span></td>
                      <td className="px-3 py-3 overflow-hidden">
                        {s.evaluated_by_me ? (
                          <Badge variant="success">Done</Badge>
                        ) : (
                          <Badge variant="outline">Pending</Badge>
                        )}
                      </td>
                      <td className="px-3 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selected.has(s.uuid)}
                          onChange={() => toggleSelect(s.uuid)}
                          className="rounded cursor-pointer"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
