"""30초 파일럿 「기억 하나」 — 카나 없는 가편집 v2 (전환 연출 반영).

새 이미지 생성 없음. 소재: 애니마틱 원본 프레임(테이프 장면은 라벨 2051.06.21 수정본),
편집 그래픽(글자 카드·섬광·암전·입자), 애니마틱 원곡 가이드 트랙.
카나 구간은 쓰지 않는다: 크루 컷인 13~15초(KANA), 레조넌스 29.8~34.4초(KANA·REC 창과 잔상).

전환(GPT 지시 #34 6921666217 → Claude 편집 구현)
  ① 테이프→무타: 오른쪽 릴로 파고들기 → 컷 → 무타 확대 상태에서 빠져나오기, 테이프 히스 0.3초 잔향
  ③ 타이포 브릿지: Black Han Sans, 흑백+적색. 마지막 글자가 사라지는 순간 삽입음+브라스
  ④ 시선 매치컷: 렌의 동공으로 파고들기 → 카이토의 흰 눈에서 빠져나오기
  ⑤ 충돌→회복: 2프레임 섬광 → 2초 암전 속 희미한 금빛 입자 → 금빛 확산

    python content/ep05-runway/pilot_cut.py <old_frames> <new_tape_frames> <guide.wav> <work> <out_dir>
"""
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
NSK = str(HERE.parent / "ep03" / "app" / "fonts" / "nsk-700.ttf")
BHS_FILES = sorted((HERE / "fonts").glob("bhs_*.ttf"))  # Black Han Sans(OFL) 글자 묶음별 파일
BHS_CMAP = {p: set(TTFont(str(p)).getBestCmap()) for p in BHS_FILES}

W, H, FPS, SR = 1080, 1920, 30, 48000
SW, SH = 1280, 720  # 애니마틱 원본 크기
BLACK, WHITE, RED, GREY, GOLD = (8, 9, 12), (244, 240, 230), (226, 48, 40), (120, 124, 134), (246, 196, 60)
VY = (H - 608) // 2
KANA_RANGES = [(13.0, 15.0), (29.8, 34.4)]

# 매치컷 기준점(원본 1280×720 좌표, 격자 측정)
REEL = (728, 372)        # 카세트 오른쪽 릴
MUTA = (640, 640)        # 떠오르는 무타 몸통 위쪽
PUPIL = (640, 360)       # 렌의 동공
KAITO_EYE = (1000, 254)  # 카이토 흰 눈
ZMAX = 4.0

# (종류, 값, 정보/길이, 옵션)
EDL = [
    ("src", (1.0, 4.0), "테이프", {"zoom_out_to": (REEL, 0.6)}),
    ("src", (42.2, 44.2), "무타 부상 → 무음", {"zoom_in_from": (MUTA, 0.6), "tail_from_prev": 0.3}),
    ("card", ("노래 한 곡.", None), 1.0, {}),
    ("card", ("기억 하나.", "기억"), 1.0, {"vanish": True}),
    ("src", (28.2, 29.8), "송 테이프 장전 PLAY 1/3", {"hit_at_start": True}),
    ("src", (11.4, 12.2), "크루: 렌", {}),
    ("src", (15.4, 16.2), "크루: 시즈", {}),
    ("src", (17.4, 18.2), "크루: 겐", {}),
    ("src", (19.4, 20.2), "크루: 치치", {}),
    ("src", (23.0, 25.4), "발진", {}),
    ("src", (37.4, 39.8), "렌의 눈 — 파형 각성", {"zoom_out_to": (PUPIL, 0.5)}),
    ("src", (51.0, 53.4), "라이벌 대치", {"zoom_in_from": (KAITO_EYE, 0.6)}),
    ("flash", None, 2 / FPS, {}),
    ("black", None, 2.0 - 2 / FPS, {"particles": True}),
    ("src", (45.4, 48.4), "결정 창 관통 → 금빛 확산", {}),
    ("src", (35.0, 37.0), "MEMORY 1,024 → 1,023 (단 한 번), 금색 로봇 첫 공개", {}),
    ("src", (56.2, 60.0), "엔드 카드", {}),
    ("hold", None, 0.2, {}),
]


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def zoom(frame, center, z):
    if z <= 1.001:
        return frame
    w, h = SW / z, SH / z
    x0 = min(max(center[0] - w / 2, 0), SW - w)
    y0 = min(max(center[1] - h / 2, 0), SH - h)
    return frame.resize((SW, SH), Image.LANCZOS, box=(x0, y0, x0 + w, y0 + h))


def letterbox(frame):
    img = Image.new("RGB", (W, H), BLACK)
    img.paste(frame.resize((W, 608), Image.LANCZOS), (0, VY))
    d = ImageDraw.Draw(img)
    t = "잔향의 카나리아 · 파일럿 가편집"
    f = ImageFont.truetype(NSK, 26)
    d.text(((W - d.textlength(t, font=f)) / 2, VY + 608 + 60), t, font=f, fill=GREY)
    return img


_cache = {}


def bhs_font(ch, size):
    for p in BHS_FILES:
        if ord(ch) in BHS_CMAP[p]:
            if (p, size) not in _cache:
                _cache[(p, size)] = ImageFont.truetype(str(p), size)
            return _cache[(p, size)]
    raise SystemExit(f"Black Han Sans에 없는 글자: {ch!r}")


def draw_bhs(d, text, size, y, red_word=None, alpha=1.0, full=None):
    """글자마다 해당 묶음 폰트로 그림. full이 있으면 전체 문장 기준으로 가운데 정렬(사라지는 중에도 위치 고정)."""
    base = full or text
    widths = [d.textlength(c, font=bhs_font(c, size)) for c in base]
    x = (W - sum(widths)) / 2
    red_idx = set()
    if red_word and red_word in base:
        s = base.index(red_word)
        red_idx = set(range(s, s + len(red_word)))
    for i, (c, w) in enumerate(zip(base, widths)):
        if i < len(text):
            col = RED if i in red_idx else WHITE
            col = tuple(int(BLACK[k] + (col[k] - BLACK[k]) * alpha) for k in range(3))
            d.text((x, y), c, font=bhs_font(c, size), fill=col)
        x += w


def card(text, red_word, i, n, vanish):
    img = Image.new("RGB", (W, H), BLACK)
    d = ImageDraw.Draw(img)
    shown = text
    if vanish:  # 마지막 6프레임 동안 뒤에서부터 한 글자씩 사라짐
        k = max(0, i - (n - 6))
        shown = text[: max(0, len(text) - k)]
    draw_bhs(d, shown, 190, 800, red_word, full=text)
    draw_bhs(d, "ONE SONG. ONE MEMORY.", 46, 1060, alpha=0.55)
    return img


def particles(i, n):
    img = Image.new("RGB", (W, H), BLACK)
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(11)
    for _ in range(36):
        x, y, sp, r = rng.uniform(0, W), rng.uniform(VY, VY + 608), rng.uniform(20, 60), rng.uniform(1.5, 3.5)
        yy = y + sp * i / FPS
        a = 0.25 * ease(i / (n * 0.5)) * (0.6 + 0.4 * np.sin(i * 0.3 + x))
        col = tuple(int(BLACK[k] + (GOLD[k] - BLACK[k]) * a) for k in range(3))
        d.ellipse([x - r, yy - r, x + r, yy + r], fill=col)
    return img


def main(old, tape, guide_wav, work, out):
    out.mkdir(parents=True, exist_ok=True)
    frames = work / "pilot_frames"
    frames.mkdir(parents=True, exist_ok=True)
    for f in frames.glob("*.png"):
        f.unlink()
    with wave.open(str(guide_wav)) as w:
        guide = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).astype(np.float32) / 32768
    total = int(round(sum((v[1] - v[0]) if k == "src" else i for k, v, i, _ in EDL) * FPS))
    audio = np.zeros((total * SR // FPS + SR, 2), np.float32)
    n, log, prev_src_end = 0, [], None

    def put(img):
        nonlocal n
        img.save(frames / f"{n:04d}.png", compress_level=1)
        n += 1

    def mix(sig, at_frame):
        s = at_frame * SR // FPS
        e = min(len(audio), s + len(sig))
        audio[s:e] += sig[: e - s]

    for kind, val, info, opt in EDL:
        f0 = n
        if kind == "src":
            a, b = val
            for ka, kb in KANA_RANGES:
                assert b <= ka or a >= kb, f"카나 구간 사용 금지: {val}"
            assert a < 5 or abs((a - 5) / 0.4 - round((a - 5) / 0.4)) < 1e-6, f"박자 밖: {a}"
            cnt = int(round((b - a) * FPS))
            for i in range(cnt):
                k = int(round(a * FPS)) + i
                fr = Image.open((tape if a < 5 else old) / f"s0_{k:04d}.jpg").convert("RGB")
                if "zoom_out_to" in opt:  # 끝부분에서 기준점으로 파고들기
                    c, dur = opt["zoom_out_to"]
                    m = int(dur * FPS)
                    fr = zoom(fr, c, 1 + (ZMAX - 1) * ease((i - (cnt - m)) / m))
                if "zoom_in_from" in opt:  # 시작부분에서 기준점으로부터 빠져나오기
                    c, dur = opt["zoom_in_from"]
                    m = int(dur * FPS)
                    fr = zoom(fr, c, 1 + (ZMAX - 1) * (1 - ease(i / m)))
                put(letterbox(fr))
            p = guide[int(round(a * SR)):int(round(a * SR)) + cnt * SR // FPS].copy()
            fd = int(0.01 * SR)
            p[:fd] *= np.linspace(0, 1, fd)[:, None]
            p[-fd:] *= np.linspace(1, 0, fd)[:, None]
            mix(p, f0)
            if opt.get("tail_from_prev") and prev_src_end is not None:  # 앞 장면 소리의 잔향
                t = opt["tail_from_prev"]
                tail = guide[int(prev_src_end * SR):int((prev_src_end + t) * SR)].copy()
                tail *= np.linspace(0.8, 0, len(tail))[:, None]
                mix(tail, f0)
            if opt.get("hit_at_start"):  # 테이프 삽입 + 브라스 폭발(원곡 첫 스탭 5.0초)
                mix(guide[int(5.0 * SR):int(5.6 * SR)].copy() * 1.2, f0)
            prev_src_end = b
            what = info
        else:
            cnt = int(round(info * FPS))
            for i in range(cnt):
                if kind == "card":
                    put(card(val[0], val[1], i, cnt, opt.get("vanish")))
                elif kind == "flash":
                    put(Image.new("RGB", (W, H), (255, 255, 255)))
                elif kind == "black":
                    put(particles(i, cnt) if opt.get("particles") else Image.new("RGB", (W, H), BLACK))
                else:  # hold
                    put(Image.open(frames / f"{n - 1:04d}.png").copy())
            if kind == "flash":  # 충돌음: 원곡 46.3초
                mix(guide[int(46.3 * SR):int(46.9 * SR)].copy(), f0)
            what = f"{kind} {val[0] if kind == 'card' else ''}".strip()
        log.append({"t": round(f0 / FPS, 2), "what": what, "src": val if kind == "src" else None})
    audio = audio[: n * SR // FPS]
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
