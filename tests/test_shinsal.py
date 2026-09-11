"""학업 신살 검증."""

from __future__ import annotations

from datetime import datetime

import pytest

from saju import constants as K
from saju.pillars import build_saju
from saju.shinsal import (
    CHEONEUL,
    GWAEGANG,
    HAKDANG,
    MUNCHANG,
    MUNGOK,
    STUDY_SHINSAL,
    find_shinsal,
)
from saju.tenstars import twelve_stage


@pytest.mark.parametrize("table", [MUNCHANG, HAKDANG, MUNGOK, CHEONEUL])
def test_tables_cover_all_ten_stems(table):
    assert set(table) == set(K.STEMS)


@pytest.mark.parametrize("table", [MUNCHANG, HAKDANG, MUNGOK])
def test_tables_point_at_real_branches(table):
    assert all(branch in K.BRANCHES for branch in table.values())


def test_cheoneul_always_names_two_branches():
    for stem, branches in CHEONEUL.items():
        assert len(branches) == 2
        assert all(b in K.BRANCHES for b in branches)


def test_hakdang_is_the_changsaeng_position():
    """학당귀인은 정의상 일간의 장생지와 같다."""
    for dm, branch in HAKDANG.items():
        assert twelve_stage(dm, branch) == "장생"


def test_gwaegang_days_are_valid_ganzhi():
    for ganzhi in GWAEGANG:
        stem, branch = ganzhi[0], ganzhi[1]
        assert stem in K.STEMS and branch in K.BRANCHES
        # 60갑자에 실재하는 조합이어야 한다 (음양이 맞아야 함)
        assert K.STEM_YANG[K.STEMS.index(stem)] == K.BRANCH_YANG[K.BRANCHES.index(branch)]


def test_every_shinsal_has_a_meaning():
    saju = build_saju(datetime(1990, 5, 15, 10, 30), True)
    for hit in find_shinsal(saju):
        assert hit.name in STUDY_SHINSAL
        assert hit.meaning == STUDY_SHINSAL[hit.name]
        assert hit.positions


def test_prominent_means_month_or_day_branch():
    for year in range(1970, 2010, 3):
        saju = build_saju(datetime(year, 4, 9, 14, 20), True)
        for hit in find_shinsal(saju):
            assert hit.is_prominent == any(p in ("월지", "일지") for p in hit.positions)


def test_gwaegang_detected_on_known_day_pillar():
    """1990-05-15 은 경진(庚辰)일주 — 괴강에 해당한다."""
    saju = build_saju(datetime(1990, 5, 15, 10, 30), True)
    assert saju.day.ganzhi == "경진"
    assert any(h.name == "괴강" for h in find_shinsal(saju))


def test_munchang_detected_when_branch_present():
    saju = build_saju(datetime(1990, 5, 15, 10, 30), True)
    target = MUNCHANG[saju.day_master]
    present = any(p.branch == target for p in saju.pillars)
    found = any(h.name == "문창귀인" for h in find_shinsal(saju))
    assert found == present


def test_no_duplicate_shinsal_entries():
    for year in range(1955, 2015, 5):
        saju = build_saju(datetime(year, 11, 21, 8, 40), False)
        names = [h.name for h in find_shinsal(saju)]
        assert len(names) == len(set(names))
