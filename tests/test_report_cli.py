"""리포트 출력과 명령줄 인터페이스 검증."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from saju import Reading, read
from saju.analysis import analyze
from saju.cli import main
from saju.korean import has_final, josa
from saju.pillars import build_saju
from saju.report import as_dict, text_report


@pytest.fixture
def result():
    return analyze(build_saju(datetime(1990, 5, 15, 10, 30), True))


def test_text_report_contains_every_section(result):
    text = text_report(result)
    for heading in [
        "사주 원국", "오행 세력", "십성 분포", "학업 관련 신살",
        "공부 능력 축", "학습 스타일", "강점과 주의점",
        "두뇌 직업 적합도", "대운으로 보는 학업 시기",
    ]:
        assert heading in text, f"{heading} 항목이 빠졌습니다"


def test_report_handles_chart_without_favourable_study_years():
    """유리한 대운이 없을 때도 리포트가 그 사실을 말해야 한다."""
    result = analyze(build_saju(datetime(1990, 5, 15, 10, 30), True))
    result.luck = []        # 유리한 대운이 하나도 없는 상황을 만든다
    text = text_report(result)
    assert "뚜렷하게 유리한 대운이 없습니다" in text


def test_text_report_includes_disclaimer(result):
    assert "통계적으로 검증된 적성검사가" in text_report(result)


def test_text_report_honours_career_count(result):
    assert "  6. " in text_report(result, top_careers=6)
    assert "  6. " not in text_report(result, top_careers=3)


def test_as_dict_is_json_serialisable(result):
    payload = as_dict(result)
    encoded = json.dumps(payload, ensure_ascii=False)
    assert json.loads(encoded)["일간"] == "경"
    assert len(payload["직업적합도"]) == len(result.careers)
    assert set(payload["능력축"]) == set(result.axes.scores)


def test_as_dict_records_time_correction(result):
    info = as_dict(result)["시각보정"]
    assert info["출생지"] == "서울"
    assert info["기준"] == "지방평균태양시"
    assert info["경도보정분"] == pytest.approx(-32.1, abs=0.2)


def test_read_helper_returns_everything():
    reading = read(datetime(1990, 5, 15, 10, 30), is_male=True)
    assert isinstance(reading, Reading)
    assert reading.saju.day_master == "경"
    assert "사주 원국" in reading.report
    assert reading.to_dict()["일간"] == "경"


# --- 한국어 조사 -----------------------------------------------------------

@pytest.mark.parametrize(
    "word,particle,expected",
    [
        ("문창귀인", "이", "문창귀인이"),
        ("화개", "이", "화개가"),
        ("역마", "은", "역마는"),
        ("괴강", "은", "괴강은"),
        ("목", "을", "목을"),
        ("수", "를", "수를"),
        ("천을귀인", "과", "천을귀인과"),
        ("화개", "와", "화개와"),
    ],
)
def test_josa_picks_the_right_form(word, particle, expected):
    assert josa(word, particle) == expected


def test_has_final_detects_batchim():
    assert has_final("강") is True
    assert has_final("가") is False
    assert has_final("") is False


def test_josa_passes_through_unknown_particles():
    assert josa("화개", "에서") == "화개에서"


# --- CLI -------------------------------------------------------------------

def test_cli_text_output(capsys):
    assert main(["1990-05-15", "10:30", "--male"]) == 0
    out = capsys.readouterr().out
    assert "사주 원국" in out
    assert "두뇌 직업 적합도" in out


def test_cli_json_output(capsys):
    assert main(["1990-05-15", "10:30", "--male", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["일간"] == "경"
    assert payload["_계산정보"]["절기계산백엔드"] in {"ephem", "builtin"}


def test_cli_accepts_place_and_basis(capsys):
    assert main(["1988-11-03", "04:20", "--female", "-p", "부산", "-b", "true", "--json"]) == 0
    info = json.loads(capsys.readouterr().out)["시각보정"]
    assert info["출생지"] == "부산"
    assert info["기준"] == "진태양시"


def test_cli_no_hour_mode(capsys):
    assert main(["2001-02-03", "--male", "--no-hour", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "시주" not in payload["원국"]


def test_cli_requires_time_unless_no_hour():
    with pytest.raises(SystemExit) as exc:
        main(["2001-02-03", "--male"])
    assert "출생 시각" in str(exc.value)


def test_cli_rejects_unknown_place():
    with pytest.raises(SystemExit) as exc:
        main(["2001-02-03", "10:00", "--male", "-p", "아틀란티스"])
    assert "모르는 출생지" in str(exc.value)


def test_cli_rejects_bad_date():
    with pytest.raises(SystemExit) as exc:
        main(["2001-13-45", "10:00", "--male"])
    assert "날짜 형식" in str(exc.value)


def test_cli_rejects_bad_time():
    with pytest.raises(SystemExit) as exc:
        main(["2001-02-03", "25시", "--male"])
    assert "시각 형식" in str(exc.value)


def test_cli_requires_sex():
    with pytest.raises(SystemExit):
        main(["2001-02-03", "10:00"])


def test_cli_yajasi_switch_changes_day_pillar(capsys):
    main(["1975-12-31", "23:45", "--male", "-b", "standard", "--json"])
    strict = json.loads(capsys.readouterr().out)["원국"]["일주"]["간지"]
    main(["1975-12-31", "23:45", "--male", "-b", "standard", "--yajasi", "--json"])
    lenient = json.loads(capsys.readouterr().out)["원국"]["일주"]["간지"]
    assert strict != lenient
