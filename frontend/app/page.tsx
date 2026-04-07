import Link from "next/link";
import { ArrowRight, CheckCircle2, Sparkles } from "lucide-react";

import { ConnectForm } from "@/components/ConnectForm";

const highlights = [
  "Ranks pages with calibrated reliability scores, not raw classifier output.",
  "Combines structural drift with Cohere-based semantic signals.",
  "Surfaces page-level reasons instead of a single workspace health number."
];

export default function HomePage() {
  return (
    <main className="pb-16 pt-8 sm:pb-24 sm:pt-12">
      <div className="shell">
        <header className="mb-10 grid gap-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
          <section className="rounded-notion border border-line bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(247,246,243,0.92))] p-7 shadow-card sm:p-10">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-line bg-white px-3 py-1.5 text-sm text-[color:var(--muted)]">
              <Sparkles size={14} />
              Knowledge reliability scoring for Notion workspaces
            </div>

            <h1 className="max-w-3xl text-4xl font-medium tracking-[-0.055em] text-ink sm:text-6xl">
              Find the pages your team should stop trusting.
            </h1>

            <p className="mt-5 max-w-2xl text-base leading-7 text-[color:var(--muted)] sm:text-lg">
              NotionPulse crawls a workspace, measures structural and semantic drift,
              and returns a reliability estimate for every page. The UI mirrors
              Notion&apos;s restraint: soft surfaces, quiet status colors, and no noise.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="#connect" className="button button-primary">
                Open workspace
                <ArrowRight size={16} />
              </Link>
              <Link href="/dashboard?source=demo" className="button button-secondary">
                View demo dashboard
              </Link>
            </div>
          </section>

          <aside className="card p-6 sm:p-8">
            <div className="label mb-3">What this scores</div>
            <div className="space-y-4">
              {highlights.map((item) => (
                <div key={item} className="flex gap-3 border-b border-line pb-4 last:border-b-0 last:pb-0">
                  <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-[color:var(--accent)]" />
                  <p className="text-sm leading-6 text-[color:var(--muted)]">{item}</p>
                </div>
              ))}
            </div>
          </aside>
        </header>

        <section
          id="connect"
          className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]"
        >
          <ConnectForm />

          <div className="card p-6">
            <div className="label mb-3">Scoring rubric</div>
            <div className="space-y-4 text-sm leading-6 text-[color:var(--muted)]">
              <p>
                <strong className="font-medium text-ink">Green</strong> pages are
                recently maintained, well-linked, and semantically aligned with
                their neighbors.
              </p>
              <p>
                <strong className="font-medium text-ink">Amber</strong> pages show
                mixed signals such as moderate age or weak graph support.
              </p>
              <p>
                <strong className="font-medium text-ink">Red</strong> pages tend to
                be stale, orphaned, or drifting away from the surrounding docs.
              </p>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
