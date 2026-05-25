/**
 * Annotation state machine for the LabelPage.
 *
 * Multi-set support: setRegistry persists per-set annotations when switching
 * between sets in a queue, so A→B→A restores A's work.
 *
 * Gating rule:
 *   ASPECTS scoring enabled ⟺ usability === "IschemicAssessable" && !lowQuality
 */

import { create } from "zustand";
import type {
  ImageRecord,
  ImageSet,
  ImageSetUsability,
  Region,
  RegionScore,
  SliceEvalState,
} from "@/lib/types";
import { ALL_ZONES, BASAL_ZONES, CORONA_ZONES } from "@/lib/types";

function emptyScores(): Record<string, RegionScore | null> {
  const scores: Record<string, RegionScore | null> = {};
  for (const zone of ALL_ZONES) {
    scores[`${zone}_left_score`] = null;
    scores[`${zone}_right_score`] = null;
  }
  return scores;
}

function emptySlice(): SliceEvalState {
  return { region: "None", scores: emptyScores(), notes: "" };
}

function relevantScoreKeys(region: Region): string[] {
  if (region === "None") return [];
  const zones = region === "BasalGanglia" ? BASAL_ZONES : CORONA_ZONES;
  return zones.flatMap((z) => [`${z}_left_score`, `${z}_right_score`]);
}

function isSliceValid(state: SliceEvalState): boolean {
  if (state.region === "None") return true;
  const keys = relevantScoreKeys(state.region);
  return keys.every((k) => state.scores[k] !== null);
}

interface SetSnapshot {
  usability: ImageSetUsability | null;
  lowQuality: boolean;
  setNotes: string;
  slices: Record<string, SliceEvalState>;
  currentIndex: number;
}

interface LabelStore {
  // Per-set registry — persists annotations across set switches
  setRegistry: Record<string, SetSnapshot>;

  // Current set data
  imageSet: ImageSet | null;
  images: ImageRecord[];
  annotationSessionUuid: string | null;

  // Set-level state
  usability: ImageSetUsability | null;
  lowQuality: boolean;
  setNotes: string;

  // Per-slice state (keyed by image UUID)
  slices: Record<string, SliceEvalState>;

  // UI state
  currentIndex: number;
  windowLevel: number;
  windowWidth: number;
  defaultWindowLevel: number;
  defaultWindowWidth: number;

  // Actions — load
  loadImageSet: (imageSet: ImageSet, images: ImageRecord[], sessionUuid: string) => void;
  reset: () => void;

  // Actions — set level
  setUsability: (u: ImageSetUsability) => void;
  setLowQuality: (lq: boolean) => void;
  setSetNotes: (n: string) => void;

  // Actions — slice level
  setCurrentIndex: (i: number) => void;
  setRegion: (imageUuid: string, region: Region) => void;
  setScore: (imageUuid: string, field: string, score: RegionScore) => void;
  setSliceNotes: (imageUuid: string, notes: string) => void;
  setWindow: (wl: number, ww: number) => void;
  resetWindow: () => void;

  // Derived
  aspectsEnabled: () => boolean;
  currentImage: () => ImageRecord | null;
  currentSlice: () => SliceEvalState;
  isCurrentSliceValid: () => boolean;
  isSetSubmittable: () => boolean;
  validationMessage: () => string;
  buildSubmitPayload: () => object;
}

export const useLabelStore = create<LabelStore>((set, get) => ({
  setRegistry: {},
  imageSet: null,
  images: [],
  annotationSessionUuid: null,
  usability: null,
  lowQuality: false,
  setNotes: "",
  slices: {},
  currentIndex: 0,
  windowLevel: 35,
  windowWidth: 100,
  defaultWindowLevel: 35,
  defaultWindowWidth: 100,

  loadImageSet: (imageSet, images, sessionUuid) => {
    const s = get();
    // Save current set to registry before switching
    const registry = { ...s.setRegistry };
    if (s.imageSet) {
      registry[String(s.imageSet.uuid)] = {
        usability: s.usability,
        lowQuality: s.lowQuality,
        setNotes: s.setNotes,
        slices: { ...s.slices },
        currentIndex: s.currentIndex,
      };
    }
    // Restore saved state for the new set, or start fresh
    const saved = registry[String(imageSet.uuid)];
    const slices: Record<string, SliceEvalState> = {};
    for (const img of images) {
      slices[img.uuid] = saved?.slices[img.uuid] ?? emptySlice();
    }
    const defaultWL = imageSet.image_window_level ?? 35;
    const defaultWW = imageSet.image_window_width ?? 100;
    set({
      setRegistry: registry,
      imageSet,
      images,
      annotationSessionUuid: sessionUuid,
      slices,
      currentIndex: saved?.currentIndex ?? 0,
      windowLevel: defaultWL,
      windowWidth: defaultWW,
      defaultWindowLevel: defaultWL,
      defaultWindowWidth: defaultWW,
      usability: saved?.usability ?? null,
      lowQuality: saved?.lowQuality ?? false,
      setNotes: saved?.setNotes ?? "",
    });
  },

  reset: () =>
    set({
      setRegistry: {},
      imageSet: null,
      images: [],
      annotationSessionUuid: null,
      usability: null,
      lowQuality: false,
      setNotes: "",
      slices: {},
      currentIndex: 0,
      windowLevel: 35,
      windowWidth: 100,
      defaultWindowLevel: 35,
      defaultWindowWidth: 100,
    }),

  setUsability: (u) => set({ usability: u }),
  setLowQuality: (lq) => set({ lowQuality: lq }),
  setSetNotes: (n) => set({ setNotes: n }),
  setCurrentIndex: (i) => set({ currentIndex: i }),
  setWindow: (wl, ww) => set({ windowLevel: wl, windowWidth: ww }),

  resetWindow: () => {
    const { defaultWindowLevel, defaultWindowWidth } = get();
    set({ windowLevel: defaultWindowLevel, windowWidth: defaultWindowWidth });
  },

  setRegion: (imageUuid, region) =>
    set((s) => ({
      slices: {
        ...s.slices,
        [imageUuid]: { ...s.slices[imageUuid], region, scores: emptyScores() },
      },
    })),

  setScore: (imageUuid, field, score) =>
    set((s) => ({
      slices: {
        ...s.slices,
        [imageUuid]: {
          ...s.slices[imageUuid],
          scores: { ...s.slices[imageUuid].scores, [field]: score },
        },
      },
    })),

  setSliceNotes: (imageUuid, notes) =>
    set((s) => ({
      slices: {
        ...s.slices,
        [imageUuid]: { ...s.slices[imageUuid], notes },
      },
    })),

  aspectsEnabled: () => {
    const { usability, lowQuality } = get();
    return usability === "IschemicAssessable" && !lowQuality;
  },

  currentImage: () => {
    const { images, currentIndex } = get();
    return images[currentIndex] ?? null;
  },

  currentSlice: () => {
    const img = get().currentImage();
    if (!img) return emptySlice();
    return get().slices[img.uuid] ?? emptySlice();
  },

  isCurrentSliceValid: () => {
    const img = get().currentImage();
    if (!img) return true;
    const slice = get().slices[img.uuid];
    return slice ? isSliceValid(slice) : true;
  },

  isSetSubmittable: () => {
    const { usability, slices } = get();
    if (!usability) return false;
    if (!get().aspectsEnabled()) return true;
    const sliceList = Object.values(slices);
    const hasBasal = sliceList.some((s) => s.region === "BasalGanglia");
    const hasCorona = sliceList.some((s) => s.region === "CoronaRadiata");
    const allValid = sliceList.every(isSliceValid);
    return hasBasal && hasCorona && allValid;
  },

  validationMessage: () => {
    const { usability } = get();
    if (!usability) return "Select a usability classification first.";
    if (!get().aspectsEnabled()) return "Ready to submit.";
    const sliceList = Object.values(get().slices);
    const hasBasal = sliceList.some((s) => s.region === "BasalGanglia");
    const hasCorona = sliceList.some((s) => s.region === "CoronaRadiata");
    const invalidCount = sliceList.filter((s) => !isSliceValid(s)).length;
    if (!hasBasal && !hasCorona) return "Classify at least one BasalGanglia and one CoronaRadiata slice.";
    if (!hasBasal) return "Need at least one BasalGanglia slice.";
    if (!hasCorona) return "Need at least one CoronaRadiata slice.";
    if (invalidCount > 0) return `${invalidCount} slice(s) have incomplete zone scores.`;
    return "All slices valid — ready to submit.";
  },

  buildSubmitPayload: () => {
    const { annotationSessionUuid, usability, lowQuality, setNotes, slices, images } = get();
    const imageEvaluations = get().aspectsEnabled()
      ? images.map((img) => {
          const slice = slices[img.uuid] ?? emptySlice();
          const relevant = relevantScoreKeys(slice.region);
          const scores: Record<string, string> = {};
          for (const zone of ALL_ZONES) {
            for (const side of ["left", "right"]) {
              const key = `${zone}_${side}_score`;
              scores[key] = relevant.includes(key) ? (slice.scores[key] ?? "Not_Applicable") : "Not_Applicable";
            }
          }
          return { image_uuid: img.uuid, region: slice.region, notes: slice.notes || null, ...scores };
        })
      : [];
    return {
      annotation_session_uuid: annotationSessionUuid,
      usability,
      low_quality: lowQuality,
      notes: setNotes || null,
      image_evaluations: imageEvaluations,
    };
  },
}));
