import { NextRequest, NextResponse } from "next/server";
import { callBackend } from "@/lib/backend";
import { COOKIE, COOKIE_OPTS, makeToken } from "@/lib/session";

export async function POST(req: NextRequest) {
  try {
    const res = await callBackend("/v1/staff/login", { method: "POST", body: await req.text() });
    const data = await res.json();
    if (!res.ok) return NextResponse.json(data, { status: res.status });
    const out = NextResponse.json(data);
    out.cookies.set(COOKIE, makeToken(data.staff.id), COOKIE_OPTS);
    return out;
  } catch {
    return NextResponse.json({ error: { code: "BACKEND_DOWN", message: "サーバーにつながりません" } }, { status: 502 });
  }
}
