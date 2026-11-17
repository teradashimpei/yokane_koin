-- 行員側(話し手側)のために足すテーブルと列。要件定義書「よかね 話し手側(行員)管理画面」6章。
-- yokane-back の schema.sql を流したあとに流す。既存の列と応答は変えない。
SET NAMES utf8mb4;

-- 行員のアカウント(S-01)。デモは メール + 共通のデモ用パスコード でログインする
CREATE TABLE staff_accounts (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  speaker_id    INT UNSIGNED NULL,                 -- role='staff' なら必須(どの話し手か)
  email         VARCHAR(254) NOT NULL,
  display_name  VARCHAR(50)  NOT NULL,
  role          ENUM('staff','admin') NOT NULL DEFAULT 'staff',
  is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_login_at DATETIME     NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_staff_email (email),
  UNIQUE KEY uq_staff_speaker (speaker_id),
  CONSTRAINT fk_staff_speaker FOREIGN KEY (speaker_id) REFERENCES speakers (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- 受付の一時停止(S-07)と、見せない項目(S-05)
ALTER TABLE speakers
  ADD COLUMN accepting     BOOLEAN NOT NULL DEFAULT TRUE AFTER is_active,
  ADD COLUMN hidden_fields JSON    NULL                  AFTER accepting;

-- 行員が書いた体験談は運営の確認(published)まで下書き(S-04)。既存の行は公開済みとして扱う
ALTER TABLE speaker_episodes
  ADD COLUMN status      ENUM('draft','published') NOT NULL DEFAULT 'published' AFTER direction,
  ADD COLUMN reviewed_by INT UNSIGNED NULL AFTER status,
  ADD COLUMN reviewed_at DATETIME     NULL AFTER reviewed_by,
  ADD COLUMN updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER reviewed_at;

-- 申し込みの状態と返事(S-10〜S-14)
ALTER TABLE meeting_requests
  ADD COLUMN status         ENUM('new','replied','scheduled','done','declined') NOT NULL DEFAULT 'new' AFTER expires_at,
  ADD COLUMN replied_at     DATETIME(3)  NULL AFTER status,
  ADD COLUMN decline_reason VARCHAR(30)  NULL AFTER replied_at,
  ADD COLUMN share_result   BOOLEAN      NOT NULL DEFAULT FALSE AFTER decline_reason,
  ADD KEY ix_mr_speaker_status (speaker_id, status, created_at);

-- 行員からの日にちの提案(S-12。お客さんが1つ選ぶ。F2)
CREATE TABLE meeting_proposals (
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  request_id BIGINT UNSIGNED NOT NULL,
  starts_at  DATETIME        NOT NULL,
  ends_at    DATETIME        NOT NULL,
  method     ENUM('in_person','online') NOT NULL,
  place      VARCHAR(100)    NULL,
  chosen_at  DATETIME(3)     NULL,
  created_at DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY ix_proposals_request (request_id),
  CONSTRAINT fk_proposals_request FOREIGN KEY (request_id) REFERENCES meeting_requests (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- 話したあとの記録(S-16)。memo は担当の行員だけが読む
CREATE TABLE meeting_records (
  request_id   BIGINT UNSIGNED NOT NULL,
  held         BOOLEAN         NOT NULL,
  topics       JSON            NULL,
  next_promise BOOLEAN         NOT NULL DEFAULT FALSE,
  memo         VARCHAR(1000)   NULL,
  recorded_at  DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (request_id),
  CONSTRAINT fk_records_request FOREIGN KEY (request_id) REFERENCES meeting_requests (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- 行員の操作の記録(9章)。お客さんの events とは分ける(visitor_id が要らないため)
CREATE TABLE staff_events (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  staff_id    INT UNSIGNED    NOT NULL,
  request_id  BIGINT UNSIGNED NULL,
  action      VARCHAR(40)     NOT NULL,            -- login / reply / decline / record / profile_save / answers_save
  occurred_at DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY ix_staff_events (staff_id, occurred_at),
  CONSTRAINT fk_staff_events_staff FOREIGN KEY (staff_id) REFERENCES staff_accounts (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- 話したテーマ・見送りの理由の選択肢(要件10章 #9。仮)
INSERT INTO app_settings (setting_key, value) VALUES
  ('staff_record_topics', '["貯め方", "家計の分け方", "資産運用・NISA", "住まい・住宅ローン", "保険", "結婚・2人のお金", "子育て・教育", "その他"]'),
  ('staff_decline_reasons', '["日程が合わない", "得意分野と合わない", "受けられる件数を超えた", "その他"]'),
  ('staff_reply_target_days', '2'),
  ('staff_insights_min_people', '5')
ON DUPLICATE KEY UPDATE value = VALUES(value);
