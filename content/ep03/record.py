"""EP.03 앱 화면 캡처: 실제 변환기 서버를 띄우고, 입력 과정을 한 단계씩 스크린샷으로 남깁니다.

결과: <out>/app/*.png 와 <out>/app/manifest.json (장면별 [파일, 몇 프레임 유지])
    python content/ep03/record.py <out_dir>
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
PORT = 8731
VIEW = {"width": 900, "height": 1000}

# 장면: 입력할 문장들, 장면 길이(프레임, 30fps), 강조할 결과 수
SCENES = [
    {"name": "answer", "inputs": ["500,000,000,000원"], "frames": 90},
    {"name": "made", "inputs": ["1억 2500만 원"], "frames": 120},
    {"name": "twist", "inputs": ["10000원", "1만 원"], "frames": 120, "highlight": True},
]
TYPE_HOLD = 2   # 글자 하나 칠 때마다 유지 프레임
PRESS_HOLD = 4  # 버튼 눌림 유지 프레임


def wait_server():
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/normalize?text=1", timeout=1)
            return
        except OSError:
            time.sleep(0.1)
    raise SystemExit("서버가 뜨지 않았어요")


def main(out: Path):
    shots = out / "app"
    shots.mkdir(parents=True, exist_ok=True)
    server = subprocess.Popen([sys.executable, "-I", str(HERE / "app" / "server.py"), str(PORT)])
    manifest, results = {}, []
    try:
        wait_server()
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
            page = browser.new_page(viewport=VIEW, device_scale_factor=1)
            page.goto(f"http://127.0.0.1:{PORT}/index.html")
            page.evaluate("document.fonts.ready")
            n = 0

            def snap(hold):
                nonlocal n
                path = shots / f"{n:04d}.png"
                page.screenshot(path=str(path))
                n += 1
                seq.append([path.name, hold])

            for sc in SCENES:
                seq = []
                page.evaluate("clearList()")
                snap(6)
                for text in sc["inputs"]:
                    for i in range(1, len(text) + 1):
                        page.fill("#q", text[:i])
                        snap(TYPE_HOLD)
                    page.evaluate("document.getElementById('go').classList.add('press')")
                    snap(PRESS_HOLD)
                    page.evaluate("document.getElementById('go').classList.remove('press')")
                    page.click("#go")
                    page.wait_for_function("window.lastResult && window.lastResult.input === %s" % json.dumps(text))
                    results.append(page.evaluate("window.lastResult"))
                    snap(10)
                if sc.get("highlight"):
                    page.evaluate("document.querySelectorAll('#list li').forEach(li => li.classList.add('hi'))")
                used = sum(h for _, h in seq)
                if used > sc["frames"]:
                    raise SystemExit(f"{sc['name']} 장면이 {used}프레임으로 너무 길어요")
                snap(sc["frames"] - used)
                manifest[sc["name"]] = seq
            browser.close()
    finally:
        server.terminate()
    (shots / "manifest.json").write_text(json.dumps({"scenes": manifest, "results": results}, ensure_ascii=False, indent=1))
    for r in results:
        print(f"{r['input']} → {r['output']}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
