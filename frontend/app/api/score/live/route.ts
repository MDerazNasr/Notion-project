import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { notionCookieNames } from "@/lib/auth";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function POST() {
  const cookieStore = await cookies();
  const notionToken = cookieStore.get(notionCookieNames.accessToken)?.value;

  if (!notionToken) {
    return NextResponse.json(
      { detail: "No Notion session found." },
      { status: 401 }
    );
  }

  const response = await fetch(`${API_BASE_URL}/score`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      notion_token: notionToken
    })
  });

  const payload = await response.text();

  return new NextResponse(payload, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("Content-Type") ?? "application/json"
    }
  });
}
