"""비서 서버를 오프라인 모드로 띄워 기능을 확인해요(인터넷·AI 연결 없이).

    python apps/dido-assistant/tests/test_server.py
"""
import base64
import http.client
import importlib.util
import json
import os
import pathlib
import socket
import subprocess
import sys
import time
import types
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


def raw(port, method, path, body=b"", headers=None, host=None):
    """http.client로 머리말을 마음대로 정해 보내요. (상태 코드, 본문 글)"""
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        c.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
        c.putheader("Host", host or f"127.0.0.1:{port}")
        for k, v in (headers or {}).items():
            c.putheader(k, v)
        c.endheaders(body)
        r = c.getresponse()
        return r.status, r.read().decode("utf-8", "replace")
    finally:
        c.close()


JSON = {"Content-Type": "application/json"}


class Guard(unittest.TestCase):
    """R28-1 요청 출처·Host 검사, R28-4 본문 크기, R28-5 숫자 예외로 연결이 끊기지 않기."""

    @classmethod
    def setUpClass(cls):
        os.environ["DIDO_TTS"] = "browser"
        cls.srv = start_app()
        cls.port = cls.srv.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def post(self, path="/api/reset", body=b"{}", headers=None, host=None):
        return raw(self.port, "POST", path, body, {"Content-Length": str(len(body)), **(headers or JSON)}, host)

    def test_foreign_origin_rejected(self):  # R28-1 재현: 외부 Origin·Host + text/plain
        code, _ = self.post(headers={"Content-Type": "text/plain", "Origin": "http://evil.example"}, host="evil.example")
        self.assertEqual(code, 403)
        code, _ = self.post(headers={**JSON, "Origin": "http://evil.example"})
        self.assertEqual(code, 403)
        code, _ = self.post(headers={**JSON, "Origin": "null"})
        self.assertEqual(code, 403)
        code, _ = self.post(headers={**JSON, "Origin": f"http://127.0.0.1:{self.port + 1}"})  # 다른 포트도 다른 출처
        self.assertEqual(code, 403)

    def test_foreign_host_rejected_even_get(self):  # DNS 되돌림 공격 막기
        for host in ("evil.example", f"evil.example:{self.port}", "127.0.0.1", f"localhost.evil.example:{self.port}"):
            code, _ = raw(self.port, "GET", "/api/status", host=host)
            self.assertEqual(code, 403, host)
            code, _ = raw(self.port, "GET", "/", host=host)
            self.assertEqual(code, 403, host)

    def test_own_origin_and_localhost_ok(self):
        for origin in (f"http://127.0.0.1:{self.port}", f"http://localhost:{self.port}"):
            code, _ = self.post(headers={**JSON, "Origin": origin})
            self.assertEqual(code, 200, origin)
        code, _ = raw(self.port, "GET", "/api/status", host=f"localhost:{self.port}")
        self.assertEqual(code, 200)

    def test_json_content_type_required(self):
        code, _ = self.post(headers={"Content-Type": "text/plain"})
        self.assertEqual(code, 415)
        code, _ = self.post(headers={"Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(code, 415)

    def test_content_length_limits(self):  # R28-4: 음수·과대·숫자 아님은 읽기 전에 거절
        t0 = time.time()
        for cl, want in (("-1", 400), ("abc", 400), ("0", 400), ("", 400), ("999999999", 413), ("200001", 413)):
            code, _ = raw(self.port, "POST", "/api/chat", b"", {**JSON, "Content-Length": cl})
            self.assertEqual(code, want, repr(cl))
        self.assertLess(time.time() - t0, 5)  # 본문을 기다리며 멈추지 않아요

    def test_status_names_the_service(self):  # R28-13: 시작 파일이 우리 비서인지 알아봐요
        self.assertEqual(call(self.port, "/api/status")["service"], "dido-assistant")

    def test_numbers_that_used_to_crash(self):  # R28-5: 연결이 끊기지 않고 JSON으로
        for text in ("시험 번호는 12-12예요.", "날짜는 2026-10-06이에요.", "10000000000000000원이에요."):
            self.assertIn("speak", call(self.port, "/api/normalize", {"text": text}))
            self.assertIn("speak", call(self.port, "/api/speak", {"text": text}))
            self.assertIn("text", call(self.port, "/api/chat", {"text": text}))
            self.assertIn("result", call(self.port, "/api/script", {"text": text}))

    def test_internal_error_is_json_500(self):
        import server
        orig = server.normalize
        server.normalize = lambda t: 1 / 0
        try:
            code, body = self.post("/api/normalize", b'{"text":"3"}')
        finally:
            server.normalize = orig
        self.assertEqual(code, 500)
        self.assertNotIn("division", body)  # 예외 글을 그대로 내보내지 않아요

    def test_port_in_use_is_explained(self):  # R28-13
        import server
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        try:
            self.assertEqual(server.main(["--port", str(s.getsockname()[1])]), 2)
        finally:
            s.close()


class VoiceSafety(unittest.TestCase):
    """R28-2 목소리 토큰은 리디렉션·평문 외부 주소로 새지 않아요, R28-4 목소리 서버 본문 크기."""

    def test_redirect_not_followed_token_not_forwarded(self):
        class Target(BaseHTTPRequestHandler):
            seen = []

            def log_message(self, *a):
                pass

            def do_POST(self):
                Target.seen.append(self.headers.get("Authorization"))
                self.send_response(200)
                self.send_header("Content-Type", "audio/wav")
                self.send_header("Content-Length", "4")
                self.end_headers()
                self.wfile.write(b"RIFF")

        target = serve(Target)

        class Redirector(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{target.server_address[1]}/tts")
                self.send_header("Content-Length", "0")
                self.end_headers()

        redir = serve(Redirector)
        os.environ.update(DIDO_TTS="http", DIDO_TTS_URL=f"http://127.0.0.1:{redir.server_address[1]}/tts",
                          DIDO_TTS_TOKEN="test-token-not-real")
        try:
            app = start_app()
            r = call(app.server_address[1], "/api/speak", {"text": "3시"})
            self.assertNotIn("audio", r)
            self.assertIn("기본 목소리", r["note"])
            self.assertNotIn("test-token-not-real", json.dumps(r))
            self.assertEqual(Target.seen, [])  # 도착지에는 아무것도 가지 않았어요
            app.shutdown()
            app.server_close()
        finally:
            redir.shutdown()
            target.shutdown()
            for k in ("DIDO_TTS", "DIDO_TTS_URL", "DIDO_TTS_TOKEN"):
                os.environ.pop(k, None)

    def test_plain_http_to_outside_refused(self):
        from tts import HttpEngine, make_engine
        with self.assertRaises(ValueError):
            HttpEngine("http://voice.example.com/tts")
        with self.assertRaises(ValueError):
            HttpEngine("https://user:pw@voice.example.com/tts")
        HttpEngine("https://voice.example.com/tts")  # https는 돼요
        HttpEngine("http://127.0.0.1:8771/tts")  # 이 컴퓨터는 http도 돼요
        os.environ.update(DIDO_TTS="http", DIDO_TTS_URL="http://voice.example.com/tts")
        try:
            e = make_engine()
            self.assertEqual(e.name, "browser")
            self.assertIn("안전하지 않아", e.label)
        finally:
            os.environ.pop("DIDO_TTS", None)
            os.environ.pop("DIDO_TTS_URL", None)

    def test_voice_server_body_limits(self):
        spec = importlib.util.spec_from_file_location("tts_server_main", HERE / "tts_server" / "server.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        calls = []
        mod.synth = lambda text: calls.append(text) or FAKE_WAV
        os.environ.pop("DIDO_TTS_TOKEN", None)
        srv = serve(mod.Handler)
        port = srv.server_address[1]
        try:
            for cl, want in (("-1", 400), ("abc", 400), ("0", 400), ("999999999", 413)):
                code, _ = raw(port, "POST", "/tts", b"", {**JSON, "Content-Length": cl})
                self.assertEqual(code, want, repr(cl))
            body = json.dumps({"text": "안녕하세요"}).encode()
            code, _ = raw(port, "POST", "/tts", body, {**JSON, "Content-Length": str(len(body))})
            self.assertEqual(code, 200)
            self.assertEqual(calls, ["안녕하세요"])
        finally:
            srv.shutdown()
            srv.server_close()


def fake_anthropic(create):
    """anthropic 패키지 없이 Claude 경로를 시험하는 가짜. create(**kw)가 응답을 만들어요."""
    m = types.ModuleType("anthropic")

    class Err(Exception):
        pass

    for n in ("AuthenticationError", "RateLimitError", "APIConnectionError"):
        setattr(m, n, type(n, (Err,), {}))
    m.APIStatusError = type("APIStatusError", (Err,), {"status_code": 500})
    m.Anthropic = lambda: types.SimpleNamespace(beta=types.SimpleNamespace(messages=types.SimpleNamespace(create=create)))
    return m


def tool_use(input_, name="read_numbers"):
    return types.SimpleNamespace(
        stop_reason="tool_use",
        content=[types.SimpleNamespace(type="tool_use", id="tu_1", name=name, input=input_)])


def text_resp(t="네, 알겠어요."):
    return types.SimpleNamespace(stop_reason="end_turn", content=[types.SimpleNamespace(type="text", text=t)])


class ClaudePath(unittest.TestCase):
    """R28-8·9: 도구 실패·예외가 대화 기록을 깨뜨리지 않고, 실패는 실패로 알려요."""

    def setUp(self):
        self._saved = sys.modules.get("anthropic")
        os.environ.pop("DIDO_OFFLINE", None)
        os.environ["ANTHROPIC_API_KEY"] = "test-placeholder-not-a-key"

    def tearDown(self):
        os.environ["DIDO_OFFLINE"] = "1"
        os.environ.pop("ANTHROPIC_API_KEY", None)
        if self._saved is None:
            sys.modules.pop("anthropic", None)
        else:
            sys.modules["anthropic"] = self._saved

    def brain(self, create):
        sys.modules["anthropic"] = fake_anthropic(create)
        import brain
        b = brain.Brain()
        self.assertEqual(b.mode, "claude")
        return b

    def test_bad_tool_json_becomes_error_result(self):  # R28-8
        sent = []
        queue = [tool_use("{깨진 JSON"), text_resp()]

        def create(**kw):
            sent.append(json.dumps([m for m in kw["messages"] if m["role"] == "user" and isinstance(m["content"], list)],
                                   default=str))
            return queue.pop(0)

        b = self.brain(create)
        out = b.reply("3시 읽어 줘")
        self.assertEqual(out["text"], "네, 알겠어요.")
        self.assertIn('"is_error": true', sent[-1])
        self.assertEqual(len(b.history), 4)  # 질문·도구 호출·도구 결과·대답이 짝이 맞아요

    def test_unexpected_exception_cleans_history(self):  # R28-8
        def create(**kw):
            raise ValueError("secret-looking-text")

        b = self.brain(create)
        out = b.reply("안녕")
        self.assertEqual(b.history, [])
        self.assertNotIn("secret-looking-text", json.dumps(out, ensure_ascii=False))
        self.assertIn("문제가 생겼어요", out["text"])

    def test_client_creation_failure_goes_offline(self):  # R28-8
        mod = fake_anthropic(lambda **kw: None)

        def boom():
            raise RuntimeError("auth setup failed")

        mod.Anthropic = boom
        sys.modules["anthropic"] = mod
        import brain
        b = brain.Brain()
        self.assertEqual(b.mode, "offline")
        self.assertIn("text", b.reply("지금 몇 시야?"))

    def test_tool_failure_reported_as_error(self):  # R28-9
        from brain import run_tool
        with tempfile.TemporaryDirectory() as d:
            os.environ["DIDO_RECORDINGS"] = d
            try:
                for folder in ("없는폴더", "../../etc"):
                    out, err = run_tool("check_recordings", {"folder": folder})
                    self.assertTrue(err, folder)
            finally:
                os.environ.pop("DIDO_RECORDINGS")
        out, err = run_tool("read_numbers", "{깨진")
        self.assertTrue(err)
        out, err = run_tool("read_numbers", '{"text": "3시"}')
        self.assertEqual((out, err), ("세 시", False))

    def test_tool_exception_text_not_leaked(self):  # R28 '비밀값 제거'
        import brain
        brain.HANDLERS["boom"] = lambda a: 1 / 0
        try:
            out, err = brain.run_tool("boom", {})
        finally:
            brain.HANDLERS.pop("boom")
        self.assertTrue(err)
        self.assertNotIn("division", out)

    def _run_recordings_with(self, runner):
        import brain
        orig = brain.subprocess.run
        brain.subprocess.run = runner
        try:
            with tempfile.TemporaryDirectory() as d:
                os.environ["DIDO_RECORDINGS"] = d
                return brain.run_tool("check_recordings", {"folder": ""})
        finally:
            brain.subprocess.run = orig
            os.environ.pop("DIDO_RECORDINGS", None)

    def test_missing_node_reported_as_error(self):  # R28-9
        def gone(*a, **k):
            raise FileNotFoundError()

        out, err = self._run_recordings_with(gone)
        self.assertTrue(err)
        self.assertIn("Node.js", out)

    def test_timeout_reported_as_error(self):  # R28-9
        def slow(*a, **k):
            raise subprocess.TimeoutExpired("node", 300)

        out, err = self._run_recordings_with(slow)
        self.assertTrue(err)

    def test_checker_exit_codes(self):  # 반려 파일이 있어도(1) 검사는 성공, 실행 오류(2)는 실패
        def result(code):
            return lambda *a, **k: types.SimpleNamespace(returncode=code, stdout="x: 반려 V02", stderr="")

        self.assertFalse(self._run_recordings_with(result(0))[1])
        self.assertFalse(self._run_recordings_with(result(1))[1])
        self.assertTrue(self._run_recordings_with(result(2))[1])


class RecordingLinks(unittest.TestCase):
    """R28-3: 녹음 폴더 안의 링크가 밖을 가리키면 검사하지 않아요."""

    def test_link_inside_root_to_outside_refused(self):
        import brain
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as outside:
            link = pathlib.Path(d) / "link"
            made = "symlink"
            try:
                os.symlink(outside, link, target_is_directory=True)
            except (OSError, NotImplementedError):
                made = None
                if os.name == "nt":  # 관리자 권한이 없어도 되는 정션
                    r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), outside], capture_output=True)
                    made = "junction" if r.returncode == 0 else None
            if made is None:
                self.skipTest("링크를 만들 수 없는 환경")
            os.environ["DIDO_RECORDINGS"] = d
            try:
                out, err = brain.run_tool("check_recordings", {"folder": ""})
            finally:
                os.environ.pop("DIDO_RECORDINGS")
                if made == "symlink":
                    link.unlink()
                else:
                    os.rmdir(link)  # 정션은 안의 것을 지우지 않고 링크만 지워요
            self.assertTrue(err)
            self.assertIn("링크", out)


if __name__ == "__main__":
    unittest.main()
