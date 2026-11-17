"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, fmtDate, fmtWait, METHOD_LABEL } from "@/lib/client";

type Wait = { id: number; requester_name: string; ask_topics: string[]; pre_question: string; preferences: string[]; meeting_method: string; overdue: boolean; waiting_hours: number };
type Meet = { request_id: number; requester_name: string; ask_topics: string[]; pre_question: string; starts_at: string; ends_at?: string; method: string; place: string };
type Home = { now: string; reply_target_days: number; waiting: Wait[]; today: Meet[]; next: Meet | null; to_record: Meet[]; month: { requests: number; held: number; next_promise: number } };

const hm = (iso: string) => { const d = new Date(iso); return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`; };
const greet = (iso: string) => { const h = new Date(iso).getHours(); return h < 11 ? "おはようございます" : h < 18 ? "こんにちは" : "おつかれさまです"; };

// P2 ホーム(今日やること)。全件の一覧は P2-2(/staff/requests)
export default function HomePage() {
  const [d, setD] = useState<Home | null>(null);
  const [name, setName] = useState("");
  const [err, setErr] = useState("");
  useEffect(() => {
    api<Home>("staff/home").then(setD).catch((e) => setErr(e.message));
    api("staff/session").then((x) => setName(x.staff.display_name.split(" ")[0])).catch(() => {});
  }, []);
  if (err) return <div className="err">{err}</div>;
  if (!d) return <p className="muted">読み込んでいます…</p>;
  const todo = d.waiting.length + d.today.length + d.to_record.length;
  return (
    <div className="stack">
      <div>
        <h1>{greet(d.now)}、{name}さん</h1>
        <p className="lead" style={{ margin: 0 }}>{fmtDate(d.now, false)}　{todo ? <>今日やることは <b>{todo}件</b> です</> : "今日やることはありません"}</p>
      </div>
      <div className="row" style={{ alignItems: "stretch" }}>
        <div className="card">
          <div className="head"><h2>返事を待っているお客さま</h2><span className="count">{d.waiting.length}件</span><span className="sp" /><Link href="/staff/requests">届いた希望をすべて見る →</Link></div>
          {d.waiting.length === 0 && <p className="muted">返事が必要な希望はありません</p>}
          {d.waiting.map((w) => (
            <div key={w.id} className="wait-row">
              <div style={{ flex: 1, minWidth: 0 }}>
                <div><b style={{ fontSize: 16 }}>{w.requester_name}様</b>{w.overdue && <> <span className="badge b-over">目安の{d.reply_target_days}日を過ぎています</span></>}</div>
                <div>{w.pre_question || w.ask_topics.join(" / ")}</div>
                <div className="muted" style={{ color: w.overdue ? "var(--err)" : undefined }}>{w.preferences.join("・")}・{METHOD_LABEL[w.meeting_method]}　／　届いてから {fmtWait(w.waiting_hours)}</div>
              </div>
              <Link className="btn" href={`/staff/requests/${w.id}`}>返事する</Link>
            </div>
          ))}
        </div>
        <div className="card stack" style={{ flex: "none", width: 400 }}>
          <div className="head" style={{ margin: 0 }}><h2>今日の予定</h2><span className="count">{d.today.length}件</span></div>
          {d.today.length === 0 && <p className="muted" style={{ margin: 0 }}>今日の予定はありません</p>}
          {d.today.map((m) => (
            <div key={m.request_id} className="today">
              <div style={{ color: "var(--primary)", fontSize: 20, fontWeight: 700 }}>{hm(m.starts_at)}{m.ends_at ? ` – ${hm(m.ends_at)}` : ""}</div>
              <b style={{ fontSize: 16 }}>{m.requester_name}様　{METHOD_LABEL[m.method]}{m.place && `（${m.place}）`}</b>
              {(m.pre_question || m.ask_topics.length > 0) && <><div className="muted" style={{ fontWeight: 700 }}>先に聞きたいこと</div><div>{m.pre_question || m.ask_topics.join(" / ")}</div></>}
              <Link className="btn sub" style={{ alignSelf: "flex-start" }} href={`/staff/requests/${m.request_id}`}>お客さまの考えを見て準備する</Link>
            </div>
          ))}
          {d.next && <p className="muted" style={{ margin: 0 }}>次の予定　{fmtDate(d.next.starts_at)}　{d.next.requester_name}様（{METHOD_LABEL[d.next.method]}{d.next.place && `・${d.next.place}`}）</p>}
        </div>
      </div>
      <div className="row" style={{ alignItems: "stretch" }}>
        <div className="card">
          <div className="head"><h2>記録がまだの面談</h2><span className="count">{d.to_record.length}件</span></div>
          {d.to_record.length === 0 && <p className="muted">記録がまだの面談はありません</p>}
          {d.to_record.map((m) => (
            <div key={m.request_id} className="wait-row">
              <div style={{ flex: 1 }}><b style={{ fontSize: 16 }}>{fmtDate(m.starts_at, false)}　{m.requester_name}様</b><div className="muted">話せたか・話したテーマ・次の約束を残すと、今月の数字に入ります</div></div>
              <Link className="btn sub" href={`/staff/schedule?r=${m.request_id}`}>記録する</Link>
            </div>
          ))}
        </div>
        <div className="card" style={{ flex: "none", width: 400 }}>
          <div className="head"><h2>今月の数字</h2><span className="sp" /><Link href="/staff/insights">傾向を見る →</Link></div>
          <div className="row" style={{ gap: 24 }}>
            {[["届いた希望", `${d.month.requests}件`], ["会って話した", `${d.month.held}人`], ["次の約束", `${d.month.next_promise}人`]].map(([k, v]) => (
              <div key={k} style={{ flex: "none" }}><div className="muted">{k}</div><div style={{ fontSize: 20, fontWeight: 700 }}>{v}</div></div>
            ))}
          </div>
        </div>
      </div>
      <p className="muted">売り込みはしない約束です。まずはお客さまの話を聞くところから。</p>
    </div>
  );
}
