"""app_settings の値を読む(6.4)。値はJSONで入っている。"""
import json

from sqlalchemy import Connection, text


_REQUIRED = object()


def get_setting(db: Connection, key: str, default=_REQUIRED):
    """default を渡すと、設定の行がないときにその値を返す(渡さなければ LookupError)。"""
    raw = db.execute(text("SELECT value FROM app_settings WHERE setting_key = :k"), {"k": key}).scalar()
    if raw is None:
        if default is not _REQUIRED:
            return default
        raise LookupError(f"app_settings に {key} がありません(取り込みを流したか確認する)")
    return json.loads(raw)
