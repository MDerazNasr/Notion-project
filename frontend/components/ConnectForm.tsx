"use client";

import { useRouter } from "next/navigation";
import { ArrowRight, DatabaseZap, LoaderCircle } from "lucide-react";
import { useState } from "react";

import { requestDemoScore, requestLiveScore } from "@/lib/api";

export function ConnectForm() {
  const router = useRouter();
  const [notionToken, setNotionToken] = useState("");
  const [cohereApiKey, setCohereApiKey] = useState("");
  const [isSubmitting, setIsSubmitting] = useState<"demo" | "live" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function startDemo() {
    setIsSubmitting("demo");
    setError(null);

    try {
      await requestDemoScore();
      router.push("/dashboard?source=demo");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not score demo workspace.");
    } finally {
      setIsSubmitting(null);
    }
  }

  async function scoreLiveWorkspace() {
    setIsSubmitting("live");
    setError(null);

    try {
      await requestLiveScore({
        notionToken,
        cohereApiKey
      });
      router.push("/dashboard?source=live");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not score workspace.");
    } finally {
      setIsSubmitting(null);
    }
  }

  return (
    <div className="card p-6 sm:p-8">
      <div className="mb-8 flex items-start justify-between gap-4">
        <div>
          <div className="label mb-2">Connect workspace</div>
          <h2 className="text-2xl font-medium tracking-[-0.03em] text-ink">
            Score trustworthiness page by page
          </h2>
        </div>
        <span className="rounded-subtle border border-line bg-surface px-3 py-2 text-sm text-[color:var(--muted)]">
          FastAPI + Next.js
        </span>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="mb-2 block text-sm font-medium text-ink">
            Notion integration token
          </span>
          <input
            className="field"
            placeholder="secret_..."
            value={notionToken}
            onChange={(event) => setNotionToken(event.target.value)}
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-medium text-ink">
            Cohere API key
          </span>
          <input
            className="field"
            placeholder="Optional"
            value={cohereApiKey}
            onChange={(event) => setCohereApiKey(event.target.value)}
          />
        </label>
      </div>

      <div className="mt-3 rounded-subtle border border-line bg-surface px-4 py-3 text-sm text-[color:var(--muted)]">
        Live mode crawls the current workspace through the Notion API. Demo mode uses the hand-crafted 28-page fixture from the technical plan.
      </div>

      {error ? (
        <div className="mt-4 rounded-subtle border border-[rgba(182,93,74,0.2)] bg-[rgba(255,221,210,0.46)] px-4 py-3 text-sm text-ink">
          {error}
        </div>
      ) : null}

      <div className="mt-6 flex flex-col gap-3 sm:flex-row">
        <button
          type="button"
          className="button button-primary"
          onClick={startDemo}
          disabled={isSubmitting !== null}
        >
          {isSubmitting === "demo" ? (
            <LoaderCircle size={16} className="animate-spin" />
          ) : (
            <DatabaseZap size={16} />
          )}
          Try demo workspace
        </button>

        <button
          type="button"
          className="button button-secondary"
          onClick={scoreLiveWorkspace}
          disabled={isSubmitting !== null || !notionToken.trim()}
        >
          {isSubmitting === "live" ? (
            <LoaderCircle size={16} className="animate-spin" />
          ) : (
            <ArrowRight size={16} />
          )}
          Score live workspace
        </button>
      </div>
    </div>
  );
}
