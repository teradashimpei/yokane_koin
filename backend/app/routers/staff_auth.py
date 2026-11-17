"""S-01 ログイン(デモ用)。登録済みの行員のメール + チーム共通のデモ用パスコード。

本番では Google(または福銀の職場アカウント)のIDトークンを BFF で確かめ、メールで staff_accounts を引く形に置き換える。
"""
import secrets

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import Connection, text

from app.config import get_settings
from app.db import get_db
from app.deps import Staff, current_staff, log_staff_event, require_internal_key
from app.errors import ApiError

router = APIRouter()


class LoginBody(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    passcode: str = Field(min_length=1, max_length=100)


def _shape(db: Connection, staff: Staff) -> dict:
    sp = None
    if staff.speaker_id is not None:
        sp = db.execute(text("SELECT id, name, photo_url FROM speakers WHERE id = :i"),
                        {"i": staff.speaker_id}).mappings().first()
    return {
        "id": staff.id, "display_name": staff.display_name, "role": staff.role,
        "speaker": dict(sp) if sp else None,
    }


@router.post("/v1/staff/login")
def login(body: LoginBody, _: None = Depends(require_internal_key), db: Connection = Depends(get_db)):
    expected = get_settings().staff_demo_passcode
    row = db.execute(text(
        "SELECT id, speaker_id, role, display_name FROM staff_accounts "
        "WHERE email = :e AND is_active = TRUE"
    ), {"e": body.email.strip().lower()}).mappings().first()
    # どちらが違っても同じ答え(登録の有無を漏らさない)
    if not expected or row is None or not secrets.compare_digest(body.passcode, expected):
        raise ApiError(401, "UNAUTHORIZED", "メールアドレスかパスコードが違います")
    db.execute(text("UPDATE staff_accounts SET last_login_at = CURRENT_TIMESTAMP WHERE id = :i"), {"i": row["id"]})
    log_staff_event(db, row["id"], "login")
    db.commit()
    return {"staff": _shape(db, Staff(row["id"], row["speaker_id"], row["role"], row["display_name"]))}


@router.get("/v1/staff/session")
def session(staff: Staff = Depends(current_staff), db: Connection = Depends(get_db)):
    return {"staff": _shape(db, staff)}
