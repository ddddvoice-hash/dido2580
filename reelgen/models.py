"""릴스 한 편의 대본 구조."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

MIN_ITEMS = 3
MAX_ITEMS = 12


class Item(BaseModel):
    """카드 한 줄. 순위표의 한 칸이나 월별 표의 한 칸이 된다."""

    label: str = Field(description="굵게 보이는 핵심 문구. 15자 이내. 예: '178cm', '담배 핀 적 없음', '방어'")
    note: str = Field(default="", description="작게 붙는 보조 설명. 20자 이내. 예: '(22.7%)', '겨울 바다가 채운 진한 고소함'")
    tag: str = Field(default="", description="번호 대신 배지에 넣을 짧은 말. 4자 이내. 예: '1월', 'O형'. 비우면 순위 번호를 쓴다")
    english: str = Field(default="", description="영어 학습 모드일 때만 채우는 짧은 영어 표현")


class ReelScript(BaseModel):
    """Claude가 채우는 릴스 대본."""

    hook: str = Field(description="제목 위 작은 문구이자 영상 첫 장면의 훅. 18자 이내. 예: '여자들이 의외로 좋아하는'")
    title: str = Field(description="큰 제목. 14자 이내. 예: '남자키 순위 TOP10'")
    highlight: str = Field(description="제목 안에서 강조색을 입힐 단어. 반드시 title의 일부여야 한다")
    layout: Literal["list", "grid"] = Field(description="항목이 길면 list, 월별처럼 짧은 항목이 많으면 grid")
    items: list[Item] = Field(description="3~12개 항목. 순위형이면 1위부터 순서대로")
    cta: str = Field(description="마지막 장면 행동 유도 문구. 예: '나는 몇 위? 댓글로 알려줘'")
    caption: str = Field(description="인스타 본문. 3~6줄, 질문으로 댓글을 유도하고 저장을 권한다")
    hashtags: list[str] = Field(description="해시태그 8~15개, # 없이")
    source_note: str = Field(description="근거 표기. 통계가 있으면 출처, 없으면 '재미로 보는 콘텐츠예요' 같은 문구")

    def validate_shape(self) -> list[str]:
        """구조화 출력 스키마로 걸러지지 않는 조건을 점검한다. 문제 목록을 돌려준다."""
        problems = []
        if not MIN_ITEMS <= len(self.items) <= MAX_ITEMS:
            problems.append(f"항목 수 {len(self.items)}개 (허용 {MIN_ITEMS}~{MAX_ITEMS})")
        if self.highlight and self.highlight not in self.title:
            problems.append(f"강조어 '{self.highlight}'가 제목에 없음")
        return problems

    def hashtag_line(self) -> str:
        return " ".join("#" + t.lstrip("#").replace(" ", "") for t in self.hashtags)

    def full_caption(self) -> str:
        parts = [self.caption.strip()]
        if self.source_note:
            parts.append(f"※ {self.source_note.strip()}")
        parts.append(self.hashtag_line())
        return "\n\n".join(p for p in parts if p)
