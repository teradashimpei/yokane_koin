"use client";
import Link from "next/link";
import { use, useEffect, useState } from "react";
import { api, Customer, customerLine, fmtDate, freeTextLabel, METHOD_LABEL, Source, STATUS_LABEL } from "@/lib/client";
import { Situations, SourceLine } from "@/components/RequestContext";

type Proposal = { id: number; starts_at: string; ends_at: string; method: string; place: string; chosen: boolean };
type Detail = {
  request: {
    id: number; requester_name: string; ask_topics: string[]; pre_question: string; preferences: string[]; meeting_method: string;
    created_at: string; status: string; overdue: boolean; decline_reason: string | null; share_result: boolean;
    result: { texts: string[]; same_levels: number; axes: number } | null; proposals: Proposal[];
    record: { held: boolean; topics: string[]; next_promise: boolean; memo: string } | null;
    source: Source; customer: Customer;
    story: { good_text: string; regret_text: string; trigger_title: string; trigger_body: string; hesitation_title: string; hesitation_body: string } | null;
  };
  decline_reasons: string[];
};

function nextDays(): string[] {
  const out: string[] = [];
  for (let i = 1; i <= 14; i++) { const d = new Date(); d.setDate(d.getDate() + i); out.push(d.toISOString().slice(0, 10)); }
  return out;
}
const TIMES = ["10:00", "12:00", "15:00", "18:00", "19:00", "19:30", "20:00"];

// P3 希望の詳細と返事。返事はボタンだけ(話せます=日にちの提案つき / 今回は見送る)
export default function RequestDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [d, setD] = useState<Detail | null>(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [slots, setSlots] = useState<{ date: string; time: string; method: string; place: string }[]>([]);
  const [mode, setMode] = useState<"" | "decline">("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { api<Detail>(`staff/requests/${id}`).then((x) => { setD(x); setSlots([{ date: nextDays()[1], time: "19:00", method: x.request.meeting_method, place: "" }]); }).catch((e) => setErr(e.message)); }, [id]);
  if (err) return <div className="err">{err}</div>;
  if (!d) return <p className="muted">読み込んでいます…</p>;
  const r = d.request;
  const canReply = r.status === "new" || r.status === "replied";
  const send = async (path: string, body: unknown, done: string) => {
    setBusy(true); setErr("");
    try { const x = await api<Detail>(`staff/requests/${id}/${path}`, { method: "POST", body }); setD(x); setMsg(done); setMode(""); }
    catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };
  const reply = () => send("reply", { proposals: slots.map((s) => ({ starts_at: `${s.date}T${s.time}:00`, method: s.method, place: s.place })) }, "返事を送りました。お客さまが日にちを選ぶと「予定」に入ります。");
  return (
    <div className="stack">
      <Link href="/staff" className="muted">← 届いた希望に戻る</Link>
      <div className="row" style={{ alignItems: "center" }}>
        <h1 style={{ margin: 0, flex: "none" }}>{r.requester_name}様からの希望</h1>
        <div style={{ flex: "none" }}><span className={`badge b-${r.status}`}>{STATUS_LABEL[r.status]}</span>{r.overdue && <> <span className="badge b-over">返事の目安を過ぎた</span></>}</div>
      </div>
      {msg && <div className="okmsg">{msg}</div>}
      <div className="row" style={{ alignItems: "flex-start" }}>
        <div className="card stack">
          <h2>お客さまのこと</h2>
          <div><label className="f">いまの状況</label>{r.customer.situations.length ? <Situations c={r.customer} max={9} /> : <span className="muted">選んでいません</span>}
            {customerLine(r.customer) && <div className="muted" style={{ marginTop: 4 }}>{customerLine(r.customer)}</div>}</div>
          <div><label className="f">どこから来たか</label><SourceLine s={r.source} />
            {r.story && (
              <details style={{ marginTop: 6 }}>
                <summary style={{ cursor: "pointer", color: "var(--primary)" }}>お客さまが読んだ経験談を見る</summary>
                <div className="story-box" style={{ marginTop: 8 }}>
                  <h3>やって良かったこと</h3><p>{r.story.good_text}</p>
                  <h3>後悔していること</h3><p>{r.story.regret_text}</p>
                  <h3>きっかけ｜{r.story.trigger_title}</h3><p>{r.story.trigger_body}</p>
                  <h3>迷ったこと｜{r.story.hesitation_title}</h3><p style={{ margin: 0 }}>{r.story.hesitation_body}</p>
                </div>
              </details>
            )}
            {r.source.route === "graduate_story" && <div className="note" style={{ marginTop: 6 }}>卒業生の話を読んで、考え方の近いあなたに届いた希望です。卒業生の名前はお客さまにも出していません。</div>}
          </div>
          {r.ask_topics.length > 0 && <div><label className="f">聞いてみたいこと</label>{r.ask_topics.map((t) => <div key={t}>・{t}</div>)}</div>}
          <div><label className="f">{freeTextLabel(r.source)}</label>{r.pre_question || "—"}</div>
          <div><label className="f">都合のいい時間帯・会い方</label>{r.preferences.length ? r.preferences.join("・") : "時間帯の指定なし"} ／ {METHOD_LABEL[r.meeting_method]}</div>
          <div>
            <label className="f">考えの近さ・お客さまの考え（12問から）</label>
            {r.result ? (<>
              <div><b>3つの軸のうち {r.result.same_levels} つがあなたと同じ</b></div>
              {r.result.texts.map((t) => <div key={t}>・{t}</div>)}
            </>) : <span className="muted">お客さまが「考えを見せてよい」にしていないので表示しません</span>}
          </div>
          <div className="muted">届いた日 {fmtDate(r.created_at)}</div>
        </div>
        <div className="card stack">
          <h2>返事</h2>
          {canReply && mode === "" && (<>
            <p className="muted" style={{ margin: 0 }}>話せる日にちを3つまで出せます。お客さまが1つ選ぶと決まります。</p>
            {slots.map((s, i) => (
              <div key={i} className="row" style={{ gap: 8 }}>
                <select className="inp" value={s.date} onChange={(e) => setSlots(slots.map((x, j) => j === i ? { ...x, date: e.target.value } : x))}>
                  {nextDays().map((v) => <option key={v} value={v}>{fmtDate(v + "T00:00:00", false)}</option>)}
                </select>
                <select className="inp" value={s.time} onChange={(e) => setSlots(slots.map((x, j) => j === i ? { ...x, time: e.target.value } : x))}>
                  {TIMES.map((t) => <option key={t}>{t}</option>)}
                </select>
                <select className="inp" value={s.method} onChange={(e) => setSlots(slots.map((x, j) => j === i ? { ...x, method: e.target.value } : x))}>
                  <option value="online">オンライン</option><option value="in_person">会って話す</option>
                </select>
                <button className="btn ghost" style={{ flex: "none" }} onClick={() => setSlots(slots.filter((_, j) => j !== i))}>×</button>
              </div>
            ))}
            {slots.length < 3 && <button className="btn sub" onClick={() => setSlots([...slots, { date: nextDays()[2 + slots.length], time: "19:00", method: r.meeting_method, place: "" }])}>＋ 日にちを足す</button>}
            <div className="btns">
              <button className="btn" disabled={busy} onClick={reply}>{r.status === "replied" ? "日にちを出し直す" : "話せます（返事を送る）"}</button>
              <button className="btn ghost" onClick={() => setMode("decline")}>今回は見送る</button>
            </div>
          </>)}
          {canReply && mode === "decline" && (<>
            <p style={{ margin: 0 }}>理由を選んでください（お客さまには「今回は難しそうです」とだけ伝わります）</p>
            <div className="btns">{d.decline_reasons.map((x) => <button key={x} className="btn sub" disabled={busy} onClick={() => send("decline", { reason: x }, "見送りました。")}>{x}</button>)}</div>
            <button className="btn ghost" onClick={() => setMode("")}>やめる</button>
          </>)}
          {r.proposals.length > 0 && (
            <div><label className="f">出した日にち</label>
              {r.proposals.map((p) => <div key={p.id}>{p.chosen ? "✔ " : "・"}{fmtDate(p.starts_at)}〜 {METHOD_LABEL[p.method]}{p.place && `（${p.place}）`}{p.chosen && <b>（お客さまが選んだ）</b>}</div>)}
            </div>
          )}
          {r.status === "declined" && <div className="muted">見送った理由：{r.decline_reason}</div>}
          {(r.status === "scheduled" || r.status === "done") && <Link className="btn sub" href={`/staff/schedule?r=${r.id}`}>予定と記録へ</Link>}
          <div className="note">売り込みはしない約束です。まずは話を聞くところから。</div>
        </div>
      </div>
    </div>
  );
}
