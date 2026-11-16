"""EP.05 「잔향의 카나리아」 OP 애니마틱 릴스 렌더.

record.py가 뽑은 실제 애니마틱 프레임(1280×720)과 원곡 가이드 트랙에서 여섯 구간을 골라
9:16 카드 틀 안에 붙입니다. 자르는 지점은 원곡 박자(0.4초, 5초 시작)에 맞춰 음악이 튀지 않게 했습니다.

    python content/ep05/record.py <work> '[[0,60]]'
    python content/ep05/render.py <work> <out_dir>
"""
import importlib.util
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ep03r", HERE.parent / "ep03" / "render.py")
ep03 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ep03)
font, fit = ep03.font, ep03.fit

W, H, FPS, SR = 1080, 1920, 30, 48000
INK, PAPER, WHITE, GREY, LINE = (14, 16, 22), (246, 243, 236), (255, 255, 255), (150, 156, 168), (60, 64, 76)
GOLD, RED, TEAL = (246, 196, 60), (226, 72, 52), (40, 150, 150)
VY = 640  # 영상 위치
# (원본 시작, 끝, 장면 이름, 자막 두 줄, 강조 줄 번호)
SEGS = [
    (33.0, 37.0, "레조넌스", ["AI와 애니메이션", "오프닝을 만들어봤다"], 1),
    (5.0, 9.0, "타이틀", ["그림 파일 없이", "전부 코드로 그렸어요"], 1),
    (11.0, 17.0, "크루", ["캐릭터 다섯 명,", "한 명당 2초 컷인"], 1),
    (42.2, 48.2, "무타", ["2초 동안 소리를 끈 것도", "계산해서 넣은 연출"], 1),
    (51.0, 56.0, "라이벌", ["배경 재즈도", "코드로 합성했어요"], 1),
    (56.2, 60.0, "엔드 카드", ["60초짜리", "가편집본(애니마틱)이에요"], 1),
]
OUTRO = 3.2
TAG = "VANTA WORKS · ARTIFACT EP.05"


def ctext(d, y, t, f, fill, stroke=0):
    x0, _, x1, _ = d.textbbox((0, 0), t, font=f)
    d.text(((W - (x1 - x0)) / 2 - x0, y), t, font=f, fill=fill, stroke_width=stroke, stroke_fill=INK)


def chrome(d, no, total, dark=True):
    col = GREY if dark else (110, 112, 120)
    d.text((90, 236), TAG, font=font(30, 700), fill=col)
    pg = f"{no:02d} / {total:02d}"
    d.text((W - 90 - d.textlength(pg, font=font(30, 700)), 236), pg, font=font(30, 700), fill=col)
    d.line([90, 290, W - 90, 290], fill=LINE if dark else (222, 216, 204), width=3)
    gap = 26
    x0 = (W - (total - 1) * gap) / 2
    for k in range(total):
        r = 9 if k + 1 == no else 6
        cx = x0 + k * gap
        on = WHITE if dark else INK
        d.ellipse([cx - r, 1555 - r, cx + r, 1555 + r], fill=on if k + 1 == no else LINE if dark else (222, 216, 204))


SCENE_TICKS = [5, 11, 21, 28, 37, 42, 51, 56]


def seg_frame(src: Image.Image, seg, no, total, i):
    a, b, name, cap, hi = seg
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    chrome(d, no, total)
    for k, line in enumerate(cap):
        f = fit(line, 900, 80)
        if i < 3:  # 첫 3프레임 살짝 튀어나옴
            f = fit(line, 900, int(80 * (0.9 + 0.033 * i)))
        ctext(d, 340 + k * 104, line, f, GOLD if k == hi else WHITE, stroke=5)
    v = src.resize((W, int(W * 720 / 1280)), Image.LANCZOS)
    img.paste(v, (0, VY))
    d.rectangle([0, VY - 4, W, VY - 1], fill=LINE)
    d.rectangle([0, VY + v.height, W, VY + v.height + 3], fill=LINE)
    f = font(28, 700)
    t = "실제 애니마틱 화면"
    tw = d.textlength(t, font=f)
    d.rounded_rectangle([90, VY + v.height + 30, 130 + tw, VY + v.height + 76], 22, fill=(255, 90, 31))
    d.text((110, VY + v.height + 34), t, font=f, fill=WHITE)
    tc = f"{int(a) // 60}:{int(a) % 60:02d} {name}"
    d.text((150 + tw, VY + v.height + 34), tc, font=font(30, 700), fill=GREY)
    # 60초 오프닝 안에서 지금 보는 위치
    ty, x0, x1 = 1430, 90, W - 90
    d.text((x0, ty - 58), "60초 오프닝 중 지금 여기", font=font(30, 700), fill=GREY)
    d.rounded_rectangle([x0, ty, x1, ty + 16], 8, fill=LINE)
    for s_ in SCENE_TICKS:
        x = x0 + (x1 - x0) * s_ / 60
        d.line([x, ty - 6, x, ty + 22], fill=(90, 96, 110), width=2)
    sx, ex = x0 + (x1 - x0) * a / 60, x0 + (x1 - x0) * b / 60
    d.rounded_rectangle([sx, ty, ex, ty + 16], 8, fill=GOLD)
    px = x0 + (x1 - x0) * (a + i / FPS) / 60
    d.ellipse([px - 14, ty - 6, px + 14, ty + 22], fill=WHITE)
    d.text((x0, ty + 34), "0:00", font=font(26, 700), fill=GREY)
    d.text((x1 - d.textlength("1:00", font=font(26, 700)), ty + 34), "1:00", font=font(26, 700), fill=GREY)
    return img


def outro(i, total):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    chrome(d, total, total, dark=False)
    ctext(d, 560, "이 오프닝에", font(96), INK)
    ctext(d, 690, "어울리는 노래는?", font(96), INK)
    if i >= 10:
        t = "댓글로 추천해 주세요"
        f = font(66)
        tw = d.textlength(t, font=f)
        d.rounded_rectangle([(W - tw) / 2 - 44, 880, (W + tw) / 2 + 44, 1010], 42, fill=RED)
        ctext(d, 892, t, f, WHITE)
    for k, l in enumerate(["'잔향의 카나리아' OP 애니마틱 · 방송 작품이 아닌 가편집본",
                           "그림은 HTML 캔버스, 음악은 웹 오디오 코드로 Claude와 함께 만들었어요"]):
        ctext(d, 1180 + k * 52, l, fit(l, 920, 32, 400), (90, 92, 100))
    return img


def load_wav(p: Path):
    with wave.open(str(p)) as w:
        assert w.getframerate() == SR and w.getnchannels() == 2
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).astype(np.float32) / 32768


def main(work: Path, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    cap = json.loads((work / "capture.json").read_text(encoding="utf-8"))
    assert cap["segments"] == [[0, 60]] and not cap["page_errors"], cap
    names = {s["name"] for s in cap["scenes"]}
    for a, b, name, *_ in SEGS:
        sc = next(s for s in cap["scenes"] if s["a"] <= a < s["b"])
        assert sc["name"] == name, (a, sc["name"], name)  # 자막의 장면 이름이 원본과 같은지
        assert abs(((a - 5) / 0.4) - round((a - 5) / 0.4)) < 1e-6 or a < 5, a  # 박자 위에서 자름
    src = work / "src_frames"
    frames = work / "frames"
    frames.mkdir(exist_ok=True)
    for old in frames.glob("*.png"):
        old.unlink()
    total_cards = len(SEGS) + 1
    n = 0
    guide = load_wav(work / "guide.wav")
    pieces = []
    for no, seg in enumerate(SEGS, 1):
        a, b = seg[0], seg[1]
        cnt = int(round((b - a) * FPS))
        for i in range(cnt):
            k = int(round(a * FPS)) + i
            seg_frame(Image.open(src / f"s0_{k:04d}.jpg").convert("RGB"), seg, no, total_cards, i).save(frames / f"{n:04d}.png", compress_level=1)
            n += 1
        piece = guide[int(round(a * SR)):int(round(a * SR)) + cnt * SR // FPS].copy()
        fade = int(0.012 * SR)
        piece[:fade] *= np.linspace(0, 1, fade)[:, None]
        piece[-fade:] *= np.linspace(1, 0, fade)[:, None]
        pieces.append(piece)
    oc = int(OUTRO * FPS)
    for i in range(oc):
        outro(i, total_cards).save(frames / f"{n:04d}.png", compress_level=1)
        n += 1
    tail = guide[int(60.0 * SR):int(60.0 * SR) + oc * SR // FPS].copy()  # 엔드 카드 뒤 여운(원곡 그대로)
    if len(tail) < oc * SR // FPS:
        tail = np.vstack([tail, np.zeros((oc * SR // FPS - len(tail), 2), np.float32)])
    tail *= np.linspace(1, 0, len(tail))[:, None]
    pieces.append(tail)
    audio = np.vstack(pieces)
    wav = work / "reel.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())
    meas = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(wav), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                           "-f", "null", "-"], capture_output=True, text=True).stderr
    m = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
    ln = ("loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I={input_i}:measured_TP={input_tp}:"
          "measured_LRA={input_lra}:measured_thresh={input_thresh}:offset={target_offset}").format(**m)
    mp4 = out / "EP05_잔향의카나리아_1080x1920.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "%04d.png"), "-i", str(wav),
        "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow", "-r", str(FPS),
        "-af", ln + ",alimiter=limit=0.71:level=false", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", "-shortest", str(mp4)], check=True)
    picks, acc = [], 0
    for seg in SEGS:
        cnt = int(round((seg[1] - seg[0]) * FPS))
        picks.append(acc + cnt // 2)
        acc += cnt
    picks += [acc + oc - 1]
    tw, th = W // 4, H // 4
    sheet = Image.new("RGB", (tw * 4, th * 2), INK)
    for k, fr in enumerate(picks[:8]):
        sheet.paste(Image.open(frames / f"{fr:04d}.png").resize((tw, th)), ((k % 4) * tw, (k // 4) * th))
    sheet.save(out / "EP05_장면미리보기.png")
    Image.open(frames / f"{picks[0]:04d}.png").save(out / "EP05_커버후보_1080x1920.png")
    print(f"{n}프레임 · {n / FPS:.2f}초")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
