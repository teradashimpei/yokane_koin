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
  new: "返事が必要", replied: "お客さまの返事待ち", scheduled: "予定あり", done: "終わった", declined: "見送った",
};
export const METHOD_LABEL: Record<string, string> = { online: "オンライン", in_person: "会って話す" };

export function fmtDate(iso: string | null | undefined, withTime = true): string {
  if (!iso) return "";
  const d = new Date(iso);
  const w = "日月火水木金土"[d.getDay()];
  const md = `${d.getMonth() + 1}/${d.getDate()}（${w}）`;
  return withTime ? `${md} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}` : md;
}

export function fmtWait(h: number | null | undefined): string {
  if (h === null || h === undefined) return "—";
  if (h < 1) return "1時間以内";
  return h >= 24 ? `${Math.floor(h / 24)}日${h % 24 ? `${h % 24}時間` : ""}` : `${h}時間`;
}

// 申し込みの出どころ(どの経験談から来たか)と、お客さまの A1・A2。年収はAPIが返さない
export type Source = { route: "own_story" | "graduate_story" | "staff_story" | "direct"; story_id?: number; headline?: string; writer_label?: string; writer_situation?: string | null };
export type Customer = { faculty: string | null; age_band: string | null; situations: string[] };

export function sourceText(s: Source): string {
  if (s.route === "own_story") return "あなたの経験談を読んで";
  if (s.route === "graduate_story") return `卒業生（${s.writer_label}${s.writer_situation ? `・${s.writer_situation}` : ""}）の経験談から`;
  if (s.route === "staff_story") return `${s.writer_label}さんの経験談から`;
  return "経験談を通らずに";
}

// A6-2(卒業生の経験談から)の自由入力は「気になったこと」、08(行員の経験談から)は「先に聞きたいこと」
export const freeTextLabel = (s: Source) => (s.route === "graduate_story" ? "気になったこと" : "先に聞きたいこと");

export const customerLine = (c: Customer) => [c.age_band, c.faculty && `西南・${c.faculty}`].filter(Boolean).join("・");
