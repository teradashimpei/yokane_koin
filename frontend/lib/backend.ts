import "server-only";

// FastAPI(backend/)を呼ぶ。内部キーと行員IDはここで付ける
export async function callBackend(path: string, init: { method?: string; body?: string; staffId?: number | null; query?: string } = {}) {
  const base = process.env.BACKEND_BASE_URL;
  if (!base) throw new Error("BACKEND_BASE_URL が設定されていません");
  const headers: Record<string, string> = { "X-Internal-Key": process.env.INTERNAL_API_KEY ?? "" };
  if (init.body) headers["Content-Type"] = "application/json";
  if (init.staffId) headers["X-Staff-Id"] = String(init.staffId);
  return fetch(`${base}${path}${init.query ?? ""}`, { method: init.method ?? "GET", headers, body: init.body, cache: "no-store" });
}
