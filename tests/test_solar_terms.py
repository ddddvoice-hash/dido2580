"""절기 계산 검증."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import saju.solar_terms as st
from saju.solar_terms import (
    BACKEND,
    MONTH_JIE,
    delta_t,
    from_julian_day,
    julian_day,
    month_jie_boundaries,
    next_jie,
    previous_jie,
    solar_longitude_at,
    solar_term_at,
)

KST = timezone(timedelta(hours=9))
UTC = timezone.utc


def test_julian_day_roundtrip():
    for dt in [
        datetime(1899, 12, 31, 12, tzinfo=UTC),
        datetime(1988, 7, 14, 3, 25, tzinfo=UTC),
        datetime(2000, 1, 1, 12, tzinfo=UTC),
        datetime(2046, 11, 30, 23, 59, tzinfo=UTC),
    ]:
        assert from_julian_day(julian_day(dt)) == dt


def test_julian_day_known_epoch():
    """J2000.0 = 2000-01-01 12:00 UT 의 율리우스일은 2451545.0 이다."""
    assert julian_day(datetime(2000, 1, 1, 12, tzinfo=UTC)) == pytest.approx(2451545.0)


def test_solar_longitude_advances_about_one_degree_per_day():
    jd = julian_day(datetime(2020, 6, 1, tzinfo=UTC))
    step = solar_longitude_at(jd + 1) - solar_longitude_at(jd)
    assert 0.9 < step < 1.05


def test_month_jie_longitudes_are_exact():
    """각 절의 절입 순간에는 태양 황경이 정확히 목표값이어야 한다."""
    for i, (_, lon, _, _, _) in enumerate(MONTH_JIE):
        term = solar_term_at(2015, i)
        got = solar_longitude_at(julian_day(term.moment_utc))
        assert abs((got - lon + 180) % 360 - 180) < 1e-4


@pytest.mark.parametrize(
    "year,name,expected_kst",
    [
        # 한국천문연구원 발표 절입 시각 (분 단위)
        (2024, "입춘", "2024-02-04 17:27"),
        (1984, "입춘", "1984-02-05 00:19"),
    ],
)
@pytest.mark.skipif(
    BACKEND != "ephem",
    reason="2분 이내 정확도는 ephem 백엔드의 보증입니다 (pip install ephem)",
)
def test_ipchun_matches_published_times(year, name, expected_kst):
    """입춘 시각이 공식 발표값과 2분 이내로 맞아야 한다."""
    term = solar_term_at(year, 0)
    assert term.name == name
    expected = datetime.strptime(expected_kst, "%Y-%m-%d %H:%M").replace(tzinfo=KST)
    assert abs((term.moment_in(KST) - expected).total_seconds()) <= 120


def test_boundaries_are_ordered_and_cover_twelve_branches():
    terms = month_jie_boundaries(2010)
    assert len(terms) == 12
    assert [t.moment_utc for t in terms] == sorted(t.moment_utc for t in terms)
    assert len({t.month_branch for t in terms}) == 12


def test_previous_and_next_jie_bracket_the_moment():
    moment = datetime(1993, 9, 20, 4, 30, tzinfo=UTC)
    prev, nxt = previous_jie(moment), next_jie(moment)
    assert prev.moment_utc <= moment < nxt.moment_utc
    # 연속한 절은 28~32일 간격이다
    gap = (nxt.moment_utc - prev.moment_utc).days
    assert 28 <= gap <= 32


def test_delta_t_is_positive_and_continuous_in_modern_era():
    values = [delta_t(y) for y in range(1930, 2050)]
    assert all(v > 0 for v in values)
    # 구간 경계에서 튀지 않아야 한다
    assert max(abs(b - a) for a, b in zip(values, values[1:])) < 2.0


@pytest.mark.parametrize(
    "year,index,expected_kst",
    [
        # 회귀 기준선 — ephem 백엔드로 계산해 고정한 값이다.
        # 계산 방식을 바꿨을 때 결과가 흔들리는지 잡아내기 위한 것이다.
        # 허용 오차 15분은 ephem 이 없을 때 쓰는 내장 급수(최대 약 13분 오차)도
        # 통과하도록 잡은 값이다.
        (2000, 0, "2000-02-04 21:40"),
        (1970, 6, "1970-08-08 07:54"),
        (2030, 11, "2030-01-05 16:30"),
    ],
)
def test_solar_terms_match_recorded_baseline(year, index, expected_kst):
    term = solar_term_at(year, index)
    expected = datetime.strptime(expected_kst, "%Y-%m-%d %H:%M").replace(tzinfo=KST)
    assert abs((term.moment_in(KST) - expected).total_seconds()) <= 900


# --------------------------------------------------------------------------
# 내장 급수 백엔드
#
# ephem 이 설치돼 있어도 내장 경로는 늘 검증해야 한다. 설치되지 않은 환경에서
# 쓰이는 코드가 아무도 실행하지 않는 채로 남는 일을 막기 위해서다.
# --------------------------------------------------------------------------

@pytest.fixture
def builtin_backend(monkeypatch):
    """ephem 을 감춰 내장 급수만 쓰게 만든다."""
    monkeypatch.setattr(st, "_ephem", None)
    return st


def test_builtin_backend_produces_sane_terms(builtin_backend):
    term = builtin_backend.solar_term_at(2024, 0)
    assert term.name == "입춘"
    assert term.month_branch == "인"
    # 입춘은 늘 2월 3~5일 사이다
    assert term.moment_in(KST).month == 2
    assert term.moment_in(KST).day in (3, 4, 5)


def test_builtin_backend_stays_within_documented_error(builtin_backend):
    """내장 급수의 절기 시각 오차는 문서에 적은 대로 15분 안쪽이어야 한다."""
    if BACKEND != "ephem":
        pytest.skip("대조할 고정밀 백엔드가 없습니다")
    for year in (1950, 1985, 2010, 2035):
        for index in range(0, 12, 3):
            builtin_backend._ephem = None
            approx = builtin_backend.solar_term_at(year, index).moment_utc
            builtin_backend._ephem = st._ephem_module_for_test
            precise = builtin_backend.solar_term_at(year, index).moment_utc
            gap = abs((approx - precise).total_seconds()) / 60
            assert gap < 15, f"{year} {index}번째 절 오차 {gap:.1f}분"


def test_builtin_longitude_advances_like_the_precise_one(builtin_backend):
    jd = julian_day(datetime(1999, 4, 1, tzinfo=UTC))
    step = builtin_backend.solar_longitude_at(jd + 1) - builtin_backend.solar_longitude_at(jd)
    assert 0.9 < step < 1.05
