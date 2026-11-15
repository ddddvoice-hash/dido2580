"""EP.03 「억 단위 읽기」 20초 릴스 렌더.

record.py가 남긴 실제 앱 캡처에 훅·힌트·문제 장면과 자막을 붙이고,
코드로 합성한 BGM·효과음을 넣어 1080×1920 H.264/AAC MP4와 썸네일을 만듭니다.
음원 파일·TTS·녹음은 쓰지 않습니다.

    python content/ep03/record.py <work>
    python content/ep03/render.py <work> <out_dir>
"""
import json
import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONT = {w: str(HERE / "app" / "fonts" / f"nsk-{w}.ttf") for w in (400, 700, 900)}
W, H, FPS, SR = 1080, 1920, 30, 48000
INK, PAPER, ACCENT, YELLOW, TEAL, WHITE, GREY = (21, 22, 26), (244, 241, 234), (255, 90, 31), (255, 200, 61), (60, 200, 170), (255, 255, 255), (150, 154, 162)
APP_X, APP_Y, APP_CROP = 90, 590, 910  # 앱 캡처를 놓을 자리(위 910px만 사용, 아래 끝 y=1500)


def font(size, w=900):
    return ImageFont.truetype(FONT[w], size)


def center_text(d, y, text, f, fill):
    x0, y0, x1, y1 = d.textbbox((0, 0), text, font=f)
    d.text(((W - (x1 - x0)) / 2 - x0, y), text, font=f, fill=fill)


def fit(text, w_max, size, weight=900):
    while size > 20:
        f = font(size, weight)
        x0, _, x1, _ = f.getbbox(text)
        if x1 - x0 <= w_max:
            return f
        size -= 2
    return font(size, weight)


def pop(i, n=4):
    """처음 n프레임 동안 0.85→1.0으로 커지는 비율."""
    return 1.0 if i >= n else 0.85 + 0.15 * (1 - (1 - i / n) ** 3)


def scaled(img, s):
    if s >= 0.999:
        return img
    small = img.resize((int(W * s), int(H * s)), Image.LANCZOS)
    bg = Image.new("RGB", (W, H), img.getpixel((5, 5)))
    bg.paste(small, ((W - small.width) // 2, (H - small.height) // 2))
    return bg


def series_tag(d, dark=True):
    center_text(d, 236, "VANTA WORKS · ARTIFACT EP.03", font(30, 700), GREY if dark else (120, 120, 120))


def caption(d, lines, y=310, color=WHITE, box=None):
    """자막: 굵은 고딕 + 외곽선, 안전영역(x 100~980, y 300~1450) 안."""
    for k, (t, c) in enumerate(lines):
        f = fit(t, 860, 76)
        x0, y0, x1, y1 = d.textbbox((0, 0), t, font=f)
        x = (W - (x1 - x0)) / 2 - x0
        d.text((x, y + k * 96), t, font=f, fill=c or color, stroke_width=6, stroke_fill=INK)


def number_with_commas(d, y, text, f, comma_color, base=WHITE):
    total = d.textlength(text, font=f)
    x = (W - total) / 2
    for ch in text:
        d.text((x, y), ch, font=f, fill=comma_color if ch == "," else base)
        x += d.textlength(ch, font=f)


# ── 장면 ───────────────────────────────────────────────────────────

def hook_frame(i):
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    series_tag(d)
    blink = ACCENT if (i // 8) % 2 == 0 else YELLOW
    f = fit("500,000,000,000원", 940, 140)
    number_with_commas(d, 760, "500,000,000,000원", f, blink)
    center_text(d, 1010, "바로 읽을 수 있어?", font(92), WHITE)
    return scaled(img, pop(i))


def hint_frame(i):
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    series_tag(d)
    caption(d, [("힌트: 0을 4개씩 끊어 보세요", YELLOW)])
    groups = [("5000", ACCENT, "억"), ("0000", YELLOW, "만"), ("0000", TEAL, "")]
    gap, size = 36, 150
    while True:  # 화면 폭(좌우 60px 여백) 안에 들어갈 때까지 줄임
        f = font(size)
        widths = [d.textlength(g, font=f) for g, _, _ in groups]
        unit = d.textlength("원", font=f)
        if sum(widths) + gap * 2 + unit + 40 <= W - 120:
            break
        size -= 4
    fl = font(84)
    x = (W - (sum(widths) + gap * 2 + unit)) / 2
    show = min(3, 1 + i // 12)  # 묶음이 하나씩 나타남
    for k, ((g, c, lab), w) in enumerate(zip(groups, widths)):
        if k < show:
            d.rounded_rectangle([x - 10, 780, x + w + 10, 990], 24, outline=c, width=6)
            d.text((x, 790), g, font=f, fill=c)
            if lab:
                lw = d.textlength(lab, font=fl)
                d.text((x + (w - lw) / 2, 1020), lab, font=fl, fill=c)
        x += w + gap
    if show == 3:
        d.text((x - gap + 10, 790), "원", font=f, fill=WHITE)
    return img


def app_frame(shot, cap_lines, tag="실제 실행 화면"):
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    series_tag(d)
    caption(d, cap_lines)
    app = Image.open(shot).convert("RGB").crop((0, 0, 900, APP_CROP))
    mask = Image.new("L", app.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, app.width - 1, app.height - 1], 36, fill=255)
    img.paste(app, (APP_X, APP_Y), mask)
    tf = font(28, 700)
    tw = d.textlength(tag, font=tf)
    d.rounded_rectangle([APP_X + 24, APP_Y - 58, APP_X + 24 + tw + 40, APP_Y - 12], 22, fill=ACCENT)
    d.text((APP_X + 44, APP_Y - 54), tag, font=tf, fill=WHITE)
    return img


def quiz_frame(i):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    series_tag(d, dark=False)
    center_text(d, 560, "그럼 이건?", font(70, 700), (90, 92, 100))
    f = fit("1억 1000만 1원", 940, 150)
    center_text(d, 740, "1억 1000만 1원", f, INK)
    center_text(d, 1000, "어떻게 읽어요?", font(92), INK)
    if i >= 20:
        f2 = font(78)
        t = "댓글로 알려 주세요!"
        tw = d.textlength(t, font=f2)
        d.rounded_rectangle([(W - tw) / 2 - 40, 1180, (W + tw) / 2 + 40, 1310], 40, fill=ACCENT)
        center_text(d, 1192, t, f2, WHITE)
    return scaled(img, pop(i))


# ── 오디오 (전부 코드 합성) ─────────────────────────────────────────

def env(n, a=0.005, r=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / r)


def tone(freq, dur, r=0.25, kind="sine", amp=0.3):
    n = int(dur * SR)
    t = np.arange(n) / SR
    if kind == "tri":
        w = 2 / np.pi * np.arcsin(np.sin(2 * np.pi * freq * t))
    else:
        w = np.sin(2 * np.pi * freq * t)
    return amp * w * env(n, r=r)


def add(buf, sig, at):
    s = int(at * SR)
    e = min(len(buf), s + len(sig))
    if s < len(buf):
        buf[s:e] += sig[: e - s]


def midi(m):
    return 440 * 2 ** ((m - 69) / 12)


def make_audio(path, key_times, ding_times, twist_t, quiz_t, total):
    buf = np.zeros(int(total * SR))
    bpm, beat = 116, 60 / 116
    rng = np.random.default_rng(3)
    chords = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]  # Am F C G
    bass = [45, 41, 36, 43]
    t, k = 0.0, 0
    while t < total - 0.05:
        bar = int(t / (beat * 4)) % 4
        quiet = twist_t <= t < twist_t + beat * 2  # 반전에서 음악을 잠깐 멈춤
        if not quiet:
            n = int(0.18 * SR)  # 킥
            tt = np.arange(n) / SR
            if k % 2 == 0:
                add(buf, 0.55 * np.sin(2 * np.pi * (50 + 90 * np.exp(-tt * 30)) * tt) * env(n, r=0.12), t)
            add(buf, 0.05 * rng.standard_normal(int(0.04 * SR)) * env(int(0.04 * SR), a=0.001, r=0.01), t + beat / 2)  # 하이햇
            add(buf, tone(midi(bass[bar]), beat * 0.9, r=0.3, kind="tri", amp=0.22), t)
            note = chords[bar][k % 3] + 12
            add(buf, tone(midi(note), beat * 0.6, r=0.12, amp=0.10), t)
            add(buf, tone(midi(note + 12), beat * 0.4, r=0.08, amp=0.04), t + beat / 2)
        t += beat
        k += 1
    for kt in key_times:  # 타자 소리
        n = int(0.025 * SR)
        add(buf, 0.10 * rng.standard_normal(n) * env(n, a=0.0005, r=0.006), kt)
    for dt in ding_times:  # 결과 등장
        add(buf, tone(midi(84), 0.5, r=0.18, amp=0.22) + tone(midi(91), 0.5, r=0.15, amp=0.10), dt)
    # 반전: 내려가는 '뿅'
    n = int(0.45 * SR)
    tt = np.arange(n) / SR
    add(buf, 0.28 * np.sin(2 * np.pi * np.cumsum(700 * np.exp(-tt * 5) + 120) / SR) * env(n, r=0.25), twist_t)
    # 문제 카드: 올라가는 화음
    for j, m in enumerate([69, 72, 76, 81]):
        add(buf, tone(midi(m), 1.2, r=0.5, amp=0.12), quiz_t + j * 0.06)
    fade = int(0.6 * SR)
    buf[-fade:] *= np.linspace(1, 0, fade)
    buf /= max(1e-9, np.abs(buf).max()) / 0.8
    stereo = np.stack([buf, buf], axis=1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((stereo * 32767).astype("<i2").tobytes())


# ── 썸네일 ────────────────────────────────────────────────────────

def thumbnail(path):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    center_text(d, 560, "VANTA WORKS · ARTIFACT EP.03", font(34, 700), (120, 120, 120))
    f = fit("500,000,000,000원", 960, 150)
    number_with_commas(d, 760, "500,000,000,000원", f, ACCENT, base=INK)
    t = "3초 안에 읽어 보세요"
    f2 = font(84)
    tw = d.textlength(t, font=f2)
    d.rounded_rectangle([(W - tw) / 2 - 44, 1010, (W + tw) / 2 + 44, 1150], 44, fill=INK)
    center_text(d, 1024, t, f2, WHITE)
    img.save(path)


# ── 조립 ──────────────────────────────────────────────────────────

def main(work: Path, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    frames = work / "frames"
    frames.mkdir(exist_ok=True)
    for old in frames.glob("*.png"):
        old.unlink()
    man = json.loads((work / "app" / "manifest.json").read_text())
    n = 0
    key_times, ding_times = [], []

    def put(img, count=1):
        nonlocal n
        for _ in range(count):
            img.save(frames / f"{n:04d}.png", compress_level=1)
            n += 1

    for i in range(90):
        put(hook_frame(i))
    for i in range(60):
        put(hint_frame(i))
    # 장면마다 [결과 전 자막, 결과 뒤 자막]. 'after'번째 결과가 뜬 뒤에 바뀜(답을 미리 보여 주지 않게)
    caps = {
        "answer": {"after": 1, "before": [("프로그램한테 읽혀 보면?", None)], "then": [("정답: 오천억 원", YELLOW)]},
        "made": {"after": 0, "before": [("AI랑 만든", None), ("숫자 읽기 프로그램", None)], "then": None},
        "twist": {"after": 2, "before": [("그럼 만 원은?", None)], "then": [("근데… 같은 만 원을", None), ("다르게 읽었다", YELLOW)]},
    }
    for name in ("answer", "made", "twist"):
        prev, shown = None, 0
        for shot, hold in man["scenes"][name]:
            t0 = n / FPS
            if hold == 2:
                key_times.append(t0)
            if prev == 4:  # 버튼 누른 다음 화면 = 결과 등장
                ding_times.append(t0)
                shown += 1
            c = caps[name]
            lines = c["then"] if c["then"] and shown >= c["after"] else c["before"]
            put(app_frame(work / "app" / shot, lines), hold)
            prev = hold
    twist_t = ding_times[-1]  # 반전 = '1만 원 → 일만 원'이 뜨는 순간
    quiz_t = n / FPS
    for i in range(120):
        put(quiz_frame(i))
    total = n / FPS
    assert n == 600, n

    wav = work / "bgm.wav"
    make_audio(wav, key_times, ding_times, twist_t, quiz_t, total)
    mp4 = out / "EP03_억단위읽기_1080x1920.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "%04d.png"), "-i", str(wav),
        "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow", "-r", str(FPS),
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", "-shortest", str(mp4)], check=True)
    thumbnail(out / "EP03_썸네일_1080x1920.png")
    picks = [10, 140, 230, 300, 400, 470, 560, 599]  # 장면 미리보기 8컷 (4×2)
    tw, th = W // 4, H // 4
    sheet = Image.new("RGB", (tw * 4, th * 2), INK)
    for k, fr in enumerate(picks):
        sheet.paste(Image.open(frames / f"{fr:04d}.png").resize((tw, th)), ((k % 4) * tw, (k // 4) * th))
    sheet.save(out / "EP03_장면미리보기.png")
    print(f"{n}프레임 · {total:.2f}초 · 결과 등장 {', '.join(f'{t:.2f}s' for t in ding_times)} · 반전 {twist_t:.2f}s · 문제 {quiz_t:.2f}s")
    print(mp4)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
