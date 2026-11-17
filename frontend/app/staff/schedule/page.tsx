"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, fmtDate, METHOD_LABEL } from "@/lib/client";

type Item = { request_id: number; requester_name: string; ask_topics: string[]; pre_question: string; status: string; starts_at: string; method: string; place: string; recorded: boolean };
type Rec = { held: boolean; topics: string[]; next_promise: boolean; memo: string };

// P4 予定と話したあとのメモ
function Schedule() {
  const q = useSearchParams();
  const [items, setItems] = useState<Item[] | null>(null);
  const [sel, setSel] = useState<number | null>(null);
  const [topics, setTopics] = useState<string[]>([]);
  const [rec, setRec] = useState<Rec>({ held: true, topics: [], next_promise: false, memo: "" });
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  const load = () => api<{ items: Item[] }>("staff/schedule").then((d) => {
    setItems(d.items);
    const want = Number(q.get("r")) || d.items.find((i) => !i.recorded)?.request_id || d.items[0]?.request_id || null;
    setSel((s) => s ?? want);
  }).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (!sel) return;
    setMsg("");
    api(`staff/requests/${sel}`).then((d) => { setTopics(d.record_topics); setRec(d.request.record ?? { held: true, topics: [], next_promise: false, memo: "" }); });
  }, [sel]);
  if (err) return <div className="err">{err}</div>;
  if (!items) return <p className="muted">読み込んでいます…</p>;
  const cur = items.find((i) => i.request_id === sel);
  const now = new Date();
  const save = async () => {
    try { await api(`staff/requests/${sel}/record`, { method: "PUT", body: rec }); setMsg("保存しました。この記録は「お客さんの傾向」に数えられます（メモは数えません）。"); load(); }
    catch (e: any) { setErr(e.message); }
  };
  return (
    <div className="stack">
      <h1>予定</h1>
      <div className="row" style={{ alignItems: "flex-start" }}>
        <div className="card stack" style={{ flex: 1.1 }}>
          {items.length === 0 && <p className="muted">決まった予定はまだありません</p>}
          {items.map((i) => (
            <button key={i.request_id} onClick={() => setSel(i.request_id)} className="card" style={{ width: "100%", textAlign: "left", cursor: "pointer", borderColor: sel === i.request_id ? "var(--sky)" : undefined, background: sel === i.request_id ? "var(--pale)" : undefined }}>
              <div className="muted">{fmtDate(i.starts_at)}〜{new Date(i.starts_at) < now ? "（終わった）" : ""}</div>
              <b>{i.requester_name}さん</b>　{i.pre_question || i.ask_topics[0] || ""}
              <div className="muted">{METHOD_LABEL[i.method]}{i.place && `（${i.place}）`}　{i.recorded ? "記録あり" : "記録まだ"}</div>
            </button>
          ))}
        </div>
        <div className="card stack">
          {cur ? (<>
            <h2>話したあとのメモ：{cur.requester_name}さん</h2>
            <p className="muted" style={{ margin: 0 }}>お客さんには見えません。次に話すときの自分のためのメモです。</p>
            <div><label className="f">話せましたか</label>
              <div className="chips">{[true, false].map((v) => <button key={String(v)} className={rec.held === v ? "chip on" : "chip"} onClick={() => setRec({ ...rec, held: v, next_promise: v ? rec.next_promise : false })}>{v ? "話せた" : "話せなかった"}</button>)}</div>
            </div>
            <div><label className="f">話したテーマ（いくつでも）</label>
              <div className="chips">{topics.map((t) => <button key={t} className={rec.topics.includes(t) ? "chip on" : "chip"} onClick={() => setRec({ ...rec, topics: rec.topics.includes(t) ? rec.topics.filter((x) => x !== t) : [...rec.topics, t] })}>{t}</button>)}</div>
            </div>
            <div><label className="f">次も話す約束</label>
              <div className="chips">{[true, false].map((v) => <button key={String(v)} disabled={!rec.held} className={rec.next_promise === v ? "chip on" : "chip"} onClick={() => setRec({ ...rec, next_promise: v })}>{v ? "あり" : "なし"}</button>)}</div>
            </div>
            <div><label className="f">メモ（自分だけ）</label><textarea className="inp" maxLength={1000} value={rec.memo} onChange={(e) => setRec({ ...rec, memo: e.target.value })} /></div>
            {msg && <div className="okmsg">{msg}</div>}
            <button className="btn" onClick={save}>メモを保存する</button>
          </>) : <p className="muted">左の予定を選んでください</p>}
        </div>
      </div>
    </div>
  );
}

export default function Page() { return <Suspense><Schedule /></Suspense>; }
