# 行員用の画面（Streamlit 版・デモデータだけ）

Next.js 版（`frontend/`）と同じ7画面を、DB につながずに見せるための版です。発表や共有で、URL を開くだけで行員側を触ってもらうために使います。

- **データ**：`data/snapshot.json`（森下 由美さんのデモデータ。12件のうち森下さん宛ての10件）。お客さん側のアプリや DB にはつながっていません。
- **操作**：返事・見送り・記録・プロフィール・経験談の書き直し・12問・運営の公開は、ブラウザのタブを開いている間だけ残ります。再読み込みすると最初に戻ります。
- **時刻**：開いた時刻に合わせて、デモの日時をずらします（今日の予定・待っている時間がいつ開いても同じ見え方になる）。
- **ログイン**：「森下 由美（行員）として入る」か「運営として入る」を選ぶだけです。パスコードを掛けたいときは、Streamlit の Secrets に `DEMO_PASSCODE = "..."` を入れると、ログイン画面で求めるようになります。
- **Next.js 版との違い**：お客さま側の返事がないので、詳細画面に「お客さまが日にちを選んだことにする」というデモだけの操作があります。経験談の「今の年齢」のチェックは本番の API だけで行います（年齢をデモデータに入れないため）。金額（円・万円・年収）のチェックは同じです。CSV は森下さん宛ての分だけです。

## 手元で動かす

```bash
cd streamlit
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd .. && streamlit/.venv/bin/streamlit run streamlit/app.py     # http://localhost:8501
```

リポジトリの一番上から動かすと、`.streamlit/config.toml`（色）が効きます。

## Streamlit Community Cloud に出す

share.streamlit.io →「Create app」→ GitHub のリポジトリ `yokane_koin`、ブランチ `main`、Main file path は `streamlit/app.py`。Python は 3.12 以上。

## デモデータを作り直す

Excel やデモの作り方を変えたら、DB を作り直した直後にスナップショットを取り直します（デモの時刻は DB を作った時刻から作られるため）。

```bash
cd backend
.venv/bin/python -m scripts.apply_db
.venv/bin/python -m scripts.make_streamlit_snapshot     # → streamlit/data/snapshot.json
```

年収の幅と行員の年齢は API が返さないので、スナップショットにも入りません。
