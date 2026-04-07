import { Buffer } from "node:buffer";

import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

import { notionCookieNames, notionOauthConfigured, oauthErrorRedirect } from "@/lib/auth";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

type NotionTokenResponse = {
  access_token: string;
  refresh_token: string;
  workspace_id: string;
  workspace_name?: string | null;
};

export async function GET(request: NextRequest) {
  if (!notionOauthConfigured()) {
    return NextResponse.redirect(
      new URL(oauthErrorRedirect("Notion OAuth is not configured."), request.url)
    );
  }

  const { searchParams } = request.nextUrl;
  const error = searchParams.get("error");
  const code = searchParams.get("code");
  const state = searchParams.get("state");

  if (error) {
    return NextResponse.redirect(
      new URL(oauthErrorRedirect(`Notion authorization failed: ${error}`), request.url)
    );
  }

  if (!code || !state) {
    return NextResponse.redirect(
      new URL(oauthErrorRedirect("Missing OAuth callback parameters."), request.url)
    );
  }

  const cookieStore = await cookies();
  const storedState = cookieStore.get(notionCookieNames.oauthState)?.value;

  if (!storedState || storedState !== state) {
    return NextResponse.redirect(
      new URL(oauthErrorRedirect("OAuth state check failed."), request.url)
    );
  }

  const clientId = process.env.NOTION_OAUTH_CLIENT_ID!;
  const clientSecret = process.env.NOTION_OAUTH_CLIENT_SECRET!;
  const redirectUri = process.env.NOTION_OAUTH_REDIRECT_URI!;
  const basicAuth = Buffer.from(`${clientId}:${clientSecret}`).toString("base64");

  const tokenResponse = await fetch("https://api.notion.com/v1/oauth/token", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Basic ${basicAuth}`,
      "Notion-Version": "2026-03-11"
    },
    body: JSON.stringify({
      grant_type: "authorization_code",
      code,
      redirect_uri: redirectUri
    })
  });

  if (!tokenResponse.ok) {
    return NextResponse.redirect(
      new URL(oauthErrorRedirect("Could not exchange the Notion authorization code."), request.url)
    );
  }

  const tokenPayload = (await tokenResponse.json()) as NotionTokenResponse;

  const scoreResponse = await fetch(`${API_BASE_URL}/score`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      notion_token: tokenPayload.access_token
    })
  });

  if (!scoreResponse.ok) {
    return NextResponse.redirect(
      new URL(oauthErrorRedirect("Connected to Notion, but initial scoring failed."), request.url)
    );
  }

  const response = NextResponse.redirect(new URL("/dashboard?source=live", request.url));

  response.cookies.set(notionCookieNames.accessToken, tokenPayload.access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 7
  });
  response.cookies.set(notionCookieNames.refreshToken, tokenPayload.refresh_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 30
  });
  response.cookies.set(notionCookieNames.workspaceId, tokenPayload.workspace_id, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 30
  });
  if (tokenPayload.workspace_name) {
    response.cookies.set(notionCookieNames.workspaceName, tokenPayload.workspace_name, {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
      maxAge: 60 * 60 * 24 * 30
    });
  }
  response.cookies.delete(notionCookieNames.oauthState);

  return response;
}
