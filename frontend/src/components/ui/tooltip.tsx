import * as React from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { cn } from "@/lib/utils";
import { useAppearanceStore } from "@/store/appearanceStore";
import { navLabel, type NavDir } from "@/lib/navKeys";

const TooltipProvider = TooltipPrimitive.Provider;
const Tooltip = TooltipPrimitive.Root;
const TooltipTrigger = TooltipPrimitive.Trigger;

function TooltipContent({
  className,
  sideOffset = 6,
  children,
  ...props
}: React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content
        sideOffset={sideOffset}
        className={cn(
          "z-50 max-w-[360px] rounded-xl bg-foreground/[0.93] px-3.5 py-2.5",
          "text-sm font-medium leading-snug text-background shadow-xl ring-1 ring-background/10",
          "animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95",
          "data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2",
          "data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2",
          className
        )}
        {...props}
      >
        {children}
        <TooltipPrimitive.Arrow className="fill-foreground" />
      </TooltipPrimitive.Content>
    </TooltipPrimitive.Portal>
  );
}

/**
 * type="medical"    — zone names, usability definitions
 * type="functional" — UI hints, button labels (default)
 * type="meta"       — tooltip-option descriptions; always on unless mode is "off"
 */
/** Kbd chip styled for the dark tooltip background. */
function TooltipKbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="inline-flex items-center rounded-md border border-background/50 bg-background/[0.15] px-2 py-0.5 font-mono text-xs font-semibold leading-none text-background shrink-0 shadow-sm">
      {children}
    </kbd>
  );
}

function WithTooltip({
  type = "functional",
  content,
  side,
  delayDuration,
  children,
}: {
  type?: "medical" | "functional" | "meta";
  content: React.ReactNode;
  side?: "top" | "right" | "bottom" | "left";
  delayDuration?: number;
  children: React.ReactElement;
}) {
  const { tooltipMode } = useAppearanceStore();

  const visible =
    tooltipMode === "all" ||
    (type === "medical"    && tooltipMode === "medical") ||
    (type === "functional" && tooltipMode === "functional") ||
    (type === "meta"       && tooltipMode !== "off");

  if (!visible) return children;
  return (
    <Tooltip delayDuration={delayDuration}>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent side={side}>{content}</TooltipContent>
    </Tooltip>
  );
}

/** Kbd chip that shows the correct key(s) for a navigation direction based on the current nav mode. */
function NavKbd({ dir }: { dir: NavDir }) {
  const { navMode } = useAppearanceStore();
  return <TooltipKbd>{navLabel(dir, navMode)}</TooltipKbd>;
}

export { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger, WithTooltip, TooltipKbd, NavKbd };
