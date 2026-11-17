"""S-10〜S-16 届いた希望(P2)・詳細と返事(P3)・予定と記録(P4)。

見えるのは自分(話し手)宛ての申し込みだけ。ほかの話し手の申し込みIDは 404。
返事はボタンだけ(OK=日にちの提案つき/見送る)。メールは送らない(デモの決定)。
"""
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Connection, text

from app.db import get_db
from app.deps import Staff, log_staff_event, require_speaker
from app.errors import ApiError
from app.services.settings_repo import get_setting
from app.timefmt import iso

router = APIRouter()

STATUSES = ("new", "replied", "scheduled", "done", "declined")
NOT_EXPIRED = "(mr.expires_at IS NULL OR mr.expires_at > CURRENT_TIMESTAMP(3))"
_BASE = (
    "SELECT mr.id, mr.requester_name, mr.preferences, mr.meeting_method, mr.ask_topics, mr.pre_question, "
    "mr.created_at, mr.status, mr.replied_at, mr.decline_reason, mr.share_result, mr.diagnosis_id "
    "FROM meeting_requests mr WHERE mr.speaker_id = :s AND " + NOT_EXPIRED
)


def _row(r, target_days: int, now: datetime) -> dict:
    return {
        "id": r["id"],
        "requester_name": r["requester_name"] or "（名前なし）",
        "preferences": json.loads(r["preferences"]),
        "meeting_method": r["meeting_method"],
        "ask_topics": json.loads(r["ask_topics"]) if r["ask_topics"] else [],
        "pre_question": r["pre_question"] or "",
        "created_at": iso(r["created_at"]),
        "status": r["status"],
        "overdue": r["status"] == "new" and r["created_at"] < now - timedelta(days=target_days),
    }


def _own(db: Connection, staff: Staff, request_id: int):
    r = db.execute(text(_BASE + " AND mr.id = :i"), {"s": staff.speaker_id, "i": request_id}).mappings().first()
    if r is None:
        raise ApiError(404, "NOT_FOUND", "見つかりません")
    return r


def _now(db: Connection) -> datetime:
    return db.execute(text("SELECT CURRENT_TIMESTAMP(3)")).scalar()


@router.get("/v1/staff/requests")
def list_requests(status: str | None = Query(default=None), staff: Staff = Depends(require_speaker),
                  db: Connection = Depends(get_db)):
    if status is not None and status not in STATUSES:
        raise ApiError(422, "VALIDATION_ERROR", "入力に誤りがあります", [{"field": "status", "reason": "invalid"}])
    rows = db.execute(text(_BASE + " ORDER BY mr.created_at DESC, mr.id DESC"), {"s": staff.speaker_id}).mappings().all()
    days, now = int(get_setting(db, "staff_reply_target_days", 2)), _now(db)
    items = [_row(r, days, now) for r in rows]
    counts = {s: sum(1 for i in items if i["status"] == s) for s in STATUSES}
    week_end = now + timedelta(days=7)
    this_week = db.execute(text(
        "SELECT COUNT(*) FROM meeting_proposals p JOIN meeting_requests mr ON mr.id = p.request_id "
        "WHERE mr.speaker_id = :s AND mr.status = 'scheduled' AND p.chosen_at IS NOT NULL "
        "AND p.starts_at >= :a AND p.starts_at < :b"
    ), {"s": staff.speaker_id, "a": now, "b": week_end}).scalar()
    return {
        "requests": [i for i in items if status is None or i["status"] == status],
        "counts": counts,
        "this_week": this_week,
        "reply_target_days": days,
    }


def _result(db: Connection, staff: Staff, r) -> dict | None:
    """お客さんが「考えを見せてよい」に同意した申し込みだけ、結果の文と一致数を出す(S-11。SN-01)。"""
    if not r["share_result"] or r["diagnosis_id"] is None:
        return None
    mine = dict(db.execute(text(
        "SELECT axis_id, level FROM speaker_axis_scores WHERE speaker_id = :s"), {"s": staff.speaker_id}).all())
    rows = db.execute(text(
        "SELECT d.axis_id, d.level, rt.body FROM diagnosis_axis_scores d "
        "JOIN axes a ON a.id = d.axis_id LEFT JOIN result_texts rt ON rt.axis_id = d.axis_id AND rt.level = d.level "
        "WHERE d.diagnosis_id = :d ORDER BY a.display_order"
    ), {"d": r["diagnosis_id"]}).all()
    if not rows:
        return None
    return {
        "texts": [b for _, _, b in rows if b],
        "same_levels": sum(1 for aid, lv, _ in rows if mine.get(aid) == lv),
        "axes": len(rows),
    }


def _proposals(db: Connection, request_id: int) -> list:
    rows = db.execute(text(
        "SELECT id, starts_at, ends_at, method, place, chosen_at FROM meeting_proposals "
        "WHERE request_id = :r ORDER BY starts_at, id"), {"r": request_id}).mappings().all()
    return [{"id": p["id"], "starts_at": iso(p["starts_at"]), "ends_at": iso(p["ends_at"]), "method": p["method"],
             "place": p["place"] or "", "chosen": p["chosen_at"] is not None} for p in rows]


def _record(db: Connection, request_id: int) -> dict | None:
    r = db.execute(text("SELECT held, topics, next_promise, memo, recorded_at FROM meeting_records WHERE request_id = :r"),
                   {"r": request_id}).mappings().first()
    if r is None:
        return None
    return {"held": bool(r["held"]), "topics": json.loads(r["topics"]) if r["topics"] else [],
            "next_promise": bool(r["next_promise"]), "memo": r["memo"] or "", "recorded_at": iso(r["recorded_at"])}


@router.get("/v1/staff/requests/{request_id}")
def detail(request_id: int, staff: Staff = Depends(require_speaker), db: Connection = Depends(get_db)):
    r = _own(db, staff, request_id)
    item = _row(r, int(get_setting(db, "staff_reply_target_days", 2)), _now(db))
    item.update({
        "decline_reason": r["decline_reason"],
        "share_result": bool(r["share_result"]),
        "result": _result(db, staff, r),
        "proposals": _proposals(db, request_id),
        "record": _record(db, request_id),
    })
    return {
        "request": item,
        "decline_reasons": get_setting(db, "staff_decline_reasons", []),
        "record_topics": get_setting(db, "staff_record_topics", []),
    }


class Proposal(BaseModel):
    starts_at: datetime
    minutes: int = Field(default=30, ge=15, le=180)
    method: str
    place: str = Field(default="", max_length=100)

    @field_validator("method")
    @classmethod
    def _method(cls, v):
        if v not in ("in_person", "online"):
            raise ValueError("method")
        return v


class ReplyBody(BaseModel):
    proposals: list[Proposal] = Field(default=[], max_length=3)


@router.post("/v1/staff/requests/{request_id}/reply")
def reply(request_id: int, body: ReplyBody, staff: Staff = Depends(require_speaker), db: Connection = Depends(get_db)):
    """「話せます」ボタン。日にちは3つまで(0でもよい=OKだけ返す)。返事をし直すと提案は入れ替わる。"""
    r = _own(db, staff, request_id)
    if r["status"] not in ("new", "replied"):
        raise ApiError(409, "INVALID_STATUS", "この希望にはもう返事できません")
    db.execute(text("DELETE FROM meeting_proposals WHERE request_id = :r"), {"r": request_id})
    for p in body.proposals:
        start = p.starts_at.replace(tzinfo=None)
        db.execute(text(
            "INSERT INTO meeting_proposals (request_id, starts_at, ends_at, method, place) VALUES (:r, :a, :b, :m, :p)"
        ), {"r": request_id, "a": start, "b": start + timedelta(minutes=p.minutes), "m": p.method,
            "p": p.place.strip() or None})
    db.execute(text("UPDATE meeting_requests SET status = 'replied', replied_at = CURRENT_TIMESTAMP(3) WHERE id = :r"),
               {"r": request_id})
    log_staff_event(db, staff.id, "reply", request_id)
    db.commit()
    return detail(request_id, staff, db)


class DeclineBody(BaseModel):
    reason: str = Field(min_length=1, max_length=30)


@router.post("/v1/staff/requests/{request_id}/decline")
def decline(request_id: int, body: DeclineBody, staff: Staff = Depends(require_speaker),
            db: Connection = Depends(get_db)):
    """「今回は見送る」ボタン。理由はお客さんには出さない(S-13)。"""
    r = _own(db, staff, request_id)
    if r["status"] not in ("new", "replied"):
        raise ApiError(409, "INVALID_STATUS", "この希望はもう見送れません")
    if body.reason not in get_setting(db, "staff_decline_reasons", []):
        raise ApiError(422, "VALIDATION_ERROR", "入力に誤りがあります", [{"field": "reason", "reason": "invalid"}])
    db.execute(text("UPDATE meeting_requests SET status = 'declined', decline_reason = :d, "
                    "replied_at = COALESCE(replied_at, CURRENT_TIMESTAMP(3)) WHERE id = :r"),
               {"d": body.reason, "r": request_id})
    log_staff_event(db, staff.id, "decline", request_id)
    db.commit()
    return detail(request_id, staff, db)


@router.get("/v1/staff/schedule")
def schedule(staff: Staff = Depends(require_speaker), db: Connection = Depends(get_db)):
    rows = db.execute(text(
        "SELECT mr.id, mr.requester_name, mr.ask_topics, mr.pre_question, mr.status, "
        "p.starts_at, p.ends_at, p.method, p.place, (rec.request_id IS NOT NULL) AS recorded "
        "FROM meeting_requests mr JOIN meeting_proposals p ON p.request_id = mr.id AND p.chosen_at IS NOT NULL "
        "LEFT JOIN meeting_records rec ON rec.request_id = mr.id "
        "WHERE mr.speaker_id = :s AND mr.status IN ('scheduled','done') AND " + NOT_EXPIRED +
        " ORDER BY p.starts_at"), {"s": staff.speaker_id}).mappings().all()
    return {"items": [{
        "request_id": r["id"], "requester_name": r["requester_name"] or "（名前なし）",
        "ask_topics": json.loads(r["ask_topics"]) if r["ask_topics"] else [], "pre_question": r["pre_question"] or "",
        "status": r["status"], "starts_at": iso(r["starts_at"]), "ends_at": iso(r["ends_at"]),
        "method": r["method"], "place": r["place"] or "", "recorded": bool(r["recorded"]),
    } for r in rows]}


class RecordBody(BaseModel):
    held: bool
    topics: list[str] = Field(default=[], max_length=8)
    next_promise: bool = False
    memo: str = Field(default="", max_length=1000)


@router.put("/v1/staff/requests/{request_id}/record")
def record(request_id: int, body: RecordBody, staff: Staff = Depends(require_speaker),
           db: Connection = Depends(get_db)):
    """話したあとの記録(S-16)。保存すると「終わった」。memo はこの行員にだけ返す。"""
    r = _own(db, staff, request_id)
    if r["status"] not in ("scheduled", "done"):
        raise ApiError(409, "INVALID_STATUS", "日にちが決まった希望だけ記録できます")
    allowed = set(get_setting(db, "staff_record_topics", []))
    if any(t not in allowed for t in body.topics):
        raise ApiError(422, "VALIDATION_ERROR", "入力に誤りがあります", [{"field": "topics", "reason": "invalid"}])
    db.execute(text(
        "INSERT INTO meeting_records (request_id, held, topics, next_promise, memo) VALUES (:r, :h, :t, :n, :m) "
        "ON DUPLICATE KEY UPDATE held = VALUES(held), topics = VALUES(topics), next_promise = VALUES(next_promise), "
        "memo = VALUES(memo)"
    ), {"r": request_id, "h": body.held, "t": json.dumps(body.topics, ensure_ascii=False),
        "n": body.next_promise and body.held, "m": body.memo.strip() or None})
    db.execute(text("UPDATE meeting_requests SET status = 'done' WHERE id = :r"), {"r": request_id})
    log_staff_event(db, staff.id, "record", request_id)
    db.commit()
    return detail(request_id, staff, db)
