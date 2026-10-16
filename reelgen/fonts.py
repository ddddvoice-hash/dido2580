"""한글 폰트 찾기.

우선순위: 환경변수 → 프로젝트 fonts/ 폴더 → 운영체제별 흔한 한글 폰트.
제목용(굵고 둥근 폰트)과 본문용을 따로 고른다.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

PROJECT_FONTS = Path(__file__).resolve().parent.parent / "fonts"

# 앞에 있을수록 먼저 쓴다. Black Han Sans, Jua 같은 무료 폰트를 fonts/에 넣으면 그게 1순위다.
TITLE_CANDIDATES = [
    "BlackHanSans-Regular.ttf",
    "Jua-Regular.ttf",
    "/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf",
    "/usr/share/fonts/truetype/nanum/NanumSquareB.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/Library/Fonts/NanumSquareRoundB.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "C:/Windows/Fonts/malgunbd.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]

BODY_CANDIDATES = [
    "Jua-Regular.ttf",
    "/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf",
    "/usr/share/fonts/truetype/nanum/NanumBarunGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "C:/Windows/Fonts/malgunbd.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]


def _resolve(env_name: str, candidates: list[str]) -> Path:
    override = os.environ.get(env_name)
    if override:
        path = Path(override)
        if not path.is_file():
            raise FileNotFoundError(f"{env_name}={override} 파일이 없습니다")
        return path
    for name in candidates:
        path = Path(name)
        if not path.is_absolute():
            path = PROJECT_FONTS / name
        if path.is_file():
            return path
    raise FileNotFoundError(
        "한글 폰트를 찾지 못했습니다. fonts/ 폴더에 .ttf를 넣거나 "
        f"{env_name} 환경변수로 경로를 지정하세요. (리눅스: apt install fonts-nanum)"
    )


@lru_cache(maxsize=None)
def title_font_path() -> Path:
    return _resolve("REELGEN_TITLE_FONT", TITLE_CANDIDATES)


@lru_cache(maxsize=None)
def body_font_path() -> Path:
    return _resolve("REELGEN_BODY_FONT", BODY_CANDIDATES)


@lru_cache(maxsize=512)
def title_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(title_font_path()), size)


@lru_cache(maxsize=512)
def body_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(body_font_path()), size)
