import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Stethoscope, CheckCircle2, Globe, Layers } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { dashboardApi, imageSetsApi, annotationSessionsApi } from "@/lib/api";
import type { DashboardStats, ImageSetWithProgress } from "@/lib/types";

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: React.ElementType;
  label: string;
  value: number;
  sub?: string;
}) {
  return (
    <Card>
      <CardHeader className="pb-2 flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
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
  const [starting, setStarting] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [statsRes] = await Promise.all([dashboardApi.stats()]);
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

  const handleAnnotate = async (imageSetUuid: string) => {
    setStarting(imageSetUuid);
    try {
      const res = await annotationSessionsApi.open(imageSetUuid);
      navigate(`/label/${imageSetUuid}?session=${res.data.annotation_session_uuid}`);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to start annotation";
      toast.error(msg);
    } finally {
      setStarting(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        Loading…
      </div>
    );
  }

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
          <StatCard
            icon={Layers}
            label="Total Image Sets"
            value={stats.total_image_sets}
          />
          <StatCard
            icon={Stethoscope}
            label="My Progress"
            value={stats.my_progress}
            sub="sets evaluated by you"
          />
          <StatCard
            icon={Globe}
            label="Global Progress"
            value={stats.global_progress}
            sub="unique sets with ≥1 evaluation"
          />
          <StatCard
            icon={CheckCircle2}
            label="Remaining"
            value={Math.max(0, stats.total_image_sets - stats.my_progress)}
            sub="sets you haven't evaluated"
          />
        </div>
      )}

      {/* Image set table */}
      {stats?.assigned_dataset && (
        <div>
          <h2 className="text-lg font-medium mb-3">Image Sets</h2>
          {imageSets.length === 0 ? (
            <p className="text-muted-foreground text-sm">No image sets found in this dataset.</p>
          ) : (
            <div className="rounded-lg border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium">Name</th>
                    <th className="text-left px-4 py-3 font-medium">ICD</th>
                    <th className="text-left px-4 py-3 font-medium">Slices</th>
                    <th className="text-left px-4 py-3 font-medium">Evaluators</th>
                    <th className="text-left px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {imageSets.map((s) => (
                    <tr key={s.uuid} className="hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-3 font-medium">{s.image_set_name}</td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {s.icd_code ?? "—"}
                      </td>
                      <td className="px-4 py-3">{s.num_images}</td>
                      <td className="px-4 py-3">{s.total_evaluators}</td>
                      <td className="px-4 py-3">
                        {s.evaluated_by_me ? (
                          <Badge variant="success">Done</Badge>
                        ) : (
                          <Badge variant="outline">Pending</Badge>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Button
                          size="sm"
                          variant={s.evaluated_by_me ? "secondary" : "default"}
                          disabled={starting === s.uuid}
                          onClick={() => handleAnnotate(s.uuid)}
                        >
                          {starting === s.uuid
                            ? "Starting…"
                            : s.evaluated_by_me
                            ? "Re-annotate"
                            : "Annotate"}
                        </Button>
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
