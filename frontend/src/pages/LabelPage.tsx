/**
 * LabelPage — the core annotation experience.
 *
 * Layout:
 *   Left:  DICOM image viewer + slice navigation + window controls
 *   Right: Set-level eval → Slice-level eval (gated) → Validation + Submit
 *
 * The annotation session UUID is passed via query param ?session=<uuid>
 * (opened by DashboardPage before navigating here).
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import {
  ChevronLeft,
  ChevronRight,
  ArrowLeft,
  Send,
  SlidersHorizontal,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import SetLevelEvaluation from "@/components/label/SetLevelEvaluation";
import SliceEvaluation from "@/components/label/SliceEvaluation";
import ValidationStatus from "@/components/label/ValidationStatus";
import { imagesApi, imageSetsApi, evaluationsApi, annotationSessionsApi } from "@/lib/api";
import { useLabelStore } from "@/store/labelStore";
import type { ImageRecord, ImageSet } from "@/lib/types";

export default function LabelPage() {
  const { imageSetUuid } = useParams<{ imageSetUuid: string }>();
  const [searchParams] = useSearchParams();
  const sessionUuid = searchParams.get("session");
  const queue = (searchParams.get("queue") ?? "").split(",").filter(Boolean);
  const queueIndex = queue.indexOf(imageSetUuid ?? "");
  const navigate = useNavigate();

  const {
    imageSet,
    images,
    currentIndex,
    windowLevel,
    windowWidth,
    loadImageSet,
    reset,
    setCurrentIndex,
    setWindow,
    aspectsEnabled,
    currentImage,
    isSetSubmittable,
    buildSubmitPayload,
  } = useLabelStore();

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [imgLoading, setImgLoading] = useState(false);
  const [wlInput, setWlInput] = useState(String(windowLevel));
  const [wwInput, setWwInput] = useState(String(windowWidth));
  const [activeTab, setActiveTab] = useState<"eval" | "info">("eval");
  const [navigating, setNavigating] = useState(false);

  // Load image set + images on mount
  useEffect(() => {
    if (!imageSetUuid || !sessionUuid) {
      navigate("/");
      return;
    }

    const load = async () => {
      try {
        const [setRes, imgRes] = await Promise.all([
          imageSetsApi.get(imageSetUuid),
          imagesApi.listByImageSet(imageSetUuid),
        ]);
        const imgSet: ImageSet = setRes.data;
        const imgs: ImageRecord[] = imgRes.data;
        loadImageSet(imgSet, imgs, sessionUuid);
        setWlInput(String(imgSet.image_window_level ?? 35));
        setWwInput(String(imgSet.image_window_width ?? 100));
      } catch {
        toast.error("Failed to load image set");
        navigate("/");
      } finally {
        setLoading(false);
      }
    };
    load();

    return () => reset();
  }, [imageSetUuid, sessionUuid]);

  // Sync WL/WW input with store
  useEffect(() => {
    setWlInput(String(windowLevel));
    setWwInput(String(windowWidth));
  }, [windowLevel, windowWidth]);

  const goToSet = async (targetUuid: string) => {
    setNavigating(true);
    try {
      const res = await annotationSessionsApi.open(targetUuid);
      navigate(`/label/${targetUuid}?session=${res.data.annotation_session_uuid}&queue=${queue.join(",")}`);
    } catch {
      toast.error("Failed to open set");
    } finally {
      setNavigating(false);
    }
  };

  const applyWindow = () => {
    const wl = parseInt(wlInput);
    const ww = parseInt(wwInput);
    if (!isNaN(wl) && !isNaN(ww) && ww > 0) {
      setWindow(wl, ww);
    }
  };

  const handleSubmit = async () => {
    if (!isSetSubmittable()) return;
    setSubmitting(true);
    try {
      const payload = buildSubmitPayload();
      await evaluationsApi.submit(payload);
      toast.success("Annotation submitted successfully!");
      navigate("/");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Submission failed";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const currentImg = currentImage();
  const canSubmit = isSetSubmittable();

  // Image URL with current window settings
  const imageUrl = currentImg
    ? imagesApi.renderUrl(currentImg.uuid, windowLevel, windowWidth)
    : null;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-3rem)] text-muted-foreground">
        Loading image set…
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-3rem)] overflow-hidden">
      {/* ───── Left panel: image viewer ───── */}
      <div className="flex flex-col flex-1 min-w-0 max-w-[680px] bg-black">
        {/* Image area */}
        <div className="flex-1 flex items-center justify-center relative overflow-hidden">
          {imageUrl ? (
            <img
              key={imageUrl}
              src={imageUrl}
              alt={`Slice ${currentIndex + 1}`}
              className="dicom-image max-h-full max-w-full object-contain"
              onLoadStart={() => setImgLoading(true)}
              onLoad={() => setImgLoading(false)}
            />
          ) : (
            <div className="text-muted-foreground text-sm">No image</div>
          )}
          {imgLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/40">
              <span className="text-white text-sm">Loading…</span>
            </div>
          )}

          {/* Slice counter — top left */}
          <div className="absolute top-3 left-3 bg-black/60 rounded px-2 py-1 text-white text-xs font-mono">
            Image {currentIndex + 1} of {images.length}
          </div>
          {/* Slice name — top right */}
          {currentImg?.image_name && (
            <div className="absolute top-3 right-3 bg-black/60 rounded px-2 py-1 text-white text-xs font-mono max-w-[50%] truncate">
              {currentImg.image_name}
            </div>
          )}
        </div>

        {/* Navigation + window controls */}
        <div className="border-t border-border/30 bg-background/80 backdrop-blur px-4 py-2 flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            disabled={currentIndex === 0}
            onClick={() => setCurrentIndex(currentIndex - 1)}
          >
            <ChevronLeft className="h-5 w-5" />
          </Button>
<Button
            variant="ghost"
            size="icon"
            disabled={currentIndex >= images.length - 1}
            onClick={() => setCurrentIndex(currentIndex + 1)}
          >
            <ChevronRight className="h-5 w-5" />
          </Button>

          <Separator orientation="vertical" className="h-5 mx-1" />

          {/* Window controls */}
          <SlidersHorizontal className="h-4 w-4 text-muted-foreground shrink-0" />
          <div className="flex items-center gap-2">
            <Label className="text-xs text-muted-foreground shrink-0">WL</Label>
            <Input
              className="w-20 h-7 text-xs"
              value={wlInput}
              onChange={(e) => setWlInput(e.target.value)}
              onBlur={applyWindow}
              onKeyDown={(e) => e.key === "Enter" && applyWindow()}
            />
            <Label className="text-xs text-muted-foreground shrink-0">WW</Label>
            <Input
              className="w-20 h-7 text-xs"
              value={wwInput}
              onChange={(e) => setWwInput(e.target.value)}
              onBlur={applyWindow}
              onKeyDown={(e) => e.key === "Enter" && applyWindow()}
            />
          </div>

          <div className="ml-auto flex items-center gap-2">
            {queue.length > 1 && (
              <>
                <Separator orientation="vertical" className="h-5" />
                <span className="text-xs text-muted-foreground">
                  Set {queueIndex + 1} of {queue.length}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  disabled={queueIndex <= 0 || navigating}
                  onClick={() => goToSet(queue[queueIndex - 1])}
                  title="Previous set"
                >
                  <ChevronLeft className="h-5 w-5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  disabled={queueIndex >= queue.length - 1 || navigating}
                  onClick={() => goToSet(queue[queueIndex + 1])}
                  title="Next set"
                >
                  <ChevronRight className="h-5 w-5" />
                </Button>
                <Separator orientation="vertical" className="h-5" />
              </>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate("/")}
              className="gap-1.5 text-muted-foreground"
            >
              <ArrowLeft className="h-4 w-4" />
              Exit
            </Button>
          </div>
        </div>
      </div>

      {/* ───── Right panel: evaluation ───── */}
      <div className="w-80 flex flex-col border-l border-border overflow-y-auto bg-background shrink-0">
        <div className="p-4 border-b border-border">
          <h2 className="font-semibold text-sm">{imageSet?.image_set_name}</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {imageSet?.icd_code ?? ""} · {images.length} slices
          </p>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border shrink-0">
          {(["eval", "info"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-2 text-xs font-medium transition-colors ${
                activeTab === tab
                  ? "border-b-2 border-primary text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab === "eval" ? "Evaluation" : "Patient Info"}
            </button>
          ))}
        </div>

        <div className="flex-1 p-4 space-y-5 overflow-y-auto">
          {activeTab === "info" ? (
            <section className="space-y-3 text-sm">
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1 font-medium">ICD Code</div>
                <p className="font-mono">{imageSet?.icd_code ?? "—"}</p>
              </div>
              <Separator />
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1 font-medium">Description / Prognosis</div>
                <p className="text-muted-foreground leading-relaxed whitespace-pre-wrap">{imageSet?.description ?? "—"}</p>
              </div>
              <Separator />
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1 font-medium">Slices</div>
                <p>{images.length}</p>
              </div>
            </section>
          ) : (
            <>
              {/* Set-level evaluation */}
              <section>
                <div className="text-xs uppercase tracking-wide text-muted-foreground mb-3 font-medium">
                  Set Classification
                </div>
                <SetLevelEvaluation />
              </section>

              {/* Slice-level (gated) */}
              {aspectsEnabled() && currentImg && (
                <>
                  <Separator />
                  <section>
                    <div className="text-xs uppercase tracking-wide text-muted-foreground mb-3 font-medium">
                      Slice {currentIndex + 1} Scoring
                    </div>
                    <SliceEvaluation imageUuid={currentImg.uuid} />
                  </section>
                </>
              )}

              <Separator />

              {/* Validation + submit */}
              <section className="space-y-3">
                <ValidationStatus />
                <Button
                  className="w-full gap-2"
                  disabled={!canSubmit || submitting}
                  onClick={handleSubmit}
                >
                  <Send className="h-4 w-4" />
                  {submitting ? "Submitting…" : "Submit Annotation"}
                </Button>
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
