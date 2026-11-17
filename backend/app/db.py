"""MySQL 接続(12.4)。DB_SSL_CA が空ならTLSなし(ローカルの docker 用)。"""
from functools import lru_cache
from typing import Iterator

from sqlalchemy import Connection, Engine, URL, create_engine

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    s = get_settings()
    url = URL.create(
        "mysql+pymysql",
        username=s.db_user,
        password=s.db_password,
        host=s.db_host,
        port=s.db_port,
        database=s.db_name,
        query={"charset": "utf8mb4"},
    )
    connect_args: dict = {"init_command": "SET time_zone = '+09:00'"}
    if s.db_ssl_ca:
        connect_args["ssl"] = {"ca": s.db_ssl_ca}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


def get_db() -> Iterator[Connection]:
    with get_engine().connect() as conn:
        yield conn
