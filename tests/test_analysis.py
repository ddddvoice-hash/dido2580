"""공부 성향·직업 적성 분석 검증."""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from saju.analysis import AXES, CAREERS, analyze
from saju.pillars import build_saju


def sample_charts(n: int, seed: int = 4242):
    rng = random.Random(seed)
    for _ in range(n):
        birth = datetime(1950, 1, 1) + timedelta(
            days=rng.randint(0, 30000), minutes=rng.randint(0, 1439)
        )
        yield build_saju(birth, rng.random() < 0.5)


def test_axis_scores_stay_in_range():
    for saju in sample_charts(120):
        scores = analyze(saju).axes.scores
        assert set(scores) == set(AXES)
        assert all(0.0 <= v <= 100.0 for v in scores.values())


def test_career_scores_stay_in_range_and_are_sorted():
    for saju in sample_charts(60):
        fits = analyze(saju).careers
        assert len(fits) == len(CAREERS)
        assert all(0.0 <= f.score <= 100.0 for f in fits)
        assert [f.score for f in fits] == sorted((f.score for f in fits), reverse=True)


def test_every_career_declares_known_axes():
    for career in CAREERS:
        assert career.weights, f"{career.name} 에 가중치가 없습니다"
        assert set(career.weights) <= set(AXES)
        assert all(w > 0 for w in career.weights.values())
        assert career.blurb and career.advice and career.field


def test_career_names_are_unique():
    names = [c.name for c in CAREERS]
    assert len(names) == len(set(names))


def test_analysis_is_deterministic():
    saju = build_saju(datetime(1990, 5, 15, 10, 30), True)
    first, second = analyze(saju), analyze(saju)
    assert first.axes.scores == second.axes.scores
    assert [f.score for f in first.careers] == [f.score for f in second.careers]


def test_grade_matches_score_bands():
    for saju in sample_charts(40):
        for fit in analyze(saju).careers:
            if fit.score >= 70:
                assert fit.grade == "매우 높음"
            elif fit.score >= 60:
                assert fit.grade == "높음"
            elif fit.score >= 50:
                assert fit.grade == "보통"
            elif fit.score >= 40:
                assert fit.grade == "낮음"
            else:
                assert fit.grade == "매우 낮음"


def test_style_axes_are_bounded():
    for saju in sample_charts(40):
        for axis in analyze(saju).study.style_axes:
            assert -100.0 <= axis.value <= 100.0
            assert axis.label
            assert len(axis.bar()) == 21


def test_luck_readings_cover_every_luck_pillar():
    saju = build_saju(datetime(1990, 5, 15, 10, 30), True, luck_count=8)
    result = analyze(saju)
    assert len(result.luck) == 8
    for reading in result.luck:
        assert 0.0 <= reading.score <= 100.0
        assert reading.tags and reading.comment


def test_best_study_years_prefers_learning_ages():
    """학업 시기 추천은 기본적으로 45세 이전 대운에서 고른다."""
    saju = build_saju(datetime(1988, 11, 3, 4, 20), False, luck_count=10)
    result = analyze(saju)
    picks = result.best_study_years(3)
    assert len(picks) == 3
    assert all(p.luck.start_age < 45 for p in picks)
    assert [p.score for p in picks] == sorted((p.score for p in picks), reverse=True)


def test_inseong_luck_scores_above_jaeseong_luck():
    """인성운은 배움이 들어오는 운, 재성운은 흩어지는 운이다."""
    saju = build_saju(datetime(1988, 11, 3, 4, 20), False, luck_count=10)
    result = analyze(saju)
    inseong = [r.score for r in result.luck if {"정인", "편인"} & set(r.tags)]
    jaeseong = [r.score for r in result.luck if {"정재", "편재"} & set(r.tags)]
    assert inseong and jaeseong
    assert min(inseong) > max(jaeseong)


def test_best_study_years_excludes_unfavourable_periods():
    """상위 N개를 무조건 뽑느라 불리한 대운이 '유리한 시기'에 섞이면 안 된다."""
    for saju in sample_charts(40):
        result = analyze(saju)
        for reading in result.best_study_years(3):
            assert reading.score >= 55.0
            assert reading.luck.start_age < 45


def test_almost_every_chart_has_some_favourable_study_period():
    """학습 연령대 대운이 다섯 개쯤 되므로 유리한 시기가 하나도 없기는 어렵다.

    1,500개 표본에서 빈 결과는 0건이었다. 이 테스트는 점수 기준이나 대운
    계산을 손댔을 때 그 성질이 깨지는지를 본다. 리포트가 빈 목록을 만났을
    때의 동작은 `tests/test_report_cli.py` 에서 따로 확인한다.
    """
    for saju in sample_charts(120, seed=808):
        picks = analyze(saju).best_study_years(3)
        assert 1 <= len(picks) <= 3


def test_hardest_study_years_are_actually_low():
    for saju in sample_charts(40):
        for reading in analyze(saju).hardest_study_years(2):
            assert reading.score <= 45.0
            assert reading.luck.start_age < 45


def test_favourable_and_hard_periods_never_overlap():
    for saju in sample_charts(40):
        result = analyze(saju)
        good = {r.age_range for r in result.best_study_years(3)}
        bad = {r.age_range for r in result.hardest_study_years(2)}
        assert not (good & bad)


def test_unknown_hour_still_analyzes():
    saju = build_saju(datetime(1990, 5, 15, 12), True, hour_known=False)
    result = analyze(saju)
    assert result.axes.scores
    assert result.top_careers(3)


def test_careers_in_field_filters():
    result = analyze(build_saju(datetime(1990, 5, 15, 10, 30), True))
    research = result.careers_in("연구")
    assert research
    assert all(f.career.field == "연구" for f in research)


def test_axis_bar_length_is_stable():
    axes = analyze(build_saju(datetime(1990, 5, 15, 10, 30), True)).axes
    for axis in AXES:
        assert len(axes.bar(axis, width=20)) == 20
