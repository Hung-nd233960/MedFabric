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
import { useEffect, useRef, useState } from "react";
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
import { imagesApi, imageSetsApi, evaluationsApi } from "@/lib/api";
import { useLabelStore } from "@/store/labelStore";
import type { ImageRecord, ImageSet } from "@/lib/types";
import { useAuthStore } from "@/store/authStore";

function buildImageUrl(
  imageUuid: string,
  token: string | null,
  wl: number,
  ww: number
): string {
  const base = imagesApi.renderUrl(imageUuid, wl, ww);
  // Token auth: pass as header via the proxy — but since <img> can't set headers,
  // we use the access token in a query param here. Backend needs to support this
  // or we use a blob URL pattern instead.
  // For now, the proxy forwards /api/* and the interceptor adds the header on
  // XHR requests. For <img> src we'll just omit auth and rely on session cookie
  // (or implement a fetch+objectURL approach later).
  return base;
}

export default function LabelPage() {
  const { imageSetUuid } = useParams<{ imageSetUuid: string }>();
  const [searchParams] = useSearchParams();
  const sessionUuid = searchParams.get("session");
  const navigate = useNavigate();
  const token = useAuthStore((s) => s.accessToken);

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
      <div className="flex flex-col flex-1 min-w-0 bg-black">
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

          {/* Slice index overlay */}
          <div className="absolute top-3 left-3 bg-black/60 rounded px-2 py-1 text-white text-xs font-mono">
            {currentIndex + 1} / {images.length}
          </div>
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
          <span className="text-sm text-muted-foreground w-20 text-center">
            {currentImg?.image_name ?? "—"}
          </span>
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

          <div className="ml-auto">
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

        <div className="flex-1 p-4 space-y-5">
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
        </div>
      </div>
    </div>
  );
}
