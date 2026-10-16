"""주제 은행과 제작 기록.

같은 주제를 두 번 올리지 않도록 만든 주제를 history.json에 남긴다.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

# 스크린샷 속 반응 좋은 포맷을 분야별로 나눈 씨앗 주제
TOPIC_BANK: dict[str, list[str]] = {
    "연애·관계": [
        "여자들이 의외로 좋아하는 남자 키 순위 TOP10",
        "상위 3% 남자의 생활 습관 특징 10가지",
        "아내가 남편을 찐사랑하면 생기는 일 8가지",
        "연락 문제로 싸우지 않는 커플 특징",
        "첫 데이트에서 호감 사는 말 TOP7",
    ],
    "궁합·운세": [
        "티격태격해도 오래가는 혈액형 남녀 궁합 순위",
        "말 안 듣는 아내 띠 순위",
        "연말 귀인을 만나는 생일 모음",
        "MBTI별 연애할 때 서운한 순간",
    ],
    "이름·외모": [
        "박씨 중 예쁜 여자가 많다는 이름 30",
        "여자 머리 길이 뭐가 좋아요? 6가지 길이 비교",
        "얼굴형별 잘 어울리는 앞머리",
    ],
    "음식·시즌": [
        "월별로 꼭 먹어봐야 할 제철회 총정리",
        "월별 제철 과일 총정리",
        "편의점 꿀조합 TOP10",
        "겨울에 꼭 먹어야 할 제철 음식 10가지",
    ],
    "생활정보": [
        "모르면 손해 보는 연말정산 꿀팁 7가지",
        "자취생 필수 다이소 꿀템 TOP10",
        "돈 모으는 사람들의 공통 습관",
    ],
    "영어": [
        "원어민이 매일 쓰는 찐 영어표현 TOP10",
        "한국인이 자주 틀리는 영어 표현 10가지",
        "카톡 대신 쓰는 영어 줄임말 TOP10",
        "월별로 외우는 영어 계절 표현",
    ],
}


def all_seed_topics() -> list[tuple[str, str]]:
    return [(cat, t) for cat, topics in TOPIC_BANK.items() for t in topics]


class History:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.entries: list[dict] = []
        if self.path.is_file():
            self.entries = json.loads(self.path.read_text(encoding="utf-8"))

    def topics(self) -> list[str]:
        return [e["topic"] for e in self.entries]

    def has(self, topic: str) -> bool:
        key = _normalize(topic)
        return any(_normalize(t) == key for t in self.topics())

    def add(self, topic: str, title: str, folder: str) -> None:
        self.entries.append({
            "topic": topic,
            "title": title,
            "folder": folder,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.entries, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize(text: str) -> str:
    return "".join(text.split()).lower()


def unused_seeds(history: History, category: str = "") -> list[str]:
    return [t for cat, t in all_seed_topics()
            if (not category or category in cat) and not history.has(t)]
