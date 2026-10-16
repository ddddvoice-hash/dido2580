"""Claude로 주제를 고르고 대본을 쓴다."""

from __future__ import annotations

import os

import anthropic
from pydantic import BaseModel, Field

from .models import ReelScript

MODEL = os.environ.get("REELGEN_MODEL", "claude-opus-5-5")

SYSTEM = """\
당신은 인스타그램 정보 카드 릴스 작가입니다. 20~30대 한국인이 '저장'하고 '공유'하고 \
'댓글'을 달고 싶어지는 순위표·체크리스트·월별 정리 카드를 만듭니다.

스타일
- 제목은 짧고 세게. 의외성("의외로"), 소속감("상위 3%"), 시기성("월별로 꼭") 중 하나를 건다.
- 항목 문구는 한눈에 읽히게 짧게. 설명은 note에 짧게 단다.
- 순위형이면 tag에 '1위' 같은 순위를, 월별이면 '1월'을, 혈액형·띠면 'O형'·'말띠'를 쓴다. 특징 목록이면 tag를 비운다.
- caption은 첫 줄에 공감 한 마디, 마지막 줄에 댓글을 부르는 질문. 이모지는 2~4개.
- cta는 "나는 몇 위?"처럼 댓글을 부르는 짧은 말.

사실 규칙
- 실제 통계나 수치를 확실히 모르면 숫자를 지어내지 마세요. 대신 질적인 표현을 쓰고 \
source_note에 '재미로 보는 콘텐츠예요'라고 적으세요.
- 혐오, 외모 비하, 특정 집단 낙인, 건강·의학적 단정은 피합니다.
- 실존 인물이나 브랜드를 깎아내리지 않습니다.
"""


class TopicIdeas(BaseModel):
    topics: list[str] = Field(description="릴스 주제. 한 줄짜리 한국어 주제문")


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def _parse(client: anthropic.Anthropic, prompt: str, output_format):
    # 안전 분류기가 거절하면 서버가 대체 모델로 다시 시도한다(fallbacks="default").
    response = client.beta.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM,
        output_config={"effort": "medium"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": prompt}],
        output_format=output_format,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"모델이 이 주제를 거절했습니다: {prompt[:60]}")
    if response.stop_reason == "max_tokens" or response.parsed_output is None:
        raise RuntimeError("대본이 중간에 잘렸거나 형식이 맞지 않습니다")
    return response.parsed_output


def write_script(topic: str, *, english: bool = False, items: int | None = None,
                 client: anthropic.Anthropic | None = None) -> ReelScript:
    """주제 한 줄을 받아 릴스 대본을 만든다. 모양이 어긋나면 한 번 더 시도한다."""
    client = client or _client()
    prompt = f"주제: {topic}\n"
    if items:
        prompt += f"항목 수: {items}개\n"
    if english:
        prompt += ("영어 학습 모드: 각 항목의 english에 그 항목과 어울리는 짧은 영어 표현을 넣으세요. "
                   "영어 표현 자체가 주제라면 label에 영어를, note에 뜻을 넣으세요.\n")
    prompt += "위 주제로 릴스 대본을 작성하세요."

    script = _parse(client, prompt, ReelScript)
    problems = script.validate_shape()
    if problems:
        retry = prompt + "\n\n이전 시도의 문제: " + "; ".join(problems) + ". 고쳐서 다시 작성하세요."
        script = _parse(client, retry, ReelScript)
        problems = script.validate_shape()
        if problems:
            raise ValueError("대본 형식 오류: " + "; ".join(problems))
    return script


def brainstorm_topics(count: int, *, category: str = "", avoid: list[str] | None = None,
                      client: anthropic.Anthropic | None = None) -> list[str]:
    """새 주제를 뽑는다. 이미 만든 주제는 avoid로 넘겨 겹치지 않게 한다."""
    client = client or _client()
    prompt = f"저장·공유가 잘 되는 정보 카드 릴스 주제를 {count}개 제안하세요.\n"
    if category:
        prompt += f"분야: {category}\n"
    if avoid:
        prompt += "이미 만든 주제(겹치지 말 것):\n" + "\n".join(f"- {t}" for t in avoid[-80:]) + "\n"
    ideas = _parse(client, prompt, TopicIdeas)
    return [t.strip() for t in ideas.topics if t.strip()][:count]
