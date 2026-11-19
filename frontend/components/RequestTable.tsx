"use client";
import { useRouter } from "next/navigation";
import { Customer, Source, STATUS_LABEL, fmtDate, fmtWait } from "@/lib/client";
import { Situations, SourceLine } from "./RequestContext";

export type Req = { id: number; requester_name: string; ask_topics: string[]; pre_question: string; preferences: string[]; meeting_method: string; created_at: string; status: string; overdue: boolean; waiting_hours: number | null; source: Source; customer: Customer };
const METHOD: Record<string, string> = { online: "オンライン", in_person: "会って話す" };

export default function RequestTable({ items }: { items: Req[] }) {
  const router = useRouter();
  if (!items.length) return <div className="card muted">当てはまる希望はありません</div>;
  return (
    <table className="list">
      <thead><tr><th style={{ width: 110 }}>名前</th><th style={{ width: 150 }}>いまの状況</th><th>聞きたいこと・どこから来たか</th><th style={{ width: 140 }}>時間帯・会い方</th><th style={{ width: 100 }}>届いた日</th><th style={{ width: 140 }}>状態</th><th style={{ width: 90 }}>待っている時間</th></tr></thead>
      <tbody>
        {items.map((r) => (
          <tr key={r.id} className="click" onClick={() => router.push(`/staff/requests/${r.id}`)}>
            <td><b>{r.requester_name}様</b>{r.customer.age_band && <div className="muted" style={{ fontSize: 12 }}>{r.customer.age_band}</div>}</td>
            <td><Situations c={r.customer} max={2} />{!r.customer.situations.length && <span className="muted">—</span>}</td>
            <td><div>{r.pre_question || r.ask_topics.join(" / ") || "—"}</div><SourceLine s={r.source} /></td>
            <td className="muted" style={{ fontSize: 13 }}>{[...r.preferences, METHOD[r.meeting_method]].join("・")}</td>
            <td className="muted" style={{ fontSize: 13 }}>{fmtDate(r.created_at)}</td>
            <td><span className={`badge b-${r.status}`}>{STATUS_LABEL[r.status]}</span></td>
            <td style={{ color: r.overdue ? "var(--err)" : undefined, fontWeight: r.overdue ? 700 : 400 }}>{fmtWait(r.waiting_hours)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
