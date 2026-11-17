"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/client";

const MENU = [
  { href: "/staff", label: "ホーム" },
  { href: "/staff/requests", label: "届いた希望", match: "/staff/requests" },
  { href: "/staff/schedule", label: "予定" },
  { href: "/staff/insights", label: "お客さんの傾向" },
  { href: "/staff/profile", label: "プロフィール" },
  { href: "/staff/answers", label: "12問の答え" },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [me, setMe] = useState<{ display_name: string; role: string } | null>(null);
  useEffect(() => { api("staff/session").then((d) => setMe(d.staff)).catch(() => {}); }, []);
  const logout = async () => { await fetch("/api/logout", { method: "POST" }); window.location.href = "/staff/login"; };
  const active = (m: (typeof MENU)[number]) => (m.match ? path.startsWith(m.match) : path === m.href);
  return (
    <div className="shell">
      <aside className="side">
        <div className="logo"><b>よかね</b><span>話し手用</span></div>
        <nav>
          {MENU.map((m) => <Link key={m.href} href={m.href} className={active(m) ? "item on" : "item"}>{m.label}</Link>)}
          {me?.role === "admin" && <Link href="/staff/admin" className={path === "/staff/admin" ? "item on" : "item"}>運営</Link>}
        </nav>
        <div className="me">
          <div className="avatar">{me?.display_name?.slice(0, 1) ?? ""}</div>
          <div><b>{me?.display_name ?? ""}</b><button className="linkbtn" onClick={logout}>ログアウト</button></div>
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
