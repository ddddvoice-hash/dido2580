"""한국어 출력 다듬기 — 조사(助詞) 자동 선택.

'문창귀인이'와 '화개가'처럼 앞 글자의 받침 유무에 따라 조사가 달라진다.
리포트 문장을 코드로 조립하다 보면 '화개이(가)' 같은 어색한 표기가 남는데,
한글 음절은 유니코드에서 규칙적으로 배열돼 있어 간단히 계산할 수 있다.

    (코드포인트 - 0xAC00) % 28 != 0  →  받침 있음
"""

from __future__ import annotations

__all__ = ["has_final", "josa"]

_HANGUL_START = 0xAC00
_HANGUL_END = 0xD7A3

# (받침 있을 때, 받침 없을 때)
_PAIRS = {
    "은": ("은", "는"), "는": ("은", "는"),
    "이": ("이", "가"), "가": ("이", "가"),
    "을": ("을", "를"), "를": ("을", "를"),
    "과": ("과", "와"), "와": ("과", "와"),
    "으로": ("으로", "로"), "로": ("으로", "로"),
    "이라": ("이라", "라"), "라": ("이라", "라"),
}


def has_final(word: str) -> bool:
    """`word` 의 마지막 글자에 받침이 있는지.

    한글이 아닌 글자로 끝나면 받침이 있는 것으로 본다(보수적 선택).
    """
    if not word:
        return False
    last = word[-1]
    code = ord(last)
    if _HANGUL_START <= code <= _HANGUL_END:
        return (code - _HANGUL_START) % 28 != 0
    # 숫자는 읽는 소리를 기준으로 판단한다
    if last.isdigit():
        return last in "0136780"
    return True


def josa(word: str, particle: str) -> str:
    """`word` 뒤에 붙일 조사를 골라 이어 붙인다.

    >>> josa("문창귀인", "이")
    '문창귀인이'
    >>> josa("화개", "이")
    '화개가'
    >>> josa("역마", "은")
    '역마는'
    """
    if particle not in _PAIRS:
        return word + particle
    with_final, without_final = _PAIRS[particle]
    return word + (with_final if has_final(word) else without_final)
