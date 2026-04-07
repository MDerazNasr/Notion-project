import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { notionCookieNames } from "@/lib/auth";

export async function POST() {
  const cookieStore = await cookies();

  Object.values(notionCookieNames).forEach((cookieName) => {
    cookieStore.delete(cookieName);
  });

  return NextResponse.json({ ok: true });
}
