# yokane_koin（よかね 行員側・話し手用）

「よかね（仮）」の行員側（アプリ上の呼び名は「話し手」）の画面とAPIです。展示用の**動くデモ**として作りました。
要件は Claude Docs「よかね 話し手側（行員）管理画面 要件定義書」、画面は Figma「行員マッチング 画面遷移図」の ⑤（B1・B2）と ⑦（P1〜P6）に合わせています。

| 画面 | URL | できること |
| --- | --- | --- |
| P1 ログイン | `/staff/login` | 登録済みのメール＋デモ用パスコード |
| P2 ホーム（届いた希望） | `/staff`・`/staff/requests` | 件数のまとめ、状態での絞り込み、返事の目安（2日）を過ぎた新着の表示 |
| P3 詳細と返事 | `/staff/requests/{id}` | 「話せます」で日にちを3つまで提案／「今回は見送る」で理由を選ぶ。返事はボタンだけ |
| P4 予定と記録 | `/staff/schedule` | 決まった予定、話したテーマ・次の約束・自分用メモ |
| P5 プロフィール | `/staff/profile` | 基本情報・タグ・見せる／見せない・受付の一時停止・体験談3本。お客さんからの見え方つき |
| B2 12問 | `/staff/answers` | お客さんと同じ12問。答えると3軸の点とタグを計算し直す |
| P6 お客さんの傾向 | `/staff/insights` | 自分宛ての集計。5人そろうまで出さない |
| 運営 | `/staff/admin` | 体験談の公開確認、CSV書き出し（名前・連絡先・メモなし） |

## 構成

```
backend/   FastAPI（yokane-back と同じ版・同じ書き方）
  app/routers/  staff_*（行員）・customer_replies（お客さん側に足すAPI）・admin
  db/base_schema.sql      yokane-back の schema.sql の写し（お客さん側のテーブル）
  db/migrations/001_staff.sql  行員側で足すテーブルと列
  db/demo_seed.sql        デモデータ（excel/yokane_poc_30staff_90episodes_v3.xlsm から作った架空の行員3人＋架空のお客さん12件）
frontend/  Next.js（BFF。内部キーと行員IDはサーバー側だけで持つ）
```

お客さん側（yokane-front / yokane-back）と**同じDB**を使う前提です。本番では `db/migrations/*.sql` だけを流します。

## 動かし方（ローカル）

必要なもの: Python 3.11 以上、Node 20 以上、MySQL（yokane-back の docker compose でも、ローカルのMySQLでもよい）

```bash
cd backend
cp .env.example .env        # DB_*、INTERNAL_API_KEY（長いランダム値）、STAFF_DEMO_PASSCODE を入れる
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m scripts.apply_db      # DBを作り直してデモデータを入れる（中身は消える）
.venv/bin/uvicorn app.main:app --port 8100
```

```bash
cd frontend
cp .env.example .env.local  # INTERNAL_API_KEY は backend と同じ値。SESSION_SECRET は長いランダム値
npm install
npm run dev                 # http://localhost:3100
```

テスト（`DB_NAME` の DB を毎回作り直す。既定は `yokane_koin_test`）:

```bash
cd backend && DB_HOST=127.0.0.1 DB_USER=root .venv/bin/pytest -q
```

## デモの流れ

1. `ota@example.com`（太田 悠人）と `.env` のパスコードでログイン
2. ホームで新着3件を見る（1件は返事の目安を過ぎて赤く出る）
3. ゆうさんの希望を開き、「考えの近さ」を見て「話せます」で日にちを送る
4. お客さん側で日にちを選ぶ（yokane-front は未対応なので、いまは下のAPIを直接呼ぶ）
5. 予定でその回を選び、話したテーマと次の約束を記録する → 「お客さんの傾向」の数字が変わる

ほかのアカウント: `nakamura@example.com`（希望2件だけ。傾向は「5人そろうと表示」になる）、`admin@example.com`（運営）。

## お客さん側に足すAPI（yokane-front から呼ぶ）

| メソッド | パス | 中身 |
| --- | --- | --- |
| GET | `/v1/meeting-requests/{id}/reply` | 状態・メッセージ・提案された日にち（見送りの理由は返さない） |
| POST | `/v1/meeting-requests/{id}/choose` | `{"proposal_id": n}` で1つ選ぶ → 予定に入る |

どちらも `X-Internal-Key` と `X-User-Id`（申し込んだ本人）が要ります。13（会う日）の画面で使う想定です。

## このデモで決めたこと

- 作るのは展示用の動くデモ。チームの決定50（行員側は絵だけ）とは違うが、試しに作る（11/17 てらさん）
- ログインはデモ用（登録済みメール＋共通パスコード）。本番は Google か福銀の職場アカウントに置き換える
- 返事はボタンだけ。メールや電話での連絡はしない
- お客さんの考え（結果の文）は、申し込みに `share_result`（見せてよい）が付いたものだけ行員に出す
- 集計は5人以上から。名前・連絡先・メモは集計にもCSVにも入れない

## 残っていること

- [ ] yokane-front：08に「考えを見せてよい」の同意を足し、13で返事と日にちの選択を出す
- [ ] yokane-back：06・05で `speaker_episodes.status = 'published'` と `speakers.accepting` を見る
- [ ] 本番のログイン（Auth.js など）と、行員の許可一覧の運用
- [ ] Azure へのデプロイ（App Service を1つ足すか、yokane-back に取り込むか）
- [ ] 見送りの理由・話したテーマの選択肢をチームで決める（いまは仮。`app_settings`）
