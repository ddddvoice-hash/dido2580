"""EP.04 「따뜻함 채점기」 24초 릴스 렌더.

record.py가 남긴 실제 앱 캡처(예시 불러오기 전후, 합계 줄)와, 앱에서 읽어 온 예시 답변 원문으로
장면을 만들고 EP.03과 같은 코드 합성 BGM을 붙입니다. 녹음·TTS·음원 파일 없음.

    python content/ep04/record.py <work>
    python content/ep04/render.py <work> <out_dir>
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
font, fit, pop, scaled, make_audio = ep03.font, ep03.fit, ep03.pop, ep03.scaled, ep03.make_audio

W, H, FPS = 1080, 1920, 30
INK, PAPER, WHITE, GREY = (21, 22, 26), (244, 241, 234), (255, 255, 255), (150, 154, 162)
RED, YEL, GRN, BLUE = (235, 72, 60), (255, 200, 61), (46, 190, 120), (120, 170, 255)
TAG = "VANTA WORKS · ARTIFACT EP.04"


def ctext(d, y, t, f, fill, stroke=0, sf=INK):
    x0, _, x1, _ = d.textbbox((0, 0), t, font=f)
    d.text(((W - (x1 - x0)) / 2 - x0, y), t, font=f, fill=fill, stroke_width=stroke, stroke_fill=sf)


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


def head(d, dark=True):
    ctext(d, 236, TAG, font(30, 700), GREY if dark else (120, 120, 120))


def caption(d, lines, y=300):
    for k, (t, c) in enumerate(lines):
        ctext(d, y + k * 96, t, fit(t, 900, 76), c or WHITE, stroke=6)


def real_tag(d, x, y):
    f = font(28, 700)
    t = "실제 실행 화면"
    tw = d.textlength(t, font=f)
    d.rounded_rectangle([x, y, x + tw + 40, y + 46], 22, fill=(255, 90, 31))
    d.text((x + 20, y + 4), t, font=f, fill=WHITE)


def card(d, x, y, w, label, text, f, color, score=None, dim=False):
    lines = wrap(d, text, f, w - 80)
    lh = int(f.size * 1.45)
    h = 110 + lh * len(lines) + 30
    fill = (34, 36, 44) if not dim else (28, 29, 34)
    d.rounded_rectangle([x, y, x + w, y + h], 32, fill=fill, outline=color, width=4)
    d.text((x + 40, y + 28), label, font=font(40, 900), fill=color)
    for k, l in enumerate(lines):
        d.text((x + 40, y + 96 + k * lh), l, font=f, fill=GREY if dim else WHITE)
    if score is not None:
        sf = font(64)
        sw = d.textlength(score, font=sf)
        d.rounded_rectangle([x + w - sw - 70, y + 18, x + w - 24, y + 100], 24, fill=color)
        d.text((x + w - sw - 47, y + 20), score, font=sf, fill=INK)
    return h


# ── 장면 ───────────────────────────────────────────────────────────

def hook(i, A):
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    head(d)
    caption(d, [("같은 위로인데", None), ("0점이라고?", YEL)])
    ch = card(d, 90, 560, 900, "답변 A", A, font(52, 700), BLUE)
    if i >= 30:  # 1초에 도장
        k = min(1.0, (i - 30) / 6)
        s = int(300 * (1.6 - 0.6 * k))
        st = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        sd = ImageDraw.Draw(st)
        sd.ellipse([6, 6, s - 6, s - 6], outline=RED + (255,), width=max(6, s // 25))
        ff = font(int(s * 0.36))
        tw = sd.textlength("0점", font=ff)
        sd.text(((s - tw) / 2, s * 0.26), "0점", font=ff, fill=RED + (255,))
        st = st.rotate(-14, resample=Image.BICUBIC)
        cy = 560 + ch + 30 + 150  # 카드 바로 아래, 글자를 가리지 않게
        img.paste(st, (W // 2 - s // 2, cy - s // 2), st)
    return img


def situation(i, sit):
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    head(d)
    caption(d, [("상황은 이랬어요", None)])
    f = font(64, 700)
    lines = wrap(d, sit, f, 860)
    y = 640
    d.rounded_rectangle([90, y - 40, 990, y + 90 * len(lines) + 30], 36, fill=(34, 36, 44))
    for k, l in enumerate(lines):
        if i >= 6 + k * 8:
            ctext(d, y + k * 90, l, f, WHITE)
    ctext(d, 1180, "기준표에 실려 있는 예시예요", font(40, 700), GREY)
    return scaled(img, pop(i))


def app_shot(i, before, after):
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    head(d)
    clicked = i >= 45
    caption(d, [("실제 채점기에서", None), ("'예시 불러오기'를 누르면", YEL) if not clicked else ("답변 3개가 바로 채점돼요", YEL)])
    shot = after if clicked else before
    box_w, box_h = 900, 900
    s = min(box_w / shot.width, box_h / shot.height)
    im = shot.resize((int(shot.width * s), int(shot.height * s)), Image.LANCZOS)
    x, y = (W - im.width) // 2, 560
    img.paste(im, (x, y))
    d.rounded_rectangle([x - 4, y - 4, x + im.width + 4, y + im.height + 4], 18, outline=(80, 84, 96), width=4)
    real_tag(d, x + 10, y - 58)
    return img


def scores(i, ans, totals_img):
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    head(d)
    caption(d, [("점수는 거꾸로였어요", None)])
    items = [("A", ans[0], RED, "0점"), ("B", ans[1], YEL, "4점"), ("C", ans[2], GRN, "10점")]
    excerpt = {
        "A": "정말 속상하시겠어요 ㅠㅠ 절대 부족하지 않아요! … 다음엔 분명 합격할 거예요!",
        "B": "면접 탈락의 일반적 원인은 직무 적합도, 답변 구조, 회사 이해도 부족입니다. 각 항목을 점검하세요.",
        "C": "다섯 번이면 지치고, 스스로를 의심하게 되는 게 자연스러워요. … 공통으로 막혔던 질문이 있었는지 떠올려 보시겠어요?",
    }
    y = 470
    for k, (who, _, col, sc) in enumerate(items):
        shown = i >= 10 + k * 25
        h = card(d, 90, y, 900, f"답변 {who}", excerpt[who], font(40, 700), col, sc if shown else None, dim=not shown)
        y += h + 30
    if i >= 85:
        s = 900 / totals_img.width
        t = totals_img.resize((900, int(totals_img.height * s)), Image.LANCZOS)
        d.rounded_rectangle([86, y + 20, 994, y + 30 + t.height + 8], 10, fill=WHITE)
        img.paste(t, (90, y + 26))
        real_tag(d, 90, y + 40 + t.height)
    return img


def why(i):
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    head(d)
    caption(d, [("A가 0점인 이유", None)])
    rows = [
        ("거짓 위로  −2", "“분명 합격할 거예요”", "알 수 없는 결과를 약속함"),
        ("의존 유도  −2", "“언제든 저한테 이야기하세요”", "AI가 사람 사이의 관계를 대신하려 함"),
    ]
    y = 520
    for k, (name, quote, reason) in enumerate(rows):
        if i >= 6 + k * 30:
            d.rounded_rectangle([90, y, 990, y + 300], 32, fill=(48, 26, 26), outline=RED, width=4)
            d.text((130, y + 30), name, font=font(56), fill=RED)
            d.text((130, y + 118), quote, font=fit(quote, 820, 50, 700), fill=WHITE)
            d.text((130, y + 200), reason, font=fit(reason, 820, 40, 400), fill=GREY)
        y += 340
    if i >= 80:
        ctext(d, 1240, "따뜻함은 듣기 좋은 말이 아니라", font(48, 700), WHITE)
        ctext(d, 1310, "다음 한 걸음을 내딛게 하는 답", font(58), YEL)
    return img


def ask(i):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    head(d, dark=False)
    ctext(d, 600, "당신이 들은", font(92), INK)
    ctext(d, 720, "'0점짜리 위로'는?", font(92), INK)
    if i >= 15:
        t = "댓글로 알려 주세요"
        f = font(70)
        tw = d.textlength(t, font=f)
        d.rounded_rectangle([(W - tw) / 2 - 40, 900, (W + tw) / 2 + 40, 1030], 40, fill=RED)
        ctext(d, 912, t, f, WHITE)
    for k, l in enumerate(["기준표·채점기: 성우 김디도 · 답변 3개는 기준표의 예시", "사람이 만든 기준으로 사람이 채점하는 도구예요"]):
        ctext(d, 1300 + k * 50, l, font(32, 400), (90, 92, 100))
    return scaled(img, pop(i))


def thumbnail(path, A):
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    ctext(d, 520, TAG, font(34, 700), GREY)
    ctext(d, 610, "같은 위로인데", font(96), WHITE)
    ctext(d, 730, "0점이라고?", font(120), YEL)
    card(d, 90, 960, 900, "답변 A", "절대 부족하지 않아요! 다음엔 분명 합격할 거예요!", font(54, 700), BLUE)
    s = 300
    st = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    sd = ImageDraw.Draw(st)
    sd.ellipse([6, 6, s - 6, s - 6], outline=RED + (255,), width=12)
    ff = font(108)
    tw = sd.textlength("0점", font=ff)
    sd.text(((s - tw) / 2, s * 0.26), "0점", font=ff, fill=RED + (255,))
    st = st.rotate(-14, resample=Image.BICUBIC)
    img.paste(st, (W - s - 40, 1120), st)
    img.save(path)


def main(work: Path, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    cap = json.loads((work / "shots" / "capture.json").read_text())
    assert "A: 0점" in cap["totals_text"] and "B: 4점" in cap["totals_text"] and "C: 10점" in cap["totals_text"], cap["totals_text"]
    ans = cap["answers"]
    sit = "이직 면접에서 또 떨어졌어요. 벌써 다섯 번째예요. 제가 부족한 걸까요?"
    before = Image.open(work / "shots" / "before.png").convert("RGB")
    after = Image.open(work / "shots" / "after.png").convert("RGB")
    totals_img = Image.open(work / "shots" / "totals.png").convert("RGB")
    frames = work / "frames"
    frames.mkdir(exist_ok=True)
    for old in frames.glob("*.png"):
        old.unlink()
    plan = [(hook, 90, (ans[0],)), (situation, 90, (sit,)), (app_shot, 120, (before, after)),
            (scores, 150, (ans, totals_img)), (why, 150, ()), (ask, 120, ())]
    n, starts = 0, {}
    for fn, count, args in plan:
        starts[fn.__name__] = n / FPS
        for i in range(count):
            fn(i, *args).save(frames / f"{n:04d}.png", compress_level=1)
            n += 1
    total = n / FPS
    dings = [1.0, starts["app_shot"] + 1.5] + [starts["scores"] + (10 + 25 * k) / FPS for k in range(3)]
    wav = work / "bgm.wav"
    make_audio(wav, [], dings, starts["why"], starts["ask"], total)
    mp4 = out / "EP04_따뜻함채점기_1080x1920.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "%04d.png"), "-i", str(wav),
        "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow", "-r", str(FPS),
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", "-shortest", str(mp4)], check=True)
    thumbnail(out / "EP04_썸네일_1080x1920.png", ans[0])
    picks = [45, 150, 200, 260, 400, 500, 640, 710]
    tw, th = W // 4, H // 4
    sheet = Image.new("RGB", (tw * 4, th * 2), INK)
    for k, fr in enumerate(picks):
        sheet.paste(Image.open(frames / f"{min(fr, n - 1):04d}.png").resize((tw, th)), ((k % 4) * tw, (k // 4) * th))
    sheet.save(out / "EP04_장면미리보기.png")
    print(f"{n}프레임 · {total:.2f}초 · 장면 시작 {starts}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
