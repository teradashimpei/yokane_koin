import { NextResponse } from "next/server";
import { COOKIE } from "@/lib/session";

export async function POST() {
  const out = NextResponse.json({ ok: true });
  out.cookies.delete(COOKIE);
  return out;
}
