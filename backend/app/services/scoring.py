# yokane-back の app/services/scoring.py を写したもの(main 20ef673)。採点を変えるときは両方そろえる。
"""採点とマッチング(MR-01〜MR-08)。お客さんと話し手で同じ関数を使う。
DBやWebに依存しない純粋な関数だけを置く(単体テストしやすくするため)。"""
from dataclasses import dataclass

AGREE, DISAGREE, PASS = 1, -1, 0          # わかる / ちがうかも / パス(MR-03)
LEVEL_CHAR = {-1: "-", 0: "0", 1: "+"}


@dataclass(frozen=True)
class Question:
    id: int
    axis_code: str
    direction: int        # +1 / -1


@dataclass(frozen=True)
class Thresholds:
    minus_max: int        # この値以下なら −側(仮 -2)
    plus_min: int         # この値以上なら +側(仮 +2)


@dataclass(frozen=True)
class Evaluation:
    scores: dict          # {"L": 3, "C": -1, "M": -3}
    levels: dict          # {"L": 1, "C": 0, "M": -1}
    pattern: str          # "+0-"(軸の表示順に並べる)


@dataclass(frozen=True)
class Candidate:
    speaker_id: int
    evaluation: Evaluation


def to_level(score: int, th: Thresholds) -> int:
    if score <= th.minus_max:
        return -1
    if score >= th.plus_min:
        return 1
    return 0


def evaluate(answers: dict, questions: list, axis_order: list, th: Thresholds) -> Evaluation:
    """answers: {question_id: 1/-1/0}。12問そろっていることは呼び出し側で確認する。"""
    scores = {code: 0 for code in axis_order}
    for q in questions:
        scores[q.axis_code] += answers.get(q.id, PASS) * q.direction   # P-01
    return from_scores(scores, axis_order, th)


def from_scores(scores: dict, axis_order: list, th: Thresholds) -> Evaluation:
    """保存済みの軸ごとの点(speaker_axis_scores など)から作り直すときにも使う。"""
    levels = {code: to_level(scores[code], th) for code in axis_order}
    pattern = "".join(LEVEL_CHAR[levels[code]] for code in axis_order)
    return Evaluation(scores, levels, pattern)


def distance(a: Evaluation, b: Evaluation, weights: dict) -> int:
    """MR-08: 軸ごとの点の差の大きさ×重み の合計。"""
    return sum(weights.get(code, 1) * abs(a.scores[code] - b.scores[code]) for code in a.scores)


def match_count(a: Evaluation, b: Evaluation) -> int:
    """MR-07: 段階が合っている軸の数(0〜3)。どうずれたかは見ない、重みも付けない。"""
    return sum(1 for code in a.levels if a.levels[code] == b.levels[code])


def match(customer: Evaluation, candidates: list, weights: dict, limit: int):
    """MR-08: 一致数の多い順 → 重みつきの点の差の合計が小さい順 → 話し手ID順。上位limit人を返す。
    戻り値: [(speaker_id, match_count, distance), ...]"""
    rows = [(c.speaker_id, match_count(customer, c.evaluation), distance(customer, c.evaluation, weights))
            for c in candidates]
    rows.sort(key=lambda r: (-r[1], r[2], r[0]))
    return rows[:limit]


def value_tags(ev: Evaluation, axis_order: list, labels: dict) -> list:
    """真ん中(0)の軸も出す(P-42。11/16 フロントFB)。軸の表示順に並べるので軸の数だけ返る。
    A09の value_tags と A07の tag の両方で使う(DP-53・DP-55)。
    設定にその段階の言葉がない、または形が崩れている(null など)ときは None にして落とさない
    (取り込み前の古い設定には真ん中の言葉がない。取り込みでは形を確かめている)。"""
    def word(code):
        words = labels.get(code) if isinstance(labels, dict) else None
        w = words.get(str(ev.levels[code])) if isinstance(words, dict) else None
        return w if isinstance(w, str) else None
    return [word(code) for code in axis_order]
