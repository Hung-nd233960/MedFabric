/**
 * Vim-inspired navigation key helpers.
 *
 * nav.left(e, mode) — true if the event should trigger "go left/back"
 * navLabel("left", mode) — display string for that direction given the current mode
 */

export type NavMode = "arrow" | "vim" | "both";

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function vim(e: KeyboardEvent, k: string, shift = false): boolean {
  return (
    e.key.toLowerCase() === k &&
    e.shiftKey === shift &&
    !e.ctrlKey &&
    !e.metaKey &&
    !e.altKey
  );
}

// ---------------------------------------------------------------------------
// Directional matchers
// Each returns true when the event should be treated as that direction.
// Modifier state (shift) is encoded in the matcher name.
// ---------------------------------------------------------------------------

export const nav = {
  left:       (e: KeyboardEvent, m: NavMode) =>
    (e.key === "ArrowLeft"  && !e.shiftKey) ||
    (m !== "arrow" && vim(e, "h")),

  right:      (e: KeyboardEvent, m: NavMode) =>
    (e.key === "ArrowRight" && !e.shiftKey) ||
    (m !== "arrow" && vim(e, "l")),

  up:         (e: KeyboardEvent, m: NavMode) =>
    (e.key === "ArrowUp"    && !e.shiftKey) ||
    (m !== "arrow" && vim(e, "k")),

  down:       (e: KeyboardEvent, m: NavMode) =>
    (e.key === "ArrowDown"  && !e.shiftKey) ||
    (m !== "arrow" && vim(e, "j")),

  shiftLeft:  (e: KeyboardEvent, m: NavMode) =>
    (e.key === "ArrowLeft"  && e.shiftKey && !e.ctrlKey && !e.metaKey) ||
    (m !== "arrow" && vim(e, "h", true)),

  shiftRight: (e: KeyboardEvent, m: NavMode) =>
    (e.key === "ArrowRight" && e.shiftKey && !e.ctrlKey && !e.metaKey) ||
    (m !== "arrow" && vim(e, "l", true)),

  shiftUp:    (e: KeyboardEvent, m: NavMode) =>
    (e.key === "ArrowUp"    && e.shiftKey && !e.ctrlKey && !e.metaKey) ||
    (m !== "arrow" && vim(e, "k", true)),

  shiftDown:  (e: KeyboardEvent, m: NavMode) =>
    (e.key === "ArrowDown"  && e.shiftKey && !e.ctrlKey && !e.metaKey) ||
    (m !== "arrow" && vim(e, "j", true)),
} as const;

export type NavDir = keyof typeof nav;

// ---------------------------------------------------------------------------
// Display labels
// ---------------------------------------------------------------------------

const ARROW: Record<NavDir, string> = {
  left:       "←",
  right:      "→",
  up:         "↑",
  down:       "↓",
  shiftLeft:  "Shift+←",
  shiftRight: "Shift+→",
  shiftUp:    "Shift+↑",
  shiftDown:  "Shift+↓",
};

const VIM_KEYS: Record<NavDir, string> = {
  left:       "h",
  right:      "l",
  up:         "k",
  down:       "j",
  shiftLeft:  "Shift+H",
  shiftRight: "Shift+L",
  shiftUp:    "Shift+K",
  shiftDown:  "Shift+J",
};

/** Returns the display label for a direction given the active nav mode. */
export function navLabel(dir: NavDir, mode: NavMode): string {
  if (mode === "arrow") return ARROW[dir];
  if (mode === "vim")   return VIM_KEYS[dir];
  return `${ARROW[dir]} / ${VIM_KEYS[dir]}`;
}
