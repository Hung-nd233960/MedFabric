import { useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export interface ConfirmDialogButton {
  label: ReactNode;
  onClick: () => void;
  className?: string;
  disabled?: boolean;
}

interface ConfirmDialogProps {
  title: ReactNode;
  body?: ReactNode;
  /** Button definitions in display order. */
  buttons: ConfirmDialogButton[];
  /** Whether buttons are laid out side-by-side (horizontal) or stacked (vertical). */
  layout?: "horizontal" | "vertical";
  /** Index of the button that is highlighted on open. Default: 0. */
  defaultFocusIndex?: number;
  /** Index of the button triggered by ESC. Default: last button. */
  escIndex?: number;
}

/**
 * Modal confirmation dialog with keyboard navigation.
 *
 * Arrow keys move the highlight, Enter activates the highlighted button,
 * ESC activates the cancel button. Uses a capture-phase window listener
 * so it intercepts keys before parent handlers.
 *
 * Y / N keys are intentionally NOT consumed so callers that have their
 * own Y/N shortcuts still receive them.
 */
export function ConfirmDialog({
  title,
  body,
  buttons,
  layout = "vertical",
  defaultFocusIndex = 0,
  escIndex,
}: ConfirmDialogProps) {
  const [focusIdx, setFocusIdx] = useState(defaultFocusIndex);
  const focusIdxRef = useRef(defaultFocusIndex);
  const buttonsRef = useRef(buttons);
  const cancelIdx = escIndex ?? buttons.length - 1;
  const cancelIdxRef = useRef(cancelIdx);

  useEffect(() => { buttonsRef.current = buttons; }, [buttons]);
  useEffect(() => { cancelIdxRef.current = cancelIdx; }, [cancelIdx]);

  // Sync focus when defaultFocusIndex changes (dialog re-shown with different default)
  useEffect(() => {
    focusIdxRef.current = defaultFocusIndex;
    setFocusIdx(defaultFocusIndex);
  }, [defaultFocusIndex]);

  const moveFocus = (next: number) => {
    focusIdxRef.current = next;
    setFocusIdx(next);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const key = e.key;
      const isHoriz = layout === "horizontal";

      const fwd = isHoriz ? key === "ArrowRight" : key === "ArrowDown";
      const bwd = isHoriz ? key === "ArrowLeft"  : key === "ArrowUp";

      if (fwd || bwd) {
        e.preventDefault();
        e.stopPropagation();
        const len = buttonsRef.current.length;
        const next = fwd
          ? Math.min(focusIdxRef.current + 1, len - 1)
          : Math.max(focusIdxRef.current - 1, 0);
        moveFocus(next);
        return;
      }

      // Consume the opposing axis arrows too (prevent background navigation)
      if (isHoriz && (key === "ArrowUp" || key === "ArrowDown")) {
        e.preventDefault(); e.stopPropagation(); return;
      }
      if (!isHoriz && (key === "ArrowLeft" || key === "ArrowRight")) {
        e.preventDefault(); e.stopPropagation(); return;
      }

      if (key === "Enter") {
        e.preventDefault();
        e.stopPropagation();
        const btn = buttonsRef.current[focusIdxRef.current];
        if (btn && !btn.disabled) btn.onClick();
        return;
      }

      if (key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        const btn = buttonsRef.current[cancelIdxRef.current];
        if (btn) btn.onClick();
        return;
      }

      // Tab — consume so it doesn't escape to other handlers
      if (key === "Tab") {
        e.preventDefault();
        e.stopPropagation();
        const len = buttonsRef.current.length;
        moveFocus((focusIdxRef.current + (e.shiftKey ? len - 1 : 1)) % len);
        return;
      }

      // Intentionally NOT consuming Y / N — let parent handlers receive them
    };

    window.addEventListener("keydown", onKey, true); // capture phase — fires first
    return () => window.removeEventListener("keydown", onKey, true);
  }, [layout]); // layout is the only stable dep; everything else uses refs

  const isHoriz = layout === "horizontal";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-background border border-border rounded-lg p-6 shadow-xl space-y-4"
           style={{ width: isHoriz ? "20rem" : "20rem", maxWidth: "90vw" }}>
        <p className="text-base font-semibold">{title}</p>
        {body && <p className="text-sm text-muted-foreground">{body}</p>}
        <div className={cn("flex gap-2", isHoriz ? "flex-row" : "flex-col")}>
          {buttons.map((btn, i) => (
            <Button
              key={i}
              type="button"
              disabled={btn.disabled}
              onClick={btn.onClick}
              className={cn(
                isHoriz ? "flex-1" : "w-full",
                btn.className,
                focusIdx === i && "ring-2 ring-offset-2 ring-offset-background ring-white/70"
              )}
            >
              {btn.label}
            </Button>
          ))}
        </div>
        <p className="text-xs text-muted-foreground/50 text-center font-mono select-none">
          {isHoriz ? "← →" : "↑ ↓"} navigate · Enter confirm · Esc cancel
        </p>
      </div>
    </div>
  );
}
