"""분석 결과를 읽을 수 있는 글로 바꾼다.

터미널에 바로 뿌릴 텍스트 리포트와, 다른 프로그램에 넘길 딕셔너리 두 가지를
지원한다. 출력은 전부 여기 모아 두었다 — 계산 모듈은 문자열을 만들지 않는다.
"""

from __future__ import annotations

from typing import Any

from . import constants as K
from .analysis import AXES, Analysis
from .pillars import FourPillars

__all__ = ["text_report", "as_dict"]

_RULE = "─" * 64


def _header(title: str) -> str:
    return f"\n{title}\n{_RULE}"


def _chart_section(saju: FourPillars) -> list[str]:
    out = [_header("■ 사주 원국")]
    out.append(saju.grid())
    out.append("")
    ti = saju.time_info
    for line in ti.describe():
        out.append(f"  {line}")
    out.append(
        f"  일간(나)    {saju.day_master}"
        f"({K.STEMS_HANJA[saju.day.stem_index]}) · "
        f"{saju.day_master_element}({K.ELEMENTS_HANJA[saju.day_master_element]}) · "
        f"{'양' if saju.day.is_yang else '음'}"
    )
    out.append(
        f"  띠          {K.ZODIAC[saju.year.branch_index]}"
        f"({K.BRANCHES_HANJA[saju.year.branch_index]})"
    )
    return out


def _element_section(analysis: Analysis) -> list[str]:
    ep = analysis.elements
    out = [_header("■ 오행 세력")]
    for e in K.ELEMENTS:
        mark = " ← 일간" if e == ep.day_master_element else ""
        out.append(
            f"  {e}({K.ELEMENTS_HANJA[e]})  {ep.bar(e)} {ep.percent[e]:5.1f}%{mark}"
        )
    out.append("")
    out.append(
        f"  신강신약    {ep.strength_label} "
        f"(나를 돕는 힘 {ep.support_score:.1f} : 나를 쓰는 힘 {ep.drain_score:.1f})"
    )
    if ep.missing:
        out.append(f"  약한 오행    {'·'.join(ep.missing)} — 해당 성향을 의식적으로 채우면 좋습니다")
    return out


def _god_section(analysis: Analysis) -> list[str]:
    gp = analysis.gods
    out = [_header("■ 십성 분포 — 나와 세상의 관계")]
    for g in K.GROUPS:
        pct = gp.group_percent[g]
        bar = "█" * round(pct / 100 * 24) + "·" * (24 - round(pct / 100 * 24))
        out.append(f"  {g}  {bar} {pct:5.1f}%")
    out.append("")
    out.append("  두드러진 십성")
    for name, score in gp.top(3):
        where = "·".join(gp.placements.get(name, [])) or "지장간"
        out.append(f"    {name}({where})  {K.TEN_GOD_MEANING[name]}")
    return out


def _shinsal_section(analysis: Analysis) -> list[str]:
    out = [_header("■ 학업 관련 신살")]
    if not analysis.shinsal:
        out.append("  해당하는 신살이 없습니다. 신살은 보조 근거이니 없다고 불리한 것은 아닙니다.")
        return out
    for hit in analysis.shinsal:
        star = "★" if hit.is_prominent else " "
        out.append(f"  {star} {hit.name}({'·'.join(hit.positions)})")
        out.append(f"      {hit.meaning}")
    out.append("")
    out.append("  ★ 표시는 월지·일지에 있어 작용이 뚜렷한 경우입니다.")
    return out


def _axis_section(analysis: Analysis) -> list[str]:
    axes = analysis.axes
    out = [_header("■ 공부 능력 축 (50점이 평균)")]
    for axis in sorted(AXES, key=lambda a: -axes[a]):
        out.append(f"  {axis:<5} {axes.bar(axis)} {axes[axis]:5.1f}  {AXES[axis]}")
    return out


def _style_section(analysis: Analysis) -> list[str]:
    out = [_header("■ 학습 스타일")]
    for ax in analysis.study.style_axes:
        out.append(f"  {ax.left:>12} {ax.bar()} {ax.right:<12}")
        out.append(f"               → {ax.label}")
        out.append(f"                 {ax.note}")
        out.append("")
    return out


def _notes_section(analysis: Analysis) -> list[str]:
    st = analysis.study
    out = [_header("■ 강점과 주의점")]
    if st.strengths:
        out.append("  ▸ 강점")
        for line in st.strengths:
            out.append(f"    · {line}")
    if st.cautions:
        out.append("")
        out.append("  ▸ 주의할 점")
        for line in st.cautions:
            out.append(f"    · {line}")
    if st.method_tips:
        out.append("")
        out.append("  ▸ 공부법 제안")
        for line in st.method_tips:
            out.append(f"    · {line}")
    if not (st.strengths or st.cautions or st.method_tips):
        out.append("  능력 축이 고르게 분포해 특별히 치우친 곳이 없습니다.")
    return out


def _career_section(analysis: Analysis, top: int) -> list[str]:
    out = [_header(f"■ 두뇌 직업 적합도 (상위 {top}개)")]
    for i, fit in enumerate(analysis.top_careers(top), 1):
        out.append(
            f"  {i:2d}. {fit.career.name}  [{fit.career.field}]  "
            f"{fit.score:.1f}점 · {fit.grade}"
        )
        out.append(f"      {fit.career.blurb}")
        out.append(f"      {fit.reason()}")
        out.append(f"      조언: {fit.career.advice}")
        out.append("")
    bottom = analysis.careers[-3:]
    out.append("  ▸ 상대적으로 덜 맞는 쪽")
    out.append(
        "    " + ", ".join(f"{f.career.name}({f.score:.0f})" for f in reversed(bottom))
    )
    out.append("    점수가 낮다고 못 한다는 뜻은 아닙니다. 같은 결과를 내는 데")
    out.append("    더 많은 의식적 노력이 든다는 쪽으로 읽는 편이 맞습니다.")
    return out


def _luck_section(analysis: Analysis) -> list[str]:
    saju = analysis.saju
    out = [_header("■ 대운으로 보는 학업 시기")]
    out.append(
        f"  대운 방향   {'순행' if saju.luck_forward else '역행'} · "
        f"{saju.luck_start_age:.1f}세부터 10년마다 바뀜"
    )
    out.append("")
    for reading in analysis.luck:
        gz = reading.luck.pillar
        bar = "█" * round(reading.score / 100 * 16) + "·" * (16 - round(reading.score / 100 * 16))
        out.append(
            f"  {reading.age_range:>10}  {gz.ganzhi}({gz.hanja})  "
            f"{bar} {reading.score:5.1f}  {'/'.join(reading.tags)}"
        )
    out.append("")
    favourable = analysis.best_study_years(3)
    out.append("  ▸ 학업에 유리한 시기")
    if favourable:
        for reading in favourable:
            out.append(
                f"    · {reading.age_range} ({reading.luck.pillar.ganzhi}) — {reading.comment}"
            )
    else:
        out.append("    · 학습 연령대(45세 이전)에는 뚜렷하게 유리한 대운이 없습니다.")
        out.append("      대운은 배경 조건일 뿐이니, 환경을 직접 만들어 보완하는 편이 낫습니다.")

    tough = analysis.hardest_study_years(2)
    if tough:
        out.append("")
        out.append("  ▸ 공부가 밀리기 쉬운 시기")
        for reading in tough:
            out.append(
                f"    · {reading.age_range} ({reading.luck.pillar.ganzhi}) — {reading.comment}"
            )
    return out


def _warning_section(saju: FourPillars) -> list[str]:
    if not saju.warnings:
        return []
    out = [_header("■ 계산상 유의사항")]
    for w in saju.warnings:
        out.append(f"  ! {w}")
    return out


_DISCLAIMER = """
이 결과는 전통 명리 이론을 코드로 옮긴 것입니다. 통계적으로 검증된 적성검사가
아니며, 같은 사주라도 해석하는 유파에 따라 결론이 달라집니다. 진로를 좁히는
근거가 아니라 자신을 다른 각도에서 살펴보는 재료로 쓰시기 바랍니다.
"""


def text_report(analysis: Analysis, top_careers: int = 6) -> str:
    """터미널용 텍스트 리포트."""
    saju = analysis.saju
    lines: list[str] = []
    lines.append("=" * 64)
    lines.append("  사주로 보는 공부 성향과 두뇌 직업 적성".center(58))
    lines.append("=" * 64)

    for section in (
        _chart_section(saju),
        _element_section(analysis),
        _god_section(analysis),
        _shinsal_section(analysis),
        _axis_section(analysis),
        _style_section(analysis),
        _notes_section(analysis),
        _career_section(analysis, top_careers),
        _luck_section(analysis),
        _warning_section(saju),
    ):
        lines.extend(section)

    lines.append(_RULE)
    lines.append(_DISCLAIMER.strip())
    return "\n".join(lines)


def as_dict(analysis: Analysis) -> dict[str, Any]:
    """JSON 으로 내보내기 좋은 형태."""
    saju = analysis.saju
    return {
        "원국": {
            p.label: {"간지": p.ganzhi, "한자": p.hanja,
                      "천간오행": p.stem_element, "지지오행": p.branch_element}
            for p in saju.pillars
        },
        "일간": saju.day_master,
        "일간오행": saju.day_master_element,
        "시각보정": {
            "입력": saju.time_info.wall.isoformat(),
            "기준": saju.time_info.basis.value,
            "출생지": saju.time_info.place.name,
            "적용태양시": saju.time_info.solar.isoformat(),
            "경도보정분": round(saju.time_info.longitude_shift_minutes, 1),
            "균시차분": round(saju.time_info.equation_of_time_minutes, 1),
            "서머타임": saju.time_info.dst_active,
        },
        "오행": analysis.elements.percent,
        "신강신약": {
            "판정": analysis.elements.strength_label,
            "비율": analysis.elements.strength_ratio,
        },
        "십성그룹": analysis.gods.group_percent,
        "십성": analysis.gods.scores,
        "신살": [
            {"이름": h.name, "자리": h.positions, "뚜렷함": h.is_prominent}
            for h in analysis.shinsal
        ],
        "능력축": analysis.axes.scores,
        "학습스타일": [
            {"축": f"{a.left}↔{a.right}", "값": a.value, "판정": a.label}
            for a in analysis.study.style_axes
        ],
        "강점": analysis.study.strengths,
        "주의점": analysis.study.cautions,
        "공부법": analysis.study.method_tips,
        "직업적합도": [
            {
                "직업": f.career.name,
                "분야": f.career.field,
                "점수": f.score,
                "등급": f.grade,
                "근거": f.reason(),
            }
            for f in analysis.careers
        ],
        "대운": [
            {
                "나이": r.age_range,
                "간지": r.luck.pillar.ganzhi,
                "학업점수": r.score,
                "십성": r.tags,
                "해설": r.comment,
            }
            for r in analysis.luck
        ],
        "유의사항": saju.warnings,
    }
