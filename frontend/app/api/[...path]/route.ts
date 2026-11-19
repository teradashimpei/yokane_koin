import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { callBackend } from "@/lib/backend";
import { COOKIE, readToken } from "@/lib/session";

// BFF: 画面から /api/staff/... /api/admin/... を受け、/v1/... に中継する。ほかの道は通さない
const ALLOWED = /^(staff\/(me(\/profile|\/answers|\/story)?|questions|requests(\/\d+(\/(reply|decline|record))?)?|schedule|insights|session|home)|admin\/(export|story-drafts(\/\d+\/publish)?))$/;

async function relay(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const path = (await ctx.params).path.join("/");
  if (!ALLOWED.test(path)) return NextResponse.json({ error: { code: "NOT_FOUND", message: "見つかりません" } }, { status: 404 });
  const staffId = readToken((await cookies()).get(COOKIE)?.value);
  if (!staffId) return NextResponse.json({ error: { code: "LOGIN_REQUIRED", message: "ログインが必要です" } }, { status: 401 });
  const body = req.method === "GET" ? undefined : await req.text();
  try {
    const res = await callBackend(`/v1/${path}`, { method: req.method, body: body || undefined, staffId, query: req.nextUrl.search });
    const type = res.headers.get("content-type") ?? "application/json";
    const out = new NextResponse(await res.arrayBuffer(), { status: res.status, headers: { "content-type": type } });
    const disp = res.headers.get("content-disposition");
    if (disp) out.headers.set("content-disposition", disp);
    return out;
  } catch {
    return NextResponse.json({ error: { code: "BACKEND_DOWN", message: "サーバーにつながりません" } }, { status: 502 });
  }
}

export { relay as GET, relay as POST, relay as PUT, relay as DELETE };
