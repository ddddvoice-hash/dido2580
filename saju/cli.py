"""명령줄 인터페이스.

    python -m saju 1990-05-15 10:30 --male
    python -m saju 1990-05-15 --female --no-hour --place 부산
    python -m saju 1990-05-15 10:30 --male --json > result.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from .analysis import analyze
from .pillars import build_saju
from .report import as_dict, text_report
from .solar_terms import BACKEND
from .timeutil import PLACES, TimeBasis

_BASIS = {
    "standard": TimeBasis.STANDARD,
    "local": TimeBasis.LOCAL_MEAN,
    "true": TimeBasis.TRUE_SOLAR,
}


def _parse_birth(date_str: str, time_str: str | None) -> datetime:
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise SystemExit(f"날짜 형식이 잘못됐습니다: {date_str!r} (예: 1990-05-15)")
    if time_str is None:
        return date.replace(hour=12)
    for fmt in ("%H:%M", "%H%M", "%H"):
        try:
            t = datetime.strptime(time_str, fmt)
            return date.replace(hour=t.hour, minute=t.minute)
        except ValueError:
            continue
    raise SystemExit(f"시각 형식이 잘못됐습니다: {time_str!r} (예: 10:30)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="saju",
        description="사주팔자로 공부 성향과 두뇌 직업 적성을 분석합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "등록된 출생지:\n  " + ", ".join(PLACES) + "\n\n"
            "예시:\n"
            "  python -m saju 1990-05-15 10:30 --male\n"
            "  python -m saju 1988-11-03 04:20 --female --place 부산 --basis true\n"
            "  python -m saju 2001-02-03 --male --no-hour --json\n"
        ),
    )
    p.add_argument("date", help="생년월일 (YYYY-MM-DD)")
    p.add_argument("time", nargs="?", help="출생 시각 (HH:MM). 모르면 --no-hour 를 쓰세요")

    sex = p.add_mutually_exclusive_group(required=True)
    sex.add_argument("--male", "-m", action="store_true", help="남성")
    sex.add_argument("--female", "-f", action="store_true", help="여성")

    p.add_argument("--place", "-p", default="서울", help="출생지 (기본: 서울)")
    p.add_argument(
        "--basis", "-b", default="local", choices=sorted(_BASIS),
        help="시각 보정 기준 — standard(표준시) / local(지방평균태양시, 기본) / true(진태양시)",
    )
    p.add_argument("--no-hour", action="store_true", help="출생 시각을 모를 때 (시주 제외)")
    p.add_argument(
        "--yajasi", action="store_true",
        help="야자시설 적용 — 23시 이후에도 일주를 넘기지 않습니다 (기본은 정자시설)",
    )
    p.add_argument("--careers", "-c", type=int, default=6, help="표시할 직업 개수 (기본 6)")
    p.add_argument("--luck", type=int, default=9, help="뽑을 대운 개수 (기본 9)")
    p.add_argument("--json", action="store_true", help="JSON 으로 출력")
    p.add_argument("--version", action="version", version="saju 1.0")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.time is None and not args.no_hour:
        raise SystemExit(
            "출생 시각이 없습니다. 시각을 넣거나 --no-hour 를 함께 쓰세요.\n"
            "시주는 사주 여덟 글자 중 둘을 차지하므로, 모르면 해석이 크게 흐려집니다."
        )

    birth = _parse_birth(args.date, args.time)
    if args.place not in PLACES:
        raise SystemExit(
            f"모르는 출생지입니다: {args.place!r}\n등록된 곳: {', '.join(PLACES)}"
        )

    saju = build_saju(
        birth,
        is_male=args.male,
        place=args.place,
        basis=_BASIS[args.basis],
        hour_known=not args.no_hour,
        late_zi_next_day=not args.yajasi,
        luck_count=args.luck,
    )
    result = analyze(saju)

    if args.json:
        payload = as_dict(result)
        payload["_계산정보"] = {"절기계산백엔드": BACKEND}
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(text_report(result, top_careers=args.careers))
        if BACKEND == "builtin":
            print(
                "\n[참고] 절기 시각을 내장 급수로 계산했습니다(오차 평균 약 5분). "
                "`pip install ephem` 을 설치하면 1초 이내로 정확해집니다."
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
