"use client";
import { useEffect, useState } from "react";
import { api, STATUS_LABEL } from "@/lib/client";
import RequestTable, { Req } from "./RequestTable";

type Data = { requests: Req[]; counts: Record<string, number>; this_week: number; reply_target_days: number };

// P2 ホーム(届いた希望)。/staff と /staff/requests の両方で使う
export default function RequestsView({ greet }: { greet: boolean }) {
  const [data, setData] = useState<Data | null>(null);
  const [name, setName] = useState("");
  const [filter, setFilter] = useState<string>("all");
  const [err, setErr] = useState("");
  useEffect(() => {
    api<Data>("staff/requests").then(setData).catch((e) => setErr(e.message));
    api("staff/session").then((d) => setName(d.staff.display_name.split(" ")[0])).catch(() => {});
  }, []);
  if (err) return <div className="err">{err}</div>;
  if (!data) return <p className="muted">読み込んでいます…</p>;
  const shown = filter === "all" ? data.requests : data.requests.filter((r) => r.status === filter);
  return (
    <div className="stack">
      <h1>{greet ? `こんにちは、${name}さん` : "届いた希望"}</h1>
      <div className="row">
        <div className="card stat"><div className="k">新しい希望</div><div className="v blue">{data.counts.new}件</div></div>
        <div className="card stat"><div className="k">返事を待っている</div><div className="v">{data.counts.replied}件</div></div>
        <div className="card stat"><div className="k">今週の予定</div><div className="v">{data.this_week}件</div></div>
      </div>
      <div className="row" style={{ alignItems: "center" }}>
        <h2 style={{ margin: 0, flex: "none" }}>届いた希望</h2>
        <div className="chips">
          {["all", "new", "replied", "scheduled", "done", "declined"].map((s) => (
            <button key={s} className={filter === s ? "chip on" : "chip"} onClick={() => setFilter(s)}>
              {s === "all" ? "すべて" : `${STATUS_LABEL[s]} ${data.counts[s]}`}
            </button>
          ))}
        </div>
      </div>
      <RequestTable items={shown} />
      <p className="muted">新着は {data.reply_target_days} 日以内の返事を目安にしています。</p>
    </div>
  );
}
