"""로또 6/45 역대 당첨번호를 내려받아 index.html 안의 데이터 블록을 갱신합니다.

사용법:
    python lotto/update_data.py              # 인터넷에서 최신 데이터 받기
    python lotto/update_data.py all.json     # 이미 받아 둔 파일 사용

데이터 출처: https://github.com/smok95/lotto (동행복권 발표 결과를 모아 둔 공개 저장소)
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

SOURCE_URL = "https://raw.githubusercontent.com/smok95/lotto/main/results/all.json"
HTML_PATH = Path(__file__).with_name("index.html")
BLOCK = re.compile(r"(/\*DATA-START\*/).*?(/\*DATA-END\*/)", re.S)


def load(arg: str | None) -> list[dict]:
    if arg:
        return json.loads(Path(arg).read_text(encoding="utf-8"))
    with urllib.request.urlopen(SOURCE_URL, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def encode(draws: list[dict]) -> str:
    """회차 순서대로 '번호6개,보너스' 를 ';' 로 이어 붙입니다."""
    draws = sorted(draws, key=lambda r: r["draw_no"])
    out = []
    for expect, r in enumerate(draws, start=1):
        if r["draw_no"] != expect:
            raise ValueError(f"{expect}회 데이터가 빠져 있습니다")
        nums = sorted(r["numbers"])
        if len(set(nums)) != 6 or not all(1 <= n <= 45 for n in nums):
            raise ValueError(f"{expect}회 번호가 이상합니다: {nums}")
        out.append(",".join(map(str, nums + [r["bonus_no"]])))
    return ";".join(out)


def main() -> None:
    draws = load(sys.argv[1] if len(sys.argv) > 1 else None)
    data = encode(draws)
    html = HTML_PATH.read_text(encoding="utf-8")
    if not BLOCK.search(html):
        raise SystemExit("index.html 에서 데이터 블록을 찾지 못했습니다")
    html = BLOCK.sub(lambda m: f'{m[1]}const DRAWS="{data}";{m[2]}', html, count=1)
    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"{len(draws)}회차까지 반영했습니다 → {HTML_PATH}")


if __name__ == "__main__":
    main()
