"""S-02〜S-08 プロフィール(P5・B1)、経験談(A5 に出る1人1本)と 12問(B2)。"""
import json
import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import Connection, text

from app.db import get_db
from app.deps import Staff, log_staff_event, require_speaker
from app.errors import ApiError
from app.services import scoring
from app.services.settings_repo import get_setting
from app.timefmt import iso

router = APIRouter()

HIDEABLE = ("area", "job_title", "intro_text", "personality_text", "private_tags")
TAG_RANGE = {"specialty": (2, 4), "private": (3, 5)}   # 03_タグ辞書の推奨数(S-03)
STORY_FIELDS = {  # 列 → (お客さんに見える見出し, 最大文字数)
    "headline": ("カードの一言", 100), "good_text": ("やって良かったこと", 600), "regret_text": ("後悔していること", 600),
    "trigger_title": ("きっかけ(見出し)", 50), "trigger_body": ("きっかけ(本文)", 600),
    "hesitation_title": ("迷ったこと(見出し)", 50), "hesitation_body": ("迷ったこと(本文)", 600),
}
QA_COUNT = 4
MONEY = re.compile(r"万円|年収|円")   # yokane-back の取り込みと同じ決まり(RK-16)。行員の文に金額を書かない


def _value_tags(db: Connection, speaker_id: int) -> list:
    rows = db.execute(text(
        "SELECT a.code, s.level FROM speaker_axis_scores s JOIN axes a ON a.id = s.axis_id "
        "WHERE s.speaker_id = :s ORDER BY a.display_order"
    ), {"s": speaker_id}).all()
    labels = get_setting(db, "value_tag_labels", {})
    return [(labels.get(code) or {}).get(str(level)) for code, level in rows]


def _story(db: Connection, speaker_id: int) -> dict | None:
    """公開中の経験談(お客さんの A5 に出ているもの)。"""
    st = db.execute(text(
        "SELECT id, headline, good_text, regret_text, trigger_title, trigger_body, hesitation_title, hesitation_body "
        "FROM stories WHERE speaker_id = :s"), {"s": speaker_id}).mappings().first()
    if st is None:
        return None
    qas = db.execute(text("SELECT question, answer FROM story_qas WHERE story_id = :i ORDER BY qa_no"),
                     {"i": st["id"]}).mappings().all()
    return {**dict(st), "qas": [dict(q) for q in qas]}


def _draft(db: Connection, speaker_id: int) -> dict | None:
    """運営の確認を待っている書き直し。"""
    d = db.execute(text(
        "SELECT headline, good_text, regret_text, trigger_title, trigger_body, hesitation_title, hesitation_body, "
        "qas, situation_label, submitted_at FROM story_drafts WHERE speaker_id = :s"), {"s": speaker_id}).mappings().first()
    if d is None:
        return None
    out = dict(d)
    out["qas"] = json.loads(out["qas"])
    out["submitted_at"] = iso(out["submitted_at"])
    return out


@router.get("/v1/staff/me")
def me(staff: Staff = Depends(require_speaker), db: Connection = Depends(get_db)):
    sp = db.execute(text(
        "SELECT id, speaker_key, name, kind, photo_url, one_liner, area, job_title, intro_text, personality_text, "
        "faculty, gender, situation_label, pattern, accepting, hidden_fields FROM speakers WHERE id = :i"
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
        "story": _story(db, staff.speaker_id),
        "story_draft": _draft(db, staff.speaker_id),
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


class QA(BaseModel):
    question: str = Field(min_length=1, max_length=200)
    answer: str = Field(min_length=1, max_length=600)


class StoryBody(BaseModel):
    headline: str = Field(min_length=1, max_length=100)
    good_text: str = Field(min_length=1, max_length=600)
    regret_text: str = Field(min_length=1, max_length=600)
    trigger_title: str = Field(min_length=1, max_length=50)
    trigger_body: str = Field(min_length=1, max_length=600)
    hesitation_title: str = Field(min_length=1, max_length=50)
    hesitation_body: str = Field(min_length=1, max_length=600)
    qas: list[QA] = Field(min_length=QA_COUNT, max_length=QA_COUNT)
    situation_label: str = Field(default="", max_length=30)


def story_problems(db: Connection, speaker_id: int, body: dict) -> list:
    """行員の経験談に書いてはいけないこと(金額・今の年齢)。yokane-back の取り込みのチェックと同じ。"""
    age = db.execute(text("SELECT age FROM speakers WHERE id = :s"), {"s": speaker_id}).scalar()
    age_re = re.compile(rf"(?<!\d){age}歳") if age else None
    texts = {k: body[k] for k in STORY_FIELDS}
    for i, qa in enumerate(body["qas"], 1):
        texts[f"qas.{i}.question"], texts[f"qas.{i}.answer"] = qa["question"], qa["answer"]
    out = []
    for field, value in texts.items():
        if MONEY.search(value or ""):
            out.append({"field": field, "reason": "money"})
        if age_re and age_re.search(value or ""):
            out.append({"field": field, "reason": "age"})
    return out


@router.put("/v1/staff/me/story")
def save_story(body: StoryBody, staff: Staff = Depends(require_speaker), db: Connection = Depends(get_db)):
    """経験談を書き直す。下書きに入り、運営が確かめて「公開」するとお客さんの画面(A4・A5)が変わる(S-04)。"""
    data = body.model_dump()
    data = {k: (v.strip() if isinstance(v, str) else v) for k, v in data.items()}
    data["qas"] = [{"question": q["question"].strip(), "answer": q["answer"].strip()} for q in data["qas"]]
    problems = story_problems(db, staff.speaker_id, data)
    if problems:
        raise ApiError(422, "VALIDATION_ERROR", "金額や今の年齢は書けません(本人が特定されやすいため)", problems)
    db.execute(text(
        "INSERT INTO story_drafts (speaker_id, headline, good_text, regret_text, trigger_title, trigger_body, "
        "hesitation_title, hesitation_body, qas, situation_label) VALUES (:s, :headline, :good_text, :regret_text, "
        ":trigger_title, :trigger_body, :hesitation_title, :hesitation_body, :qas, :situation_label) "
        "ON DUPLICATE KEY UPDATE headline = VALUES(headline), good_text = VALUES(good_text), "
        "regret_text = VALUES(regret_text), trigger_title = VALUES(trigger_title), trigger_body = VALUES(trigger_body), "
        "hesitation_title = VALUES(hesitation_title), hesitation_body = VALUES(hesitation_body), qas = VALUES(qas), "
        "situation_label = VALUES(situation_label)"
    ), {**data, "s": staff.speaker_id, "qas": json.dumps(data["qas"], ensure_ascii=False),
        "situation_label": data["situation_label"] or None})
    log_staff_event(db, staff.id, "story_save")
    db.commit()
    return me(staff, db)


@router.delete("/v1/staff/me/story")
def discard_story(staff: Staff = Depends(require_speaker), db: Connection = Depends(get_db)):
    """確認待ちの書き直しを取り消す(公開中の経験談はそのまま)。"""
    db.execute(text("DELETE FROM story_drafts WHERE speaker_id = :s"), {"s": staff.speaker_id})
    db.commit()
    return me(staff, db)


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
