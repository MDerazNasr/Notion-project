import { ScoreBand } from "@/lib/types";

const bandStyles: Record<ScoreBand, string> = {
  red: "var(--red-soft)",
  amber: "var(--amber-soft)",
  green: "var(--green-soft)"
};

type ScoreBarProps = {
  score: number;
  band: ScoreBand;
  compact?: boolean;
};

export function ScoreBar({
  score,
  band,
  compact = false
}: ScoreBarProps) {
  const width = `${Math.max(6, Math.round(score * 100))}%`;

  return (
    <div className="flex items-center gap-3">
      <div
        className={`relative overflow-hidden rounded-[3px] border border-line bg-surface ${
          compact ? "h-2.5 w-28" : "h-3 w-40"
        }`}
      >
        <div
          className="absolute inset-y-0 left-0 rounded-[2px]"
          style={{
            width,
            backgroundColor: bandStyles[band]
          }}
        />
      </div>
      <span className="min-w-12 text-right text-sm font-medium text-ink">
        {Math.round(score * 100)}%
      </span>
    </div>
  );
}
