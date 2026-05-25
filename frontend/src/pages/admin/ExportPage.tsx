import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { datasetsApi, exportApi } from "@/lib/api";
import type { DataSet } from "@/lib/types";
import { useAuthStore } from "@/store/authStore";

export default function ExportPage() {
  const [datasets, setDatasets] = useState<DataSet[]>([]);
  const [selectedDataset, setSelectedDataset] = useState("all");
  const [format, setFormat] = useState<"xlsx" | "csv">("xlsx");
  const token = useAuthStore(s => s.accessToken);

  useEffect(() => {
    datasetsApi.list(false).then(r => setDatasets(r.data)).catch(() => toast.error("Failed to load datasets"));
  }, []);

  const handleDownload = () => {
    const datasetUuid = selectedDataset === "all" ? undefined : selectedDataset;
    const url = exportApi.download(format, datasetUuid);

    // Create a temporary link with auth header workaround:
    // We need to pass the token. The simplest approach for a download
    // is to use fetch + blob URL.
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then(async res => {
        if (!res.ok) throw new Error("Download failed");
        const blob = await res.blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `medfabric_annotations.${format}`;
        a.click();
        URL.revokeObjectURL(a.href);
      })
      .catch(() => toast.error("Export failed"));
  };

  return (
    <div className="p-6 max-w-lg space-y-4">
      <h1 className="text-xl font-semibold">Export Annotations</h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Download annotation data</CardTitle>
          <CardDescription>
            Exports all submitted annotations including set-level usability and per-slice ASPECTS
            scores in one flat table.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label>Dataset</Label>
            <select
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
              value={selectedDataset}
              onChange={e => setSelectedDataset(e.target.value)}
            >
              <option value="all">All datasets</option>
              {datasets.map(d => (
                <option key={d.dataset_uuid} value={d.dataset_uuid}>{d.name}</option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <Label>Format</Label>
            <div className="flex gap-3">
              {(["xlsx", "csv"] as const).map(f => (
                <label key={f} className="flex items-center gap-2 cursor-pointer text-sm">
                  <input
                    type="radio"
                    value={f}
                    checked={format === f}
                    onChange={() => setFormat(f)}
                  />
                  {f.toUpperCase()}
                </label>
              ))}
            </div>
          </div>

          <Button className="w-full gap-2" onClick={handleDownload}>
            <Download className="h-4 w-4" />
            Download {format.toUpperCase()}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
