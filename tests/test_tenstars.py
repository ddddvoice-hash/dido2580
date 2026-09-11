"""십성·십이운성·오행 세력 검증."""

from __future__ import annotations

from datetime import datetime

import pytest

from saju import constants as K
from saju.pillars import build_saju
from saju.tenstars import (
    Weights,
    element_profile,
    ten_god_of,
    ten_god_profile,
    twelve_stage,
)


def test_each_day_master_sees_all_ten_gods_exactly_once():
    for dm in K.STEMS:
        gods = [ten_god_of(dm, other) for other in K.STEMS]
        assert sorted(gods) == sorted(K.TEN_GODS)


def test_same_stem_is_bigyeon():
    for dm in K.STEMS:
        assert ten_god_of(dm, dm) == "비견"


@pytest.mark.parametrize(
    "day_master,other,expected",
    [
        ("갑", "병", "식신"),   # 목이 화를 생, 양-양
        ("갑", "정", "상관"),   # 목이 화를 생, 양-음
        ("갑", "무", "편재"),   # 목이 토를 극, 양-양
        ("갑", "기", "정재"),   # 목이 토를 극, 양-음
        ("갑", "경", "편관"),   # 금이 목을 극, 양-양
        ("갑", "신", "정관"),   # 금이 목을 극, 양-음
        ("갑", "임", "편인"),   # 수가 목을 생, 양-양
        ("갑", "계", "정인"),   # 수가 목을 생, 양-음
        ("갑", "을", "겁재"),
    ],
)
def test_ten_god_table(day_master, other, expected):
    assert ten_god_of(day_master, other) == expected


def test_twelve_stages_hit_each_branch_once():
    for dm in K.STEMS:
        stages = [twelve_stage(dm, b) for b in K.BRANCHES]
        assert sorted(stages) == sorted(K.TWELVE_STAGES)


@pytest.mark.parametrize(
    "day_master,branch",
    [("갑", "인"), ("을", "묘"), ("병", "사"), ("정", "오"), ("무", "사"),
     ("기", "오"), ("경", "신"), ("신", "유"), ("임", "해"), ("계", "자")],
)
def test_geonrok_positions(day_master, branch):
    """건록(建祿)은 일간이 가장 힘을 받는 자리다."""
    assert twelve_stage(day_master, branch) == "건록"


def test_changsaeng_matches_table():
    for dm, index in K.CHANGSAENG_BRANCH.items():
        assert twelve_stage(dm, K.BRANCHES[index]) == "장생"


def test_hidden_stem_weights_sum_to_one():
    for branch, hidden in K.HIDDEN_STEMS.items():
        assert sum(w for _, w in hidden) == pytest.approx(1.0)
        assert all(stem in K.STEMS for stem, _ in hidden)


def test_element_percentages_sum_to_hundred():
    saju = build_saju(datetime(1990, 5, 15, 10, 30), True)
    profile = element_profile(saju)
    assert sum(profile.percent.values()) == pytest.approx(100.0, abs=0.3)
    assert set(profile.percent) == set(K.ELEMENTS)


def test_strength_ratio_is_a_fraction():
    for year in range(1960, 2010, 6):
        saju = build_saju(datetime(year, 6, 15, 12), True)
        profile = element_profile(saju)
        assert 0.0 <= profile.strength_ratio <= 1.0
        assert profile.strength_label in {
            "신강", "중화신강", "중화", "중화신약", "신약"
        }
        assert profile.is_strong == (profile.strength_ratio >= 0.5)


def test_season_factor_favours_the_ruling_element():
    # 자월(子月)은 한겨울이라 수가 가장 왕성하고 토가 가장 약하다
    assert K.season_factor("수", "자") == max(
        K.season_factor(e, "자") for e in K.ELEMENTS
    )
    assert K.season_factor("화", "오") > K.season_factor("수", "오")


def test_ten_god_groups_sum_to_hundred():
    saju = build_saju(datetime(1977, 9, 2, 18, 10), False)
    profile = ten_god_profile(saju)
    assert sum(profile.group_percent.values()) == pytest.approx(100.0, abs=0.3)
    assert set(profile.group_percent) == set(K.GROUPS)


def test_day_master_itself_is_not_counted():
    """일간은 '나'이므로 비견으로 세지 않는다."""
    saju = build_saju(datetime(1990, 5, 15, 10, 30), True)
    profile = ten_god_profile(saju)
    # 일간 자리가 비견으로 잡혔다면 '일간' 이 위치 목록에 들어갔을 것이다
    assert "일간" not in profile.placements.get("비견", [])


def test_weights_are_configurable():
    saju = build_saju(datetime(1990, 5, 15, 10, 30), True)
    flat = Weights(
        year_stem=1, month_stem=1, day_stem=1, hour_stem=1,
        year_branch=1, month_branch=1, day_branch=1, hour_branch=1,
        apply_season=False,
    )
    assert element_profile(saju, flat).percent != element_profile(saju).percent
    # 가중치를 모두 1로 두면 원시 세력의 합이 기둥 수의 두 배가 된다
    assert sum(element_profile(saju, flat).raw.values()) == pytest.approx(8.0)
