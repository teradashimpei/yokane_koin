"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/client";

type Q = { id: number; question_no: number; episode_text: string; summary: string; source_label: string; answer: number | null };
const CHOICES: [number, string][] = [[-1, "ちがうかも"], [0, "パス"], [1, "わかる"]];

// B2 話し手も12問に答える(お客さまと同じ質問。答えがマッチングに使われる)
export default function Answers() {
  const [qs, setQs] = useState<Q[] | null>(null);
  const [ans, setAns] = useState<Record<number, number>>({});
  const [i, setI] = useState(0);
  const [done, setDone] = useState<{ value_tags: (string | null)[] } | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { api<{ questions: Q[] }>("staff/questions").then((d) => { setQs(d.questions); setAns(Object.fromEntries(d.questions.filter((q) => q.answer !== null).map((q) => [q.id, q.answer!]))); }).catch((e) => setErr(e.message)); }, []);
  if (err) return <div className="err">{err}</div>;
  if (!qs) return <p className="muted">読み込んでいます…</p>;
  const q = qs[i];
  const pick = async (v: number) => {
    const next = { ...ans, [q.id]: v }; setAns(next);
    if (i < qs.length - 1) { setI(i + 1); return; }
    try { setDone(await api("staff/me/answers", { method: "PUT", body: { answers: next } })); } catch (e: any) { setErr(e.message); }
  };
  if (done) return (
    <div className="stack" style={{ maxWidth: 640 }}>
      <h1>答えを保存しました</h1>
      <p className="lead">あなたの考えのタグはこうなりました。お客さまの「考えが近い人」の並びに使われます。</p>
      <div className="chips">{done.value_tags.filter(Boolean).map((v) => <span key={v!} className="chip on">{v}</span>)}</div>
      <p className="muted">本人の体験と向きが大きく食い違っていないか、プロフィールで確かめてください。</p>
      <div className="btns"><a className="btn" href="/staff/profile">プロフィールへ</a><button className="btn ghost" onClick={() => { setDone(null); setI(0); }}>もう一度答える</button></div>
    </div>
  );
  return (
    <div className="stack" style={{ maxWidth: 640 }}>
      <h1>あなたも12問に答えてください</h1>
      <p className="lead">答えがマッチングに使われます。お客さまと同じ質問です。</p>
      <div className="muted">{i + 1} / {qs.length}</div>
      <div className="card stack">
        <b>{q.summary}</b>
        <div className="qcard">{q.episode_text}</div>
        <div className="muted">{q.source_label}</div>
      </div>
      <div className="btns">{CHOICES.map(([v, l]) => <button key={v} className={ans[q.id] === v ? "btn" : "btn sub"} onClick={() => pick(v)}>{l}</button>)}</div>
      {i > 0 && <button className="btn ghost" onClick={() => setI(i - 1)}>ひとつ戻す</button>}
    </div>
  );
}
