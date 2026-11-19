import { Customer, Source, sourceText } from "@/lib/client";

// 一覧・ホームの行に出す「いまの状況」の札と「どこから来たか」の1行
export function Situations({ c, max = 3 }: { c: Customer; max?: number }) {
  if (!c.situations.length) return null;
  return (
    <span className="chips" style={{ display: "inline-flex", gap: 4 }}>
      {c.situations.slice(0, max).map((s) => <span key={s} className="chip sit">{s}</span>)}
      {c.situations.length > max && <span className="muted" style={{ fontSize: 12 }}>ほか{c.situations.length - max}つ</span>}
    </span>
  );
}

export function SourceLine({ s }: { s: Source }) {
  return (
    <div className={`src src-${s.route}`}>
      <span className="src-k">{sourceText(s)}</span>
      {s.headline && <span className="src-h">「{s.headline}」</span>}
    </div>
  );
}
