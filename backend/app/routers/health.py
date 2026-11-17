from fastapi import APIRouter, Depends
from sqlalchemy import Connection, text

from app.db import get_db

router = APIRouter()


@router.get("/v1/health")
def health(db: Connection = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "ok"}
