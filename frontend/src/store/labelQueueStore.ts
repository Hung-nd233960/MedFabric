import { create } from "zustand";

export interface LabelQueueState {
  queue: string[];
  currentPos: number;
  indices: number[];
  sources: string[];          // "submission" | "draft" per slot; empty in annotate mode
  sessionUuid: string | null; // current set's annotation session
  adminDoctors: string[];     // admin-read: doctor UUID per slot
  isReadMode: boolean;
  isPreviewMode: boolean;
}

interface LabelQueueActions {
  enter: (state: LabelQueueState) => void;
  setCurrentPos: (pos: number) => void;
  setSessionUuid: (uuid: string | null) => void;
  clear: () => void;
}

const EMPTY: LabelQueueState = {
  queue: [],
  currentPos: 0,
  indices: [],
  sources: [],
  sessionUuid: null,
  adminDoctors: [],
  isReadMode: false,
  isPreviewMode: false,
};

export const useLabelQueueStore = create<LabelQueueState & LabelQueueActions>((set) => ({
  ...EMPTY,
  enter: (state) => set(state),
  setCurrentPos: (pos) => set({ currentPos: pos }),
  setSessionUuid: (uuid) => set({ sessionUuid: uuid }),
  clear: () => set(EMPTY),
}));
