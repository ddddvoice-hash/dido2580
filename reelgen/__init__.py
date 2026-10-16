"""오영완 스타일 정보 카드 릴스를 자동으로 만드는 파이프라인.

주제 선정 → Claude로 대본 작성 → 카드 이미지 렌더 → 릴스 영상 합성 → 인스타그램 업로드.
"""

from .models import Item, ReelScript

__all__ = ["Item", "ReelScript"]
__version__ = "0.1.0"
