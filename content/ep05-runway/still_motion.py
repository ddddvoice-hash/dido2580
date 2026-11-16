"""포스터 잘라낸 첫 장면을 '생성 없이' 움직이는 시험 렌더 (크레딧 0, 얼굴 변형 0).

원본 픽셀은 그대로 두고 카메라(밀기·이동)·빛(눈 발광, 빛줄기)·입자만 코드로 얹는다.
    python content/ep05-runway/still_motion.py <out_dir>
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
W, H, FPS, SEC = 1080, 1920, 30, 4.0


def ease(x):
    return 0.5 - 0.5 * np.cos(np.pi * min(1, max(0, x)))


def camera(src, t, z0, z1, cx0, cy0, cx1, cy1):
    """t(0~1)에 따라 확대·중심 이동. 원본 비율 유지, 출력 1080×1920."""
    e = ease(t)
    z = z0 + (z1 - z0) * e
    cx, cy = cx0 + (cx1 - cx0) * e, cy0 + (cy1 - cy0) * e
    w, h = src.width / z, src.height / z
    x0 = min(max(cx * src.width - w / 2, 0), src.width - w)
    y0 = min(max(cy * src.height - h / 2, 0), src.height - h)
    return src.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + w, y0 + h)), (x0, y0, w, h)


def glow(img, pos, r, strength, color=(90, 170, 255)):
    layer = Image.new("RGB", img.size, (0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([pos[0] - r, pos[1] - r, pos[0] + r, pos[1] + r], fill=color)
    layer = layer.filter(ImageFilter.GaussianBlur(r * 0.6))
    a = np.asarray(img, np.float32) + np.asarray(layer, np.float32) * strength
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def sparks(img, t, seed, n=40, color=(255, 214, 120)):
    rng = np.random.default_rng(seed)
    xs, ys, sp, sz = rng.uniform(0, W, n), rng.uniform(0, H, n), rng.uniform(80, 220, n), rng.uniform(2, 5, n)
    layer = Image.new("RGB", img.size, (0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x, y, s, z in zip(xs, ys, sp, sz):
        yy = (y - s * t * SEC) % H
        xx = x + 18 * np.sin(t * 6 + x)
        d.ellipse([xx - z, yy - z, xx + z, yy + z], fill=color)
    layer = layer.filter(ImageFilter.GaussianBlur(1.5))
    a = np.asarray(img, np.float32) + np.asarray(layer, np.float32) * 0.8
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def sweep(img, t, angle_deg=-20, width=260, strength=0.18):
    """빛줄기 한 번 지나가기."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    k = np.tan(np.radians(angle_deg))
    pos = -400 + (W + 800) * t
    dist = np.abs((xx + yy * k) - pos)
    m = np.clip(1 - dist / width, 0, 1)[..., None] * strength * 255
    a = np.asarray(img, np.float32) + m * np.array([1.0, 0.9, 0.75])
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def render(name, frames, out):
    tmp = out / f"_{name}"
    tmp.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(frames):
        f.save(tmp / f"{i:04d}.png", compress_level=1)
    mp4 = out / f"{name}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(mp4)], check=True)
    return mp4


def main(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    n = int(SEC * FPS)
    s1 = Image.open(HERE / "firstframes/shot1_mecha_720x1280.jpg").convert("RGB")
    eye = (0.53, 0.105)  # 잘라낸 그림에서 로봇 눈 위치(비율)
    f1 = []
    for i in range(n):
        t = i / (n - 1)
        img, (x0, y0, w, h) = camera(s1, t, 1.0, 1.35, 0.5, 0.5, eye[0], 0.32)
        ex, ey = (eye[0] * s1.width - x0) / w * W, (eye[1] * s1.height - y0) / h * H
        pulse = 0.35 + 0.65 * ease(min(1, t * 1.6)) * (0.85 + 0.15 * np.sin(t * 20))
        img = glow(img, (ex, ey), 70, pulse)
        f1.append(sparks(img, t, 1))
    m1 = render("shot1_still_motion", f1, out)
    s3 = Image.open(HERE / "firstframes/shot3_crew_720x1280.jpg").convert("RGB")
    f3 = []
    for i in range(n):
        t = i / (n - 1)
        img, _ = camera(s3, t, 1.08, 1.22, 0.42, 0.5, 0.58, 0.42)
        f3.append(sweep(sparks(img, t, 3, n=24), t))
    m3 = render("shot3_still_motion", f3, out)
    print(m1, m3)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
