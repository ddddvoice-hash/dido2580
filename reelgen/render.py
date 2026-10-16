"""대본을 1080×1920 세로 카드 이미지로 그린다.

릴스 화면은 위아래가 인스타 UI에 가려지므로 내용은 가운데 안전 영역에만 둔다.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .fonts import body_font, title_font
from .models import ReelScript

W, H = 1080, 1920
SAFE_TOP = 210      # 상단 계정명·음악 표시 영역
SAFE_BOTTOM = 1520  # 하단 캡션·버튼 영역 시작
MARGIN = 50


@dataclass(frozen=True)
class Theme:
    name: str
    bg_top: tuple[int, int, int]
    bg_bottom: tuple[int, int, int]
    accent: tuple[int, int, int]   # 강조 제목, 배지
    accent2: tuple[int, int, int]  # 보조 배지
    ink: tuple[int, int, int]      # 본문 글자


THEMES = [
    Theme("pink", (255, 228, 236), (255, 246, 214), (255, 64, 129), (255, 145, 77), (40, 36, 80)),
    Theme("sky", (214, 236, 255), (240, 248, 255), (33, 118, 255), (0, 184, 212), (28, 40, 82)),
    Theme("mint", (214, 248, 232), (250, 255, 236), (0, 168, 120), (255, 120, 90), (30, 52, 60)),
    Theme("lemon", (255, 244, 196), (255, 228, 210), (255, 120, 0), (230, 57, 70), (60, 40, 30)),
    Theme("lavender", (234, 224, 255), (255, 232, 246), (124, 77, 255), (255, 82, 163), (44, 34, 90)),
]


def pick_theme(script: ReelScript, name: str | None = None) -> Theme:
    if name:
        for theme in THEMES:
            if theme.name == name:
                return theme
        raise ValueError(f"알 수 없는 테마: {name} (가능: {', '.join(t.name for t in THEMES)})")
    digest = hashlib.sha1(script.title.encode()).digest()
    return THEMES[digest[0] % len(THEMES)]


# ── 글자 도우미 ─────────────────────────────────────────────

def text_width(font: ImageFont.FreeTypeFont, text: str, stroke: int = 0) -> int:
    if not text:
        return 0
    left, _, right, _ = font.getbbox(text, stroke_width=stroke)
    return right - left


def fit(make_font, text: str, max_width: int, start: int, minimum: int, stroke: int = 0):
    """max_width 안에 들어가는 가장 큰 폰트를 돌려준다."""
    size = start
    while size > minimum and text_width(make_font(size), text, stroke) > max_width:
        size -= 2
    return make_font(size)


def wrap(font: ImageFont.FreeTypeFont, text: str, max_width: int) -> list[str]:
    """한글은 띄어쓰기 단위로, 그래도 넘치면 글자 단위로 줄을 나눈다."""
    lines: list[str] = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split(" "):
            candidate = f"{line} {word}".strip()
            if text_width(font, candidate) <= max_width:
                line = candidate
                continue
            if line:
                lines.append(line)
            line = ""
            for ch in word:
                if text_width(font, line + ch) > max_width and line:
                    lines.append(line)
                    line = ""
                line += ch
        lines.append(line)
    return lines


def _gradient(top, bottom) -> Image.Image:
    column = Image.new("RGB", (1, H))
    for y in range(H):
        t = y / (H - 1)
        column.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    return column.resize((W, H))


def _sparkles(img: Image.Image, theme: Theme, seed: int) -> None:
    """배경에 흐릿한 원 몇 개를 흩뿌려 밋밋함을 줄인다."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for i in range(14):
        x = (seed * (i + 3) * 7919) % W
        y = (seed * (i + 5) * 104729) % H
        r = 20 + (seed * (i + 1)) % 70
        color = theme.accent if i % 2 else theme.accent2
        draw.ellipse((x - r, y - r, x + r, y + r), fill=color + (38,))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(18)))


# ── 카드 ────────────────────────────────────────────────────

@dataclass
class CardOptions:
    handle: str = ""
    theme: str | None = None
    illustration: Path | None = None


def _draw_title(draw: ImageDraw.ImageDraw, script: ReelScript, theme: Theme) -> int:
    """훅 문구와 큰 제목을 그리고, 제목 아래 y 좌표를 돌려준다."""
    y = SAFE_TOP + 10
    hook_font = fit(title_font, script.hook, W - 2 * MARGIN, 64, 36, stroke=6)
    draw.text((W // 2, y), script.hook, font=hook_font, fill=theme.ink, anchor="ma",
              stroke_width=6, stroke_fill="white")
    y += hook_font.size + 22

    stroke = 12
    font = fit(title_font, script.title, W - 2 * MARGIN, 132, 60, stroke=stroke)
    hl = script.highlight if script.highlight and script.highlight in script.title else ""
    if hl:
        before, after = script.title.split(hl, 1)
        segments = [(before, theme.ink), (hl, theme.accent), (after, theme.ink)]
    else:
        segments = [(script.title, theme.accent)]
    total = sum(text_width(font, s) for s, _ in segments)
    x = (W - total) // 2
    for text, color in segments:
        if not text:
            continue
        # 살짝 아래로 그림자를 깔아 스티커 느낌을 낸다
        draw.text((x + 6, y + 8), text, font=font, fill=(0, 0, 0, 70), stroke_width=stroke, stroke_fill=(0, 0, 0, 70))
        draw.text((x, y), text, font=font, fill=color, stroke_width=stroke, stroke_fill="white")
        x += text_width(font, text)
    return y + font.size + 40


def _badge(draw, box, text: str, color, font_size: int) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=(y1 - y0) // 2, fill=color)
    font = fit(title_font, text, x1 - x0 - 14, font_size, 18)
    draw.text(((x0 + x1) // 2, (y0 + y1) // 2), text, font=font, fill="white", anchor="mm")


def _paste_illustration(img: Image.Image, path: Path, box: tuple[int, int, int, int]) -> None:
    art = Image.open(path).convert("RGBA")
    bw, bh = box[2] - box[0], box[3] - box[1]
    scale = min(bw / art.width, bh / art.height)
    art = art.resize((max(1, int(art.width * scale)), max(1, int(art.height * scale))), Image.LANCZOS)
    x = box[0] + (bw - art.width) // 2
    y = box[3] - art.height
    img.alpha_composite(art, (x, y))


def render_card(script: ReelScript, visible: set[int] | None = None,
                options: CardOptions | None = None) -> Image.Image:
    """카드 한 장을 그린다. visible에 없는 항목은 '???'로 가린다(None이면 전부 공개)."""
    options = options or CardOptions()
    theme = pick_theme(script, options.theme)
    seed = int(hashlib.sha1(script.title.encode()).hexdigest()[:6], 16)
    img = _gradient(theme.bg_top, theme.bg_bottom).convert("RGBA")
    _sparkles(img, theme, seed)

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    top = _draw_title(draw, script, theme)

    panel = (MARGIN - 20, top, W - MARGIN + 20, SAFE_BOTTOM - 10)
    draw.rounded_rectangle(panel, radius=44, fill=(255, 255, 255, 215),
                           outline=theme.accent + (120,), width=5)
    img.alpha_composite(overlay)
    draw = ImageDraw.Draw(img)

    inner = (panel[0] + 30, panel[1] + 30, panel[2] - 30, panel[3] - 70)
    text_right = inner[2]
    if options.illustration:
        # 오른쪽 38%를 그림 자리로 비운다
        art_left = inner[0] + int((inner[2] - inner[0]) * 0.62)
        _paste_illustration(img, Path(options.illustration), (art_left, inner[1], inner[2], inner[3]))
        draw = ImageDraw.Draw(img)
        text_right = art_left - 10

    shown = set(range(len(script.items))) if visible is None else visible
    if script.layout == "grid" and not options.illustration:
        _draw_grid(draw, script, theme, shown, inner)
    else:
        _draw_list(draw, script, theme, shown, (inner[0], inner[1], text_right, inner[3]))

    footer = body_font(26)
    if options.handle:
        draw.text((panel[2] - 34, panel[3] - 30), "@" + options.handle.lstrip("@"),
                  font=footer, fill=(150, 150, 160), anchor="rs")
    if script.source_note:
        note_font = fit(body_font, "※ " + script.source_note, (panel[2] - panel[0]) // 2 + 60, 24, 16)
        draw.text((panel[0] + 34, panel[3] - 30), "※ " + script.source_note,
                  font=note_font, fill=(150, 150, 160), anchor="ls")
    return img.convert("RGB")


def _badge_text(script: ReelScript, i: int) -> str:
    return script.items[i].tag or str(i + 1)


def _badge_width(script: ReelScript, badge_h: int) -> int:
    """가장 긴 배지 글자에 맞춰 모든 배지 폭을 맞춘다. 한두 글자면 동그라미."""
    font = title_font(int(badge_h * 0.55))
    widest = max(text_width(font, _badge_text(script, i)) for i in range(len(script.items)))
    return max(badge_h, widest + int(badge_h * 0.6))


def _draw_list(draw, script: ReelScript, theme: Theme, shown: set[int], box) -> None:
    x0, y0, x1, y1 = box
    n = len(script.items)
    row = min(160, (y1 - y0) // n)
    y = y0 + ((y1 - y0) - row * n) // 2
    badge_h = min(84, int(row * 0.66))
    badge_w = _badge_width(script, badge_h)
    label_size = min(66, int(row * 0.5))
    for i, item in enumerate(script.items):
        cy = y + row // 2
        color = theme.accent if i % 2 == 0 else theme.accent2
        _badge(draw, (x0, cy - badge_h // 2, x0 + badge_w, cy + badge_h // 2),
               _badge_text(script, i), color, int(badge_h * 0.55))
        tx = x0 + badge_w + 22
        avail = x1 - tx
        if i not in shown:
            draw.text((tx, cy), "? ? ?", font=title_font(label_size), fill=(205, 205, 215), anchor="lm")
        else:
            label = item.label
            note = item.note
            if item.english:
                note = f"{item.english}  {note}".strip()
            label_font = fit(title_font, label, int(avail * (0.62 if note else 1.0)), label_size, 24)
            draw.text((tx, cy), label, font=label_font, fill=theme.ink, anchor="lm")
            if note:
                nx = tx + text_width(label_font, label) + 18
                note_font = fit(body_font, note, x1 - nx, int(label_size * 0.62), 16)
                draw.text((nx, cy + 2), note, font=note_font, fill=(110, 110, 125), anchor="lm")
        if i < n - 1:
            draw.line((tx, y + row - 1, x1, y + row - 1), fill=(230, 230, 238), width=2)
        y += row


def _draw_grid(draw, script: ReelScript, theme: Theme, shown: set[int], box) -> None:
    x0, y0, x1, y1 = box
    n = len(script.items)
    rows = math.ceil(n / 2)
    gap = 18
    cell_w = (x1 - x0 - gap) // 2
    cell_h = min(200, (y1 - y0 - gap * (rows - 1)) // rows)
    oy = y0 + ((y1 - y0) - (cell_h * rows + gap * (rows - 1))) // 2
    for i, item in enumerate(script.items):
        # 월별 표처럼 왼쪽 열을 먼저 위에서 아래로 채운다
        col, r = divmod(i, rows)
        cx = x0 + col * (cell_w + gap)
        cy = oy + r * (cell_h + gap)
        color = theme.accent if col == 0 else theme.accent2
        draw.rounded_rectangle((cx, cy, cx + cell_w, cy + cell_h), radius=26,
                               fill=(255, 255, 255), outline=color, width=4)
        badge_h = int(cell_h * 0.36)
        badge_w = _badge_width(script, badge_h)
        _badge(draw, (cx + 14, cy + 14, cx + 14 + badge_w, cy + 14 + badge_h),
               _badge_text(script, i), color, int(badge_h * 0.55))
        lx = cx + 14 + badge_w + 14
        label_font_size = int(cell_h * 0.3)
        if i not in shown:
            draw.text((lx, cy + 14 + badge_h // 2), "???", font=title_font(label_font_size),
                      fill=(205, 205, 215), anchor="lm")
            continue
        label_font = fit(title_font, item.label, cx + cell_w - lx - 12, label_font_size, 22)
        draw.text((lx, cy + 14 + badge_h // 2), item.label, font=label_font, fill=theme.ink, anchor="lm")
        note = f"{item.english} {item.note}".strip() if item.english else item.note
        if note:
            nf = body_font(max(20, int(cell_h * 0.17)))
            lines = wrap(nf, note, cell_w - 28)[:2]
            ny = cy + 14 + badge_h + 14
            for line in lines:
                draw.text((cx + 16, ny), line, font=nf, fill=(110, 110, 125))
                ny += nf.size + 6


def render_cta(script: ReelScript, options: CardOptions | None = None) -> Image.Image:
    """마지막 장면: 완성된 카드를 흐리게 깔고 행동 유도 말풍선을 띄운다."""
    options = options or CardOptions()
    theme = pick_theme(script, options.theme)
    base = render_card(script, None, options).filter(ImageFilter.GaussianBlur(6)).convert("RGBA")
    base.alpha_composite(Image.new("RGBA", base.size, (255, 255, 255, 90)))
    draw = ImageDraw.Draw(base)
    font = title_font(76)
    lines = wrap(font, script.cta, W - 2 * MARGIN - 120)
    box_h = len(lines) * (font.size + 18) + 220
    top = (SAFE_TOP + SAFE_BOTTOM) // 2 - box_h // 2
    draw.rounded_rectangle((MARGIN, top, W - MARGIN, top + box_h), radius=56,
                           fill=(255, 255, 255), outline=theme.accent, width=8)
    y = top + 60
    for line in lines:
        draw.text((W // 2, y), line, font=font, fill=theme.ink, anchor="ma")
        y += font.size + 18
    sub = title_font(50)
    draw.text((W // 2, y + 30), "저장 · 공유 · 팔로우", font=sub, fill=theme.accent, anchor="ma")
    return base.convert("RGB")
