/**
 * Zone score grid for a single ASPECTS slice.
 *
 * Shows the relevant zones for the selected region (BasalGanglia or CoronaRadiata).
 * Each zone has Left / Right buttons with three states: Damaged / Not Damaged / Not Visible.
 */
import { useLabelStore } from "@/store/labelStore";
import type { RegionScore, Zone } from "@/lib/types";
import { BASAL_ZONES, CORONA_ZONES, SCORE_LABELS } from "@/lib/types";
import { cn } from "@/lib/utils";

const SCORE_OPTIONS: Exclude<RegionScore, "Not_Applicable">[] = [
  "Affected",
  "Not_Affected",
  "Not_In_This_Slice",
];

const SCORE_STYLES: Record<Exclude<RegionScore, "Not_Applicable">, string> = {
  Affected: "border-red-500 bg-red-500/20 text-red-400 hover:bg-red-500/30",
  Not_Affected: "border-green-500 bg-green-500/20 text-green-400 hover:bg-green-500/30",
  Not_In_This_Slice:
    "border-muted-foreground/40 bg-muted/40 text-muted-foreground hover:bg-muted/60",
};

function ScoreButton({
  value,
  current,
  onClick,
}: {
  value: Exclude<RegionScore, "Not_Applicable">;
  current: RegionScore | null;
  onClick: () => void;
}) {
  const selected = current === value;
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded border px-1.5 py-0.5 text-[10px] font-medium transition-all",
        selected ? SCORE_STYLES[value] : "border-border text-muted-foreground hover:bg-muted"
      )}
    >
      {SCORE_LABELS[value]}
    </button>
  );
}

interface ZoneRowProps {
  zone: Zone;
  imageUuid: string;
}

function ZoneRow({ zone, imageUuid }: ZoneRowProps) {
  const { slices, setScore } = useLabelStore();
  const slice = slices[imageUuid];
  const leftKey = `${zone}_left_score`;
  const rightKey = `${zone}_right_score`;
  const leftScore = (slice?.scores[leftKey] as RegionScore) ?? null;
  const rightScore = (slice?.scores[rightKey] as RegionScore) ?? null;

  return (
    <div className="grid grid-cols-[3rem_1fr_1fr] gap-2 items-center">
      <span className="text-xs font-mono text-muted-foreground uppercase text-right pr-1">
        {zone}
      </span>

      {/* Left */}
      <div className="space-y-1">
        <span className="text-[10px] text-muted-foreground block">Left</span>
        <div className="flex gap-1 flex-wrap">
          {SCORE_OPTIONS.map((s) => (
            <ScoreButton
              key={s}
              value={s}
              current={leftScore}
              onClick={() => setScore(imageUuid, leftKey, s)}
            />
          ))}
        </div>
      </div>

      {/* Right */}
      <div className="space-y-1">
        <span className="text-[10px] text-muted-foreground block">Right</span>
        <div className="flex gap-1 flex-wrap">
          {SCORE_OPTIONS.map((s) => (
            <ScoreButton
              key={s}
              value={s}
              current={rightScore}
              onClick={() => setScore(imageUuid, rightKey, s)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

interface ZoneScoreGridProps {
  imageUuid: string;
}

export default function ZoneScoreGrid({ imageUuid }: ZoneScoreGridProps) {
  const { slices } = useLabelStore();
  const region = slices[imageUuid]?.region ?? "None";

  if (region === "None") return null;

  const zones = region === "BasalGanglia" ? BASAL_ZONES : CORONA_ZONES;

  return (
    <div className="space-y-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {region === "BasalGanglia" ? "Basal Ganglia Zones" : "Corona Radiata Zones"}
      </div>
      {zones.map((z) => (
        <ZoneRow key={z} zone={z as Zone} imageUuid={imageUuid} />
      ))}
    </div>
  );
}
