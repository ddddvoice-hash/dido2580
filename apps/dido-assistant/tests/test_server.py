"""비서 서버를 오프라인 모드로 띄워 기능을 확인해요(인터넷·AI 연결 없이).

    python apps/dido-assistant/tests/test_server.py
"""
import base64
import json
import os
import pathlib
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
os.environ["DIDO_OFFLINE"] = "1"

FAKE_WAV = b"RIFF\x24\x00\x00\x00WAVEfmt "  # 내용은 상관없이 WAV 머리만


class FakeTTS(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        FakeTTS.seen.append((json.loads(self.rfile.read(n)), self.headers.get("Authorization")))
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(FAKE_WAV)))
        self.end_headers()
        self.wfile.write(FAKE_WAV)


def serve(handler):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def call(port, path, body=None):
    if body is None:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}") as r:
            return json.loads(r.read())
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def start_app():
    import server
    server.STATE = server.State()
    return serve(server.Handler)


class Offline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["DIDO_TTS"] = "browser"
        cls.srv = start_app()
        cls.port = cls.srv.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_status_discloses_ai(self):
        s = call(self.port, "/api/status")
        self.assertEqual(s["mode"], "offline")
        self.assertEqual(s["engine"], "browser")
        self.assertIn("AI 비서", s["greeting"])

    def test_chat_numbers(self):
        r = call(self.port, "/api/chat", {"text": "총 1,234,500원 어떻게 읽어?"})
        self.assertIn("백이십삼만 사천오백 원", r["speak"])
        self.assertNotIn("audio", r)

    def test_chat_time_speak_has_no_digits(self):
        r = call(self.port, "/api/chat", {"text": "지금 몇 시야?"})
        self.assertTrue(any(c.isdigit() for c in r["text"]))
        self.assertFalse(any(c.isdigit() for c in r["speak"]))

    def test_script(self):
        r = call(self.port, "/api/script", {"text": "안녕하세요. 예약 번호는 4719-2386이에요."})
        self.assertIn("사칠일구, 이삼팔육", r["result"])
        self.assertNotIn("안녕하세요", r["result"])

    def test_bad_body(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/chat", data=b"not json",
                                     headers={"Content-Type": "application/json"})
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req)
        self.assertEqual(cm.exception.code, 400)

    def test_source_files_not_served(self):
        for p in ("/brain.py", "/server.py", "/tts_server/server.py"):
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(f"http://127.0.0.1:{self.port}{p}")
            self.assertEqual(cm.exception.code, 404, p)

    def test_ui_served(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/") as r:
            html = r.read().decode("utf-8")
        self.assertIn("성우 김디도 AI 비서", html)
        self.assertIn("이 비서는 AI예요", html)


class HttpVoice(unittest.TestCase):
    def test_audio_from_voice_server_with_token(self):
        fake = serve(FakeTTS)
        os.environ.update(DIDO_TTS="http", DIDO_TTS_URL=f"http://127.0.0.1:{fake.server_address[1]}/tts", DIDO_TTS_TOKEN="t0k")
        try:
            app = start_app()
            r = call(app.server_address[1], "/api/chat", {"text": "체온이 38.5도예요"})
            self.assertEqual(base64.b64decode(r["audio"]), FAKE_WAV)
            sent, auth = FakeTTS.seen[-1]
            self.assertIn("삼십팔 점 오 도", sent["text"])  # 엔진에는 다듬은 글이 가요
            self.assertEqual(auth, "Bearer t0k")
            app.shutdown()
        finally:
            fake.shutdown()
            for k in ("DIDO_TTS", "DIDO_TTS_URL", "DIDO_TTS_TOKEN"):
                os.environ.pop(k, None)

    def test_voice_server_down_falls_back(self):
        os.environ.update(DIDO_TTS="http", DIDO_TTS_URL="http://127.0.0.1:9/tts")
        try:
            app = start_app()
            r = call(app.server_address[1], "/api/speak", {"text": "3시"})
            self.assertNotIn("audio", r)
            self.assertIn("기본 목소리", r["note"])
            app.shutdown()
        finally:
            os.environ.pop("DIDO_TTS", None)
            os.environ.pop("DIDO_TTS_URL", None)


class Tools(unittest.TestCase):
    def test_recordings_stay_inside_root(self):
        from brain import tool_check_recordings
        with tempfile.TemporaryDirectory() as d:
            os.environ["DIDO_RECORDINGS"] = d
            try:
                self.assertIn("밖은", tool_check_recordings({"folder": "../../etc"}))
                self.assertIn("찾지 못했어요", tool_check_recordings({"folder": "없는폴더"}))
            finally:
                os.environ.pop("DIDO_RECORDINGS")

    def test_unknown_tool(self):
        from brain import run_tool
        out, err = run_tool("rm_rf", {})
        self.assertTrue(err)


if __name__ == "__main__":
    unittest.main()
