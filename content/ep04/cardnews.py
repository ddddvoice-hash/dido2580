"""EP.04 「따뜻함 채점기」 카드뉴스형 릴스.

카드 10장을 한 장씩 밀어 넘기는 1080×1920 영상. 점수·감점·정의 문구는 앱의 rubric.json에서,
합계 화면은 record.py가 찍은 실제 앱 캡처에서 가져옵니다. 배경음은 EP.03과 같은 코드 합성.

    python content/ep04/record.py <work>
    python content/ep04/cardnews.py <work> <out_dir>
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ep03r", HERE.parent / "ep03" / "render.py")
ep03 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ep03)
font, fit, make_audio = ep03.font, ep03.fit, ep03.make_audio

W, H, FPS = 1080, 1920, 30
HOLDS = [72, 75, 90, 72, 108, 78, 114, 96, 90, 90]  # 카드별 유지 프레임(글이 긴 카드는 길게)
SLIDE = 8  # 넘김 0.27초
PAPER, INK, SUB, LINE = (246, 243, 236), (24, 25, 30), (110, 112, 120), (222, 216, 204)
RED, YEL, GRN, BLUE, ORG = (226, 62, 52), (255, 196, 45), (34, 160, 100), (60, 120, 230), (255, 90, 31)
SCORE_COL = {"A": RED, "B": (214, 150, 0), "C": GRN}


def ctext(d, y, t, f, fill):
    x0, _, x1, _ = d.textbbox((0, 0), t, font=f)
    d.text(((W - (x1 - x0)) / 2 - x0, y), t, font=f, fill=fill)


def wrap(d, text, f, width):
    out, cur = [], ""
    for w in text.split(" "):
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= width or not cur:
            cur = t
        else:
            out.append(cur)
            cur = w
    return out + [cur]


def para(d, x, y, text, f, fill, width, lh=1.5):
    lines = wrap(d, text, f, width)
    for k, l in enumerate(lines):
        d.text((x, y + k * f.size * lh), l, font=f, fill=fill)
    return int(len(lines) * f.size * lh)


def frame(no, total, kicker):
    """카드 공통 틀: 상단 시리즈명·페이지, 하단 진행 점."""
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.text((90, 236), "VANTA WORKS · 따뜻함 채점기", font=font(30, 700), fill=SUB)
    pg = f"{no:02d} / {total:02d}"
    d.text((W - 90 - d.textlength(pg, font=font(30, 700)), 236), pg, font=font(30, 700), fill=SUB)
    d.line([90, 290, W - 90, 290], fill=LINE, width=3)
    if kicker:
        f = font(34, 900)
        tw = d.textlength(kicker, font=f)
        d.rounded_rectangle([90, 330, 90 + tw + 44, 386], 28, fill=INK)
        d.text((112, 334), kicker, font=f, fill=PAPER)
    gap = 26
    x0 = (W - (total - 1) * gap) / 2
    for k in range(total):
        r = 9 if k + 1 == no else 6
        cx = x0 + k * gap
        d.ellipse([cx - r, 1500 - r, cx + r, 1500 + r], fill=INK if k + 1 == no else LINE)
    return img, d


def stamp(img, cx, cy, s=280, text="0점"):
    st = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    sd = ImageDraw.Draw(st)
    sd.ellipse([6, 6, s - 6, s - 6], outline=RED + (255,), width=s // 22)
    ff = font(int(s * 0.36))
    tw = sd.textlength(text, font=ff)
    sd.text(((s - tw) / 2, s * 0.26), text, font=ff, fill=RED + (255,))
    st = st.rotate(-14, resample=Image.BICUBIC)
    img.paste(st, (int(cx - s / 2), int(cy - s / 2)), st)


def quote_box(d, y, label, text, col, f):
    lines = wrap(d, text, f, 800)
    lh = int(f.size * 1.5)
    h = 120 + lh * len(lines) + 30
    d.rounded_rectangle([90, y, W - 90, y + h], 34, fill=(255, 255, 255), outline=col, width=5)
    d.text((130, y + 34), label, font=font(38, 900), fill=col)
    for k, l in enumerate(lines):
        d.text((130, y + 104 + k * lh), l, font=f, fill=INK)
    return h


# ── 카드 ───────────────────────────────────────────────────────────

def build_cards(ex, rubric, totals_img):
    A, B, C = ex["answers"]
    crit = rubric["criteria"]
    pen = {p["id"]: p for p in rubric["penalties"]}
    N = 10
    cards = []

    img, d = frame(1, N, None)
    ctext(d, 520, "같은 위로인데", font(104), INK)
    ctext(d, 650, "0점?", font(200), RED)
    ctext(d, 930, "AI 답변 따뜻함 채점기로 재 봤다", font(50, 700), SUB)
    stamp(img, W / 2, 1230, 300)
    cards.append(img)

    img, d = frame(2, N, "상황")
    ctext(d, 520, "이직 면접,", font(96), INK)
    ctext(d, 640, "다섯 번째 탈락", font(96), INK)
    h = quote_box(d, 840, "사용자의 한 마디", ex["situation"], INK, font(52, 700))
    ctext(d, 840 + h + 40, "이 말에 답변 3개를 채점했어요", font(40, 700), SUB)
    cards.append(img)

    for no, ans, title, tag in [(3, A, "가장 다정해 보이는 답", "답변 A"), (4, B, "정보만 주는 답", "답변 B"),
                                (5, C, "짚고, 바로잡고, 같이 보는 답", "답변 C")]:
        img, d = frame(no, N, tag)
        ctext(d, 470, title, fit(title, 900, 80), INK)
        quote_box(d, 640, tag, ans["text"], SCORE_COL[ans["id"]], font(46 if len(ans["text"]) > 100 else 54, 700))
        cards.append(img)

    img, d = frame(6, N, "결과")
    ctext(d, 450, "점수는 거꾸로였어요", font(84), INK)
    for k, ans in enumerate([A, B, C]):
        x = 110 + k * 300
        col = SCORE_COL[ans["id"]]
        d.rounded_rectangle([x, 600, x + 260, 960], 36, fill=col)
        tw = d.textlength(ans["id"], font=font(70))
        d.text((x + (260 - tw) / 2, 630), ans["id"], font=font(70), fill=PAPER)
        sc = f"{ans['total']}"
        tw = d.textlength(sc, font=font(150))
        d.text((x + (260 - tw) / 2, 720), sc, font=font(150), fill=PAPER)
        tw = d.textlength("점", font=font(44, 700))
        d.text((x + (260 - tw) / 2, 895), "점", font=font(44, 700), fill=PAPER)
    s = 900 / totals_img.width
    t = totals_img.resize((900, int(totals_img.height * s)), Image.LANCZOS)
    d.rounded_rectangle([86, 1040, 994, 1040 + t.height + 16], 12, fill=(255, 255, 255), outline=LINE, width=3)
    img.paste(t, (90, 1048))
    f = font(28, 700)
    tw = d.textlength("실제 채점기 화면", font=f)
    d.rounded_rectangle([90, 1040 + t.height + 34, 130 + tw, 1040 + t.height + 80], 22, fill=ORG)
    d.text((110, 1040 + t.height + 38), "실제 채점기 화면", font=f, fill=(255, 255, 255))
    cards.append(img)

    img, d = frame(7, N, "기준")
    ctext(d, 450, "다섯 가지를 0~2점씩", font(80), INK)
    ctext(d, 560, "합계 10점, 감점은 2점씩", font(50, 700), SUB)
    y = 680
    d.text((470, y), "A", font=font(44), fill=SCORE_COL["A"])
    d.text((620, y), "B", font=font(44), fill=SCORE_COL["B"])
    d.text((770, y), "C", font=font(44), fill=SCORE_COL["C"])
    for k, c in enumerate(crit):
        yy = y + 80 + k * 100
        d.line([90, yy - 14, W - 90, yy - 14], fill=LINE, width=2)
        d.text((100, yy), c["name"], font=font(48, 700), fill=INK)
        for j, ans in enumerate([A, B, C]):
            v = str(ans["scores"][c["id"]])
            d.text((470 + j * 150, yy), v, font=font(52), fill=SCORE_COL[ans["id"]])
    yy = y + 80 + 5 * 100
    d.line([90, yy - 14, W - 90, yy - 14], fill=INK, width=3)
    d.text((100, yy), "감점", font=font(48, 700), fill=RED)
    for j, ans in enumerate([A, B, C]):
        v = f"−{2 * len(ans['penalties'])}" if ans["penalties"] else "0"
        d.text((455 + j * 150, yy), v, font=font(52), fill=SCORE_COL[ans["id"]])
    a_raw = sum(A["scores"].values())
    note = f"A: {a_raw}점 − 감점 {2 * len(A["penalties"])}점 = 0점 (0점 아래로는 내려가지 않아요)"
    ctext(d, yy + 110, note, fit(note, 900, 36, 700), RED)
    cards.append(img)

    img, d = frame(8, N, "왜 0점?")
    ctext(d, 450, "A가 놓친 것", font(90), INK)
    y = 620
    for pid, quote in [("false_comfort", "“다음엔 분명 합격할 거예요!”"), ("dependency", "“힘들 때는 언제든 저한테 이야기하세요.”")]:
        p = pen[pid]
        d.rounded_rectangle([90, y, W - 90, y + 300], 34, fill=(255, 255, 255), outline=RED, width=5)
        d.text((130, y + 30), f"{p['name']}  −2", font=font(58), fill=RED)
        d.text((130, y + 115), quote, font=fit(quote, 820, 46, 700), fill=INK)
        d.text((130, y + 200), p["why"], font=fit(p["why"], 820, 38, 400), fill=SUB)
        y += 340
    cards.append(img)

    img, d = frame(9, N, "정의")
    ctext(d, 520, "따뜻함은", font(96), INK)
    ctext(d, 650, "듣기 좋은 말이 아니라", font(80), SUB)
    ctext(d, 780, "다음 한 걸음을", font(104), RED)
    ctext(d, 910, "내딛게 하는 답", font(104), RED)
    para(d, 130, 1100, rubric["definition"], font(36, 400), SUB, 820)
    cards.append(img)

    img, d = frame(10, N, None)
    ctext(d, 560, "당신이 들은", font(96), INK)
    ctext(d, 690, "'0점짜리 위로'는?", font(96), INK)
    t = "댓글로 알려 주세요"
    f = font(66)
    tw = d.textlength(t, font=f)
    d.rounded_rectangle([(W - tw) / 2 - 44, 880, (W + tw) / 2 + 44, 1010], 42, fill=RED)
    ctext(d, 892, t, f, (255, 255, 255))
    for k, l in enumerate(["기준표·채점기: 성우 김디도", "답변 3개는 기준표에 실린 예시 · 사람이 만든 기준으로 사람이 채점해요"]):
        ctext(d, 1180 + k * 52, l, font(32, 400), SUB)
    cards.append(img)
    return cards


def main(work: Path, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    cap = json.loads((work / "shots" / "capture.json").read_text())
    assert all(s in cap["totals_text"] for s in ("A: 0점", "B: 4점", "C: 10점")), cap["totals_text"]
    rubric = json.loads((work / "app" / "apps/warmth-scorer/rubric.json").read_text())
    ex = rubric["examples"][0]
    assert [a["text"] for a in ex["answers"]] == cap["answers"], "앱 화면의 답변과 rubric 예시가 다름"
    for a in ex["answers"]:  # 기준표 규칙으로 합계 재계산
        raw = sum(a["scores"].values()) - 2 * len(a["penalties"])
        assert max(0, raw) == a["total"], (a["id"], raw, a["total"])
    cards = build_cards(ex, rubric, Image.open(work / "shots" / "totals.png").convert("RGB"))
    frames = work / "cn_frames"
    frames.mkdir(exist_ok=True)
    for old in frames.glob("*.png"):
        old.unlink()
    n, flips = 0, []
    for k, c in enumerate(cards):
        for _ in range(HOLDS[k]):
            c.save(frames / f"{n:04d}.png", compress_level=1); n += 1
        if k + 1 < len(cards):
            flips.append(n / FPS)
            nxt = cards[k + 1]
            for j in range(1, SLIDE + 1):
                e = 1 - (1 - j / SLIDE) ** 3
                off = int(W * e)
                fr = Image.new("RGB", (W, H), PAPER)
                fr.paste(c, (-off, 0))
                fr.paste(nxt, (W - off, 0))
                fr.save(frames / f"{n:04d}.png", compress_level=1); n += 1
    for _ in range(12):
        cards[-1].save(frames / f"{n:04d}.png", compress_level=1); n += 1
    total = n / FPS
    wav = work / "cn_bgm.wav"
    make_audio(wav, flips, [flips[4] + SLIDE / FPS], flips[6], flips[8], total)  # 넘김마다 '착', 결과 카드에 '딩'
    mp4 = out / "EP04_카드뉴스_1080x1920.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "%04d.png"), "-i", str(wav),
        "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow", "-r", str(FPS),
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", "-shortest", str(mp4)], check=True)
    cards[0].save(out / "EP04_카드뉴스_썸네일_1080x1920.png")
    tw, th = W // 5, H // 5
    sheet = Image.new("RGB", (tw * 5, th * 2), PAPER)
    for k, c in enumerate(cards):
        sheet.paste(c.resize((tw, th)), ((k % 5) * tw, (k // 5) * th))
    sheet.save(out / "EP04_카드뉴스_10장.png")
    print(f"{n}프레임 · {total:.2f}초 · 카드 {len(cards)}장")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
