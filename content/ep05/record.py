"""EP.05 촬영: 「잔향의 카나리아」 OP 애니마틱을 프레임 단위로 뽑고, 합성 재즈 가이드 트랙을 오프라인으로 렌더합니다.

원본: 브랜치 ccr-2099f74b-5weu5o 의 anime/echo-canary/op-animatic.html
촬영용 사본에서만 두 가지를 바꿉니다(원본 파일은 그대로).
  1) 구글 폰트 링크 → 미리 받은 같은 폰트 파일(로컬)
  2) 맨 앞에 <meta charset="utf-8"> (원본에 없어서 로컬 서버로 열면 한글이 깨짐)
  3) 스크립트 끝에 `window.__ec` 연결 코드: 기존 render(t)·schedule()를 그대로 부르기만 함
     (오디오는 OfflineAudioContext에 같은 schedule(0, 60)을 걸어 렌더)

    python content/ep05/record.py <work_dir> <seg_json>
seg_json: [[시작초, 끝초], ...] 뽑을 구간
"""
import base64
import os
import json
import re
import subprocess
import sys
import time
import urllib.request
import wave
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
SRC_REF = "origin/ccr-2099f74b-5weu5o"
SRC_PATH = "anime/echo-canary/op-animatic.html"
PORT = 8745
FPS, SR = 30, 48000
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

HOOK = r"""
window.__ec = {
  DUR, SIL_A, SIL_B, scenes: SCENES.map(s => ({a: s.a, b: s.b, name: s.name})),
  frame(t) { render(t); return document.getElementById('stage').toDataURL('image/jpeg', 0.93); },
  async audio(sr) {
    const oc = new OfflineAudioContext(2, Math.ceil(sr * (DUR + 1)), sr);
    actx = oc;
    noiseBuf = oc.createBuffer(1, sr * 2, sr);
    const nd = noiseBuf.getChannelData(0); for (let i = 0; i < nd.length; i++) nd[i] = Math.random() * 2 - 1;
    bus = oc.createGain(); bus.gain.value = 0.5; bus.connect(oc.destination);
    anchor = 0; schedule(0, DUR + 0.5);
    const buf = await oc.startRendering();
    const L = buf.getChannelData(0), R = buf.getChannelData(1), out = new Int16Array(L.length * 2);
    for (let i = 0; i < L.length; i++) { out[2*i] = Math.max(-1, Math.min(1, L[i])) * 32767; out[2*i+1] = Math.max(-1, Math.min(1, R[i])) * 32767; }
    let s = ''; const u8 = new Uint8Array(out.buffer);
    for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000));
    return btoa(s);
  }
};
"""


def local_fonts(html: str, app: Path) -> str:
    m = re.search(r'<link rel="stylesheet" href="(https://fonts\.googleapis\.com/[^"]+)">', html)
    req = urllib.request.Request(m.group(1).replace("&amp;", "&"), headers={"User-Agent": UA})
    css = urllib.request.urlopen(req, timeout=30).read().decode()
    (app / "fonts").mkdir(exist_ok=True)
    for k, url in enumerate(sorted(set(re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", css)))):
        name = f"f{k:03d}.woff2"
        (app / "fonts" / name).write_bytes(urllib.request.urlopen(url, timeout=30).read())
        css = css.replace(url, f"fonts/{name}")
    (app / "fonts.css").write_text(css, encoding="utf-8")
    html = html.replace(m.group(0), '<link rel="stylesheet" href="fonts.css">')
    return re.sub(r'<link rel="preconnect"[^>]*>\n?', "", html)


def main(work: Path, segs):
    app = work / "app"
    app.mkdir(parents=True, exist_ok=True)
    if os.environ.get("ECHO_SRC_FILE"):  # 로컬 수정본(예: 테이프 라벨 날짜 변경본)으로 촬영
        html = Path(os.environ["ECHO_SRC_FILE"]).read_text(encoding="utf-8")
    else:
        html = subprocess.run(["git", "-C", str(REPO), "show", f"{SRC_REF}:{SRC_PATH}"], capture_output=True, text=True, encoding="utf-8", check=True).stdout
    commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", SRC_REF], capture_output=True, text=True).stdout.strip()
    sc = int(os.environ.get("ECHO_SCALE", "1"))  # 고해상도 렌더(그림은 같은 벡터 코드, 캔버스만 sc배)
    if sc > 1:
        html = html.replace('width="1280" height="720"', f'width="{1280*sc}" height="{720*sc}"')
        html = html.replace("ctx.setTransform(1, 0, 0, 1, 0, 0);", f"ctx.setTransform({sc}, 0, 0, {sc}, 0, 0);")
    if "charset" not in html[:500].lower():  # 원본에 인코딩 선언이 없어 로컬 서버에서 한글이 깨짐
        html = '<meta charset="utf-8">\n' + html
    end = html.rindex("})();")
    html = html[:end] + HOOK + html[end:]
    (app / "op.html").write_text(local_fonts(html, app), encoding="utf-8")
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1", "-d", str(app)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    frames = work / "src_frames"
    frames.mkdir(exist_ok=True)
    try:
        time.sleep(0.8)
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", args=["--autoplay-policy=no-user-gesture-required"])
            pg = b.new_page(viewport={"width": 1400, "height": 1000})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(f"http://127.0.0.1:{PORT}/op.html")
            pg.wait_for_function("window.__ec !== undefined")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(500)
            info = pg.evaluate("({DUR: __ec.DUR, SIL_A: __ec.SIL_A, SIL_B: __ec.SIL_B, scenes: __ec.scenes, fonts: [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family)})")
            for si, (a, bb) in enumerate(segs):
                n = int(round((bb - a) * FPS))
                for k in range(n):
                    data = pg.evaluate("t => __ec.frame(t)", a + k / FPS)
                    (frames / f"s{si}_{k:04d}.jpg").write_bytes(base64.b64decode(data.split(",", 1)[1]))
            pcm = base64.b64decode(pg.evaluate("sr => __ec.audio(sr)", SR))
            b.close()
    finally:
        srv.terminate()
    with wave.open(str(work / "guide.wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm)
    info.update({"src_ref": SRC_REF, "src_commit": commit, "segments": segs, "page_errors": errs})
    (work / "capture.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(info, ensure_ascii=False))


if __name__ == "__main__":
    main(Path(sys.argv[1]), json.loads(sys.argv[2]))
