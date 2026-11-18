"""30초 파일럿 「기억 하나」 — 카나 포함 완성 초안 (9:16 세로 전체 화면).

이미지·영상 생성 없음(편집만). 소재:
  - 애니마틱 3배 해상도 렌더(record.py ECHO_SCALE=3) 세로 자르기: 테이프·장전 HUD·크루·렌의 눈
  - GPT 이미지 A 카나 / B 도시 / F 렌 뒷모습 (1088×1920 → 1080 폭으로 자름)
  - Runway 무타를 Claude가 보정한 시험본(muta_edit_test)
  - GPT 라이벌 키프레임 D(074cb00f) — 검은 기체 머리만 크롭한 ECU(편집 푸시인·눈 밝기)
  - 디도 님 녹음: H1·H2(허밍2), L1(대사 테이크2) — 비공개 저장소에서 꺼내 인자로 받음
  - 편집 그래픽: 글자 카드, 섬광·암전·금빛 입자, 기억 카운터, 자막, 타이틀
타임라인: titus #34 6934663570 (30fps 900프레임)

    python content/ep05-runway/final_cut.py <hires_frames> <img_dir> <voice_dir> <clips_dir> <guide.wav> <work> <out_dir>
"""
import importlib.util
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("pc", HERE / "pilot_cut.py")
pc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pc)
FONT = {w: str(HERE.parent / "ep03" / "app" / "fonts" / f"nsk-{w}.ttf") for w in (400, 700, 900)}

W, H, FPS, SR = 1080, 1920, 30, 48000
BLACK, CREAM, GOLD, RED, GREY = (8, 9, 12), (240, 230, 205), (246, 196, 60), (226, 48, 40), (130, 134, 146)
SC = 3  # 애니마틱 렌더 배율 (3840×2160)
CW, CH = 1215, 2160  # 9:16 세로 자르기 크기(3배 좌표)


def f(size, w=900):
    return ImageFont.truetype(FONT[w], size)


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def vcrop(img, cx, cy=1080, zoom=1.0, focus=None):
    """3840×2160에서 (cx,cy) 중심 9:16을 잘라 1080×1920. zoom>1이면 focus 쪽으로 더 확대."""
    w, h = CW / zoom, CH / zoom
    if focus:
        cx = cx + (focus[0] - cx) * (1 - 1 / zoom)
        cy = cy + (focus[1] - cy) * (1 - 1 / zoom)
    x0 = min(max(cx - w / 2, 0), img.width - w)
    y0 = min(max(cy - h / 2, 0), img.height - h)
    return img.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + w, y0 + h))


def still(img, zoom=1.0, center=None):
    c = center or (W / 2, H / 2)
    w, h = W / zoom, H / zoom
    x0 = min(max(c[0] - w / 2, 0), W - w)
    y0 = min(max(c[1] - h / 2, 0), H - h)
    return img.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + w, y0 + h))


def ctext(d, y, t, font, fill, stroke=0):
    x0, _, x1, _ = d.textbbox((0, 0), t, font=font)
    d.text(((W - (x1 - x0)) / 2 - x0, y), t, font=font, fill=fill, stroke_width=stroke, stroke_fill=BLACK)


def particles_over(img, i, n, seed=7, count=60, alpha=0.9, big=False):
    layer = img.copy()
    d = ImageDraw.Draw(layer)
    rng = np.random.default_rng(seed)
    for _ in range(count):
        x, y, sp, r = rng.uniform(0, W), rng.uniform(-200, H), rng.uniform(80, 220), rng.uniform(4, 11) if big else rng.uniform(2, 6)
        yy = y + sp * i / FPS
        a = alpha * (0.5 + 0.5 * np.sin(i * 0.25 + x))
        col = tuple(int(img.getpixel((int(min(W - 1, max(0, x))), int(min(H - 1, max(0, yy)))))[k] * (1 - a) + GOLD[k] * a) for k in range(3))
        d.ellipse([x - r, yy - r, x + r, yy + r], fill=col)
    return layer


def main(hires, imgs, voice, clips, guide_wav, work, out):
    out.mkdir(parents=True, exist_ok=True)
    frames = work / "final_frames"
    frames.mkdir(parents=True, exist_ok=True)
    for p in frames.glob("*.png"):
        p.unlink()
    # 정지 이미지: 1088 → 1080 (양쪽 4px)
    load = lambda n: Image.open(imgs / n).convert("RGB").crop((4, 0, 1084, 1920))
    A = ImageOps.mirror(load("A_kana.png"))  # 렌(오른쪽을 봄)과 시선이 마주치게 좌우 반전
    B = load("B_city.png")
    F = load("F_ren.png")
    SUN = (540 - 4, 615)  # B의 해 중심(1080 기준)
    A_C = (1080 - 500 - 4, 560)  # 반전 후 카나 얼굴 중심 근처
    clipframes = {}
    for name in ("muta_edit_test",):
        d = work / name
        d.mkdir(exist_ok=True)
        for p in d.glob("*.png"):
            p.unlink()
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(clips / f"{name}.mp4"), str(d / "%03d.png")], check=True)
        clipframes[name] = sorted(d.glob("*.png"))
    hf = lambda seg, k: Image.open(hires / f"s{seg}_{k:04d}.jpg").convert("RGB")

    n = 0
    log = []

    def put(img, note=None):
        nonlocal n
        if note:
            log.append({"frame": n, "t": round(n / FPS, 3), "what": note})
        img.save(frames / f"{n:04d}.png", compress_level=1)
        n += 1

    # 0–44 암전 + 테이프 라벨 글자만 (애니마틱 릴 삭제 — 창작 QC #6950456358). 소리는 가이드 트랙의 테이프 삽입음 그대로
    for i in range(45):
        im = Image.new("RGB", (W, H), BLACK)
        al = min(1, i / 12) * min(1, (44 - i) / 10)
        d = ImageDraw.Draw(im)
        c = tuple(int(v * al) for v in CREAM)
        ctext(d, 940, "SHIRATORI · 2051.06.21 · SIDE A", f(44, 700), c)
        put(im, "암전 + 테이프 라벨" if i == 0 else None)
    # 45–104 A 카나 — 아주 느린 밀기
    for i in range(60):
        put(still(A, 1.45 + 0.06 * ease(i / 59), A_C), "A 카나 + H1 허밍" if i == 0 else None)
    # 105–164 B 멈춘 도시 — 해에서 빠져나옴(릴 매치컷)
    for i in range(60):
        put(still(B, 1 + 3.0 * (1 - ease(i / 15)), SUN), "B 멈춘 도시 — 무음" if i == 0 else None)
    # 165–239 C 무타 (보정본 75프레임)
    for i, p in enumerate(clipframes["muta_edit_test"][:75]):
        put(Image.open(p).convert("RGB"), "C 무타" if i == 0 else None)
    # 240–299 글자 카드
    for i in range(30):
        put(pc.card("노래 한 곡.", None, i, 30, False), "글자 카드" if i == 0 else None)
    for i in range(30):
        put(pc.card("기억 하나.", "기억", i, 30, True))
    # 300–569 v4 (11/18 대표 지시): 포스터 크롭 폐기 → 캐릭터 시트 트럭 + 대치 컷(0f3a1613, 대표 지정)
    def ecrop(img, cx, cy, w):
        h = w * 16 / 9
        box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
        assert box[0] >= -0.5 and box[1] >= -0.5 and box[2] <= img.width + 0.5 and box[3] <= img.height + 0.5, box
        return img.transform((W, H), Image.EXTENT, box, Image.BICUBIC)

    # 300–431 크루: 시트(1920×1088) 위 가로 트럭, 336·360·384에 박자 스냅(가이드 트랙 스탭과 같은 프레임)
    SH = Image.open(imgs / "sheet_clean_c6f70a29.png").convert("RGB")
    assert SH.size == (1920, 1088)
    SW = 1088 * 9 / 16  # 612
    cxs = [306, 716, 1137, 1614]  # 패널 중심(양끝은 화면 안으로 고정)
    starts = [300, 336, 360, 384]
    for fr in range(300, 432):
        k = max(j for j, s in enumerate(starts) if fr >= s)
        s0 = starts[k]
        if k == 0:
            cx = 306 + 40 * (1 - ease((fr - 300) / 35))  # 들어오며 감속
            punch = 0.0
        else:
            m = ease((fr - s0) / 6)  # 6프레임 스냅
            cx = cxs[k - 1] + (cxs[k] - cxs[k - 1]) * m
            punch = 0.04 * (1 - ease((fr - s0 - 6) / 14)) if fr - s0 >= 6 else 0.04 * m
        if k == 3 and fr >= 408:
            punch = 0.03 * ease((fr - 408) / 23)  # 마지막 패널은 천천히 밀기
        w = SW / (1 + punch)
        cx = min(max(cx, w / 2), 1920 - w / 2)
        put(ecrop(SH, cx, 544, w), f"시트 패널 {k + 1}" if fr == s0 else None)
    # 432–479 대치 컷: 금색 기체 머리에서 빠지며 뒤의 검은 기체를 드러냄(움직임 하나: 뒤로 빠지기)
    FO = Image.open(imgs / "face_off_a1ab35b5.png").convert("RGB")
    assert FO.size == (1088, 1920)
    for i in range(48):
        k = ease(i / 47)
        cx, cy, w = 300 + (544 - 300) * k, 1000 + (960 - 1000) * k, 520 + (1080 - 520) * k
        put(ecrop(FO, cx, cy, w), "대치 컷 — 금색 기체에서 빠지기" if i == 0 else None)
    # 480–569 라이벌 Runway 클립(1c76703d, 대표 지정) — 첫 불꽃 구간(광과민)은 버리고 2.0초 이후의 정지 대치만,
    # 두 기체 사이 경계로 아주 느리게 밀다가 570 섬광으로 충돌
    rv = work / "rival_src"
    rv.mkdir(exist_ok=True)
    for p_ in rv.glob("*.png"):
        p_.unlink()
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(clips / "rival_runway_1c76703d.mp4"), str(rv / "%03d.png")], check=True)
    rframes = sorted(rv.glob("*.png"))
    assert len(rframes) == 121
    for i in range(90):
        src = Image.open(rframes[min(120, round((2.0 + i / 30) * 24))]).convert("RGB").resize((W, H), Image.LANCZOS)
        put(still(src, 1.0 + 0.06 * ease(i / 89), (W / 2, H * 0.45)), "라이벌 대치(Runway, 2초 이후)" if i == 0 else None)
    # 570–571 섬광, 572–631 암전+입자 (정확히 2.000초 무음)
    for i in range(2):
        put(Image.new("RGB", (W, H), (255, 255, 255)), "섬광 2프레임" if i == 0 else None)
    for i in range(60):
        put(particles_over(Image.new("RGB", (W, H), BLACK), i, 60, seed=3, count=30, alpha=0.18 * ease(i / 30)), "암전 2초" if i == 0 else None)
    # 632–704 E 금빛 회복 — B와 같은 구도 + 금빛 입자
    for i in range(73):
        put(particles_over(still(B, 1.0 + 0.03 * i / 72, SUN), i, 73, count=110, alpha=1.0, big=True), "E 금빛 회복 + H2 허밍" if i == 0 else None)
    # 705–734 기억 카운터 (한 번)
    for i in range(30):
        im = Image.new("RGB", (W, H), BLACK)
        d = ImageDraw.Draw(im)
        ctext(d, 760, "MEMORY", f(54, 700), GREY)
        num = "1,024" if i < 12 else "1,023"
        col = CREAM if i < 12 else RED
        ctext(d, 840, num, f(190), col)
        if i >= 12:
            ctext(d, 1080, "기억 하나를 잃었다", f(52, 700), RED)
        put(im, "MEMORY 1,024 → 1,023" if i == 0 else None)
    # 735–788 F 렌 뒷모습 + L1 자막
    for i in range(54):
        im = still(F, 1.0 + 0.04 * ease(i / 53))
        d = ImageDraw.Draw(im)
        if i >= 7:
            ctext(d, 1300, "…당신, 누구였더라?", f(64, 700), (255, 255, 255), stroke=5)
        put(im, "F 렌 뒷모습 + L1" if i == 0 else None)
    # 789–833 A 카나(미소) + 카나의 기억 — 렌 × (카나가 렌을 잊음)
    for i in range(45):
        im = still(A, 1.51, A_C)
        d = ImageDraw.Draw(im)
        if i >= 12:
            ctext(d, 1420, "카나의 기억 — 렌 ×", f(50, 700), RED, stroke=4)
        put(im, "A 카나 미소 + 카나의 기억 — 렌 ×" if i == 0 else None)
    # 834–899 타이틀
    for i in range(66):
        im = Image.new("RGB", (W, H), BLACK)
        d = ImageDraw.Draw(im)
        a = ease(i / 12)
        c = lambda col: tuple(int(BLACK[k] + (col[k] - BLACK[k]) * a) for k in range(3))
        ctext(d, 820, "ECHO CANARY", f(130), c(CREAM))
        d.rectangle([340, 990, 740, 996], fill=c(GOLD))
        ctext(d, 1030, "잔향의 카나리아", f(66, 700), c(GOLD))
        put(im, "타이틀" if i == 0 else None)
    assert n == 900, n

    # ── 오디오 ──
    with wave.open(str(guide_wav)) as w:
        guide = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).astype(np.float32) / 32768
    mono = lambda p: np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                                                  capture_output=True, check=True).stdout, np.float32)
    mix = np.zeros((900 * SR // FPS, 2), np.float32)

    def add(sig, at_s, gain=1.0):
        s = int(at_s * SR)
        if sig.ndim == 1:
            sig = np.stack([sig, sig], 1)
        e = min(len(mix), s + len(sig))
        mix[s:e] += sig[: e - s] * gain

    def g(a, b, fade=0.01):
        p = guide[int(a * SR):int(b * SR)].copy()
        k = int(fade * SR)
        p[:k] *= np.linspace(0, 1, k)[:, None]
        p[-k:] *= np.linspace(1, 0, k)[:, None]
        return p

    MUS = 0.8
    add(g(1.0, 3.5), 0.0, MUS * 0.7)                        # 테이프 히스 (허밍 밑에 깔림)
    add(mono(voice / "H1_허밍2_앞2.0초.wav"), 1.5, 1.6)     # H1
    add(g(42.2, 44.7), 5.5, MUS)                             # 무타 럼블 → 무음
    add(g(5.0, 5.6), 10.0, MUS * 1.2)                        # 글자 사라짐 = 삽입음 + 브라스
    add(g(28.2, 29.8), 10.0, MUS)                            # (구 장전음) 포스터 카나 컷 아래
    for k, a in enumerate([11.4, 15.4, 17.4, 19.4]):         # 크루
        add(g(a, a + 0.8), 336 / FPS + 0.8 * k, MUS)  # 포스터 크루 컷(REN 336프레임부터 0.8초 간격)에 맞춤
    add(g(37.4, 38.6), 14.8, MUS)                            # 렌의 눈
    add(g(51.0, 54.0), 16.0, MUS)                            # 라이벌
    add(g(46.3, 46.3 + 2 / FPS, fade=0.004), 570 / FPS, MUS)  # 충돌음: 섬광 2프레임에만, 572프레임에서 끊음
    add(mono(voice / "H2_허밍2_앞2.4초.wav"), 632 / FPS, 1.6)  # H2
    t = np.arange(int(0.03 * SR)) / SR                       # 카운터 째깍
    add(0.25 * np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 120), 705 / FPS + 0.4)
    add(mono(voice / "L1_테이크2.wav"), 735 / FPS, 1.4)      # L1
    add(g(57.6, 59.8, fade=0.05), 834 / FPS, MUS)            # 타이틀: 마지막 화음 + 허밍 선율
    mix[int(572 / FPS * SR):int(632 / FPS * SR)] = 0         # 암전 60프레임 = 정확히 2.000초 무음
    wav = work / "final_mix.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())
    meas = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(wav), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                           "-f", "null", "-"], capture_output=True, text=True).stderr
    m = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
    ln = ("loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I={input_i}:measured_TP={input_tp}:"
          "measured_LRA={input_lra}:measured_thresh={input_thresh}:offset={target_offset}").format(**m)
    mp4 = out / "pilot30_기억하나_완성초안_1080x1920.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "%04d.png"), "-i", str(wav),
                    "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow", "-r", str(FPS),
                    "-af", ln + ",alimiter=limit=0.71:level=false", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-movflags", "+faststart", "-shortest", str(mp4)], check=True)
    (out / "pilot30_완성초안_편집표.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    print(mp4, n)


if __name__ == "__main__":
    main(*[Path(a) for a in sys.argv[1:8]])
