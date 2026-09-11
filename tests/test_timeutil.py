"""시각 보정 검증 — 표준시 이력·서머타임·경도·균시차."""

from __future__ import annotations

from datetime import datetime

import pytest

from saju.solar_terms import julian_day
from saju.timeutil import (
    PLACES,
    TimeBasis,
    equation_of_time,
    resolve_birth_time,
)


def test_seoul_longitude_shift_is_about_32_minutes():
    """서울은 표준자오선 135°보다 8° 서쪽이라 태양이 32분 늦게 남중한다."""
    r = resolve_birth_time(datetime(1995, 6, 15, 12), "서울", TimeBasis.LOCAL_MEAN)
    assert r.longitude_shift_minutes == pytest.approx(-32.1, abs=0.2)
    assert r.solar.hour == 11 and r.solar.minute == pytest.approx(27, abs=1)


def test_busan_is_less_shifted_than_seoul():
    seoul = resolve_birth_time(datetime(1995, 6, 15, 12), "서울", TimeBasis.LOCAL_MEAN)
    busan = resolve_birth_time(datetime(1995, 6, 15, 12), "부산", TimeBasis.LOCAL_MEAN)
    assert busan.solar > seoul.solar        # 동쪽일수록 태양이 일찍 남중한다
    assert abs(busan.longitude_shift_minutes) < abs(seoul.longitude_shift_minutes)


def test_historic_half_hour_offset_is_applied():
    """1954~1961년 한국 표준시는 UTC+8:30(동경 127.5°)이었다."""
    r = resolve_birth_time(datetime(1958, 3, 10, 14, 30), "서울", TimeBasis.LOCAL_MEAN)
    assert r.utc_offset_minutes == 510      # 8시간 30분
    # 표준자오선이 127.5° 라 서울과의 차이가 2분밖에 안 된다
    assert r.longitude_shift_minutes == pytest.approx(-2.1, abs=0.3)


def test_summer_time_is_detected_and_unwound():
    r = resolve_birth_time(datetime(1988, 7, 20, 14, 30), "서울", TimeBasis.LOCAL_MEAN)
    assert r.dst_active is True
    assert r.utc_offset_minutes == 600      # UTC+10
    # 서머타임 한 시간과 경도 32분이 함께 빠진다
    assert r.total_shift_minutes == pytest.approx(-92.1, abs=0.3)


def test_no_summer_time_outside_those_years():
    r = resolve_birth_time(datetime(1995, 7, 20, 14, 30), "서울", TimeBasis.LOCAL_MEAN)
    assert r.dst_active is False
    assert r.total_shift_minutes == pytest.approx(-32.1, abs=0.3)


def test_standard_basis_leaves_clock_time_alone():
    r = resolve_birth_time(datetime(1995, 6, 15, 12), "서울", TimeBasis.STANDARD)
    assert r.solar == datetime(1995, 6, 15, 12)


def test_true_solar_adds_equation_of_time():
    local = resolve_birth_time(datetime(1995, 11, 1, 12), "서울", TimeBasis.LOCAL_MEAN)
    true = resolve_birth_time(datetime(1995, 11, 1, 12), "서울", TimeBasis.TRUE_SOLAR)
    delta = (true.solar - local.solar).total_seconds() / 60
    assert delta == pytest.approx(true.equation_of_time_minutes, abs=0.1)
    assert delta > 10        # 11월 초는 균시차가 +16분 부근이다


def test_equation_of_time_stays_in_known_range():
    """균시차는 연중 대략 -14.2 ~ +16.4분 사이를 오간다."""
    values = [
        equation_of_time(julian_day(datetime(2021, month, day, 12)))
        for month in range(1, 13)
        for day in (1, 11, 21)
    ]
    assert -14.5 < min(values) < -13.5
    assert 15.5 < max(values) < 16.9


def test_unknown_place_is_rejected():
    with pytest.raises(KeyError):
        resolve_birth_time(datetime(1995, 6, 15, 12), "아틀란티스")


def test_every_registered_place_resolves():
    for name in PLACES:
        r = resolve_birth_time(datetime(1995, 6, 15, 12), name, TimeBasis.TRUE_SOLAR)
        assert r.place.name == name
        assert r.describe()
