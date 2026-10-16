"""명령줄 진입점.

  python -m reelgen demo                       API 키 없이 예시 릴스 만들기
  python -m reelgen make "월별 제철 과일 총정리"   주제 하나로 릴스 만들기
  python -m reelgen auto --count 3             안 만든 주제를 골라 여러 편 만들기
  python -m reelgen render output/.../script.json  고친 대본으로 다시 렌더
  python -m reelgen publish output/...         만든 릴스를 인스타그램에 올리기
  python -m reelgen topics                     주제 은행과 남은 주제 보기
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .pipeline import BuildSettings, load_script, produce
from .render import THEMES, CardOptions
from .topics import TOPIC_BANK, History, unused_seeds


def _add_build_options(p: argparse.ArgumentParser) -> None:
    p.add_argument("--out", type=Path, default=Path("output"), help="결과물 폴더 (기본 output)")
    p.add_argument("--handle", default="", help="카드 아래 넣을 계정명")
    p.add_argument("--theme", choices=[t.name for t in THEMES], help="색 테마 (기본: 제목으로 자동 선택)")
    p.add_argument("--illustration", type=Path, help="카드 오른쪽에 넣을 PNG 일러스트 (배경 투명 권장)")
    p.add_argument("--bgm", type=Path, help="배경 음악 파일 (저작권 문제없는 음원)")
    p.add_argument("--order", choices=["auto", "countdown", "forward"], default="auto",
                   help="항목 공개 순서 (기본 auto: 순위는 꼴찌부터, 월별 표는 1월부터)")
    p.add_argument("--no-video", action="store_true", help="영상 없이 카드 이미지만 만들기")
    p.add_argument("--publish", action="store_true", help="만들자마자 인스타그램에 올리기")


def _settings(args) -> BuildSettings:
    return BuildSettings(
        out_root=args.out,
        card=CardOptions(handle=args.handle, theme=args.theme, illustration=args.illustration),
        order=args.order,
        bgm=args.bgm,
        video=not args.no_video,
    )


def _finish(folder: Path, args) -> None:
    print(f"완성: {folder}")
    if getattr(args, "publish", False):
        _publish(folder, None)


def _publish(folder: Path, video_url: str | None) -> None:
    from .publish import publish_reel

    caption = (folder / "caption.txt").read_text(encoding="utf-8").strip()
    media_id = publish_reel(folder / "reel.mp4", caption, video_url=video_url)
    (folder / "published.txt").write_text(media_id + "\n", encoding="utf-8")
    print(f"게시 완료: media id {media_id}")


def cmd_demo(args) -> int:
    from .samples import SAMPLES

    names = [args.sample] if args.sample else list(SAMPLES)
    for name in names:
        _finish(produce(SAMPLES[name](), _settings(args)), args)
    return 0


def cmd_make(args) -> int:
    from .content import write_script

    history = History(args.out / "history.json")
    script = write_script(args.topic, english=args.english, items=args.items)
    _finish(produce(script, _settings(args), args.topic, history), args)
    return 0


def cmd_auto(args) -> int:
    from .content import brainstorm_topics, write_script

    history = History(args.out / "history.json")
    queue = [] if args.brainstorm else unused_seeds(history, args.category)
    if len(queue) < args.count:
        queue += brainstorm_topics(args.count - len(queue), category=args.category,
                                   avoid=history.topics() + queue)
    failures = 0
    for topic in queue[: args.count]:
        if history.has(topic):
            continue
        print(f"▶ {topic}")
        try:
            script = write_script(topic, english=args.english)
            _finish(produce(script, _settings(args), topic, history), args)
        except Exception as exc:  # 한 편이 실패해도 나머지는 계속 만든다
            failures += 1
            print(f"  실패: {exc}", file=sys.stderr)
    return 1 if failures else 0


def cmd_render(args) -> int:
    script, topic = load_script(args.script)
    problems = script.validate_shape()
    if problems:
        print("대본 형식 오류: " + "; ".join(problems), file=sys.stderr)
        return 2
    _finish(produce(script, _settings(args), topic), args)
    return 0


def cmd_publish(args) -> int:
    _publish(args.folder, args.video_url)
    return 0


def cmd_topics(args) -> int:
    history = History(args.out / "history.json")
    for category, topics in TOPIC_BANK.items():
        print(f"[{category}]")
        for t in topics:
            print(f"  {'✓' if history.has(t) else '·'} {t}")
    print(f"\n남은 씨앗 주제 {len(unused_seeds(history))}개 · 만든 릴스 {len(history.entries)}편")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reelgen", description="정보 카드 릴스 자동 생성기")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("demo", help="API 키 없이 예시 릴스 만들기")
    p.add_argument("--sample", choices=["seasonal_fish", "top_traits", "english"])
    _add_build_options(p)
    p.set_defaults(func=cmd_demo)

    p = sub.add_parser("make", help="주제 하나로 릴스 만들기")
    p.add_argument("topic")
    p.add_argument("--english", action="store_true", help="항목마다 영어 표현 붙이기")
    p.add_argument("--items", type=int, help="항목 수 (3~12)")
    _add_build_options(p)
    p.set_defaults(func=cmd_make)

    p = sub.add_parser("auto", help="안 만든 주제를 골라 여러 편 만들기")
    p.add_argument("--count", type=int, default=3)
    p.add_argument("--category", default="", help="분야 (예: 영어, 음식)")
    p.add_argument("--brainstorm", action="store_true", help="주제 은행 대신 Claude가 새 주제를 뽑기")
    p.add_argument("--english", action="store_true")
    _add_build_options(p)
    p.set_defaults(func=cmd_auto)

    p = sub.add_parser("render", help="script.json으로 다시 렌더")
    p.add_argument("script", type=Path)
    _add_build_options(p)
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("publish", help="만든 릴스를 인스타그램에 올리기")
    p.add_argument("folder", type=Path)
    p.add_argument("--video-url", help="영상을 공개 URL에 올려 두었으면 그 주소")
    p.set_defaults(func=cmd_publish)

    p = sub.add_parser("topics", help="주제 은행 보기")
    p.add_argument("--out", type=Path, default=Path("output"))
    p.set_defaults(func=cmd_topics)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
