-- yokane-back の db/schema.sql を写したもの(road-yasu/yokane-back main 54b9fb3, 2026-11-20)。
-- お客さん側のテーブルの持ち主は yokane-back。ここではローカルの開発・テストのためだけに使う。
-- 仕様設計書 v0.4 6.3 の CREATE TABLE をそのまま写したもの。
-- 6.3末尾の「新版」の記述にある diagnoses.expires_at / meeting_requests.expires_at と、v0.6 6.3 の追加・変更を反映している。
SET NAMES utf8mb4;

-- ===== 設定データ(差し替えるもの: MR-09 / N-11) =====
CREATE TABLE axes (
  id            TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
  code          VARCHAR(8)  NOT NULL,              -- 'L','C','M'(Excel 01_軸と判定の「軸ID」。画面に出さない)
  internal_name VARCHAR(50) NOT NULL,              -- チーム用の軸の中身(U-01)。画面に出さない
  display_order TINYINT UNSIGNED NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_axes_code (code),
  UNIQUE KEY uq_axes_order (display_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE app_settings (
  setting_key VARCHAR(50) NOT NULL,
  value       JSON        NOT NULL,
  updated_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (setting_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE result_texts (
  axis_id TINYINT UNSIGNED NOT NULL,
  level   TINYINT          NOT NULL,               -- -1=−側 / 0=真ん中 / 1=+側
  body    VARCHAR(300)     NOT NULL,
  PRIMARY KEY (axis_id, level),
  CONSTRAINT fk_result_texts_axis FOREIGN KEY (axis_id) REFERENCES axes (id),
  CONSTRAINT ck_result_texts_level CHECK (level IN (-1, 0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE tags (
  id            SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  tag_key       VARCHAR(10) NOT NULL,              -- Excel 03_タグ辞書の「タグID」
  kind          ENUM('specialty','private') NOT NULL, -- 金融の得意分野/プライベート(06には出さない。価値観タグは判定から作る。DP-53)
  name          VARCHAR(30) NOT NULL,
  display_order SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uq_tags_key (tag_key),
  UNIQUE KEY uq_tags_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ===== 話し手(ダミー) =====
CREATE TABLE speakers (
  id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
  speaker_key      VARCHAR(20)  NOT NULL,          -- Excelの「行員ID」(例 ST0001)
  name             VARCHAR(50)  NOT NULL,
  kind            ENUM('staff','graduate') NOT NULL DEFAULT 'staff', -- 13_卒業生30「種別」
  photo_url        VARCHAR(255) NULL,              -- 例 /images/speakers/ST0001.webp(顔写真。ファイルはフロントに置く。DP-36)
  one_liner        VARCHAR(100) NULL,              -- 05の一言(Excel「ひと言キャッチ」。D-18)
  area             VARCHAR(50)  NULL,              -- プロフィール(基本情報): 担当エリア(架空)
  job_title        VARCHAR(50)  NULL,              -- プロフィール(基本情報): 業務担当
  intro_text       TEXT         NULL,              -- プロフィール(基本情報): 自己紹介
  personality_text TEXT         NULL,              -- プロフィール(基本情報): 人柄・休日
  pattern          VARCHAR(8)   NULL,              -- 例 '+0-'。12問の答えから計算(D-34)
  is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
  created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  gender          VARCHAR(10)  NULL,   -- 「性別」
  age             TINYINT UNSIGNED NULL, -- 「年齢」。行員の年齢は画面に出さない(API で落とす)
  faculty         VARCHAR(30)  NULL,   -- 「学部」
  grad_year       SMALLINT UNSIGNED NULL, -- 「卒業年(目安)」
  occupation      VARCHAR(50)  NULL,   -- 「職業(一般のみ)」。画面には出さない(PoC)
  income_band     VARCHAR(20)  NULL,   -- 「年収帯(一般のみ・画面に出さない)」。どのAPIも返さない
  situation_label VARCHAR(30)  NULL,   -- 「状況の札」例 結婚して2年目
  PRIMARY KEY (id),
  UNIQUE KEY uq_speakers_key (speaker_key),
  KEY ix_speakers_pattern (is_active, pattern)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE questions (
  id           SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  question_no  TINYINT UNSIGNED  NOT NULL,         -- 出す順 1〜12
  axis_id      TINYINT UNSIGNED  NOT NULL,
  direction    TINYINT           NOT NULL,         -- +1 / -1(MR-02)
  episode_text VARCHAR(500)      NOT NULL,
  summary      VARCHAR(100)      NOT NULL,         -- 04で添える短い要約(F-09)。Excelの「見出し」
  source_type  ENUM('self','heard') NOT NULL,      -- 本人の体験/お客さまとの話(Excelの「種類」)
  source_label VARCHAR(100)      NOT NULL,         -- 誰の話か。例「山本 涼介さんの話」「山本 涼介さんが聞いた話」(DP-38)
  speaker_id   INT UNSIGNED      NULL,             -- 元の話し手(Excelの「発信行員ID」)
  image_url    VARCHAR(255)      NULL,             -- 03のカードの絵。NULLなら絵なしで出す(Q-17)
  PRIMARY KEY (id),
  UNIQUE KEY uq_questions_no (question_no),
  KEY ix_questions_axis (axis_id),
  CONSTRAINT fk_questions_axis    FOREIGN KEY (axis_id)    REFERENCES axes (id),
  CONSTRAINT fk_questions_speaker FOREIGN KEY (speaker_id) REFERENCES speakers (id),
  CONSTRAINT ck_questions_direction CHECK (direction IN (-1, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE speaker_tags (
  speaker_id INT UNSIGNED      NOT NULL,
  tag_id     SMALLINT UNSIGNED NOT NULL,
  PRIMARY KEY (speaker_id, tag_id),
  KEY ix_speaker_tags_tag (tag_id),
  CONSTRAINT fk_speaker_tags_speaker FOREIGN KEY (speaker_id) REFERENCES speakers (id) ON DELETE CASCADE,
  CONSTRAINT fk_speaker_tags_tag     FOREIGN KEY (tag_id)     REFERENCES tags (id)     ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE speaker_episodes (                    -- 私の話/聞いた話(Excel 05_エピソード600)
  id          INT UNSIGNED     NOT NULL AUTO_INCREMENT,
  episode_key VARCHAR(10)      NOT NULL,           -- Excelの「エピソードID」(例 EP0001)
  speaker_id  INT UNSIGNED     NOT NULL,
  source_type ENUM('self','heard') NOT NULL,       -- 本人の体験=私の話/お客さまとの話=聞いた話
  title       VARCHAR(50)      NOT NULL,           -- カード見出し
  body        TEXT             NOT NULL,           -- 本文
  axis_id     TINYINT UNSIGNED NULL,               -- 内部用(画面に出さない)。ランダム12本に変わったとき用(15.3)
  direction   TINYINT          NULL,               -- 内部用 +1/-1
  PRIMARY KEY (id),
  UNIQUE KEY uq_speaker_episodes_key (episode_key),
  KEY ix_speaker_episodes_speaker (speaker_id, source_type),
  CONSTRAINT fk_speaker_episodes_speaker FOREIGN KEY (speaker_id) REFERENCES speakers (id) ON DELETE CASCADE,
  CONSTRAINT fk_speaker_episodes_axis    FOREIGN KEY (axis_id)    REFERENCES axes (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE speaker_answers (
  speaker_id  INT UNSIGNED      NOT NULL,
  question_id SMALLINT UNSIGNED NOT NULL,
  answer      TINYINT           NOT NULL,          -- 1=わかる / -1=ちがうかも / 0=パス
  PRIMARY KEY (speaker_id, question_id),
  CONSTRAINT fk_speaker_answers_speaker  FOREIGN KEY (speaker_id)  REFERENCES speakers (id)  ON DELETE CASCADE,
  CONSTRAINT fk_speaker_answers_question FOREIGN KEY (question_id) REFERENCES questions (id),
  CONSTRAINT ck_speaker_answers_answer CHECK (answer IN (-1, 0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE speaker_axis_scores (
  speaker_id INT UNSIGNED     NOT NULL,
  axis_id    TINYINT UNSIGNED NOT NULL,
  score      TINYINT          NOT NULL,            -- -4〜+4
  level      TINYINT          NOT NULL,            -- -1 / 0 / 1
  PRIMARY KEY (speaker_id, axis_id),
  CONSTRAINT fk_sas_speaker FOREIGN KEY (speaker_id) REFERENCES speakers (id) ON DELETE CASCADE,
  CONSTRAINT fk_sas_axis    FOREIGN KEY (axis_id)    REFERENCES axes (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ===== お客さん(訪問者・利用者) =====
CREATE TABLE users (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  google_sub    VARCHAR(255) NOT NULL,             -- Googleの識別番号(P-33)
  email         VARCHAR(254) NULL,                 -- Googleのメールアドレス(P-33)。名前は残さない
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_login_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_sub (google_sub)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE visitors (
  id           CHAR(36)     NOT NULL,              -- UUID(ブラウザのCookieに持たせる)
  user_id      INT UNSIGNED NULL,                  -- ログインしたら結びつける
  cohort       VARCHAR(20)  NOT NULL DEFAULT 'unknown', -- 試した人の区分(M-11)
  created_at   DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  last_seen_at DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  linked_at    DATETIME(3)  NULL,
  PRIMARY KEY (id),
  KEY ix_visitors_user (user_id),
  CONSTRAINT fk_visitors_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE diagnoses (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, -- 12問を1回通すごとに1行
  visitor_id   CHAR(36)        NOT NULL,
  status       ENUM('in_progress','completed','discarded') NOT NULL DEFAULT 'in_progress',
  pattern      VARCHAR(8)      NULL,
  started_at   DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  completed_at DATETIME(3)     NULL,
  expires_at   DATETIME(3)     NULL,             -- 未ログインの診断だけ期限を入れる(8.1。DP-49)
  PRIMARY KEY (id),
  KEY ix_diagnoses_visitor (visitor_id, status, completed_at),
  CONSTRAINT fk_diagnoses_visitor FOREIGN KEY (visitor_id) REFERENCES visitors (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE answers (
  diagnosis_id BIGINT UNSIGNED   NOT NULL,
  question_id  SMALLINT UNSIGNED NOT NULL,
  answer       TINYINT           NOT NULL,         -- 1=わかる / -1=ちがうかも / 0=パス
  answered_at  DATETIME(3)       NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (diagnosis_id, question_id),
  CONSTRAINT fk_answers_diagnosis FOREIGN KEY (diagnosis_id) REFERENCES diagnoses (id) ON DELETE CASCADE,
  CONSTRAINT fk_answers_question  FOREIGN KEY (question_id)  REFERENCES questions (id),
  CONSTRAINT ck_answers_answer CHECK (answer IN (-1, 0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE diagnosis_axis_scores (
  diagnosis_id BIGINT UNSIGNED  NOT NULL,
  axis_id      TINYINT UNSIGNED NOT NULL,
  score        TINYINT          NOT NULL,
  level        TINYINT          NOT NULL,
  PRIMARY KEY (diagnosis_id, axis_id),
  CONSTRAINT fk_das_diagnosis FOREIGN KEY (diagnosis_id) REFERENCES diagnoses (id) ON DELETE CASCADE,
  CONSTRAINT fk_das_axis      FOREIGN KEY (axis_id)      REFERENCES axes (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE likes (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  visitor_id  CHAR(36)        NOT NULL,
  episode_id  INT UNSIGNED    NOT NULL,            -- 06で「わかる」を押した話
  created_at  DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_likes (visitor_id, episode_id),
  CONSTRAINT fk_likes_visitor FOREIGN KEY (visitor_id) REFERENCES visitors (id)         ON DELETE CASCADE,
  CONSTRAINT fk_likes_episode FOREIGN KEY (episode_id) REFERENCES speaker_episodes (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE experiences (                        -- 14_状況と一段先「話し手の経験」
  code          VARCHAR(4)  NOT NULL,             -- E01〜E08
  name          VARCHAR(50) NOT NULL,
  display_order TINYINT UNSIGNED NOT NULL,
  PRIMARY KEY (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE situations (                         -- 14_状況と一段先「A2の状況」
  code          VARCHAR(4)  NOT NULL,             -- S01〜S09
  label         VARCHAR(30) NOT NULL,
  display_order TINYINT UNSIGNED NOT NULL,
  is_active     BOOLEAN     NOT NULL DEFAULT TRUE, -- Excel から消えたコードは FALSE(行は消さない)
  PRIMARY KEY (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE situation_next_steps (               -- 状況 → 一段先に当たる経験(「(なし)」は行を作らない)
  situation_code  VARCHAR(4) NOT NULL,
  experience_code VARCHAR(4) NOT NULL,
  PRIMARY KEY (situation_code, experience_code),
  CONSTRAINT fk_sns_situation  FOREIGN KEY (situation_code)  REFERENCES situations (code)  ON DELETE CASCADE,
  CONSTRAINT fk_sns_experience FOREIGN KEY (experience_code) REFERENCES experiences (code) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE speaker_experiences (                -- 13「経験した出来事」「いちばん語れる出来事」
  speaker_id      INT UNSIGNED NOT NULL,
  experience_code VARCHAR(4)   NOT NULL,
  is_main         BOOLEAN      NOT NULL DEFAULT FALSE,
  PRIMARY KEY (speaker_id, experience_code),
  CONSTRAINT fk_sx_speaker    FOREIGN KEY (speaker_id)      REFERENCES speakers (id)    ON DELETE CASCADE,
  CONSTRAINT fk_sx_experience FOREIGN KEY (experience_code) REFERENCES experiences (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE stories (                            -- 経験談(PoCは1人1本)
  id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
  speaker_id       INT UNSIGNED NOT NULL,
  headline         VARCHAR(100) NOT NULL,         -- 「カードの一言」
  good_text        TEXT         NOT NULL,         -- 「やって良かったこと」
  regret_text      TEXT         NOT NULL,         -- 「後悔していること」
  trigger_title    VARCHAR(50)  NOT NULL,         -- 「きっかけ_見出し」
  trigger_body     TEXT         NOT NULL,
  hesitation_title VARCHAR(50)  NOT NULL,         -- 「迷ったこと_見出し」
  hesitation_body  TEXT         NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_stories_speaker (speaker_id),     -- 1人1本(将来複数にするならこの一意キーを外す)
  CONSTRAINT fk_stories_speaker FOREIGN KEY (speaker_id) REFERENCES speakers (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE story_qas (
  story_id INT UNSIGNED     NOT NULL,
  qa_no    TINYINT UNSIGNED NOT NULL,             -- 1〜4
  question VARCHAR(200)     NOT NULL,
  answer   TEXT             NOT NULL,
  PRIMARY KEY (story_id, qa_no),
  CONSTRAINT fk_story_qas_story FOREIGN KEY (story_id) REFERENCES stories (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE customer_profiles (                  -- A1(利用者に1行。上書き)
  user_id     INT UNSIGNED NOT NULL,
  faculty     VARCHAR(30)  NULL,
  age_band    VARCHAR(8)   NULL,                  -- age_band_options の code
  income_band VARCHAR(8)   NULL,                  -- income_band_options の code。だれにも見せない
  updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id),
  CONSTRAINT fk_cp_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE customer_situations (                -- A2(0行〜有効な状況の数。上書き = 消して入れ直す)
  user_id        INT UNSIGNED NOT NULL,
  situation_code VARCHAR(4)   NOT NULL,
  PRIMARY KEY (user_id, situation_code),
  CONSTRAINT fk_cs_user      FOREIGN KEY (user_id)        REFERENCES users (id)       ON DELETE CASCADE,
  CONSTRAINT fk_cs_situation FOREIGN KEY (situation_code) REFERENCES situations (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE story_likes (                        -- A5 の「わかる」
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  visitor_id CHAR(36)        NOT NULL,
  story_id   INT UNSIGNED    NOT NULL,
  created_at DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_story_likes (visitor_id, story_id),
  CONSTRAINT fk_sl_visitor FOREIGN KEY (visitor_id) REFERENCES visitors (id) ON DELETE CASCADE,
  CONSTRAINT fk_sl_story   FOREIGN KEY (story_id)   REFERENCES stories (id)  ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE meeting_requests (
  id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  visitor_id     CHAR(36)        NOT NULL,
  user_id        INT UNSIGNED    NULL,             -- 送ったときログインしていれば入る(DP-31)
  speaker_id     INT UNSIGNED    NOT NULL,
  story_id       INT UNSIGNED NULL,               -- どの経験談から来たか(A6-1/A6-2)
  diagnosis_id   BIGINT UNSIGNED NULL,             -- 送ったときの結果
  preferences    JSON            NOT NULL,         -- ざっくりした希望の文の配列(1つ以上。P-29)
  meeting_method ENUM('in_person','online') NOT NULL, -- 会い方(P-27。呼び方はQ-11)
  ask_topics     JSON            NULL,             -- 07でチェックした文の配列(固定3つから。P-30)
  pre_question   VARCHAR(200)    NULL,             -- 08の自由入力(200文字まで)
  requester_name VARCHAR(50)     NULL,             -- 申し込んだ人の名前。新規はA11で必須(DP-54)。既存レコード用にNULL可
  client_request_id CHAR(36)     NULL,             -- 画面が作る重複防止のUUID(A11。DP-50)
  contact_email  VARCHAR(254)    NULL,             -- 既存レコード用。新規保存しない
  contact_phone  VARCHAR(15)     NULL,             -- 既存レコード用。新規保存しない
  created_at     DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  expires_at     DATETIME(3)     NULL,             -- 既存の未ログイン申し込みの期限(8.1)
  PRIMARY KEY (id),
  KEY ix_meeting_requests_visitor (visitor_id),
  KEY ix_meeting_requests_user (user_id),
  UNIQUE KEY uq_mr_client_request (user_id, client_request_id),  -- NULLは何件あってもよい
  CONSTRAINT fk_mr_visitor   FOREIGN KEY (visitor_id)   REFERENCES visitors (id)  ON DELETE CASCADE,
  CONSTRAINT fk_mr_user      FOREIGN KEY (user_id)      REFERENCES users (id)     ON DELETE CASCADE,
  CONSTRAINT fk_mr_speaker   FOREIGN KEY (speaker_id)   REFERENCES speakers (id),
  CONSTRAINT fk_mr_diagnosis FOREIGN KEY (diagnosis_id) REFERENCES diagnoses (id) ON DELETE SET NULL,
  CONSTRAINT fk_mr_story FOREIGN KEY (story_id) REFERENCES stories (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ===== 計測 =====
CREATE TABLE events (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  visitor_id  CHAR(36)        NOT NULL,
  occurred_at DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3), -- サーバーが受けた時刻
  screen      VARCHAR(8)      NOT NULL,            -- 画面ID '01','03','08','15' など
  action      VARCHAR(40)     NOT NULL,            -- 'page_view','swipe_answer' など(10章)
  props       JSON            NULL,
  PRIMARY KEY (id),
  KEY ix_events_visitor_time (visitor_id, occurred_at),
  KEY ix_events_action_time (action, occurred_at),
  CONSTRAINT fk_events_visitor FOREIGN KEY (visitor_id) REFERENCES visitors (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
