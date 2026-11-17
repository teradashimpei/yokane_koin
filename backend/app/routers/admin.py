"""S-09・S-18 運営だけのAPI。CSVには名前・連絡先・メモを入れない(SN-02・SN-04)。"""
import csv
import io
import json

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import Connection, text

from app.db import get_db
from app.deps import Staff, require_admin
from app.errors import ApiError
from app.timefmt import iso

router = APIRouter()


@router.get("/v1/admin/export")
def export(staff: Staff = Depends(require_admin), db: Connection = Depends(get_db)):
    rows = db.execute(text(
        "SELECT mr.id, sp.speaker_key, mr.created_at, mr.status, mr.replied_at, mr.decline_reason, mr.meeting_method, "
        "mr.ask_topics, mr.share_result, "
        "(SELECT COUNT(*) FROM meeting_proposals p WHERE p.request_id = mr.id) AS proposals, "
        "(SELECT MIN(p.starts_at) FROM meeting_proposals p WHERE p.request_id = mr.id AND p.chosen_at IS NOT NULL) AS meet_at, "
        "rec.held, rec.next_promise, rec.topics FROM meeting_requests mr JOIN speakers sp ON sp.id = mr.speaker_id "
        "LEFT JOIN meeting_records rec ON rec.request_id = mr.id ORDER BY mr.id"
    )).mappings().all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["request_id", "speaker_key", "created_at", "status", "replied_at", "reply_hours", "decline_reason",
                "meeting_method", "ask_topics", "share_result", "proposals", "meet_at", "held", "next_promise",
                "talked_topics"])
    for r in rows:
        hours = round((r["replied_at"] - r["created_at"]).total_seconds() / 3600, 1) if r["replied_at"] else ""
        w.writerow([r["id"], r["speaker_key"], iso(r["created_at"]), r["status"], iso(r["replied_at"]) or "", hours,
                    r["decline_reason"] or "", r["meeting_method"],
                    " / ".join(json.loads(r["ask_topics"]) if r["ask_topics"] else []), int(bool(r["share_result"])),
                    r["proposals"], iso(r["meet_at"]) or "", "" if r["held"] is None else int(bool(r["held"])),
                    "" if r["next_promise"] is None else int(bool(r["next_promise"])),
                    " / ".join(json.loads(r["topics"]) if r["topics"] else [])])
    return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="yokane_staff_export.csv"'})


@router.get("/v1/admin/episodes")
def drafts(staff: Staff = Depends(require_admin), db: Connection = Depends(get_db)):
    rows = db.execute(text(
        "SELECT e.id, sp.name AS speaker_name, e.title, e.body, e.status, a.code AS axis, e.direction "
        "FROM speaker_episodes e JOIN speakers sp ON sp.id = e.speaker_id LEFT JOIN axes a ON a.id = e.axis_id "
        "WHERE e.status = 'draft' ORDER BY e.updated_at"
    )).mappings().all()
    return {"episodes": [dict(r) for r in rows]}


@router.post("/v1/admin/episodes/{episode_id}/publish")
def publish(episode_id: int, body: dict, staff: Staff = Depends(require_admin), db: Connection = Depends(get_db)):
    """運営が軸と向きを付けて公開する(S-04)。body: {"axis": "L", "direction": 1}"""
    axis_id = db.execute(text("SELECT id FROM axes WHERE code = :c"), {"c": body.get("axis")}).scalar()
    if axis_id is None or body.get("direction") not in (-1, 1):
        raise ApiError(422, "VALIDATION_ERROR", "入力に誤りがあります", [{"field": "axis", "reason": "invalid"}])
    n = db.execute(text(
        "UPDATE speaker_episodes SET axis_id = :a, direction = :d, status = 'published', reviewed_by = :s, "
        "reviewed_at = CURRENT_TIMESTAMP WHERE id = :i"
    ), {"a": axis_id, "d": body["direction"], "s": staff.id, "i": episode_id}).rowcount
    if n == 0:
        raise ApiError(404, "NOT_FOUND", "見つかりません")
    db.commit()
    return {"id": episode_id, "status": "published"}
