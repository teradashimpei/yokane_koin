"""お客さん側のデモデータ(db/customer_seed.sql)を書き出す。

yokane-back の venv で、yokane-back の scripts.import_seed を流したDB(DB_NAME)を読んで INSERT 文にする:

    cd ../yokane-back && DB_NAME=yokane_seedtmp .venv/bin/python -m scripts.import_seed --terra seed/yokane_poc_30staff_90episodes_v4_demo_v2.xlsx
    DB_NAME=yokane_seedtmp ../yokane-back/.venv/bin/python scripts/dump_customer_seed.py db/customer_seed.sql <yokane-back のコミット>
"""
import datetime, decimal, os, sys
from sqlalchemy import create_engine, text
TABLES = ["axes", "app_settings", "result_texts", "tags", "speakers", "questions", "speaker_tags", "speaker_episodes",
          "speaker_answers", "speaker_axis_scores", "experiences", "situations", "situation_next_steps",
          "speaker_experiences", "stories", "story_qas"]
def lit(v):
    if v is None: return "NULL"
    if isinstance(v, bool): return "1" if v else "0"
    if isinstance(v, (int, float, decimal.Decimal)): return str(v)
    if isinstance(v, (datetime.datetime, datetime.date)): return "'" + str(v) + "'"
    s = str(v).replace("\\", "\\\\").replace("'", "''").replace("\r", "\\r").replace("\n", "\\n")
    return "'" + s + "'"
eng = create_engine(f"mysql+pymysql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ.get('DB_NAME', 'yokane_seedtmp')}?charset=utf8mb4")
out = [f"-- お客さん側のデモデータ。yokane-back {sys.argv[2]} の scripts/import_seed.py で",
       "-- seed/yokane_poc_30staff_90episodes_v4_demo_v2.xlsx と seed/yokane_settings.xlsx を取り込んだDBから書き出したもの。",
       "-- 中身の持ち主は yokane-back。ここではローカルの開発・テストのためだけに使う(作り直し: README「デモデータの作り直し」)。",
       "SET NAMES utf8mb4;"]
with eng.connect() as c:
    for t in TABLES:
        cols = [r[0] for r in c.execute(text(f"SHOW COLUMNS FROM `{t}`"))]
        rows = c.execute(text(f"SELECT * FROM `{t}`")).all()
        if not rows: continue
        out.append(f"-- {t}: {len(rows)}行")
        for i in range(0, len(rows), 40):
            vals = ",\n".join("(" + ",".join(lit(v) for v in r) + ")" for r in rows[i:i + 40])
            out.append(f"INSERT INTO `{t}` ({','.join('`'+x+'`' for x in cols)}) VALUES\n{vals};")
open(sys.argv[1], "w", encoding="utf-8").write("\n".join(out) + "\n")
print("written", len(out))
