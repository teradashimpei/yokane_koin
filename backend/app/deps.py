"""共通の前処理: 内部キーの確認、行員の特定、お客さん(利用者)の特定。

画面(Next.js)は BFF として動き、ブラウザには内部キーも行員IDも見せない。
BFF が署名つき Cookie から行員IDを取り出し、X-Staff-Id として付ける。
"""
import secrets
from dataclasses import dataclass

from fastapi import Depends, Header
from sqlalchemy import Connection, text

from app.config import get_settings
from app.db import get_db
from app.errors import ApiError


def require_internal_key(x_internal_key: str = Header(default="")) -> None:
    expected = get_settings().internal_api_key
    if not expected or not secrets.compare_digest(x_internal_key, expected):
        raise ApiError(401, "UNAUTHORIZED", "認証に失敗しました")


@dataclass(frozen=True)
class Staff:
    id: int
    speaker_id: int | None
    role: str
    display_name: str


def load_staff(db: Connection, staff_id: int) -> Staff | None:
    row = db.execute(text(
        "SELECT id, speaker_id, role, display_name FROM staff_accounts WHERE id = :i AND is_active = TRUE"
    ), {"i": staff_id}).mappings().first()
    return Staff(row["id"], row["speaker_id"], row["role"], row["display_name"]) if row else None


def current_staff(
    _: None = Depends(require_internal_key),
    x_staff_id: str = Header(default=""),
    db: Connection = Depends(get_db),
) -> Staff:
    staff = load_staff(db, int(x_staff_id)) if x_staff_id.isdigit() else None
    if staff is None:
        raise ApiError(401, "LOGIN_REQUIRED", "ログインが必要です")
    return staff


def require_speaker(staff: Staff = Depends(current_staff)) -> Staff:
    """話し手として使う画面(P2〜P6・B2)。運営だけのアカウントは話し手を持たない。"""
    if staff.speaker_id is None:
        raise ApiError(403, "FORBIDDEN", "話し手として登録されていません")
    return staff


def require_admin(staff: Staff = Depends(current_staff)) -> Staff:
    if staff.role != "admin":
        raise ApiError(403, "FORBIDDEN", "運営だけが使えます")
    return staff


def current_user_id(
    _: None = Depends(require_internal_key),
    x_user_id: str = Header(default=""),
    db: Connection = Depends(get_db),
) -> int:
    """お客さん側(yokane-front の BFF)から呼ぶAPI。ログイン中の利用者だけ。"""
    uid = int(x_user_id) if x_user_id.isdigit() else None
    if uid is None or db.execute(text("SELECT 1 FROM users WHERE id = :u"), {"u": uid}).scalar() is None:
        raise ApiError(401, "LOGIN_REQUIRED", "ログインが必要です")
    return uid


def log_staff_event(db: Connection, staff_id: int, action: str, request_id: int | None = None) -> None:
    db.execute(text(
        "INSERT INTO staff_events (staff_id, request_id, action) VALUES (:s, :r, :a)"
    ), {"s": staff_id, "r": request_id, "a": action})
