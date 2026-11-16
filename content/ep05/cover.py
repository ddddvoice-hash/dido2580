"""EP.05 커버: 영상 1번 카드 문구 + 실제 애니마틱 프레임(0:35 레조넌스, 금색 K07).

디도 님 결정(11/17): GPT 일러스트 대신 실제 화면 커버. 핵심은 가운데 1080×1440 안에 둔다.

    python content/ep05/cover.py <work> <out_dir>
"""
import importlib.util
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ep03r", HERE.parent / "ep03" / "render.py")
ep03 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ep03)
font, fit = ep03.font, ep03.fit

W, H = 1080, 1920
INK, WHITE, GREY, GOLD, ORG = (14, 16, 22), (255, 255, 255), (150, 156, 168), (246, 196, 60), (255, 90, 31)
FRAME_T = 35.0


def ctext(d, y, t, f, fill):
    x0, _, x1, _ = d.textbbox((0, 0), t, font=f)
    d.text(((W - (x1 - x0)) / 2 - x0, y), t, font=f, fill=fill, stroke_width=6, stroke_fill=INK)


def main(work: Path, out: Path):
    src = Image.open(work / "src_frames" / f"s0_{int(FRAME_T * 30):04d}.jpg").convert("RGB")
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    ctext(d, 300, "VANTA WORKS · ARTIFACT EP.05", font(34, 700), GREY)
    ctext(d, 390, "AI와 애니메이션", fit("AI와 애니메이션", 960, 116), WHITE)
    ctext(d, 530, "오프닝을 만들어봤다", fit("오프닝을 만들어봤다", 960, 116), GOLD)
    v = src.resize((W, int(W * 720 / 1280)), Image.LANCZOS)
    img.paste(v, (0, 760))
    d.rectangle([0, 756, W, 759], fill=(60, 64, 76))
    d.rectangle([0, 760 + v.height, W, 763 + v.height], fill=(60, 64, 76))
    f = font(30, 700)
    t = "실제 애니마틱 화면"
    tw = d.textlength(t, font=f)
    d.rounded_rectangle([90, 760 + v.height + 34, 130 + tw, 760 + v.height + 82], 24, fill=ORG)
    d.text((110, 760 + v.height + 38), t, font=f, fill=WHITE)
    ctext(d, 1520, "그림 파일 0장 · 화면도 음악도 코드로", font(52, 700), WHITE)
    out.mkdir(parents=True, exist_ok=True)
    img.save(out / "EP05_커버_1080x1920.jpg", quality=92)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
