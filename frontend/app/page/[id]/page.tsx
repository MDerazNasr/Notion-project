import Link from "next/link";
import { ArrowLeft, ArrowUpRight } from "lucide-react";

import { FeatureTable } from "@/components/FeatureTable";
import { ScoreBar } from "@/components/ScoreBar";
import { getPageDetail } from "@/lib/api";

export default async function PageDetail({
  params,
  searchParams
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ source?: string }>;
}) {
  const resolvedParams = await params;
  const resolvedSearchParams = await searchParams;
  const source = resolvedSearchParams.source ?? "demo";
  const detail = await getPageDetail(resolvedParams.id, source);

  return (
    <main className="pb-16 pt-8 sm:pb-24 sm:pt-10">
      <div className="shell">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="label mb-2">Page detail</div>
            <h1 className="max-w-3xl text-3xl font-medium tracking-[-0.04em] text-ink">
              {detail.title}
            </h1>
          </div>

          <Link href={`/dashboard?source=${source}`} className="button button-secondary">
            <ArrowLeft size={16} />
            Back to dashboard
          </Link>
        </div>

        <section className="mb-6 grid gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
          <div className="card p-6">
            <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="label mb-2">Reliability estimate</div>
                <div className="metric">{Math.round(detail.reliability_score * 100)}%</div>
              </div>
              <ScoreBar score={detail.reliability_score} band={detail.score_band} />
            </div>

            <div className="flex flex-wrap gap-2">
              {detail.top_signals.map((signal) => (
                <span key={signal} className="signal-pill">
                  {signal}
                </span>
              ))}
            </div>
          </div>

          <div className="card p-6">
            <div className="label mb-2">Metadata</div>
            <div className="space-y-3 text-sm leading-6 text-[color:var(--muted)]">
              <p>
                Source: <span className="text-ink">{detail.source}</span>
              </p>
              <p>
                Last edited:{" "}
                <span className="text-ink">
                  {new Date(detail.last_edited_time).toLocaleString()}
                </span>
              </p>
              <p>
                Page id: <span className="text-ink">{detail.page_id}</span>
              </p>
            </div>
          </div>
        </section>

        <section className="mb-6 grid gap-6 lg:grid-cols-2">
          <FeatureTable title="Structural signals" rows={detail.structural_features} />
          <FeatureTable title="Semantic signals" rows={detail.semantic_features} />
        </section>

        <section className="grid gap-6 lg:grid-cols-2">
          <div className="card p-5">
            <div className="label mb-2">Most similar linked pages</div>
            <div className="overflow-hidden rounded-subtle border border-line">
              {detail.most_similar_neighbors.map((neighbor) => (
                <Link
                  key={neighbor.page_id}
                  href={`/page/${neighbor.page_id}?source=${source}`}
                  className="grid grid-cols-[1fr_auto] gap-3 border-t border-line px-4 py-3 first:border-t-0 hover:bg-surface"
                >
                  <span className="flex items-center gap-2 text-sm font-medium text-ink">
                    {neighbor.title}
                    <ArrowUpRight size={14} className="text-[color:var(--muted)]" />
                  </span>
                  <span className="text-sm text-[color:var(--muted)]">
                    {(neighbor.similarity * 100).toFixed(1)}%
                  </span>
                </Link>
              ))}
            </div>
          </div>

          <div className="card p-5">
            <div className="label mb-2">Least similar linked pages</div>
            <div className="overflow-hidden rounded-subtle border border-line">
              {detail.least_similar_neighbors.map((neighbor) => (
                <Link
                  key={neighbor.page_id}
                  href={`/page/${neighbor.page_id}?source=${source}`}
                  className="grid grid-cols-[1fr_auto] gap-3 border-t border-line px-4 py-3 first:border-t-0 hover:bg-surface"
                >
                  <span className="flex items-center gap-2 text-sm font-medium text-ink">
                    {neighbor.title}
                    <ArrowUpRight size={14} className="text-[color:var(--muted)]" />
                  </span>
                  <span className="text-sm text-[color:var(--muted)]">
                    {(neighbor.similarity * 100).toFixed(1)}%
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
