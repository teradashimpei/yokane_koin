"""S-17 お客さんの傾向(P6)。自分宛ての申し込みの集計だけ。名前・連絡先・メモは使わない。

人数が staff_insights_min_people(仮5)に届かないうちは出さない(SN-03)。
考えの傾向は「考えを見せてよい」に同意した人だけで数え、その人数も同じ基準で判定する。
今の状況(A2)・年代(A1)・どの経験談から来たかも数える。年収の幅はだれにも見せない(要件8.1)ので数えない。
"""
import json
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import Connection, bindparam, text

from app.db import get_db
from app.deps import Staff, require_speaker
from app.services.settings_repo import get_setting

router = APIRouter()


@router.get("/v1/staff/insights")
def insights(staff: Staff = Depends(require_speaker), db: Connection = Depends(get_db)):
    min_people = int(get_setting(db, "staff_insights_min_people", 5))
    rows = db.execute(text(
        "SELECT mr.id, mr.user_id, mr.status, mr.preferences, mr.ask_topics, mr.meeting_method, mr.share_result, "
        "mr.diagnosis_id, wr.id AS writer_id, wr.kind AS writer_kind, cp.age_band, "
        "rec.held, rec.next_promise, rec.topics FROM meeting_requests mr "
        "LEFT JOIN meeting_records rec ON rec.request_id = mr.id "
        "LEFT JOIN stories st ON st.id = mr.story_id LEFT JOIN speakers wr ON wr.id = st.speaker_id "
        "LEFT JOIN customer_profiles cp ON cp.user_id = mr.user_id "
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
    route_label = {"own": "あなたの経験談を読んで", "graduate": "卒業生の経験談から", "direct": "経験談を通らずに"}
    routes = Counter(route_label["direct" if r["writer_id"] is None else
                                 ("own" if r["writer_id"] == staff.speaker_id else "graduate")] for r in rows)
    ages = {o["code"]: o["label"] for o in get_setting(db, "age_band_options", [])}
    age_count = Counter(ages.get(r["age_band"], "答えていない") for r in rows)
    users = sorted({r["user_id"] for r in rows if r["user_id"] is not None})
    situations = Counter()
    if users:
        q = text("SELECT s.label FROM customer_situations cs JOIN situations s ON s.code = cs.situation_code "
                 "WHERE cs.user_id IN :ids").bindparams(bindparam("ids", expanding=True))
        situations.update(label for (label,) in db.execute(q, {"ids": users}).all())

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
        "situations": top(situations),
        "routes": top(routes),
        "age_bands": top(age_count),
        "shared_count": len(shared),
        "axes": axes_out,
    }
