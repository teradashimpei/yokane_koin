"""ローカル・デモ用のDBを作り直す。中身は消える。

  python -m scripts.apply_db            # base_schema → 001_staff → demo_seed → 話し手の点を計算
  python -m scripts.apply_db --no-seed  # データなし(テスト用)

本番(Azure)では yokane-back がお客さん側のテーブルを持つので、db/migrations/*.sql だけを流す。
"""
import argparse
from pathlib import Path

from sqlalchemy import Connection, text

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "db"


def run_sql(conn: Connection, path: Path) -> None:
    for stmt in path.read_text(encoding="utf-8").split(";\n"):
        body = "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("--")).strip()
        if body:
            conn.execute(text(body))


def reset(conn: Connection, seed: bool = True) -> None:
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
    for (name,) in conn.execute(text("SHOW TABLES")).all():
        conn.execute(text(f"DROP TABLE `{name}`"))
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    run_sql(conn, DB / "base_schema.sql")
    for m in sorted((DB / "migrations").glob("*.sql")):
        run_sql(conn, m)
    if seed:
        run_sql(conn, DB / "demo_seed.sql")
        recalc_speakers(conn)


def recalc_speakers(conn: Connection) -> int:
    import json

    from app.services import scoring

    th = json.loads(conn.execute(text("SELECT value FROM app_settings WHERE setting_key='level_thresholds'")).scalar())
    axes = conn.execute(text("SELECT id, code FROM axes ORDER BY display_order")).all()
    qs = [scoring.Question(i, c, d) for i, c, d in conn.execute(text(
        "SELECT q.id, a.code, q.direction FROM questions q JOIN axes a ON a.id = q.axis_id"))]
    answers: dict = {}
    for s, qid, a in conn.execute(text("SELECT speaker_id, question_id, answer FROM speaker_answers")):
        answers.setdefault(s, {})[qid] = a
    for s, ans in answers.items():
        ev = scoring.evaluate(ans, qs, [c for _, c in axes], scoring.Thresholds(th["minus_max"], th["plus_min"]))
        conn.execute(text("DELETE FROM speaker_axis_scores WHERE speaker_id = :s"), {"s": s})
        for aid, code in axes:
            conn.execute(text("INSERT INTO speaker_axis_scores VALUES (:s, :a, :sc, :lv)"),
                         {"s": s, "a": aid, "sc": ev.scores[code], "lv": ev.levels[code]})
        conn.execute(text("UPDATE speakers SET pattern = :p WHERE id = :s"), {"p": ev.pattern, "s": s})
    return len(answers)


def main() -> None:
    from app.db import get_engine

    p = argparse.ArgumentParser()
    p.add_argument("--no-seed", action="store_true")
    a = p.parse_args()
    with get_engine().begin() as conn:
        reset(conn, seed=not a.no_seed)
    print("DBを作り直しました" + ("" if a.no_seed else "(デモデータ入り)"))


if __name__ == "__main__":
    main()
