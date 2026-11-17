"use client";
import { useState } from "react";

// P1 話し手のログイン(デモ用: 登録済みのメール + チーム共通のパスコード)
export default function Login() {
  const [email, setEmail] = useState("");
  const [pass, setPass] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setErr("");
    const res = await fetch("/api/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, passcode: pass }) });
    const data = await res.json().catch(() => ({}));
    setBusy(false);
    if (res.ok) window.location.href = "/staff";
    else setErr(data?.error?.message ?? "ログインできませんでした");
  };
  return (
    <div className="login">
      <div className="hero">
        <h1 style={{ fontSize: 40, margin: 0 }}>よかね</h1>
        <p style={{ fontSize: 18, fontWeight: 700 }}>話し手のページ</p>
        <p style={{ opacity: .85 }}>お客さんから届いた「話を聞いてみたい」に返事をしたり、プロフィールを整えたりできます。</p>
      </div>
      <div className="form">
        <form onSubmit={submit} className="stack" style={{ width: 380 }}>
          <h2>ログイン</h2>
          <div><label className="f">メールアドレス</label><input className="inp" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="username" /></div>
          <div><label className="f">デモ用パスコード</label><input className="inp" type="password" value={pass} onChange={(e) => setPass(e.target.value)} required autoComplete="current-password" /></div>
          {err && <div className="err">{err}</div>}
          <button className="btn" style={{ width: "100%" }} disabled={busy}>{busy ? "確かめています…" : "ログイン"}</button>
          <p className="muted">デモ用のログインです。本番では職場のアカウントでログインする想定です。</p>
        </form>
      </div>
    </div>
  );
}
