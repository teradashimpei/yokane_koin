"""よかね 行員用の画面(Streamlit 版・デモデータだけで動く)。

Next.js 版(frontend/)と同じ画面・文言を、DB につながずに見せるためのもの。
データは data/snapshot.json(backend/scripts/make_streamlit_snapshot.py で書き出す)。
操作(返事・見送り・記録・プロフィール・経験談・12問・公開)はこのブラウザのタブを開いている間だけ残る。

    cd streamlit && .venv/bin/streamlit run app.py      # ローカル
    Streamlit Community Cloud では Main file を streamlit/app.py にする
"""
import base64
import copy
import csv
import html
import io
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st

APP = Path(__file__).resolve().parent
ROOT = APP.parent
JST = timezone(timedelta(hours=9))
SNAP = json.loads((APP / "data" / "snapshot.json").read_text(encoding="utf-8"))

STATUS_LABEL = {"new": "返事が必要", "replied": "お客さまの返事待ち", "scheduled": "予定あり", "done": "終わった", "declined": "見送った"}
METHOD_LABEL = {"online": "オンライン", "in_person": "会って話す"}
TIMES = ["10:00", "12:00", "15:00", "18:00", "19:00", "19:30", "20:00"]
MONEY = re.compile(r"万円|年収|円")   # 行員の文に金額を書かない(RK-16。yokane-back の取り込みと同じ)
STORY = [("headline", "カードの一言（一覧に出る）", 100, False), ("good_text", "やって良かったこと", 600, True),
         ("regret_text", "後悔していること", 600, True), ("trigger_title", "きっかけ（見出し）", 50, False),
         ("trigger_body", "きっかけ（本文）", 600, True), ("hesitation_title", "迷ったこと（見出し）", 50, False),
         ("hesitation_body", "迷ったこと（本文）", 600, True)]
FIELDS = [("area", "担当エリア", False), ("job_title", "業務担当", False), ("intro_text", "自己紹介", True),
          ("personality_text", "人柄・休日", True)]
AXIS_NAME = {"L": "暮らし方", "C": "決め方", "M": "お金"}

st.set_page_config(page_title="よかね 行員用（デモ）", page_icon="🏦", layout="wide")
st.markdown("""<style>
:root{--primary:#254aa5;--sky:#36aee8;--pale:#e0f2fb;--ink:#1e2430;--sub:#4a5568;--muted:#8a94a6;--line:#d5dae0;--bg:#f3f5f9;--ok:#2e8b57;--okbg:#eaf4ee;--warn:#b7860b;--warnbg:#fef7e1;--err:#d64545;--errbg:#fbecec}
.block-container{padding-top:2rem;max-width:1400px}
h3{font-size:1.2rem!important;padding:.2rem 0 .4rem!important}
.yk-chip{display:inline-block;border-radius:8px;padding:2px 10px;font-size:12px;background:#eef6fb;border:1px solid #cfe6f3;color:#1b3c8f;margin:0 4px 4px 0}
.yk-chip.on{background:var(--pale);border-color:var(--sky);color:var(--primary);font-weight:700}
.yk-chip.plain{background:var(--bg);border-color:var(--bg);color:var(--ink)}
.yk-badge{display:inline-block;border-radius:6px;padding:2px 10px;font-size:12px;font-weight:700;white-space:nowrap}
.b-new{background:var(--errbg);color:var(--err)}.b-replied{background:var(--warnbg);color:var(--warn)}.b-scheduled{background:var(--okbg);color:var(--ok)}
.b-done{background:var(--bg);color:var(--sub)}.b-declined{background:var(--bg);color:var(--muted)}.b-over{background:var(--errbg);color:var(--err)}
.yk-src{font-size:13px;line-height:1.5;color:var(--muted)}.yk-src b{margin-right:4px}.src-own_story b{color:var(--primary)}.src-graduate_story b{color:#0b7a75}.yk-src span{color:#374151}
.yk-muted{color:var(--muted);font-size:13px}.yk-label{color:var(--sub);font-weight:700;font-size:13px;margin:10px 0 2px}
.yk-note{background:var(--warnbg);color:#6b5310;padding:10px 14px;border-radius:8px;font-size:13px;margin:6px 0}
.yk-demo{border:1px dashed var(--muted);color:var(--sub);padding:8px 12px;border-radius:8px;font-size:12px;margin:6px 0}
.yk-ok{background:var(--okbg);color:var(--ok);padding:10px 14px;border-radius:8px;margin-bottom:8px}
.yk-story{border:1px solid #e5e7eb;border-radius:10px;padding:14px 16px;background:#fafbfc}.yk-story h4{margin:0 0 4px;font-size:13px;color:#6b7280;padding:0}.yk-story p{margin:0 0 10px;white-space:pre-wrap}
.yk-today{background:var(--pale);border-radius:8px;padding:14px 16px;margin-bottom:6px}.yk-time{color:var(--primary);font-size:20px;font-weight:700}
.yk-stat .k{color:var(--sub);font-size:13px}.yk-stat .v{font-size:26px;font-weight:700}.yk-stat .v.blue{color:var(--primary)}
.yk-hbar{display:flex;align-items:center;gap:12px;margin:8px 0}.yk-hbar .t{width:230px;font-size:14px}.yk-hbar .track{flex:1;height:10px;background:var(--bg);border-radius:5px}.yk-hbar .fill{height:10px;background:var(--primary);border-radius:5px}
.yk-bar{display:flex;height:14px;gap:2px}.yk-bar span{border-radius:3px;display:block}.yk-legend{display:flex;justify-content:space-between;color:var(--sub);font-size:12px;margin:4px 0 12px}
.yk-a5{border:1px solid #e5e7eb;border-radius:16px;overflow:hidden;background:#fff}.yk-a5 img{width:100%;height:170px;object-fit:cover;display:block}.yk-a5 .body{padding:12px 14px 4px}
.yk-ep{border-radius:10px;padding:10px 12px;font-size:13px;line-height:1.6;background:#f3f6fa;margin-bottom:8px}.yk-ep.good{background:#eef8f1}.yk-ep.regret{background:#fff8e8}.yk-ep b{display:block;font-size:12px;margin-bottom:2px}
.yk-cta{background:#2048a0;color:#fff;text-align:center;border-radius:10px;padding:10px;font-weight:700;margin:6px 0}
.yk-err{color:var(--err);font-size:12px;margin:-6px 0 8px}
.yk-hero{background:linear-gradient(135deg,#1b3a85,#254aa5);color:#fff;border-radius:16px;padding:48px 40px;min-height:380px}.yk-hero h1{color:#fff;font-size:40px;padding:0;margin:0 0 8px}
.yk-tbl{width:100%;border-collapse:collapse;font-size:14px}.yk-tbl th{text-align:left;color:var(--sub);font-size:12px;border-bottom:1px solid var(--line);padding:6px 8px}.yk-tbl td{border-bottom:1px solid var(--line);padding:8px;vertical-align:top;white-space:pre-wrap}
.yk-chg{background:#fff8e8;font-weight:700}.yk-row{border-top:1px solid var(--line);margin:4px 0}
.yk-qcard{font-size:17px;line-height:1.8}
</style>""", unsafe_allow_html=True)


# ---------- 時刻: デモデータの時刻を「いま」に合わせる ----------
def now() -> datetime:
    return datetime.now(JST).replace(microsecond=0)


def parse(iso: str | None) -> datetime | None:
    return datetime.fromisoformat(iso) if iso else None


def iso(d: datetime | None) -> str | None:
    return d.isoformat() if d else None


def rebase(snap: dict) -> dict:
    """スナップショットを取った時刻からの経過ぶん、ずらす。
    申し込みの日時は「いま」からの差を保ち、19時台の面談は日付だけずらす(make_demo_seed.py の作り方に合わせる)。"""
    s = copy.deepcopy(snap)
    taken, cur = parse(s["taken_at"]), now()
    delta, days = cur - taken, (cur.date() - taken.date()).days

    def exact(v):
        return iso(parse(v) + delta) if v else v

    def meet(a, b):
        a0, b0 = parse(a), parse(b)
        if a0.hour >= 19:
            return iso(a0 + timedelta(days=days)), iso(b0 + timedelta(days=days))
        a1 = (a0 + delta).replace(minute=0, second=0)
        return iso(a1), iso(a1 + (b0 - a0))

    for r in s["requests"]:
        r["created_at"] = exact(r["created_at"])
        for p in r["proposals"]:
            p["starts_at"], p["ends_at"] = meet(p["starts_at"], p["ends_at"])
        if r["record"]:
            r["record"]["recorded_at"] = exact(r["record"].get("recorded_at"))
    if s["me"].get("story_draft"):
        s["me"]["story_draft"]["submitted_at"] = exact(s["me"]["story_draft"]["submitted_at"])
    return s


def fmt_date(v, with_time=True) -> str:
    d = parse(v) if isinstance(v, str) else v
    if not d:
        return ""
    md = f"{d.month}/{d.day}（{'月火水木金土日'[d.weekday()]}）"
    return f"{md} {d:%H:%M}" if with_time else md


def fmt_wait(h) -> str:
    if h is None:
        return "—"
    if h < 1:
        return "1時間以内"
    return f"{h // 24}日{f'{h % 24}時間' if h % 24 else ''}" if h >= 24 else f"{h}時間"


# ---------- 状態(このタブの中だけ) ----------
ss = st.session_state
if "db" not in ss:
    ss.db = rebase(SNAP)
    ss.user, ss.page, ss.sel, ss.sched_sel = None, "home", None, None
    ss.flash, ss.ver, ss.story_err = "", 0, {}
    ss.slots, ss.decline = {}, {}
    ss.qi, ss.done_tags = 0, None
    ss.ans = {q["id"]: q["answer"] for q in SNAP["questions"] if q["answer"] is not None}
DB = ss.db
REQ = {r["id"]: r for r in DB["requests"]}
ME = DB["me"]
TARGET = DB["reply_target_days"]


def go(page: str, **kw):
    ss.page = page
    for k, v in kw.items():
        ss[k] = v
    st.rerun()


def say(msg: str):
    ss.flash = msg


def flash():
    if ss.flash:
        st.markdown(f'<div class="yk-ok">{esc(ss.flash)}</div>', unsafe_allow_html=True)
        ss.flash = ""


def esc(t) -> str:
    return html.escape(str(t or ""))


def md(h: str):
    st.markdown(h, unsafe_allow_html=True)


def waiting_hours(r) -> int | None:
    return int((now() - parse(r["created_at"])).total_seconds() // 3600) if r["status"] == "new" else None


def overdue(r) -> bool:
    return r["status"] == "new" and parse(r["created_at"]) < now() - timedelta(days=TARGET)


# ---------- 表示の部品(Next.js 版の RequestContext / lib/client と同じ文言) ----------
def source_text(s: dict) -> str:
    if s["route"] == "own_story":
        return "あなたの経験談を読んで"
    if s["route"] == "graduate_story":
        return f"卒業生（{s['writer_label']}{'・' + s['writer_situation'] if s.get('writer_situation') else ''}）の経験談から"
    if s["route"] == "staff_story":
        return f"{s['writer_label']}さんの経験談から"
    return "経験談を通らずに"


def free_text_label(s: dict) -> str:
    return "気になったこと" if s["route"] == "graduate_story" else "先に聞きたいこと"


def customer_line(c: dict) -> str:
    return "・".join(x for x in [c.get("age_band"), c.get("faculty") and f"西南・{c['faculty']}"] if x)


def chips(items, cls="") -> str:
    return "".join(f'<span class="yk-chip {cls}">{esc(i)}</span>' for i in items)


def situations(c: dict, mx=3) -> str:
    s = c["situations"]
    more = f'<span class="yk-muted">ほか{len(s) - mx}つ</span>' if len(s) > mx else ""
    return chips(s[:mx]) + more


def source_line(s: dict) -> str:
    h = f'<span>「{esc(s["headline"])}」</span>' if s.get("headline") else ""
    return f'<div class="yk-src src-{s["route"]}"><b>{esc(source_text(s))}</b>{h}</div>'


def badge(status: str) -> str:
    return f'<span class="yk-badge b-{status}">{STATUS_LABEL[status]}</span>'


def ask_text(r) -> str:
    return r["pre_question"] or " / ".join(r["ask_topics"]) or "—"


def meets() -> list:
    out = []
    for r in DB["requests"]:
        ch = next((p for p in r["proposals"] if p["chosen"]), None)
        if r["status"] in ("scheduled", "done") and ch:
            out.append({**r, "starts_at": ch["starts_at"], "ends_at": ch["ends_at"], "method": ch["method"],
                        "place": ch["place"], "recorded": r["record"] is not None})
    return sorted(out, key=lambda m: m["starts_at"])


def photo_tag(url: str | None) -> str:
    p = ROOT / "frontend" / "public" / (url or "").lstrip("/")
    if not url or not p.exists():
        return '<div style="height:170px;background:#e5e7eb"></div>'
    return f'<img src="data:image/webp;base64,{base64.b64encode(p.read_bytes()).decode()}" alt="">'


# ---------- P1 ログイン ----------
def page_login():
    left, right = st.columns([1.1, 1], gap="large")
    with left:
        md('<div class="yk-hero"><h1>よかね</h1><p style="font-size:18px;font-weight:700">行員用のページ</p>'
           '<p style="opacity:.85">お客さまから届いた「話を聞いてみたい」に返事をしたり、プロフィールを整えたりできます。</p></div>')
    with right:
        st.subheader("ログイン")
        try:
            code = st.secrets.get("DEMO_PASSCODE", "")
        except Exception:
            code = ""
        typed = st.text_input("デモ用パスコード", type="password") if code else ""
        md('<div class="yk-label">だれとして入るか</div>')
        c1, c2 = st.columns(2)
        who = None
        if c1.button(f"{DB['staff']['display_name']}（行員）として入る", type="primary", width="stretch"):
            who = "staff"
        if c2.button("運営として入る", width="stretch"):
            who = "admin"
        if who:
            if code and typed != code:
                st.error("パスコードが違います")
            else:
                go("home" if who == "staff" else "admin", user=who)
        md('<p class="yk-muted">デモ用のログインです。本番では職場のアカウントでログインする想定です。</p>'
           '<div class="yk-demo">この Streamlit 版はデモデータだけで動きます。返事・記録・保存は、このタブを開いている間だけ残ります（再読み込みすると最初に戻ります）。お客さま側のアプリやDBにはつながっていません。</div>')


# ---------- サイドバー ----------
MENU = [("home", "ホーム"), ("requests", "届いた希望"), ("schedule", "予定"), ("insights", "お客さまの傾向"),
        ("profile", "プロフィール"), ("answers", "12問の答え")]


def sidebar():
    with st.sidebar:
        md('<div style="font-size:20px;font-weight:700;color:#254aa5">よかね</div><div class="yk-muted">行員用（デモ）</div>')
        st.write("")
        items = MENU if ss.user == "staff" else [("admin", "運営")]
        for key, label in items:
            on = ss.page == key or (key == "requests" and ss.page == "detail")
            if st.button(label, key=f"nav_{key}", type="primary" if on else "secondary", width="stretch"):
                go(key)
        st.write("")
        name = DB["staff"]["display_name"] if ss.user == "staff" else "運営"
        md(f"<b>{esc(name)}</b>")
        if st.button("ログアウト", key="logout"):
            go("home", user=None)
        md('<div class="yk-demo">デモデータで動いています。操作はこのタブの中だけで、再読み込みすると元に戻ります。</div>')


# ---------- P2 ホーム ----------
def page_home():
    n = now()
    waiting = sorted([r for r in DB["requests"] if r["status"] == "new"], key=lambda r: r["created_at"])
    ms = meets()
    upcoming = [m for m in ms if parse(m["starts_at"]) >= n]
    today = [m for m in upcoming if parse(m["starts_at"]).date() == n.date()]
    nxt = next((m for m in upcoming if parse(m["starts_at"]).date() != n.date()), None)
    to_record = [m for m in ms if parse(m["starts_at"]) < n and not m["recorded"]]
    month_start = n.replace(day=1, hour=0, minute=0, second=0)
    mine = [r for r in DB["requests"] if parse(r["created_at"]) >= month_start]
    held = sum(1 for r in mine if r["record"] and r["record"]["held"])
    promised = sum(1 for r in mine if r["record"] and r["record"]["held"] and r["record"]["next_promise"])
    greet = "おはようございます" if n.hour < 11 else "こんにちは" if n.hour < 18 else "おつかれさまです"
    todo = len(waiting) + len(today) + len(to_record)
    st.title(f"{greet}、{DB['staff']['display_name'].split(' ')[0]}さん")
    md(f'<p>{fmt_date(n, False)}　' + (f"今日やることは <b>{todo}件</b> です" if todo else "今日やることはありません") + "</p>")
    flash()
    left, right = st.columns([1.7, 1], gap="medium")
    with left, st.container(border=True):
        h1, h2 = st.columns([2.2, 1.6], vertical_alignment="center")
        h1.subheader(f"返事を待っているお客さま　{len(waiting)}件")
        if h2.button("届いた希望をすべて見る →", key="home_all"):
            go("requests")
        if not waiting:
            md('<p class="yk-muted">返事が必要な希望はありません</p>')
        for r in waiting:
            md('<div class="yk-row"></div>')
            a, b = st.columns([5, 1], vertical_alignment="center")
            over = f' <span class="yk-badge b-over">目安の{TARGET}日を過ぎています</span>' if overdue(r) else ""
            a.markdown(f'<b style="font-size:16px">{esc(r["requester_name"])}様</b> {situations(r["customer"])}{over}'
                       f'<div>{esc(ask_text(r))}</div>{source_line(r["source"])}'
                       f'<div class="yk-muted" style="color:{"var(--err)" if overdue(r) else ""}">'
                       f'{esc("・".join(r["preferences"] + [METHOD_LABEL[r["meeting_method"]]]))}　／　届いてから {fmt_wait(waiting_hours(r))}</div>',
                       unsafe_allow_html=True)
            if b.button("返事する", key=f"home_reply_{r['id']}", type="primary"):
                go("detail", sel=r["id"])
    with right, st.container(border=True):
        st.subheader(f"今日の予定　{len(today)}件")
        if not today:
            md('<p class="yk-muted">今日の予定はありません</p>')
        for m in today:
            place = f"（{m['place']}）" if m["place"] else ""
            pre = (f'<div class="yk-label">先に聞きたいこと</div><div>{esc(ask_text(m))}</div>'
                   if m["pre_question"] or m["ask_topics"] else "")
            md(f'<div class="yk-today"><div class="yk-time">{parse(m["starts_at"]):%H:%M} – {parse(m["ends_at"]):%H:%M}</div>'
               f'<b style="font-size:16px">{esc(m["requester_name"])}様　{METHOD_LABEL[m["method"]]}{esc(place)}</b><div>{situations(m["customer"])}</div>{pre}</div>')
            if st.button("お客さまの考えを見て準備する", key=f"home_prep_{m['id']}"):
                go("detail", sel=m["id"])
        if nxt:
            place = f"・{nxt['place']}" if nxt["place"] else ""
            md(f'<p class="yk-muted">次の予定　{fmt_date(nxt["starts_at"])}　{esc(nxt["requester_name"])}様（{METHOD_LABEL[nxt["method"]]}{esc(place)}）</p>')
    left, right = st.columns([1.7, 1], gap="medium")
    with left, st.container(border=True):
        st.subheader(f"記録がまだの面談　{len(to_record)}件")
        if not to_record:
            md('<p class="yk-muted">記録がまだの面談はありません</p>')
        for m in to_record:
            a, b = st.columns([5, 1], vertical_alignment="center")
            a.markdown(f'<b style="font-size:16px">{fmt_date(m["starts_at"], False)}　{esc(m["requester_name"])}様</b>'
                       '<div class="yk-muted">話せたか・話したテーマ・次の約束を残すと、今月の数字に入ります</div>', unsafe_allow_html=True)
            if b.button("記録する", key=f"home_rec_{m['id']}"):
                go("schedule", sched_sel=m["id"])
    with right, st.container(border=True):
        h1, h2 = st.columns([2, 1], vertical_alignment="center")
        h1.subheader("今月の数字")
        if h2.button("傾向を見る →", key="home_ins"):
            go("insights")
        cols = st.columns(3)
        for col, (k, v) in zip(cols, [("届いた希望", f"{len(mine)}件"), ("会って話した", f"{held}人"), ("次の約束", f"{promised}人")]):
            col.markdown(f'<div class="yk-stat"><div class="k">{k}</div><div class="v">{v}</div></div>', unsafe_allow_html=True)
    md('<p class="yk-muted">売り込みはしない約束です。まずはお客さまの話を聞くところから。</p>')


# ---------- P2-2 届いた希望(一覧) ----------
def page_requests():
    a, b = st.columns([2, 1], vertical_alignment="bottom")
    a.title("届いた希望")
    a.markdown("お客さまから届いた「話を聞いてみたい」の一覧です。行の「開く」で詳細と返事の画面に進みます。")
    word = b.text_input("探す", placeholder="名前・聞きたいこと・状況で探す", label_visibility="collapsed").strip()
    counts = Counter(r["status"] for r in DB["requests"])
    tabs = ["all", "new", "replied", "scheduled", "done", "declined"]
    a, b = st.columns([3, 1], vertical_alignment="center")
    tab = a.segmented_control("状態", tabs, default="all", label_visibility="collapsed",
                              format_func=lambda s: f"すべて {len(DB['requests'])}" if s == "all" else f"{STATUS_LABEL[s]} {counts.get(s, 0)}") or "all"
    sort = b.selectbox("並び", ["wait", "new"], label_visibility="collapsed",
                       format_func=lambda s: "並び：待っている時間が長い順" if s == "wait" else "並び：届いた順（新しい順）")

    def hit(r):
        return (not word or word in r["requester_name"] or word in r["pre_question"] or any(word in t for t in r["ask_topics"])
                or any(word in t for t in r["customer"]["situations"]) or word in (r["source"].get("headline") or ""))
    rows = [r for r in DB["requests"] if (tab == "all" or r["status"] == tab) and hit(r)]
    if sort == "new":
        rows.sort(key=lambda r: r["created_at"], reverse=True)
    else:
        new = sorted([r for r in rows if r["status"] == "new"], key=lambda r: r["created_at"])
        rest = sorted([r for r in rows if r["status"] != "new"], key=lambda r: r["created_at"], reverse=True)
        rows = new + rest
    W = [1.0, 1.4, 3.4, 1.4, 1.0, 1.4, 0.9, 0.9]
    with st.container(border=True):
        if not rows:
            md('<p class="yk-muted">当てはまる希望はありません</p>')
        else:
            for col, h in zip(st.columns(W), ["名前", "いまの状況", "聞きたいこと・どこから来たか", "時間帯・会い方", "届いた日", "状態", "待っている時間", ""]):
                col.markdown(f'<div class="yk-label" style="margin:0">{h}</div>', unsafe_allow_html=True)
        for r in rows:
            md('<div class="yk-row"></div>')
            c = st.columns(W, vertical_alignment="center")
            c[0].markdown(f'<b>{esc(r["requester_name"])}様</b><div class="yk-muted">{esc(r["customer"]["age_band"] or "")}</div>', unsafe_allow_html=True)
            c[1].markdown(situations(r["customer"], 2) or '<span class="yk-muted">—</span>', unsafe_allow_html=True)
            c[2].markdown(f'<div>{esc(ask_text(r))}</div>{source_line(r["source"])}', unsafe_allow_html=True)
            c[3].markdown(f'<span class="yk-muted">{esc("・".join(r["preferences"] + [METHOD_LABEL[r["meeting_method"]]]))}</span>', unsafe_allow_html=True)
            c[4].markdown(f'<span class="yk-muted">{fmt_date(r["created_at"])}</span>', unsafe_allow_html=True)
            c[5].markdown(badge(r["status"]), unsafe_allow_html=True)
            c[6].markdown(f'<span style="color:{"var(--err)" if overdue(r) else "inherit"};font-weight:{700 if overdue(r) else 400}">{fmt_wait(waiting_hours(r))}</span>', unsafe_allow_html=True)
            if c[7].button("開く", key=f"open_{r['id']}"):
                go("detail", sel=r["id"])
    md(f'<p class="yk-muted">{len(DB["requests"])}件中 {len(rows)}件を表示　｜　返事の目安は届いてから{TARGET}日。過ぎたものは赤で出します。</p>')


# ---------- P3 希望の詳細と返事 ----------
def next_days() -> list:
    t = now().date()
    return [t + timedelta(days=i) for i in range(1, 15)]


def page_detail():
    r = REQ.get(ss.sel)
    if r is None:
        go("requests")
    if st.button("← 届いた希望に戻る"):
        go("requests")
    over = ' <span class="yk-badge b-over">返事の目安を過ぎた</span>' if overdue(r) else ""
    md(f'<h1 style="padding-bottom:4px">{esc(r["requester_name"])}様からの希望　{badge(r["status"])}{over}</h1>')
    flash()
    left, right = st.columns(2, gap="medium")
    with left, st.container(border=True):
        st.subheader("お客さまのこと")
        c = r["customer"]
        md('<div class="yk-label">いまの状況</div>' + (situations(c, 9) if c["situations"] else '<span class="yk-muted">選んでいません</span>')
           + (f'<div class="yk-muted">{esc(customer_line(c))}</div>' if customer_line(c) else ""))
        md('<div class="yk-label">どこから来たか</div>' + source_line(r["source"]))
        if r["story"]:
            s = r["story"]
            with st.expander("お客さまが読んだ経験談を見る"):
                md(f'<div class="yk-story"><h4>やって良かったこと</h4><p>{esc(s["good_text"])}</p><h4>後悔していること</h4><p>{esc(s["regret_text"])}</p>'
                   f'<h4>きっかけ｜{esc(s["trigger_title"])}</h4><p>{esc(s["trigger_body"])}</p>'
                   f'<h4>迷ったこと｜{esc(s["hesitation_title"])}</h4><p style="margin:0">{esc(s["hesitation_body"])}</p></div>')
        if r["source"]["route"] == "graduate_story":
            md('<div class="yk-note">卒業生の話を読んで、考え方の近いあなたに届いた希望です。卒業生の名前はお客さまにも出していません。</div>')
        if r["ask_topics"]:
            md('<div class="yk-label">聞いてみたいこと</div>' + "".join(f"<div>・{esc(t)}</div>" for t in r["ask_topics"]))
        md(f'<div class="yk-label">{free_text_label(r["source"])}</div><div>{esc(r["pre_question"] or "—")}</div>')
        md(f'<div class="yk-label">都合のいい時間帯・会い方</div><div>{esc("・".join(r["preferences"]) or "時間帯の指定なし")} ／ {METHOD_LABEL[r["meeting_method"]]}</div>')
        md('<div class="yk-label">考えの近さ・お客さまの考え（12問から）</div>')
        if r["result"]:
            md(f'<div><b>3つの軸のうち {r["result"]["same_levels"]} つがあなたと同じ</b></div>' + "".join(f"<div>・{esc(t)}</div>" for t in r["result"]["texts"]))
        else:
            md('<span class="yk-muted">お客さまが「考えを見せてよい」にしていないので表示しません</span>')
        md(f'<p class="yk-muted" style="margin-top:10px">届いた日 {fmt_date(r["created_at"])}</p>')
    with right, st.container(border=True):
        st.subheader("返事")
        rid = r["id"]
        can = r["status"] in ("new", "replied")
        days = next_days()
        if can and not ss.decline.get(rid):
            md('<p class="yk-muted">話せる日にちを3つまで出せます。お客さまが1つ選ぶと決まります。</p>')
            slots = ss.slots.setdefault(rid, [{"date": days[1], "time": "19:00", "method": r["meeting_method"]}])
            for i, s in enumerate(slots):
                c1, c2, c3, c4 = st.columns([1.8, 1.1, 1.5, 0.6], vertical_alignment="bottom")
                s["date"] = c1.selectbox("日にち", days, index=days.index(s["date"]) if s["date"] in days else 0, key=f"d_{rid}_{i}_{len(slots)}",
                                         format_func=lambda d: fmt_date(datetime(d.year, d.month, d.day), False), label_visibility="collapsed")
                s["time"] = c2.selectbox("時間", TIMES, index=TIMES.index(s["time"]), key=f"t_{rid}_{i}_{len(slots)}", label_visibility="collapsed")
                s["method"] = c3.selectbox("会い方", ["online", "in_person"], index=["online", "in_person"].index(s["method"]),
                                           format_func=METHOD_LABEL.get, key=f"m_{rid}_{i}_{len(slots)}", label_visibility="collapsed")
                if c4.button("×", key=f"x_{rid}_{i}"):
                    slots.pop(i)
                    st.rerun()
            if len(slots) < 3 and st.button("＋ 日にちを足す"):
                slots.append({"date": days[min(2 + len(slots), len(days) - 1)], "time": "19:00", "method": r["meeting_method"]})
                st.rerun()
            b1, b2 = st.columns(2)
            if b1.button("日にちを出し直す" if r["status"] == "replied" else "話せます（返事を送る）", type="primary", width="stretch"):
                r["proposals"] = []
                for k, s in enumerate(slots, 1):
                    hh, mm = map(int, s["time"].split(":"))
                    a = datetime(s["date"].year, s["date"].month, s["date"].day, hh, mm, tzinfo=JST)
                    r["proposals"].append({"id": rid * 10 + k, "starts_at": iso(a), "ends_at": iso(a + timedelta(minutes=30)),
                                           "method": s["method"], "place": "", "chosen": False})
                r["status"] = "replied"
                say("返事を送りました。お客さまが日にちを選ぶと「予定」に入ります。")
                st.rerun()
            if b2.button("今回は見送る", width="stretch"):
                ss.decline[rid] = True
                st.rerun()
        if can and ss.decline.get(rid):
            st.write("理由を選んでください（お客さまには「今回は難しそうです」とだけ伝わります）")
            cols = st.columns(2)
            for k, reason in enumerate(DB["decline_reasons"]):
                if cols[k % 2].button(reason, key=f"dec_{rid}_{k}", width="stretch"):
                    r["status"], r["decline_reason"] = "declined", reason
                    ss.decline[rid] = False
                    say("見送りました。")
                    st.rerun()
            if st.button("やめる"):
                ss.decline[rid] = False
                st.rerun()
        if r["proposals"]:
            md('<div class="yk-label">出した日にち</div>' + "".join(
                f'<div>{"✔ " if p["chosen"] else "・"}{fmt_date(p["starts_at"])}〜 {METHOD_LABEL[p["method"]]}{esc("（" + p["place"] + "）" if p["place"] else "")}'
                f'{"<b>（お客さまが選んだ）</b>" if p["chosen"] else ""}</div>' for p in r["proposals"]))
        if r["status"] == "replied" and r["proposals"]:
            md('<div class="yk-demo">デモだけの操作：お客さま側のアプリにはつながっていないので、お客さまが日にちを選んだことにできます。</div>')
            for p in r["proposals"]:
                if st.button(f"お客さまが {fmt_date(p['starts_at'])} を選んだことにする", key=f"choose_{p['id']}"):
                    for q in r["proposals"]:
                        q["chosen"] = q is p
                    r["status"] = "scheduled"
                    say("お客さまが日にちを選びました。「予定」に入りました。")
                    st.rerun()
        if r["status"] == "declined":
            md(f'<p class="yk-muted">見送った理由：{esc(r["decline_reason"])}</p>')
        if r["status"] in ("scheduled", "done") and st.button("予定と記録へ"):
            go("schedule", sched_sel=rid)
        md('<div class="yk-note">売り込みはしない約束です。まずは話を聞くところから。</div>')


# ---------- P4 予定と話したあとのメモ ----------
def page_schedule():
    st.title("予定")
    flash()
    items = meets()
    if ss.sched_sel not in [m["id"] for m in items]:
        ss.sched_sel = next((m["id"] for m in items if not m["recorded"]), items[0]["id"] if items else None)
    left, right = st.columns([1.1, 1], gap="medium")
    with left, st.container(border=True):
        if not items:
            md('<p class="yk-muted">決まった予定はまだありません</p>')
        for m in items:
            with st.container(border=True):
                past = "（終わった）" if parse(m["starts_at"]) < now() else ""
                place = f"（{m['place']}）" if m["place"] else ""
                md(f'<div class="yk-muted">{fmt_date(m["starts_at"])}〜{past}</div><b>{esc(m["requester_name"])}様</b> {situations(m["customer"], 2)}'
                   f'<div>{esc(m["pre_question"] or (m["ask_topics"][0] if m["ask_topics"] else ""))}</div>{source_line(m["source"])}'
                   f'<div class="yk-muted">{METHOD_LABEL[m["method"]]}{esc(place)}　{"記録あり" if m["recorded"] else "記録まだ"}</div>')
                if st.button("選んでいる" if ss.sched_sel == m["id"] else "メモを書く", key=f"sel_{m['id']}",
                             type="primary" if ss.sched_sel == m["id"] else "secondary"):
                    ss.sched_sel = m["id"]
                    st.rerun()
    with right, st.container(border=True):
        r = REQ.get(ss.sched_sel)
        if not r:
            md('<p class="yk-muted">左の予定を選んでください</p>')
            return
        rec = r["record"] or {"held": True, "topics": [], "next_promise": False, "memo": ""}
        k = f"{r['id']}_{ss.ver}"
        st.subheader(f"話したあとのメモ：{r['requester_name']}様")
        md('<p class="yk-muted">お客さまには見えません。次に話すときの自分のためのメモです。</p>')
        held = st.segmented_control("話せましたか", [True, False], default=rec["held"], key=f"held_{k}",
                                    format_func=lambda v: "話せた" if v else "話せなかった")
        held = True if held is None else held
        topics = st.pills("話したテーマ（いくつでも）", DB["record_topics"], selection_mode="multi", default=rec["topics"], key=f"top_{k}")
        promise = st.segmented_control("次も話す約束", [True, False], default=rec["next_promise"] if held else False, key=f"pro_{k}",
                                       format_func=lambda v: "あり" if v else "なし", disabled=not held)
        memo = st.text_area("メモ（自分だけ）", value=rec["memo"], max_chars=1000, key=f"memo_{k}")
        if st.button("メモを保存する", type="primary"):
            r["record"] = {"held": held, "topics": topics or [], "next_promise": bool(promise) and held, "memo": memo.strip(),
                           "recorded_at": iso(now())}
            r["status"] = "done"
            say("保存しました。この記録は「お客さまの傾向」に数えられます（メモは数えません）。")
            st.rerun()


# ---------- P6 お客さまの傾向 ----------
def bars(items: list):
    if not items:
        md('<p class="yk-muted">まだありません</p>')
        return
    mx = max(1, *(c for _, c in items))
    md("".join(f'<div class="yk-hbar"><span class="t">{esc(l)}</span><span class="track"><span class="fill" style="display:block;width:{c / mx * 100:.0f}%"></span></span><b>{c}件</b></div>' for l, c in items))


def page_insights():
    st.title("お客さまの傾向")
    st.write("あなたに「話を聞いてみたい」と送ってくれた人の傾向です。一人ひとりが分からない形でまとめています。")
    rows, mn = DB["requests"], DB["insights_min_people"]
    total = len(rows)
    if total < mn:
        with st.container(border=True):
            st.write(f"いま {total} 人です。{mn} 人そろうと表示します。")
        return
    held = sum(1 for r in rows if r["record"] and r["record"]["held"])
    promised = sum(1 for r in rows if r["record"] and r["record"]["held"] and r["record"]["next_promise"])
    pct = lambda a, b: round(a / b * 100) if b else 0  # noqa: E731
    cols = st.columns(3)
    for col, (k, v, sub, blue) in zip(cols, [("届いた希望", f"{total}件", "", True), ("会って話した", f"{held}人", f"希望の{pct(held, total)}%", False),
                                             ("次も話す約束", f"{promised}人", f"会った人の{pct(promised, held)}%", False)]):
        with col, st.container(border=True):
            md(f'<div class="yk-stat"><div class="k">{k}</div><div class="v{" blue" if blue else ""}">{v}</div><div class="yk-muted">{sub}</div></div>')
    route = {"own_story": "あなたの経験談を読んで", "direct": "経験談を通らずに"}
    a, b = st.columns(2, gap="medium")
    with a, st.container(border=True):
        st.subheader("いまの状況（お客さまが選んだもの）")
        bars(Counter(s for r in rows for s in r["customer"]["situations"]).most_common())
    with b, st.container(border=True):
        st.subheader("どこから来たか")
        bars(Counter(route.get(r["source"]["route"], "卒業生の経験談から") for r in rows).most_common())
        md('<p class="yk-muted">「卒業生の経験談から」は、卒業生の話を読んで、考え方の近いあなたを選んだ人です。</p><b>年代</b><div style="margin-top:6px">'
           + "".join(f'<span class="yk-chip plain">{esc(l)} <b>{c}人</b></span>' for l, c in Counter(r["customer"]["age_band"] or "答えていない" for r in rows).most_common()) + "</div>")
    a, b = st.columns(2, gap="medium")
    with a, st.container(border=True):
        st.subheader("考えの傾向（12問の答えから）")
        axes = DB["insights"].get("axes")
        if axes:
            colors = ["var(--pale)", "var(--sky)", "var(--primary)"]
            for ax in axes:
                tot = sum(l["count"] for l in ax["levels"]) or 1
                md(f'<b>{AXIS_NAME.get(ax["code"], ax["code"])}</b><div class="yk-bar" style="margin-top:6px">'
                   + "".join(f'<span style="width:{l["count"] / tot * 100:.0f}%;background:{colors[i]}"></span>' for i, l in enumerate(ax["levels"]))
                   + '</div><div class="yk-legend">' + "".join(f'<span>{esc(l["label"])} {l["count"]}人</span>' for l in ax["levels"]) + "</div>")
        else:
            md(f'<p class="yk-muted">「考えを見せてよい」にした人が {DB["insights"].get("shared_count", 0)} 人です。{mn} 人そろうと表示します。</p>')
    with b, st.container(border=True):
        st.subheader("聞いてみたいこと")
        bars(Counter(t for r in rows for t in r["ask_topics"]).most_common())
    a, b = st.columns(2, gap="medium")
    with a, st.container(border=True):
        st.subheader("希望の時間帯")
        prefs = Counter(t for r in rows for t in r["preferences"]).most_common()
        md("".join(f'<span class="yk-chip {"on" if i == 0 else "plain"}">{esc(l)} <b>{c}件</b></span>' for i, (l, c) in enumerate(prefs)))
    with b, st.container(border=True):
        st.subheader("話したテーマ")
        bars(Counter(t for r in rows if r["record"] for t in r["record"]["topics"]).most_common())
    md(f'<p class="yk-muted">集計は{mn}人以上そろってから表示します。名前・連絡先・メモ・年収は集計に含めません。</p>')


# ---------- P5 プロフィールと経験談 ----------
def story_source() -> dict:
    src = ME["story_draft"] or ME["story"] or {}
    out = {k: src.get(k, "") for k, *_ in STORY}
    out["qas"] = [dict(q) for q in (src.get("qas") or [])] + [{"question": "", "answer": ""}] * (4 - len(src.get("qas") or []))
    out["situation_label"] = (ME["story_draft"] or {}).get("situation_label") or ME["profile"].get("situation_label") or ""
    return out


def page_profile():
    st.title("プロフィールと経験談")
    flash()
    v, p, src = ss.ver, ME["profile"], story_source()
    err = ss.story_err
    left, right = st.columns([1.8, 1], gap="large")
    with left:
        with st.container(border=True):
            a, b = st.columns([2, 2], vertical_alignment="center")
            a.subheader("経験談")
            b.markdown(f'<div style="text-align:right"><span class="yk-badge b-replied">確認待ちの書き直しあり（{fmt_date(ME["story_draft"]["submitted_at"])}）</span></div>'
                       if ME["story_draft"] else '<div style="text-align:right"><span class="yk-badge b-scheduled">公開中</span></div>', unsafe_allow_html=True)
            md('<p class="yk-muted">お客さまが「近い人の経験談」で読む、あなたの経験です。書き直すと運営が確かめてから公開されます（それまでは今の文が出ます）。金額（円・万円・年収）と今の年齢は、本人が特定されやすいので書けません。</p>')
            ed = {"situation_label": st.text_input("状況の札（例　家を買って3年）", value=src["situation_label"], max_chars=30, key=f"sl_{v}")}
            for k, label, mx, long in STORY:
                w = st.text_area if long else st.text_input
                ed[k] = w(label, value=src[k], max_chars=mx, key=f"st_{k}_{v}")
                for m in err.get(k, []):
                    md(f'<div class="yk-err">{m}</div>')
            st.subheader("Q&A（4問）")
            md('<p class="yk-muted">直接話す前に、お客さまがよく聞きたくなることへの答えを先に載せます。</p>')
            ed["qas"] = []
            for i, qa in enumerate(src["qas"], 1):
                q = st.text_input(f"Q{i} 問い", value=qa["question"], max_chars=200, key=f"q_{i}_{v}")
                for m in err.get(f"qas.{i}.question", []):
                    md(f'<div class="yk-err">{m}</div>')
                ans = st.text_area(f"A{i} 答え", value=qa["answer"], max_chars=600, key=f"a_{i}_{v}", height=80)
                for m in err.get(f"qas.{i}.answer", []):
                    md(f'<div class="yk-err">{m}</div>')
                ed["qas"].append({"question": q, "answer": ans})
            b1, b2 = st.columns(2)
            if b1.button("書き直しを送る（運営が確かめてから公開）", type="primary", width="stretch"):
                texts = {k: ed[k] for k, *_ in STORY} | {f"qas.{i}.{w}": qa[w] for i, qa in enumerate(ed["qas"], 1) for w in ("question", "answer")}
                empty = [k for k, t in texts.items() if not t.strip()]
                money = {k: ["金額（円・万円・年収）は書けません"] for k, t in texts.items() if MONEY.search(t)}
                if money:
                    ss.story_err = money
                    st.error("金額や今の年齢は書けません（本人が特定されやすいため）")
                elif empty:
                    ss.story_err = {k: ["書いてください"] for k in empty}
                    st.error("空いている欄があります")
                else:
                    ME["story_draft"] = {**{k: ed[k].strip() for k, *_ in STORY}, "qas": [{w: qa[w].strip() for w in qa} for qa in ed["qas"]],
                                         "situation_label": ed["situation_label"].strip() or None, "submitted_at": iso(now())}
                    ss.story_err, ss.ver = {}, ss.ver + 1
                    say("経験談の書き直しを送りました。運営が確かめてから、お客さまの画面に出ます。（デモでは、ログアウトして「運営として入る」から公開できます）")
                    st.rerun()
            if ME["story_draft"] and b2.button("書き直しを取り消す", width="stretch"):
                ME["story_draft"], ss.story_err, ss.ver = None, {}, ss.ver + 1
                say("書き直しを取り消しました。公開中の経験談はそのままです。")
                st.rerun()
        with st.container(border=True):
            st.subheader("基本情報（プロフィールのタブ）")
            hidden = set(p.get("hidden_fields") or [])
            f = {"name": st.text_input("名前（お客さまに見える名前）", value=p["name"], max_chars=50, key=f"pn_{v}"),
                 "one_liner": st.text_input("ひと言", value=p.get("one_liner") or "", max_chars=100, key=f"po_{v}")}
            new_hidden = set()
            for k, label, long in FIELDS:
                a, b = st.columns([5, 1], vertical_alignment="center")
                f[k] = (a.text_area if long else a.text_input)(label, value=p.get(k) or "", max_chars=1000 if long else 50, key=f"pf_{k}_{v}")
                if not b.toggle("見せる", value=k not in hidden, key=f"ph_{k}_{v}"):
                    new_hidden.add(k)
            picked = {}
            for kind, label in [("specialty", "得意分野"), ("private", "プライベート")]:
                lo, hi = ME["tag_range"][kind]
                tags = [t for t in ME["tags"] if t["kind"] == kind]
                names = {t["name"]: t["id"] for t in tags}
                picked[kind] = st.pills(f"{label}のタグ（{lo}〜{hi}個）", list(names), selection_mode="multi",
                                        default=[t["name"] for t in tags if t["selected"]], key=f"pt_{kind}_{v}") or []
                if kind == "private" and not st.toggle("プライベートのタグを見せる", value="private_tags" not in hidden, key=f"ph_private_{v}"):
                    new_hidden.add("private_tags")
            acc = st.segmented_control("新しい希望を受ける", [True, False], default=p["accepting"], key=f"pa_{v}",
                                       format_func=lambda x: "受ける" if x else "いまは止める")
            if st.button("基本情報を保存する", type="primary"):
                bad = [f"{lab}のタグは{ME['tag_range'][k][0]}〜{ME['tag_range'][k][1]}個にしてください" for k, lab in [("specialty", "得意分野"), ("private", "プライベート")]
                       if not ME["tag_range"][k][0] <= len(picked[k]) <= ME["tag_range"][k][1]]
                if bad:
                    st.error("タグの数を確かめてください：" + "／".join(bad))
                elif not f["name"].strip():
                    st.error("名前を書いてください")
                else:
                    p.update({k: (val.strip() or None) if k != "name" else val.strip() for k, val in f.items()})
                    p["hidden_fields"], p["accepting"] = sorted(new_hidden), acc if acc is not None else p["accepting"]
                    sel = set(picked["specialty"]) | set(picked["private"])
                    for t in ME["tags"]:
                        t["selected"] = t["name"] in sel
                    ss.ver += 1
                    say("基本情報を保存しました。お客さま側の画面に反映されます。（デモでは、このタブの中だけです）")
                    st.rerun()
    with right:
        st.markdown("**お客さまからの見え方（経験談の詳細）**")
        alumni = f"西南・{p.get('faculty') or ''}{'OG' if p.get('gender') == '女性' else 'OB'}"
        label = ed["situation_label"]
        md(f'<div class="yk-a5">{photo_tag(p.get("photo_url"))}<div class="body"><b style="font-size:18px">{esc(f["name"])}さんのこと</b><div style="margin-top:6px">'
           f'{chips([alumni] + ([label] if label else []))}<span class="yk-chip on">福銀の行員</span></div></div></div>')
        t1, t2, t3 = st.tabs(["エピソード", "Q&A", "プロフィール"])
        with t1:
            md(f'<div class="yk-ep good"><b>やって良かったこと</b>{esc(ed["good_text"] or "—")}</div><div class="yk-ep regret"><b>後悔していること</b>{esc(ed["regret_text"] or "—")}</div>'
               f'<div class="yk-ep"><b>きっかけ｜{esc(ed["trigger_title"])}</b>{esc(ed["trigger_body"] or "—")}</div><div class="yk-ep"><b>迷ったこと｜{esc(ed["hesitation_title"])}</b>{esc(ed["hesitation_body"] or "—")}</div>')
        with t2:
            md("".join(f'<div class="yk-ep"><b>Q. {esc(q["question"] or "—")}</b>{esc(q["answer"] or "—")}</div>' for q in ed["qas"]))
        with t3:
            spec = [t for t in ME["tags"] if t["kind"] == "specialty" and t["name"] in picked["specialty"]]
            priv = [t for t in ME["tags"] if t["kind"] == "private" and t["name"] in picked["private"]]
            md((f'<div>「{esc(f["one_liner"])}」</div>' if f["one_liner"] else "")
               + f'<div style="margin:6px 0">{chips([x for x in ME["value_tags"] if x], "on")}</div>'
               + "".join(f'<div style="font-size:13px;margin-bottom:6px"><div class="yk-muted">{lab}</div>{esc(f[k])}</div>' for k, lab, _ in FIELDS if k not in new_hidden and f[k])
               + f'<div class="yk-muted">得意分野　{esc("・".join(t["name"] for t in spec))}</div>'
               + (f'<div style="margin-top:6px">{chips([t["name"] for t in priv], "plain")}</div>' if "private_tags" not in new_hidden else ""))
        md('<div class="yk-cta">この人に話を聞いてみる</div>' + ("" if acc is not False else '<div class="yk-err" style="margin:0">いまは新しい希望を受けていません</div>'))
        md(f'<p class="yk-muted">一覧のカードには「カードの一言」が出ます：「{esc(ed["headline"] or "—")}」</p>'
           '<p class="yk-muted">「見せない」にした項目は表示されません。行員の年齢は出しません。</p>')


# ---------- B2 12問の答え ----------
def evaluate(ans: dict) -> list:
    sc = DB["scoring"]
    score = {a: 0 for a in sc["axes"]}
    for q in sc["questions"]:
        score[q["axis"]] += ans.get(q["id"], 0) * q["direction"]
    th = sc["thresholds"]
    level = {a: (-1 if s <= th["minus_max"] else 1 if s >= th["plus_min"] else 0) for a, s in score.items()}
    return [(sc["labels"].get(a) or {}).get(str(level[a])) for a in sc["axes"]]


def page_answers():
    qs = DB["questions"]
    if ss.done_tags is not None:
        st.title("答えを保存しました")
        st.write("あなたの考えのタグはこうなりました。お客さまの「考えが近い人」の並びに使われます。")
        md(chips([x for x in ss.done_tags if x], "on"))
        md('<p class="yk-muted">本人の体験と向きが大きく食い違っていないか、プロフィールで確かめてください。（デモでは、このタブの中だけです）</p>')
        a, b = st.columns([1, 1])
        if a.button("プロフィールへ", type="primary"):
            go("profile")
        if b.button("もう一度答える"):
            ss.done_tags, ss.qi = None, 0
            st.rerun()
        return
    st.title("あなたも12問に答えてください")
    st.write("答えがマッチングに使われます。お客さまと同じ質問です。")
    q = qs[ss.qi]
    md(f'<p class="yk-muted">{ss.qi + 1} / {len(qs)}</p>')
    with st.container(border=True):
        md(f'<b>{esc(q["summary"])}</b><div class="yk-qcard">{esc(q["episode_text"])}</div><div class="yk-muted">{esc(q["source_label"])}</div>')
    cols = st.columns(3)
    for col, (val, label) in zip(cols, [(-1, "ちがうかも"), (0, "パス"), (1, "わかる")]):
        if col.button(label, key=f"ans_{q['id']}_{val}", type="primary" if ss.ans.get(q["id"]) == val else "secondary", width="stretch"):
            ss.ans[q["id"]] = val
            if ss.qi < len(qs) - 1:
                ss.qi += 1
            else:
                ME["value_tags"] = evaluate(ss.ans)
                for x in qs:
                    x["answer"] = ss.ans.get(x["id"])
                ss.done_tags = ME["value_tags"]
            st.rerun()
    if ss.qi > 0 and st.button("ひとつ戻す"):
        ss.qi -= 1
        st.rerun()


# ---------- 運営 ----------
def export_csv() -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["request_id", "speaker_key", "route", "story_id", "situations", "age_band", "created_at", "status", "decline_reason",
                "meeting_method", "ask_topics", "share_result", "proposals", "meet_at", "held", "next_promise", "talked_topics"])
    for r in sorted(DB["requests"], key=lambda r: r["id"]):
        ch = next((p for p in r["proposals"] if p["chosen"]), None)
        rec = r["record"]
        w.writerow([r["id"], ME["profile"]["speaker_key"], r["source"]["route"], r["source"].get("story_id") or "",
                    " ".join(r["customer"]["situations"]), r["customer"]["age_band"] or "", r["created_at"], r["status"],
                    r["decline_reason"] or "", r["meeting_method"], " / ".join(r["ask_topics"]), int(r["share_result"]),
                    len(r["proposals"]), ch["starts_at"] if ch else "", "" if rec is None else int(rec["held"]),
                    "" if rec is None else int(rec["next_promise"]), " / ".join(rec["topics"]) if rec else ""])
    return ("﻿" + buf.getvalue()).encode("utf-8")


def page_admin():
    st.title("運営")
    flash()
    with st.container(border=True):
        st.subheader("記録の書き出し")
        md('<p class="yk-muted">申し込み・どこから来たか・お客さまの状況・返事・面談・記録をCSVで出します。名前・連絡先・メモ・年収は入りません。（デモでは森下さん宛ての分だけです）</p>')
        st.download_button("CSVを書き出す", export_csv(), file_name="yokane_staff_export.csv", mime="text/csv", type="primary")
    with st.container(border=True):
        st.subheader("確認待ちの経験談")
        md('<p class="yk-muted">行員が書き直した経験談です。金額と今の年齢は送る時点で止めています。言い回しや中身を確かめてから公開してください。</p>')
        d = ME["story_draft"]
        if not d:
            md('<p class="yk-muted">ありません</p><div class="yk-demo">デモでは、森下さんとして入り「プロフィール」で経験談を書き直して送ると、ここに出ます。</div>')
            return
        cur = ME["story"] or {}
        md(f'<b>{esc(ME["profile"]["name"])}さん</b>　<span class="yk-muted">{fmt_date(d["submitted_at"])} に送信</span>')
        rows = [("状況の札", ME["profile"].get("situation_label") or "—", d["situation_label"] or "（変えない）",
                 (d["situation_label"] or None) != ME["profile"].get("situation_label"))]
        rows += [(lab.split("（一覧")[0], cur.get(k) or "—", d[k], cur.get(k) != d[k]) for k, lab, *_ in STORY]
        old_qas = cur.get("qas") or []
        for i, q in enumerate(d["qas"]):
            o = old_qas[i] if i < len(old_qas) else {"question": "—", "answer": ""}
            rows.append((f"Q&A {i + 1}", f"Q. {o['question']}\n{o['answer']}", f"Q. {q['question']}\n{q['answer']}", o != q))
        md('<table class="yk-tbl"><thead><tr><th style="width:150px">項目</th><th>いま公開中</th><th>書き直し</th></tr></thead><tbody>'
           + "".join(f'<tr><td>{esc(a)}</td><td class="yk-muted">{esc(b)}</td><td class="{"yk-chg" if ch else ""}">{esc(c)}</td></tr>' for a, b, c, ch in rows)
           + "</tbody></table>")
        if st.button("確かめたので公開する", type="primary"):
            texts = [d[k] for k, *_ in STORY] + [q[w] for q in d["qas"] for w in ("question", "answer")]
            if any(MONEY.search(t) for t in texts):
                st.error("金額や今の年齢が含まれています")
            else:
                ME["story"] = {**(ME["story"] or {}), **{k: d[k] for k, *_ in STORY}, "qas": d["qas"]}
                if d["situation_label"]:
                    ME["profile"]["situation_label"] = d["situation_label"]
                ME["story_draft"], ss.ver = None, ss.ver + 1
                say(f"{ME['profile']['name']}さんの経験談を公開しました。お客さまの画面にすぐ出ます。（デモでは、このタブの中だけです）")
                st.rerun()


# ---------- 振り分け ----------
if ss.user is None:
    page_login()
else:
    sidebar()
    if ss.user == "admin":
        page_admin()
    else:
        {"home": page_home, "requests": page_requests, "detail": page_detail, "schedule": page_schedule,
         "insights": page_insights, "profile": page_profile, "answers": page_answers}.get(ss.page, page_home)()
