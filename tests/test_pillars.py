"""사주 산출 검증.

기댓값은 독립 구현체(sxtwl)와 대조해 확인한 것이다. 차이가 났던 두 건은
전부 이쪽이 맞았다 — sxtwl 은 월주·연주를 날짜 단위로 매기지만 이 패키지는
절입 시각까지 따지기 때문이다.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from saju import constants as K
from saju.pillars import build_saju
from saju.timeutil import TimeBasis

GOLDEN = [
    ("1990-05-15 10:30", True, "서울", ("경오", "신사", "경진", "신사")),
    ("1975-12-31 23:45", False, "서울", ("을묘", "무자", "임자", "경자")),
    ("2000-01-20 06:00", True, "부산", ("기묘", "정축", "정축", "계묘")),
    ("1984-02-04 12:00", False, "서울", ("계해", "을축", "무진", "무오")),
    ("1962-08-08 15:20", True, "대구", ("임인", "무신", "무인", "경신")),
    ("2005-03-09 02:10", False, "제주", ("을유", "기묘", "임진", "신축")),
]


@pytest.mark.parametrize("stamp,male,place,expected", GOLDEN)
def test_golden_charts(stamp, male, place, expected):
    birth = datetime.strptime(stamp, "%Y-%m-%d %H:%M")
    saju = build_saju(birth, male, place, basis=TimeBasis.STANDARD)
    got = (saju.year.ganzhi, saju.month.ganzhi, saju.day.ganzhi, saju.hour.ganzhi)
    assert got == expected


def test_day_pillar_advances_one_step_per_day():
    """일주는 60갑자를 하루에 한 칸씩, 끊이지 않고 돈다."""
    base = datetime(1999, 3, 1, 12)
    previous = None
    for offset in range(70):
        saju = build_saju(base + timedelta(days=offset), True, basis=TimeBasis.STANDARD)
        index = saju.day.sexagenary_index
        if previous is not None:
            assert index == (previous + 1) % 60
        previous = index


def test_year_changes_at_ipchun_not_new_year():
    """양력 1월 1일에는 연주가 바뀌지 않는다."""
    before = build_saju(datetime(1999, 12, 31, 12), True, basis=TimeBasis.STANDARD)
    after = build_saju(datetime(2000, 1, 1, 12), True, basis=TimeBasis.STANDARD)
    assert before.year.ganzhi == after.year.ganzhi == "기묘"

    # 입춘(2000-02-04 20:40 KST)을 사이에 두고서야 바뀐다
    pre = build_saju(datetime(2000, 2, 4, 12), True, basis=TimeBasis.STANDARD)
    post = build_saju(datetime(2000, 2, 5, 12), True, basis=TimeBasis.STANDARD)
    assert pre.year.ganzhi == "기묘"
    assert post.year.ganzhi == "경진"


def test_month_changes_at_jie_boundary():
    pre = build_saju(datetime(2024, 8, 7, 8, 0), True, basis=TimeBasis.STANDARD)
    post = build_saju(datetime(2024, 8, 7, 11, 0), True, basis=TimeBasis.STANDARD)
    # 2024 입추는 09:09 KST — 세 시간 사이에 월주가 바뀐다
    assert pre.month.branch == "미"
    assert post.month.branch == "신"


def test_zi_hour_schools_differ_only_after_23():
    birth = datetime(1975, 12, 31, 23, 45)
    strict = build_saju(birth, True, basis=TimeBasis.STANDARD, late_zi_next_day=True)
    lenient = build_saju(birth, True, basis=TimeBasis.STANDARD, late_zi_next_day=False)
    assert strict.day.ganzhi != lenient.day.ganzhi
    assert strict.day.sexagenary_index == (lenient.day.sexagenary_index + 1) % 60

    early = datetime(1975, 12, 31, 22, 30)
    assert (
        build_saju(early, True, basis=TimeBasis.STANDARD, late_zi_next_day=True).day.ganzhi
        == build_saju(early, True, basis=TimeBasis.STANDARD, late_zi_next_day=False).day.ganzhi
    )


def test_hour_branch_covers_two_hours_each():
    """자시는 23~01시, 나머지는 두 시간씩 끊긴다."""
    seen: dict[str, list[int]] = {}
    for hour in range(24):
        saju = build_saju(
            datetime(2001, 6, 10, hour, 30), True, basis=TimeBasis.STANDARD
        )
        seen.setdefault(saju.hour.branch, []).append(hour)
    assert len(seen) == 12
    assert sorted(seen["자"]) == [23, 0] or sorted(seen["자"]) == [0, 23]


def test_luck_direction_follows_yang_male_yin_female_rule():
    # 1990 경오년 = 양년. 남자는 순행, 여자는 역행.
    birth = datetime(1990, 5, 15, 10, 30)
    assert build_saju(birth, True, basis=TimeBasis.STANDARD).luck_forward is True
    assert build_saju(birth, False, basis=TimeBasis.STANDARD).luck_forward is False

    # 1975 을묘년 = 음년. 반대가 된다.
    birth = datetime(1975, 6, 15, 10, 30)
    assert build_saju(birth, True, basis=TimeBasis.STANDARD).luck_forward is False
    assert build_saju(birth, False, basis=TimeBasis.STANDARD).luck_forward is True


def test_luck_pillars_step_from_month_pillar():
    saju = build_saju(datetime(1990, 5, 15, 10, 30), True, basis=TimeBasis.STANDARD)
    assert saju.luck_forward
    expected = saju.month.sexagenary_index
    for lp in saju.luck_pillars:
        expected = (expected + 1) % 60
        assert lp.pillar.sexagenary_index == expected
    assert saju.luck_pillars[0].start_age == pytest.approx(saju.luck_start_age)


def test_luck_start_age_is_within_a_decade():
    for year in range(1960, 2010, 7):
        saju = build_saju(datetime(year, 6, 15, 12), True, basis=TimeBasis.STANDARD)
        assert 0 <= saju.luck_start_age <= 10.5


def test_unknown_hour_leaves_three_pillars():
    saju = build_saju(datetime(1990, 5, 15, 12), True, hour_known=False)
    assert saju.hour is None
    assert saju.has_hour is False
    assert len(saju.pillars) == 3
    assert any("시주" in w for w in saju.warnings)


def test_borderline_birth_raises_warning():
    """2024 입추 절입(09:09 KST) 직후 출생은 경고가 붙어야 한다."""
    saju = build_saju(
        datetime(2024, 8, 7, 9, 20), True, basis=TimeBasis.STANDARD,
        borderline_minutes=30,
    )
    assert any("입추" in w for w in saju.warnings)


def test_summer_time_birth_raises_warning():
    saju = build_saju(datetime(1988, 7, 20, 14, 30), True)
    assert any("서머타임" in w for w in saju.warnings)


def test_sexagenary_index_matches_stem_and_branch():
    for index in range(60):
        stem, branch = index % 10, index % 12
        from saju.pillars import Pillar

        assert Pillar("연주", stem, branch).sexagenary_index == index


def test_pillar_elements_are_consistent():
    saju = build_saju(datetime(1990, 5, 15, 10, 30), True)
    for pillar in saju.pillars:
        assert pillar.stem_element == K.STEM_ELEMENT[pillar.stem_index]
        assert pillar.branch_element == K.BRANCH_ELEMENT[pillar.branch_index]
        assert pillar.hanja[0] == K.STEMS_HANJA[pillar.stem_index]
