import { useState } from "react";
import { Bug, Lightbulb, Send, CheckCircle2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { bugReportApi } from "@/lib/api";
import { useLabelQueueStore } from "@/store/labelQueueStore";
import { useLabelStore } from "@/store/labelStore";
import { useLocation } from "react-router-dom";

type ReportType = "bug" | "feature";

export default function BugReportDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const [type, setType] = useState<ReportType>("bug");
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const { pathname } = useLocation();
  const { queue, currentPos, sessionUuid } = useLabelQueueStore();
  const currentIndex = useLabelStore((s) => s.currentIndex);
  const imageSet = useLabelStore((s) => s.imageSet);

  const handleSubmit = async () => {
    if (!text.trim()) return;
    setSubmitting(true);
    try {
      const imageSetUuid = queue[currentPos] ?? null;
      await bugReportApi.submit({
        type,
        text: text.trim(),
        page: pathname,
        context: {
          annotation_session_uuid: sessionUuid ?? null,
          image_set_uuid: imageSetUuid ?? null,
          image_set_name: imageSet?.image_set_name ?? null,
          image_index: imageSetUuid ? currentIndex : null,
        },
      });
      setDone(true);
    } catch {
      // still show success — don't burden the doctor with network errors
      setDone(true);
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = (v: boolean) => {
    onOpenChange(v);
    if (!v) {
      setTimeout(() => { setText(""); setDone(false); setType("bug"); }, 300);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Send Feedback</DialogTitle>
        </DialogHeader>

        {done ? (
          <div className="flex flex-col items-center gap-3 py-6 text-center">
            <CheckCircle2 className="h-10 w-10 text-green-500" />
            <p className="text-base font-medium">Thank you for your feedback!</p>
            <p className="text-sm text-muted-foreground">Your report helps improve MedFabric.</p>
            <Button className="mt-2" onClick={() => handleClose(false)}>Close</Button>
          </div>
        ) : (
          <div className="space-y-4 pt-1">
            {/* Type toggle */}
            <div className="flex rounded-lg border border-border p-0.5 gap-0.5">
              {([
                { value: "bug" as const, label: "Bug Report", icon: Bug },
                { value: "feature" as const, label: "Feature Request", icon: Lightbulb },
              ]).map(({ value, label, icon: Icon }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setType(value)}
                  className={cn(
                    "flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors",
                    type === value
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </button>
              ))}
            </div>

            {/* Text area */}
            <Textarea
              placeholder={
                type === "bug"
                  ? "Describe what happened and how to reproduce it…"
                  : "Describe the feature you'd like to see…"
              }
              rows={5}
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="resize-none text-base"
              autoFocus
            />

            <Button
              className="w-full gap-2"
              disabled={!text.trim() || submitting}
              onClick={handleSubmit}
            >
              <Send className="h-4 w-4" />
              {submitting ? "Sending…" : "Submit"}
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
