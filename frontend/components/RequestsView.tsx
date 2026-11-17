"use client";
import { useEffect, useMemo, useState } from "react";
import { api, STATUS_LABEL } from "@/lib/client";
import RequestTable, { Req } from "./RequestTable";

type Data = { requests: Req[]; counts: Record<string, number>; reply_target_days: number };
const TABS = ["all", "new", "replied", "scheduled", "done", "declined"];

// P2-2 届いた希望(一覧)。全件を状態・検索・並びで探す
export default function RequestsView() {
  const [data, setData] = useState<Data | null>(null);
  const [tab, setTab] = useState("all");
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<"wait" | "new">("wait");
  const [err, setErr] = useState("");
  useEffect(() => { api<Data>("staff/requests").then(setData).catch((e) => setErr(e.message)); }, []);
  const shown = useMemo(() => {
    if (!data) return [];
    const word = q.trim();
    const rows = data.requests.filter((r) => (tab === "all" || r.status === tab) &&
      (!word || r.requester_name.includes(word) || r.pre_question.includes(word) || r.ask_topics.some((t) => t.includes(word))));
    const rank = (r: Req) => (r.status === "new" ? 0 : 1);
    return [...rows].sort((a, b) => sort === "new" ? b.created_at.localeCompare(a.created_at)
      : rank(a) - rank(b) || a.created_at.localeCompare(b.created_at) * (rank(a) === 0 ? 1 : -1));
  }, [data, tab, q, sort]);
  if (err) return <div className="err">{err}</div>;
  if (!data) return <p className="muted">読み込んでいます…</p>;
  const total = data.requests.length;
  return (
    <div className="stack">
      <div className="row" style={{ alignItems: "center" }}>
        <div><h1>届いた希望</h1><p className="lead" style={{ margin: 0 }}>お客さまから届いた「話を聞いてみたい」の一覧です。行を押すと詳細と返事の画面に進みます。</p></div>
        <input className="inp" style={{ flex: "none", width: 320 }} placeholder="名前・聞きたいことで探す" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      <div className="row" style={{ alignItems: "center" }}>
        <div className="chips" style={{ flex: 1 }}>
          {TABS.map((s) => (
            <button key={s} className={tab === s ? "chip on" : "chip tab"} onClick={() => setTab(s)}>
              {s === "all" ? "すべて" : STATUS_LABEL[s]} <b style={{ color: s === "new" && data.counts.new ? "var(--err)" : undefined }}>{s === "all" ? total : data.counts[s]}</b>
            </button>
          ))}
        </div>
        <select className="inp" style={{ flex: "none", width: 260 }} value={sort} onChange={(e) => setSort(e.target.value as "wait" | "new")}>
          <option value="wait">並び：待っている時間が長い順</option>
          <option value="new">並び：届いた順（新しい順）</option>
        </select>
      </div>
      <RequestTable items={shown} />
      <p className="muted">{total}件中 {shown.length}件を表示　｜　返事の目安は届いてから{data.reply_target_days}日。過ぎたものは赤で出します。</p>
    </div>
  );
}
