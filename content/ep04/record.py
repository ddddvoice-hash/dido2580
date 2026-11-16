"""EP.04 촬영: 따뜻함 채점기 실제 앱을 띄우고 '예시 불러오기' 전후 화면을 요소 단위로 캡처합니다.

앱 원본: 브랜치 ccr-dfaecddb-lml56o 의 apps/warmth-scorer (git archive로 꺼내 그대로 띄움, 수정 없음)
결과: <out>/shots/*.png, <out>/shots/capture.json (화면에서 읽은 실제 합계 문자열 포함)

    python content/ep04/record.py <work_dir>
"""
import json
import subprocess
import sys
import tarfile
import io
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
SRC_REF = "origin/ccr-dfaecddb-lml56o"
PORT = 8743


def main(work: Path):
    app = work / "app"
    shots = work / "shots"
    shots.mkdir(parents=True, exist_ok=True)
    if not (app / "apps/warmth-scorer/index.html").exists():
        tar = subprocess.run(["git", "-C", str(REPO), "archive", SRC_REF, "apps/warmth-scorer"], capture_output=True, check=True).stdout
        tarfile.open(fileobj=io.BytesIO(tar)).extractall(app, filter="data")
    commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", SRC_REF], capture_output=True, text=True).stdout.strip()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1", "-d", str(app / "apps/warmth-scorer")],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/index.html", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
            pg = b.new_page(viewport={"width": 900, "height": 1600}, device_scale_factor=2)
            pg.goto(f"http://127.0.0.1:{PORT}/index.html")
            pg.wait_for_function("document.getElementById('rubric-status').textContent.includes('불러왔')")
            sec = pg.locator("#register-section")
            pg.locator("#load-example").evaluate("e => e.style.boxShadow = '0 0 0 6px #ffb703'")
            sec.screenshot(path=str(shots / "before.png"))
            pg.locator("#load-example").evaluate("e => e.style.boxShadow = ''")
            pg.click("#load-example")
            pg.wait_for_function("document.getElementById('answer-totals').textContent.includes('C:')")
            totals = pg.inner_text("#answer-totals")
            sec.screenshot(path=str(shots / "after.png"))
            pg.locator("#situation").screenshot(path=str(shots / "situation.png"))
            areas = pg.locator("#answers-list textarea")
            texts = []
            for i in range(areas.count()):
                areas.nth(i).screenshot(path=str(shots / f"answer_{'ABC'[i]}.png"))
                texts.append(areas.nth(i).input_value())
            pg.locator("#answer-totals").screenshot(path=str(shots / "totals.png"))
            b.close()
    finally:
        srv.terminate()
    cap = {"app_ref": SRC_REF, "app_commit": commit, "totals_text": totals, "answers": texts}
    (shots / "capture.json").write_text(json.dumps(cap, ensure_ascii=False, indent=1))
    print(totals)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
