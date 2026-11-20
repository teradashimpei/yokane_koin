"""Streamlit 版(デモデータだけで動く行員の画面)のためのデータを書き出す。

ローカルの DB に apply_db を流した直後に動かす(デモの時刻は「流した時刻」から作られているため)。
API をこのプロセスの中で呼ぶので、uvicorn を立てなくてよい。

    cd backend
    .venv/bin/python -m scripts.apply_db
    .venv/bin/python -m scripts.make_streamlit_snapshot

書き出し先: ../streamlit/data/snapshot.json
年収の幅・行員の年齢は API が返さないので、ここにも入らない。
"""
import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import get_settings
from app.db import get_engine
from app.main import app
from app.services.settings_repo import get_setting

OUT = Path(__file__).resolve().parents[2] / "streamlit" / "data" / "snapshot.json"
STAFF_ID, ADMIN_ID = 1, 4     # make_demo_seed.py: 1 = 森下 由美(ST0009)、4 = 運営


def main() -> None:
    c = TestClient(app)
    key = get_settings().internal_api_key

    def get(path: str, staff: int = STAFF_ID) -> dict:
        r = c.get(path, headers={"X-Internal-Key": key, "X-Staff-Id": str(staff)})
        r.raise_for_status()
        return r.json()

    listing = get("/v1/staff/requests")
    details = [get(f"/v1/staff/requests/{r['id']}") for r in listing["requests"]]
    with get_engine().connect() as db:
        db.execute(text("SET time_zone = '+09:00'"))
        now = db.execute(text("SELECT DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s+09:00')")).scalar()
        axes = [code for (code,) in db.execute(text("SELECT code FROM axes ORDER BY display_order"))]
        qs = [{"id": i, "axis": code, "direction": d} for i, code, d in db.execute(text(
            "SELECT q.id, a.code, q.direction FROM questions q JOIN axes a ON a.id = q.axis_id ORDER BY q.question_no"))]
        scoring = {"axes": axes, "questions": qs, "thresholds": get_setting(db, "level_thresholds"),
                   "labels": get_setting(db, "value_tag_labels", {})}
        min_people = int(get_setting(db, "staff_insights_min_people", 5))
    snap = {
        "taken_at": now,
        "staff": get("/v1/staff/session")["staff"],
        "requests": [d["request"] for d in details],
        "decline_reasons": details[0]["decline_reasons"] if details else [],
        "record_topics": details[0]["record_topics"] if details else [],
        "reply_target_days": listing["reply_target_days"],
        "me": get("/v1/staff/me"),
        "questions": get("/v1/staff/questions")["questions"],
        "insights": get("/v1/staff/insights"),
        "insights_min_people": min_people,
        "scoring": scoring,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT, "requests", len(snap["requests"]), "taken_at", now)


if __name__ == "__main__":
    main()
