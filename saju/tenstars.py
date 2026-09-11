"""십성(十神)과 오행 세력 — 원국을 해석 가능한 수치로 바꾼다.

사주 여덟 글자를 그대로 읽어서는 아무 말도 할 수 없다. 일간(日干)을 '나'로
놓고 나머지 글자가 나와 어떤 관계인지 따진 것이 십성이고, 오행이 각각 얼마나
힘을 가졌는지 잰 것이 세력이다. 공부 성향 분석은 전부 이 두 가지 위에 얹힌다.

세력을 잴 때 쓰는 가중치는 `Weights` 에 모아 두었다. 유파마다 배분이 다르므로
숫자를 바꿔 끼울 수 있게 했고, 기본값은 아래 원칙을 따랐다.

* 월지(月支)가 가장 무겁다. 태어난 계절이 오행의 강약을 좌우한다.
* 일지(日支)는 일간이 깔고 앉은 자리라 다음으로 무겁다.
* 지지는 지장간 비율대로 나눠 담는다. 표면 글자만 세면 실제와 어긋난다.
* 마지막으로 월령에 따른 왕상휴수 계수를 곱한다.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from . import constants as K
from .pillars import FourPillars

__all__ = [
    "Weights",
    "ElementProfile",
    "TenGodProfile",
    "ten_god_of",
    "twelve_stage",
    "element_profile",
    "ten_god_profile",
]


@dataclass(frozen=True)
class Weights:
    """세력 계산 가중치. 유파에 맞게 바꿔 쓸 수 있다."""

    year_stem: float = 1.0
    month_stem: float = 1.2
    day_stem: float = 1.0
    hour_stem: float = 1.0

    year_branch: float = 1.0
    month_branch: float = 1.8
    day_branch: float = 1.4
    hour_branch: float = 1.0

    apply_season: bool = True

    def for_pillar(self, label: str, is_stem: bool) -> float:
        key = {"연주": "year", "월주": "month", "일주": "day", "시주": "hour"}[label]
        return getattr(self, f"{key}_{'stem' if is_stem else 'branch'}")


DEFAULT_WEIGHTS = Weights()


# --------------------------------------------------------------------------
# 십성
# --------------------------------------------------------------------------

def ten_god_of(day_master: str, other_stem: str) -> str:
    """일간 `day_master` 에서 본 천간 `other_stem` 의 십성."""
    dm_i = K.STEMS.index(day_master)
    ot_i = K.STEMS.index(other_stem)
    dm_el, ot_el = K.STEM_ELEMENT[dm_i], K.STEM_ELEMENT[ot_i]
    same_polarity = K.STEM_YANG[dm_i] == K.STEM_YANG[ot_i]

    if ot_el == dm_el:
        return "비견" if same_polarity else "겁재"
    if ot_el == K.sheng_of(dm_el):        # 내가 생한다 → 식상
        return "식신" if same_polarity else "상관"
    if ot_el == K.ke_of(dm_el):           # 내가 극한다 → 재성
        return "편재" if same_polarity else "정재"
    if ot_el == K.ke_from(dm_el):         # 나를 극한다 → 관성
        return "편관" if same_polarity else "정관"
    return "편인" if same_polarity else "정인"   # 나를 생한다 → 인성


def twelve_stage(day_master: str, branch: str) -> str:
    """일간이 `branch` 에서 갖는 십이운성."""
    dm_i = K.STEMS.index(day_master)
    start = K.CHANGSAENG_BRANCH[day_master]
    b = K.BRANCHES.index(branch)
    offset = (b - start) % 12 if K.STEM_YANG[dm_i] else (start - b) % 12
    return K.TWELVE_STAGES[offset]


# --------------------------------------------------------------------------
# 오행 세력
# --------------------------------------------------------------------------

@dataclass
class ElementProfile:
    """오행별 세력과 거기서 나온 판정들."""

    raw: dict[str, float]              # 왕상휴수 적용 전
    weighted: dict[str, float]         # 적용 후
    percent: dict[str, float]
    day_master_element: str
    support_score: float               # 비겁 + 인성
    drain_score: float                 # 식상 + 재성 + 관성
    strength_ratio: float              # support / (support + drain)

    @property
    def is_strong(self) -> bool:
        """신강(身强) 여부. 0.5 를 기준선으로 삼는다."""
        return self.strength_ratio >= 0.5

    @property
    def strength_label(self) -> str:
        r = self.strength_ratio
        if r >= 0.62:
            return "신강"
        if r >= 0.52:
            return "중화신강"
        if r >= 0.48:
            return "중화"
        if r >= 0.38:
            return "중화신약"
        return "신약"

    @property
    def dominant(self) -> str:
        return max(self.percent, key=self.percent.get)

    @property
    def missing(self) -> list[str]:
        """세력이 5% 미만이라 사실상 없는 것과 같은 오행."""
        return [e for e in K.ELEMENTS if self.percent[e] < 5.0]

    def bar(self, element: str, width: int = 24) -> str:
        filled = round(self.percent[element] / 100 * width)
        return "█" * filled + "·" * (width - filled)


def element_profile(saju: FourPillars, weights: Weights = DEFAULT_WEIGHTS) -> ElementProfile:
    """원국의 오행 세력을 잰다."""
    raw: dict[str, float] = defaultdict(float)

    for pillar in saju.pillars:
        # 천간은 글자 그대로 한 몫
        raw[pillar.stem_element] += weights.for_pillar(pillar.label, True)
        # 지지는 지장간 비율대로 쪼개 담는다
        bw = weights.for_pillar(pillar.label, False)
        for hidden, ratio in K.HIDDEN_STEMS[pillar.branch]:
            raw[K.STEM_ELEMENT[K.STEMS.index(hidden)]] += bw * ratio

    raw_full = {e: round(raw.get(e, 0.0), 4) for e in K.ELEMENTS}

    if weights.apply_season:
        weighted = {
            e: round(v * K.season_factor(e, saju.month_branch), 4)
            for e, v in raw_full.items()
        }
    else:
        weighted = dict(raw_full)

    total = sum(weighted.values()) or 1.0
    percent = {e: round(v / total * 100, 1) for e, v in weighted.items()}

    dm_el = saju.day_master_element
    support = weighted[dm_el] + weighted[K.sheng_from(dm_el)]          # 비겁 + 인성
    drain = (
        weighted[K.sheng_of(dm_el)]      # 식상
        + weighted[K.ke_of(dm_el)]       # 재성
        + weighted[K.ke_from(dm_el)]     # 관성
    )

    return ElementProfile(
        raw=raw_full,
        weighted=weighted,
        percent=percent,
        day_master_element=dm_el,
        support_score=round(support, 3),
        drain_score=round(drain, 3),
        strength_ratio=round(support / (support + drain or 1.0), 4),
    )


# --------------------------------------------------------------------------
# 십성 분포
# --------------------------------------------------------------------------

@dataclass
class TenGodProfile:
    """십성별 세력과 그룹(비겁·식상·재성·관성·인성) 집계."""

    scores: dict[str, float]
    group_scores: dict[str, float]
    group_percent: dict[str, float]
    placements: dict[str, list[str]] = field(default_factory=dict)
    """십성 → 어느 자리에 있는지 (예: '정인': ['월간', '일지(지장간)'])"""

    def group(self, name: str) -> float:
        return self.group_percent.get(name, 0.0)

    @property
    def dominant_group(self) -> str:
        return max(self.group_percent, key=self.group_percent.get)

    @property
    def weakest_group(self) -> str:
        return min(self.group_percent, key=self.group_percent.get)

    def top(self, n: int = 3) -> list[tuple[str, float]]:
        return sorted(self.scores.items(), key=lambda kv: -kv[1])[:n]


_POSITION_NAME = {
    ("연주", True): "연간", ("연주", False): "연지",
    ("월주", True): "월간", ("월주", False): "월지",
    ("일주", True): "일간", ("일주", False): "일지",
    ("시주", True): "시간", ("시주", False): "시지",
}


def ten_god_profile(
    saju: FourPillars, weights: Weights = DEFAULT_WEIGHTS
) -> TenGodProfile:
    """원국의 십성 분포를 잰다. 일간 자신은 '나'이므로 세지 않는다."""
    scores: dict[str, float] = {g: 0.0 for g in K.TEN_GODS}
    placements: dict[str, list[str]] = defaultdict(list)
    dm = saju.day_master

    for pillar in saju.pillars:
        # 천간
        if pillar.label != "일주":   # 일간은 기준점이므로 제외
            god = ten_god_of(dm, pillar.stem)
            w = weights.for_pillar(pillar.label, True)
            w *= K.season_factor(pillar.stem_element, saju.month_branch) if weights.apply_season else 1
            scores[god] += w
            placements[god].append(_POSITION_NAME[(pillar.label, True)])

        # 지지 — 지장간을 통해 본다
        bw = weights.for_pillar(pillar.label, False)
        for hidden, ratio in K.HIDDEN_STEMS[pillar.branch]:
            god = ten_god_of(dm, hidden)
            el = K.STEM_ELEMENT[K.STEMS.index(hidden)]
            w = bw * ratio
            w *= K.season_factor(el, saju.month_branch) if weights.apply_season else 1
            scores[god] += w
            if ratio >= 0.5:   # 정기(正氣)만 자리로 표시한다
                placements[god].append(_POSITION_NAME[(pillar.label, False)])

    scores = {k: round(v, 4) for k, v in scores.items()}

    group_scores = {g: 0.0 for g in K.GROUPS}
    for god, v in scores.items():
        group_scores[K.TEN_GOD_GROUP[god]] += v
    group_scores = {k: round(v, 4) for k, v in group_scores.items()}

    total = sum(group_scores.values()) or 1.0
    group_percent = {k: round(v / total * 100, 1) for k, v in group_scores.items()}

    return TenGodProfile(
        scores=scores,
        group_scores=group_scores,
        group_percent=group_percent,
        placements=dict(placements),
    )
