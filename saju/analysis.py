"""공부 성향과 두뇌 직업 적성 분석.

원국의 십성·오행·신살을 **열한 개의 능력 축**으로 환산한 뒤, 그 축의 조합으로
학습 스타일과 직업 적합도를 낸다. 중간에 축을 한 번 거치는 이유는 두 가지다.

* 직업마다 "정인이 몇 점" 식으로 적으면 규칙이 수십 개로 불어나고 서로
  모순되기 쉽다. 축으로 묶으면 직업 정의가 짧아지고 비교가 된다.
* 축 점수를 그대로 보여줄 수 있어서, 왜 그 직업이 추천됐는지 설명이 된다.

점수는 모두 0~100이고 **50이 평균**이다. 십성 다섯 그룹이 고르게 20%씩
퍼져 있으면 모든 축이 50점 근처로 나온다. 70점이 넘으면 또렷한 강점,
30점 아래면 의식적으로 보완할 영역이라고 읽으면 된다.

한 가지 분명히 해 둘 것: 이것은 통계적 예측이 아니라 전통 명리 규칙을
코드로 옮긴 결과다. 진로를 좁히는 근거가 아니라 자기 이해를 넓히는 재료로
쓰는 편이 맞다.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import constants as K
from .korean import josa
from .pillars import FourPillars, LuckPillar
from .shinsal import ShinsalHit, find_shinsal
from .tenstars import (
    DEFAULT_WEIGHTS,
    ElementProfile,
    TenGodProfile,
    Weights,
    element_profile,
    ten_god_of,
    ten_god_profile,
)

__all__ = [
    "AXES",
    "CAREERS",
    "Career",
    "CareerFit",
    "StudyProfile",
    "LuckReading",
    "analyze",
    "Analysis",
]


# --------------------------------------------------------------------------
# 능력 축
# --------------------------------------------------------------------------

AXES: dict[str, str] = {
    "흡수력": "새 개념을 받아들이고 암기해 체계로 쌓는 힘",
    "표현력": "이해한 것을 말과 글로 내보내는 힘",
    "논리력": "구조를 세우고 따져서 결론까지 밀고 가는 힘",
    "창의력": "기존 틀을 의심하고 다르게 엮어 보는 힘",
    "정밀성": "숫자와 디테일을 틀리지 않고 끝까지 챙기는 힘",
    "몰입력": "한 주제에 오래 잠겨 파고드는 힘",
    "지구력": "매일 같은 분량을 흔들림 없이 끌고 가는 힘",
    "경쟁력": "겨루는 상황에서 오히려 올라가는 힘",
    "실행력": "마감과 압박을 결과로 바꾸는 힘",
    "소통력": "사람을 읽고 설득하며 함께 굴리는 힘",
    "직관력": "근거가 다 모이기 전에 방향을 감지하는 힘",
}


MAX_SHINSAL_BONUS = 18.0
"""신살이 한 능력 축에 더할 수 있는 최대 점수."""

# 오행별 평균 세력 — 1940~2038년 무작위 사주 3000개를 돌려 실측한 값이다.
# 토(土)가 유독 높은 것은 진·술·축·미 네 지지가 모두 토인 데다 다른 지지의
# 지장간에도 무·기가 자주 섞여 들어가기 때문이다. 다섯 오행이 20%씩 고르게
# 나온다고 가정하면 토가 들어가는 축만 통째로 부풀어 오르므로, 축 점수의
# '50점 = 평균' 기준을 이 실측값으로 잡는다.
ELEMENT_BASELINE: dict[str, float] = {
    "목": 18.25, "화": 17.62, "토": 26.98, "금": 19.30, "수": 17.86,
}

GROUP_BASELINE = 20.0
"""십성 다섯 그룹의 평균 비율. 실측해도 20%에 거의 정확히 맞는다."""

GOD_BASELINE = 10.0
"""개별 십성 열 개의 평균 비율. 이쪽도 실측값이 10%와 일치한다."""

# 축별 보정값 — 축마다 분포가 달라 그대로 두면 서로 비교가 안 된다.
# 예컨대 창의력은 중앙값이 43 근처, 몰입력은 54 근처로 나온다. 직업 점수는
# 여러 축의 가중평균이므로, 낮게 깔리는 축을 요구하는 직업이 구조적으로
# 불리해진다. 그래서 무작위 사주 표본의 중앙값이 50이 되도록 축마다 평행이동
# 시킨다. 값은 `tools/calibrate.py` 로 다시 뽑을 수 있다.
AXIS_OFFSET: dict[str, float] = {
    "흡수력": 0.9, "표현력": 2.8, "논리력": 2.3, "창의력": 6.8,
    "정밀성": 5.9, "몰입력": -0.8, "지구력": 5.0, "경쟁력": 2.9,
    "실행력": 0.4, "소통력": 0.9, "직관력": -0.4,
}


def _index(percent: float, average: float) -> float:
    """비율을 '50이 평균'인 지수로 바꾼다."""
    if average <= 0:
        return 50.0
    return round(min(100.0, percent / average * 50.0), 1)


@dataclass
class AxisScores:
    """열한 개 능력 축의 점수."""

    scores: dict[str, float]

    def __getitem__(self, key: str) -> float:
        return self.scores[key]

    def top(self, n: int = 3) -> list[tuple[str, float]]:
        return sorted(self.scores.items(), key=lambda kv: -kv[1])[:n]

    def bottom(self, n: int = 3) -> list[tuple[str, float]]:
        return sorted(self.scores.items(), key=lambda kv: kv[1])[:n]

    def bar(self, axis: str, width: int = 20) -> str:
        filled = round(self.scores[axis] / 100 * width)
        return "█" * filled + "·" * (width - filled)


def _axis_scores(
    gods: TenGodProfile, elements: ElementProfile, shinsal: list[ShinsalHit]
) -> AxisScores:
    """십성·오행·신살을 능력 축으로 환산한다."""
    g = {name: _index(pct, GROUP_BASELINE) for name, pct in gods.group_percent.items()}
    e = {name: _index(pct, ELEMENT_BASELINE[name]) for name, pct in elements.percent.items()}

    total_god = sum(gods.scores.values()) or 1.0
    s = {
        name: _index(score / total_god * 100, GOD_BASELINE)
        for name, score in gods.scores.items()
    }

    # 신살 보정 — 해당 축에 가산점을 준다. 월지·일지면 두 배.
    bonus: dict[str, float] = {axis: 0.0 for axis in AXES}
    shinsal_bonus = {
        "문창귀인": [("표현력", 8), ("흡수력", 5)],
        "학당귀인": [("흡수력", 8), ("지구력", 4)],
        "문곡귀인": [("논리력", 5), ("몰입력", 4)],
        "천을귀인": [("소통력", 5)],
        "화개": [("몰입력", 6), ("직관력", 4)],
        "역마": [("실행력", 5), ("소통력", 3)],
        "양인": [("경쟁력", 8), ("실행력", 5)],
        "괴강": [("몰입력", 5), ("경쟁력", 6)],
        "천문성": [("직관력", 8)],
    }
    for hit in shinsal:
        mult = 2.0 if hit.is_prominent else 1.0
        for axis, pts in shinsal_bonus.get(hit.name, []):
            bonus[axis] += pts * mult
    # 신살이 여럿 겹쳐도 한 축을 통째로 밀어 올리지는 못하게 상한을 둔다.
    # 신살은 원국의 보조 근거이지 그 자체로 결론이 아니기 때문이다.
    bonus = {axis: min(v, MAX_SHINSAL_BONUS) for axis, v in bonus.items()}

    raw = {
        "흡수력": 0.70 * g["인성"] + 0.30 * e["수"],
        "표현력": 0.60 * g["식상"] + 0.20 * e["화"] + 0.20 * e["목"],
        "논리력": 0.40 * e["금"] + 0.30 * e["수"] + 0.30 * s["정관"],
        "창의력": 0.45 * s["상관"] + 0.30 * s["편인"] + 0.25 * e["화"],
        "정밀성": 0.45 * s["정재"] + 0.35 * e["금"] + 0.20 * s["정관"],
        "몰입력": 0.50 * s["편인"] + 0.30 * e["토"] + 0.20 * g["인성"],
        "지구력": 0.40 * s["정관"] + 0.30 * e["토"] + 0.30 * s["정인"],
        "경쟁력": 0.60 * g["비겁"] + 0.40 * s["편관"],
        "실행력": 0.40 * s["편관"] + 0.30 * g["비겁"] + 0.30 * g["재성"],
        "소통력": 0.50 * s["식신"] + 0.30 * g["재성"] + 0.20 * s["정관"],
        "직관력": 0.50 * s["편인"] + 0.30 * e["수"] + 0.20 * e["화"],
    }
    return AxisScores(
        {
            k: round(max(0.0, min(100.0, v + bonus[k] + AXIS_OFFSET[k])), 1)
            for k, v in raw.items()
        }
    )


# --------------------------------------------------------------------------
# 학습 스타일
# --------------------------------------------------------------------------

@dataclass
class Axis2:
    """두 극 사이 어디쯤인지 나타내는 축."""

    left: str
    right: str
    value: float          # -100(완전 왼쪽) ~ +100(완전 오른쪽)
    note: str

    @property
    def label(self) -> str:
        if abs(self.value) < 15:
            return f"{self.left} · {self.right} 균형"
        return self.right if self.value > 0 else self.left

    def bar(self, width: int = 21) -> str:
        mid = width // 2
        pos = max(0, min(width - 1, mid + round(self.value / 100 * mid)))
        cells = ["·"] * width
        cells[mid] = "│"
        cells[pos] = "●"
        return "".join(cells)


@dataclass
class StudyProfile:
    """공부와 관련된 성향 묶음."""

    axes: AxisScores
    style_axes: list[Axis2]
    strengths: list[str]
    cautions: list[str]
    method_tips: list[str]


def _style_axes(axes: AxisScores, gods: TenGodProfile) -> list[Axis2]:
    def spread(a: float, b: float) -> float:
        """두 점수의 차이를 -100~100 으로."""
        return round(max(-100.0, min(100.0, (b - a) * 2.0)), 1)

    total_god = sum(gods.scores.values()) or 1.0

    def god_index(name: str) -> float:
        """개별 십성의 지수(50이 평균)."""
        return _index(gods.scores[name] / total_god * 100, GOD_BASELINE)

    def group_index(name: str) -> float:
        """십성 그룹의 지수(50이 평균)."""
        return _index(gods.group(name), GROUP_BASELINE)

    return [
        Axis2(
            "암기·흡수형", "이해·표현형",
            spread(axes["흡수력"], axes["표현력"]),
            "인성(받아들이는 힘)과 식상(내보내는 힘) 중 어느 쪽이 두터운가",
        ),
        Axis2(
            "제도권 시험형", "자기주도 연구형",
            spread(
                0.5 * group_index("관성") + 0.5 * god_index("정인"),
                0.5 * group_index("식상") + 0.5 * god_index("편인"),
            ),
            "정해진 커리큘럼·시험에 강한가, 스스로 주제를 파는 쪽에 강한가",
        ),
        Axis2(
            "꾸준한 누적형", "단기 몰입형",
            spread(axes["지구력"], axes["몰입력"]),
            "매일 조금씩 쌓는 쪽인가, 한번에 몰아쳐 끝내는 쪽인가",
        ),
        Axis2(
            "혼자 파는 쪽", "함께 겨루는 쪽",
            spread(axes["몰입력"], axes["경쟁력"]),
            "고립된 환경이 효율적인가, 경쟁과 자극이 있어야 오르는가",
        ),
        Axis2(
            "구조·논리 우선", "직관·감각 우선",
            spread(axes["논리력"], axes["직관력"]),
            "차근차근 쌓아 올리는가, 전체 그림을 먼저 잡는가",
        ),
    ]


def _study_notes(
    axes: AxisScores, gods: TenGodProfile, elements: ElementProfile,
    shinsal: list[ShinsalHit],
) -> tuple[list[str], list[str], list[str]]:
    """강점·주의점·학습법 조언을 글로 뽑는다."""
    strengths: list[str] = []
    cautions: list[str] = []
    tips: list[str] = []

    hi = {name for name, v in axes.scores.items() if v >= 65}
    lo = {name for name, v in axes.scores.items() if v <= 35}

    detail = {
        "흡수력": (
            "개념을 받아들이는 속도가 빠릅니다. 새 과목의 진입장벽이 낮은 편입니다.",
            "읽고 들은 것이 오래 남지 않는 편입니다. 입력량보다 정리가 관건입니다.",
        ),
        "표현력": (
            "이해한 것을 밖으로 꺼내는 힘이 좋습니다. 서술형·발표·논술에서 유리합니다.",
            "아는 것을 설명하려면 막히는 편입니다. 시험에서 손해를 보기 쉽습니다.",
        ),
        "논리력": (
            "구조를 세우고 끝까지 따지는 힘이 있습니다. 수리·법리·코드에 맞습니다.",
            "논리적 전개가 느슨해지기 쉽습니다. 근거를 적어 가며 푸는 습관이 필요합니다.",
        ),
        "창의력": (
            "정해진 답 밖을 보는 눈이 있습니다. 연구 주제를 스스로 잡는 데 강합니다.",
            "기존 틀 안에서 안정적으로 움직입니다. 정답이 있는 분야가 편합니다.",
        ),
        "정밀성": (
            "숫자와 디테일에서 실수가 적습니다. 계산·검증 과목에서 점수를 지킵니다.",
            "실수로 잃는 점수가 많을 수 있습니다. 검산 절차를 습관으로 만드세요.",
        ),
        "몰입력": (
            "한 주제에 오래 잠기는 힘이 강합니다. 연구와 장기 프로젝트에 맞습니다.",
            "오래 앉아 있기가 힘든 편입니다. 짧게 끊어 가는 구성이 유리합니다.",
        ),
        "지구력": (
            "매일 같은 분량을 끌고 가는 힘이 있습니다. 장기 수험에서 강합니다.",
            "일정이 흐트러지기 쉽습니다. 외부 장치(스터디·학원)로 리듬을 고정하세요.",
        ),
        "경쟁력": (
            "겨루는 상황에서 오히려 실력이 올라갑니다. 모의고사형 환경이 맞습니다.",
            "경쟁이 압박으로만 작용하기 쉽습니다. 자기 기록을 상대로 두세요.",
        ),
        "실행력": (
            "마감이 걸리면 결과를 냅니다. 압박을 동력으로 씁니다.",
            "시작이 늦어지기 쉽습니다. 마감을 인위적으로 만들어 두세요.",
        ),
        "소통력": (
            "사람을 통해 배우고 가르치며 정리하는 데 능합니다.",
            "혼자 하는 편이 효율적입니다. 그룹 스터디는 오히려 손해일 수 있습니다.",
        ),
        "직관력": (
            "전체 그림을 먼저 잡는 감이 있습니다. 새 분야 적응이 빠릅니다.",
            "감보다 절차가 안전합니다. 단계를 밟아 확인하는 쪽이 맞습니다.",
        ),
    }

    for axis in AXES:
        if axis in hi:
            strengths.append(f"[{axis} {axes[axis]:.0f}] {detail[axis][0]}")
        elif axis in lo:
            cautions.append(f"[{axis} {axes[axis]:.0f}] {detail[axis][1]}")

    # 구조적 조합에서 나오는 조언
    if axes["흡수력"] - axes["표현력"] >= 20:
        tips.append(
            "받아들이는 힘이 내보내는 힘보다 큽니다. 읽은 다음 반드시 백지에 "
            "복원하거나 남에게 설명하는 단계를 넣어야 점수로 바뀝니다."
        )
    if axes["표현력"] - axes["흡수력"] >= 20:
        tips.append(
            "내보내는 힘이 앞섭니다. 아는 것처럼 느껴지는 착각을 조심하고, "
            "기본서를 처음부터 한 번 통독하는 시간을 따로 확보하세요."
        )
    if axes["몰입력"] >= 60 and axes["지구력"] <= 45:
        tips.append(
            "몰아치기형입니다. 짧고 굵은 집중 구간을 여러 번 배치하고, "
            "쉬는 날을 계획에 미리 넣어 번아웃을 관리하세요."
        )
    if axes["지구력"] >= 60 and axes["몰입력"] <= 45:
        tips.append(
            "누적형입니다. 하루 분량을 작게 고정해 오래 끌고 가는 방식이 맞고, "
            "벼락치기 전략으로 바꾸면 오히려 손해입니다."
        )
    if gods.group("재성") >= 28 and gods.group("인성") <= 15:
        tips.append(
            "재성이 인성을 누르는 구조입니다(재극인). 관심사가 넓게 흩어져 "
            "공부가 뒤로 밀리기 쉬우니, 학습 시간을 먼저 떼어 놓고 나머지를 "
            "배치하는 순서로 바꾸세요."
        )
    if gods.group("인성") >= 35:
        tips.append(
            "인성이 매우 두텁습니다. 자료를 모으고 계획을 다듬는 데 시간을 "
            "다 쓰기 쉽습니다. 입력을 줄이고 문제 풀이 비중을 올리세요."
        )
    if gods.group("관성") <= 10:
        cautions.append(
            "[관성 부족] 외부에서 걸어 주는 규율이 약합니다. 스스로 정한 "
            "계획은 무너지기 쉬우니 시험 일정·스터디처럼 강제력이 있는 "
            "장치를 붙이는 편이 안전합니다."
        )
    if elements.missing:
        lacking = "·".join(elements.missing)
        tips.append(
            f"오행 중 {josa(lacking, '이')} 거의 없습니다. "
            "해당 성향의 과목이나 활동을 의도적으로 섞으면 균형이 잡힙니다."
        )

    for hit in shinsal:
        if hit.is_prominent:
            tips.append(
                f"{josa(hit.name, '이')} {'·'.join(hit.positions)}에 있어 작용이 "
                f"뚜렷합니다. {hit.meaning}."
            )

    return strengths, cautions, tips


# --------------------------------------------------------------------------
# 두뇌 직업
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Career:
    """두뇌를 쓰는 직업 하나와 그 직업이 요구하는 능력 비중."""

    name: str
    field: str
    weights: dict[str, float]
    blurb: str
    advice: str


def _c(name, field, blurb, advice, **weights) -> Career:
    return Career(name, field, weights, blurb, advice)


CAREERS: list[Career] = [
    _c("기초과학 연구자", "연구",
       "물리·수학·생물처럼 답이 정해지지 않은 문제를 오래 붙들고 있는 일",
       "학부 때부터 한 연구실에 깊이 붙는 편이 유리합니다. 논문 읽기를 일상 루틴으로 만드세요.",
       몰입력=3.0, 논리력=2.5, 창의력=2.0, 지구력=1.5, 흡수력=1.5, 직관력=1.0),
    _c("공학 R&D", "연구",
       "제약 조건 안에서 실제로 동작하는 것을 만들어 내는 일",
       "이론과 구현을 같이 굴리세요. 손으로 만들어 본 경험이 곧 경쟁력이 됩니다.",
       논리력=2.5, 실행력=2.0, 정밀성=2.0, 몰입력=1.8, 창의력=1.5, 지구력=1.2),
    _c("소프트웨어 개발자", "기술",
       "추상적인 구조를 코드로 옮기고 끊임없이 고쳐 나가는 일",
       "만들고 싶은 것을 정해 끝까지 완성해 보는 경험이 자격증보다 낫습니다.",
       논리력=2.8, 몰입력=2.0, 정밀성=1.8, 창의력=1.5, 실행력=1.5, 흡수력=1.2),
    _c("데이터 사이언티스트·AI", "기술",
       "데이터에서 구조를 찾아내고 모델로 세우는 일",
       "수학 기초와 코드 중 하나라도 비면 금방 한계가 옵니다. 둘을 같이 끌고 가세요.",
       논리력=2.8, 정밀성=2.2, 흡수력=1.8, 창의력=1.5, 몰입력=1.5, 직관력=1.2),
    _c("의사·의료인", "의료",
       "방대한 지식을 외우고 사람의 몸 상태를 판단하는 일",
       "압도적인 암기량을 버티는 체력과 루틴이 먼저입니다. 장기전으로 설계하세요.",
       흡수력=2.5, 지구력=2.5, 정밀성=2.0, 직관력=1.5, 실행력=1.5, 소통력=1.2),
    _c("약사·바이오 연구", "의료",
       "물질과 생체의 상호작용을 다루는, 정확성이 곧 안전인 일",
       "화학·생물의 기본기를 반복해서 다지는 것이 가장 확실한 투자입니다.",
       정밀성=2.8, 흡수력=2.2, 논리력=1.8, 지구력=1.8, 몰입력=1.2),
    _c("법조인", "법·행정",
       "규칙 체계를 해석하고 사실에 적용해 결론을 내는 일",
       "장기 수험이 관문입니다. 리듬을 잃지 않는 생활 설계가 실력만큼 중요합니다.",
       논리력=2.5, 지구력=2.5, 흡수력=2.2, 표현력=1.8, 경쟁력=1.5, 정밀성=1.2),
    _c("행정·공공정책", "법·행정",
       "제도를 설계하고 운영하며 이해관계를 조율하는 일",
       "시험 통과가 끝이 아니라 시작입니다. 사람과 제도를 함께 보는 눈을 기르세요.",
       지구력=2.5, 흡수력=2.0, 소통력=2.0, 논리력=1.8, 실행력=1.5),
    _c("교수·학자", "교육",
       "스스로 질문을 만들고 연구하며 그것을 가르치는 일",
       "긴 무보상 구간을 견디는 일입니다. 연구 자체가 즐거운지 먼저 확인하세요.",
       몰입력=2.8, 흡수력=2.2, 표현력=2.0, 논리력=2.0, 창의력=1.8, 지구력=1.5),
    _c("교사·강사", "교육",
       "어려운 것을 알아듣게 바꿔 전달하는 일",
       "잘 아는 것과 잘 가르치는 것은 다릅니다. 설명을 연습 대상으로 삼으세요.",
       표현력=2.8, 소통력=2.5, 흡수력=1.8, 지구력=1.8, 창의력=1.2),
    _c("작가·저널리스트", "언어·콘텐츠",
       "취재하고 사유한 것을 글로 구조화해 내보내는 일",
       "매일 정해진 분량을 쓰는 습관이 재능보다 오래갑니다.",
       표현력=3.0, 창의력=2.2, 흡수력=1.8, 직관력=1.5, 몰입력=1.5),
    _c("통번역·언어전문가", "언어·콘텐츠",
       "두 언어 사이의 의미를 잃지 않고 옮기는 일",
       "어휘 암기와 실전 노출을 병행하세요. 한쪽만으로는 늘지 않습니다.",
       흡수력=2.8, 표현력=2.5, 정밀성=2.0, 소통력=1.5, 지구력=1.5),
    _c("심리상담·정신건강", "사람",
       "사람의 내면을 읽고 변화가 일어나도록 돕는 일",
       "이론 학습과 자기 분석을 같이 가야 합니다. 수련 기간을 길게 잡으세요.",
       직관력=2.8, 소통력=2.5, 흡수력=2.0, 몰입력=1.5, 표현력=1.5),
    _c("회계·세무·재무", "금융",
       "숫자로 실체를 드러내고 규정에 맞게 정리하는 일",
       "규정은 계속 바뀝니다. 최신 개정을 따라가는 루틴을 만들어 두세요.",
       정밀성=3.0, 지구력=2.2, 논리력=2.0, 흡수력=1.5),
    _c("금융 애널리스트·트레이더", "금융",
       "불확실한 정보 속에서 판단하고 그 결과를 책임지는 일",
       "분석력만큼 심리 관리가 성패를 가릅니다. 자기 원칙을 글로 정해 두세요.",
       논리력=2.2, 직관력=2.2, 실행력=2.0, 정밀성=2.0, 경쟁력=1.8),
    _c("경영전략·컨설팅", "비즈니스",
       "복잡한 상황을 구조로 정리해 의사결정을 끌어내는 일",
       "프레임워크보다 현장 이해가 먼저입니다. 숫자로 말하는 훈련을 하세요.",
       논리력=2.5, 표현력=2.2, 실행력=2.0, 소통력=2.0, 경쟁력=1.5, 흡수력=1.2),
    _c("기획·프로덕트 매니저", "비즈니스",
       "무엇을 만들지 정하고 여러 사람을 한 방향으로 모으는 일",
       "설득은 결국 근거입니다. 데이터와 사용자 관찰을 함께 들고 다니세요.",
       소통력=2.5, 창의력=2.2, 실행력=2.2, 논리력=1.8, 표현력=1.8),
    _c("건축·설계", "설계",
       "제약과 아름다움을 동시에 만족시키는 구조를 그리는 일",
       "공간 감각은 많이 보고 그려야 늡니다. 답사를 공부로 치세요.",
       창의력=2.5, 정밀성=2.2, 논리력=2.0, 몰입력=1.8, 표현력=1.5),
    _c("디자인·크리에이티브", "설계",
       "의도를 시각 언어로 번역해 사람을 움직이는 일",
       "취향을 쌓는 것도 훈련입니다. 좋은 것을 많이 보고 이유를 적어 두세요.",
       창의력=3.0, 직관력=2.2, 표현력=2.0, 몰입력=1.5, 소통력=1.2),
    _c("인문·역사 연구", "연구",
       "사료와 텍스트를 읽어 맥락을 복원하고 해석하는 일",
       "언어(고전어·외국어)가 곧 도구입니다. 일찍 시작할수록 유리합니다.",
       몰입력=2.8, 흡수력=2.5, 표현력=2.2, 논리력=1.8, 지구력=1.5),
]


@dataclass
class CareerFit:
    """직업 하나에 대한 적합도."""

    career: Career
    score: float
    matched: list[tuple[str, float]]     # 요구 축 중 높게 나온 것
    lacking: list[tuple[str, float]]     # 요구 축 중 낮게 나온 것

    @property
    def grade(self) -> str:
        if self.score >= 70:
            return "매우 높음"
        if self.score >= 60:
            return "높음"
        if self.score >= 50:
            return "보통"
        if self.score >= 40:
            return "낮음"
        return "매우 낮음"

    def reason(self) -> str:
        parts = []
        if self.matched:
            parts.append(
                "강점이 맞물림: " + ", ".join(f"{a} {v:.0f}" for a, v in self.matched)
            )
        if self.lacking:
            parts.append(
                "보완 필요: " + ", ".join(f"{a} {v:.0f}" for a, v in self.lacking)
            )
        return " / ".join(parts) if parts else "두드러진 편차 없음"


def _career_fits(axes: AxisScores) -> list[CareerFit]:
    fits: list[CareerFit] = []
    for career in CAREERS:
        total_w = sum(career.weights.values())
        score = sum(axes[a] * w for a, w in career.weights.items()) / total_w
        ranked = sorted(career.weights.items(), key=lambda kv: -kv[1])
        matched = [(a, axes[a]) for a, _ in ranked if axes[a] >= 62][:3]
        lacking = [(a, axes[a]) for a, w in ranked if axes[a] <= 40 and w >= 2.0][:2]
        fits.append(CareerFit(career, round(score, 1), matched, lacking))
    return sorted(fits, key=lambda f: -f.score)


# --------------------------------------------------------------------------
# 대운으로 보는 학업 시기
# --------------------------------------------------------------------------

@dataclass
class LuckReading:
    """대운 한 구간의 학업 관점 해석."""

    luck: LuckPillar
    score: float
    tags: list[str]
    comment: str

    @property
    def age_range(self) -> str:
        return f"{self.luck.start_age:.0f}~{self.luck.end_age:.0f}세"


_LUCK_WEIGHT = {
    "정인": 1.00, "편인": 0.85,     # 배움이 들어오는 운
    "식신": 0.70, "상관": 0.55,     # 산출·표현이 터지는 운
    "정관": 0.65, "편관": 0.40,     # 규율과 시험의 운
    "비견": 0.15, "겁재": 0.00,     # 경쟁의 운
    "정재": -0.35, "편재": -0.55,   # 관심이 흩어지는 운(재극인)
}

_LUCK_NOTE = {
    "정인": "배움이 순하게 들어오는 시기입니다. 학위·자격·정규 과정에 붙이기 좋습니다.",
    "편인": "한 분야를 깊이 파기 좋은 시기입니다. 비주류·전문 영역에서 성과가 납니다.",
    "식신": "배운 것을 밖으로 꺼내기 좋은 시기입니다. 발표·집필·창작이 잘 풀립니다.",
    "상관": "기존 틀을 깨는 시기입니다. 독창적 성과가 나지만 제도권과 마찰이 생길 수 있습니다.",
    "정관": "규율이 잡히는 시기입니다. 시험·임용처럼 정해진 관문을 통과하기 좋습니다.",
    "편관": "압박이 커지는 시기입니다. 견디면 급성장하지만 소진을 조심해야 합니다.",
    "비견": "또래와 나란히 달리는 시기입니다. 스터디·협업에서 힘을 받습니다.",
    "겁재": "경쟁이 격해지는 시기입니다. 페이스를 남에게 맡기지 마세요.",
    "정재": "현실적인 일에 시간을 뺏기기 쉬운 시기입니다. 공부 시간을 먼저 확보하세요.",
    "편재": "관심이 넓게 흩어지는 시기입니다. 벌여 놓은 것을 줄이는 결단이 필요합니다.",
}


def _luck_readings(saju: FourPillars) -> list[LuckReading]:
    dm = saju.day_master
    readings: list[LuckReading] = []
    for lp in saju.luck_pillars:
        stem_god = ten_god_of(dm, lp.pillar.stem)
        # 지지는 정기(지장간의 대표 글자)로 본다
        main_hidden = max(K.HIDDEN_STEMS[lp.pillar.branch], key=lambda hr: hr[1])[0]
        branch_god = ten_god_of(dm, main_hidden)

        raw = _LUCK_WEIGHT[stem_god] * 0.55 + _LUCK_WEIGHT[branch_god] * 0.45
        score = round(50 + raw * 45, 1)

        tags = sorted({stem_god, branch_god})
        note = _LUCK_NOTE[stem_god]
        if branch_god != stem_god:
            note += " " + _LUCK_NOTE[branch_god]
        readings.append(LuckReading(lp, score, tags, note))
    return readings


# --------------------------------------------------------------------------
# 전체 분석
# --------------------------------------------------------------------------

@dataclass
class Analysis:
    """분석 결과 한 벌."""

    saju: FourPillars
    elements: ElementProfile
    gods: TenGodProfile
    shinsal: list[ShinsalHit]
    study: StudyProfile
    careers: list[CareerFit]
    luck: list[LuckReading]

    @property
    def axes(self) -> AxisScores:
        return self.study.axes

    def best_study_years(
        self, top: int = 3, max_age: float = 45.0, min_score: float = 55.0
    ) -> list[LuckReading]:
        """학업에 유리한 대운.

        학습 연령대(기본 45세 이전)의 대운 중 실제로 유리한 것만 돌려준다.
        상위 몇 개를 무조건 뽑으면 불리한 시기까지 '유리한 시기'로 올라오므로,
        `min_score` 를 넘는 것만 남긴다. 하나도 없으면 빈 목록이 나온다 —
        그 자체가 "학습 연령대에 뚜렷한 학업운이 없다"는 정보다.
        """
        candidates = [
            r for r in self.luck
            if r.luck.start_age < max_age and r.score >= min_score
        ]
        return sorted(candidates, key=lambda r: -r.score)[:top]

    def hardest_study_years(
        self, top: int = 2, max_age: float = 45.0, max_score: float = 45.0
    ) -> list[LuckReading]:
        """반대로, 학습 연령대 중 공부가 밀리기 쉬운 대운."""
        candidates = [
            r for r in self.luck
            if r.luck.start_age < max_age and r.score <= max_score
        ]
        return sorted(candidates, key=lambda r: r.score)[:top]

    def top_careers(self, n: int = 5) -> list[CareerFit]:
        return self.careers[:n]

    def careers_in(self, field: str) -> list[CareerFit]:
        return [f for f in self.careers if f.career.field == field]


def analyze(saju: FourPillars, weights: Weights = DEFAULT_WEIGHTS) -> Analysis:
    """사주 하나를 받아 공부·직업 분석을 끝까지 수행한다."""
    elements = element_profile(saju, weights)
    gods = ten_god_profile(saju, weights)
    shinsal = find_shinsal(saju)

    axes = _axis_scores(gods, elements, shinsal)
    strengths, cautions, tips = _study_notes(axes, gods, elements, shinsal)
    study = StudyProfile(
        axes=axes,
        style_axes=_style_axes(axes, gods),
        strengths=strengths,
        cautions=cautions,
        method_tips=tips,
    )

    return Analysis(
        saju=saju,
        elements=elements,
        gods=gods,
        shinsal=shinsal,
        study=study,
        careers=_career_fits(axes),
        luck=_luck_readings(saju),
    )
