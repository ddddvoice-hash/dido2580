"""그날의 뉴스 숫자를 index.html 의 NEWS 블록에 넣습니다.

사용법:
    python lotto/update_news.py news.json

news.json 형식:
    {"date": "2026-10-28",
     "items": [{"t": "기사 제목/요약", "v": "5469.47", "src": "SBS", "url": "https://..."}, ...]}

v 는 기사에 나온 숫자 그대로(쉼표 없이). 항목은 3~8개, 중요한 뉴스부터.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

HTML_PATH = Path(__file__).with_name("index.html")
BLOCK = re.compile(r"(/\*NEWS-START\*/).*?(/\*NEWS-END\*/)", re.S)
NUM = re.compile(r"^\d+(\.\d+)?$")


def validate(news: dict) -> dict:
    date.fromisoformat(news["date"])
    items = news["items"]
    if not 3 <= len(items) <= 8:
        raise ValueError("뉴스 항목은 3~8개여야 합니다")
    clean = []
    for it in items:
        v = str(it["v"]).replace(",", "").strip()
        if not NUM.match(v):
            raise ValueError(f"숫자가 아닙니다: {it['v']!r}")
        url = it.get("url", "")
        if url and not url.startswith("https://"):
            raise ValueError(f"https 주소가 아닙니다: {url}")
        clean.append({"t": str(it["t"]).strip(), "v": v, "src": str(it.get("src", "")).strip(), "url": url})
    return {"date": news["date"], "items": clean}


def main() -> None:
    news = validate(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    body = json.dumps(news, ensure_ascii=False, indent=2).replace("</", "<\\/")
    html = HTML_PATH.read_text(encoding="utf-8")
    if not BLOCK.search(html):
        raise SystemExit("index.html 에서 NEWS 블록을 찾지 못했습니다")
    html = BLOCK.sub(lambda m: f"{m[1]}const NEWS = {body};{m[2]}", html, count=1)
    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"{news['date']} 뉴스 {len(news['items'])}개를 반영했습니다")


if __name__ == "__main__":
    main()
