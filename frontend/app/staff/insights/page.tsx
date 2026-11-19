"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/client";

type Count = { label: string; count: number };
type Data = { enough: boolean; total: number; min_people: number; replied?: number; held?: number; next_promise?: number;
  ask_topics?: Count[]; talked_topics?: Count[]; preferences?: Count[]; shared_count?: number;
  situations?: Count[]; routes?: Count[]; age_bands?: Count[];
  axes?: { code: string; levels: { level: number; label: string; count: number }[] }[] | null };
const AXIS_NAME: Record<string, string> = { L: "暮らし方", C: "決め方", M: "お金" };
const pct = (a: number, b: number) => (b ? Math.round((a / b) * 100) : 0);

function Bars({ items }: { items: Count[] }) {
  const max = Math.max(1, ...items.map((i) => i.count));
  if (!items.length) return <p className="muted">まだありません</p>;
  return <div className="stack" style={{ gap: 10 }}>{items.map((i) => (
    <div key={i.label} className="hbar" style={{ marginTop: 10 }}><span className="t">{i.label}</span><span className="track"><span className="fill" style={{ display: "block", width: `${(i.count / max) * 100}%` }} /></span><b>{i.count}件</b></div>
  ))}</div>;
}

// P6 お客さまの傾向(集計)。自分宛ての申し込みだけ。5人そろうまでは出さない
export default function Insights() {
  const [d, setD] = useState<Data | null>(null); const [err, setErr] = useState("");
  useEffect(() => { api<Data>("staff/insights").then(setD).catch((e) => setErr(e.message)); }, []);
  if (err) return <div className="err">{err}</div>;
  if (!d) return <p className="muted">読み込んでいます…</p>;
  return (
    <div className="stack">
      <h1>お客さまの傾向</h1>
      <p className="lead">あなたに「話を聞いてみたい」と送ってくれた人の傾向です。一人ひとりが分からない形でまとめています。</p>
      {!d.enough ? <div className="card">いま {d.total} 人です。{d.min_people} 人そろうと表示します。</div> : (<>
        <div className="row">
          <div className="card stat"><div className="k">届いた希望</div><div className="v blue">{d.total}件</div></div>
          <div className="card stat"><div className="k">会って話した</div><div className="v">{d.held}人</div><div className="muted">希望の{pct(d.held!, d.total)}%</div></div>
          <div className="card stat"><div className="k">次も話す約束</div><div className="v">{d.next_promise}人</div><div className="muted">会った人の{pct(d.next_promise!, d.held!)}%</div></div>
        </div>
        <div className="row" style={{ alignItems: "stretch" }}>
          <div className="card"><h2>いまの状況（お客さまが選んだもの）</h2><Bars items={d.situations!} /></div>
          <div className="card stack"><h2>どこから来たか</h2><Bars items={d.routes!} />
            <p className="muted" style={{ margin: 0 }}>「卒業生の経験談から」は、卒業生の話を読んで、考え方の近いあなたを選んだ人です。</p>
            <div><b>年代</b><div className="chips" style={{ marginTop: 6 }}>{d.age_bands!.map((a) => <span key={a.label} className="chip">{a.label} <b>{a.count}人</b></span>)}</div></div>
          </div>
        </div>
        <div className="row" style={{ alignItems: "stretch" }}>
          <div className="card stack">
            <h2>考えの傾向（12問の答えから）</h2>
            {d.axes ? d.axes.map((a) => {
              const tot = a.levels.reduce((s, l) => s + l.count, 0) || 1;
              const colors = ["var(--pale)", "var(--sky)", "var(--primary)"];
              return <div key={a.code}><b>{AXIS_NAME[a.code] ?? a.code}</b>
                <div className="bar" style={{ marginTop: 6 }}>{a.levels.map((l, i) => <span key={l.level} style={{ width: `${(l.count / tot) * 100}%`, background: colors[i] }} />)}</div>
                <div className="legend">{a.levels.map((l) => <span key={l.level}>{l.label} {l.count}人</span>)}</div></div>;
            }) : <p className="muted">「考えを見せてよい」にした人が {d.shared_count} 人です。{d.min_people} 人そろうと表示します。</p>}
          </div>
          <div className="card"><h2>聞いてみたいこと</h2><Bars items={d.ask_topics!} /></div>
        </div>
        <div className="row" style={{ alignItems: "stretch" }}>
          <div className="card"><h2>希望の時間帯</h2><div className="chips">{d.preferences!.map((p, i) => <span key={p.label} className={i === 0 ? "chip on" : "chip"}>{p.label} <b>{p.count}件</b></span>)}</div></div>
          <div className="card"><h2>話したテーマ</h2><Bars items={d.talked_topics!} /></div>
        </div>
      </>)}
      <p className="muted">集計は{d.min_people}人以上そろってから表示します。名前・連絡先・メモ・年収は集計に含めません。</p>
    </div>
  );
}
