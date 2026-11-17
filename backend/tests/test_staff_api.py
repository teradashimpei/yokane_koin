from tests.conftest import KEY, staff, user

OTA, NAKAMURA, ADMIN = 1, 2, 4


def test_health(client):
    assert client.get("/v1/health").json() == {"status": "ok", "db": "ok"}


def test_login(client):
    r = client.post("/v1/staff/login", headers=KEY, json={"email": "OTA@example.com ", "passcode": "demo-pass"})
    assert r.status_code == 200 and r.json()["staff"]["speaker"]["id"] == 1
    for body in ({"email": "ota@example.com", "passcode": "x"}, {"email": "nobody@example.com", "passcode": "demo-pass"}):
        assert client.post("/v1/staff/login", headers=KEY, json=body).status_code == 401
    assert client.post("/v1/staff/login", json={"email": "ota@example.com", "passcode": "demo-pass"}).status_code == 401


def test_requires_staff(client):
    assert client.get("/v1/staff/requests", headers=KEY).json()["error"]["code"] == "LOGIN_REQUIRED"
    assert client.get("/v1/staff/requests", headers=staff(ADMIN)).status_code == 403


def test_profile_roundtrip_and_tag_rules(client):
    me = client.get("/v1/staff/me", headers=staff(OTA)).json()
    assert me["profile"]["name"] == "太田 悠人" and len(me["value_tags"]) == 3
    ids = [t["id"] for t in me["tags"] if t["selected"]]
    body = {"name": "太田 悠人", "one_liner": "まず聞きます", "accepting": False,
            "hidden_fields": ["area"], "tag_ids": ids}
    r = client.put("/v1/staff/me/profile", headers=staff(OTA), json=body)
    assert r.status_code == 200
    p = r.json()["profile"]
    assert p["one_liner"] == "まず聞きます" and p["accepting"] is False and p["hidden_fields"] == ["area"]
    spec = [t["id"] for t in me["tags"] if t["kind"] == "specialty"][:1]
    r = client.put("/v1/staff/me/profile", headers=staff(OTA), json={**body, "tag_ids": spec})
    assert r.status_code == 422
    assert client.put("/v1/staff/me/profile", headers=staff(OTA), json={**body, "hidden_fields": ["age"]}).status_code == 422


def test_episodes_draft_and_limit(client):
    eps = client.get("/v1/staff/me", headers=staff(OTA)).json()["episodes"]
    assert len(eps) == 3
    assert client.post("/v1/staff/me/episodes", headers=staff(OTA), json={"title": "t", "body": "b"}).status_code == 409
    r = client.put(f"/v1/staff/me/episodes/{eps[0]['id']}", headers=staff(OTA), json={"title": "新しい見出し", "body": "本文"})
    assert r.json()["episodes"][0]["status"] == "draft"
    assert client.put(f"/v1/staff/me/episodes/{eps[0]['id']}", headers=staff(NAKAMURA),
                      json={"title": "x", "body": "y"}).status_code == 404


def test_answers_recalculate(client):
    qs = client.get("/v1/staff/questions", headers=staff(OTA)).json()["questions"]
    assert len(qs) == 12
    r = client.put("/v1/staff/me/answers", headers=staff(OTA), json={"answers": {str(q["id"]): 0 for q in qs}})
    assert r.json()["pattern"] == "000"
    assert client.put("/v1/staff/me/answers", headers=staff(OTA), json={"answers": {"1": 1}}).status_code == 422


def test_requests_scope(client):
    r = client.get("/v1/staff/requests", headers=staff(OTA)).json()
    assert len(r["requests"]) == 10 and r["counts"]["new"] == 3
    assert any(i["overdue"] for i in r["requests"])
    assert client.get("/v1/staff/requests/11", headers=staff(OTA)).status_code == 404
    assert client.get("/v1/staff/requests?status=x", headers=staff(OTA)).status_code == 422


def test_result_only_with_consent(client):
    shared = client.get("/v1/staff/requests/1", headers=staff(OTA)).json()["request"]
    hidden = client.get("/v1/staff/requests/2", headers=staff(OTA)).json()["request"]
    assert shared["result"]["texts"] and shared["result"]["axes"] == 3
    assert hidden["result"] is None


def test_reply_then_customer_chooses_then_record(client):
    body = {"proposals": [{"starts_at": "2026-12-01T19:00:00", "method": "online"},
                          {"starts_at": "2026-12-02T19:00:00", "method": "in_person", "place": "博多駅前"}]}
    r = client.post("/v1/staff/requests/1/reply", headers=staff(OTA), json=body).json()["request"]
    assert r["status"] == "replied" and len(r["proposals"]) == 2
    assert client.get("/v1/meeting-requests/1/reply", headers=user(2)).status_code == 404
    rep = client.get("/v1/meeting-requests/1/reply", headers=user(1)).json()
    assert rep["status"] == "replied"
    pid = rep["proposals"][1]["id"]
    assert client.post("/v1/meeting-requests/1/choose", headers=user(1), json={"proposal_id": pid}).json()["status"] == "scheduled"
    assert client.post("/v1/staff/requests/1/reply", headers=staff(OTA), json=body).status_code == 409
    rec = {"held": True, "topics": ["貯め方"], "next_promise": True, "memo": "自分用"}
    out = client.put("/v1/staff/requests/1/record", headers=staff(OTA), json=rec).json()["request"]
    assert out["status"] == "done" and out["record"]["memo"] == "自分用"
    assert client.put("/v1/staff/requests/1/record", headers=staff(OTA),
                      json={**rec, "topics": ["なにか"]}).status_code == 422
    sched = client.get("/v1/staff/schedule", headers=staff(OTA)).json()["items"]
    assert any(i["request_id"] == 1 and i["recorded"] for i in sched)


def test_decline(client):
    assert client.post("/v1/staff/requests/3/decline", headers=staff(OTA), json={"reason": "嫌"}).status_code == 422
    r = client.post("/v1/staff/requests/3/decline", headers=staff(OTA), json={"reason": "日程が合わない"}).json()
    assert r["request"]["status"] == "declined"
    rep = client.get("/v1/meeting-requests/3/reply", headers=user(3)).json()
    assert rep["status"] == "declined" and "日程" not in rep["message"] and rep["proposals"] == []


def test_insights_minimum(client):
    ota = client.get("/v1/staff/insights", headers=staff(OTA)).json()
    assert ota["enough"] and ota["total"] == 10 and ota["held"] == 3 and ota["axes"] is not None
    assert sum(l["count"] for l in ota["axes"][0]["levels"]) == ota["shared_count"]
    naka = client.get("/v1/staff/insights", headers=staff(NAKAMURA)).json()
    assert naka == {"enough": False, "total": 2, "min_people": 5}


def test_admin_export(client):
    assert client.get("/v1/admin/export", headers=staff(OTA)).status_code == 403
    r = client.get("/v1/admin/export", headers=staff(ADMIN))
    assert r.status_code == 200 and "request_id" in r.text
    assert "ゆう" not in r.text and "次は家計簿" not in r.text and "@example.com" not in r.text


def test_home_today(client):
    h = client.get("/v1/staff/home", headers=staff(OTA)).json()
    assert [w["requester_name"] for w in h["waiting"]] == ["あや", "まい", "ゆう"]  # 待っている時間が長い順
    assert h["waiting"][0]["overdue"] and h["waiting"][0]["waiting_hours"] >= 48
    assert len(h["today"]) == 1 and len(h["to_record"]) == 1 and not h["to_record"][0]["recorded"]
    assert set(h["month"]) == {"requests", "held", "next_promise"}
    assert client.get("/v1/staff/home", headers=staff(ADMIN)).status_code == 403
