"""사주팔자로 공부 성향과 두뇌 직업 적성을 분석하는 패키지.

가장 짧은 사용법::

    from datetime import datetime
    from saju import read

    result = read(datetime(1990, 5, 15, 10, 30), is_male=True)
    print(result.report)
    print(result.analysis.top_careers(3))

단계별로 쓰고 싶다면::

    from saju import build_saju, analyze, text_report

    chart = build_saju(datetime(1990, 5, 15, 10, 30), is_male=True, place="부산")
    analysis = analyze(chart)
    print(text_report(analysis))
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .analysis import AXES, CAREERS, Analysis, Career, CareerFit, analyze
from .pillars import FourPillars, Pillar, build_saju
from .report import as_dict, text_report
from .shinsal import find_shinsal
from .solar_terms import BACKEND, solar_term_at
from .tenstars import Weights, element_profile, ten_god_of, ten_god_profile
from .timeutil import PLACES, Place, TimeBasis

__version__ = "1.0.0"

__all__ = [
    "AXES",
    "BACKEND",
    "CAREERS",
    "Analysis",
    "Career",
    "CareerFit",
    "FourPillars",
    "Pillar",
    "Place",
    "PLACES",
    "Reading",
    "TimeBasis",
    "Weights",
    "analyze",
    "as_dict",
    "build_saju",
    "element_profile",
    "find_shinsal",
    "read",
    "solar_term_at",
    "ten_god_of",
    "ten_god_profile",
    "text_report",
    "__version__",
]


@dataclass
class Reading:
    """사주 · 분석 · 리포트를 한 번에 담은 결과."""

    saju: FourPillars
    analysis: Analysis
    report: str

    def to_dict(self) -> dict:
        return as_dict(self.analysis)


def read(
    birth: datetime,
    is_male: bool,
    place: Place | str = "서울",
    basis: TimeBasis = TimeBasis.LOCAL_MEAN,
    hour_known: bool = True,
    **kwargs,
) -> Reading:
    """생년월일시 하나로 사주 세우기부터 리포트까지 끝낸다.

    Args:
        birth: 출생 시각(시계 시각 그대로).
        is_male: 대운 방향 판정에 쓴다.
        place: 출생지. 경도 보정에 쓴다.
        basis: 시각 보정 수준.
        hour_known: 출생 시각을 모르면 False.
        **kwargs: `build_saju` 에 그대로 넘어간다.
    """
    chart = build_saju(
        birth, is_male=is_male, place=place, basis=basis,
        hour_known=hour_known, **kwargs,
    )
    result = analyze(chart)
    return Reading(saju=chart, analysis=result, report=text_report(result))
