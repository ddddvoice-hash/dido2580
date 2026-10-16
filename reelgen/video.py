"""카드 장면들을 이어 붙여 릴스 mp4를 만든다.

장면 구성 (10개 항목 기준 약 15초)
  1. 훅      — 제목과 가려진 '???' 목록. 끝까지 보게 만드는 장면
  2. 공개    — 항목을 하나씩 연다. 순위는 꼴찌부터 1위로, 월별 표는 1월부터
  3. 완성    — 전체 카드를 멈춰 보여 준다. 캡처·저장용
  4. 행동유도 — "나는 몇 위? 댓글로!" 말풍선
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .models import ReelScript
from .render import CardOptions, render_card, render_cta

FPS = 30


@dataclass
class Timing:
    hook: float = 2.0
    reveal_total: float = 7.0   # 공개 구간 전체 길이. 항목 수로 나눈다
    reveal_min: float = 0.55
    reveal_max: float = 1.2
    hold: float = 3.5
    cta: float = 2.5

    def per_item(self, n: int) -> float:
        return max(self.reveal_min, min(self.reveal_max, self.reveal_total / n))


def reveal_steps(n: int, order: str) -> list[set[int]]:
    """공개 순서대로 '보이는 항목 집합'을 늘려 간다."""
    if order == "auto":
        raise ValueError("auto는 resolve_order로 먼저 풀어야 합니다")
    if order == "countdown":
        sequence = list(range(n - 1, -1, -1))
    elif order == "forward":
        sequence = list(range(n))
    else:
        raise ValueError(f"order는 countdown 또는 forward: {order}")
    steps, shown = [], set()
    for i in sequence:
        shown = shown | {i}
        steps.append(shown)
    return steps


def resolve_order(script: ReelScript, order: str) -> str:
    """auto면 월별 표(grid)는 1월부터, 순위·목록은 카운트다운으로 연다."""
    if order != "auto":
        return order
    return "forward" if script.layout == "grid" else "countdown"


def build_scenes(script: ReelScript, frames_dir: Path, options: CardOptions,
                 timing: Timing, order: str) -> list[tuple[Path, float]]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    scenes: list[tuple[Path, float]] = []

    def save(img, name: str, seconds: float) -> None:
        path = frames_dir / f"{len(scenes):03d}_{name}.png"
        img.save(path)
        scenes.append((path, seconds))

    n = len(script.items)
    save(render_card(script, set(), options), "hook", timing.hook)
    steps = reveal_steps(n, resolve_order(script, order))
    for k, shown in enumerate(steps[:-1]):
        save(render_card(script, shown, options), f"reveal{k:02d}", timing.per_item(n))
    # 마지막 공개 장면이 곧 완성 장면이다
    save(render_card(script, None, options), "full", timing.per_item(n) + timing.hold)
    save(render_cta(script, options), "cta", timing.cta)
    return scenes


def encode(scenes: list[tuple[Path, float]], out_path: Path, bgm: Path | None = None) -> Path:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg가 필요합니다 (apt install ffmpeg / brew install ffmpeg)")
    total = sum(d for _, d in scenes)
    listing = out_path.parent / "scenes.txt"
    lines = []
    for path, seconds in scenes:
        lines.append(f"file '{path.resolve().as_posix()}'")
        lines.append(f"duration {seconds:.3f}")
    lines.append(f"file '{scenes[-1][0].resolve().as_posix()}'")  # concat 형식상 마지막 파일을 한 번 더 적는다
    listing.write_text("\n".join(lines) + "\n", encoding="utf-8")

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing)]
    if bgm:
        cmd += ["-stream_loop", "-1", "-i", str(bgm)]
    else:
        # 소리 트랙이 없으면 일부 기기에서 재생·업로드가 불안정해 무음 트랙을 넣는다
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    fade_start = max(0.0, total - 1.5)
    cmd += [
        "-map", "0:v", "-map", "1:a",
        "-vf", f"fps={FPS},format=yuv420p",
        "-af", f"afade=t=out:st={fade_start:.2f}:d=1.5",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-t", f"{total:.3f}", "-movflags", "+faststart",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)
    return out_path


def make_video(script: ReelScript, out_dir: Path, options: CardOptions | None = None,
               timing: Timing | None = None, order: str = "auto",
               bgm: Path | None = None, keep_frames: bool = False) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    options = options or CardOptions()
    timing = timing or Timing()
    frames_dir = out_dir / "frames"
    scenes = build_scenes(script, frames_dir, options, timing, order)
    video = encode(scenes, out_dir / "reel.mp4", bgm)
    if not keep_frames:
        shutil.rmtree(frames_dir, ignore_errors=True)
        (out_dir / "scenes.txt").unlink(missing_ok=True)
    return video
