"""사주(四柱) 산출 — 연월일시 네 기둥의 간지를 구한다.

경계가 어디인지가 이 모듈의 전부라고 해도 좋다.

* **연주(年柱)** 는 1월 1일이 아니라 입춘에 바뀐다.
* **월주(月柱)** 는 매달 1일이 아니라 절(節)에 바뀐다.
* **일주(日柱)** 는 자정이 아니라 자시가 시작되는 23시에 바뀐다(설이 갈린다).
* **시주(時柱)** 는 시계 시각이 아니라 태양시로 판정한다.

연·월은 절기라는 '천문 사건'이 기준이므로 세계시 순간끼리 비교하고,
일·시는 그 지역의 하루가 기준이므로 보정된 태양시로 판정한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from . import constants as K
from .solar_terms import next_jie, previous_jie, solar_term_at
from .timeutil import Place, ResolvedTime, TimeBasis, resolve_birth_time

__all__ = ["Pillar", "FourPillars", "LuckPillar", "build_saju", "ZI_HOUR_SCHOOLS"]

UTC = timezone.utc

# 일주가 언제 바뀌는지에 대한 두 학설
ZI_HOUR_SCHOOLS = {
    "야자시": "23시부터 자시로 보되 일주는 자정에 바꾼다 (야자시설)",
    "정자시": "23시부터 자시이자 다음 날로 본다 (정자시설, 기본값)",
}

# 일진 기준점: 2000-01-07 은 갑자일. 이 날의 율리우스일수는 2451551 이다.
_DAY_ANCHOR_JDN = 2451551


def _jdn(year: int, month: int, day: int) -> int:
    """그레고리력 날짜의 율리우스일수(정오 기준 정수)."""
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


# --------------------------------------------------------------------------
# 기둥
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Pillar:
    """간지 한 쌍 — 천간 하나와 지지 하나."""

    label: str
    stem_index: int
    branch_index: int

    @property
    def stem(self) -> str:
        return K.STEMS[self.stem_index]

    @property
    def branch(self) -> str:
        return K.BRANCHES[self.branch_index]

    @property
    def ganzhi(self) -> str:
        return self.stem + self.branch

    @property
    def hanja(self) -> str:
        return K.STEMS_HANJA[self.stem_index] + K.BRANCHES_HANJA[self.branch_index]

    @property
    def stem_element(self) -> str:
        return K.STEM_ELEMENT[self.stem_index]

    @property
    def branch_element(self) -> str:
        return K.BRANCH_ELEMENT[self.branch_index]

    @property
    def is_yang(self) -> bool:
        return K.STEM_YANG[self.stem_index]

    @property
    def sexagenary_index(self) -> int:
        """60갑자 중 몇 번째인지 (0 = 갑자)."""
        return (self.stem_index * 6 - self.branch_index * 5) % 60

    def __str__(self) -> str:  # pragma: no cover - 표시용
        return f"{self.ganzhi}({self.hanja})"


@dataclass(frozen=True)
class LuckPillar:
    """대운(大運) 한 구간."""

    start_age: float
    pillar: Pillar

    @property
    def end_age(self) -> float:
        return self.start_age + 10


@dataclass
class FourPillars:
    """사주 한 벌과 계산 과정에서 나온 부가 정보."""

    year: Pillar
    month: Pillar
    day: Pillar
    hour: Pillar | None

    time_info: ResolvedTime
    is_male: bool
    luck_forward: bool
    luck_start_age: float
    luck_pillars: list[LuckPillar] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # --- 자주 쓰는 접근자 -------------------------------------------------

    @property
    def day_master(self) -> str:
        """일간(日干) — 사주 해석의 기준점이 되는 '나'."""
        return self.day.stem

    @property
    def day_master_element(self) -> str:
        return self.day.stem_element

    @property
    def pillars(self) -> list[Pillar]:
        """시주가 없으면 세 기둥만 돌려준다."""
        return [p for p in (self.year, self.month, self.day, self.hour) if p is not None]

    @property
    def has_hour(self) -> bool:
        return self.hour is not None

    @property
    def month_branch(self) -> str:
        return self.month.branch

    def luck_at(self, age: float) -> LuckPillar | None:
        """만 `age` 세에 지나고 있는 대운."""
        for lp in self.luck_pillars:
            if lp.start_age <= age < lp.end_age:
                return lp
        return None

    def grid(self) -> str:
        """사주 원국을 표로 그린다 (시-일-월-연 순, 전통 배열)."""
        cols = [self.hour, self.day, self.month, self.year]
        heads = ["시주", "일주", "월주", "연주"]
        line1 = line2 = line3 = ""
        for head, p in zip(heads, cols):
            line1 += f"{head:^8}"
            line2 += f"{(p.stem + '(' + K.STEMS_HANJA[p.stem_index] + ')') if p else '- ':^8}"
            line3 += f"{(p.branch + '(' + K.BRANCHES_HANJA[p.branch_index] + ')') if p else '- ':^8}"
        return "\n".join([line1, line2, line3])


# --------------------------------------------------------------------------
# 각 기둥 계산
# --------------------------------------------------------------------------

def _year_pillar(birth_utc: datetime) -> tuple[Pillar, int]:
    """연주 — 입춘을 새해로 삼는다. (기둥, 사주상 연도) 를 돌려준다.

    판정은 '그 해 입춘을 지났는가' 하나로 끝난다. 1~2월 초에 태어났다면
    아직 입춘 전이라 사주로는 전년도 사람이다.
    """
    lichun = solar_term_at(birth_utc.year, 0).moment_utc
    saju_year = birth_utc.year if birth_utc >= lichun else birth_utc.year - 1
    stem = (saju_year - 4) % 10
    branch = (saju_year - 4) % 12
    return Pillar("연주", stem, branch), saju_year


def _month_pillar(birth_utc: datetime, year_stem_index: int) -> Pillar:
    """월주 — 절입을 경계로, 연간에 따라 월간이 정해진다(년상기월법)."""
    jie = previous_jie(birth_utc)
    branch = K.BRANCHES.index(jie.month_branch)
    # 인월(寅月)이 한 해의 첫 달. 갑·기년의 인월은 병인(丙寅)에서 시작한다.
    order = (branch - 2) % 12
    stem = (year_stem_index * 2 + 2 + order) % 10
    return Pillar("월주", stem, branch)


def _day_pillar(solar: datetime, late_zi_next_day: bool) -> Pillar:
    """일주 — 60갑자가 하루씩 끊이지 않고 돌아간다."""
    jdn = _jdn(solar.year, solar.month, solar.day)
    if late_zi_next_day and solar.hour >= 23:
        jdn += 1
    index = (jdn - _DAY_ANCHOR_JDN) % 60
    return Pillar("일주", index % 10, index % 12)


def _hour_pillar(solar: datetime, day_stem_index: int) -> Pillar:
    """시주 — 두 시간이 한 지지. 일간에 따라 시간(時干)이 정해진다(일상기시법)."""
    branch = ((solar.hour + 1) // 2) % 12
    stem = (day_stem_index * 2 + branch) % 10
    return Pillar("시주", stem, branch)


# --------------------------------------------------------------------------
# 대운
# --------------------------------------------------------------------------

def _luck_cycle(
    birth_utc: datetime,
    year_pillar: Pillar,
    month_pillar: Pillar,
    is_male: bool,
    count: int,
) -> tuple[bool, float, list[LuckPillar]]:
    """대운의 방향·시작 나이·간지 목록.

    양년생 남자와 음년생 여자는 순행(順行), 나머지는 역행(逆行)한다.
    시작 나이는 절입까지의 날수를 3으로 나눠 구한다(3일 = 1년).
    """
    forward = year_pillar.is_yang == is_male

    if forward:
        days = (next_jie(birth_utc).moment_utc - birth_utc).total_seconds() / 86400
    else:
        days = (birth_utc - previous_jie(birth_utc).moment_utc).total_seconds() / 86400
    start_age = round(days / 3, 2)

    pillars: list[LuckPillar] = []
    base = month_pillar.sexagenary_index
    for i in range(1, count + 1):
        idx = (base + i) % 60 if forward else (base - i) % 60
        # 60갑자 인덱스 → 천간·지지 인덱스
        pillars.append(
            LuckPillar(
                start_age=round(start_age + (i - 1) * 10, 2),
                pillar=Pillar(f"{i}대운", idx % 10, idx % 12),
            )
        )
    return forward, start_age, pillars


# --------------------------------------------------------------------------
# 진입점
# --------------------------------------------------------------------------

def build_saju(
    birth: datetime,
    is_male: bool,
    place: Place | str = "서울",
    basis: TimeBasis = TimeBasis.LOCAL_MEAN,
    hour_known: bool = True,
    late_zi_next_day: bool = True,
    luck_count: int = 10,
    borderline_minutes: int = 30,
) -> FourPillars:
    """생년월일시로 사주를 세운다.

    Args:
        birth: 출생 시각 (시계 시각 그대로).
        is_male: 대운 방향 판정에 쓴다.
        place: 출생지. 경도 보정에 쓴다.
        basis: 시각 보정 수준. 기본은 지방평균태양시.
        hour_known: 출생 시각을 모르면 False — 시주를 비운다.
        late_zi_next_day: 23시 이후를 다음 날로 볼지(정자시설). 기본 True.
        luck_count: 뽑을 대운 개수.
        borderline_minutes: 절입에 이만큼 가까우면 경고를 단다.

    Returns:
        `FourPillars`.
    """
    resolved = resolve_birth_time(birth, place, basis)
    birth_utc = resolved.utc
    solar = resolved.solar

    year_p, saju_year = _year_pillar(birth_utc)
    month_p = _month_pillar(birth_utc, year_p.stem_index)
    day_p = _day_pillar(solar, late_zi_next_day)
    hour_p = _hour_pillar(solar, day_p.stem_index) if hour_known else None

    forward, start_age, luck = _luck_cycle(
        birth_utc, year_p, month_p, is_male, luck_count
    )

    warnings: list[str] = []

    # 절입 경계 경고 — 여기 걸리면 월주(때로는 연주)가 통째로 달라질 수 있다.
    prev_j, next_j = previous_jie(birth_utc), next_jie(birth_utc)
    to_prev = (birth_utc - prev_j.moment_utc).total_seconds() / 60
    to_next = (next_j.moment_utc - birth_utc).total_seconds() / 60
    if to_prev < borderline_minutes:
        warnings.append(
            f"{prev_j.name} 절입({prev_j.moment_utc.astimezone(resolved.wall.tzinfo):%m-%d %H:%M}) "
            f"{to_prev:.0f}분 뒤에 태어났습니다. 월주가 갈리는 경계이니 만세력으로 확인하세요."
        )
    if to_next < borderline_minutes:
        warnings.append(
            f"{next_j.name} 절입({next_j.moment_utc.astimezone(resolved.wall.tzinfo):%m-%d %H:%M}) "
            f"{to_next:.0f}분 전에 태어났습니다. 월주가 갈리는 경계이니 만세력으로 확인하세요."
        )

    # 자시 경계 경고
    if hour_known and (solar.hour == 23 or solar.hour == 0):
        warnings.append(
            "자시(23~01시) 출생입니다. 일주를 언제 넘길지 학설이 갈리므로 "
            f"현재 '{'정자시' if late_zi_next_day else '야자시'}설'로 계산했습니다."
        )

    if resolved.dst_active:
        warnings.append(
            "서머타임 시행 기간에 태어났습니다. 출생 기록의 시각이 이미 "
            "표준시로 환산된 값이라면 결과가 한 시간 밀릴 수 있습니다."
        )

    if not hour_known:
        warnings.append("출생 시각을 몰라 시주를 비웠습니다. 해석의 정밀도가 떨어집니다.")

    return FourPillars(
        year=year_p,
        month=month_p,
        day=day_p,
        hour=hour_p,
        time_info=resolved,
        is_male=is_male,
        luck_forward=forward,
        luck_start_age=start_age,
        luck_pillars=luck,
        warnings=warnings,
    )
