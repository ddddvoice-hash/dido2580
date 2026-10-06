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

    def test_other_websites_blocked(self):
        """다른 웹페이지가 몰래 부르는 요청은 막아요(R28-1)."""
        def raw(headers, body=b"{}"):
            req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/reset", data=body, headers=headers)
            try:
                with urllib.request.urlopen(req) as r:
                    return r.status
            except urllib.error.HTTPError as e:
                return e.code
        self.assertEqual(raw({"Content-Type": "application/json", "Origin": "http://evil.example"}), 403)
        self.assertEqual(raw({"Content-Type": "text/plain"}, b'{"text":"x"}'), 400)
        self.assertEqual(raw({"Content-Type": "application/json", "Host": "evil.example"}), 403)
        self.assertEqual(raw({"Content-Type": "application/json", "Content-Length": "abc"}), 400)
        self.assertEqual(call(self.port, "/api/status")["service"], "seongwoo-kimdido-assistant")

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


class Redirect(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        self.send_response(302)
        self.send_header("Location", f"http://127.0.0.1:{FakeTTS_port[0]}/tts")
        self.end_headers()


FakeTTS_port = [0]


class FakeEleven(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        FakeEleven.seen.append((self.path, self.headers.get("xi-api-key"), json.loads(self.rfile.read(n))))
        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.end_headers()
        self.wfile.write(b"ID3fake")


class CloudVoice(unittest.TestCase):
    def test_cloud_voice_engine(self):
        """클라우드 맞춤 목소리(Q14 1순위): 키·목소리 ID만 있으면 자동 선택, 다듬은 글을 보내요."""
        fake = serve(FakeEleven)
        os.environ.update(ELEVENLABS_API_KEY="k", DIDO_ELEVEN_VOICE_ID="voice/1",
                          DIDO_ELEVEN_API=f"http://127.0.0.1:{fake.server_address[1]}/v1/text-to-speech/")
        try:
            app = start_app()
            r = call(app.server_address[1], "/api/speak", {"text": "오전 9시 30분"})
            self.assertEqual(base64.b64decode(r["audio"]), b"ID3fake")
            self.assertEqual(r["audio_type"], "audio/mpeg")
            path, key, body = FakeEleven.seen[-1]
            self.assertEqual((path, key), ("/v1/text-to-speech/voice%2F1", "k"))
            self.assertEqual(body["text"], "오전 아홉 시 삼십 분")
            app.shutdown()
        finally:
            fake.shutdown()
            for k in ("ELEVENLABS_API_KEY", "DIDO_ELEVEN_VOICE_ID", "DIDO_ELEVEN_API"):
                os.environ.pop(k, None)


class VoiceSecurity(unittest.TestCase):
    def test_token_not_sent_on_redirect(self):
        """목소리 서버가 다른 곳으로 보내도 토큰을 따라 보내지 않아요(R28-2)."""
        fake = serve(FakeTTS)
        FakeTTS_port[0] = fake.server_address[1]
        red = serve(Redirect)
        FakeTTS.seen.clear()
        os.environ["DIDO_TTS_TOKEN"] = "secret"
        try:
            from tts import HttpEngine, synth_or_none
            audio, warn = synth_or_none(HttpEngine(f"http://127.0.0.1:{red.server_address[1]}/tts"), "x")
            self.assertIsNone(audio)
            self.assertEqual(FakeTTS.seen, [])
            self.assertNotIn("secret", warn)
        finally:
            os.environ.pop("DIDO_TTS_TOKEN")
            fake.shutdown(); red.shutdown()

    def test_remote_http_url_refused(self):
        from tts import make_engine
        os.environ.update(DIDO_TTS="http", DIDO_TTS_URL="http://example.com/tts")
        try:
            self.assertEqual(make_engine().name, "browser")
        finally:
            os.environ.pop("DIDO_TTS"); os.environ.pop("DIDO_TTS_URL")


class Tools(unittest.TestCase):
    def test_recordings_stay_inside_root(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["DIDO_RECORDINGS"] = d
            try:
                from brain import run_tool
                out, err = run_tool("check_recordings", {"folder": "../../etc"})
                self.assertTrue(err); self.assertIn("밖은", out)
                out, err = run_tool("check_recordings", {"folder": "없는폴더"})
                self.assertTrue(err); self.assertIn("찾지 못했어요", out)  # 실패는 오류로 표시(R28-9)
                outside = tempfile.mkdtemp()
                os.symlink(outside, os.path.join(d, "link"))
                out, err = run_tool("check_recordings", {"folder": ""})
                self.assertTrue(err); self.assertIn("바로가기", out)  # R28-3
            finally:
                os.environ.pop("DIDO_RECORDINGS")

    def test_unknown_tool(self):
        from brain import run_tool
        out, err = run_tool("rm_rf", {})
        self.assertTrue(err)


if __name__ == "__main__":
    unittest.main()
