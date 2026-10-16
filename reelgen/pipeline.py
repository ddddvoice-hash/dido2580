"""대본 한 편을 결과물 폴더 하나로 만든다.

output/20261016-2130-제철회-총정리/
  script.json   대본 (손으로 고쳐서 from-json으로 다시 렌더 가능)
  cover.png     완성 카드. 릴스 커버나 피드용 이미지로 쓴다
  reel.mp4      릴스 영상
  caption.txt   본문 + 해시태그
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .models import ReelScript
from .render import CardOptions, render_card
from .topics import History
from .video import Timing, make_video


@dataclass
class BuildSettings:
    out_root: Path = Path("output")
    card: CardOptions = field(default_factory=CardOptions)
    timing: Timing = field(default_factory=Timing)
    order: str = "auto"
    bgm: Path | None = None
    video: bool = True


def slugify(text: str, limit: int = 30) -> str:
    slug = re.sub(r"[^\w가-힣]+", "-", text).strip("-")
    return slug[:limit] or "reel"


def produce(script: ReelScript, settings: BuildSettings, topic: str = "",
            history: History | None = None) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    folder = Path(settings.out_root) / f"{stamp}-{slugify(script.title)}"
    folder.mkdir(parents=True, exist_ok=True)

    (folder / "script.json").write_text(
        json.dumps({"topic": topic, **script.model_dump()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (folder / "caption.txt").write_text(script.full_caption() + "\n", encoding="utf-8")
    render_card(script, None, settings.card).save(folder / "cover.png")
    if settings.video:
        make_video(script, folder, settings.card, settings.timing, settings.order, settings.bgm)
    if history is not None and topic:
        history.add(topic, script.title, folder.name)
    return folder


def load_script(path: Path) -> tuple[ReelScript, str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    topic = data.pop("topic", "")
    return ReelScript.model_validate(data), topic
