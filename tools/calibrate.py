"""축 점수 기준선을 다시 뽑는 도구.

`analysis.AXIS_OFFSET` 는 무작위 사주 표본에서 각 축의 중앙값이 50이 되도록
맞춘 평행이동 값이다. 가중치나 신살 보정을 손대면 이 값도 다시 뽑아야 한다.

    python tools/calibrate.py [표본수]

출력된 딕셔너리를 `saju/analysis.py` 의 `AXIS_OFFSET` 에 붙여 넣으면 된다.
"""

from __future__ import annotations

import random
import statistics
import sys
from datetime import datetime, timedelta

from saju import analysis
from saju.analysis import AXES, analyze
from saju.pillars import build_saju


def sample_axis_scores(n: int, seed: int = 20240101) -> dict[str, list[float]]:
    """무작위 생년월일시로 사주를 만들어 축 점수를 모은다."""
    rng = random.Random(seed)
    out: dict[str, list[float]] = {axis: [] for axis in AXES}
    start = datetime(1940, 1, 1)
    span_days = 36000  # 1940 ~ 2038
    for _ in range(n):
        birth = start + timedelta(
            days=rng.randint(0, span_days), minutes=rng.randint(0, 1439)
        )
        result = analyze(build_saju(birth, rng.random() < 0.5))
        for axis, value in result.axes.scores.items():
            out[axis].append(value)
    return out


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000

    # 이미 적용된 보정을 걷어내고 순수 분포를 본다
    applied = dict(analysis.AXIS_OFFSET)
    analysis.AXIS_OFFSET = {axis: 0.0 for axis in AXES}

    samples = sample_axis_scores(n)

    print(f"표본 {n}개 — 보정 전 분포")
    print(f"{'축':<8}{'중앙값':>8}{'평균':>8}{'표준편차':>9}")
    offsets: dict[str, float] = {}
    for axis, values in samples.items():
        median = statistics.median(values)
        offsets[axis] = round(50.0 - median, 1)
        print(
            f"{axis:<8}{median:8.1f}{statistics.mean(values):8.1f}"
            f"{statistics.pstdev(values):9.1f}"
        )

    print("\n기존 값:")
    print(f"AXIS_OFFSET = {applied}")
    print("\n새 값 — saju/analysis.py 의 AXIS_OFFSET 에 붙여 넣으세요:")
    print(f"AXIS_OFFSET = {offsets}")


if __name__ == "__main__":
    main()
