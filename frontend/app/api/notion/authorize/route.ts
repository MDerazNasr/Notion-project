import crypto from "node:crypto";

import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

import { buildNotionAuthorizeUrl, notionCookieNames, notionOauthConfigured, oauthErrorRedirect } from "@/lib/auth";

export async function GET(request: NextRequest) {
  if (!notionOauthConfigured()) {
    return NextResponse.redirect(
      new URL(oauthErrorRedirect("Notion OAuth is not configured."), request.url)
    );
  }

  const state = crypto.randomUUID();
  const cookieStore = await cookies();

  cookieStore.set(notionCookieNames.oauthState, state, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 10
  });

  return NextResponse.redirect(buildNotionAuthorizeUrl(state));
}
