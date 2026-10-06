"""성우 김디도 목소리 AI 비서 서버.

    python apps/dido-assistant/server.py            # http://127.0.0.1:8770
    python apps/dido-assistant/server.py --port 9000

이 컴퓨터 안(127.0.0.1)에서만 열려요. 화면은 index.html, 기능은 /api/... 로 받아요.
"""
from __future__ import annotations

import argparse
import base64
import json
import pathlib
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from brain import GREETING, Brain, tool_check_script  # noqa: E402
from korean_numbers import normalize  # noqa: E402
from tts import make_engine, synth_or_none  # noqa: E402

MAX_BODY = 200_000  # 대본도 받을 수 있게 200KB까지


class State:
    def __init__(self):
        self.brain = Brain()
        self.engine = make_engine()
        self.lock = threading.Lock()


STATE: State | None = None


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(HERE), **kw)

    def log_message(self, fmt, *args):  # 조용히
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, code: int, obj: dict):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict | None:
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX_BODY:
            return None
        try:
            obj = json.loads(self.rfile.read(n).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return obj if isinstance(obj, dict) else None

    def do_GET(self):
        if self.path == "/api/status":
            s = STATE
            return self._json(200, {"mode": s.brain.mode, "engine": s.engine.name,
                                    "engine_label": s.engine.label, "greeting": GREETING})
        if self.path in ("/", ""):
            self.path = "/index.html"
        if not self.path.split("?")[0].endswith((".html", ".js", ".css", ".svg", ".ico", ".png")):
            return self._json(404, {"error": "없는 주소예요"})
        return super().do_GET()

    def do_POST(self):
        body = self._body()
        if body is None:
            return self._json(400, {"error": "보낸 내용을 읽지 못했어요"})
        text = str(body.get("text", "")).strip()
        s = STATE
        if self.path == "/api/normalize":
            return self._json(200, {"speak": normalize(text)})
        if self.path == "/api/script":
            return self._json(200, {"result": tool_check_script({"script": text})})
        if self.path == "/api/reset":
            with s.lock:
                s.brain.reset()
            return self._json(200, {"ok": True})
        if self.path == "/api/chat":
            if not text:
                return self._json(400, {"error": "말이 비어 있어요"})
            with s.lock:
                out = s.brain.reply(text)
            audio, warn = synth_or_none(s.engine, out["speak"])
            if audio:
                out["audio"] = base64.b64encode(audio).decode("ascii")
            if warn:
                out["note"] = warn
            out["engine"] = s.engine.name
            return self._json(200, out)
        if self.path == "/api/speak":
            audio, warn = synth_or_none(s.engine, normalize(text))
            out = {"speak": normalize(text), "engine": s.engine.name}
            if audio:
                out["audio"] = base64.b64encode(audio).decode("ascii")
            if warn:
                out["note"] = warn
            return self._json(200, out)
        return self._json(404, {"error": "없는 주소예요"})


def main(argv=None):
    global STATE
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8770)
    args = ap.parse_args(argv)
    STATE = State()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"성우 김디도 AI 비서: http://127.0.0.1:{args.port}  (생각: {STATE.brain.mode}, 목소리: {STATE.engine.label})")
    print("이 창을 닫으면 비서도 꺼져요.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
