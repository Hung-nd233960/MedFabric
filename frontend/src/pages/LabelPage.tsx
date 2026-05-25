/**
 * LabelPage — core annotation experience.
 *
 * Left panel : DICOM image viewer (full height, no controls)
 * Right panel: 4 groups + submit + exit
 *   Group 1 — Image navigation & windowing
 *   Group 2 — Per-image ASPECTS scoring (gated)
 *   Group 3 — Image set info & set navigation (queue)
 *   Group 4 — Image set usability / low-quality / notes
 *
 * Keyboard: ← / → navigate images (blocked when focus is on an input).
 */
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { ChevronLeft, ChevronRight, RotateCcw, Send, ArrowLeft } from "lucide-react";
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
  const indices = (searchParams.get("indices") ?? "").split(",").filter(Boolean).map(Number);
  const queuePos = queue.indexOf(imageSetUuid ?? "");
  const navigate = useNavigate();

  const {
    imageSet, images, currentIndex, windowLevel, windowWidth,
    defaultWindowLevel, defaultWindowWidth,
    loadImageSet, reset,
    setCurrentIndex, setWindow, resetWindow,
    aspectsEnabled, currentImage, isSetSubmittable, buildSubmitPayload,
  } = useLabelStore();

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [navigating, setNavigating] = useState(false);
  const [imgLoading, setImgLoading] = useState(false);

  // Local input state (uncontrolled until apply)
  const [wlInput, setWlInput] = useState(String(windowLevel));
  const [wwInput, setWwInput] = useState(String(windowWidth));
  const [jumpImgInput, setJumpImgInput] = useState(String(currentIndex + 1));
  const [jumpSetInput, setJumpSetInput] = useState(String(queuePos + 1));

  // Load image set on mount / set change
  useEffect(() => {
    if (!imageSetUuid || !sessionUuid) { navigate("/"); return; }
    setLoading(true);
    const load = async () => {
      try {
        const [setRes, imgRes] = await Promise.all([
          imageSetsApi.get(imageSetUuid),
          imagesApi.listByImageSet(imageSetUuid),
        ]);
        const imgSet: ImageSet = setRes.data;
        const imgs: ImageRecord[] = imgRes.data;
        loadImageSet(imgSet, imgs, sessionUuid);
      } catch {
        toast.error("Failed to load image set");
        navigate("/");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [imageSetUuid, sessionUuid]);

  // Sync WL/WW inputs from store
  useEffect(() => {
    setWlInput(String(windowLevel));
    setWwInput(String(windowWidth));
  }, [windowLevel, windowWidth]);

  // Sync jump-to-image input
  useEffect(() => {
    setJumpImgInput(String(currentIndex + 1));
  }, [currentIndex]);

  // Sync jump-to-set input
  useEffect(() => {
    setJumpSetInput(String(queuePos + 1));
  }, [queuePos]);

  // Keyboard navigation (← →)
  const inputFocusRef = useRef(false);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.key === "ArrowLeft") setCurrentIndex(Math.max(0, currentIndex - 1));
      if (e.key === "ArrowRight") setCurrentIndex(Math.min(images.length - 1, currentIndex + 1));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [currentIndex, images.length]);
  void inputFocusRef; // suppress unused warning

  const applyWindow = () => {
    const wl = parseInt(wlInput);
    const ww = parseInt(wwInput);
    if (!isNaN(wl) && !isNaN(ww) && ww > 0) setWindow(wl, ww);
  };

  const handleResetWindow = () => {
    resetWindow();
  };

  const applyJumpImage = (val: string) => {
    const n = parseInt(val);
    if (!isNaN(n) && n >= 1 && n <= images.length) setCurrentIndex(n - 1);
    else setJumpImgInput(String(currentIndex + 1));
  };

  const goToSet = async (targetUuid: string) => {
    setNavigating(true);
    try {
      const res = await annotationSessionsApi.open(targetUuid);
      const q = queue.join(",");
      const idx = indices.join(",");
      navigate(`/label/${targetUuid}?session=${res.data.annotation_session_uuid}&queue=${q}&indices=${idx}`);
    } catch {
      toast.error("Failed to open set");
    } finally {
      setNavigating(false);
    }
  };

  const applyJumpSet = (val: string) => {
    const n = parseInt(val);
    if (!isNaN(n) && n >= 1 && n <= queue.length) {
      goToSet(queue[n - 1]);
    } else {
      setJumpSetInput(String(queuePos + 1));
    }
  };

  const handleSubmit = async () => {
    if (!isSetSubmittable()) return;
    setSubmitting(true);
    try {
      await evaluationsApi.submit(buildSubmitPayload());
      toast.success("Annotation submitted!");
      // Auto-advance to next set in queue, or exit
      const nextPos = queuePos + 1;
      if (queue.length > 1 && nextPos < queue.length) {
        await goToSet(queue[nextPos]);
      } else {
        reset();
        navigate("/");
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Submission failed";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleExit = () => {
    reset();
    navigate("/");
  };

  const currentImg = currentImage();
  const canSubmit = isSetSubmittable();
  const imageUrl = currentImg ? imagesApi.renderUrl(currentImg.uuid, windowLevel, windowWidth) : null;
  const datasetIndex = indices[queuePos] ?? null;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-3rem)] text-muted-foreground">
        Loading image set…
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-3rem)] overflow-hidden">
      {/* ── Left: image only ── */}
      <div className="flex-1 min-w-0 max-w-[680px] bg-black relative flex items-center justify-center overflow-hidden">
        {imageUrl ? (
          <img
            key={imageUrl}
            src={imageUrl}
            alt={`Slice ${currentIndex + 1}`}
            className="max-h-full max-w-full object-contain"
            onLoadStart={() => setImgLoading(true)}
            onLoad={() => setImgLoading(false)}
          />
        ) : (
          <span className="text-muted-foreground text-sm">No image</span>
        )}
        {imgLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40">
            <span className="text-white text-sm">Loading…</span>
          </div>
        )}
        {/* Overlays */}
        <div className="absolute top-3 left-3 bg-black/60 rounded px-2 py-1 text-white text-xs font-mono">
          Image {currentIndex + 1} of {images.length}
        </div>
        {currentImg?.image_name && (
          <div className="absolute top-3 right-3 bg-black/60 rounded px-2 py-1 text-white text-xs font-mono max-w-[50%] truncate">
            {currentImg.image_name}
          </div>
        )}
      </div>

      {/* ── Right: annotation panel ── */}
      <div className="w-96 flex flex-col border-l border-border bg-background shrink-0 overflow-hidden">
        <div className="flex-1 overflow-y-auto">

          {/* ═══ IMAGE ANNOTATION ═══ */}
          <div className="p-4 space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              Image Annotation
            </h3>

            {/* Group 1 — Navigation & Controls */}
            <div className="space-y-3">
              {/* Image navigation */}
              <div className="flex items-center gap-2">
                <Button
                  variant="outline" size="icon" className="h-8 w-8 shrink-0"
                  disabled={currentIndex === 0}
                  onClick={() => setCurrentIndex(currentIndex - 1)}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Input
                  type="number"
                  className="h-8 w-16 text-center text-sm"
                  value={jumpImgInput}
                  onChange={(e) => setJumpImgInput(e.target.value)}
                  onBlur={(e) => applyJumpImage(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && applyJumpImage(jumpImgInput)}
                  min={1} max={images.length}
                />
                <span className="text-xs text-muted-foreground shrink-0">of {images.length}</span>
                <Button
                  variant="outline" size="icon" className="h-8 w-8 shrink-0"
                  disabled={currentIndex >= images.length - 1}
                  onClick={() => setCurrentIndex(currentIndex + 1)}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>

              {/* Window controls */}
              <div className="flex items-center gap-2">
                <Label className="text-xs text-muted-foreground shrink-0">WL</Label>
                <Input
                  className="h-7 w-16 text-xs"
                  value={wlInput}
                  onChange={(e) => setWlInput(e.target.value)}
                  onBlur={applyWindow}
                  onKeyDown={(e) => e.key === "Enter" && applyWindow()}
                />
                <Label className="text-xs text-muted-foreground shrink-0">WW</Label>
                <Input
                  className="h-7 w-16 text-xs"
                  value={wwInput}
                  onChange={(e) => setWwInput(e.target.value)}
                  onBlur={applyWindow}
                  onKeyDown={(e) => e.key === "Enter" && applyWindow()}
                />
                <Button
                  variant="outline" size="icon" className="h-7 w-7 shrink-0"
                  onClick={handleResetWindow}
                  title={`Reset to WL ${defaultWindowLevel} / WW ${defaultWindowWidth}`}
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>

            <Separator />

            {/* Group 2 — Image Annotation */}
            <div className="space-y-3">
              <p className="text-xs font-medium text-muted-foreground">Image Annotation</p>
              {!aspectsEnabled() ? (
                <div className="rounded border border-dashed border-muted-foreground/30 px-4 py-6 text-center">
                  <p className="text-xs font-medium text-muted-foreground">
                    ASPECTS scoring is disabled for this image set
                  </p>
                </div>
              ) : currentImg ? (
                <SliceEvaluation imageUuid={currentImg.uuid} />
              ) : (
                <p className="text-xs text-muted-foreground">No image loaded</p>
              )}
            </div>
          </div>

          <Separator />

          {/* ═══ IMAGE SET EVALUATION ═══ */}
          <div className="p-4 space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              Image Set Evaluation
            </h3>

            {/* Group 3 — Set info & navigation */}
            <div className="space-y-3">
              <div className="space-y-1 text-xs">
                {datasetIndex !== null && (
                  <div className="flex gap-2">
                    <span className="text-muted-foreground w-20 shrink-0">Set Index</span>
                    <span className="font-mono">#{datasetIndex}</span>
                  </div>
                )}
                <div className="flex gap-2">
                  <span className="text-muted-foreground w-20 shrink-0">ICD</span>
                  <span className="font-mono">{imageSet?.icd_code ?? "—"}</span>
                </div>
                <div className="flex gap-2">
                  <span className="text-muted-foreground w-20 shrink-0">Slices</span>
                  <span>{images.length}</span>
                </div>
                {imageSet?.description && (
                  <div className="flex gap-2">
                    <span className="text-muted-foreground w-20 shrink-0">Description</span>
                    <span className="leading-relaxed">{imageSet.description}</span>
                  </div>
                )}
              </div>

              {/* Set navigation — only when queue has multiple sets */}
              {queue.length > 1 && (
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline" size="icon" className="h-8 w-8 shrink-0"
                    disabled={queuePos <= 0 || navigating}
                    onClick={() => goToSet(queue[queuePos - 1])}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <Input
                    type="number"
                    className="h-8 w-14 text-center text-sm"
                    value={jumpSetInput}
                    onChange={(e) => setJumpSetInput(e.target.value)}
                    onBlur={(e) => applyJumpSet(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && applyJumpSet(jumpSetInput)}
                    min={1} max={queue.length}
                  />
                  <span className="text-xs text-muted-foreground shrink-0">of {queue.length} sets</span>
                  <Button
                    variant="outline" size="icon" className="h-8 w-8 shrink-0"
                    disabled={queuePos >= queue.length - 1 || navigating}
                    onClick={() => goToSet(queue[queuePos + 1])}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </div>

            <Separator />

            {/* Group 4 — Set annotation */}
            <div className="space-y-3">
              <p className="text-xs font-medium text-muted-foreground">Set Classification</p>
              <SetLevelEvaluation />
            </div>
          </div>

          <Separator />

          {/* Submit + Exit */}
          <div className="p-4 space-y-3">
            <ValidationStatus />
            <Button
              className="w-full gap-2"
              disabled={!canSubmit || submitting || navigating}
              onClick={handleSubmit}
            >
              <Send className="h-4 w-4" />
              {submitting ? "Submitting…" : "Submit Annotation"}
            </Button>
            <Button
              variant="ghost"
              className="w-full gap-2 text-muted-foreground"
              onClick={handleExit}
            >
              <ArrowLeft className="h-4 w-4" />
              Exit to Dashboard
            </Button>
          </div>

        </div>
      </div>
    </div>
  );
}
