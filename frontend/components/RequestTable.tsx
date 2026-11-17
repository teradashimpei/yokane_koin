"use client";
import { useRouter } from "next/navigation";
import { STATUS_LABEL, fmtDate } from "@/lib/client";

export type Req = { id: number; requester_name: string; ask_topics: string[]; pre_question: string; preferences: string[]; created_at: string; status: string; overdue: boolean };

export default function RequestTable({ items }: { items: Req[] }) {
  const router = useRouter();
  if (!items.length) return <div className="card muted">まだありません</div>;
  return (
    <table className="list">
      <thead><tr><th style={{ width: 140 }}>名前</th><th>聞きたいこと</th><th style={{ width: 160 }}>時間帯</th><th style={{ width: 130 }}>届いた日</th><th style={{ width: 150 }}>状態</th></tr></thead>
      <tbody>
        {items.map((r) => (
          <tr key={r.id} className="click" onClick={() => router.push(`/staff/requests/${r.id}`)}>
            <td><b>{r.requester_name}</b>さん</td>
            <td>{r.pre_question || r.ask_topics.join(" / ") || "—"}</td>
            <td>{r.preferences.join("・")}</td>
            <td>{fmtDate(r.created_at)}</td>
            <td><span className={`badge b-${r.status}`}>{STATUS_LABEL[r.status]}</span>{r.overdue && <> <span className="badge b-over">返事の目安を過ぎた</span></>}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
