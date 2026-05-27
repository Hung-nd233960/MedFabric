import * as React from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { cn } from "@/lib/utils";
import { useAppearanceStore } from "@/store/appearanceStore";

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
          "z-50 max-w-[240px] overflow-hidden rounded-md bg-foreground/[0.92] px-2.5 py-1.5",
          "text-xs font-medium leading-snug text-background shadow-lg",
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
function WithTooltip({
  type = "functional",
  content,
  side,
  children,
}: {
  type?: "medical" | "functional" | "meta";
  content: string;
  side?: "top" | "right" | "bottom" | "left";
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
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent side={side}>{content}</TooltipContent>
    </Tooltip>
  );
}

export { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger, WithTooltip };
