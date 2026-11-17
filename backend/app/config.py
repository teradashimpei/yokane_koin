"""環境変数。ローカルでは .env を読み、すでにある環境変数は上書きしない。"""
import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    db_ssl_ca: str
    internal_api_key: str
    staff_demo_passcode: str


@lru_cache
def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        db_host=os.environ.get("DB_HOST", "localhost"),
        db_port=int(os.environ.get("DB_PORT", "3306")),
        db_name=os.environ.get("DB_NAME", "yokane"),
        db_user=os.environ.get("DB_USER", ""),
        db_password=os.environ.get("DB_PASSWORD", ""),
        db_ssl_ca=os.environ.get("DB_SSL_CA", ""),
        internal_api_key=os.environ.get("INTERNAL_API_KEY", ""),
        staff_demo_passcode=os.environ.get("STAFF_DEMO_PASSCODE", ""),
    )
