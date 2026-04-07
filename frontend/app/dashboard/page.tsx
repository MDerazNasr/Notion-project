import Link from "next/link";
import { ArrowLeft, Network, TriangleAlert } from "lucide-react";

import { DashboardActions } from "@/components/DashboardActions";
import { PageRow } from "@/components/PageRow";
import { getScores } from "@/lib/api";
import { ScoreBand } from "@/lib/types";

function countBand(band: ScoreBand, scores: Array<{ score_band: ScoreBand }>) {
  return scores.filter((page) => page.score_band === band).length;
}

export default async function DashboardPage({
  searchParams
}: {
  searchParams: Promise<{ source?: string }>;
}) {
  const resolvedSearchParams = await searchParams;
  const source = resolvedSearchParams.source ?? "demo";

  try {
    const result = await getScores(source);

    return (
      <main className="pb-16 pt-8 sm:pb-24 sm:pt-10">
        <div className="shell">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="label mb-2">Dashboard</div>
              <h1 className="text-3xl font-medium tracking-[-0.04em] text-ink">
                Reliability ranking for {result.workspace_id}
              </h1>
            </div>
            <div className="flex flex-wrap gap-3">
              <DashboardActions source={source} />
              <Link href="/" className="button button-secondary">
                <ArrowLeft size={16} />
                Back
              </Link>
            </div>
          </div>

          <section className="mb-6 grid gap-4 md:grid-cols-4">
            <div className="card p-5">
              <div className="label">Pages scored</div>
              <div className="metric mt-2">{result.page_count}</div>
            </div>
            <div className="card p-5">
              <div className="label">Green pages</div>
              <div className="metric mt-2">{countBand("green", result.pages)}</div>
            </div>
            <div className="card p-5">
              <div className="label">Amber pages</div>
              <div className="metric mt-2">{countBand("amber", result.pages)}</div>
            </div>
            <div className="card p-5">
              <div className="label">Red pages</div>
              <div className="metric mt-2">{countBand("red", result.pages)}</div>
            </div>
          </section>

          <section className="mb-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_310px]">
            <div className="card overflow-hidden">
              <div className="flex items-center justify-between gap-4 border-b border-line px-5 py-4">
                <div>
                  <div className="label mb-1">Ranked pages</div>
                  <h2 className="text-lg font-medium tracking-[-0.02em] text-ink">
                    Highest confidence first
                  </h2>
                </div>
                <div className="rounded-subtle border border-line bg-surface px-3 py-2 text-sm text-[color:var(--muted)]">
                  Snapshot {new Date(result.snapshot_time).toLocaleDateString()}
                </div>
              </div>

              {result.pages.map((page) => (
                <PageRow key={page.page_id} page={page} source={source} />
              ))}
            </div>

            <aside className="space-y-6">
              <div className="card p-5">
                <div className="mb-3 flex items-center gap-2">
                  <Network size={16} className="text-[color:var(--accent)]" />
                  <div className="label">Model</div>
                </div>
                <div className="space-y-3 text-sm leading-6 text-[color:var(--muted)]">
                  <p>
                    Source: <span className="text-ink">{result.model.source}</span>
                  </p>
                  <p>{result.model.evaluation_target}</p>
                  <p>{result.model.calibration}</p>
                </div>
              </div>

              <div className="card p-5">
                <div className="mb-3 flex items-center gap-2">
                  <TriangleAlert size={16} className="text-[color:var(--accent)]" />
                  <div className="label">Read this ranking carefully</div>
                </div>
                <p className="text-sm leading-6 text-[color:var(--muted)]">
                  This is a reliability estimate, not ground truth. Open a page to
                  inspect which structural and semantic signals drove its score.
                </p>
              </div>
            </aside>
          </section>
        </div>
      </main>
    );
  } catch (error) {
    return (
      <main className="pb-16 pt-12">
        <div className="shell">
          <div className="card p-8">
            <div className="label mb-2">Dashboard unavailable</div>
            <h1 className="text-2xl font-medium tracking-[-0.03em] text-ink">
              {error instanceof Error ? error.message : "Could not load dashboard."}
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-[color:var(--muted)]">
              For live mode, connect from the home page first so the backend can cache
              the most recent run. Demo mode can be opened directly.
            </p>
            <div className="mt-6">
              <Link href="/" className="button button-secondary">
                <ArrowLeft size={16} />
                Back home
              </Link>
            </div>
          </div>
        </div>
      </main>
    );
  }
}
