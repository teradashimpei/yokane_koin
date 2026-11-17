"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/client";

type Ep = { id: number; speaker_name: string; title: string; body: string; axis: string | null; direction: number | null };

// 運営だけ: 体験談の公開確認(S-04・S-09)と CSV 書き出し(S-18)
export default function Admin() {
  const [eps, setEps] = useState<Ep[] | null>(null); const [err, setErr] = useState("");
  const load = () => api<{ episodes: Ep[] }>("admin/episodes").then((d) => setEps(d.episodes)).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);
  const publish = async (id: number, axis: string, direction: number) => { await api(`admin/episodes/${id}/publish`, { method: "POST", body: { axis, direction } }); load(); };
  return (
    <div className="stack">
      <h1>運営</h1>
      {err && <div className="err">{err}</div>}
      <div className="card stack"><h2>記録の書き出し</h2><p className="muted" style={{ margin: 0 }}>申し込み・返事・面談・記録をCSVで出します。名前・連絡先・メモは入りません。</p><a className="btn" style={{ alignSelf: "flex-start" }} href="/api/admin/export">CSVを書き出す</a></div>
      <div className="card stack"><h2>確認待ちの体験談</h2>
        {eps?.length === 0 && <p className="muted">ありません</p>}
        {eps?.map((e) => (
          <div key={e.id} className="card stack" style={{ padding: 16 }}>
            <b>{e.speaker_name}：{e.title}</b><div>{e.body}</div>
            <div className="btns">{["L", "C", "M"].flatMap((a) => [1, -1].map((d) => <button key={a + d} className="btn sub" onClick={() => publish(e.id, a, d)}>{a}{d > 0 ? "＋" : "−"}で公開</button>))}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
