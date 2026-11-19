from tests.conftest import KEY, staff, user

MORISHITA, TAKANO, ADMIN = 1, 2, 4   # 森下由美(話し手2)・高野直人(話し手1)・運営


def test_health(client):
    assert client.get("/v1/health").json() == {"status": "ok", "db": "ok"}


def test_login(client):
    r = client.post("/v1/staff/login", headers=KEY, json={"email": "Morishita@example.com ", "passcode": "demo-pass"})
    assert r.status_code == 200 and r.json()["staff"]["speaker"]["id"] == 2
    for body in ({"email": "morishita@example.com", "passcode": "x"}, {"email": "nobody@example.com", "passcode": "demo-pass"}):
        assert client.post("/v1/staff/login", headers=KEY, json=body).status_code == 401
    assert client.post("/v1/staff/login", json={"email": "morishita@example.com", "passcode": "demo-pass"}).status_code == 401


def test_requires_staff(client):
    assert client.get("/v1/staff/requests", headers=KEY).json()["error"]["code"] == "LOGIN_REQUIRED"
    assert client.get("/v1/staff/requests", headers=staff(ADMIN)).status_code == 403


def test_profile_roundtrip_and_tag_rules(client):
    me = client.get("/v1/staff/me", headers=staff(MORISHITA)).json()
    assert me["profile"]["name"] == "森下由美" and len(me["value_tags"]) == 3
    assert me["profile"]["photo_url"] == "/images/speakers/demo_ST0009.webp" and "age" not in me["profile"]
    ids = [t["id"] for t in me["tags"] if t["selected"]]
    body = {"name": "森下由美", "one_liner": "まず聞きます", "accepting": False,
            "hidden_fields": ["area"], "tag_ids": ids}
    r = client.put("/v1/staff/me/profile", headers=staff(MORISHITA), json=body)
    assert r.status_code == 200
    p = r.json()["profile"]
    assert p["one_liner"] == "まず聞きます" and p["accepting"] is False and p["hidden_fields"] == ["area"]
    spec = [t["id"] for t in me["tags"] if t["kind"] == "specialty"][:1]
    r = client.put("/v1/staff/me/profile", headers=staff(MORISHITA), json={**body, "tag_ids": spec})
    assert r.status_code == 422
    assert client.put("/v1/staff/me/profile", headers=staff(MORISHITA), json={**body, "hidden_fields": ["age"]}).status_code == 422


def _story_body(me: dict, **change) -> dict:
    s = me["story"]
    return {**{k: s[k] for k in ("headline", "good_text", "regret_text", "trigger_title", "trigger_body",
                                 "hesitation_title", "hesitation_body")}, "qas": s["qas"], "situation_label": "", **change}


def test_story_draft_rules_and_publish(client):
    me = client.get("/v1/staff/me", headers=staff(MORISHITA)).json()
    assert me["story"]["headline"].startswith("家は、買うとき") and len(me["story"]["qas"]) == 4
    assert me["story_draft"] is None
    money = client.put("/v1/staff/me/story", headers=staff(MORISHITA), json=_story_body(me, good_text="頭金は500万円でした"))
    assert money.status_code == 422 and {"field": "good_text", "reason": "money"} in money.json()["error"]["fields"]
    age = client.put("/v1/staff/me/story", headers=staff(MORISHITA), json=_story_body(me, regret_text="40歳で気づいた"))
    assert {"field": "regret_text", "reason": "age"} in age.json()["error"]["fields"]
    assert client.put("/v1/staff/me/story", headers=staff(MORISHITA),
                      json={**_story_body(me), "qas": me["story"]["qas"][:3]}).status_code == 422
    r = client.put("/v1/staff/me/story", headers=staff(MORISHITA),
                   json=_story_body(me, headline="買ったあとの計画が大事でした", situation_label="家を買って4年")).json()
    assert r["story_draft"]["headline"] == "買ったあとの計画が大事でした"
    assert r["story"]["headline"].startswith("家は、買うとき")          # 公開中の文は確認まで変わらない
    assert client.get("/v1/admin/story-drafts", headers=staff(MORISHITA)).status_code == 403
    drafts = client.get("/v1/admin/story-drafts", headers=staff(ADMIN)).json()["drafts"]
    assert [d["speaker_name"] for d in drafts] == ["森下由美"] and drafts[0]["current"]["headline"].startswith("家は")
    assert client.post("/v1/admin/story-drafts/2/publish", headers=staff(ADMIN)).json()["status"] == "published"
    after = client.get("/v1/staff/me", headers=staff(MORISHITA)).json()
    assert after["story"]["headline"] == "買ったあとの計画が大事でした" and after["story_draft"] is None
    assert after["profile"]["situation_label"] == "家を買って4年"
    assert client.post("/v1/admin/story-drafts/2/publish", headers=staff(ADMIN)).status_code == 404


def test_request_source_and_customer(client):
    own = client.get("/v1/staff/requests/1", headers=staff(MORISHITA))
    r = own.json()["request"]
    assert r["source"]["route"] == "own_story" and r["source"]["writer_label"] == "あなた"
    assert r["customer"] == {"faculty": "法学部", "age_band": "30代前半", "situations": ["結婚したばかり", "住宅を検討中"]}
    assert r["story"]["good_text"]
    grad = client.get("/v1/staff/requests/2", headers=staff(MORISHITA)).json()["request"]
    assert grad["source"]["route"] == "graduate_story" and grad["source"]["writer_label"] == "50代女性"
    assert grad["source"]["headline"].startswith("50代で一人で買うなら") and grad["preferences"] == []
    assert client.get("/v1/staff/requests/9", headers=staff(MORISHITA)).json()["request"]["source"] == {"route": "direct"}
    lst = client.get("/v1/staff/requests", headers=staff(MORISHITA))
    for body in (own.text, lst.text, client.get("/v1/staff/home", headers=staff(MORISHITA)).text):
        assert "income" not in body and "万円" not in body and "大野" not in body   # 年収と卒業生の名前は出さない


def test_answers_recalculate(client):
    qs = client.get("/v1/staff/questions", headers=staff(MORISHITA)).json()["questions"]
    assert len(qs) == 12
    r = client.put("/v1/staff/me/answers", headers=staff(MORISHITA), json={"answers": {str(q["id"]): 0 for q in qs}})
    assert r.json()["pattern"] == "000"
    assert client.put("/v1/staff/me/answers", headers=staff(MORISHITA), json={"answers": {"1": 1}}).status_code == 422


def test_requests_scope(client):
    r = client.get("/v1/staff/requests", headers=staff(MORISHITA)).json()
    assert len(r["requests"]) == 10 and r["counts"]["new"] == 3
    assert any(i["overdue"] for i in r["requests"])
    assert client.get("/v1/staff/requests/11", headers=staff(MORISHITA)).status_code == 404
    assert client.get("/v1/staff/requests?status=x", headers=staff(MORISHITA)).status_code == 422


def test_result_only_with_consent(client):
    shared = client.get("/v1/staff/requests/1", headers=staff(MORISHITA)).json()["request"]
    hidden = client.get("/v1/staff/requests/2", headers=staff(MORISHITA)).json()["request"]
    assert shared["result"]["texts"] and shared["result"]["axes"] == 3
    assert hidden["result"] is None


def test_reply_then_customer_chooses_then_record(client):
    body = {"proposals": [{"starts_at": "2026-12-01T19:00:00", "method": "online"},
                          {"starts_at": "2026-12-02T19:00:00", "method": "in_person", "place": "博多駅前"}]}
    r = client.post("/v1/staff/requests/1/reply", headers=staff(MORISHITA), json=body).json()["request"]
    assert r["status"] == "replied" and len(r["proposals"]) == 2
    assert client.get("/v1/meeting-requests/1/reply", headers=user(2)).status_code == 404
    rep = client.get("/v1/meeting-requests/1/reply", headers=user(1)).json()
    assert rep["status"] == "replied"
    pid = rep["proposals"][1]["id"]
    assert client.post("/v1/meeting-requests/1/choose", headers=user(1), json={"proposal_id": pid}).json()["status"] == "scheduled"
    assert client.post("/v1/staff/requests/1/reply", headers=staff(MORISHITA), json=body).status_code == 409
    rec = {"held": True, "topics": ["貯め方"], "next_promise": True, "memo": "自分用"}
    out = client.put("/v1/staff/requests/1/record", headers=staff(MORISHITA), json=rec).json()["request"]
    assert out["status"] == "done" and out["record"]["memo"] == "自分用"
    assert client.put("/v1/staff/requests/1/record", headers=staff(MORISHITA),
                      json={**rec, "topics": ["なにか"]}).status_code == 422
    sched = client.get("/v1/staff/schedule", headers=staff(MORISHITA)).json()["items"]
    assert any(i["request_id"] == 1 and i["recorded"] for i in sched)


def test_decline(client):
    assert client.post("/v1/staff/requests/3/decline", headers=staff(MORISHITA), json={"reason": "嫌"}).status_code == 422
    r = client.post("/v1/staff/requests/3/decline", headers=staff(MORISHITA), json={"reason": "日程が合わない"}).json()
    assert r["request"]["status"] == "declined"
    rep = client.get("/v1/meeting-requests/3/reply", headers=user(3)).json()
    assert rep["status"] == "declined" and "日程" not in rep["message"] and rep["proposals"] == []


def test_insights_minimum(client):
    mori = client.get("/v1/staff/insights", headers=staff(MORISHITA)).json()
    assert mori["enough"] and mori["total"] == 10 and mori["held"] == 3 and mori["axes"] is not None
    assert sum(l["count"] for l in mori["axes"][0]["levels"]) == mori["shared_count"]
    assert {"label": "住宅を検討中", "count": 6} in mori["situations"]
    assert {i["label"]: i["count"] for i in mori["routes"]} == {"あなたの経験談を読んで": 5, "卒業生の経験談から": 4,
                                                               "経験談を通らずに": 1}
    taka = client.get("/v1/staff/insights", headers=staff(TAKANO)).json()
    assert taka == {"enough": False, "total": 2, "min_people": 5}


def test_admin_export(client):
    assert client.get("/v1/admin/export", headers=staff(MORISHITA)).status_code == 403
    r = client.get("/v1/admin/export", headers=staff(ADMIN))
    assert r.status_code == 200 and "request_id" in r.text and "graduate_story" in r.text and "S05" in r.text
    assert "ゆう" not in r.text and "次は家計" not in r.text and "@example.com" not in r.text and "万円" not in r.text


def test_home_today(client):
    h = client.get("/v1/staff/home", headers=staff(MORISHITA)).json()
    assert [w["requester_name"] for w in h["waiting"]] == ["あや", "まい", "ゆう"]  # 待っている時間が長い順
    assert h["waiting"][0]["overdue"] and h["waiting"][0]["waiting_hours"] >= 48
    assert len(h["today"]) == 1 and len(h["to_record"]) == 1 and not h["to_record"][0]["recorded"]
    assert set(h["month"]) == {"requests", "held", "next_promise"}
    assert client.get("/v1/staff/home", headers=staff(ADMIN)).status_code == 403
