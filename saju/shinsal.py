"""신살(神殺) — 공부와 머리 쓰는 일에 관련된 것만 골라 본다.

신살은 수백 가지가 전해지지만 대부분은 길흉을 단정하는 쪽이라 이 패키지의
관심사가 아니다. 여기서는 학습·연구·시험·표현과 연결되는 것만 추렸고,
각 신살이 '무엇을 뜻하는가' 보다 '어떤 공부 방식과 맞는가' 로 풀어 썼다.

모든 판정은 어느 자리(연지·월지·일지·시지)에서 걸렸는지까지 돌려준다.
자리마다 힘이 다르기 때문이다. 대체로 일지·월지에 있을 때 가장 뚜렷하다.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import constants as K
from .pillars import FourPillars

__all__ = ["ShinsalHit", "STUDY_SHINSAL", "find_shinsal"]


# --------------------------------------------------------------------------
# 판정표
# --------------------------------------------------------------------------

# 문창귀인 — 일간 기준. 글과 시험에 강한 별.
MUNCHANG = {
    "갑": "사", "을": "오", "병": "신", "정": "유", "무": "신",
    "기": "유", "경": "해", "신": "자", "임": "인", "계": "묘",
}

# 학당귀인 — 일간의 장생지. 배움이 몸에 붙는 자리.
HAKDANG = {dm: K.BRANCHES[b] for dm, b in K.CHANGSAENG_BRANCH.items()}

# 문곡귀인 — 문창의 짝. 암기보다 궁리에 가깝다.
MUNGOK = {
    "갑": "해", "을": "자", "병": "인", "정": "묘", "무": "인",
    "기": "묘", "경": "사", "신": "오", "임": "신", "계": "유",
}

# 천을귀인 — 일간 기준. 결정적인 순간에 도와주는 사람이 나타나는 별.
CHEONEUL = {
    "갑": ("축", "미"), "무": ("축", "미"), "경": ("축", "미"),
    "을": ("자", "신"), "기": ("자", "신"),
    "병": ("해", "유"), "정": ("해", "유"),
    "신": ("인", "오"),
    "임": ("사", "묘"), "계": ("사", "묘"),
}

# 삼합국별 화개(華蓋)와 역마(驛馬) — 연지·일지를 기준으로 본다.
_TRIAD = {
    frozenset(("인", "오", "술")): {"화개": "술", "역마": "신"},
    frozenset(("사", "유", "축")): {"화개": "축", "역마": "해"},
    frozenset(("신", "자", "진")): {"화개": "진", "역마": "인"},
    frozenset(("해", "묘", "미")): {"화개": "미", "역마": "사"},
}

# 양인 — 양간만 본다. 날이 선 집중력.
YANGIN = {"갑": "묘", "병": "오", "무": "오", "경": "유", "임": "자"}

# 괴강 — 일주로 본다. 총명하되 극단으로 치우치기 쉽다.
GWAEGANG = {"경진", "경술", "임진", "무술"}

# 천문성 — 술·해. 사람의 속과 몸을 들여다보는 분야와 인연이 깊다.
CHEONMUN = {"술", "해"}


STUDY_SHINSAL: dict[str, str] = {
    "문창귀인": "글·시험에 강한 별. 읽고 쓰는 학습이 잘 붙고 서술형·논술에서 힘을 낸다",
    "학당귀인": "배움이 몸에 붙는 별. 정규 교육과정과 궁합이 좋고 스승 복이 있다",
    "문곡귀인": "궁리하는 별. 외우기보다 파고들어 이해하는 쪽이 맞는다",
    "천을귀인": "귀인의 별. 결정적인 시험·진학 국면에서 도와주는 사람이 나타난다",
    "화개": "홀로 깊이 파는 별. 연구·철학·예술처럼 혼자 몰입하는 분야와 맞는다",
    "역마": "움직이는 별. 유학·어학·출장이 잦은 분야, 현장을 도는 공부에서 살아난다",
    "양인": "날 선 집중력. 몰아치기와 승부처에 강하지만 번아웃을 조심해야 한다",
    "괴강": "극단적 총명. 한번 잡으면 끝을 보지만 중간이 없다",
    "천문성": "사람의 속을 들여다보는 별. 의료·심리·상담·역학과 인연이 깊다",
}

_POS_NAME = {"연주": "연지", "월주": "월지", "일주": "일지", "시주": "시지"}


@dataclass(frozen=True)
class ShinsalHit:
    """걸린 신살 하나."""

    name: str
    positions: list[str]
    meaning: str

    @property
    def is_prominent(self) -> bool:
        """월지·일지에 있으면 작용이 뚜렷하다."""
        return any(p in ("월지", "일지") for p in self.positions)

    def __str__(self) -> str:  # pragma: no cover - 표시용
        return f"{self.name}({'·'.join(self.positions)})"


def _branch_positions(saju: FourPillars, target: str | tuple[str, ...]) -> list[str]:
    targets = (target,) if isinstance(target, str) else tuple(target)
    return [
        _POS_NAME[p.label] for p in saju.pillars if p.branch in targets
    ]


def find_shinsal(saju: FourPillars) -> list[ShinsalHit]:
    """원국에서 학업·두뇌 관련 신살을 찾는다."""
    dm = saju.day_master
    hits: list[ShinsalHit] = []

    def add(name: str, positions: list[str]) -> None:
        if positions:
            hits.append(ShinsalHit(name, positions, STUDY_SHINSAL[name]))

    add("문창귀인", _branch_positions(saju, MUNCHANG[dm]))
    add("학당귀인", _branch_positions(saju, HAKDANG[dm]))
    add("문곡귀인", _branch_positions(saju, MUNGOK[dm]))
    add("천을귀인", _branch_positions(saju, CHEONEUL[dm]))

    # 화개·역마는 연지와 일지 각각을 기준으로 본다
    hwagae: set[str] = set()
    yeokma: set[str] = set()
    for base in (saju.year.branch, saju.day.branch):
        for triad, marks in _TRIAD.items():
            if base in triad:
                hwagae.update(_branch_positions(saju, marks["화개"]))
                yeokma.update(_branch_positions(saju, marks["역마"]))
    add("화개", sorted(hwagae, key=lambda p: list(_POS_NAME.values()).index(p)))
    add("역마", sorted(yeokma, key=lambda p: list(_POS_NAME.values()).index(p)))

    if dm in YANGIN:
        add("양인", _branch_positions(saju, YANGIN[dm]))

    if saju.day.ganzhi in GWAEGANG:
        hits.append(ShinsalHit("괴강", ["일주"], STUDY_SHINSAL["괴강"]))

    cheonmun = [
        _POS_NAME[p.label]
        for p in saju.pillars
        if p.branch in CHEONMUN and p.label in ("일주", "시주")
    ]
    add("천문성", cheonmun)

    return hits
