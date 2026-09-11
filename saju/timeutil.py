"""출생 시각 보정 — 표준시·서머타임·진태양시.

사주에서 시주(時柱)는 "태양이 남중한 때"를 자시(子時)의 기준으로 잡는다.
그런데 우리가 아는 출생 시각은 시계가 가리킨 값, 곧 표준시다. 둘 사이에는
세 가지 어긋남이 있다.

1. **표준시 변경** — 한국은 동경 127.5°(UTC+8:30)와 135°(UTC+9)를 오갔다.
   1908~1911년과 1954~1961년은 UTC+8:30 이었다.
2. **서머타임** — 1948~1951, 1955~1960, 1987~1988년 여름에 시행됐다.
   이 시기 출생자는 시계가 한 시간 앞당겨져 있어 시주가 통째로 밀릴 수 있다.
3. **경도차와 균시차** — 서울(동경 약 127°)은 표준자오선 135°보다 서쪽이라
   태양이 약 32분 늦게 남중한다. 여기에 지구 공전궤도가 타원이라 생기는
   균시차(-14~+16분)가 더해진다.

1과 2는 `zoneinfo` 의 Asia/Seoul 이력이 정확히 담고 있으므로 그대로 쓴다.
3은 `TimeBasis` 로 어디까지 반영할지 고를 수 있게 했다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from zoneinfo import ZoneInfo

from .solar_terms import julian_day, julian_century, delta_t, _year_of

__all__ = [
    "TimeBasis",
    "Place",
    "PLACES",
    "ResolvedTime",
    "equation_of_time",
    "resolve_birth_time",
]

UTC = timezone.utc


class TimeBasis(Enum):
    """시주를 뽑을 때 어느 시각을 쓸지."""

    STANDARD = "표준시"
    """시계가 가리킨 값 그대로. 표준시·서머타임만 반영한다."""

    LOCAL_MEAN = "지방평균태양시"
    """경도차를 보정한다. 한국 사주에서 가장 널리 쓰는 방식."""

    TRUE_SOLAR = "진태양시"
    """경도차에 균시차까지 보정한다. 천문학적으로 가장 엄밀하다."""


@dataclass(frozen=True)
class Place:
    """출생지 — 경도만 있으면 시각 보정에는 충분하다."""

    name: str
    longitude: float  # 동경 +, 서경 -
    tz: str = "Asia/Seoul"


PLACES: dict[str, Place] = {
    "서울": Place("서울", 126.978),
    "인천": Place("인천", 126.705),
    "수원": Place("수원", 127.009),
    "춘천": Place("춘천", 127.730),
    "강릉": Place("강릉", 128.896),
    "대전": Place("대전", 127.385),
    "청주": Place("청주", 127.489),
    "전주": Place("전주", 127.148),
    "광주": Place("광주", 126.852),
    "목포": Place("목포", 126.392),
    "대구": Place("대구", 128.601),
    "부산": Place("부산", 129.075),
    "울산": Place("울산", 129.311),
    "포항": Place("포항", 129.365),
    "제주": Place("제주", 126.531),
    "평양": Place("평양", 125.738),
    "도쿄": Place("도쿄", 139.692, "Asia/Tokyo"),
    "베이징": Place("베이징", 116.407, "Asia/Shanghai"),
    "로스앤젤레스": Place("로스앤젤레스", -118.244, "America/Los_Angeles"),
    "뉴욕": Place("뉴욕", -74.006, "America/New_York"),
}


def equation_of_time(jd_ut: float) -> float:
    """균시차(분). 진태양시 - 평균태양시.

    Meeus, *Astronomical Algorithms* 28장. 값의 범위는 대략 -14 ~ +16분이다.
    """
    t = julian_century(jd_ut + delta_t(_year_of(jd_ut)) / 86400.0)

    # 태양 기하 평균 황경과 평균 근점이각
    l0 = (280.4664567 + 360007.6982779 * (t / 10) + 0.03032028 * (t / 10) ** 2) % 360
    m = math.radians(357.52911 + 35999.05029 * t - 0.0001537 * t * t)
    e = 0.016708634 - 0.000042037 * t - 0.0000001267 * t * t  # 궤도 이심률

    # 황도경사의 반각 탄젠트 제곱
    eps = math.radians(
        (23 * 3600 + 26 * 60 + 21.448 - 46.8150 * t - 0.00059 * t * t) / 3600
    )
    y = math.tan(eps / 2) ** 2

    l0r = math.radians(l0)
    eot_rad = (
        y * math.sin(2 * l0r)
        - 2 * e * math.sin(m)
        + 4 * e * y * math.sin(m) * math.cos(2 * l0r)
        - 0.5 * y * y * math.sin(4 * l0r)
        - 1.25 * e * e * math.sin(2 * m)
    )
    return math.degrees(eot_rad) * 4  # 1도 = 4분


@dataclass(frozen=True)
class ResolvedTime:
    """보정을 마친 출생 시각."""

    wall: datetime          # 입력한 시계 시각 (tz 포함)
    utc: datetime           # 세계시
    solar: datetime         # 시주 판정에 쓸 태양시
    basis: TimeBasis
    place: Place
    utc_offset_minutes: int
    dst_active: bool
    longitude_shift_minutes: float
    equation_of_time_minutes: float

    @property
    def total_shift_minutes(self) -> float:
        """시계 시각 대비 태양시가 얼마나 밀렸는지(분)."""
        return (self.solar - self.wall.replace(tzinfo=None)).total_seconds() / 60

    def describe(self) -> list[str]:
        """어떤 보정이 적용됐는지 사람이 읽을 수 있게 설명한다."""
        lines = [
            f"입력 시각   {self.wall:%Y-%m-%d %H:%M} ({self.place.name}, "
            f"UTC{self.utc_offset_minutes // 60:+d}:{abs(self.utc_offset_minutes) % 60:02d})"
        ]
        if self.dst_active:
            lines.append("서머타임    시행 중 — 시계가 1시간 앞당겨진 시기입니다")
        if self.basis is not TimeBasis.STANDARD:
            lines.append(
                f"경도 보정   {self.longitude_shift_minutes:+.1f}분 "
                f"(동경 {self.place.longitude:.2f}°)"
            )
        if self.basis is TimeBasis.TRUE_SOLAR:
            lines.append(f"균시차      {self.equation_of_time_minutes:+.1f}분")
        lines.append(f"적용 기준   {self.basis.value} → {self.solar:%Y-%m-%d %H:%M}")
        return lines


def resolve_birth_time(
    wall_time: datetime,
    place: Place | str = "서울",
    basis: TimeBasis = TimeBasis.LOCAL_MEAN,
) -> ResolvedTime:
    """시계 시각을 사주 계산에 쓸 태양시로 바꾼다.

    Args:
        wall_time: 출생 증명서에 적힌 그대로의 시각 (tz 없이 넘기면 출생지 기준).
        place: `Place` 또는 `PLACES` 의 키.
        basis: 어디까지 보정할지.
    """
    if isinstance(place, str):
        if place not in PLACES:
            raise KeyError(
                f"모르는 지역입니다: {place!r}. "
                f"PLACES 에 등록된 곳: {', '.join(PLACES)}"
            )
        place = PLACES[place]

    tz = ZoneInfo(place.tz)
    local = wall_time if wall_time.tzinfo is not None else wall_time.replace(tzinfo=tz)
    local = local.astimezone(tz)

    offset = local.utcoffset() or timedelta(0)
    dst = bool(local.dst())
    utc = local.astimezone(UTC)

    # 표준자오선과 실제 경도의 차이. 서머타임 중에는 표준자오선이 아니라
    # '서머타임을 뺀' 본래 표준자오선을 기준으로 삼아야 한다.
    base_offset = offset - (local.dst() or timedelta(0))
    standard_meridian = base_offset.total_seconds() / 3600 * 15
    lon_shift = (place.longitude - standard_meridian) * 4  # 1도 = 4분

    eot = equation_of_time(julian_day(utc))

    shift = 0.0
    if basis is not TimeBasis.STANDARD:
        shift += lon_shift
        # 서머타임이 걸려 있으면 시계가 앞당겨진 만큼 되돌린다.
        shift -= (local.dst() or timedelta(0)).total_seconds() / 60
    if basis is TimeBasis.TRUE_SOLAR:
        shift += eot

    solar = local.replace(tzinfo=None) + timedelta(minutes=shift)

    return ResolvedTime(
        wall=local,
        utc=utc,
        solar=solar,
        basis=basis,
        place=place,
        utc_offset_minutes=int(offset.total_seconds() // 60),
        dst_active=dst,
        longitude_shift_minutes=lon_shift,
        equation_of_time_minutes=eot,
    )
