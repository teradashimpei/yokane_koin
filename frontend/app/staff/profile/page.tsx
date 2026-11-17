"use client";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/client";

type Tag = { id: number; kind: "specialty" | "private"; name: string; selected: boolean };
type Ep = { id: number; title: string; body: string; status: string };
type Me = { profile: any; tags: Tag[]; tag_range: Record<string, [number, number]>; episodes: Ep[]; value_tags: (string | null)[] };
const FIELDS: [string, string, boolean][] = [["area", "担当エリア", false], ["job_title", "業務担当", false], ["intro_text", "自己紹介", true], ["personality_text", "人柄・休日", true]];

// P5 プロフィール(お客さまからの見え方つき)
export default function Profile() {
  const [me, setMe] = useState<Me | null>(null);
  const [f, setF] = useState<any>(null);
  const [tagIds, setTagIds] = useState<number[]>([]);
  const [eps, setEps] = useState<Ep[]>([]);
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  const apply = (d: Me) => { setMe(d); setF({ ...d.profile }); setTagIds(d.tags.filter((t) => t.selected).map((t) => t.id)); setEps(d.episodes); };
  useEffect(() => { api<Me>("staff/me").then(apply).catch((e) => setErr(e.message)); }, []);
  if (err && !me) return <div className="err">{err}</div>;
  if (!me || !f) return <p className="muted">読み込んでいます…</p>;
  const hidden: string[] = f.hidden_fields ?? [];
  const toggleHide = (k: string) => setF({ ...f, hidden_fields: hidden.includes(k) ? hidden.filter((x) => x !== k) : [...hidden, k] });
  const save = async () => {
    setErr(""); setMsg("");
    try { apply(await api<Me>("staff/me/profile", { method: "PUT", body: { ...f, tag_ids: tagIds } })); setMsg("保存しました。お客さま側の画面に反映されます。"); }
    catch (e) { const x = e as ApiError; setErr(x.message); }
  };
  const saveEp = async (ep: Ep) => {
    try { const d = await api(`staff/me/episodes${ep.id ? "/" + ep.id : ""}`, { method: ep.id ? "PUT" : "POST", body: { title: ep.title, body: ep.body } }); setEps(d.episodes); setMsg("体験談を保存しました。運営の確認のあとで公開されます。"); }
    catch (e: any) { setErr(e.message); }
  };
  const tagsOf = (k: string) => me.tags.filter((t) => t.kind === k);
  const picked = (k: string) => me.tags.filter((t) => t.kind === k && tagIds.includes(t.id));
  const Hide = ({ k }: { k: string }) => <button className={hidden.includes(k) ? "chip" : "chip on"} style={{ flex: "none" }} onClick={() => toggleHide(k)}>{hidden.includes(k) ? "見せない" : "見せる"}</button>;
  return (
    <div className="stack">
      <h1>プロフィール</h1>
      {msg && <div className="okmsg">{msg}</div>}{err && <div className="err">{err}</div>}
      <div className="row" style={{ alignItems: "flex-start" }}>
        <div className="card stack" style={{ flex: 1.8 }}>
          <div><label className="f">名前（お客さまに見える名前）</label><input className="inp" value={f.name} maxLength={50} onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
          <div><label className="f">ひと言（一覧に出る）</label><input className="inp" value={f.one_liner ?? ""} maxLength={100} onChange={(e) => setF({ ...f, one_liner: e.target.value })} /></div>
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
          <button className="btn" onClick={save}>保存する</button>
          <h2 style={{ marginTop: 24 }}>本人の体験（3本まで）</h2>
          <p className="muted" style={{ margin: 0 }}>書き直すと下書きに戻り、運営が確かめてから公開されます。スワイプのカードにも使われることがあります。</p>
          {[...eps, ...(eps.length < 3 ? [{ id: 0, title: "", body: "", status: "new" }] : [])].map((ep, i) => (
            <div key={ep.id || "new" + i} className="card stack" style={{ padding: 16 }}>
              <div className="row" style={{ alignItems: "center" }}><b style={{ flex: "none" }}>体験 {i + 1}</b><span style={{ flex: "none" }} className={`badge ${ep.status === "published" ? "b-scheduled" : "b-replied"}`}>{ep.status === "published" ? "公開中" : ep.status === "draft" ? "確認待ち" : "新しく書く"}</span></div>
              <input className="inp" placeholder="見出し（50字まで）" maxLength={50} defaultValue={ep.title} onChange={(e) => (ep.title = e.target.value)} />
              <textarea className="inp" placeholder="本文（400字まで）" maxLength={400} defaultValue={ep.body} onChange={(e) => (ep.body = e.target.value)} />
              <button className="btn sub" onClick={() => saveEp(ep)}>この体験を保存</button>
            </div>
          ))}
        </div>
        <div className="stack" style={{ position: "sticky", top: 24 }}>
          <b>お客さまからの見え方</b>
          <div className="preview stack">
            <div className="row" style={{ alignItems: "center" }}>
              <div className="avatar" style={{ flex: "none", width: 56, height: 56, fontSize: 22 }}>{f.name.slice(0, 1)}</div>
              <div><b style={{ fontSize: 18 }}>{f.name}さん</b><div className="muted">{picked("specialty").map((t) => t.name).join("・")}</div></div>
            </div>
            <div className="chips">{me.value_tags.filter(Boolean).map((v) => <span key={v!} className="chip on">{v}</span>)}</div>
            {f.one_liner && <div>「{f.one_liner}」</div>}
            {FIELDS.filter(([k]) => !hidden.includes(k) && f[k]).map(([k, label]) => <div key={k}><div className="muted">{label}</div>{f[k]}</div>)}
            {!hidden.includes("private_tags") && <div className="chips">{picked("private").map((t) => <span key={t.id} className="chip">{t.name}</span>)}</div>}
            <div className="note">まずは聞くだけでも大丈夫。決めるのはお客さまです</div>
            {!f.accepting && <div className="err">いまは新しい希望を受けていません（一覧に出ません）</div>}
          </div>
          <p className="muted">「見せない」にした項目は、お客さまには表示されません。年齢は出しません。</p>
        </div>
      </div>
    </div>
  );
}
