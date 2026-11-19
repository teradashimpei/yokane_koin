"""行員側のデモデータ(db/demo_seed.sql)を書き出す。db/customer_seed.sql(お客さん側)を入れたあとに流す前提。

    .venv/bin/python -m scripts.make_demo_seed

お客さん側のIDは customer_seed.sql(yokane-back の取り込み結果)に合わせている。
  話し手 1=高野直人(ST0004) 2=森下由美(ST0009) 3=青山祐介(ST0016)。経験談の id は話し手の id と同じ。
  卒業生の経験談: 6=大野 萌(家を買って3年) 15=福田 誠(家を買って8年) 17=遠藤 千尋(家を買って2年目)
                   24=森 ひかり(結婚して1年目) 30=山崎 剛(住宅ローンを完済)
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "db" / "demo_seed.sql"

# 申し込み: (担当の話し手, 経験談(None=経験談を通らず), 状態, 何時間前, 考えを見せてよい, 面談の記録,
#           お客さんの学部・年代・状況, 時間帯, 会い方, 聞いてみたいこと, 気になったこと/先に聞きたいこと)
ASK = ["資産運用に興味があるが、何から始めればいいか", "漠然とした不安・もやもやを聞いてほしい", "もっと他の事例も聞いてみたい"]
PLAN = [
    (2, 2, "new", 3, 1, None, ("法学部", "30a", ["S04", "S05"]), ["平日の夜"], "online", [ASK[1]],
     "家を買うか借りるかで迷っています。買ったあとのお金の計画を聞きたいです"),
    (2, 6, "new", 60, 0, None, (None, "40a", ["S05"]), [], "online", None,
     "一人で家を買うのは早いのか、気になりました"),
    (2, 17, "new", 20, 1, None, ("商学部", "20b", ["S01", "S05"]), [], "in_person", None,
     "頭金をどれくらい用意すればいいのか気になります"),
    (2, 2, "replied", 30, 1, None, ("文学部", "30a", ["S04"]), ["休日の午前", "休日の午後"], "online", [ASK[0]],
     "結婚して家計を一つにしたところです。住まいのお金をどう分けるか聞きたい"),
    (2, 2, "scheduled_today", 72, 1, None, ("法学部", "30b", ["S05"]), ["平日の夜"], "in_person", [ASK[1], ASK[2]],
     "固定金利と変動金利で迷っています"),
    (2, 15, "scheduled_past", 90, 0, None, ("経済学部", "40b", ["S09"]), [], "online", None,
     "独身で家を買った人の話を、もう少し聞いてみたい"),
    (2, 2, "done", 200, 1, (["住まい・住宅ローン", "家計の分け方"], 1), (None, "30a", ["S04", "S05"]), ["休日の午後"], "in_person",
     [ASK[0]], "家を買ったあとの、毎月の貯め方を知りたい"),
    (2, 30, "done", 260, 1, (["住まい・住宅ローン"], 0), ("商学部", "50", ["S05"]), [], "online", None,
     "定年までに返し終えるには、いつまでに買えばいいか気になった"),
    (2, None, "done", 300, 0, (["資産運用・NISA", "貯め方"], 1), ("神学部", "20b", ["S07"]), ["平日の夜"], "online",
     [ASK[0]], ""),
    (2, 2, "declined", 120, 1, None, (None, "30b", ["S06"]), ["平日の午後"], "online", [ASK[1]],
     "子どもが生まれる前に、住まいをどうするか"),
    (1, 1, "new", 5, 1, None, ("商学部", "40a", ["S01"]), ["休日の午前"], "online", [ASK[1]],
     "遅めの結婚なので、二人のお金の分け方を聞きたいです"),
    (1, 24, "replied", 40, 0, None, ("人間科学部", "20b", ["S02"]), [], "in_person", None,
     "結婚前に貯金の置き場所を決めるべきか気になりました"),
]
NAMES = ["ゆう", "あや", "まい", "けん", "さき", "りょう", "なつみ", "たく", "みお", "しん", "はるか", "そうた"]
# 考えの近さが分かるよう、12問の結果(L, C, M の段階)を人ごとに置く。森下さんは L- C- M+
LEVELS = [(-1, -1, 1), (0, -1, 1), (-1, 0, 0), (-1, -1, 0), (-1, -1, 1), (1, 0, -1),
          (-1, -1, 1), (0, -1, -1), (1, 1, 0), (0, 0, 1), (1, 1, 1), (0, 1, 0)]
INCOME = ["400", "none", "300", None, "500", "600", None, "700", "u300", None, "500", None]  # だれにも見せない


def q(s):
    return "NULL" if s in (None, "") else "'" + str(s).replace("\\", "\\\\").replace("'", "''") + "'"


def main() -> None:
    L = ["-- 行員側のデモデータ。scripts/make_demo_seed.py が書き出す(手で直さない)。customer_seed.sql のあとに流す。",
         "SET NAMES utf8mb4;",
         "-- 発表用の顔写真(yokane-front の public/images/speakers/demo_*.webp と同じもの)",
         "UPDATE speakers SET photo_url = CONCAT('/images/speakers/demo_', speaker_key, '.webp') "
         "WHERE speaker_key IN ('ST0004', 'ST0009', 'ST0016');",
         "-- 行員アカウント(デモ)。パスコードは .env の STAFF_DEMO_PASSCODE",
         "INSERT INTO staff_accounts (id, speaker_id, email, display_name, role) VALUES "
         "(1, 2, 'morishita@example.com', '森下 由美', 'staff'), (2, 1, 'takano@example.com', '高野 直人', 'staff'), "
         "(3, 3, 'aoyama@example.com', '青山 祐介', 'staff'), (4, NULL, 'admin@example.com', '運営', 'admin');"]
    for i, (sp, story, st, h, share, rec, (fac, age, sits), prefs, method, asks, preq) in enumerate(PLAN, 1):
        vid = "aaaaaaaa-0000-4000-8000-%012d" % i
        lv = LEVELS[i - 1]
        pat = "".join({1: "+", 0: "0", -1: "-"}[x] for x in lv)
        status = "scheduled" if st.startswith("scheduled") else st
        L.append(f"INSERT INTO users (id, google_sub, email) VALUES ({i}, 'demo-sub-{i}', 'demo{i}@example.com');")
        L.append(f"INSERT INTO visitors (id, user_id, cohort) VALUES ('{vid}', {i}, 'demo');")
        L.append(f"INSERT INTO customer_profiles (user_id, faculty, age_band, income_band) VALUES ({i}, {q(fac)}, {q(age)}, {q(INCOME[i - 1])});")
        for code in sits:
            L.append(f"INSERT INTO customer_situations (user_id, situation_code) VALUES ({i}, '{code}');")
        L.append(f"INSERT INTO diagnoses (id, visitor_id, status, pattern, completed_at) VALUES "
                 f"({i}, '{vid}', 'completed', '{pat}', DATE_SUB(NOW(), INTERVAL {h + 1} HOUR));")
        for a in range(3):
            L.append(f"INSERT INTO diagnosis_axis_scores (diagnosis_id, axis_id, score, level) VALUES ({i}, {a + 1}, {lv[a] * 3}, {lv[a]});")
        replied = "NULL" if st == "new" else f"DATE_SUB(NOW(), INTERVAL {max(h - 20, 1)} HOUR)"
        dec = "'日程が合わない'" if st == "declined" else "NULL"
        asks_sql = q(json.dumps(asks, ensure_ascii=False)) if asks else "NULL"
        L.append("INSERT INTO meeting_requests (id, visitor_id, user_id, speaker_id, story_id, diagnosis_id, preferences, "
                 "meeting_method, ask_topics, pre_question, requester_name, created_at, status, replied_at, decline_reason, "
                 f"share_result) VALUES ({i}, '{vid}', {i}, {sp}, {story if story else 'NULL'}, {i}, "
                 f"{q(json.dumps(prefs, ensure_ascii=False))}, '{method}', {asks_sql}, {q(preq)}, '{NAMES[i - 1]}', "
                 f"DATE_SUB(NOW(), INTERVAL {h} HOUR), '{status}', {replied}, {dec}, {share});")
        place = "'福岡銀行 本店'" if method == "in_person" else "NULL"
        chosen = "DATE_SUB(NOW(), INTERVAL 10 HOUR)"
        if st == "replied":
            for d in (2, 3, 5):
                L.append("INSERT INTO meeting_proposals (request_id, starts_at, ends_at, method, place) VALUES "
                         f"({i}, TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL {d} DAY), '19:00:00'), "
                         f"TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL {d} DAY), '19:30:00'), '{method}', {place});")
        elif st == "scheduled_today":
            L.append("INSERT INTO meeting_proposals (request_id, starts_at, ends_at, method, place, chosen_at) VALUES "
                     f"({i}, DATE_FORMAT(DATE_ADD(NOW(), INTERVAL 2 HOUR), '%Y-%m-%d %H:00:00'), "
                     f"DATE_FORMAT(DATE_ADD(NOW(), INTERVAL 2 HOUR), '%Y-%m-%d %H:30:00'), '{method}', {place}, {chosen});")
        elif st in ("scheduled_past", "done"):
            d = -2 if st == "scheduled_past" else -6
            L.append("INSERT INTO meeting_proposals (request_id, starts_at, ends_at, method, place, chosen_at) VALUES "
                     f"({i}, TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL {d} DAY), '19:00:00'), "
                     f"TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL {d} DAY), '19:30:00'), '{method}', {place}, {chosen});")
        if rec:
            L.append("INSERT INTO meeting_records (request_id, held, topics, next_promise, memo) VALUES "
                     f"({i}, 1, {q(json.dumps(rec[0], ensure_ascii=False))}, {rec[1]}, '次は家計の表を見ながら話す');")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{OUT.name}: {len(L)}行")


if __name__ == "__main__":
    main()
