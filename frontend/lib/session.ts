import "server-only";
import { createHmac, timingSafeEqual } from "node:crypto";

// 行員のログイン状態。Cookie には「行員ID.期限.署名」だけを入れる(内部キーはブラウザに出さない)
export const COOKIE = "yk_staff";
const HOURS = 12;

function secret(): string {
  const s = process.env.SESSION_SECRET;
  if (!s) throw new Error("SESSION_SECRET が設定されていません");
  return s;
}

function sign(v: string): string {
  return createHmac("sha256", secret()).update(v).digest("base64url");
}

export function makeToken(staffId: number): string {
  const body = `${staffId}.${Date.now() + HOURS * 3600_000}`;
  return `${body}.${sign(body)}`;
}

export function readToken(token: string | undefined): number | null {
  if (!token) return null;
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  const [id, exp, sig] = parts;
  const expected = Buffer.from(sign(`${id}.${exp}`));
  const got = Buffer.from(sig);
  if (expected.length !== got.length || !timingSafeEqual(expected, got)) return null;
  if (Number(exp) < Date.now() || !/^\d+$/.test(id)) return null;
  return Number(id);
}

export const COOKIE_OPTS = { httpOnly: true, sameSite: "lax" as const, path: "/", maxAge: HOURS * 3600, secure: process.env.NODE_ENV === "production" };
