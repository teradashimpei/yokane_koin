"use client";
import { useRouter } from "next/navigation";
import { STATUS_LABEL, fmtDate, fmtWait } from "@/lib/client";

export type Req = { id: number; requester_name: string; ask_topics: string[]; pre_question: string; preferences: string[]; meeting_method: string; created_at: string; status: string; overdue: boolean; waiting_hours: number | null };
const METHOD: Record<string, string> = { online: "オンライン", in_person: "会って話す" };

export default function RequestTable({ items }: { items: Req[] }) {
  const router = useRouter();
  if (!items.length) return <div className="card muted">当てはまる希望はありません</div>;
  return (
    <table className="list">
      <thead><tr><th style={{ width: 120 }}>名前</th><th>聞きたいこと</th><th style={{ width: 190 }}>希望の時間帯・会い方</th><th style={{ width: 110 }}>届いた日</th><th style={{ width: 160 }}>状態</th><th style={{ width: 110 }}>待っている時間</th></tr></thead>
      <tbody>
        {items.map((r) => (
          <tr key={r.id} className="click" onClick={() => router.push(`/staff/requests/${r.id}`)}>
            <td><b>{r.requester_name}様</b></td>
            <td>{r.pre_question || r.ask_topics.join(" / ") || "—"}</td>
            <td className="muted" style={{ fontSize: 13 }}>{r.preferences.join("・")}・{METHOD[r.meeting_method]}</td>
            <td className="muted" style={{ fontSize: 13 }}>{fmtDate(r.created_at)}</td>
            <td><span className={`badge b-${r.status}`}>{STATUS_LABEL[r.status]}</span></td>
            <td style={{ color: r.overdue ? "var(--err)" : undefined, fontWeight: r.overdue ? 700 : 400 }}>{fmtWait(r.waiting_hours)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
