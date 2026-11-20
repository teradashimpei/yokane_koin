# yokane_koin（よかね 行員用）

「よかね（仮）」の行員用の画面とAPIです（お客さま用アプリでの呼び名は「話せる人」）。展示用の**動くデモ**として作りました。
要件は Claude Docs「よかね 話し手側（行員）管理画面 要件定義書」、画面は Figma「行員マッチング 画面遷移図」の ⑤（B1・B2）と ⑦（P1〜P6）に合わせています。

| 画面 | URL | できること |
| --- | --- | --- |
| P1 ログイン | `/staff/login` | 登録済みのメール＋デモ用パスコード |
| P2 ホーム（今日やること） | `/staff` | 返事を待っているお客さま（待っている時間が長い順・目安の2日を過ぎたら赤）、今日の予定と準備、記録がまだの面談、今月の数字 |
| P2-2 届いた希望（一覧） | `/staff/requests` | 全件。いまの状況・どこから来たか（あなたの経験談／卒業生の経験談）つき。状態のタブ、名前・聞きたいこと・状況で探す、並び替え |
| P3 詳細と返事 | `/staff/requests/{id}` | お客さまのいまの状況・年代・学部、どの経験談を読んで来たか（本文も読める）、気になったこと。「話せます」で日にちを3つまで提案／「今回は見送る」。返事はボタンだけ |
| P4 予定と記録 | `/staff/schedule` | 決まった予定、話したテーマ・次の約束・自分用メモ |
| P5 プロフィールと経験談 | `/staff/profile` | 経験談（カードの一言・やって良かったこと・後悔していること・きっかけ・迷ったこと・Q&A 4問・状況の札）を書き直して運営に送る。金額と今の年齢は送る時点で止める。基本情報・タグ・見せる／見せない・受付の一時停止。お客さまの A5 と同じ見え方のプレビューつき |
| B2 12問 | `/staff/answers` | お客さんと同じ12問。答えると3軸の点とタグを計算し直す |
| P6 お客さまの傾向 | `/staff/insights` | 自分宛ての集計（いまの状況・どこから来たか・年代・考え・聞きたいこと）。5人そろうまで出さない。年収は数えない |
| 運営 | `/staff/admin` | 経験談の書き直しを公開中の文と並べて確認し、公開（お客さまの A4・A5 にすぐ出る）。CSV書き出し（名前・連絡先・メモ・年収なし） |

## 構成

```
backend/   FastAPI（yokane-back と同じ版・同じ書き方）
  app/routers/  staff_*（行員）・customer_replies（お客さん側に足すAPI）・admin
  db/base_schema.sql      yokane-back の schema.sql の写し（お客さん側のテーブル。2026-11-20 の main 54b9fb3）
  db/migrations/001_staff.sql        行員側で足すテーブルと列
  db/migrations/002_story_drafts.sql 経験談の書き直し（運営の確認待ち）
  db/customer_seed.sql    お客さん側のデモデータ（yokane-back の import_seed で v4_demo_v2.xlsx を取り込んだ結果の書き出し）
  db/demo_seed.sql        行員側のデモデータ（scripts/make_demo_seed.py。発表の行員3人＋架空のお客さん12件）
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

お客さま側（yokane-front）の発表デモの行員3人（高野直人・森下由美・青山祐介）と同じ人・同じ顔写真・同じ経験談です。

1. `morishita@example.com`（森下 由美）と `.env` のパスコードでログイン
2. ホームで「返事を待っているお客さま」3件を見る。札でいまの状況、下の1行でどこから来たか（「あなたの経験談を読んで」／「卒業生（50代女性・家を買って3年）の経験談から」）が分かる
3. あや様の「返事する」から詳細を開き、「お客さまが読んだ経験談を見る」で卒業生の話を読んでから「話せます」で日にちを送る
4. お客さん側で日にちを選ぶ（yokane-front は未対応なので、いまは下のAPIを直接呼ぶ）
5. 予定でその回を選び、話したテーマと次の約束を記録する → 「お客さまの傾向」の数字が変わる
6. プロフィールで経験談を書き直して送る（「500万円」などを入れると止まる）→ `admin@example.com` の運営で公開 → お客さまの A5 に出る

ほかのアカウント: `takano@example.com`（高野 直人。希望2件だけ。傾向は「5人そろうと表示」になる）、`aoyama@example.com`（青山 祐介）、`admin@example.com`（運営）。

## Streamlit 版（デモデータだけ）

DB につながずに URL だけで行員側を見せる版を `streamlit/` に置いています。7画面と文言は Next.js 版と同じです。動かし方と公開のしかたは [streamlit/README.md](streamlit/README.md)。

## デモデータの作り直し

- お客さん側（`db/customer_seed.sql`）: yokane-back の Excel が変わったら、yokane-back で `import_seed` を空のDB（例 `yokane_seedtmp`）に流し、`scripts/dump_customer_seed.py` で書き出す（手順はファイルの先頭）。あわせて `db/base_schema.sql` を yokane-back の `db/schema.sql` に合わせる
- 行員側（`db/demo_seed.sql`）: `.venv/bin/python -m scripts.make_demo_seed`

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
- お客さんの年収の幅は、行員にも運営のCSVにも出さない（要件v0.7 8.1）。一般の卒業生は名前・写真を出さず「50代女性」のように表す（yokane-front と同じ）
- 行員の経験談は1人1本（stories）。書き直しは `story_drafts` に入り、運営の公開で stories・story_qas に写す。金額（円・万円・年収）と今の年齢は yokane-back の取り込みと同じ決まりで止める（RK-16）
- 集計は5人以上から。名前・連絡先・メモは集計にもCSVにも入れない

## 残っていること

- [ ] yokane-front：08に「考えを見せてよい」の同意を足し、13で返事と日にちの選択を出す
- [ ] yokane-back：06・05で `speaker_episodes.status = 'published'` と `speakers.accepting` を見る
- [ ] 本番のログイン（Auth.js など）と、行員の許可一覧の運用
- [ ] Azure へのデプロイ（App Service を1つ足すか、yokane-back に取り込むか）
- [ ] 見送りの理由・話したテーマの選択肢をチームで決める（いまは仮。`app_settings`）
