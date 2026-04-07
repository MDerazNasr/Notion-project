import { PageDetailResponse, ScoreResponse } from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const fallback = `${response.status} ${response.statusText}`;

    try {
      const payload = (await response.json()) as { detail?: string };
      const message = payload.detail ?? fallback;
      throw new Error(message);
    } catch (error) {
      if (error instanceof Error && error.message !== fallback) {
        throw error;
      }
      throw new Error(fallback);
    }
  }

  return (await response.json()) as T;
}

export async function requestDemoScore(): Promise<ScoreResponse> {
  const response = await fetch(`${API_BASE_URL}/score/demo`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    }
  });

  return readJson<ScoreResponse>(response);
}

export async function requestLiveScore(input: {
  notionToken: string;
  cohereApiKey?: string;
}): Promise<ScoreResponse> {
  const response = await fetch(`${API_BASE_URL}/score`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      notion_token: input.notionToken,
      cohere_api_key: input.cohereApiKey || undefined
    })
  });

  return readJson<ScoreResponse>(response);
}

export async function getScores(source: string): Promise<ScoreResponse> {
  const response = await fetch(
    `${API_BASE_URL}/scores?source=${encodeURIComponent(source)}`,
    {
      cache: "no-store"
    }
  );

  return readJson<ScoreResponse>(response);
}

export async function getPageDetail(
  pageId: string,
  source: string
): Promise<PageDetailResponse> {
  const response = await fetch(
    `${API_BASE_URL}/page/${encodeURIComponent(pageId)}?source=${encodeURIComponent(source)}`,
    {
      cache: "no-store"
    }
  );

  return readJson<PageDetailResponse>(response);
}
