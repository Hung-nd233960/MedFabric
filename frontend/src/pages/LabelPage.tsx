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
import type { RegionScore } from "@/lib/types";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ChevronLeft, ChevronRight, RotateCcw, Send, ArrowLeft, Trash2, Save, X, ClipboardList, Loader2, Bot } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { WithTooltip, TooltipKbd, NavKbd } from "@/components/ui/tooltip";
import SetLevelEvaluation from "@/components/label/SetLevelEvaluation";
import SliceEvaluation from "@/components/label/SliceEvaluation";
import ValidationStatus from "@/components/label/ValidationStatus";
import { imagesApi, imageSetsApi, evaluationsApi, annotationSessionsApi, authApi, adminApi } from "@/lib/api";
import { useLabelStore, buildSnapshotFromPayload } from "@/store/labelStore";
import { useLabelQueueStore } from "@/store/labelQueueStore";
import { useAuthStore } from "@/store/authStore";
import { useNavGuardStore } from "@/store/navGuardStore";
import { useUiStore } from "@/store/uiStore";
import { useAppearanceStore } from "@/store/appearanceStore";
import { nav } from "@/lib/navKeys";
import type { ImageRecord, ImageSet, SliceEvalState, ImageSetUsability } from "@/lib/types";
import { USABILITY_LABELS, BASAL_ZONES, CORONA_ZONES } from "@/lib/types";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

type ZoneCell = { row: number; col: "left" | "right" };

function findSmartStart(zones: readonly string[], scores: Record<string, RegionScore | null>): ZoneCell {
  for (let i = 0; i < zones.length * 2; i++) {
    const row = Math.floor(i / 2);
    const col: "left" | "right" = i % 2 === 0 ? "left" : "right";
    if (!scores[`${zones[row]}_${col}_score`]) return { row, col };
  }
  return { row: 0, col: "left" };
}

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
    setAutoSaveStatus, setUsability, setLowQuality, setRegion, setScore,
  } = useLabelStore();

  const { logout } = useAuthStore();
  const { showKbdHints, navMode } = useAppearanceStore();

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
  const intentionalNav = useRef(false);
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

  const wlInputRef = useRef<HTMLInputElement>(null);
  const wwInputRef = useRef<HTMLInputElement>(null);
  const skipWindowApplyRef = useRef(false);
  const skipJumpImgApplyRef = useRef(false);
  const skipJumpSetApplyRef = useRef(false);
  const [mbActiveCol, setMbActiveCol] = useState<"left" | "right">("left");
  const [selectedMBImageIndex, setSelectedMBImageIndex] = useState<number>(-1);
  const [zoneModeActive, setZoneModeActive] = useState(false);
  const [zoneModeCursor, setZoneModeCursor] = useState<ZoneCell | null>(null);
  const [zoneModeVisual, setZoneModeVisual] = useState(false);
  const [zoneModeAnchor, setZoneModeAnchor] = useState<ZoneCell | null>(null);
  const [zoneModeScope, setZoneModeScope] = useState<"cell" | "row" | "col" | "all">("cell");
  const [wideMode, setWideMode] = useState(false);
  const [wideModeTab, setWideModeTab] = useState<"annotation" | "evaluation">("annotation");
  const sliceNotesRef = useRef<HTMLTextAreaElement>(null);
  const setLevelNotesRef = useRef<HTMLTextAreaElement>(null);

  const exitZoneMode = () => {
    setZoneModeActive(false); setZoneModeCursor(null);
    setZoneModeVisual(false); setZoneModeAnchor(null);
    setZoneModeScope("cell");
  };

  const handleWideModeTabClick = (tab: "annotation" | "evaluation") => {
    if (zoneModeActive) exitZoneMode();
    setWideModeTab(tab);
  };

  const currentImg = currentImage();

  // Redirect if queue is empty (e.g. page refresh)
  useEffect(() => {
    if (queue.length === 0 && !intentionalNav.current) navigate("/", { replace: true });
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

  // Keyboard navigation — image (← → / h l, no shift)
  const jumpImgInputRef = useRef<HTMLInputElement>(null);
  const jumpSetInputRef = useRef<HTMLInputElement>(null);
  const inputFocusRef = useRef(false);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.shiftKey) return; // Shift+←/→ / Shift+H/L handled in the comprehensive handler
      if (showManagementBoard) return; // MB takes over nav keys
      if (zoneModeActive) return; // Zone Mode takes over nav keys
      const m = useAppearanceStore.getState().navMode;
      if (nav.left(e, m))  setCurrentIndex((currentIndex - 1 + images.length) % images.length);
      if (nav.right(e, m)) setCurrentIndex((currentIndex + 1) % images.length);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [currentIndex, images.length, showManagementBoard, zoneModeActive, setCurrentIndex]);
  void inputFocusRef;

  useEffect(() => { setSelectedMBImageIndex(-1); }, [selectedBoardSetUuid]);

  const activateZoneMode = (imageUuid: string, region: "BasalGanglia" | "CoronaRadiata", visual = false) => {
    const zones = region === "BasalGanglia" ? BASAL_ZONES : CORONA_ZONES;
    const scores = useLabelStore.getState().slices[imageUuid]?.scores ?? {};
    const start = findSmartStart(zones, scores as Record<string, RegionScore | null>);
    setZoneModeCursor(start);
    setZoneModeActive(true);
    setZoneModeScope("cell");
    if (visual) { setZoneModeAnchor(start); setZoneModeVisual(true); }
  };

  // Auto-exit Zone Mode when ASPECTS scoring becomes unavailable
  useEffect(() => {
    if (!zoneModeActive) return;
    if (!aspectsEnabled()) exitZoneMode();
  }, [usability, lowQuality, zoneModeActive]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-exit or clamp cursor when current image region changes
  useEffect(() => {
    if (!zoneModeActive || !currentImg) return;
    const region = slices[currentImg.uuid]?.region ?? "None";
    if (region !== "BasalGanglia" && region !== "CoronaRadiata") { exitZoneMode(); return; }
    const zones = region === "BasalGanglia" ? BASAL_ZONES : CORONA_ZONES;
    setZoneModeCursor((c) => c ? { row: Math.min(c.row, zones.length - 1), col: c.col } : null);
    setZoneModeAnchor((c) => c ? { row: Math.min(c.row, zones.length - 1), col: c.col } : null);
  }, [currentImg?.uuid, slices, zoneModeActive]); // eslint-disable-line react-hooks/exhaustive-deps

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
      if (!dirty) { intentionalNav.current = true; st.reset(); useLabelQueueStore.getState().clear(); navigate(dest); return; }
      setPendingNavDest(dest);
      setConfirmExit(true);
    });
    return () => { useNavGuardStore.getState().setInterceptor(null); };
  }, [isReadMode, isPreviewMode, navigate]);

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
      intentionalNav.current = true;
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

  const doNavigatePending = async (deleteDraft = false) => {
    const dest = pendingNavDest;
    setPendingNavDest(null);
    if (deleteDraft && imageSetUuid) {
      try { await evaluationsApi.deleteDraftByImageSet(imageSetUuid); } catch { /* no draft is fine */ }
    }
    intentionalNav.current = true;
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
    if (isReadMode) { intentionalNav.current = true; reset(); clearQueue(); navigate(isAdminRead ? "/admin/submissions" : "/"); return; }
    if (isPreviewMode) { intentionalNav.current = true; reset(); clearQueue(); navigate("/"); return; }
    if (!hasAnyAnnotation) { intentionalNav.current = true; reset(); clearQueue(); navigate("/"); return; }
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

  // Comprehensive keyboard shortcuts (placed after all handlers are defined)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (useUiStore.getState().shortcutsOpen) return;
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;

      const key = e.key;
      const shift = e.shiftKey;
      const ctrl = e.ctrlKey || e.metaKey;
      const UP = key.toUpperCase();

      // Block browser Ctrl+A select-all outside Zone Mode
      if (ctrl && !shift && UP === "A" && !zoneModeActive) { e.preventDefault(); return; }

      // Y/N keyboard answer for confirmReset dialog (fires before the guard below)
      if (confirmReset && !ctrl) {
        if (UP === "Y") { e.preventDefault(); setConfirmReset(false); handleResetAll(); return; }
        if (UP === "N") { e.preventDefault(); setConfirmReset(false); return; }
      }

      // Block all other keys while any confirm dialog is open (ConfirmDialog handles them via capture)
      if (confirmReset || submitDialogMode !== null || confirmExit) { e.preventDefault(); return; }

      // Shift+Esc — return to Dashboard (all modes, same as the Exit button)
      if (shift && key === "Escape") {
        e.preventDefault();
        handleExit();
        return;
      }

      // Shift+Del — open Reset All Annotations prompt (annotate mode only)
      if (shift && !ctrl && key === "Delete" && !isReadMode && !isPreviewMode) {
        e.preventDefault();
        setConfirmReset(true);
        return;
      }

      // Shift+← / Shift+→ / Shift+H / Shift+L — queue navigation (all modes)
      if (!ctrl && nav.shiftLeft(e, navMode)) {
        e.preventDefault();
        if (zoneModeActive) exitZoneMode();
        if (queuePos > 0) goToSet(queue[queuePos - 1]);
        return;
      }
      if (!ctrl && nav.shiftRight(e, navMode)) {
        e.preventDefault();
        if (zoneModeActive) exitZoneMode();
        if (queuePos < queue.length - 1) goToSet(queue[queuePos + 1]);
        return;
      }

      // Shift+Tab — cycle through Image Set Evaluation tabs (non-preview only)
      if (shift && key === "Tab" && !ctrl && !isPreviewMode) {
        e.preventDefault();
        const tabs = (isReadMode
          ? ["set-info", "patient-info", "annotation-info"]
          : ["set-info", "patient-info"]) as Array<"set-info" | "patient-info" | "annotation-info">;
        const cur = tabs.indexOf(rightTab);
        setRightTab(tabs[(cur + 1) % tabs.length]);
        return;
      }

      // I — focus Jump to Image input | Shift+I — focus Jump to Set input (all modes)
      if (!ctrl && UP === "I") {
        e.preventDefault();
        if (shift) {
          jumpSetInputRef.current?.focus();
          jumpSetInputRef.current?.select();
        } else {
          jumpImgInputRef.current?.focus();
          jumpImgInputRef.current?.select();
        }
        return;
      }

      // W / Shift+W — focus WL input / reset windowing (all label modes)
      if (!ctrl && UP === "W") {
        e.preventDefault();
        if (shift) { handleResetWindow(); }
        else { wlInputRef.current?.focus(); wlInputRef.current?.select(); }
        return;
      }

      // Management Board keyboard navigation (when open, no modifier)
      if (showManagementBoard && !ctrl && !shift) {
        if (key === "Enter" && selectedBoardSetUuid) {
          e.preventDefault();
          if (mbActiveCol === "left") {
            const sameSet = selectedBoardSetUuid === imageSetUuid;
            if (sameSet) { setShowManagementBoard(false); }
            else { goToSet(selectedBoardSetUuid).then(() => setShowManagementBoard(false)); }
          } else if (mbActiveCol === "right" && selectedMBImageIndex >= 0) {
            const imgList = getMBImagesForUuid(selectedBoardSetUuid);
            const mbSlicesNow = getMBSlicesForUuid(selectedBoardSetUuid);
            const annotated = imgList.filter(({ uuid }) => {
              const s = mbSlicesNow[uuid];
              return s && s.region !== "None";
            });
            const target = annotated[selectedMBImageIndex];
            if (target) {
              const sameSet = selectedBoardSetUuid === imageSetUuid;
              const jump = () => { setCurrentIndex(target.index); setShowManagementBoard(false); };
              if (sameSet) jump();
              else goToSet(selectedBoardSetUuid).then(jump);
            }
          }
          return;
        }
        if (nav.left(e, navMode) || nav.right(e, navMode)) {
          if (!isPreviewMode) {
            e.preventDefault();
            const goingRight = nav.right(e, navMode);
            if (goingRight && mbActiveCol === "left") {
              // Only switch to right column if there are annotated rows to show
              if (selectedBoardSetUuid) {
                const snap = getSnapForMB(selectedBoardSetUuid);
                const imgList = getMBImagesForUuid(selectedBoardSetUuid);
                const mbSlicesNow = getMBSlicesForUuid(selectedBoardSetUuid);
                const hasRows = snap?.usability === "IschemicAssessable" && !snap.lowQuality &&
                  imgList.some(({ uuid }) => { const s = mbSlicesNow[uuid]; return s && s.region !== "None"; });
                if (hasRows) setMbActiveCol("right");
              }
            } else {
              setMbActiveCol(c => c === "left" ? "right" : "left");
            }
          }
          return;
        }
        if (nav.up(e, navMode) || nav.down(e, navMode)) {
          e.preventDefault();
          const dir = nav.up(e, navMode) ? -1 : 1;
          if (mbActiveCol === "left") {
            const cur = selectedBoardSetUuid ? queue.indexOf(selectedBoardSetUuid) : -1;
            const next = cur < 0
              ? (dir > 0 ? 0 : queue.length - 1)
              : Math.max(0, Math.min(queue.length - 1, cur + dir));
            setSelectedBoardSetUuid(queue[next] ?? null);
          } else if (selectedBoardSetUuid) {
            const imgList = getMBImagesForUuid(selectedBoardSetUuid);
            const snap = getSnapForMB(selectedBoardSetUuid);
            if (snap?.usability === "IschemicAssessable" && !snap.lowQuality) {
              const mbSlicesNow = getMBSlicesForUuid(selectedBoardSetUuid);
              const annotated = imgList.filter(({ uuid }) => {
                const s = mbSlicesNow[uuid];
                return s && s.region !== "None";
              });
              if (annotated.length > 0) {
                setSelectedMBImageIndex(prev => {
                  const start = prev < 0 ? (dir > 0 ? 0 : annotated.length - 1) : prev;
                  return Math.max(0, Math.min(annotated.length - 1, start + dir));
                });
              }
            }
          }
          return;
        }
      }

      // M — toggle Management Board (all modes)
      if (!ctrl && !shift && UP === "M") {
        setShowManagementBoard((v) => !v);
        setMbActiveCol("left");
        setSelectedMBImageIndex(-1);
        return;
      }

      // Esc — close Management Board or Zone Mode (dialogs handle their own Esc via ConfirmDialog capture listener)
      if (key === "Escape") {
        if (showManagementBoard) { setShowManagementBoard(false); return; }
        if (zoneModeScope !== "cell") { setZoneModeScope("cell"); return; }
        if (zoneModeVisual) { setZoneModeVisual(false); setZoneModeAnchor(null); return; }
        if (zoneModeActive) { exitZoneMode(); return; }
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

      // Shift+1–4/0: usability (annotate mode only, not while Zone Mode is active)
      if (shift && !ctrl && !isReadMode && !isPreviewMode && !zoneModeActive) {
        const revealEval = () => { if (wideMode && wideModeTab === "annotation") setWideModeTab("evaluation"); };
        switch (e.code) {
          case "Digit1": e.preventDefault(); setUsability("IschemicAssessable"); revealEval(); return;
          case "Digit2": e.preventDefault(); setUsability("HemorrhagicPresent"); revealEval(); return;
          case "Digit3": e.preventDefault(); setUsability("Anomaly"); revealEval(); return;
          case "Digit4": e.preventDefault(); setUsability("Irrelevant"); revealEval(); return;
          case "Digit0": e.preventDefault(); setUsability(null); revealEval(); return;
        }
      }

      // Shift+P: switch wide mode tab (wide mode only, not in Zone Mode)
      if (shift && !ctrl && UP === "P" && !isReadMode && !isPreviewMode && wideMode) {
        e.preventDefault();
        setWideModeTab(t => t === "annotation" ? "evaluation" : "annotation");
        return;
      }

      // Shift+Q: toggle low quality (annotate mode, Ischemic only)
      if (shift && !ctrl && UP === "Q" && !isReadMode && !isPreviewMode && !zoneModeActive) {
        const { usability: u, lowQuality: lq } = useLabelStore.getState();
        if (u === "IschemicAssessable") {
          setLowQuality(!lq);
          if (wideMode && wideModeTab === "annotation") setWideModeTab("evaluation");
        }
        return;
      }

      // Shift+B/C/N: set region (annotate mode, ASPECTS enabled)
      if (shift && !ctrl && !isReadMode && !isPreviewMode) {
        const zmImg2 = useLabelStore.getState().currentImage();
        if (zmImg2 && useLabelStore.getState().aspectsEnabled()) {
          if (UP === "B" || UP === "C" || UP === "N") {
            e.preventDefault();
            const targetRegion = UP === "B" ? "BasalGanglia" : UP === "C" ? "CoronaRadiata" : "None";
            const curRegion = useLabelStore.getState().slices[zmImg2.uuid]?.region ?? "None";
            if (targetRegion !== "None" && curRegion === targetRegion) {
              // Re-press same zone — activate Zone Mode instead of resetting
              activateZoneMode(zmImg2.uuid, targetRegion as "BasalGanglia" | "CoronaRadiata");
            } else if (targetRegion === "None" && curRegion === "None") {
              // Already None — jump to slice notes
              sliceNotesRef.current?.focus();
            } else {
              setRegion(zmImg2.uuid, targetRegion as "None" | "BasalGanglia" | "CoronaRadiata");
              if (zoneModeActive) exitZoneMode();
            }
            return;
          }
        }
      }

      // Zone Mode keyboard handling
      if (zoneModeActive && !isReadMode && !isPreviewMode && !showManagementBoard) {
        const zmImg = useLabelStore.getState().currentImage();
        const zmSlice = zmImg ? useLabelStore.getState().slices[zmImg.uuid] : null;
        const zmRegion = zmSlice?.region;
        const zmZones = zmRegion === "BasalGanglia" ? BASAL_ZONES :
                        zmRegion === "CoronaRadiata" ? CORONA_ZONES : null;

        if (zmImg && zmZones && zoneModeCursor) {
          const totalCells = zmZones.length * 2;

          // 1 / 2 / 3 — score based on scope or Vis selection, then advance
          if (!shift && !ctrl && (key === "1" || key === "2" || key === "3")) {
            e.preventDefault();
            const SCORE_MAP: Record<string, RegionScore> = {
              "1": "Affected", "2": "Not_Affected", "3": "Not_In_This_Slice",
            };
            const score = SCORE_MAP[key];

            if (zoneModeVisual && zoneModeAnchor) {
              // Vis Mode: score the visual rectangle
              const rMin = Math.min(zoneModeAnchor.row, zoneModeCursor.row);
              const rMax = Math.max(zoneModeAnchor.row, zoneModeCursor.row);
              const selCols = new Set([zoneModeAnchor.col, zoneModeCursor.col]);
              const cols = (["left", "right"] as const).filter((c) => selCols.has(c));
              for (let r = rMin; r <= rMax; r++)
                for (const col of cols)
                  setScore(zmImg.uuid, `${zmZones[r]}_${col}_score`, score);
              setZoneModeVisual(false); setZoneModeAnchor(null);
              const lastIdx = rMax * 2 + (selCols.has("right") ? 1 : 0);
              if (lastIdx < totalCells - 1) {
                const ni = lastIdx + 1;
                setZoneModeCursor({ row: Math.floor(ni / 2), col: ni % 2 === 0 ? "left" : "right" });
              } else { exitZoneMode(); toast.success("Zone scoring complete."); }
            } else if (zoneModeScope === "row") {
              setScore(zmImg.uuid, `${zmZones[zoneModeCursor.row]}_left_score`, score);
              setScore(zmImg.uuid, `${zmZones[zoneModeCursor.row]}_right_score`, score);
              if (zoneModeCursor.row < zmZones.length - 1)
                setZoneModeCursor({ row: zoneModeCursor.row + 1, col: "left" });
              else { exitZoneMode(); toast.success("Zone scoring complete."); }
            } else if (zoneModeScope === "col") {
              const currentCol = zoneModeCursor.col;
              const otherCol: "left" | "right" = currentCol === "left" ? "right" : "left";
              for (let r = 0; r < zmZones.length; r++)
                setScore(zmImg.uuid, `${zmZones[r]}_${currentCol}_score`, score);
              const storeSlice = useLabelStore.getState().slices[zmImg.uuid];
              const otherDone = zmZones.every(z => (storeSlice?.scores[`${z}_${otherCol}_score`] ?? null) !== null);
              if (otherDone) { exitZoneMode(); toast.success("Zone scoring complete."); }
              else setZoneModeCursor(c => c ? { ...c, col: otherCol } : c);
            } else if (zoneModeScope === "all") {
              for (let r = 0; r < zmZones.length; r++) {
                setScore(zmImg.uuid, `${zmZones[r]}_left_score`, score);
                setScore(zmImg.uuid, `${zmZones[r]}_right_score`, score);
              }
              exitZoneMode(); toast.success("Zone scoring complete.");
            } else {
              // Single cell
              setScore(zmImg.uuid, `${zmZones[zoneModeCursor.row]}_${zoneModeCursor.col}_score`, score);
              const ci = zoneModeCursor.row * 2 + (zoneModeCursor.col === "left" ? 0 : 1);
              if (ci < totalCells - 1) {
                const ni = ci + 1;
                setZoneModeCursor({ row: Math.floor(ni / 2), col: ni % 2 === 0 ? "left" : "right" });
              } else { exitZoneMode(); toast.success("Zone scoring complete."); }
            }
            return;
          }

          // V — promote scope to Vis, or toggle Vis (when scope is "cell")
          if (!shift && !ctrl && UP === "V") {
            e.preventDefault();
            if (zoneModeScope !== "cell") {
              const anchor: ZoneCell =
                zoneModeScope === "row" ? { row: zoneModeCursor.row, col: "left" } :
                zoneModeScope === "col" ? { row: 0, col: zoneModeCursor.col } :
                { row: 0, col: "left" };
              const newCursor: ZoneCell =
                zoneModeScope === "row" ? { row: zoneModeCursor.row, col: "right" } :
                zoneModeScope === "col" ? { row: zmZones.length - 1, col: zoneModeCursor.col } :
                { row: zmZones.length - 1, col: "right" };
              setZoneModeAnchor(anchor); setZoneModeCursor(newCursor);
              setZoneModeVisual(true); setZoneModeScope("cell");
            } else {
              if (zoneModeVisual) { setZoneModeVisual(false); setZoneModeAnchor(null); }
              else { setZoneModeAnchor(zoneModeCursor); setZoneModeVisual(true); }
            }
            return;
          }

          // Ctrl+A — toggle: full range ↔ Cell (both in scope and Vis modes)
          if (ctrl && !shift && UP === "A") {
            e.preventDefault();
            if (zoneModeVisual) {
              const isAllSel =
                zoneModeAnchor?.row === 0 && zoneModeAnchor?.col === "left" &&
                zoneModeCursor?.row === zmZones.length - 1 && zoneModeCursor?.col === "right";
              if (isAllSel) { setZoneModeAnchor(zoneModeCursor); }
              else { setZoneModeAnchor({ row: 0, col: "left" }); setZoneModeCursor({ row: zmZones.length - 1, col: "right" }); }
            } else if (zoneModeScope === "all") {
              setZoneModeScope("cell");
            } else {
              setZoneModeScope("all");
            }
            return;
          }

          // Shift+digit — scope "row" N (not Vis) or visual row N (Vis)
          if (shift && !ctrl && e.code.startsWith("Digit")) {
            const row = parseInt(e.code.slice(5)) - 1;
            if (row >= 0 && row < zmZones.length) {
              e.preventDefault();
              if (zoneModeVisual) {
                setZoneModeAnchor({ row, col: "left" }); setZoneModeCursor({ row, col: "right" });
              } else {
                setZoneModeScope("row"); setZoneModeCursor({ row, col: "left" });
              }
              return;
            }
          }

          // < / > — scope "col" (not Vis) or visual col (Vis)
          if (!ctrl && (key === "<" || key === ">")) {
            e.preventDefault();
            const col: "left" | "right" = key === "<" ? "left" : "right";
            if (zoneModeVisual) {
              setZoneModeAnchor({ row: 0, col }); setZoneModeCursor({ row: zmZones.length - 1, col });
            } else {
              setZoneModeScope("col"); setZoneModeCursor(c => c ? { ...c, col } : c);
            }
            return;
          }

          // Directional navigation — arrow keys and/or hjkl depending on navMode
          if (!ctrl) {
            if (nav.up(e, navMode)) {
              e.preventDefault();
              if (zoneModeScope === "cell" || zoneModeScope === "row")
                setZoneModeCursor(c => c && c.row > 0 ? { ...c, row: c.row - 1 } : c);
              return;
            }
            if (nav.shiftUp(e, navMode)) {
              e.preventDefault();
              if (zoneModeScope === "cell" || zoneModeScope === "row")
                setZoneModeCursor(c => c ? { ...c, row: 0 } : c);
              return;
            }
            if (nav.down(e, navMode)) {
              e.preventDefault();
              if (zoneModeScope === "cell" || zoneModeScope === "row")
                setZoneModeCursor(c => c && c.row < zmZones.length - 1 ? { ...c, row: c.row + 1 } : c);
              return;
            }
            if (nav.shiftDown(e, navMode)) {
              e.preventDefault();
              if (zoneModeScope === "cell" || zoneModeScope === "row")
                setZoneModeCursor(c => c ? { ...c, row: zmZones.length - 1 } : c);
              return;
            }
            if (nav.left(e, navMode)) {
              e.preventDefault();
              if (zoneModeScope === "cell" || zoneModeScope === "col")
                setZoneModeCursor(c => c ? { ...c, col: "left" } : c);
              return;
            }
            if (nav.right(e, navMode)) {
              e.preventDefault();
              if (zoneModeScope === "cell" || zoneModeScope === "col")
                setZoneModeCursor(c => c ? { ...c, col: "right" } : c);
              return;
            }
          }

          // 0 / Del / Backspace — clear current scope or Vis selection back to null
          if (!shift && !ctrl && (key === "0" || key === "Delete" || key === "Backspace")) {
            e.preventDefault();
            if (zoneModeVisual && zoneModeAnchor) {
              const rMin = Math.min(zoneModeAnchor.row, zoneModeCursor.row);
              const rMax = Math.max(zoneModeAnchor.row, zoneModeCursor.row);
              const selCols = new Set([zoneModeAnchor.col, zoneModeCursor.col]);
              const cols = (["left", "right"] as const).filter((c) => selCols.has(c));
              for (let r = rMin; r <= rMax; r++)
                for (const col of cols)
                  setScore(zmImg.uuid, `${zmZones[r]}_${col}_score`, null);
            } else if (zoneModeScope === "row") {
              setScore(zmImg.uuid, `${zmZones[zoneModeCursor.row]}_left_score`, null);
              setScore(zmImg.uuid, `${zmZones[zoneModeCursor.row]}_right_score`, null);
            } else if (zoneModeScope === "col") {
              for (let r = 0; r < zmZones.length; r++)
                setScore(zmImg.uuid, `${zmZones[r]}_${zoneModeCursor.col}_score`, null);
            } else if (zoneModeScope === "all") {
              for (let r = 0; r < zmZones.length; r++) {
                setScore(zmImg.uuid, `${zmZones[r]}_left_score`, null);
                setScore(zmImg.uuid, `${zmZones[r]}_right_score`, null);
              }
            } else {
              setScore(zmImg.uuid, `${zmZones[zoneModeCursor.row]}_${zoneModeCursor.col}_score`, null);
            }
            return;
          }

          // N — focus slice notes (Zone Mode stays active)
          if (!shift && !ctrl && UP === "N") { e.preventDefault(); sliceNotesRef.current?.focus(); return; }
          // Z — exit Zone Mode entirely
          if (!shift && !ctrl && UP === "Z") { e.preventDefault(); exitZoneMode(); return; }
        }
        return; // consume unrecognized keys while in Zone Mode
      }

      // Below shortcuts only in annotate mode, no modifier keys
      if (isReadMode || isPreviewMode || ctrl || shift) return;

      const currentImg = useLabelStore.getState().currentImage();

      // N — focus Image Set Notes
      if (UP === "N") {
        e.preventDefault();
        if (wideMode && wideModeTab === "annotation") {
          setWideModeTab("evaluation");
          setTimeout(() => setLevelNotesRef.current?.focus(), 0);
        } else {
          setLevelNotesRef.current?.focus();
        }
        return;
      }

      // P — toggle Wide Image Panel Mode
      if (UP === "P") { e.preventDefault(); setWideMode(v => !v); return; }

      // Z — activate Zone Mode | V — activate Zone Mode directly in Visual
      if ((UP === "Z" || UP === "V") && currentImg && useLabelStore.getState().aspectsEnabled()) {
        const region = useLabelStore.getState().slices[currentImg.uuid]?.region;
        if (region === "BasalGanglia" || region === "CoronaRadiata") {
          activateZoneMode(currentImg.uuid, region, UP === "V");
          return;
        }
      }
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isReadMode, isPreviewMode, queue, queuePos, showManagementBoard, submitDialogMode,
      confirmReset, confirmExit, handleSaveDraft, handleBatchAction, handleExit, handleResetAll,
      setUsability, setLowQuality, setRegion, mbActiveCol, selectedBoardSetUuid, rightTab,
      zoneModeActive, zoneModeCursor]);

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

      {/* ── Image viewer — 40% normal, 70% preview/wide ── */}
      <div className={`${isPreviewMode ? "w-[70%]" : wideMode ? "w-[70%]" : "w-[40%]"} bg-black relative flex items-center justify-center overflow-hidden shrink-0`}>
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
        {!isPreviewMode && (
          <button
            type="button"
            className="absolute bottom-3 right-3 z-10 flex items-center gap-1.5 rounded-lg bg-black/60 hover:bg-black/80 text-white px-2.5 py-1.5 transition-colors"
            onClick={() => setWideMode(v => !v)}
          >
            {wideMode ? <ChevronLeft className="h-4 w-4 shrink-0" /> : <ChevronRight className="h-4 w-4 shrink-0" />}
            <span className="text-xs font-medium">{wideMode ? "Collapse" : "Wide Mode"}</span>
            {showKbdHints && <kbd className="font-mono border border-white/30 bg-white/10 px-1 py-0.5 rounded text-xs leading-none">P</kbd>}
          </button>
        )}
      </div>

      {/* ── Side panels — collapse into tabs in Wide Mode ── */}
      {!isPreviewMode && (
        wideMode ? (
          <div className="w-[30%] flex flex-col border-l border-border bg-background shrink-0 overflow-hidden">
            {/* Wide Mode tab bar */}
            <div className="flex items-center border-b border-border shrink-0">
              {(["annotation", "evaluation"] as const).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => handleWideModeTabClick(tab)}
                  className={`px-3 py-1.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap ${
                    wideModeTab === tab
                      ? "border-primary text-foreground"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {tab === "annotation" ? "Image Annotation" : "Image Set Evaluation"}
                </button>
              ))}
              {showKbdHints && <kbd className="ml-auto font-mono border border-primary/50 bg-background text-primary px-1.5 py-0.5 rounded text-xs leading-none shrink-0 mr-2">Shift+P</kbd>}
            </div>
            {/* Active tab content */}
            {wideModeTab === "annotation" ? (
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
                        <WithTooltip content={<span className="flex items-center gap-2"><span>Previous image</span><NavKbd dir="left" /></span>} side="top">
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
                        <WithTooltip content={<span className="flex items-center gap-2"><span>Jump to image</span><TooltipKbd>I</TooltipKbd></span>} side="top">
                          <Input
                            ref={jumpImgInputRef}
                            type="number"
                            className={`h-8 w-16 text-center text-base ${NO_SPINNER}`}
                            value={jumpImgInput}
                            onChange={(e) => setJumpImgInput(e.target.value)}
                            onBlur={(e) => { if (!skipJumpImgApplyRef.current) applyJumpImage(e.target.value); skipJumpImgApplyRef.current = false; }}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") { applyJumpImage(jumpImgInput); e.currentTarget.blur(); }
                              else if (e.key === "Escape") { skipJumpImgApplyRef.current = true; setJumpImgInput(String(currentIndex + 1)); e.currentTarget.blur(); }
                            }}
                            min={1} max={images.length}
                          />
                        </WithTooltip>
                        <span className="text-base text-muted-foreground shrink-0">of {images.length}</span>
                        <WithTooltip content={<span className="flex items-center gap-2"><span>Next image</span><NavKbd dir="right" /></span>} side="top">
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
                          <span className="text-xs text-muted-foreground leading-none">Jump to Image</span>
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
                      <WithTooltip content={<span className="flex items-center gap-2"><span>Focus Window Level</span><TooltipKbd>W</TooltipKbd></span>} side="top">
                        <div className="flex items-center gap-2">
                          <Label className="text-base text-muted-foreground shrink-0 cursor-default">WL</Label>
                          <Input
                            ref={wlInputRef}
                            type="number"
                            className={`h-7 w-16 text-base ${NO_SPINNER}`}
                            value={wlInput}
                            onChange={(e) => setWlInput(e.target.value)}
                            onBlur={() => { if (!skipWindowApplyRef.current) applyWindow(); skipWindowApplyRef.current = false; }}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") { applyWindow(); e.currentTarget.blur(); }
                              else if (e.key === "Escape") { skipWindowApplyRef.current = true; setWlInput(String(windowLevel)); e.currentTarget.blur(); }
                              else if (e.key === "Tab") { e.preventDefault(); wwInputRef.current?.focus(); wwInputRef.current?.select(); }
                            }}
                          />
                        </div>
                      </WithTooltip>
                      <WithTooltip content={<span className="flex items-center gap-2"><span>Focus Window Width</span><span className="flex items-center gap-1"><TooltipKbd>W</TooltipKbd><TooltipKbd>Tab</TooltipKbd></span></span>} side="top">
                        <div className="flex items-center gap-2">
                          <Label className="text-base text-muted-foreground shrink-0 cursor-default">WW</Label>
                          <Input
                            ref={wwInputRef}
                            type="number"
                            className={`h-7 w-16 text-base ${NO_SPINNER}`}
                            value={wwInput}
                            onChange={(e) => setWwInput(e.target.value)}
                            onBlur={() => { if (!skipWindowApplyRef.current) applyWindow(); skipWindowApplyRef.current = false; }}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") { applyWindow(); e.currentTarget.blur(); }
                              else if (e.key === "Escape") { skipWindowApplyRef.current = true; setWwInput(String(windowWidth)); e.currentTarget.blur(); }
                              else if (e.key === "Tab") { e.preventDefault(); wlInputRef.current?.focus(); wlInputRef.current?.select(); }
                            }}
                          />
                        </div>
                      </WithTooltip>
                      <WithTooltip content={<span className="flex items-center gap-2"><span>Reset to WL {defaultWindowLevel} / WW {defaultWindowWidth}</span><TooltipKbd>Shift+W</TooltipKbd></span>} side="top">
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
                      <SliceEvaluation
                        imageUuid={currentImg.uuid}
                        readOnly={isReadMode}
                        zoneModeCell={zoneModeActive ? zoneModeCursor : null}
                        zoneModeAnchor={zoneModeActive && zoneModeVisual ? zoneModeAnchor : null}
                        zoneModeScope={zoneModeActive ? zoneModeScope : undefined}
                        onExitZoneMode={zoneModeActive ? exitZoneMode : undefined}
                        sliceNotesRef={sliceNotesRef}
                      />
                    ) : (
                      <p className="text-base text-muted-foreground">No image loaded</p>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <>
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
                          <WithTooltip content={<span className="flex items-center gap-2"><span>Previous image set</span><NavKbd dir="shiftLeft" /></span>} side="top">
                            <Button
                              variant="outline" size="icon" className="h-8 w-8 shrink-0"
                              disabled={navigating}
                              onClick={() => goToSet(queue[(queuePos - 1 + queue.length) % queue.length])}
                            >
                              <ChevronLeft className="h-4 w-4" />
                            </Button>
                          </WithTooltip>
                          <WithTooltip content={<span className="flex items-center gap-2"><span>Jump to set</span><TooltipKbd>Shift+I</TooltipKbd></span>} side="top">
                            <Input
                              ref={jumpSetInputRef}
                              type="number"
                              className={`h-8 w-14 text-center text-base ${NO_SPINNER}`}
                              value={jumpSetInput}
                              onChange={(e) => setJumpSetInput(e.target.value)}
                              onBlur={(e) => { if (!skipJumpSetApplyRef.current) applyJumpSet(e.target.value); skipJumpSetApplyRef.current = false; }}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") { applyJumpSet(jumpSetInput); e.currentTarget.blur(); }
                                else if (e.key === "Escape") { skipJumpSetApplyRef.current = true; setJumpSetInput(String(queuePos + 1)); e.currentTarget.blur(); }
                              }}
                              min={1} max={queue.length}
                            />
                          </WithTooltip>
                          <span className="text-sm text-muted-foreground shrink-0">of {queue.length}</span>
                          <WithTooltip content={<span className="flex items-center gap-2"><span>Next image set</span><NavKbd dir="shiftRight" /></span>} side="top">
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
                      <div className="flex items-center border-b border-border">
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
                        {showKbdHints && <kbd className="ml-auto font-mono border border-primary/50 bg-background text-primary px-1.5 py-0.5 rounded text-xs leading-none shrink-0">Shift+Tab</kbd>}
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
                                ? new Date(annotationMeta.timestamp).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Bangkok" })
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
                      <SetLevelEvaluation readOnly={isReadMode} notesRef={setLevelNotesRef} zoneMode={zoneModeActive} />
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
                      <WithTooltip content={<span className="flex items-center gap-2"><span>Toggle Management Board</span><TooltipKbd>M</TooltipKbd></span>} side="top">
                        <Button
                          variant="outline"
                          className="w-full gap-2 border-foreground text-foreground font-semibold"
                          onClick={() => setShowManagementBoard(true)}
                        >
                          <ClipboardList className="h-4 w-4" />
                          Management Board
                        </Button>
                      </WithTooltip>
                      <WithTooltip content={<span className="flex items-center gap-2"><span>Exit to Dashboard</span><TooltipKbd>Shift+Esc</TooltipKbd></span>} side="top">
                        <Button
                          className="w-full gap-2 bg-purple-600 hover:bg-purple-700 text-white"
                          onClick={handleExit}
                        >
                          <ArrowLeft className="h-4 w-4" />
                          {isAdminRead ? "Return to Submissions" : "Return to Dashboard"}
                        </Button>
                      </WithTooltip>
                    </>
                  ) : (
                    <>
                      <ValidationStatus />
                      <div className="flex gap-2">
                        <WithTooltip content={<span className="flex items-center gap-2"><span>Toggle Management Board</span><TooltipKbd>M</TooltipKbd></span>} side="top">
                          <Button
                            variant="outline"
                            className="flex-1 gap-2 border-foreground text-foreground font-semibold"
                            onClick={() => setShowManagementBoard(true)}
                          >
                            <ClipboardList className="h-4 w-4" />
                            Management Board
                          </Button>
                        </WithTooltip>
                        <WithTooltip content={<span className="flex items-center gap-2"><span>AI Assist (In Development)</span><TooltipKbd>Shift+A</TooltipKbd></span>} side="top">
                          <span className="flex-1">
                            <Button
                              variant="outline"
                              className="w-full gap-2"
                              disabled
                            >
                              <Bot className="h-4 w-4" />
                              AI Assist (In Development)
                            </Button>
                          </span>
                        </WithTooltip>
                      </div>
                      <div className="flex gap-2">
                        <WithTooltip content={<span className="flex items-center gap-2"><span>Save draft</span><TooltipKbd>Ctrl+S</TooltipKbd></span>} side="top">
                          <Button
                            className="flex-1 gap-2 bg-yellow-500 hover:bg-yellow-600 text-black"
                            disabled={savingDraft || submitting}
                            onClick={handleSaveDraft}
                          >
                            <Save className="h-4 w-4" />
                            {savingDraft ? "Saving…" : "Save Draft"}
                          </Button>
                        </WithTooltip>
                        <WithTooltip content={<span className="flex items-center gap-2"><span>Submit annotation</span><TooltipKbd>Ctrl+Enter</TooltipKbd></span>} side="top">
                          <Button
                            className="flex-1 gap-2"
                            disabled={!anyReady || submitting || navigating}
                            onClick={() => setSubmitDialogMode(allReady ? "all-ready" : "partial-ready")}
                          >
                            <Send className="h-4 w-4" />
                            {submitting ? "Submitting…" : anyReady ? "Submit Annotation" : "Not Ready"}
                          </Button>
                        </WithTooltip>
                      </div>
                      <div className="flex gap-2">
                        <WithTooltip content={<span className="flex items-center gap-2"><span>Exit to Dashboard</span><TooltipKbd>Shift+Esc</TooltipKbd></span>} side="top">
                          <Button
                            className="flex-1 gap-2 bg-purple-600 hover:bg-purple-700 text-white"
                            onClick={handleExit}
                          >
                            <ArrowLeft className="h-4 w-4" />
                            Exit to Dashboard
                          </Button>
                        </WithTooltip>
                        <WithTooltip content={<span className="flex items-center gap-2"><span>Reset all annotations</span><TooltipKbd>Shift+Del</TooltipKbd></span>} side="top">
                          <Button
                            variant="ghost"
                            className="flex-1 gap-2 text-destructive hover:text-destructive"
                            onClick={() => setConfirmReset(true)}
                          >
                            <Trash2 className="h-4 w-4" />
                            Reset All Annotations
                          </Button>
                        </WithTooltip>
                      </div>
                    </>
                  )}
                </div>
              </>
            )}
          </div>
        ) : (
          <>
            {/* Normal layout: two 30% panels */}
            <div className="w-[30%] flex flex-col border-l border-border bg-background shrink-0 overflow-hidden">
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
                        <WithTooltip content={<span className="flex items-center gap-2"><span>Previous image</span><NavKbd dir="left" /></span>} side="top">
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
                        <WithTooltip content={<span className="flex items-center gap-2"><span>Jump to image</span><TooltipKbd>I</TooltipKbd></span>} side="top">
                          <Input
                            ref={jumpImgInputRef}
                            type="number"
                            className={`h-8 w-16 text-center text-base ${NO_SPINNER}`}
                            value={jumpImgInput}
                            onChange={(e) => setJumpImgInput(e.target.value)}
                            onBlur={(e) => { if (!skipJumpImgApplyRef.current) applyJumpImage(e.target.value); skipJumpImgApplyRef.current = false; }}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") { applyJumpImage(jumpImgInput); e.currentTarget.blur(); }
                              else if (e.key === "Escape") { skipJumpImgApplyRef.current = true; setJumpImgInput(String(currentIndex + 1)); e.currentTarget.blur(); }
                            }}
                            min={1} max={images.length}
                          />
                        </WithTooltip>
                        <span className="text-base text-muted-foreground shrink-0">of {images.length}</span>
                        <WithTooltip content={<span className="flex items-center gap-2"><span>Next image</span><NavKbd dir="right" /></span>} side="top">
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
                          <span className="text-xs text-muted-foreground leading-none">Jump to Image</span>
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
                      <WithTooltip content={<span className="flex items-center gap-2"><span>Focus Window Level</span><TooltipKbd>W</TooltipKbd></span>} side="top">
                        <div className="flex items-center gap-2">
                          <Label className="text-base text-muted-foreground shrink-0 cursor-default">WL</Label>
                          <Input
                            ref={wlInputRef}
                            type="number"
                            className={`h-7 w-16 text-base ${NO_SPINNER}`}
                            value={wlInput}
                            onChange={(e) => setWlInput(e.target.value)}
                            onBlur={() => { if (!skipWindowApplyRef.current) applyWindow(); skipWindowApplyRef.current = false; }}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") { applyWindow(); e.currentTarget.blur(); }
                              else if (e.key === "Escape") { skipWindowApplyRef.current = true; setWlInput(String(windowLevel)); e.currentTarget.blur(); }
                              else if (e.key === "Tab") { e.preventDefault(); wwInputRef.current?.focus(); wwInputRef.current?.select(); }
                            }}
                          />
                        </div>
                      </WithTooltip>
                      <WithTooltip content={<span className="flex items-center gap-2"><span>Focus Window Width</span><span className="flex items-center gap-1"><TooltipKbd>W</TooltipKbd><TooltipKbd>Tab</TooltipKbd></span></span>} side="top">
                        <div className="flex items-center gap-2">
                          <Label className="text-base text-muted-foreground shrink-0 cursor-default">WW</Label>
                          <Input
                            ref={wwInputRef}
                            type="number"
                            className={`h-7 w-16 text-base ${NO_SPINNER}`}
                            value={wwInput}
                            onChange={(e) => setWwInput(e.target.value)}
                            onBlur={() => { if (!skipWindowApplyRef.current) applyWindow(); skipWindowApplyRef.current = false; }}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") { applyWindow(); e.currentTarget.blur(); }
                              else if (e.key === "Escape") { skipWindowApplyRef.current = true; setWwInput(String(windowWidth)); e.currentTarget.blur(); }
                              else if (e.key === "Tab") { e.preventDefault(); wlInputRef.current?.focus(); wlInputRef.current?.select(); }
                            }}
                          />
                        </div>
                      </WithTooltip>
                      <WithTooltip content={<span className="flex items-center gap-2"><span>Reset to WL {defaultWindowLevel} / WW {defaultWindowWidth}</span><TooltipKbd>Shift+W</TooltipKbd></span>} side="top">
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
                      <SliceEvaluation
                        imageUuid={currentImg.uuid}
                        readOnly={isReadMode}
                        zoneModeCell={zoneModeActive ? zoneModeCursor : null}
                        zoneModeAnchor={zoneModeActive && zoneModeVisual ? zoneModeAnchor : null}
                        zoneModeScope={zoneModeActive ? zoneModeScope : undefined}
                        onExitZoneMode={zoneModeActive ? exitZoneMode : undefined}
                        sliceNotesRef={sliceNotesRef}
                      />
                    ) : (
                      <p className="text-base text-muted-foreground">No image loaded</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
            <div className="w-[30%] flex flex-col border-l border-border bg-background shrink-0 overflow-hidden">
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
                        <WithTooltip content={<span className="flex items-center gap-2"><span>Previous image set</span><NavKbd dir="shiftLeft" /></span>} side="top">
                          <Button
                            variant="outline" size="icon" className="h-8 w-8 shrink-0"
                            disabled={navigating}
                            onClick={() => goToSet(queue[(queuePos - 1 + queue.length) % queue.length])}
                          >
                            <ChevronLeft className="h-4 w-4" />
                          </Button>
                        </WithTooltip>
                        <WithTooltip content={<span className="flex items-center gap-2"><span>Jump to set</span><TooltipKbd>Shift+I</TooltipKbd></span>} side="top">
                          <Input
                            ref={jumpSetInputRef}
                            type="number"
                            className={`h-8 w-14 text-center text-base ${NO_SPINNER}`}
                            value={jumpSetInput}
                            onChange={(e) => setJumpSetInput(e.target.value)}
                            onBlur={(e) => { if (!skipJumpSetApplyRef.current) applyJumpSet(e.target.value); skipJumpSetApplyRef.current = false; }}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") { applyJumpSet(jumpSetInput); e.currentTarget.blur(); }
                              else if (e.key === "Escape") { skipJumpSetApplyRef.current = true; setJumpSetInput(String(queuePos + 1)); e.currentTarget.blur(); }
                            }}
                            min={1} max={queue.length}
                          />
                        </WithTooltip>
                        <span className="text-sm text-muted-foreground shrink-0">of {queue.length}</span>
                        <WithTooltip content={<span className="flex items-center gap-2"><span>Next image set</span><NavKbd dir="shiftRight" /></span>} side="top">
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
                    <div className="flex items-center border-b border-border">
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
                      {showKbdHints && <kbd className="ml-auto font-mono border border-primary/50 bg-background text-primary px-1.5 py-0.5 rounded text-xs leading-none shrink-0">Shift+Tab</kbd>}
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
                              ? new Date(annotationMeta.timestamp).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Bangkok" })
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
                    <SetLevelEvaluation readOnly={isReadMode} notesRef={setLevelNotesRef} zoneMode={zoneModeActive} />
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
                    <WithTooltip content={<span className="flex items-center gap-2"><span>Toggle Management Board</span><TooltipKbd>M</TooltipKbd></span>} side="top">
                      <Button
                        variant="outline"
                        className="w-full gap-2 border-foreground text-foreground font-semibold"
                        onClick={() => setShowManagementBoard(true)}
                      >
                        <ClipboardList className="h-4 w-4" />
                        Management Board
                      </Button>
                    </WithTooltip>
                    <WithTooltip content={<span className="flex items-center gap-2"><span>Exit to Dashboard</span><TooltipKbd>Shift+Esc</TooltipKbd></span>} side="top">
                      <Button
                        className="w-full gap-2 bg-purple-600 hover:bg-purple-700 text-white"
                        onClick={handleExit}
                      >
                        <ArrowLeft className="h-4 w-4" />
                        {isAdminRead ? "Return to Submissions" : "Return to Dashboard"}
                      </Button>
                    </WithTooltip>
                  </>
                ) : (
                  <>
                    <ValidationStatus />
                    <div className="flex gap-2">
                      <WithTooltip content={<span className="flex items-center gap-2"><span>Toggle Management Board</span><TooltipKbd>M</TooltipKbd></span>} side="top">
                        <Button
                          variant="outline"
                          className="flex-1 gap-2 border-foreground text-foreground font-semibold"
                          onClick={() => setShowManagementBoard(true)}
                        >
                          <ClipboardList className="h-4 w-4" />
                          Management Board
                        </Button>
                      </WithTooltip>
                      <WithTooltip content={<span className="flex items-center gap-2"><span>AI Assist (In Development)</span><TooltipKbd>Shift+A</TooltipKbd></span>} side="top">
                        <span>
                          <Button
                            variant="outline"
                            className="flex-1 gap-2"
                            disabled
                          >
                            <Bot className="h-4 w-4" />
                            AI Assist (In Development)
                          </Button>
                        </span>
                      </WithTooltip>
                    </div>
                    <div className="flex gap-2">
                      <WithTooltip content={<span className="flex items-center gap-2"><span>Save draft</span><TooltipKbd>Ctrl+S</TooltipKbd></span>} side="top">
                        <Button
                          className="flex-1 gap-2 bg-yellow-500 hover:bg-yellow-600 text-black"
                          disabled={savingDraft || submitting}
                          onClick={handleSaveDraft}
                        >
                          <Save className="h-4 w-4" />
                          {savingDraft ? "Saving…" : "Save Draft"}
                        </Button>
                      </WithTooltip>
                      <WithTooltip content={<span className="flex items-center gap-2"><span>Submit annotation</span><TooltipKbd>Ctrl+Enter</TooltipKbd></span>} side="top">
                        <Button
                          className="flex-1 gap-2"
                          disabled={!anyReady || submitting || navigating}
                          onClick={() => setSubmitDialogMode(allReady ? "all-ready" : "partial-ready")}
                        >
                          <Send className="h-4 w-4" />
                          {submitting ? "Submitting…" : anyReady ? "Submit Annotation" : "Not Ready"}
                        </Button>
                      </WithTooltip>
                    </div>
                    <div className="flex gap-2">
                      <WithTooltip content={<span className="flex items-center gap-2"><span>Exit to Dashboard</span><TooltipKbd>Shift+Esc</TooltipKbd></span>} side="top">
                        <Button
                          className="flex-1 gap-2 bg-purple-600 hover:bg-purple-700 text-white"
                          onClick={handleExit}
                        >
                          <ArrowLeft className="h-4 w-4" />
                          Exit to Dashboard
                        </Button>
                      </WithTooltip>
                      <WithTooltip content={<span className="flex items-center gap-2"><span>Reset all annotations</span><TooltipKbd>Shift+Del</TooltipKbd></span>} side="top">
                        <Button
                          variant="ghost"
                          className="flex-1 gap-2 text-destructive hover:text-destructive"
                          onClick={() => setConfirmReset(true)}
                        >
                          <Trash2 className="h-4 w-4" />
                          Reset All Annotations
                        </Button>
                      </WithTooltip>
                    </div>
                  </>
                )}
              </div>
            </div>
          </>
        )
      )}

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
                    <WithTooltip content={<span className="flex items-center gap-2"><span>Previous image set</span><NavKbd dir="shiftLeft" /></span>} side="top">
                      <Button variant="outline" size="icon" className="h-8 w-8 shrink-0" disabled={navigating}
                        onClick={() => goToSet(queue[(queuePos - 1 + queue.length) % queue.length])}>
                        <ChevronLeft className="h-4 w-4" />
                      </Button>
                    </WithTooltip>
                    <WithTooltip content={<span className="flex items-center gap-2"><span>Jump to set</span><TooltipKbd>Shift+I</TooltipKbd></span>} side="top">
                      <Input ref={jumpSetInputRef} type="number" className={`h-8 w-14 text-center text-base ${NO_SPINNER}`}
                        value={jumpSetInput}
                        onChange={(e) => setJumpSetInput(e.target.value)}
                        onBlur={(e) => { if (!skipJumpSetApplyRef.current) applyJumpSet(e.target.value); skipJumpSetApplyRef.current = false; }}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") { applyJumpSet(jumpSetInput); e.currentTarget.blur(); }
                          else if (e.key === "Escape") { skipJumpSetApplyRef.current = true; setJumpSetInput(String(queuePos + 1)); e.currentTarget.blur(); }
                        }}
                        min={1} max={queue.length} />
                    </WithTooltip>
                    <span className="text-sm text-muted-foreground shrink-0">of {queue.length}</span>
                    <WithTooltip content={<span className="flex items-center gap-2"><span>Next image set</span><NavKbd dir="shiftRight" /></span>} side="top">
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
                    <WithTooltip content={<span className="flex items-center gap-2"><span>Previous image</span><NavKbd dir="left" /></span>} side="top">
                      <Button variant="outline" size="icon" className="h-8 w-8 shrink-0"
                        onClick={() => { const n = (currentIndex - 1 + images.length) % images.length; setCurrentIndex(n); setJumpImgInput(String(n + 1)); }}>
                        <ChevronLeft className="h-4 w-4" />
                      </Button>
                    </WithTooltip>
                    <WithTooltip content={<span className="flex items-center gap-2"><span>Jump to image</span><TooltipKbd>I</TooltipKbd></span>} side="top">
                      <Input type="number" className={`h-8 w-16 text-center text-base ${NO_SPINNER}`}
                        ref={jumpImgInputRef}
                        value={jumpImgInput}
                        onChange={(e) => setJumpImgInput(e.target.value)}
                        onBlur={(e) => { if (!skipJumpImgApplyRef.current) applyJumpImage(e.target.value); skipJumpImgApplyRef.current = false; }}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") { applyJumpImage(jumpImgInput); e.currentTarget.blur(); }
                          else if (e.key === "Escape") { skipJumpImgApplyRef.current = true; setJumpImgInput(String(currentIndex + 1)); e.currentTarget.blur(); }
                        }}
                        min={1} max={images.length} />
                    </WithTooltip>
                    <span className="text-base text-muted-foreground shrink-0">of {images.length}</span>
                    <WithTooltip content={<span className="flex items-center gap-2"><span>Next image</span><NavKbd dir="right" /></span>} side="top">
                      <Button variant="outline" size="icon" className="h-8 w-8 shrink-0"
                        onClick={() => { const n = (currentIndex + 1) % images.length; setCurrentIndex(n); setJumpImgInput(String(n + 1)); }}>
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </WithTooltip>
                    <div className="flex-1 min-w-0 flex flex-col gap-0.5">
                      <span className="text-xs text-muted-foreground leading-none">Jump to Image</span>
                      <input type="range" min={1} max={images.length} value={currentIndex + 1}
                        onChange={(e) => { const n = parseInt(e.target.value); setCurrentIndex(n - 1); setJumpImgInput(String(n)); }}
                        className="w-full cursor-pointer accent-primary" />
                    </div>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <WithTooltip content={<span className="flex items-center gap-2"><span>Focus Window Level</span><TooltipKbd>W</TooltipKbd></span>} side="top">
                    <div className="flex items-center gap-2">
                      <Label className="text-base text-muted-foreground shrink-0 cursor-default">WL</Label>
                      <Input ref={wlInputRef} type="number" className={`h-7 w-16 text-base ${NO_SPINNER}`} value={wlInput}
                        onChange={(e) => setWlInput(e.target.value)}
                        onBlur={() => { if (!skipWindowApplyRef.current) applyWindow(); skipWindowApplyRef.current = false; }}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") { applyWindow(); e.currentTarget.blur(); }
                          else if (e.key === "Escape") { skipWindowApplyRef.current = true; setWlInput(String(windowLevel)); e.currentTarget.blur(); }
                          else if (e.key === "Tab") { e.preventDefault(); wwInputRef.current?.focus(); wwInputRef.current?.select(); }
                        }} />
                    </div>
                  </WithTooltip>
                  <WithTooltip content={<span className="flex items-center gap-2"><span>Focus Window Width</span><span className="flex items-center gap-1"><TooltipKbd>W</TooltipKbd><TooltipKbd>Tab</TooltipKbd></span></span>} side="top">
                    <div className="flex items-center gap-2">
                      <Label className="text-base text-muted-foreground shrink-0 cursor-default">WW</Label>
                      <Input ref={wwInputRef} type="number" className={`h-7 w-16 text-base ${NO_SPINNER}`} value={wwInput}
                        onChange={(e) => setWwInput(e.target.value)}
                        onBlur={() => { if (!skipWindowApplyRef.current) applyWindow(); skipWindowApplyRef.current = false; }}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") { applyWindow(); e.currentTarget.blur(); }
                          else if (e.key === "Escape") { skipWindowApplyRef.current = true; setWwInput(String(windowWidth)); e.currentTarget.blur(); }
                          else if (e.key === "Tab") { e.preventDefault(); wlInputRef.current?.focus(); wlInputRef.current?.select(); }
                        }} />
                    </div>
                  </WithTooltip>
                  <WithTooltip content={<span className="flex items-center gap-2"><span>Reset to WL {defaultWindowLevel} / WW {defaultWindowWidth}</span><TooltipKbd>Shift+W</TooltipKbd></span>} side="top">
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
            <WithTooltip content={<span className="flex items-center gap-2"><span>Toggle Management Board</span><TooltipKbd>M</TooltipKbd></span>} side="top">
              <Button variant="outline" className="w-full gap-2 border-foreground text-foreground font-semibold"
                onClick={() => setShowManagementBoard(true)}>
                <ClipboardList className="h-4 w-4" /> Management Board
              </Button>
            </WithTooltip>
            <WithTooltip content={<span className="flex items-center gap-2"><span>Exit to Dashboard</span><TooltipKbd>Shift+Esc</TooltipKbd></span>} side="top">
              <Button className="w-full gap-2 bg-purple-600 hover:bg-purple-700 text-white" onClick={handleExit}>
                <ArrowLeft className="h-4 w-4" /> Return to Dashboard
              </Button>
            </WithTooltip>
          </div>
        </div>
      )}

      {/* ── Submit dialog — all ready ── */}
      {submitDialogMode === "all-ready" && (
        <ConfirmDialog
          title="How do you want to save?"
          body={`All ${queue.length} image set(s) are ready to submit.`}
          buttons={[
            { label: "Yes, submit all",  onClick: () => handleBatchAction("submit-all"),  className: "bg-green-600 hover:bg-green-700 text-white" },
            { label: "Save Draft All",   onClick: () => handleBatchAction("draft-all"),   className: "bg-yellow-500 hover:bg-yellow-600 text-black" },
            { label: "Cancel",           onClick: () => setSubmitDialogMode(null),        className: "bg-red-600 hover:bg-red-700 text-white" },
          ]}
        />
      )}

      {/* ── Submit dialog — partial ready ── */}
      {submitDialogMode === "partial-ready" && (
        <ConfirmDialog
          title="How do you want to save?"
          body={`${queueReady.filter(Boolean).length} of ${queue.length} image set(s) ready.`}
          buttons={[
            { label: "Submit Ready, Draft Incompleted",  onClick: () => handleBatchAction("submit-ready-draft-incomplete"),  className: "bg-green-600 hover:bg-green-700 text-white" },
            { label: "Submit Ready, Drop Incompleted",   onClick: () => handleBatchAction("submit-ready-drop-incomplete"),   className: "bg-blue-600 hover:bg-blue-700 text-white" },
            { label: "Draft All",                        onClick: () => handleBatchAction("draft-all"),                      className: "bg-yellow-500 hover:bg-yellow-600 text-black" },
            { label: "Cancel",                           onClick: () => setSubmitDialogMode(null),                           className: "bg-red-600 hover:bg-red-700 text-white" },
          ]}
        />
      )}

      {/* ── Reset confirmation ── */}
      {confirmReset && (
        <ConfirmDialog
          title="Reset all annotations?"
          body="All scored zones, region selections, and notes for this session will be cleared. This cannot be undone."
          layout="horizontal"
          defaultFocusIndex={1}
          buttons={[
            {
              label: <span>Yes, Delete {showKbdHints && <kbd className="ml-1.5 rounded border border-red-300/40 bg-red-500/20 px-1 py-0.5 font-mono text-xs">Y</kbd>}</span>,
              onClick: () => { setConfirmReset(false); handleResetAll(); },
              className: "bg-red-600 hover:bg-red-700 text-white",
            },
            {
              label: <span>No, Cancel {showKbdHints && <kbd className="ml-1.5 rounded border border-blue-300/40 bg-blue-500/20 px-1 py-0.5 font-mono text-xs">N</kbd>}</span>,
              onClick: () => setConfirmReset(false),
              className: "bg-blue-600 hover:bg-blue-700 text-white",
            },
          ]}
        />
      )}

      {/* ── Exit / Nav intercept confirmation ── */}
      {confirmExit && (
        <ConfirmDialog
          title="Leave annotation?"
          body="Your latest changes have been auto-saved. You can keep or discard them."
          escIndex={2}
          buttons={[
            {
              label: <span className="flex items-center gap-2"><Save className="h-4 w-4" />{savingDraft ? "Saving…" : "Draft the latest changes"}</span>,
              onClick: async () => { setConfirmExit(false); await handleSaveDraft(); doNavigatePending(); },
              disabled: savingDraft,
              className: "bg-yellow-500 hover:bg-yellow-600 text-black",
            },
            {
              label: "Don't keep the latest changes",
              onClick: () => { setConfirmExit(false); doNavigatePending(true); },
              className: "",
            },
            {
              label: "Back to Annotation",
              onClick: () => { setConfirmExit(false); setPendingNavDest(null); },
              className: "bg-transparent hover:bg-muted text-muted-foreground",
            },
          ]}
        />
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
                  <thead className={`sticky top-0 bg-background border-b z-10 ${mbActiveCol === "left" ? "border-t-2 border-t-primary" : ""}`}>
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
                          onDoubleClick={() => {
                            const sameSet = uuid === imageSetUuid;
                            if (sameSet) { setShowManagementBoard(false); }
                            else { goToSet(uuid).then(() => setShowManagementBoard(false)); }
                          }}
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
                      <thead className={`sticky top-0 bg-background border-b z-10 ${mbActiveCol === "right" ? "border-t-2 border-t-primary" : ""}`}>
                        <tr>
                          <th className="px-3 py-2 text-left font-medium text-muted-foreground w-16">Image</th>
                          <th className="px-3 py-2 text-left font-medium text-muted-foreground w-28">Zone</th>
                          <th className="px-3 py-2 text-left font-medium text-muted-foreground">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {annotated.map(({ uuid, index }, rowIdx) => {
                          const s = mbSlices[uuid];
                          const missing = getMissingZones(s);
                          return (
                            <tr
                              key={uuid}
                              className={`cursor-pointer border-b hover:bg-muted/50 ${rowIdx === selectedMBImageIndex ? "bg-muted" : ""}`}
                              onClick={() => setSelectedMBImageIndex(rowIdx)}
                              onDoubleClick={() => {
                                const sameSet = selectedBoardSetUuid === imageSetUuid;
                                const jump = () => { setCurrentIndex(index); setShowManagementBoard(false); };
                                if (sameSet) jump();
                                else goToSet(selectedBoardSetUuid).then(jump);
                              }}
                            >
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
