"""S-09・S-18 運営だけのAPI。CSVには名前・連絡先・メモ・年収を入れない(SN-02・SN-04)。"""
import csv
import io
import json

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import Connection, text

from app.db import get_db
from app.deps import Staff, require_admin
from app.errors import ApiError
from app.routers.staff_profile import STORY_FIELDS, story_problems
from app.timefmt import iso

router = APIRouter()


@router.get("/v1/admin/export")
def export(staff: Staff = Depends(require_admin), db: Connection = Depends(get_db)):
    rows = db.execute(text(
        "SELECT mr.id, sp.speaker_key, mr.created_at, mr.status, mr.replied_at, mr.decline_reason, mr.meeting_method, "
        "mr.ask_topics, mr.share_result, mr.story_id, wr.kind AS writer_kind, cp.age_band, "
        "(SELECT GROUP_CONCAT(cs.situation_code ORDER BY cs.situation_code SEPARATOR ' ') FROM customer_situations cs "
        "WHERE cs.user_id = mr.user_id) AS situations, "
        "(SELECT COUNT(*) FROM meeting_proposals p WHERE p.request_id = mr.id) AS proposals, "
        "(SELECT MIN(p.starts_at) FROM meeting_proposals p WHERE p.request_id = mr.id AND p.chosen_at IS NOT NULL) AS meet_at, "
        "rec.held, rec.next_promise, rec.topics FROM meeting_requests mr JOIN speakers sp ON sp.id = mr.speaker_id "
        "LEFT JOIN stories st ON st.id = mr.story_id LEFT JOIN speakers wr ON wr.id = st.speaker_id "
        "LEFT JOIN customer_profiles cp ON cp.user_id = mr.user_id "
        "LEFT JOIN meeting_records rec ON rec.request_id = mr.id ORDER BY mr.id"
    )).mappings().all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["request_id", "speaker_key", "route", "story_id", "situations", "age_band", "created_at", "status",
                "replied_at", "reply_hours", "decline_reason", "meeting_method", "ask_topics", "share_result", "proposals",
                "meet_at", "held", "next_promise", "talked_topics"])
    for r in rows:
        hours = round((r["replied_at"] - r["created_at"]).total_seconds() / 3600, 1) if r["replied_at"] else ""
        route = "direct" if r["story_id"] is None else ("graduate_story" if r["writer_kind"] == "graduate" else "staff_story")
        w.writerow([r["id"], r["speaker_key"], route, r["story_id"] or "", r["situations"] or "", r["age_band"] or "",
                    iso(r["created_at"]), r["status"], iso(r["replied_at"]) or "", hours,
                    r["decline_reason"] or "", r["meeting_method"],
                    " / ".join(json.loads(r["ask_topics"]) if r["ask_topics"] else []), int(bool(r["share_result"])),
                    r["proposals"], iso(r["meet_at"]) or "", "" if r["held"] is None else int(bool(r["held"])),
                    "" if r["next_promise"] is None else int(bool(r["next_promise"])),
                    " / ".join(json.loads(r["topics"]) if r["topics"] else [])])
    return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="yokane_staff_export.csv"'})


@router.get("/v1/admin/story-drafts")
def story_drafts(staff: Staff = Depends(require_admin), db: Connection = Depends(get_db)):
    """確認待ちの経験談の書き直し。いま公開中の文と並べて見られるよう、両方返す。"""
    rows = db.execute(text(
        "SELECT d.*, sp.name AS speaker_name, sp.situation_label AS current_label FROM story_drafts d "
        "JOIN speakers sp ON sp.id = d.speaker_id ORDER BY d.submitted_at"
    )).mappings().all()
    out = []
    for r in rows:
        cur = db.execute(text("SELECT * FROM stories WHERE speaker_id = :s"), {"s": r["speaker_id"]}).mappings().first()
        out.append({
            "speaker_id": r["speaker_id"], "speaker_name": r["speaker_name"], "submitted_at": iso(r["submitted_at"]),
            "situation_label": r["situation_label"], "current_situation_label": r["current_label"],
            "draft": {k: r[k] for k in STORY_FIELDS}, "qas": json.loads(r["qas"]),
            "current": {k: cur[k] for k in STORY_FIELDS} if cur else None,
        })
    return {"drafts": out}


@router.post("/v1/admin/story-drafts/{speaker_id}/publish")
def publish_story(speaker_id: int, staff: Staff = Depends(require_admin), db: Connection = Depends(get_db)):
    """下書きを stories・story_qas に写して公開する。お客さんの A4・A5 にすぐ出る。"""
    d = db.execute(text("SELECT * FROM story_drafts WHERE speaker_id = :s"), {"s": speaker_id}).mappings().first()
    if d is None:
        raise ApiError(404, "NOT_FOUND", "見つかりません")
    body = {**{k: d[k] for k in STORY_FIELDS}, "qas": json.loads(d["qas"])}
    if story_problems(db, speaker_id, body):   # 書いたあとで決まりが変わっても、出す前にもう一度見る
        raise ApiError(422, "VALIDATION_ERROR", "金額や今の年齢が含まれています")
    params = {k: d[k] for k in STORY_FIELDS}
    story_id = db.execute(text("SELECT id FROM stories WHERE speaker_id = :s"), {"s": speaker_id}).scalar()
    if story_id is None:
        story_id = db.execute(text(
            "INSERT INTO stories (speaker_id, " + ", ".join(STORY_FIELDS) + ") VALUES (:s, " +
            ", ".join(":" + k for k in STORY_FIELDS) + ")"), {**params, "s": speaker_id}).lastrowid
    else:
        db.execute(text("UPDATE stories SET " + ", ".join(f"{k} = :{k}" for k in STORY_FIELDS) + " WHERE id = :i"),
                   {**params, "i": story_id})
    db.execute(text("DELETE FROM story_qas WHERE story_id = :i"), {"i": story_id})
    for n, qa in enumerate(body["qas"], 1):
        db.execute(text("INSERT INTO story_qas (story_id, qa_no, question, answer) VALUES (:i, :n, :q, :a)"),
                   {"i": story_id, "n": n, "q": qa["question"], "a": qa["answer"]})
    if d["situation_label"]:
        db.execute(text("UPDATE speakers SET situation_label = :l WHERE id = :s"),
                   {"l": d["situation_label"], "s": speaker_id})
    db.execute(text("DELETE FROM story_drafts WHERE speaker_id = :s"), {"s": speaker_id})
    db.commit()
    return {"speaker_id": speaker_id, "story_id": story_id, "status": "published"}
