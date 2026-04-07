import Link from "next/link";
import { ArrowUpRight, Clock3, Link2 } from "lucide-react";

import { ScorePage } from "@/lib/types";
import { ScoreBar } from "@/components/ScoreBar";

type PageRowProps = {
  page: ScorePage;
  source: string;
};

export function PageRow({ page, source }: PageRowProps) {
  return (
    <Link
      href={`/page/${page.page_id}?source=${source}`}
      className="table-row transition-colors hover:bg-[rgba(247,246,243,0.68)]"
      style={{
        gridTemplateColumns: "minmax(0, 2fr) minmax(160px, 220px) minmax(0, 1.2fr) auto"
      }}
    >
      <div className="min-w-0">
        <div className="mb-1 flex items-center gap-2">
          <h3 className="truncate text-[15px] font-medium text-ink">{page.title}</h3>
          <ArrowUpRight size={14} className="shrink-0 text-[color:var(--muted)]" />
        </div>
        <p className="truncate text-sm text-[color:var(--muted)]">
          {page.headline_reason}
        </p>
      </div>

      <ScoreBar score={page.reliability_score} band={page.score_band} compact />

      <div className="flex flex-wrap gap-2">
        <span className="signal-pill">
          <Clock3 size={12} />
          {Math.round(page.days_since_edit)}d since edit
        </span>
        <span className="signal-pill">
          <Link2 size={12} />
          {page.score_band} signal
        </span>
      </div>

      <div className="text-right text-sm text-[color:var(--muted)]">
        {new Date(page.last_edited_time).toLocaleDateString()}
      </div>
    </Link>
  );
}
