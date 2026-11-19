"use client";
import { useEffect, useState } from "react";
import { api, ApiError, fmtDate } from "@/lib/client";

type Tag = { id: number; kind: "specialty" | "private"; name: string; selected: boolean };
type QA = { question: string; answer: string };
type Story = { headline: string; good_text: string; regret_text: string; trigger_title: string; trigger_body: string; hesitation_title: string; hesitation_body: string; qas: QA[] };
type Draft = Story & { situation_label: string | null; submitted_at: string };
type Me = { profile: any; tags: Tag[]; tag_range: Record<string, [number, number]>; story: Story | null; story_draft: Draft | null; value_tags: (string | null)[] };
type Edit = Story & { situation_label: string };
type FieldErr = { field: string; reason: string };

const FIELDS: [string, string, boolean][] = [["area", "担当エリア", false], ["job_title", "業務担当", false], ["intro_text", "自己紹介", true], ["personality_text", "人柄・休日", true]];
// お客さまの A5(経験談の詳細)と同じ見出し。[列, 見出し, 最大文字数, 長文か]
const STORY: [keyof Story, string, number, boolean][] = [
  ["headline", "カードの一言（一覧に出る）", 100, false], ["good_text", "やって良かったこと", 600, true], ["regret_text", "後悔していること", 600, true],
  ["trigger_title", "きっかけ（見出し）", 50, false], ["trigger_body", "きっかけ（本文）", 600, true],
  ["hesitation_title", "迷ったこと（見出し）", 50, false], ["hesitation_body", "迷ったこと（本文）", 600, true],
];
const EMPTY: Edit = { headline: "", good_text: "", regret_text: "", trigger_title: "", trigger_body: "", hesitation_title: "", hesitation_body: "", qas: Array.from({ length: 4 }, () => ({ question: "", answer: "" })), situation_label: "" };
const REASON: Record<string, string> = { money: "金額（円・万円・年収）は書けません", age: "今の年齢は書けません" };

// P5 プロフィールと経験談(お客さまからの見え方つき)
export default function Profile() {
  const [me, setMe] = useState<Me | null>(null);
  const [f, setF] = useState<any>(null);
  const [tagIds, setTagIds] = useState<number[]>([]);
  const [st, setSt] = useState<Edit>(EMPTY);
  const [fieldErr, setFieldErr] = useState<FieldErr[]>([]);
  const [tab, setTab] = useState<"ep" | "qa" | "pr">("ep");
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  const apply = (d: Me) => {
    setMe(d); setF({ ...d.profile }); setTagIds(d.tags.filter((t) => t.selected).map((t) => t.id));
    const src = d.story_draft ?? d.story;
    setSt(src ? { ...src, qas: src.qas.map((q) => ({ ...q })), situation_label: d.story_draft?.situation_label ?? d.profile.situation_label ?? "" } : { ...EMPTY, situation_label: d.profile.situation_label ?? "" });
  };
  useEffect(() => { api<Me>("staff/me").then(apply).catch((e) => setErr(e.message)); }, []);
  if (err && !me) return <div className="err">{err}</div>;
  if (!me || !f) return <p className="muted">読み込んでいます…</p>;
  const hidden: string[] = f.hidden_fields ?? [];
  const toggleHide = (k: string) => setF({ ...f, hidden_fields: hidden.includes(k) ? hidden.filter((x) => x !== k) : [...hidden, k] });
  const say = (m: string) => { setMsg(m); setErr(""); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const save = async () => {
    try { apply(await api<Me>("staff/me/profile", { method: "PUT", body: { ...f, tag_ids: tagIds } })); say("基本情報を保存しました。お客さま側の画面に反映されます。"); }
    catch (e) { setErr((e as ApiError).message); }
  };
  const saveStory = async () => {
    setFieldErr([]);
    try { apply(await api<Me>("staff/me/story", { method: "PUT", body: st })); say("経験談の書き直しを送りました。運営が確かめてから、お客さまの画面に出ます。"); }
    catch (e) { const x = e as ApiError; setErr(x.message); setFieldErr(Array.isArray(x.fields) ? (x.fields as FieldErr[]) : []); }
  };
  const discard = async () => { apply(await api<Me>("staff/me/story", { method: "DELETE" })); setFieldErr([]); say("書き直しを取り消しました。公開中の経験談はそのままです。"); };
  const errOf = (k: string) => fieldErr.filter((x) => x.field === k).map((x) => REASON[x.reason] ?? "入力を確かめてください");
  const tagsOf = (k: string) => me.tags.filter((t) => t.kind === k);
  const picked = (k: string) => me.tags.filter((t) => t.kind === k && tagIds.includes(t.id));
  const Hide = ({ k }: { k: string }) => <button className={hidden.includes(k) ? "chip" : "chip on"} style={{ flex: "none" }} onClick={() => toggleHide(k)}>{hidden.includes(k) ? "見せない" : "見せる"}</button>;
  const Err = ({ k }: { k: string }) => <>{errOf(k).map((m) => <div key={m} className="fielderr">{m}</div>)}</>;
  const alumni = `西南・${f.faculty ?? ""}${f.gender === "女性" ? "OG" : "OB"}`;
  return (
    <div className="stack">
      <h1>プロフィールと経験談</h1>
      {msg && <div className="okmsg">{msg}</div>}{err && <div className="err">{err}</div>}
      <div className="row" style={{ alignItems: "flex-start" }}>
        <div className="stack" style={{ flex: 1.8 }}>
          <div className="card stack">
            <div className="row" style={{ alignItems: "center" }}>
              <h2 style={{ margin: 0 }}>経験談</h2>
              <div style={{ flex: "none" }}>{me.story_draft
                ? <span className="badge b-replied">確認待ちの書き直しあり（{fmtDate(me.story_draft.submitted_at)}）</span>
                : <span className="badge b-scheduled">公開中</span>}</div>
            </div>
            <p className="muted" style={{ margin: 0 }}>お客さまが「近い人の経験談」で読む、あなたの経験です。書き直すと運営が確かめてから公開されます（それまでは今の文が出ます）。金額（円・万円・年収）と今の年齢は、本人が特定されやすいので書けません。</p>
            <div><label className="f">状況の札（例　家を買って3年）</label><input className="inp" value={st.situation_label} maxLength={30} onChange={(e) => setSt({ ...st, situation_label: e.target.value })} /></div>
            {STORY.map(([k, label, max, long]) => (
              <div key={k}><label className="f">{label}</label>
                {long ? <textarea className={`inp${errOf(k).length ? " bad" : ""}`} rows={3} value={st[k] as string} maxLength={max} onChange={(e) => setSt({ ...st, [k]: e.target.value })} />
                  : <input className={`inp${errOf(k).length ? " bad" : ""}`} value={st[k] as string} maxLength={max} onChange={(e) => setSt({ ...st, [k]: e.target.value })} />}
                <Err k={k} /></div>
            ))}
            <h2 style={{ marginTop: 12, marginBottom: 0 }}>Q&A（4問）</h2>
            <p className="muted" style={{ margin: 0 }}>直接話す前に、お客さまがよく聞きたくなることへの答えを先に載せます。</p>
            {st.qas.map((qa, i) => (
              <div key={i} className="stack" style={{ gap: 6 }}>
                <input className={`inp${errOf(`qas.${i + 1}.question`).length ? " bad" : ""}`} placeholder={`Q${i + 1} 問い`} value={qa.question} maxLength={200}
                  onChange={(e) => setSt({ ...st, qas: st.qas.map((x, j) => (j === i ? { ...x, question: e.target.value } : x)) })} />
                <Err k={`qas.${i + 1}.question`} />
                <textarea className={`inp${errOf(`qas.${i + 1}.answer`).length ? " bad" : ""}`} rows={2} placeholder={`A${i + 1} 答え`} value={qa.answer} maxLength={600}
                  onChange={(e) => setSt({ ...st, qas: st.qas.map((x, j) => (j === i ? { ...x, answer: e.target.value } : x)) })} />
                <Err k={`qas.${i + 1}.answer`} />
              </div>
            ))}
            <div className="btns">
              <button className="btn" onClick={saveStory}>書き直しを送る（運営が確かめてから公開）</button>
              {me.story_draft && <button className="btn ghost" onClick={discard}>書き直しを取り消す</button>}
            </div>
          </div>

          <div className="card stack">
            <h2 style={{ margin: 0 }}>基本情報（プロフィールのタブ）</h2>
            <div><label className="f">名前（お客さまに見える名前）</label><input className="inp" value={f.name} maxLength={50} onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
            <div><label className="f">ひと言</label><input className="inp" value={f.one_liner ?? ""} maxLength={100} onChange={(e) => setF({ ...f, one_liner: e.target.value })} /></div>
            {FIELDS.map(([k, label, long]) => (
              <div key={k}><label className="f">{label}</label>
                <div className="row" style={{ gap: 8, alignItems: "flex-start" }}>
                  {long ? <textarea className="inp" value={f[k] ?? ""} maxLength={1000} onChange={(e) => setF({ ...f, [k]: e.target.value })} /> : <input className="inp" value={f[k] ?? ""} maxLength={50} onChange={(e) => setF({ ...f, [k]: e.target.value })} />}
                  <Hide k={k} />
                </div></div>
            ))}
            {(["specialty", "private"] as const).map((k) => (
              <div key={k}><label className="f">{k === "specialty" ? "得意分野" : "プライベート"}のタグ（{me.tag_range[k][0]}〜{me.tag_range[k][1]}個）{k === "private" && <> <Hide k="private_tags" /></>}</label>
                <div className="chips">{tagsOf(k).map((t) => <button key={t.id} className={tagIds.includes(t.id) ? "chip on" : "chip"} onClick={() => setTagIds(tagIds.includes(t.id) ? tagIds.filter((x) => x !== t.id) : [...tagIds, t.id])}>{t.name}</button>)}</div></div>
            ))}
            <div><label className="f">新しい希望を受ける</label>
              <div className="chips">{[true, false].map((v) => <button key={String(v)} className={f.accepting === v ? "chip on" : "chip"} onClick={() => setF({ ...f, accepting: v })}>{v ? "受ける" : "いまは止める"}</button>)}</div></div>
            <button className="btn" onClick={save}>基本情報を保存する</button>
          </div>
        </div>

        <div className="stack" style={{ position: "sticky", top: 24, flex: 1, maxWidth: 380 }}>
          <b>お客さまからの見え方（経験談の詳細）</b>
          <div className="a5">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            {f.photo_url ? <img className="cover" src={f.photo_url} alt="" /> : <div className="cover" />}
            <div className="body">
              <b style={{ fontSize: 18 }}>{f.name}さんのこと</b>
              <div className="chips" style={{ gap: 4 }}>
                <span className="chip sit">{alumni}</span>
                {st.situation_label && <span className="chip sit">{st.situation_label}</span>}
                <span className="chip on" style={{ padding: "2px 10px", fontSize: 12 }}>福銀の行員</span>
              </div>
              <div className="tabs">{([["ep", "エピソード"], ["qa", "Q&A"], ["pr", "プロフィール"]] as const).map(([k, l]) => <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>)}</div>
              {tab === "ep" && (<>
                <div className="ep good"><b>やって良かったこと</b>{st.good_text || "—"}</div>
                <div className="ep regret"><b>後悔していること</b>{st.regret_text || "—"}</div>
                <div className="ep"><b>きっかけ｜{st.trigger_title}</b>{st.trigger_body || "—"}</div>
                <div className="ep"><b>迷ったこと｜{st.hesitation_title}</b>{st.hesitation_body || "—"}</div>
              </>)}
              {tab === "qa" && st.qas.map((q, i) => <div key={i} className="ep"><b>Q. {q.question || "—"}</b>{q.answer || "—"}</div>)}
              {tab === "pr" && (<>
                {f.one_liner && <div>「{f.one_liner}」</div>}
                <div className="chips">{me.value_tags.filter(Boolean).map((v) => <span key={v!} className="chip on">{v}</span>)}</div>
                {FIELDS.filter(([k]) => !hidden.includes(k) && f[k]).map(([k, label]) => <div key={k} style={{ fontSize: 13 }}><div className="muted">{label}</div>{f[k]}</div>)}
                <div className="muted" style={{ fontSize: 13 }}>得意分野　{picked("specialty").map((t) => t.name).join("・")}</div>
                {!hidden.includes("private_tags") && <div className="chips">{picked("private").map((t) => <span key={t.id} className="chip">{t.name}</span>)}</div>}
              </>)}
              <div className="cta">この人に話を聞いてみる</div>
              {!f.accepting && <div className="err">いまは新しい希望を受けていません</div>}
            </div>
          </div>
          <p className="muted" style={{ margin: 0 }}>一覧のカードには「カードの一言」が出ます：「{st.headline || "—"}」</p>
          <p className="muted" style={{ margin: 0 }}>「見せない」にした項目は表示されません。行員の年齢は出しません。</p>
        </div>
      </div>
    </div>
  );
}
