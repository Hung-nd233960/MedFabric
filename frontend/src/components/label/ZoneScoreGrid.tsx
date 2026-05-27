/**
 * Zone score grid for a single ASPECTS slice.
 *
 * The header row and each ZoneRow independently use grid-cols-[4%_1fr_1fr],
 * so columns visually align without needing a shared parent grid or fragments.
 */
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

function ScoreButton({
  value,
  current,
  onClick,
  readOnly,
}: {
  value: Exclude<RegionScore, "Not_Applicable">;
  current: RegionScore | null;
  onClick: () => void;
  readOnly?: boolean;
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
      {SCORE_LABELS[value]}
    </button>
  );
}

interface ZoneRowProps {
  zone: Zone;
  imageUuid: string;
  readOnly?: boolean;
}

function ZoneRow({ zone, imageUuid, readOnly }: ZoneRowProps) {
  const { slices, setScore } = useLabelStore();
  const slice = slices[imageUuid];
  const leftKey = `${zone}_left_score`;
  const rightKey = `${zone}_right_score`;
  const leftScore = (slice?.scores[leftKey] as RegionScore) ?? null;
  const rightScore = (slice?.scores[rightKey] as RegionScore) ?? null;

  const zoneComplete = leftScore !== null && rightScore !== null;

  return (
    <div className="grid grid-cols-[4%_1fr_1fr] items-center py-1">
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
      <div className="flex gap-1 flex-wrap px-1">
        {SCORE_OPTIONS.map((s) => (
          <ScoreButton
            key={s}
            value={s}
            current={leftScore}
            onClick={() => setScore(imageUuid, leftKey, s)}
            readOnly={readOnly}
          />
        ))}
      </div>
      <div className="flex gap-1 flex-wrap px-1">
        {SCORE_OPTIONS.map((s) => (
          <ScoreButton
            key={s}
            value={s}
            current={rightScore}
            onClick={() => setScore(imageUuid, rightKey, s)}
            readOnly={readOnly}
          />
        ))}
      </div>
    </div>
  );
}

interface ZoneScoreGridProps {
  imageUuid: string;
  readOnly?: boolean;
}

export default function ZoneScoreGrid({ imageUuid, readOnly }: ZoneScoreGridProps) {
  const { slices } = useLabelStore();
  const slice = slices[imageUuid];
  const region = slice?.region ?? "None";

  if (region === "None") return null;

  const zones = region === "BasalGanglia" ? BASAL_ZONES : CORONA_ZONES;

  const leftComplete = zones.every((z) => (slice?.scores[`${z}_left_score`] ?? null) !== null);
  const rightComplete = zones.every((z) => (slice?.scores[`${z}_right_score`] ?? null) !== null);

  return (
    <div className="space-y-1">
      <div className="text-base uppercase tracking-wide text-muted-foreground mb-1">
        {region === "BasalGanglia" ? "Basal Ganglia Zones" : "Corona Radiata Zones"}
      </div>

      {/* Header — same grid-cols as ZoneRow so columns align */}
      <div className="grid grid-cols-[4%_1fr_1fr]">
        <div />
        <div className={cn(
          "text-sm text-center font-semibold pb-1 border-b border-border",
          leftComplete ? "text-green-400 border-green-400/40" : "text-red-400 border-red-400/40"
        )}>
          Left
        </div>
        <div className={cn(
          "text-sm text-center font-semibold pb-1 border-b border-border",
          rightComplete ? "text-green-400 border-green-400/40" : "text-red-400 border-red-400/40"
        )}>
          Right
        </div>
      </div>

      {zones.map((z) => (
        <ZoneRow key={z} zone={z as Zone} imageUuid={imageUuid} readOnly={readOnly} />
      ))}
    </div>
  );
}
