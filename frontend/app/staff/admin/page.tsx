"use client";
import { useEffect, useState } from "react";
import { api, fmtDate } from "@/lib/client";

type S = { headline: string; good_text: string; regret_text: string; trigger_title: string; trigger_body: string; hesitation_title: string; hesitation_body: string };
type Draft = { speaker_id: number; speaker_name: string; submitted_at: string; situation_label: string | null; current_situation_label: string | null; draft: S; qas: { question: string; answer: string }[]; current: S | null };
const ROWS: [keyof S, string][] = [["headline", "カードの一言"], ["good_text", "やって良かったこと"], ["regret_text", "後悔していること"], ["trigger_title", "きっかけ（見出し）"], ["trigger_body", "きっかけ（本文）"], ["hesitation_title", "迷ったこと（見出し）"], ["hesitation_body", "迷ったこと（本文）"]];

// 運営だけ: 経験談の書き直しの確認(S-04・S-09)と CSV 書き出し(S-18)
export default function Admin() {
  const [drafts, setDrafts] = useState<Draft[] | null>(null); const [err, setErr] = useState(""); const [msg, setMsg] = useState("");
  const load = () => api<{ drafts: Draft[] }>("admin/story-drafts").then((d) => setDrafts(d.drafts)).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);
  const publish = async (d: Draft) => {
    try { await api(`admin/story-drafts/${d.speaker_id}/publish`, { method: "POST" }); setMsg(`${d.speaker_name}さんの経験談を公開しました。お客さまの画面にすぐ出ます。`); load(); }
    catch (e: any) { setErr(e.message); }
  };
  return (
    <div className="stack">
      <h1>運営</h1>
      {msg && <div className="okmsg">{msg}</div>}{err && <div className="err">{err}</div>}
      <div className="card stack"><h2>記録の書き出し</h2><p className="muted" style={{ margin: 0 }}>申し込み・どこから来たか・お客さまの状況・返事・面談・記録をCSVで出します。名前・連絡先・メモ・年収は入りません。</p><a className="btn" style={{ alignSelf: "flex-start" }} href="/api/admin/export">CSVを書き出す</a></div>
      <div className="card stack"><h2>確認待ちの経験談</h2>
        <p className="muted" style={{ margin: 0 }}>行員が書き直した経験談です。金額と今の年齢は送る時点で止めています。言い回しや中身を確かめてから公開してください。</p>
        {drafts?.length === 0 && <p className="muted">ありません</p>}
        {drafts?.map((d) => (
          <div key={d.speaker_id} className="card stack" style={{ padding: 16 }}>
            <div className="row" style={{ alignItems: "center" }}><b style={{ flex: "none" }}>{d.speaker_name}さん</b><span className="muted" style={{ flex: "none" }}>{fmtDate(d.submitted_at)} に送信</span></div>
            <table className="list"><thead><tr><th style={{ width: 150 }}>項目</th><th>いま公開中</th><th>書き直し</th></tr></thead>
              <tbody>
                <tr><td>状況の札</td><td>{d.current_situation_label ?? "—"}</td><td style={{ fontWeight: d.situation_label !== d.current_situation_label ? 700 : 400 }}>{d.situation_label ?? "（変えない）"}</td></tr>
                {ROWS.map(([k, l]) => { const changed = d.current?.[k] !== d.draft[k]; return (
                  <tr key={k}><td>{l}</td><td className="muted" style={{ whiteSpace: "pre-wrap" }}>{d.current?.[k] ?? "—"}</td><td style={{ whiteSpace: "pre-wrap", fontWeight: changed ? 700 : 400, background: changed ? "#fff8e8" : undefined }}>{d.draft[k]}</td></tr>); })}
                {d.qas.map((q, i) => <tr key={i}><td>Q&A {i + 1}</td><td className="muted">—</td><td><b>Q. {q.question}</b><div>{q.answer}</div></td></tr>)}
              </tbody>
            </table>
            <button className="btn" style={{ alignSelf: "flex-start" }} onClick={() => publish(d)}>確かめたので公開する</button>
          </div>
        ))}
      </div>
    </div>
  );
}
