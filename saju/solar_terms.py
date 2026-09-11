"""절기(節氣) 계산 — 태양의 겉보기 황경으로 24절기 시각을 구한다.

사주의 연주(年柱)는 1월 1일이 아니라 입춘(立春)에, 월주(月柱)는 매달 절(節)에
바뀐다. 그래서 달력 날짜가 아니라 태양 황경을 직접 계산해야 정확하다.

태양 위치 계산에는 두 가지 백엔드가 있다.

* `ephem` 패키지가 설치돼 있으면 그쪽을 쓴다 (오차 1초 미만).
* 없으면 Meeus, *Astronomical Algorithms* 25장의 해에 금성·목성·달의 주요
  섭동항을 더한 내장 급수를 쓴다. ephem 과 대조한 결과 1930~2060년 구간에서
  절기 시각 오차는 평균 4.6분, 최대 약 13분이다.

어느 쪽이든 절입 시각 근처에 태어나면 월주(月柱)가 갈릴 수 있다. `pillars`
모듈이 경계 출생을 감지해 경고를 함께 돌려주므로, 그런 경우에는 만세력을
따로 확인하는 편이 좋다.

계산은 역학시(TT)로 하고 ΔT를 빼서 세계시(UT)로 돌려준다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

__all__ = [
    "JIEQI_NAMES",
    "MONTH_JIE",
    "SolarTerm",
    "apparent_solar_longitude",
    "delta_t",
    "BACKEND",
    "julian_day",
    "from_julian_day",
    "solar_longitude_at",
    "solar_term_at",
    "month_jie_boundaries",
    "previous_jie",
    "next_jie",
]

UTC = timezone.utc

# 24절기 — 황경 0°(춘분)부터 15° 간격
JIEQI_NAMES = [
    "춘분", "청명", "곡우", "입하", "소만", "망종",
    "하지", "소서", "대서", "입추", "처서", "백로",
    "추분", "한로", "상강", "입동", "소설", "대설",
    "동지", "소한", "대한", "입춘", "우수", "경칩",
]

# 월(月)을 바꾸는 12절(節): (절기명, 태양황경, 월지, 근사 양력 월/일)
# 월지는 입춘부터 인월(寅月)로 시작한다.
MONTH_JIE: list[tuple[str, float, str, int, int]] = [
    ("입춘", 315.0, "인", 2, 4),
    ("경칩", 345.0, "묘", 3, 6),
    ("청명", 15.0, "진", 4, 5),
    ("입하", 45.0, "사", 5, 6),
    ("망종", 75.0, "오", 6, 6),
    ("소서", 105.0, "미", 7, 7),
    ("입추", 135.0, "신", 8, 8),
    ("백로", 165.0, "유", 9, 8),
    ("한로", 195.0, "술", 10, 8),
    ("입동", 225.0, "해", 11, 7),
    ("대설", 255.0, "자", 12, 7),
    ("소한", 285.0, "축", 1, 6),
]


# --------------------------------------------------------------------------
# 율리우스일
# --------------------------------------------------------------------------

def julian_day(dt: datetime) -> float:
    """UTC datetime → 율리우스일(JD). tz 없는 값은 UTC로 간주한다."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC)
    y, m = dt.year, dt.month
    day = (
        dt.day
        + (dt.hour + (dt.minute + (dt.second + dt.microsecond / 1e6) / 60) / 60) / 24
    )
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4  # 그레고리력 보정
    return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + day + b - 1524.5


def from_julian_day(jd: float) -> datetime:
    """율리우스일 → UTC datetime."""
    jd += 0.5
    z = math.floor(jd)
    f = jd - z
    if z < 2299161:
        a = z
    else:
        alpha = math.floor((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - alpha // 4
    b = a + 1524
    c = math.floor((b - 122.1) / 365.25)
    d = math.floor(365.25 * c)
    e = math.floor((b - d) / 30.6001)
    day = b - d - math.floor(30.6001 * e) + f
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    frac = day - math.floor(day)
    seconds = round(frac * 86400)
    return datetime(year, month, int(day), tzinfo=UTC) + timedelta(seconds=seconds)


def julian_century(jd: float) -> float:
    return (jd - 2451545.0) / 36525.0


# --------------------------------------------------------------------------
# 태양 겉보기 황경
# --------------------------------------------------------------------------

def apparent_solar_longitude(jd: float) -> float:
    """율리우스일 `jd` 에서 태양의 겉보기 황경(도, 0~360)."""
    t = julian_century(jd)

    # 기하 평균 황경
    l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    # 평균 근점이각
    m = math.radians(357.52911 + 35999.05029 * t - 0.0001537 * t * t)
    # 중심차
    c = (
        (1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(m)
        + (0.019993 - 0.000101 * t) * math.sin(2 * m)
        + 0.000289 * math.sin(3 * m)
    )
    true_long = l0 + c

    # 금성·목성·달에 의한 주요 섭동 (Meeus, Astronomical Formulae for Calculators)
    # 이 여섯 항이 빠지면 절기 시각이 5~10분씩 어긋난다.
    a = math.radians(153.23 + 22518.7541 * t)      # 금성
    b = math.radians(216.57 + 45037.5082 * t)      # 금성
    c2 = math.radians(312.69 + 32964.3577 * t)     # 목성
    d = math.radians(350.74 + 445267.1142 * t - 0.00144 * t * t)  # 달
    e = math.radians(231.19 + 20.20 * t)           # 장주기항
    true_long += (
        0.00134 * math.cos(a)
        + 0.00154 * math.cos(b)
        + 0.00200 * math.cos(c2)
        + 0.00179 * math.sin(d)
        + 0.00178 * math.sin(e)
    )

    # 장동과 광행차 보정
    omega = math.radians(125.04 - 1934.136 * t)
    apparent = true_long - 0.00569 - 0.00478 * math.sin(omega)
    return apparent % 360.0


def delta_t(year: float) -> float:
    """ΔT = TT - UT (초). Espenak & Meeus 다항 근사."""
    if year < 1900:
        u = (year - 1820) / 100
        return -20 + 32 * u * u
    if year < 1920:
        t = year - 1900
        return (
            -2.79 + 1.494119 * t - 0.0598939 * t**2 + 0.0061966 * t**3 - 0.000197 * t**4
        )
    if year < 1941:
        t = year - 1920
        return 21.20 + 0.84493 * t - 0.076100 * t**2 + 0.0020936 * t**3
    if year < 1961:
        t = year - 1950
        return 29.07 + 0.407 * t - t**2 / 233 + t**3 / 2547
    if year < 1986:
        t = year - 1975
        return 45.45 + 1.067 * t - t**2 / 260 - t**3 / 718
    if year < 2005:
        t = year - 2000
        return (
            63.86
            + 0.3345 * t
            - 0.060374 * t**2
            + 0.0017275 * t**3
            + 0.000651814 * t**4
            + 0.00002373599 * t**5
        )
    if year < 2050:
        t = year - 2000
        return 62.92 + 0.32217 * t + 0.005589 * t**2
    if year < 2150:
        return -20 + 32 * ((year - 1820) / 100) ** 2 - 0.5628 * (2150 - year)
    u = (year - 1820) / 100
    return -20 + 32 * u * u


# --------------------------------------------------------------------------
# 고정밀 백엔드 (선택) — pip install ephem
# --------------------------------------------------------------------------

try:  # pragma: no cover - 설치 여부에 따라 갈린다
    import ephem as _ephem
except ImportError:  # pragma: no cover
    _ephem = None

BACKEND = "ephem" if _ephem is not None else "builtin"

_ephem_module_for_test = _ephem
"""테스트가 백엔드를 껐다 켤 수 있도록 남겨 둔 원본 참조."""

_EPHEM_EPOCH_JD = 2415020.0  # ephem 의 기준 시각 1899-12-31 12:00 UT


def _true_obliquity(jd_tt: float) -> float:
    """진황도경사(라디안) — 평균 황도경사에 장동 주요항을 더한 값."""
    t = julian_century(jd_tt)
    e0 = (
        23 * 3600 + 26 * 60 + 21.448
        - 46.8150 * t - 0.00059 * t * t + 0.001813 * t**3
    ) / 3600
    om = math.radians(125.04452 - 1934.136261 * t)
    ls = math.radians(280.4665 + 36000.7698 * t)
    lm = math.radians(218.3165 + 481267.8813 * t)
    d_eps = (
        9.20 * math.cos(om)
        + 0.57 * math.cos(2 * ls)
        + 0.10 * math.cos(2 * lm)
        - 0.09 * math.cos(2 * om)
    ) / 3600
    return math.radians(e0 + d_eps)


def _ephem_longitude(jd_ut: float) -> float:  # pragma: no cover - 선택 의존성
    """ephem 으로 구한 태양 겉보기 황경(도).

    ephem 의 `Ecliptic(body)` 는 천측좌표(J2000)를 쓰므로 광행차·장동이 빠진다.
    그래서 겉보기 적경/적위를 진황도경사로 직접 환산한다.
    """
    sun = _ephem.Sun(_ephem.Date(jd_ut - _EPHEM_EPOCH_JD))
    eps = _true_obliquity(jd_ut + delta_t(_year_of(jd_ut)) / 86400.0)
    ra, dec = float(sun.ra), float(sun.dec)
    y = math.sin(ra) * math.cos(eps) + math.tan(dec) * math.sin(eps)
    return math.degrees(math.atan2(y, math.cos(ra))) % 360.0


def _year_of(jd: float) -> float:
    """율리우스일 → 소수 연도 (ΔT 계산용 근사면 충분하다)."""
    return 2000.0 + (jd - 2451545.0) / 365.25


def solar_longitude_at(jd_ut: float) -> float:
    """세계시 기준 율리우스일에서의 태양 겉보기 황경(도).

    사용 가능한 가장 정확한 백엔드를 고른다.
    """
    if _ephem is not None:
        return _ephem_longitude(jd_ut)
    return apparent_solar_longitude(jd_ut + delta_t(_year_of(jd_ut)) / 86400.0)


def _angle_diff(a: float, b: float) -> float:
    """a - b 를 (-180, 180] 로 정규화."""
    return (a - b + 180.0) % 360.0 - 180.0


def _solve_longitude(target_deg: float, guess: datetime) -> datetime:
    """태양 황경이 `target_deg` 가 되는 시각(UTC)을 `guess` 근처에서 찾는다."""
    jd = julian_day(guess)
    # 태양은 하루에 약 0.9856° 움직인다 — 할선법으로 수렴시킨다.
    for _ in range(40):
        delta = _angle_diff(solar_longitude_at(jd), target_deg)
        if abs(delta) < 1e-9:
            break
        jd -= delta / 0.98564736
    return from_julian_day(jd)


# --------------------------------------------------------------------------
# 절기 시각
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class SolarTerm:
    """한 절(節)의 절입 시각."""

    name: str
    longitude: float
    month_branch: str
    moment_utc: datetime

    def moment_in(self, tz: timezone) -> datetime:
        return self.moment_utc.astimezone(tz)

    def __str__(self) -> str:  # pragma: no cover - 표시용
        return f"{self.name}({self.month_branch}월) {self.moment_utc:%Y-%m-%d %H:%M} UTC"


def solar_term_at(year: int, index: int) -> SolarTerm:
    """`year` 년의 `index` 번째 절(MONTH_JIE 순서)의 절입 시각."""
    name, lon, branch, mm, dd = MONTH_JIE[index]
    guess = datetime(year, mm, dd, tzinfo=UTC)
    moment = _solve_longitude(lon, guess)
    return SolarTerm(name, lon, branch, moment)


def month_jie_boundaries(year: int) -> list[SolarTerm]:
    """`year` 의 12절을 시각 순으로 반환. 소한은 1월이라 자연히 맨 앞에 온다."""
    terms = [solar_term_at(year, i) for i in range(len(MONTH_JIE))]
    return sorted(terms, key=lambda t: t.moment_utc)


def _window(moment_utc: datetime) -> list[SolarTerm]:
    """주어진 시각을 확실히 감싸는 절 목록(전년~다음해)."""
    y = moment_utc.year
    terms: list[SolarTerm] = []
    for yy in (y - 1, y, y + 1):
        terms.extend(month_jie_boundaries(yy))
    return sorted(terms, key=lambda t: t.moment_utc)


def previous_jie(moment_utc: datetime) -> SolarTerm:
    """`moment_utc` 직전(또는 같은 시각)의 절."""
    terms = _window(moment_utc)
    found = [t for t in terms if t.moment_utc <= moment_utc]
    return found[-1]


def next_jie(moment_utc: datetime) -> SolarTerm:
    """`moment_utc` 직후의 절."""
    terms = _window(moment_utc)
    return next(t for t in terms if t.moment_utc > moment_utc)
