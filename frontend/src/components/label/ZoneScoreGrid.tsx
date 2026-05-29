/**
 * Zone score grid for a single ASPECTS slice.
 *
 * The header row and each ZoneRow independently use grid-cols-[4%_1fr_1fr],
 * so columns visually align without needing a shared parent grid or fragments.
 */
import React from "react";
import { useLabelStore } from "@/store/labelStore";
import type { RegionScore, Zone } from "@/lib/types";
import { BASAL_ZONES, CORONA_ZONES, SCORE_LABELS } from "@/lib/types";
import { cn } from "@/lib/utils";
import { WithTooltip } from "@/components/ui/tooltip";

const SCORE_OPTIONS: Exclude<RegionScore, "Not_Applicable">[] = [
  "Affected",
  "Not_Affected",
  "Not_In_This_Slice",
];

const SCORE_STYLES: Record<Exclude<RegionScore, "Not_Applicable">, string> = {
  Affected: "border-red-500 bg-red-500/20 text-red-400 hover:bg-red-500/30",
  Not_Affected: "border-green-500 bg-green-500/20 text-green-400 hover:bg-green-500/30",
  Not_In_This_Slice:
    "border-yellow-500 bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30",
};

const ZONE_TOOLTIPS: Record<string, string> = {
  c:  "Caudate nucleus",
  ic: "Internal capsule",
  l:  "Lentiform nucleus",
  i:  "Insular ribbon",
  m1: "MCA cortex — anterior (BG level)",
  m2: "MCA cortex — lateral (BG level)",
  m3: "MCA cortex — posterior (BG level)",
  m4: "MCA cortex — anterior (CR level)",
  m5: "MCA cortex — lateral (CR level)",
  m6: "MCA cortex — posterior (CR level)",
};

const SCORE_KBD: Record<Exclude<RegionScore, "Not_Applicable">, string> = {
  Affected: "1",
  Not_Affected: "2",
  Not_In_This_Slice: "3",
};

function ScoreButton({
  value,
  current,
  onClick,
  readOnly,
  showKbd,
  isVis,
}: {
  value: Exclude<RegionScore, "Not_Applicable">;
  current: RegionScore | null;
  onClick: () => void;
  readOnly?: boolean;
  showKbd?: boolean;
  isVis?: boolean;
}) {
  const selected = current === value;
  return (
    <button
      type="button"
      onClick={readOnly ? undefined : onClick}
      disabled={readOnly && !selected}
      className={cn(
        "rounded border px-1.5 py-0.5 text-sm font-medium transition-all",
        selected ? SCORE_STYLES[value] : "border-border text-muted-foreground hover:bg-muted",
        readOnly && "cursor-default pointer-events-none"
      )}
    >
      {showKbd ? (
        <span className="flex items-center gap-1">
          {SCORE_LABELS[value]}
          <kbd className={cn(
            "font-mono border px-1 py-0 rounded text-[10px] leading-none",
            isVis
              ? "border-rose-400/50 bg-rose-400/15 text-rose-300"
              : "border-amber-400/50 bg-amber-400/15 text-amber-300"
          )}>{SCORE_KBD[value]}</kbd>
        </span>
      ) : SCORE_LABELS[value]}
    </button>
  );
}

type ZoneCell = { row: number; col: "left" | "right" };

interface ZoneRowProps {
  zone: Zone;
  imageUuid: string;
  readOnly?: boolean;
  rowIndex: number;
  zoneModeCell?: ZoneCell | null;
  zoneModeAnchor?: ZoneCell | null;
  zoneModeScope?: "cell" | "row" | "col" | "all";
  onExitZoneMode?: () => void;
}

function ZoneRow({ zone, imageUuid, readOnly, rowIndex, zoneModeCell, zoneModeAnchor, zoneModeScope, onExitZoneMode }: ZoneRowProps) {
  const { slices, setScore } = useLabelStore();
  const slice = slices[imageUuid];
  const leftKey = `${zone}_left_score`;
  const rightKey = `${zone}_right_score`;
  const leftScore = (slice?.scores[leftKey] as RegionScore) ?? null;
  const rightScore = (slice?.scores[rightKey] as RegionScore) ?? null;

  const zoneComplete = leftScore !== null && rightScore !== null;
  const scope = zoneModeScope ?? "cell";
  const hlLeft  = !zoneModeCell ? false
    : scope === "row" ? zoneModeCell.row === rowIndex
    : scope === "col" ? zoneModeCell.col === "left"
    : scope === "all" ? true
    : zoneModeCell.row === rowIndex && zoneModeCell.col === "left";
  const hlRight = !zoneModeCell ? false
    : scope === "row" ? zoneModeCell.row === rowIndex
    : scope === "col" ? zoneModeCell.col === "right"
    : scope === "all" ? true
    : zoneModeCell.row === rowIndex && zoneModeCell.col === "right";

  const inVis = zoneModeAnchor != null;

  const inSel = (col: "left" | "right") => {
    if (!zoneModeAnchor || !zoneModeCell) return false;
    const rMin = Math.min(zoneModeAnchor.row, zoneModeCell.row);
    const rMax = Math.max(zoneModeAnchor.row, zoneModeCell.row);
    if (rowIndex < rMin || rowIndex > rMax) return false;
    return new Set([zoneModeAnchor.col, zoneModeCell.col]).has(col);
  };
  const selLeft  = inSel("left")  && !hlLeft;
  const selRight = inSel("right") && !hlRight;

  return (
    <div className="grid grid-cols-[5%_4%_1fr_1fr] items-center py-1">
      <div className="flex justify-center">
        {zoneModeCell != null ? (
          <kbd className={cn(
            "font-mono border px-1 py-0.5 rounded text-[10px] leading-none",
            inVis ? "border-rose-400/50 bg-rose-400/15 text-rose-300" : "border-amber-400/50 bg-amber-400/15 text-amber-300"
          )}>{rowIndex + 1}</kbd>
        ) : (
          <span className="text-[10px] text-muted-foreground/30 font-mono">{rowIndex + 1}</span>
        )}
      </div>
      <WithTooltip
        type="medical"
        content={ZONE_TOOLTIPS[zone] ?? zone}
        side="right"
      >
        <span
          tabIndex={0}
          className={cn(
            "text-sm font-mono uppercase text-center font-semibold",
            zoneComplete ? "text-green-400" : "text-red-400"
          )}
        >
          {zone}
        </span>
      </WithTooltip>
      <div className={cn(
        "flex gap-1 flex-wrap px-1 rounded transition-all",
        hlLeft  && (inVis ? "ring-2 ring-rose-400/70 bg-rose-400/10" : "ring-2 ring-amber-400/70 bg-amber-400/10"),
        selLeft && (inVis ? "ring-1 ring-rose-400/40 bg-rose-400/5"  : "ring-1 ring-amber-400/40 bg-amber-400/5"),
      )}>
        {SCORE_OPTIONS.map((s) => (
          <ScoreButton
            key={s}
            value={s}
            current={leftScore}
            onClick={() => { setScore(imageUuid, leftKey, leftScore === s ? null : s); onExitZoneMode?.(); }}
            readOnly={readOnly}
            showKbd={hlLeft || selLeft}
            isVis={inVis}
          />
        ))}
      </div>
      <div className={cn(
        "flex gap-1 flex-wrap px-1 rounded transition-all",
        hlRight  && (inVis ? "ring-2 ring-rose-400/70 bg-rose-400/10" : "ring-2 ring-amber-400/70 bg-amber-400/10"),
        selRight && (inVis ? "ring-1 ring-rose-400/40 bg-rose-400/5"  : "ring-1 ring-amber-400/40 bg-amber-400/5"),
      )}>
        {SCORE_OPTIONS.map((s) => (
          <ScoreButton
            key={s}
            value={s}
            current={rightScore}
            onClick={() => { setScore(imageUuid, rightKey, rightScore === s ? null : s); onExitZoneMode?.(); }}
            readOnly={readOnly}
            showKbd={hlRight || selRight}
            isVis={inVis}
          />
        ))}
      </div>
    </div>
  );
}

interface ZoneScoreGridProps {
  imageUuid: string;
  readOnly?: boolean;
  zoneModeCell?: ZoneCell | null;
  zoneModeAnchor?: ZoneCell | null;
  zoneModeScope?: "cell" | "row" | "col" | "all";
  onExitZoneMode?: () => void;
}

export default function ZoneScoreGrid({ imageUuid, readOnly, zoneModeCell, zoneModeAnchor, zoneModeScope, onExitZoneMode }: ZoneScoreGridProps) {
  const { slices } = useLabelStore();
  const slice = slices[imageUuid];
  const region = slice?.region ?? "None";

  if (region === "None") return null;

  const zones = region === "BasalGanglia" ? BASAL_ZONES : CORONA_ZONES;

  const leftComplete = zones.every((z) => (slice?.scores[`${z}_left_score`] ?? null) !== null);
  const rightComplete = zones.every((z) => (slice?.scores[`${z}_right_score`] ?? null) !== null);

  const activeZoneName = zoneModeCell ? zones[zoneModeCell.row]?.toUpperCase() : null;
  const activeCol = zoneModeCell?.col === "left" ? "Left" : "Right";

  const isVisual = zoneModeAnchor != null && zoneModeCell != null;
  const visRMin = isVisual ? Math.min(zoneModeAnchor!.row, zoneModeCell!.row) : 0;
  const visRMax = isVisual ? Math.max(zoneModeAnchor!.row, zoneModeCell!.row) : 0;
  const visCols = isVisual ? new Set([zoneModeAnchor!.col, zoneModeCell!.col]) : new Set<string>();
  const visColLabel = isVisual
    ? (visCols.has("left") && visCols.has("right") ? "Both" : visCols.has("left") ? "Left" : "Right")
    : "";
  const visRangeLabel = isVisual
    ? `${zones[visRMin]?.toUpperCase()}–${zones[visRMax]?.toUpperCase()} · ${visColLabel}`
    : "";

  return (
    <div className="space-y-1">
      <div className="text-base uppercase tracking-wide text-muted-foreground mb-1">
        {region === "BasalGanglia" ? "Basal Ganglia Zones" : "Corona Radiata Zones"}
      </div>

      {/* Header — same grid-cols as ZoneRow so columns align */}
      <div className="grid grid-cols-[5%_4%_1fr_1fr]">
        <div /><div />
        <div className={cn(
          "text-sm font-semibold pb-1 border-b border-border flex items-center",
          leftComplete ? "text-green-400 border-green-400/40" : "text-red-400 border-red-400/40"
        )}>
          {zoneModeCell != null && (
            <kbd className={cn(
              "font-mono border px-1 py-0.5 rounded text-[10px] leading-none shrink-0",
              isVisual ? "border-rose-400/40 bg-rose-400/10 text-rose-300/80" : "border-amber-400/40 bg-amber-400/10 text-amber-300/80"
            )}>&lt;</kbd>
          )}
          <span className="flex-1 text-center">Left</span>
        </div>
        <div className={cn(
          "text-sm font-semibold pb-1 border-b border-border flex items-center",
          rightComplete ? "text-green-400 border-green-400/40" : "text-red-400 border-red-400/40"
        )}>
          <span className="flex-1 text-center">Right</span>
          {zoneModeCell != null && (
            <kbd className={cn(
              "font-mono border px-1 py-0.5 rounded text-[10px] leading-none shrink-0",
              isVisual ? "border-rose-400/40 bg-rose-400/10 text-rose-300/80" : "border-amber-400/40 bg-amber-400/10 text-amber-300/80"
            )}>&gt;</kbd>
          )}
        </div>
      </div>

      {zones.map((z, i) => (
        <ZoneRow key={z} zone={z as Zone} imageUuid={imageUuid} readOnly={readOnly} rowIndex={i} zoneModeCell={zoneModeCell} zoneModeAnchor={zoneModeAnchor} zoneModeScope={zoneModeScope} onExitZoneMode={onExitZoneMode} />
      ))}

      {zoneModeCell != null ? (() => {
        const scope = zoneModeScope ?? "cell";
        const AKbd = ({ children }: { children: React.ReactNode }) => (
          <kbd className={cn(
            "font-mono border px-1.5 py-0.5 rounded text-[10px] leading-none",
            isVisual ? "border-rose-400/50 bg-rose-400/15 text-rose-300" : "border-amber-400/50 bg-amber-400/15 text-amber-300"
          )}>{children}</kbd>
        );
        const ADim = ({ children }: { children: React.ReactNode }) => (
          <kbd className={cn(
            "font-mono border px-1 py-0.5 rounded text-[10px] leading-none",
            isVisual ? "border-rose-400/30 bg-rose-400/10 text-rose-300/70" : "border-amber-400/30 bg-amber-400/10 text-amber-300/70"
          )}>{children}</kbd>
        );
        const hint = ({ children }: { children: React.ReactNode }) => (
          <span className={cn("flex items-center gap-1 text-[10px]", isVisual ? "text-rose-200/60" : "text-amber-200/60")}>{children}</span>
        );

        const scopeLabel = isVisual ? "Vis" : scope === "row" ? "Row" : scope === "col" ? "Col" : scope === "all" ? "All" : "Cell";
        const zoneInfo = isVisual ? visRangeLabel
          : scope === "row" ? `${activeZoneName} · Both`
          : scope === "col" ? `${zones[0].toUpperCase()}-${zones[zones.length-1].toUpperCase()} · ${activeCol}`
          : scope === "all" ? `${zones[0].toUpperCase()}-${zones[zones.length-1].toUpperCase()} · Both`
          : `${activeZoneName} · ${activeCol}`;
        const navArrows: string[] = scope === "all" ? [] : scope === "row" ? ["↑","↓"] : scope === "col" ? ["←","→"] : ["↑","↓","←","→"];
        const isVisAllSelected = isVisual &&
          zoneModeAnchor?.row === 0 && zoneModeAnchor?.col === "left" &&
          zoneModeCell?.row === zones.length - 1 && zoneModeCell?.col === "right";
        const ctrlAIsUnselect = scope === "all" || isVisAllSelected;

        return (
          <div className={cn(
            "border-t px-2 py-1.5 text-xs font-mono select-none flex flex-col gap-1.5 rounded-b mt-1",
            isVisual ? "border-rose-500/20 bg-rose-500/5" : "border-amber-500/20 bg-amber-500/5"
          )}>
            {/* Line 1 */}
            <div className="flex items-center gap-2">
              <span className={isVisual ? "text-rose-400" : "text-amber-400"}>Zone Mode · {scopeLabel}</span>
              <span className={cn("mx-0.5", isVisual ? "text-rose-400/30" : "text-amber-400/30")}>|</span>
              <span className="text-muted-foreground">{zoneInfo}</span>
              <span className="ml-auto flex items-center gap-2 shrink-0">
                {(["1","2","3","0"] as const).map((k, i) => (
                  <span key={k} className="flex items-center gap-1">
                    <AKbd>{k}</AKbd>
                    <span className={cn("text-[10px]", isVisual ? "text-rose-200/70" : "text-amber-200/70")}>{["DMG","OK","NV","CLR"][i]}</span>
                  </span>
                ))}
              </span>
            </div>
            {/* Line 2 */}
            <div className="flex items-center justify-between gap-2">
              {hint({ children: navArrows.length > 0
                ? <><span>Navigate</span>{navArrows.map(k => <ADim key={k}>{k}</ADim>)}</>
                : <span className={cn("italic", isVisual ? "text-rose-200/30" : "text-amber-200/30")}>no navigation</span>
              })}
              {hint({ children: <><ADim>Shift</ADim><span>+num or</span><ADim>&lt;</ADim><ADim>&gt;</ADim><span>to select</span></> })}
            </div>
            {/* Line 3 */}
            <div className="flex items-center justify-between gap-2">
              {hint({ children: isVisual
                ? <><ADim>V</ADim><span>/</span><ADim>Esc</ADim><span>exit Vis</span></>
                : <><ADim>V</ADim><span>Vis Mode</span></>
              })}
              {hint({ children: isVisual
                ? <><ADim>Z</ADim><span>exit Zone Mode</span></>
                : scope === "cell"
                ? <><ADim>Esc</ADim><span>/</span><ADim>Z</ADim><span>exit Zone Mode</span></>
                : <><ADim>Esc</ADim><span>Cell Mode</span></>
              })}
            </div>
            {/* Line 4 — Ctrl+A select/unselect all, centered */}
            <div className="flex justify-center">
              {hint({ children: ctrlAIsUnselect
                ? <><ADim>Ctrl+A</ADim><span>to unselect</span></>
                : <><ADim>Ctrl+A</ADim><span>to select all</span></>
              })}
            </div>
          </div>
        );
      })() : (
        <div className="border-t border-border/40 bg-muted/20 px-2 py-1 text-xs font-mono select-none flex items-center gap-1.5 rounded-b mt-1">
          <span className="text-muted-foreground/60">Press</span>
          <kbd className="font-mono border border-border/60 bg-muted px-1 py-0.5 rounded text-[10px] leading-none">Z</kbd>
          <span className="text-muted-foreground/60">for</span>
          <span className="text-amber-400/80 font-semibold">Zone Mode</span>
          <span className="text-muted-foreground/40 mx-0.5">·</span>
          <kbd className="font-mono border border-border/60 bg-muted px-1 py-0.5 rounded text-[10px] leading-none">V</kbd>
          <span className="text-muted-foreground/60">for</span>
          <span className="text-rose-400/80 font-semibold">Vis</span>
        </div>
      )}
    </div>
  );
}
