/**
 * LabelPage — core annotation experience.
 *
 * Left   (40%): DICOM image viewer
 * Middle (30%): Per-image annotation (navigation, windowing, ASPECTS)
 * Right  (30%): Image set evaluation (info, set nav, usability, submit)
 *
 * Keyboard: ← / → navigate images (blocked when focus is on an input).
 */
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ChevronLeft, ChevronRight, RotateCcw, Send, ArrowLeft, Trash2, Save, X, ClipboardList, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { WithTooltip } from "@/components/ui/tooltip";
import SetLevelEvaluation from "@/components/label/SetLevelEvaluation";
import SliceEvaluation from "@/components/label/SliceEvaluation";
import ValidationStatus from "@/components/label/ValidationStatus";
import { imagesApi, imageSetsApi, evaluationsApi, annotationSessionsApi, authApi, adminApi } from "@/lib/api";
import { useLabelStore, buildSnapshotFromPayload } from "@/store/labelStore";
import { useLabelQueueStore } from "@/store/labelQueueStore";
import { useAuthStore } from "@/store/authStore";
import { useNavGuardStore } from "@/store/navGuardStore";
import type { ImageRecord, ImageSet, SliceEvalState, ImageSetUsability } from "@/lib/types";
import { USABILITY_LABELS, BASAL_ZONES, CORONA_ZONES } from "@/lib/types";

/** Tailwind classes that hide the browser number-input spinner arrows */
const NO_SPINNER =
  "[appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none";

// Module-level helpers for Management Board (no closure needed)
function mbSliceValid(slice: SliceEvalState): boolean {
  if (slice.region === "None") return true;
  const zones = slice.region === "BasalGanglia" ? BASAL_ZONES : CORONA_ZONES;
  return zones.every(z => slice.scores[`${z}_left_score`] !== null && slice.scores[`${z}_right_score`] !== null);
}

function getMissingZones(slice: SliceEvalState): string | null {
  if (slice.region === "None") return null;
  const zones = slice.region === "BasalGanglia" ? BASAL_ZONES : CORONA_ZONES;
  const ml = [...zones].filter(z => !slice.scores[`${z}_left_score`]).map(z => z.toUpperCase());
  const mr = [...zones].filter(z => !slice.scores[`${z}_right_score`]).map(z => z.toUpperCase());
  if (!ml.length && !mr.length) return null;
  const parts: string[] = [];
  if (ml.length) parts.push(`Left: ${ml.join(", ")}`);
  if (mr.length) parts.push(`Right: ${mr.join(", ")}`);
  return "Missing: " + parts.join("; ");
}

export default function LabelPage() {
  const {
    queue, currentPos: queuePos, indices, sources,
    sessionUuid, adminDoctors, isReadMode, isPreviewMode,
    setCurrentPos, setSessionUuid, clear: clearQueue,
  } = useLabelQueueStore();
  const imageSetUuid = queue[queuePos] ?? null;
  const currentSource = sources[queuePos] ?? "submission";
  const currentAdminDoctor = adminDoctors[queuePos] ?? null;
  const isAdminRead = adminDoctors.length > 0;
  const navigate = useNavigate();

  const {
    imageSet, images, currentIndex, windowLevel, windowWidth,
    defaultWindowLevel, defaultWindowWidth, setRegistry, lowQuality, setNotes, slices,
    loadImageSet, reset, setMode, preloadRegistry,
    setCurrentIndex, setWindow, resetWindow,
    aspectsEnabled, usability, currentImage,
    isSetSubmittable, isSetSubmittableByUuid, buildSubmitPayload, buildSubmitPayloadForUuid,
    setAutoSaveStatus, setUsability, setLowQuality, setRegion,
  } = useLabelStore();

  const { logout } = useAuthStore();

  const hasAnyAnnotation =
    usability !== null ||
    lowQuality ||
    setNotes.trim() !== "" ||
    (Object.values(slices) as SliceEvalState[]).some(s => s.region !== "None" || s.notes.trim() !== "");

  const [loading, setLoading] = useState(true);
  const [showOverlay, setShowOverlay] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [savingDraft, setSavingDraft] = useState(false);
  const autoSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const initialLoadDone = useRef(false);
  const draftToastShown = useRef(false);
  const [navigating, setNavigating] = useState(false);
  const [imgLoading, setImgLoading] = useState(false);
  const [submitDialogMode, setSubmitDialogMode] = useState<"all-ready" | "partial-ready" | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);
  const [confirmExit, setConfirmExit] = useState(false);
  const [pendingNavDest, setPendingNavDest] = useState<string | null>(null);
  const [showManagementBoard, setShowManagementBoard] = useState(false);
  const [selectedBoardSetUuid, setSelectedBoardSetUuid] = useState<string | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [rightTab, setRightTab] = useState<"set-info" | "patient-info" | "annotation-info">("set-info");
  const [annotationMeta, setAnnotationMeta] = useState<{
    type: "submission" | "draft";
    doctorUsername: string | null;
    doctorFullName: string | null;
    timestamp: string | null;
  } | null>(null);

  // Local input state (uncontrolled until apply)
  const [wlInput, setWlInput] = useState(String(windowLevel));
  const [wwInput, setWwInput] = useState(String(windowWidth));
  const [jumpImgInput, setJumpImgInput] = useState(String(currentIndex + 1));
  const [jumpSetInput, setJumpSetInput] = useState(String(queuePos + 1));

  const currentImg = currentImage();

  // Redirect if queue is empty (e.g. page refresh)
  useEffect(() => {
    if (queue.length === 0) navigate("/", { replace: true });
  }, [queue.length]); // eslint-disable-line react-hooks/exhaustive-deps

  // Load image set on mount / set change
  useEffect(() => {
    if (!imageSetUuid) return;
    if (!isReadMode && !isPreviewMode && !sessionUuid) { navigate("/", { replace: true }); return; }
    setMode(isReadMode ? "read" : isPreviewMode ? "preview" : "annotate");
    setRightTab("set-info");
    setAnnotationMeta(null);
    setLoading(true);
    initialLoadDone.current = false;
    setAutoSaveStatus("idle");
    if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current);
    const load = async () => {
      try {
        const [setRes, imgRes] = await Promise.all([
          imageSetsApi.get(imageSetUuid),
          imagesApi.listByImageSet(imageSetUuid),
        ]);
        const imgSet: ImageSet = setRes.data;
        const imgs: ImageRecord[] = imgRes.data;
        loadImageSet(imgSet, imgs, sessionUuid ?? "");

        if (isReadMode) {
          // Load submission or draft data to restore into store
          try {
            const { restoreDraft } = useLabelStore.getState();
            if (currentSource === "draft") {
              const draftRes = await evaluationsApi.getDraftByImageSet(imageSetUuid);
              const d = draftRes.data;
              if (d.payload) restoreDraft(d.payload);
              setAnnotationMeta({
                type: "draft",
                doctorUsername: d.doctor_username ?? null,
                doctorFullName: d.doctor_full_name ?? null,
                timestamp: d.draft_saved_at ?? null,
              });
            } else {
              const subRes = currentAdminDoctor
                ? await adminApi.getSubmissionByImageSetAdmin(imageSetUuid, currentAdminDoctor)
                : await evaluationsApi.getSubmissionByImageSet(imageSetUuid);
              const d = subRes.data;
              if (d.payload) restoreDraft(d.payload);
              setAnnotationMeta({
                type: "submission",
                doctorUsername: d.doctor_username ?? null,
                doctorFullName: d.doctor_full_name ?? null,
                timestamp: d.draft_saved_at ?? null,
              });
            }
          } catch {
            setAnnotationMeta(null);
          }
        } else if (!isPreviewMode) {
          // Annotate mode: restore server-side draft if one exists
          try {
            const draftRes = await evaluationsApi.getDraftByImageSet(imageSetUuid);
            const p = draftRes.data.payload;
            if (p) {
              const { restoreDraft } = useLabelStore.getState();
              restoreDraft(p);
              if (!draftToastShown.current) {
                toast.info("Draft restored.");
                draftToastShown.current = true;
              }
            }
          } catch {
            // No draft — normal fresh load
          }
        }
      } catch {
        toast.error("Failed to load image set");
        navigate("/");
      } finally {
        setLoading(false);
        if (!isReadMode && !isPreviewMode) initialLoadDone.current = true;
      }
    };
    load();
  }, [imageSetUuid, sessionUuid, isReadMode, currentSource, currentAdminDoctor]);

  // Delay overlay by 500 ms — fast loads show nothing, slow loads get the blur treatment
  useEffect(() => {
    if (!loading) { setShowOverlay(false); return; }
    const t = setTimeout(() => setShowOverlay(true), 500);
    return () => clearTimeout(t);
  }, [loading]);

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

  // Keyboard navigation — image (← →, no shift)
  const jumpImgInputRef = useRef<HTMLInputElement>(null);
  const inputFocusRef = useRef(false);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.shiftKey) return; // Shift+← / Shift+→ are handled in the comprehensive handler
      if (e.key === "ArrowLeft") setCurrentIndex((currentIndex - 1 + images.length) % images.length);
      if (e.key === "ArrowRight") setCurrentIndex((currentIndex + 1) % images.length);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [currentIndex, images.length]);
  void inputFocusRef;

  // Auto-save draft while in annotate mode — debounced 2.5 s after last change
  useEffect(() => {
    if (isReadMode || !sessionUuid || !initialLoadDone.current) return;
    setAutoSaveStatus("pending");
    if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current);
    autoSaveTimer.current = setTimeout(async () => {
      setAutoSaveStatus("saving");
      try {
        await evaluationsApi.saveAutoDraft(useLabelStore.getState().buildSubmitPayload());
        setAutoSaveStatus("saved");
        // Revert to idle after 3 s, but only if nothing changed in the meantime
        setTimeout(() => { if (useLabelStore.getState().autoSaveStatus === "saved") setAutoSaveStatus("idle"); }, 3000);
      } catch {
        setAutoSaveStatus("idle");
      }
    }, 2500);
    return () => { if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [usability, lowQuality, setNotes, slices]);

  // Register navbar navigation interceptor while on this page (skip in read/preview mode)
  useEffect(() => {
    if (isReadMode || isPreviewMode) return;
    useNavGuardStore.getState().setInterceptor((dest: string) => {
      const st = useLabelStore.getState();
      const dirty =
        st.usability !== null ||
        st.lowQuality ||
        st.setNotes.trim() !== "" ||
        (Object.values(st.slices) as SliceEvalState[]).some(s => s.region !== "None" || s.notes.trim() !== "");
      if (!dirty) { st.reset(); useLabelQueueStore.getState().clear(); navigate(dest); return; }
      setPendingNavDest(dest);
      setConfirmExit(true);
    });
    return () => { useNavGuardStore.getState().setInterceptor(null); };
  }, [isReadMode, isPreviewMode]);

  // In reader mode: preload all other queue sets into setRegistry so the Management Board
  // can show their status without requiring navigation to each set first.
  useEffect(() => {
    if (!isReadMode || queue.length <= 1) return;
    let cancelled = false;
    const otherIndices = queue
      .map((uuid: string, i: number) => ({ uuid, i }))
      .filter(({ uuid }: { uuid: string; i: number }) => uuid !== imageSetUuid);

    Promise.all(
      otherIndices.map(async ({ uuid, i }: { uuid: string; i: number }) => {
        try {
          const [imgRes, annRes] = await Promise.all([
            imagesApi.listByImageSet(uuid),
            sources[i] === "draft"
              ? evaluationsApi.getDraftByImageSet(uuid)
              : adminDoctors[i]
                ? adminApi.getSubmissionByImageSetAdmin(uuid, adminDoctors[i])
                : evaluationsApi.getSubmissionByImageSet(uuid),
          ]);
          const imgs: ImageRecord[] = imgRes.data;
          const payload = annRes.data?.payload;
          if (!payload) return null;
          return { uuid, snapshot: buildSnapshotFromPayload(payload, imgs) };
        } catch {
          return null;
        }
      })
    ).then((results) => {
      if (cancelled) return;
      const entries: Record<string, ReturnType<typeof buildSnapshotFromPayload>> = {};
      for (const r of results) {
        if (r) entries[r.uuid] = r.snapshot;
      }
      if (Object.keys(entries).length > 0) preloadRegistry(entries);
    });

    return () => { cancelled = true; };
  }, [isReadMode, imageSetUuid]);

  useEffect(() => {
    if (!currentImg) { setBlobUrl(null); return; }
    let cancelled = false;
    setImgLoading(true);
    imagesApi.renderBlob(currentImg.uuid, windowLevel, windowWidth)
      .then((res: { data: Blob }) => {
        if (cancelled) return;
        const url = URL.createObjectURL(res.data);
        setBlobUrl((prev: string | null) => { if (prev) URL.revokeObjectURL(prev); return url; });
        setImgLoading(false);
      })
      .catch(() => { if (!cancelled) { setBlobUrl(null); setImgLoading(false); } });
    return () => { cancelled = true; };
  }, [currentImg?.uuid, windowLevel, windowWidth]);

  const applyWindow = () => {
    const wl = parseInt(wlInput);
    const ww = parseInt(wwInput);
    if (!isNaN(wl) && !isNaN(ww) && ww > 0) setWindow(wl, ww);
  };

  const handleResetWindow = () => resetWindow();

  const applyJumpImage = (val: string) => {
    const n = parseInt(val);
    if (!isNaN(n) && n >= 1 && n <= images.length) setCurrentIndex(n - 1);
    else setJumpImgInput(String(currentIndex + 1));
  };

  const goToSet = async (targetUuid: string) => {
    const targetPos = queue.indexOf(targetUuid);
    if (targetPos === -1) return;
    if (isReadMode || isPreviewMode) {
      setCurrentPos(targetPos);
      return;
    }
    setNavigating(true);
    try {
      const res = await annotationSessionsApi.open(targetUuid);
      setSessionUuid(res.data.annotation_session_uuid);
      setCurrentPos(targetPos);
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

  type BatchAction = "submit-all" | "draft-all" | "submit-ready-draft-incomplete" | "submit-ready-drop-incomplete";

  const handleBatchAction = async (action: BatchAction) => {
    setSubmitDialogMode(null);
    setSubmitting(true);
    const getSessionUuid = async (uuid: string) => {
      if (uuid === imageSetUuid) return sessionUuid!;
      const res = await annotationSessionsApi.open(uuid);
      return res.data.annotation_session_uuid;
    };
    const isVisited = (uuid: string) => {
      const { imageSet: cur, setRegistry: reg } = useLabelStore.getState();
      return cur?.uuid === uuid || uuid in reg;
    };
    const toSubmit: string[] = [];
    const toDraft: string[] = [];
    for (const uuid of queue) {
      if (!isVisited(uuid)) continue;
      const ready = isSetSubmittableByUuid(uuid);
      if (action === "submit-all") toSubmit.push(uuid);
      else if (action === "draft-all") toDraft.push(uuid);
      else if (action === "submit-ready-draft-incomplete") { if (ready) toSubmit.push(uuid); else toDraft.push(uuid); }
      else if (action === "submit-ready-drop-incomplete") { if (ready) toSubmit.push(uuid); }
    }
    try {
      for (const uuid of toSubmit) {
        const sessUuid = await getSessionUuid(uuid);
        await evaluationsApi.submit(buildSubmitPayloadForUuid(uuid, sessUuid));
      }
      for (const uuid of toDraft) {
        const sessUuid = await getSessionUuid(uuid);
        await evaluationsApi.saveDraft(buildSubmitPayloadForUuid(uuid, sessUuid));
      }
      const parts = [toSubmit.length && `${toSubmit.length} submitted`, toDraft.length && `${toDraft.length} drafted`].filter(Boolean);
      toast.success(parts.join(", ") || "Done.");
      reset();
      clearQueue();
      navigate("/");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Action failed";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSaveDraft = async () => {
    if (!sessionUuid) return;
    setSavingDraft(true);
    try {
      await evaluationsApi.saveDraft(buildSubmitPayload());
      toast.success("Draft saved.");
    } catch {
      toast.error("Failed to save draft.");
    } finally {
      setSavingDraft(false);
    }
  };

  // Comprehensive keyboard shortcuts (placed after all handlers are defined)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;

      const key = e.key;
      const shift = e.shiftKey;
      const ctrl = e.ctrlKey || e.metaKey;
      const UP = key.toUpperCase();

      // Shift+← / Shift+→ — queue navigation (all modes)
      if (shift && !ctrl && key === "ArrowLeft") {
        e.preventDefault();
        if (queuePos > 0) goToSet(queue[queuePos - 1]);
        return;
      }
      if (shift && !ctrl && key === "ArrowRight") {
        e.preventDefault();
        if (queuePos < queue.length - 1) goToSet(queue[queuePos + 1]);
        return;
      }

      // M — toggle Management Board (all modes)
      if (!ctrl && !shift && UP === "M") {
        setShowManagementBoard((v) => !v);
        return;
      }

      // Esc — close Management Board or dismiss open dialogs (all modes)
      if (key === "Escape") {
        if (submitDialogMode !== null) { setSubmitDialogMode(null); return; }
        if (confirmReset) { setConfirmReset(false); return; }
        if (confirmExit) { setConfirmExit(false); setPendingNavDest(null); return; }
        if (showManagementBoard) { setShowManagementBoard(false); return; }
        return;
      }

      // Ctrl+S — save draft (annotate mode only)
      if (ctrl && UP === "S" && !isReadMode && !isPreviewMode) {
        e.preventDefault();
        handleSaveDraft();
        return;
      }

      // Ctrl+Enter — submit (annotate mode, only when valid)
      if (ctrl && key === "Enter" && !isReadMode && !isPreviewMode) {
        e.preventDefault();
        const { isSetSubmittable: valid, isSetSubmittableByUuid: validByUuid } = useLabelStore.getState();
        if (!valid()) return;
        const allReady = queue.every((uuid: string) => validByUuid(uuid));
        if (queue.length === 1) {
          handleBatchAction("submit-all");
        } else {
          setSubmitDialogMode(allReady ? "all-ready" : "partial-ready");
        }
        return;
      }

      // Below shortcuts only in annotate mode, no modifier keys
      if (isReadMode || isPreviewMode || ctrl || shift) return;

      // 1–4: usability
      switch (key) {
        case "1": setUsability("IschemicAssessable"); return;
        case "2": setUsability("HemorrhagicPresent"); return;
        case "3": setUsability("Anomaly"); return;
        case "4": setUsability("Irrelevant"); return;
      }

      const currentImg = useLabelStore.getState().currentImage();

      // Q: toggle low quality (Ischemic only)
      if (UP === "Q") {
        const { usability: u, lowQuality: lq } = useLabelStore.getState();
        if (u === "IschemicAssessable") setLowQuality(!lq);
        return;
      }

      // B / C / N: region (ASPECTS enabled only)
      if (currentImg && useLabelStore.getState().aspectsEnabled()) {
        if (UP === "B") { setRegion(currentImg.uuid, "BasalGanglia"); return; }
        if (UP === "C") { setRegion(currentImg.uuid, "CoronaRadiata"); return; }
        if (UP === "N") { setRegion(currentImg.uuid, "None"); return; }
      }
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isReadMode, isPreviewMode, queue, queuePos, showManagementBoard, submitDialogMode,
      confirmReset, confirmExit, handleSaveDraft, handleBatchAction,
      setUsability, setLowQuality, setRegion]);

  const doNavigatePending = async (deleteDraft = false) => {
    const dest = pendingNavDest;
    setPendingNavDest(null);
    if (deleteDraft && imageSetUuid) {
      try { await evaluationsApi.deleteDraftByImageSet(imageSetUuid); } catch { /* no draft is fine */ }
    }
    reset();
    clearQueue();
    if (dest === "__logout__") {
      try { await authApi.logout(); } finally {
        logout();
        navigate("/login");
      }
    } else {
      navigate(dest ?? "/");
    }
  };

  const handleExit = () => {
    if (isReadMode) { reset(); clearQueue(); navigate(isAdminRead ? "/admin/submissions" : "/"); return; }
    if (isPreviewMode) { reset(); clearQueue(); navigate("/"); return; }
    if (!hasAnyAnnotation) { reset(); clearQueue(); navigate("/"); return; }
    setPendingNavDest("/");
    setConfirmExit(true);
  };

  const handleResetAll = async () => {
    if (!imageSetUuid || !sessionUuid) return;
    reset();
    setLoading(true);
    try {
      const [setRes, imgRes] = await Promise.all([
        imageSetsApi.get(imageSetUuid),
        imagesApi.listByImageSet(imageSetUuid),
      ]);
      const imgSet: ImageSet = setRes.data;
      const imgs: ImageRecord[] = imgRes.data;
      loadImageSet(imgSet, imgs, sessionUuid);
      toast.success("Annotations reset.");
    } catch {
      toast.error("Failed to reload image set");
      navigate("/");
    } finally {
      setLoading(false);
    }
  };

  void isSetSubmittable; // used internally by ValidationStatus
  const queueReady = queue.map((uuid: string) => isSetSubmittableByUuid(uuid));
  const anyReady = queueReady.some(Boolean);
  const allReady = queue.length > 0 && queueReady.every(Boolean);
  const datasetIndex = indices[queuePos] ?? null;

  const aspectsDisabledMessage = usability === null
    ? (isReadMode ? "No usability recorded" : "Please give image set usability first")
    : "ASPECTS scoring is disabled for this image set";

  // Management Board helpers (closure over store state)
  type SnapLike = { usability: ImageSetUsability | null; lowQuality: boolean; setNotes: string; slices: Record<string, SliceEvalState> };

  const getSnapForMB = (uuid: string): SnapLike | null => {
    if (imageSet?.uuid === uuid) return { usability, lowQuality, setNotes, slices };
    return (setRegistry[uuid] as SnapLike) ?? null;
  };

  const getSetStatusMB = (uuid: string): { color: "gray" | "red" | "yellow" | "green"; text: string } => {
    const snap = getSnapForMB(uuid);
    if (!snap) return { color: "gray", text: "Not Visited" };
    if (!snap.usability) return { color: "gray", text: "Need Usability Classification" };
    const aspects = snap.usability === "IschemicAssessable" && !snap.lowQuality;
    if (!aspects) {
      if ((snap.usability === "Anomaly" || snap.usability === "Irrelevant") && !snap.setNotes?.trim())
        return { color: "red", text: `${USABILITY_LABELS[snap.usability]} — Missing Description` };
      const text = snap.usability === "IschemicAssessable" ? "Ischemic Low Quality" : USABILITY_LABELS[snap.usability];
      return { color: "green", text };
    }
    const entries = Object.entries(snap.slices);
    const hasBasal = entries.some(([, s]) => s.region === "BasalGanglia");
    const hasCorona = entries.some(([, s]) => s.region === "CoronaRadiata");
    if (!hasBasal || !hasCorona) return { color: "red", text: "Missing type — Need at least one BasalGanglia and CoronaRadiata slice" };
    const allValid = entries.every(([, s]) => mbSliceValid(s));
    if (!allValid) return { color: "red", text: "Missing Image Annotation" };
    const annotatedIdx = entries.map(([, s], i) => s.region !== "None" ? i : -1).filter(i => i !== -1);
    const consecutive = annotatedIdx.every((v, i) => i === 0 || v === annotatedIdx[i - 1] + 1);
    if (!consecutive) return { color: "yellow", text: "Warning: Images not consecutive" };
    return { color: "green", text: USABILITY_LABELS[snap.usability] };
  };

  const getMBImagesForUuid = (uuid: string) => {
    if (imageSet?.uuid === uuid) return images.map((img, i) => ({ uuid: img.uuid, index: i }));
    const snap = setRegistry[uuid];
    if (!snap) return [];
    return Object.keys(snap.slices).map((imgUuid, i) => ({ uuid: imgUuid, index: i }));
  };

  const getMBSlicesForUuid = (uuid: string): Record<string, SliceEvalState> => {
    if (imageSet?.uuid === uuid) return slices;
    return (setRegistry[uuid]?.slices as Record<string, SliceEvalState>) ?? {};
  };

  return (
    <div className="relative flex h-[calc(100vh-3rem)] overflow-hidden">

      <div className={`absolute inset-0 z-20 flex items-center justify-center pointer-events-none transition-opacity duration-300 ${
        showOverlay ? "opacity-100 bg-background/50 backdrop-blur-[2px]" : "opacity-0"
      }`}>
        <Loader2 className="w-8 h-8 animate-spin text-primary/70" />
      </div>

      {/* ── Image viewer — 40% normal, 70% preview ── */}
      <div className={`${isPreviewMode ? "w-[70%]" : "w-[40%]"} bg-black relative flex items-center justify-center overflow-hidden shrink-0`}>
        {blobUrl ? (
          <img
            key={blobUrl}
            src={blobUrl}
            alt={`Slice ${currentIndex + 1}`}
            className="max-h-full max-w-full object-contain select-none"
            draggable={false}
            onContextMenu={(e) => e.preventDefault()}
          />
        ) : (
          <span className="text-muted-foreground text-sm">No image</span>
        )}
        {imgLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40">
            <span className="text-white text-sm">Loading…</span>
          </div>
        )}
        <div className="absolute top-3 left-3 bg-black/60 rounded px-2 py-1 text-white text-xs font-mono">
          Image {currentIndex + 1} of {images.length}
        </div>
        {currentImg?.image_name && (
          <div className="absolute top-3 right-3 bg-black/60 rounded px-2 py-1 text-white text-xs font-mono max-w-[50%] truncate">
            {currentImg.image_name}
          </div>
        )}
      </div>

      {/* ── Middle (30%): image annotation — hidden in preview ── */}
      {!isPreviewMode && <div className="w-[30%] flex flex-col border-l border-border bg-background shrink-0 overflow-hidden">
        <div className="flex-1 overflow-y-auto">
          <div className="p-4 space-y-4">
            <h3 className="text-base font-semibold uppercase tracking-widest text-muted-foreground">
              Image Annotation
            </h3>

            {/* Navigation & windowing */}
            <div className="space-y-3">
              {images.length === 1 ? (
                <p className="text-base text-muted-foreground">Image 1 of 1</p>
              ) : (
                <div className="flex items-end gap-2">
                  <WithTooltip content="Previous image (← key)" side="top">
                    <Button
                      variant="outline" size="icon" className="h-8 w-8 shrink-0"
                      onClick={() => {
                        const n = (currentIndex - 1 + images.length) % images.length;
                        setCurrentIndex(n);
                        setJumpImgInput(String(n + 1));
                      }}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                  </WithTooltip>
                  <Input
                    type="number"
                    className={`h-8 w-16 text-center text-base ${NO_SPINNER}`}
                    value={jumpImgInput}
                    onChange={(e) => setJumpImgInput(e.target.value)}
                    onBlur={(e) => applyJumpImage(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && applyJumpImage(jumpImgInput)}
                    min={1} max={images.length}
                  />
                  <span className="text-base text-muted-foreground shrink-0">of {images.length}</span>
                  <WithTooltip content="Next image (→ key)" side="top">
                    <Button
                      variant="outline" size="icon" className="h-8 w-8 shrink-0"
                      onClick={() => {
                        const n = (currentIndex + 1) % images.length;
                        setCurrentIndex(n);
                        setJumpImgInput(String(n + 1));
                      }}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </WithTooltip>
                  <div className="flex-1 min-w-0 flex flex-col gap-0.5">
                    <span className="text-[10px] text-muted-foreground leading-none">Jump to Image</span>
                    <input
                      type="range"
                      min={1}
                      max={images.length}
                      value={currentIndex + 1}
                      onChange={(e) => {
                        const n = parseInt(e.target.value);
                        setCurrentIndex(n - 1);
                        setJumpImgInput(String(n));
                      }}
                      className="w-full cursor-pointer accent-primary"
                    />
                  </div>
                </div>
              )}

              <div className="flex items-center gap-2">
                <Label className="text-base text-muted-foreground shrink-0">WL</Label>
                <Input
                  type="number"
                  className={`h-7 w-16 text-base ${NO_SPINNER}`}
                  value={wlInput}
                  onChange={(e) => setWlInput(e.target.value)}
                  onBlur={applyWindow}
                  onKeyDown={(e) => e.key === "Enter" && applyWindow()}
                />
                <Label className="text-base text-muted-foreground shrink-0">WW</Label>
                <Input
                  type="number"
                  className={`h-7 w-16 text-base ${NO_SPINNER}`}
                  value={wwInput}
                  onChange={(e) => setWwInput(e.target.value)}
                  onBlur={applyWindow}
                  onKeyDown={(e) => e.key === "Enter" && applyWindow()}
                />
                <WithTooltip content={`Reset to WL ${defaultWindowLevel} / WW ${defaultWindowWidth}`} side="top">
                  <Button
                    variant="outline" size="icon" className="h-7 w-7 shrink-0"
                    onClick={handleResetWindow}
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                  </Button>
                </WithTooltip>
              </div>
            </div>

            <Separator />

            {/* ASPECTS scoring */}
            <div className="space-y-3">
              <p className="text-base font-medium text-muted-foreground">Image Annotation</p>
              {!aspectsEnabled() ? (
                <div className="rounded border border-dashed border-muted-foreground/30 px-4 py-6 text-center">
                  <p className="text-base font-medium text-muted-foreground">
                    {aspectsDisabledMessage}
                  </p>
                </div>
              ) : currentImg ? (
                <SliceEvaluation imageUuid={currentImg.uuid} readOnly={isReadMode} />
              ) : (
                <p className="text-base text-muted-foreground">No image loaded</p>
              )}
            </div>
          </div>
        </div>
      </div>}

      {/* ── Right (30%): image set evaluation — hidden in preview ── */}
      {!isPreviewMode && <div className="w-[30%] flex flex-col border-l border-border bg-background shrink-0 overflow-hidden">
        <div className="flex-1 overflow-y-auto">
          <div className="p-4 space-y-4">
            <h3 className="text-base font-semibold uppercase tracking-widest text-muted-foreground">
              Image Set Evaluation
            </h3>

            {/* Set position indicator + navigation (always visible) */}
            <div className="space-y-2">
              <p className="text-lg font-semibold text-foreground">
                Set {queuePos + 1} of {queue.length}
              </p>
              {queue.length > 1 && (
                <div className="flex items-center gap-2">
                  <WithTooltip content="Previous image set" side="top">
                    <Button
                      variant="outline" size="icon" className="h-8 w-8 shrink-0"
                      disabled={navigating}
                      onClick={() => goToSet(queue[(queuePos - 1 + queue.length) % queue.length])}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                  </WithTooltip>
                  <Input
                    type="number"
                    className={`h-8 w-14 text-center text-base ${NO_SPINNER}`}
                    value={jumpSetInput}
                    onChange={(e) => setJumpSetInput(e.target.value)}
                    onBlur={(e) => applyJumpSet(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && applyJumpSet(jumpSetInput)}
                    min={1} max={queue.length}
                  />
                  <span className="text-sm text-muted-foreground shrink-0">of {queue.length}</span>
                  <WithTooltip content="Next image set" side="top">
                    <Button
                      variant="outline" size="icon" className="h-8 w-8 shrink-0"
                      disabled={navigating}
                      onClick={() => goToSet(queue[(queuePos + 1) % queue.length])}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </WithTooltip>
                  {queue.length >= 4 && (
                    <input
                      type="range"
                      min={1}
                      max={queue.length}
                      value={parseInt(jumpSetInput) || queuePos + 1}
                      onChange={(e) => setJumpSetInput(e.target.value)}
                      onPointerUp={(e) => applyJumpSet((e.target as HTMLInputElement).value)}
                      className="flex-1 min-w-0 cursor-pointer accent-primary"
                    />
                  )}
                </div>
              )}
            </div>

            {/* Tabs — Set Information / Patient Information / (Reader) Annotation Info */}
            <div className="space-y-3">
              <div className="flex border-b border-border">
                {(["set-info", "patient-info"] as const).map((tab) => (
                  <button
                    key={tab}
                    type="button"
                    onClick={() => setRightTab(tab)}
                    className={`px-3 py-1.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap ${
                      rightTab === tab
                        ? "border-primary text-foreground"
                        : "border-transparent text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {tab === "set-info" ? "Set Information" : "Patient Information"}
                  </button>
                ))}
                {isReadMode && (
                  <button
                    type="button"
                    onClick={() => setRightTab("annotation-info")}
                    className={`px-3 py-1.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap ${
                      rightTab === "annotation-info"
                        ? "border-primary text-foreground"
                        : "border-transparent text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    Annotation Info
                  </button>
                )}
              </div>

              {/* ── Set Information ── */}
              {rightTab === "set-info" && (
                <div className="space-y-1 text-base">
                  {datasetIndex !== null && (
                    <div className="flex gap-2">
                      <span className="text-muted-foreground w-24 shrink-0">Set Index</span>
                      <span className="font-mono">{datasetIndex}</span>
                    </div>
                  )}
                  {imageSet?.image_set_name && (
                    <div className="flex gap-2">
                      <span className="text-muted-foreground w-24 shrink-0">Set ID</span>
                      <span className="font-mono truncate">{imageSet.image_set_name}</span>
                    </div>
                  )}
                </div>
              )}

              {/* ── Patient Information ── */}
              {rightTab === "patient-info" && (
                <div className="space-y-1 text-base">
                  <div className="flex gap-2">
                    <span className="text-muted-foreground w-24 shrink-0">Patient ID</span>
                    <span
                      className="font-mono truncate max-w-[140px]"
                      title={imageSet?.patient_id ?? undefined}
                    >
                      {imageSet?.patient_id ?? "—"}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-muted-foreground w-24 shrink-0">Age</span>
                    <span>{imageSet?.patient_age != null ? imageSet.patient_age : "—"}</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-muted-foreground w-24 shrink-0">Gender</span>
                    <span>{imageSet?.patient_gender ?? "—"}</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-muted-foreground w-24 shrink-0">ICD</span>
                    <span className="font-mono">{imageSet?.icd_code ?? "—"}</span>
                  </div>
                  {imageSet?.description && (
                    <div className="flex gap-2">
                      <span className="text-muted-foreground w-24 shrink-0">Description</span>
                      <span className="leading-relaxed text-sm">{imageSet.description}</span>
                    </div>
                  )}
                </div>
              )}

              {/* ── Annotation Info (reader mode only) ── */}
              {rightTab === "annotation-info" && isReadMode && (
                <div className="space-y-3 text-base">
                  <div className="flex gap-2 items-start">
                    <span className="text-muted-foreground w-20 shrink-0">Type</span>
                    {annotationMeta ? (
                      annotationMeta.type === "submission" ? (
                        <span className="inline-flex items-center rounded-full border border-blue-500/40 bg-blue-500/10 px-2.5 py-0.5 text-sm font-medium text-blue-400">
                          Full Annotation
                        </span>
                      ) : (
                        <span className="inline-flex items-center rounded-full border border-yellow-500/40 bg-yellow-500/10 px-2.5 py-0.5 text-sm font-medium text-yellow-400">
                          Draft
                        </span>
                      )
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <span className="text-muted-foreground w-20 shrink-0">By</span>
                    <span className="font-medium">
                      {annotationMeta
                        ? (annotationMeta.doctorFullName ?? annotationMeta.doctorUsername ?? "—")
                        : "—"}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-muted-foreground w-20 shrink-0">Time</span>
                    <span className="text-sm">
                      {annotationMeta?.timestamp
                        ? new Date(annotationMeta.timestamp).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })
                        : "—"}
                    </span>
                  </div>
                </div>
              )}
            </div>

            <Separator />

            {/* Set classification */}
            <div className="space-y-3">
              <p className="text-base font-medium text-muted-foreground">Set Classification</p>
              <SetLevelEvaluation readOnly={isReadMode} />
            </div>
          </div>
        </div>

        {/* ── Pinned action buttons ── */}
        <div className="border-t border-border p-4 space-y-3 shrink-0">
          {isReadMode ? (
            <>
              <div className="rounded-md border border-blue-500/30 bg-blue-500/10 px-3 py-2 text-sm text-blue-400 text-center font-medium">
                Read-only — annotations cannot be changed
              </div>
              <Button
                variant="outline"
                className="w-full gap-2 border-foreground text-foreground font-semibold"
                onClick={() => setShowManagementBoard(true)}
              >
                <ClipboardList className="h-4 w-4" />
                Management Board
              </Button>
              <Button
                className="w-full gap-2 bg-purple-600 hover:bg-purple-700 text-white"
                onClick={handleExit}
              >
                <ArrowLeft className="h-4 w-4" />
                {isAdminRead ? "Return to Submissions" : "Return to Dashboard"}
              </Button>
            </>
          ) : (
            <>
              <ValidationStatus />
              <Button
                variant="outline"
                className="w-full gap-2 border-foreground text-foreground font-semibold"
                onClick={() => setShowManagementBoard(true)}
              >
                <ClipboardList className="h-4 w-4" />
                Management Board
              </Button>
              <div className="flex gap-2">
                <Button
                  className="flex-1 gap-2 bg-yellow-500 hover:bg-yellow-600 text-black"
                  disabled={savingDraft || submitting}
                  onClick={handleSaveDraft}
                >
                  <Save className="h-4 w-4" />
                  {savingDraft ? "Saving…" : "Save Draft"}
                </Button>
                <Button
                  className="flex-1 gap-2"
                  disabled={!anyReady || submitting || navigating}
                  onClick={() => setSubmitDialogMode(allReady ? "all-ready" : "partial-ready")}
                >
                  <Send className="h-4 w-4" />
                  {submitting ? "Submitting…" : anyReady ? "Submit Annotation" : "Not Ready"}
                </Button>
              </div>
              <div className="flex gap-2">
                <Button
                  className="flex-1 gap-2 bg-purple-600 hover:bg-purple-700 text-white"
                  onClick={handleExit}
                >
                  <ArrowLeft className="h-4 w-4" />
                  Exit to Dashboard
                </Button>
                <Button
                  variant="ghost"
                  className="flex-1 gap-2 text-destructive hover:text-destructive"
                  onClick={() => setConfirmReset(true)}
                >
                  <Trash2 className="h-4 w-4" />
                  Reset All Annotations
                </Button>
              </div>
            </>
          )}
        </div>
      </div>}

      {/* ── Preview panel (30%) — only in preview mode ── */}
      {isPreviewMode && (
        <div className="w-[30%] flex flex-col border-l border-border bg-background shrink-0 overflow-hidden">
          <div className="flex-1 overflow-y-auto">
            <div className="p-4 space-y-4" style={{ zoom: 1.25 }}>

              {/* Image Set Preview */}
              <h3 className="text-base font-semibold uppercase tracking-widest text-muted-foreground">
                Image Set Preview
              </h3>
              <div className="space-y-2">
                <p className="text-lg font-semibold">{queue.length > 1 ? `Set ${queuePos + 1} of ${queue.length}` : "Set"}</p>
                {queue.length > 1 && (
                  <div className="flex items-center gap-2">
                    <WithTooltip content="Previous image set" side="top">
                      <Button variant="outline" size="icon" className="h-8 w-8 shrink-0" disabled={navigating}
                        onClick={() => goToSet(queue[(queuePos - 1 + queue.length) % queue.length])}>
                        <ChevronLeft className="h-4 w-4" />
                      </Button>
                    </WithTooltip>
                    <Input type="number" className={`h-8 w-14 text-center text-base ${NO_SPINNER}`}
                      value={jumpSetInput}
                      onChange={(e) => setJumpSetInput(e.target.value)}
                      onBlur={(e) => applyJumpSet(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && applyJumpSet(jumpSetInput)}
                      min={1} max={queue.length} />
                    <span className="text-sm text-muted-foreground shrink-0">of {queue.length}</span>
                    <WithTooltip content="Next image set" side="top">
                      <Button variant="outline" size="icon" className="h-8 w-8 shrink-0" disabled={navigating}
                        onClick={() => goToSet(queue[(queuePos + 1) % queue.length])}>
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </WithTooltip>
                    {queue.length >= 4 && (
                      <input type="range" min={1} max={queue.length}
                        value={parseInt(jumpSetInput) || queuePos + 1}
                        onChange={(e) => setJumpSetInput(e.target.value)}
                        onPointerUp={(e) => applyJumpSet((e.target as HTMLInputElement).value)}
                        className="flex-1 min-w-0 cursor-pointer accent-primary" />
                    )}
                  </div>
                )}
              </div>

              {/* Set Information */}
              <div className="space-y-1 text-sm">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Set Information</p>
                {datasetIndex !== null && <div className="flex gap-2"><span className="text-muted-foreground w-24 shrink-0">Set Index</span><span className="font-mono">{datasetIndex}</span></div>}
                {imageSet?.image_set_name && <div className="flex gap-2"><span className="text-muted-foreground w-24 shrink-0">Set Name</span><span className="truncate">{imageSet.image_set_name}</span></div>}
              </div>

              {/* Patient Information */}
              <div className="space-y-1 text-sm">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Patient Information</p>
                <div className="flex gap-2"><span className="text-muted-foreground w-24 shrink-0">Patient ID</span><span className="font-mono truncate max-w-[140px]" title={imageSet?.patient_id ?? undefined}>{imageSet?.patient_id ?? "—"}</span></div>
                <div className="flex gap-2"><span className="text-muted-foreground w-24 shrink-0">Age</span><span>{imageSet?.patient_age != null ? imageSet.patient_age : "—"}</span></div>
                <div className="flex gap-2"><span className="text-muted-foreground w-24 shrink-0">Gender</span><span>{imageSet?.patient_gender ?? "—"}</span></div>
                <div className="flex gap-2"><span className="text-muted-foreground w-24 shrink-0">ICD</span><span className="font-mono">{imageSet?.icd_code ?? "—"}</span></div>
                {imageSet?.description && <div className="flex gap-2"><span className="text-muted-foreground w-24 shrink-0">Description</span><span className="text-muted-foreground">{imageSet.description}</span></div>}
              </div>

              <Separator />

              {/* Image Preview */}
              <h3 className="text-base font-semibold uppercase tracking-widest text-muted-foreground">
                Image Preview
              </h3>
              <div className="space-y-3">
                {images.length === 1 ? (
                  <p className="text-base text-muted-foreground">Image 1 of 1</p>
                ) : (
                  <div className="flex items-end gap-2">
                    <WithTooltip content="Previous image (← key)" side="top">
                      <Button variant="outline" size="icon" className="h-8 w-8 shrink-0"
                        onClick={() => { const n = (currentIndex - 1 + images.length) % images.length; setCurrentIndex(n); setJumpImgInput(String(n + 1)); }}>
                        <ChevronLeft className="h-4 w-4" />
                      </Button>
                    </WithTooltip>
                    <Input type="number" className={`h-8 w-16 text-center text-base ${NO_SPINNER}`}
                      ref={jumpImgInputRef}
                      value={jumpImgInput}
                      onChange={(e) => setJumpImgInput(e.target.value)}
                      onBlur={(e) => applyJumpImage(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && applyJumpImage(jumpImgInput)}
                      min={1} max={images.length} />
                    <span className="text-base text-muted-foreground shrink-0">of {images.length}</span>
                    <WithTooltip content="Next image (→ key)" side="top">
                      <Button variant="outline" size="icon" className="h-8 w-8 shrink-0"
                        onClick={() => { const n = (currentIndex + 1) % images.length; setCurrentIndex(n); setJumpImgInput(String(n + 1)); }}>
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </WithTooltip>
                    <div className="flex-1 min-w-0 flex flex-col gap-0.5">
                      <span className="text-[10px] text-muted-foreground leading-none">Jump to Image</span>
                      <input type="range" min={1} max={images.length} value={currentIndex + 1}
                        onChange={(e) => { const n = parseInt(e.target.value); setCurrentIndex(n - 1); setJumpImgInput(String(n)); }}
                        className="w-full cursor-pointer accent-primary" />
                    </div>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <Label className="text-base text-muted-foreground shrink-0">WL</Label>
                  <Input type="number" className={`h-7 w-16 text-base ${NO_SPINNER}`} value={wlInput}
                    onChange={(e) => setWlInput(e.target.value)} onBlur={applyWindow}
                    onKeyDown={(e) => e.key === "Enter" && applyWindow()} />
                  <Label className="text-base text-muted-foreground shrink-0">WW</Label>
                  <Input type="number" className={`h-7 w-16 text-base ${NO_SPINNER}`} value={wwInput}
                    onChange={(e) => setWwInput(e.target.value)} onBlur={applyWindow}
                    onKeyDown={(e) => e.key === "Enter" && applyWindow()} />
                  <WithTooltip content={`Reset to WL ${defaultWindowLevel} / WW ${defaultWindowWidth}`} side="top">
                    <Button variant="outline" size="icon" className="h-7 w-7 shrink-0" onClick={handleResetWindow}>
                      <RotateCcw className="h-3.5 w-3.5" />
                    </Button>
                  </WithTooltip>
                </div>
              </div>

            </div>
          </div>

          {/* Pinned actions */}
          <div className="border-t border-border p-4 space-y-3 shrink-0">
            <Button variant="outline" className="w-full gap-2 border-foreground text-foreground font-semibold"
              onClick={() => setShowManagementBoard(true)}>
              <ClipboardList className="h-4 w-4" /> Management Board
            </Button>
            <Button className="w-full gap-2 bg-purple-600 hover:bg-purple-700 text-white" onClick={handleExit}>
              <ArrowLeft className="h-4 w-4" /> Return to Dashboard
            </Button>
          </div>
        </div>
      )}

      {/* ── Submit dialog — all ready ── */}
      {submitDialogMode === "all-ready" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-background border border-border rounded-lg p-6 w-80 space-y-4 shadow-xl">
            <p className="text-base font-semibold">How do you want to save?</p>
            <p className="text-sm text-muted-foreground">All {queue.length} image set(s) are ready to submit.</p>
            <div className="flex flex-col gap-2">
              <Button className="w-full bg-green-600 hover:bg-green-700 text-white" onClick={() => handleBatchAction("submit-all")}>
                Yes, submit all
              </Button>
              <Button className="w-full bg-yellow-500 hover:bg-yellow-600 text-black" onClick={() => handleBatchAction("draft-all")}>
                Save Draft All
              </Button>
              <Button className="w-full bg-red-600 hover:bg-red-700 text-white" onClick={() => setSubmitDialogMode(null)}>
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ── Submit dialog — partial ready ── */}
      {submitDialogMode === "partial-ready" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-background border border-border rounded-lg p-6 w-80 space-y-4 shadow-xl">
            <p className="text-base font-semibold">How do you want to save?</p>
            <p className="text-sm text-muted-foreground">
              {queueReady.filter(Boolean).length} of {queue.length} image set(s) ready.
            </p>
            <div className="flex flex-col gap-2">
              <Button className="w-full bg-green-600 hover:bg-green-700 text-white" onClick={() => handleBatchAction("submit-ready-draft-incomplete")}>
                Submit Ready, Draft Incompleted
              </Button>
              <Button className="w-full bg-blue-600 hover:bg-blue-700 text-white" onClick={() => handleBatchAction("submit-ready-drop-incomplete")}>
                Submit Ready, Drop Incompleted
              </Button>
              <Button className="w-full bg-yellow-500 hover:bg-yellow-600 text-black" onClick={() => handleBatchAction("draft-all")}>
                Draft All
              </Button>
              <Button className="w-full bg-red-600 hover:bg-red-700 text-white" onClick={() => setSubmitDialogMode(null)}>
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ── Reset confirmation ── */}
      {confirmReset && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-background border border-border rounded-lg p-6 w-80 space-y-4 shadow-xl">
            <p className="text-base font-semibold">Reset all annotations?</p>
            <p className="text-sm text-muted-foreground">All scored zones, region selections, and notes for this session will be cleared. This cannot be undone.</p>
            <div className="flex gap-3">
              <Button
                className="flex-1 bg-red-600 hover:bg-red-700 text-white"
                onClick={() => { setConfirmReset(false); handleResetAll(); }}
              >
                Yes. Delete
              </Button>
              <Button
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
                onClick={() => setConfirmReset(false)}
              >
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ── Exit / Nav intercept confirmation ── */}
      {confirmExit && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-background border border-border rounded-lg p-6 w-80 space-y-4 shadow-xl">
            <p className="text-base font-semibold">Leave annotation?</p>
            <p className="text-sm text-muted-foreground">
              Your latest changes have been auto-saved. You can keep or discard them.
            </p>
            <div className="flex flex-col gap-2">
              <Button
                className="w-full gap-2 bg-yellow-500 hover:bg-yellow-600 text-black"
                disabled={savingDraft}
                onClick={async () => { setConfirmExit(false); await handleSaveDraft(); doNavigatePending(); }}
              >
                <Save className="h-4 w-4" />
                {savingDraft ? "Saving…" : "Draft the latest changes"}
              </Button>
              <Button
                variant="outline"
                className="w-full"
                onClick={() => { setConfirmExit(false); doNavigatePending(true); }}
              >
                Don't keep the latest changes
              </Button>
              <Button
                variant="ghost"
                className="w-full text-muted-foreground"
                onClick={() => { setConfirmExit(false); setPendingNavDest(null); }}
              >
                Back to Annotation
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ── Management Board ── */}
      {showManagementBoard && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div
            className="bg-background border border-border rounded-lg shadow-xl flex flex-col"
            style={{ width: "70vw", height: "70vh" }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-3 border-b shrink-0">
              <h2 className="text-base font-semibold flex items-center gap-2">
                <ClipboardList className="h-4 w-4" />
                Management Board
              </h2>
              <button
                onClick={() => setShowManagementBoard(false)}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Body: left (set statuses) | right (image status) */}
            <div className="flex flex-1 min-h-0">

              {/* Left: Image Set Statuses */}
              <div className={`${isPreviewMode ? "w-full" : "w-1/2 border-r"} overflow-y-auto`}>
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-background border-b z-10">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium text-muted-foreground w-12">Set #</th>
                      <th className="px-3 py-2 text-left font-medium text-muted-foreground w-16">Index</th>
                      {!isPreviewMode && <th className="px-3 py-2 text-left font-medium text-muted-foreground">Status</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {queue.map((uuid, pos) => {
                      const status = getSetStatusMB(uuid);
                      const isSelected = selectedBoardSetUuid === uuid;
                      const colorClass = {
                        gray: "text-gray-400",
                        red: "text-red-500",
                        yellow: "text-yellow-500",
                        green: "text-green-500",
                      }[status.color];
                      return (
                        <tr
                          key={uuid}
                          className={`cursor-pointer border-b transition-colors hover:bg-muted/50 ${isSelected ? "bg-muted" : ""}`}
                          onClick={() => setSelectedBoardSetUuid(isSelected ? null : uuid)}
                        >
                          <td className="px-3 py-2 font-mono text-muted-foreground">{pos + 1}</td>
                          <td className="px-3 py-2 font-mono text-muted-foreground">{indices[pos] ?? "—"}</td>
                          {!isPreviewMode && <td className={`px-3 py-2 font-medium ${colorClass}`}>{status.text}</td>}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Right: Image Status for selected set (hidden in preview mode) */}
              {!isPreviewMode && <div className="w-1/2 overflow-y-auto">

                {selectedBoardSetUuid ? (() => {
                  const snap = getSnapForMB(selectedBoardSetUuid);
                  const isAspects = snap?.usability === "IschemicAssessable" && !snap?.lowQuality;
                  if (!snap || !isAspects) {
                    return (
                      <div className="flex items-center justify-center h-full px-6">
                        <p className="text-sm text-muted-foreground text-center">
                          This Image Set has not evaluated any images
                        </p>
                      </div>
                    );
                  }
                  const imgList = getMBImagesForUuid(selectedBoardSetUuid);
                  const mbSlices = getMBSlicesForUuid(selectedBoardSetUuid);
                  const annotated = imgList.filter(({ uuid }) => {
                    const s = mbSlices[uuid];
                    return s && s.region !== "None";
                  });
                  if (annotated.length === 0) {
                    return (
                      <div className="flex items-center justify-center h-full px-6">
                        <p className="text-sm text-muted-foreground text-center">No images annotated yet</p>
                      </div>
                    );
                  }
                  return (
                    <table className="w-full text-sm">
                      <thead className="sticky top-0 bg-background border-b z-10">
                        <tr>
                          <th className="px-3 py-2 text-left font-medium text-muted-foreground w-16">Image</th>
                          <th className="px-3 py-2 text-left font-medium text-muted-foreground w-28">Zone</th>
                          <th className="px-3 py-2 text-left font-medium text-muted-foreground">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {annotated.map(({ uuid, index }) => {
                          const s = mbSlices[uuid];
                          const missing = getMissingZones(s);
                          return (
                            <tr key={uuid} className="border-b">
                              <td className="px-3 py-2 font-mono text-muted-foreground">{index + 1}</td>
                              <td className={`px-3 py-2 font-medium ${
                                s.region === "BasalGanglia" ? "text-purple-400"
                                : s.region === "CoronaRadiata" ? "text-cyan-400"
                                : "text-muted-foreground"
                              }`}>
                                {s.region === "BasalGanglia" ? "Basal Ganglia"
                                  : s.region === "CoronaRadiata" ? "Corona Radiata"
                                  : s.region}
                              </td>
                              <td className={`px-3 py-2 font-medium ${missing ? "text-red-500" : "text-green-500"}`}>
                                {missing ?? "Valid"}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  );
                })() : (
                  <div className="flex items-center justify-center h-full px-6">
                    <p className="text-sm text-muted-foreground text-center">
                      Select a set from the left to see image details
                    </p>
                  </div>
                )}
              </div>}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
