"""日時の返し方。DBは日本時間で持つ(接続時に time_zone を +09:00 にしている)。"""
from datetime import datetime


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.replace(microsecond=0).isoformat() + "+09:00"
