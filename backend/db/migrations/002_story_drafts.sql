-- 行員が書き直した経験談(stories)の下書き。運営が確かめるまでお客さんには出さない(S-04 を経験談にも当てはめる)。
-- お客さん側(yokane-back)は stories と story_qas をそのまま読むので、そちらの表には列を足さず、
-- 確認が済んだら運営の「公開」で stories・story_qas に写す。1人1本(stories と同じ)なので話し手ごとに1行。
SET NAMES utf8mb4;

CREATE TABLE story_drafts (
  speaker_id       INT UNSIGNED NOT NULL,
  headline         VARCHAR(100) NOT NULL,         -- カードの一言
  good_text        TEXT         NOT NULL,         -- やって良かったこと
  regret_text      TEXT         NOT NULL,         -- 後悔していること
  trigger_title    VARCHAR(50)  NOT NULL,         -- きっかけ(見出し・本文)
  trigger_body     TEXT         NOT NULL,
  hesitation_title VARCHAR(50)  NOT NULL,         -- 迷ったこと(見出し・本文)
  hesitation_body  TEXT         NOT NULL,
  qas              JSON         NOT NULL,         -- [{"question": "...", "answer": "..."}] 4問
  situation_label  VARCHAR(30)  NULL,             -- 状況の札(例 家を買って3年)
  submitted_at     DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (speaker_id),
  CONSTRAINT fk_story_drafts_speaker FOREIGN KEY (speaker_id) REFERENCES speakers (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
