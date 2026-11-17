"""S-02〜S-08 プロフィール(P5・B1)と 12問(B2)。"""
import json
import secrets

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import Connection, text

from app.db import get_db
from app.deps import Staff, log_staff_event, require_speaker
from app.errors import ApiError
from app.services import scoring
from app.services.settings_repo import get_setting

router = APIRouter()

HIDEABLE = ("area", "job_title", "intro_text", "personality_text", "private_tags")
TAG_RANGE = {"specialty": (2, 4), "private": (3, 5)}   # 03_タグ辞書の推奨数(S-03)
MAX_EPISODES = 3


def _episodes(db: Connection, speaker_id: int) -> list:
    rows = db.execute(text(
        "SELECT e.id, e.title, e.body, e.status, a.code AS axis FROM speaker_episodes e "
        "LEFT JOIN axes a ON a.id = e.axis_id "
        "WHERE e.speaker_id = :s AND e.source_type = 'self' ORDER BY e.id"
    ), {"s": speaker_id}).mappings().all()
    return [dict(r) for r in rows]


def _value_tags(db: Connection, speaker_id: int) -> list:
    rows = db.execute(text(
        "SELECT a.code, s.level FROM speaker_axis_scores s JOIN axes a ON a.id = s.axis_id "
        "WHERE s.speaker_id = :s ORDER BY a.display_order"
    ), {"s": speaker_id}).all()
    labels = get_setting(db, "value_tag_labels", {})
    return [(labels.get(code) or {}).get(str(level)) for code, level in rows]


@router.get("/v1/staff/me")
def me(staff: Staff = Depends(require_speaker), db: Connection = Depends(get_db)):
    sp = db.execute(text(
        "SELECT id, speaker_key, name, photo_url, one_liner, area, job_title, intro_text, personality_text, "
        "pattern, accepting, hidden_fields FROM speakers WHERE id = :i"
    ), {"i": staff.speaker_id}).mappings().first()
    tags = db.execute(text(
        "SELECT t.id, t.kind, t.name, (st.tag_id IS NOT NULL) AS selected FROM tags t "
        "LEFT JOIN speaker_tags st ON st.tag_id = t.id AND st.speaker_id = :s ORDER BY t.kind, t.display_order, t.id"
    ), {"s": staff.speaker_id}).mappings().all()
    answered = db.execute(text("SELECT COUNT(*) FROM speaker_answers WHERE speaker_id = :s"),
                          {"s": staff.speaker_id}).scalar()
    profile = dict(sp)
    profile["accepting"] = bool(profile["accepting"])
    profile["hidden_fields"] = json.loads(profile["hidden_fields"]) if profile["hidden_fields"] else []
    return {
        "profile": profile,
        "tags": [{**dict(t), "selected": bool(t["selected"])} for t in tags],
        "tag_range": TAG_RANGE,
        "episodes": _episodes(db, staff.speaker_id),
        "value_tags": _value_tags(db, staff.speaker_id),
        "answered_count": answered,
    }


class ProfileBody(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    one_liner: str = Field(default="", max_length=100)
    area: str = Field(default="", max_length=50)
    job_title: str = Field(default="", max_length=50)
    intro_text: str = Field(default="", max_length=1000)
    personality_text: str = Field(default="", max_length=1000)
    accepting: bool = True
    hidden_fields: list[str] = []
    tag_ids: list[int] = []


@router.put("/v1/staff/me/profile")
def save_profile(body: ProfileBody, staff: Staff = Depends(require_speaker), db: Connection = Depends(get_db)):
    bad = [f for f in body.hidden_fields if f not in HIDEABLE]
    if bad:
        raise ApiError(422, "VALIDATION_ERROR", "入力に誤りがあります",
                       [{"field": "hidden_fields", "reason": "invalid"}])
    kinds = dict(db.execute(text("SELECT id, kind FROM tags")).all())
    picked = {"specialty": 0, "private": 0}
    for tid in set(body.tag_ids):
        if tid not in kinds:
            raise ApiError(422, "VALIDATION_ERROR", "入力に誤りがあります", [{"field": "tag_ids", "reason": "invalid"}])
        picked[kinds[tid]] += 1
    fields = []
    for kind, (lo, hi) in TAG_RANGE.items():
        if kinds and not (lo <= picked[kind] <= hi):
            fields.append({"field": f"tags.{kind}", "reason": "count", "min": lo, "max": hi, "actual": picked[kind]})
    if fields:
        raise ApiError(422, "VALIDATION_ERROR", "タグの数を確かめてください", fields)
    db.execute(text(
        "UPDATE speakers SET name = :name, one_liner = :one, area = :area, job_title = :job, intro_text = :intro, "
        "personality_text = :pers, accepting = :acc, hidden_fields = :hid WHERE id = :i"
    ), {"name": body.name.strip(), "one": body.one_liner.strip() or None, "area": body.area.strip() or None,
        "job": body.job_title.strip() or None, "intro": body.intro_text.strip() or None,
        "pers": body.personality_text.strip() or None, "acc": body.accepting,
        "hid": json.dumps(sorted(set(body.hidden_fields))), "i": staff.speaker_id})
    db.execute(text("DELETE FROM speaker_tags WHERE speaker_id = :s"), {"s": staff.speaker_id})
    for tid in sorted(set(body.tag_ids)):
        db.execute(text("INSERT INTO speaker_tags (speaker_id, tag_id) VALUES (:s, :t)"),
                   {"s": staff.speaker_id, "t": tid})
    log_staff_event(db, staff.id, "profile_save")
    db.commit()
    return me(staff, db)


class EpisodeBody(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    body: str = Field(min_length=1, max_length=400)


@router.post("/v1/staff/me/episodes", status_code=201)
def add_episode(body: EpisodeBody, staff: Staff = Depends(require_speaker), db: Connection = Depends(get_db)):
    if len(_episodes(db, staff.speaker_id)) >= MAX_EPISODES:
        raise ApiError(409, "TOO_MANY_EPISODES", f"体験談は{MAX_EPISODES}本までです")
    key = "N" + secrets.token_hex(4)[:9]
    db.execute(text(
        "INSERT INTO speaker_episodes (episode_key, speaker_id, source_type, title, body, status) "
        "VALUES (:k, :s, 'self', :t, :b, 'draft')"
    ), {"k": key, "s": staff.speaker_id, "t": body.title.strip(), "b": body.body.strip()})
    log_staff_event(db, staff.id, "episode_save")
    db.commit()
    return {"episodes": _episodes(db, staff.speaker_id)}


@router.put("/v1/staff/me/episodes/{episode_id}")
def edit_episode(episode_id: int, body: EpisodeBody, staff: Staff = Depends(require_speaker),
                 db: Connection = Depends(get_db)):
    """書き換えると下書きに戻り、運営の確認後に公開される(S-04)。"""
    n = db.execute(text(
        "UPDATE speaker_episodes SET title = :t, body = :b, status = 'draft', reviewed_by = NULL, reviewed_at = NULL "
        "WHERE id = :i AND speaker_id = :s AND source_type = 'self'"
    ), {"t": body.title.strip(), "b": body.body.strip(), "i": episode_id, "s": staff.speaker_id}).rowcount
    if n == 0:
        raise ApiError(404, "NOT_FOUND", "見つかりません")
    log_staff_event(db, staff.id, "episode_save")
    db.commit()
    return {"episodes": _episodes(db, staff.speaker_id)}


@router.get("/v1/staff/questions")
def questions(staff: Staff = Depends(require_speaker), db: Connection = Depends(get_db)):
    rows = db.execute(text(
        "SELECT q.id, q.question_no, q.episode_text, q.summary, q.source_label, sa.answer FROM questions q "
        "LEFT JOIN speaker_answers sa ON sa.question_id = q.id AND sa.speaker_id = :s ORDER BY q.question_no"
    ), {"s": staff.speaker_id}).mappings().all()
    return {"questions": [dict(r) for r in rows]}


class AnswersBody(BaseModel):
    answers: dict[int, int]     # question_id → 1 わかる / -1 ちがうかも / 0 パス


@router.put("/v1/staff/me/answers")
def save_answers(body: AnswersBody, staff: Staff = Depends(require_speaker), db: Connection = Depends(get_db)):
    qs = [scoring.Question(i, code, d) for i, code, d in db.execute(text(
        "SELECT q.id, a.code, q.direction FROM questions q JOIN axes a ON a.id = q.axis_id"))]
    ids = {q.id for q in qs}
    if set(body.answers) != ids or any(v not in (-1, 0, 1) for v in body.answers.values()):
        raise ApiError(422, "VALIDATION_ERROR", "12問すべてに答えてください",
                       [{"field": "answers", "reason": "invalid", "expected": len(ids)}])
    axes = db.execute(text("SELECT id, code FROM axes ORDER BY display_order")).all()
    th = get_setting(db, "level_thresholds")
    ev = scoring.evaluate(body.answers, qs, [c for _, c in axes], scoring.Thresholds(th["minus_max"], th["plus_min"]))
    db.execute(text("DELETE FROM speaker_answers WHERE speaker_id = :s"), {"s": staff.speaker_id})
    for qid, a in body.answers.items():
        db.execute(text("INSERT INTO speaker_answers (speaker_id, question_id, answer) VALUES (:s, :q, :a)"),
                   {"s": staff.speaker_id, "q": qid, "a": a})
    db.execute(text("DELETE FROM speaker_axis_scores WHERE speaker_id = :s"), {"s": staff.speaker_id})
    for aid, code in axes:
        db.execute(text("INSERT INTO speaker_axis_scores (speaker_id, axis_id, score, level) VALUES (:s, :a, :sc, :lv)"),
                   {"s": staff.speaker_id, "a": aid, "sc": ev.scores[code], "lv": ev.levels[code]})
    db.execute(text("UPDATE speakers SET pattern = :p WHERE id = :s"), {"p": ev.pattern, "s": staff.speaker_id})
    log_staff_event(db, staff.id, "answers_save")
    db.commit()
    return {"pattern": ev.pattern, "value_tags": _value_tags(db, staff.speaker_id)}
