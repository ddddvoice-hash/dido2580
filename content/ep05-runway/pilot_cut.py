"""30초 파일럿 「기억 하나」 — 카나 없는 가편집 (v3 콘티에서 카나 컷 제외).

새 이미지 생성 없음. 소재: 애니마틱 원본 프레임(테이프 장면은 라벨 날짜 2051.06.21 수정본),
편집 그래픽(글자 카드·섬광·암전), 애니마틱 원곡 가이드 트랙.
카나가 나오는 구간은 쓰지 않는다: 크루 컷인 13~15초(KANA), 레조넌스 29.8~33초(KANA·REC 창).

    python content/ep05-runway/pilot_cut.py <old_frames_dir> <new_tape_frames_dir> <guide.wav> <work> <out_dir>
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
BLACK, CREAM, GREY = (8, 9, 12), (240, 230, 205), (120, 124, 134)
VY = (H - 608) // 2
KANA_RANGES = [(13.0, 15.0), (29.8, 34.4)]  # 크루 KANA 컷인 / KANA·REC 창(33초 이후 사라지는 잔상 포함)

# (종류, 값, 릴스 길이초). src = 애니마틱 원본 구간(시작, 끝). 박자(5초 시작, 0.4초) 위에서 자름
EDL = [
    ("src", (1.0, 4.0), "테이프 — 2051.06.21 라벨, 41년 전 노래"),
    ("src", (42.2, 44.2), "무타 부상 → 무음"),
    ("card", "노래 한 곡.", 1.0),
    ("card", "기억 하나.", 1.0),
    ("src", (28.2, 29.8), "송 테이프 장전, PLAY 1/3"),
    ("src", (37.4, 39.8), "렌의 눈 — 파형 각성 (금색 로봇은 마지막 카운터 컷에서 처음 공개)"),
    ("src", (11.4, 12.2), "크루: 렌"),
    ("src", (15.4, 16.2), "크루: 시즈"),
    ("src", (17.4, 18.2), "크루: 겐"),
    ("src", (19.4, 20.2), "크루: 치치"),
    ("src", (23.0, 25.4), "발진"),
    ("src", (51.0, 53.4), "라이벌 대치"),
    ("flash", None, 2 / FPS),
    ("black", None, 2.0 - 2 / FPS),
    ("src", (45.4, 48.4), "결정 창 관통 → 금빛 확산"),
    ("src", (35.0, 37.0), "MEMORY 1,024 → 1,023 (단 한 번)"),
    ("src", (56.2, 60.0), "엔드 카드"),
    ("hold", None, 0.2),
]


def letterbox(frame: Image.Image):
    img = Image.new("RGB", (W, H), BLACK)
    img.paste(frame.resize((W, 608), Image.LANCZOS), (0, VY))
    d = ImageDraw.Draw(img)
    t = "잔향의 카나리아 · 파일럿 가편집"
    d.text(((W - d.textlength(t, font=font(26, 700))) / 2, VY + 608 + 60), t, font=font(26, 700), fill=GREY)
    return img


def card(text):
    img = Image.new("RGB", (W, H), BLACK)
    d = ImageDraw.Draw(img)
    f = fit(text, 900, 150)
    x0, y0, x1, y1 = d.textbbox((0, 0), text, font=f)
    d.text(((W - (x1 - x0)) / 2 - x0, (H - (y1 - y0)) / 2 - y0), text, font=f, fill=CREAM)
    return img


def main(old: Path, tape: Path, guide_wav: Path, work: Path, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    frames = work / "pilot_frames"
    frames.mkdir(parents=True, exist_ok=True)
    for f in frames.glob("*.png"):
        f.unlink()
    with wave.open(str(guide_wav)) as w:
        guide = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).astype(np.float32) / 32768
    n, pieces, log = 0, [], []

    def put(img, count):
        nonlocal n
        for _ in range(count):
            img.save(frames / f"{n:04d}.png", compress_level=1)
            n += 1

    for kind, val, info in EDL:
        t0 = n / FPS
        if kind == "src":
            a, b = val
            for ka, kb in KANA_RANGES:
                assert b <= ka or a >= kb, f"카나 구간 사용 금지: {val}"
            assert a < 5 or abs((a - 5) / 0.4 - round((a - 5) / 0.4)) < 1e-6, f"박자 밖: {a}"
            cnt = int(round((b - a) * FPS))
            for i in range(cnt):
                k = int(round(a * FPS)) + i
                src = (tape if a < 5 else old) / f"s0_{k:04d}.jpg"
                put(letterbox(Image.open(src).convert("RGB")), 1)
            p = guide[int(round(a * SR)):int(round(a * SR)) + cnt * SR // FPS].copy()
            fd = int(0.01 * SR)
            p[:fd] *= np.linspace(0, 1, fd)[:, None]
            p[-fd:] *= np.linspace(1, 0, fd)[:, None]
            pieces.append(p)
        else:
            cnt = int(round(info * FPS))  # info = 길이(초)
            img = card(val) if kind == "card" else Image.new("RGB", (W, H), (255, 255, 255) if kind == "flash" else BLACK)
            if kind == "hold":
                img = Image.open(frames / f"{n - 1:04d}.png")
            put(img, cnt)
            if kind == "flash":  # 충돌음: 원곡의 충돌 지점(46.3초)에서 가져옴
                hit = guide[int(46.3 * SR):int(46.3 * SR) + cnt * SR // FPS].copy()
                pieces.append(hit)
            else:
                pieces.append(np.zeros((cnt * SR // FPS, 2), np.float32))
            info = f"{kind} {val or ''}".strip()
        log.append({"t": round(t0, 2), "what": info, "src": val if kind == "src" else None})
    audio = np.vstack(pieces)
    wav = work / "pilot.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())
    meas = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(wav), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                           "-f", "null", "-"], capture_output=True, text=True).stderr
    m = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
    ln = ("loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I={input_i}:measured_TP={input_tp}:"
          "measured_LRA={input_lra}:measured_thresh={input_thresh}:offset={target_offset}").format(**m)
    mp4 = out / "pilot30_카나제외_가편집_1080x1920.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "%04d.png"), "-i", str(wav),
                    "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow", "-r", str(FPS),
                    "-af", ln + ",alimiter=limit=0.71:level=false", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-movflags", "+faststart", "-shortest", str(mp4)], check=True)
    (out / "pilot30_편집표.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{n}프레임 · {n / FPS:.2f}초")


if __name__ == "__main__":
    main(*[Path(a) for a in sys.argv[1:6]])
