"""お客さん側に足すAPI(F1〜F3)。yokane-front の BFF から、内部キーと X-User-Id を付けて呼ぶ。

- GET  /v1/meeting-requests/{id}/reply   行員からの返事(状態と、日にちの提案)
- POST /v1/meeting-requests/{id}/choose  提案された日にちを1つ選ぶ → 予定に入る
見送りの理由はお客さんには返さない(S-13)。
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import Connection, text

from app.db import get_db
from app.deps import current_user_id
from app.errors import ApiError
from app.timefmt import iso

router = APIRouter()

MESSAGES = {
    "new": "返事を待っています",
    "replied": "話せる日にちが届きました。1つ選んでください",
    "scheduled": "会う日が決まりました",
    "done": "お話しした記録があります",
    "declined": "今回は難しそうです。ほかの人の話も聞いてみませんか",
}


def _own(db: Connection, uid: int, request_id: int):
    r = db.execute(text(
        "SELECT mr.id, mr.status, sp.name AS speaker_name FROM meeting_requests mr "
        "JOIN speakers sp ON sp.id = mr.speaker_id WHERE mr.id = :i AND mr.user_id = :u"
    ), {"i": request_id, "u": uid}).mappings().first()
    if r is None:
        raise ApiError(404, "NOT_FOUND", "見つかりません")
    return r


def _reply(db: Connection, r) -> dict:
    props = db.execute(text(
        "SELECT id, starts_at, ends_at, method, place, chosen_at FROM meeting_proposals "
        "WHERE request_id = :r ORDER BY starts_at, id"), {"r": r["id"]}).mappings().all()
    return {
        "id": r["id"], "speaker_name": r["speaker_name"], "status": r["status"], "message": MESSAGES[r["status"]],
        "proposals": [{"id": p["id"], "starts_at": iso(p["starts_at"]), "ends_at": iso(p["ends_at"]),
                       "method": p["method"], "place": p["place"] or "", "chosen": p["chosen_at"] is not None}
                      for p in props] if r["status"] != "declined" else [],
    }


@router.get("/v1/meeting-requests/{request_id}/reply")
def get_reply(request_id: int, uid: int = Depends(current_user_id), db: Connection = Depends(get_db)):
    return _reply(db, _own(db, uid, request_id))


class ChooseBody(BaseModel):
    proposal_id: int


@router.post("/v1/meeting-requests/{request_id}/choose")
def choose(request_id: int, body: ChooseBody, uid: int = Depends(current_user_id), db: Connection = Depends(get_db)):
    r = _own(db, uid, request_id)
    if r["status"] != "replied":
        raise ApiError(409, "INVALID_STATUS", "いまは日にちを選べません")
    n = db.execute(text("UPDATE meeting_proposals SET chosen_at = CURRENT_TIMESTAMP(3) WHERE id = :p AND request_id = :r"),
                   {"p": body.proposal_id, "r": request_id}).rowcount
    if n == 0:
        raise ApiError(404, "NOT_FOUND", "見つかりません")
    db.execute(text("UPDATE meeting_requests SET status = 'scheduled' WHERE id = :r"), {"r": request_id})
    db.commit()
    return _reply(db, _own(db, uid, request_id))
