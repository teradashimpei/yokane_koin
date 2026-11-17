"use client";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public fields?: unknown) { super(message); }
}

export async function api<T = any>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const res = await fetch(`/api/${path}`, {
    method: opts.method ?? "GET",
    headers: opts.body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && data?.error?.code === "LOGIN_REQUIRED" && typeof window !== "undefined") {
    window.location.href = "/staff/login";
  }
  if (!res.ok) throw new ApiError(res.status, data?.error?.code ?? "ERROR", data?.error?.message ?? "うまくいきませんでした", data?.error?.fields);
  return data as T;
}

export const STATUS_LABEL: Record<string, string> = {
  new: "新着", replied: "返事した", scheduled: "日にちが決まった", done: "終わった", declined: "見送った",
};
export const METHOD_LABEL: Record<string, string> = { online: "オンライン", in_person: "会って話す" };

export function fmtDate(iso: string | null | undefined, withTime = true): string {
  if (!iso) return "";
  const d = new Date(iso);
  const w = "日月火水木金土"[d.getDay()];
  const md = `${d.getMonth() + 1}/${d.getDate()}（${w}）`;
  return withTime ? `${md} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}` : md;
}
