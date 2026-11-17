"""テストの共通準備。ローカルの MySQL の DB_NAME(既定 yokane_koin_test)を、テストごとにデモデータ入りで作り直す。"""
import os

import pytest

os.environ.setdefault("DB_NAME", "yokane_koin_test")
os.environ["INTERNAL_API_KEY"] = "test-key"
os.environ["STAFF_DEMO_PASSCODE"] = "demo-pass"

from fastapi.testclient import TestClient  # noqa: E402

from app.db import get_engine  # noqa: E402
from app.main import app  # noqa: E402
from scripts.apply_db import reset  # noqa: E402

KEY = {"X-Internal-Key": "test-key"}


@pytest.fixture(autouse=True)
def fresh_db():
    with get_engine().begin() as conn:
        reset(conn, seed=True)


@pytest.fixture
def client():
    return TestClient(app)


def staff(i: int) -> dict:
    return {**KEY, "X-Staff-Id": str(i)}


def user(i: int) -> dict:
    return {**KEY, "X-User-Id": str(i)}
