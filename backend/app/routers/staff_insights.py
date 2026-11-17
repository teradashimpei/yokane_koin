"""S-17 お客さんの傾向(P6)。自分宛ての申し込みの集計だけ。名前・連絡先・メモは使わない。

人数が staff_insights_min_people(仮5)に届かないうちは出さない(SN-03)。
考えの傾向は「考えを見せてよい」に同意した人だけで数え、その人数も同じ基準で判定する。
"""
import json
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import Connection, text

from app.db import get_db
from app.deps import Staff, require_speaker
from app.services.settings_repo import get_setting

router = APIRouter()


@router.get("/v1/staff/insights")
def insights(staff: Staff = Depends(require_speaker), db: Connection = Depends(get_db)):
    min_people = int(get_setting(db, "staff_insights_min_people", 5))
    rows = db.execute(text(
        "SELECT mr.id, mr.status, mr.preferences, mr.ask_topics, mr.meeting_method, mr.share_result, mr.diagnosis_id, "
        "rec.held, rec.next_promise, rec.topics FROM meeting_requests mr "
        "LEFT JOIN meeting_records rec ON rec.request_id = mr.id "
        "WHERE mr.speaker_id = :s AND (mr.expires_at IS NULL OR mr.expires_at > CURRENT_TIMESTAMP(3))"
    ), {"s": staff.speaker_id}).mappings().all()
    total = len(rows)
    if total < min_people:
        return {"enough": False, "total": total, "min_people": min_people}

    held = sum(1 for r in rows if r["held"])
    promised = sum(1 for r in rows if r["held"] and r["next_promise"])
    replied = sum(1 for r in rows if r["status"] != "new")
    ask = Counter(t for r in rows for t in (json.loads(r["ask_topics"]) if r["ask_topics"] else []))
    prefs = Counter(t for r in rows for t in json.loads(r["preferences"]))
    talked = Counter(t for r in rows for t in (json.loads(r["topics"]) if r["topics"] else []))
    method = Counter(r["meeting_method"] for r in rows)

    shared = [r["diagnosis_id"] for r in rows if r["share_result"] and r["diagnosis_id"] is not None]
    axes_out = None
    if len(shared) >= min_people:
        axes = db.execute(text("SELECT id, code, internal_name FROM axes ORDER BY display_order")).all()
        labels = get_setting(db, "value_tag_labels", {})
        lv = Counter()
        q = text("SELECT axis_id, level FROM diagnosis_axis_scores WHERE diagnosis_id = :d")
        for d in shared:
            for aid, level in db.execute(q, {"d": d}).all():
                lv[(aid, level)] += 1
        axes_out = [{
            "code": code,
            "levels": [{"level": level, "label": (labels.get(code) or {}).get(str(level), str(level)),
                        "count": lv[(aid, level)]} for level in (-1, 0, 1)],
        } for aid, code, _ in axes]

    def top(c: Counter) -> list:
        return [{"label": k, "count": v} for k, v in c.most_common()]

    return {
        "enough": True,
        "total": total,
        "min_people": min_people,
        "replied": replied,
        "held": held,
        "next_promise": promised,
        "ask_topics": top(ask),
        "talked_topics": top(talked),
        "preferences": top(prefs),
        "methods": top(method),
        "shared_count": len(shared),
        "axes": axes_out,
    }
