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
MAX_SPEAK_CHARS = 800  # 목소리로 만드는 글은 이만큼까지(다듬은 뒤 기준). 더 길면 화면이 기본 목소리로 읽어요
SERVICE = "seongwoo-kimdido-assistant"  # /api/status에 넣어 시작 파일이 우리 비서인지 알아봐요
LOCAL_NAMES = ("127.0.0.1", "localhost")


class State:
    def __init__(self):
        self.brain = Brain()
        self.engine = make_engine()
        self.lock = threading.Lock()


STATE: State | None = None


class Server(ThreadingHTTPServer):
    allow_reuse_address = False  # 윈도우에서는 켜 두면 이미 쓰는 포트에도 겹쳐 열려요


def synth_limited(engine, speak: str):
    """글이 너무 길면 목소리 엔진(클라우드 비용·서버 부담)을 부르지 않고 안내만 돌려줘요."""
    if len(speak) > MAX_SPEAK_CHARS:
        return None, f"글이 {MAX_SPEAK_CHARS}자보다 길어 기본 목소리로 읽어요"
    return synth_or_none(engine, speak)


class Handler(SimpleHTTPRequestHandler):
    timeout = 30  # 본문을 늦게 보내며 붙잡아 두는 연결을 끊어요

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

    def _port(self) -> int:
        return self.server.server_address[1]

    def _allowed_origin(self, value: str) -> bool:
        return value in {f"http://{h}:{self._port()}" for h in LOCAL_NAMES}

    def _guard(self) -> bool:
        """Host·Origin이 이 컴퓨터의 비서 주소일 때만 통과. 아니면 거절 응답을 보내고 False."""
        host = (self.headers.get("Host") or "").strip().lower()
        if host not in {f"{h}:{self._port()}" for h in LOCAL_NAMES}:
            self._json(403, {"error": "허용되지 않은 주소예요"})
            return False
        origin = self.headers.get("Origin")
        if origin is not None and not self._allowed_origin(origin.strip().lower()):
            self._json(403, {"error": "허용되지 않은 출처예요"})
            return False
        return True

    def _body(self):
        """(본문 dict, None) 또는 (None, (코드, 안내)). 읽기 전에 길이부터 확인해요."""
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            return None, (415, "JSON으로 보내 주세요")
        raw = (self.headers.get("Content-Length") or "").strip()
        if not raw.isascii() or not raw.isdigit():
            return None, (400, "보낸 내용의 길이가 올바르지 않아요")
        if len(raw.lstrip("0")) > 9:  # 수천 자리 숫자를 정수로 바꾸다 터지지 않게 바꾸기 전에 걸러요
            self.close_connection = True
            return None, (413, "보낸 내용이 너무 커요")
        n = int(raw)
        if n == 0:
            return None, (400, "보낸 내용의 길이가 올바르지 않아요")
        if n > MAX_BODY:
            self.close_connection = True  # 읽지 않은 본문이 남으니 연결을 닫아요
            return None, (413, "보낸 내용이 너무 커요")
        try:
            obj = json.loads(self.rfile.read(n).decode("utf-8"))
        except (UnicodeDecodeError, ValueError, OSError):
            return None, (400, "보낸 내용을 읽지 못했어요")
        if not isinstance(obj, dict):
            return None, (400, "보낸 내용을 읽지 못했어요")
        return obj, None

    def do_GET(self):
        if not self._guard():
            return
        if self.path == "/api/status":
            s = STATE
            return self._json(200, {"service": SERVICE, "mode": s.brain.mode, "engine": s.engine.name,
                                    "engine_label": s.engine.label, "greeting": GREETING})
        if self.path in ("/", ""):
            self.path = "/index.html"
        if not self.path.split("?")[0].endswith((".html", ".js", ".css", ".svg", ".ico", ".png")):
            return self._json(404, {"error": "없는 주소예요"})
        return super().do_GET()

    def do_HEAD(self):
        if self._guard():
            super().do_HEAD()

    def do_POST(self):
        if not self._guard():
            return
        try:
            self._post()
        except Exception:  # 연결이 끊기지 않게, 비밀이 샐 수 있는 예외 글은 내보내지 않아요
            self._json(500, {"error": "비서 안에서 문제가 생겼어요. 다시 해 주세요."})

    def _post(self):
        body, err = self._body()
        if err:
            return self._json(err[0], {"error": err[1]})
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
            audio, warn = synth_limited(s.engine, out["speak"])
            if audio:
                out["audio"] = base64.b64encode(audio).decode("ascii")
                out["audio_type"] = s.engine.mime
            if warn:
                out["note"] = warn
            out["engine"] = s.engine.name
            return self._json(200, out)
        if self.path == "/api/speak":
            speak = normalize(text)
            audio, warn = synth_limited(s.engine, speak)
            out = {"speak": speak, "engine": s.engine.name}
            if audio:
                out["audio"] = base64.b64encode(audio).decode("ascii")
                out["audio_type"] = s.engine.mime
            if warn:
                out["note"] = warn
            return self._json(200, out)
        return self._json(404, {"error": "없는 주소예요"})


def main(argv=None):
    global STATE
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8770)
    args = ap.parse_args(argv)
    try:
        srv = Server(("127.0.0.1", args.port), Handler)
    except OSError:
        print(f"[포트 사용 중] {args.port}번 자리를 다른 프로그램이 쓰고 있어요. 이미 켜진 비서가 있으면 그 창을 닫거나, "
              f"--port 뒤에 다른 번호를 붙여 다시 켜 주세요.", file=sys.stderr)
        return 2
    STATE = State()
    print(f"성우 김디도 AI 비서: http://127.0.0.1:{args.port}  (생각: {STATE.brain.mode}, 목소리: {STATE.engine.label})")
    print("이 창을 닫으면 비서도 꺼져요.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
