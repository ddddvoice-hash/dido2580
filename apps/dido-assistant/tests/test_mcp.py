"""MCP 서버를 실제 stdio로 띄워 Claude·GPT·Gemini 앱이 부르는 것과 같은 방식으로 확인해요.
가짜 목소리 모델(tests/fakes)로 '음성 폴더만 있으면 바로 구동' 경로도 끝까지 확인해요.

    pip install mcp
    python apps/dido-assistant/tests/test_mcp.py
"""
import json
import os
import pathlib
import sys
import tempfile
import time
import types
import unittest

HERE = pathlib.Path(__file__).resolve().parents[1]
FAKES = HERE / "tests" / "fakes"
sys.path.insert(0, str(HERE))

try:
    import anyio
    from mcp import StdioServerParameters
    HAVE_MCP = True
except ImportError:
    HAVE_MCP = False
if HAVE_MCP:
    try:  # mcp 2.x
        from mcp.client import Client
    except ImportError:  # mcp 1.x
        Client = None
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client


def run_session(env, steps):
    async def go():
        params = StdioServerParameters(command=sys.executable, args=[str(HERE / "mcp_server.py")], env=env)
        if Client is not None:
            async with Client(params) as c:
                return await steps(c)
        async with stdio_client(params) as (r, w), ClientSession(r, w) as c:
            await c.initialize()
            return await steps(c)
    return anyio.run(go)


def text_of(result):
    return "".join(getattr(b, "text", "") for b in result.content)


@unittest.skipUnless(HAVE_MCP, "mcp가 설치돼 있지 않아요")
class Mcp(unittest.TestCase):
    def env(self, voice_dir, extra=None):
        e = dict(os.environ)
        e.update({"DIDO_VOICE_DIR": str(voice_dir), "DIDO_OFFLINE": "1"})
        e.pop("DIDO_TTS_URL", None)
        e.pop("DIDO_TTS", None)
        if extra:
            e.update(extra)
        return e

    def test_tools_listed_and_numbers(self):
        with tempfile.TemporaryDirectory() as d:
            async def steps(c):
                names = sorted(t.name for t in (await c.list_tools()).tools)
                r = await c.call_tool("read_numbers_like_dido", {"text": "예약 번호는 4719-2386이에요."})
                s = await c.call_tool("check_script_numbers", {"script": "안녕하세요. 오전 9시 30분에 출발해요."})
                return names, text_of(r), text_of(s)
            names, r, s = run_session(self.env(d), steps)
        self.assertEqual(names, ["check_script_numbers", "dido_voice_status", "read_numbers_like_dido", "speak_as_dido"])
        self.assertIn("사칠일구, 이삼팔육", r)
        self.assertIn("아홉 시 삼십 분", s)

    def test_no_voice_yet_explains(self):
        with tempfile.TemporaryDirectory() as d:
            async def steps(c):
                return text_of(await c.call_tool("speak_as_dido", {"text": "3시예요", "play": False}))
            out = run_session(self.env(d), steps)
        self.assertIn("ref.wav", out)

    def test_voice_folder_only_then_speaks(self):
        """음성 두 파일만 넣으면(모델은 가짜) 바로 대표 목소리 파일이 나와요."""
        with tempfile.TemporaryDirectory() as d:
            vd = pathlib.Path(d)
            (vd / "ref.wav").write_bytes(b"RIFF....WAVE")
            (vd / "ref.txt").write_text("안녕하세요, 성우 김디도예요.", encoding="utf-8")
            log = vd / "calls.txt"
            env = self.env(vd, {"PYTHONPATH": str(FAKES) + os.pathsep + os.environ.get("PYTHONPATH", ""),
                                "FAKE_TTS_LOG": str(log)})

            async def steps(c):
                st = text_of(await c.call_tool("dido_voice_status", {}))
                a = text_of(await c.call_tool("speak_as_dido", {"text": "체온이 38.5도예요.", "play": False}))
                b = text_of(await c.call_tool("speak_as_dido", {"text": "체온이 38.5도예요.", "play": False}))
                return st, a, b
            st, a, b = run_session(env, steps)
            self.assertIn('"local"', st.replace(" ", "")) if st.startswith("{") else self.assertIn("local", st)
            ra = json.loads(a)
            self.assertTrue(ra["ok"], a)
            self.assertEqual(ra["spoken_text"], "체온이 삼십팔 점 오 도예요.")
            self.assertNotIn("file", ra)  # R29-12: 서버의 절대 경로는 알려 주지 않고 result_id만
            self.assertNotIn(str(vd), a)
            self.assertTrue((vd / "out" / (ra["result_id"] + ".wav")).read_bytes().startswith(b"RIFF"))
            self.assertEqual(ra["playback"], "not_requested")
            self.assertIn("AI", ra["notice"])
            # 같은 문장은 저장해 둔 것을 써서 모델을 한 번만 불러요
            self.assertEqual(log.read_text(encoding="utf-8").splitlines(), ["체온이 삼십팔 점 오 도예요."])
            self.assertTrue(json.loads(b)["ok"])


class Core(unittest.TestCase):
    """mcp 패키지 없이도 도는 시험: 도구의 속 함수(speak_core 등)와 접근 토큰 문지기를 직접 확인해요."""

    def setUp(self):
        from unittest import mock
        import mcp_server as m
        self.m = m
        self.tmp = tempfile.TemporaryDirectory()
        self.vd = pathlib.Path(self.tmp.name)
        self.calls = []

        def synth(text):
            self.calls.append(text)
            return b"RIFFfake"

        self.eng = types.SimpleNamespace(name="local", mime="audio/wav", label="가짜 복제", synth=synth)
        self.patches = [mock.patch.object(m, "ENGINE", self.eng), mock.patch.object(m, "OUT_DIR", self.vd / "out"),
                        mock.patch.object(m, "VOICE_DIR", self.vd), mock.patch.object(m, "REMOTE", False),
                        mock.patch.object(m, "LIMIT", m.RateLimit()),
                        mock.patch.dict(os.environ, {"DIDO_MCP_PER_MIN": "100", "DIDO_MCP_PER_DAY": "1000"})]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def test_synthesis_size_limited_after_normalizing(self):
        """R29-05 재현: 입력 400자 이하라도 숫자를 풀어 읽은 글이 상한을 넘으면 합성하지 않아요."""
        long_in = "99% " * 99  # 395자 → 풀면 791자
        self.assertLessEqual(len(long_in.strip()), self.m.MAX_CHARS)
        out, _, _ = self.m.speak_core(long_in, play=False)
        self.assertFalse(out["ok"])
        self.assertIn(str(self.m.MAX_SPOKEN_CHARS), out["error"])
        self.assertEqual(self.calls, [])
        self.assertFalse(self.m.speak_core("가" * 401, play=False)[0]["ok"])
        self.assertTrue(self.m.speak_core("99% " * 10, play=False)[0]["ok"])

    def test_other_tools_have_input_limits(self):
        self.assertIn("넘어요", self.m.read_numbers_like_dido("1" * (self.m.MAX_NUMBERS_CHARS + 1)))
        self.assertIn("넘어요", self.m.check_script_numbers("1 " * self.m.MAX_SCRIPT_CHARS))

    def test_play_failure_still_returns_generated_result(self):
        """R29-06 재현: 소리를 틀다 OSError가 나도 만든 결과는 돌려줘요."""
        from unittest import mock
        with mock.patch.object(self.m, "_play", side_effect=OSError("no device")):
            out, _, _ = self.m.speak_core("안녕하세요", play=True)
        self.assertTrue(out["ok"])
        self.assertEqual((out["playback"], out["played"]), ("failed", False))
        self.assertIn("play_error", out)
        self.assertTrue((self.vd / "out" / (out["result_id"] + ".wav")).is_file())
        with mock.patch.object(self.m, "_play", return_value=True):
            out2, _, _ = self.m.speak_core("안녕하세요", play=True)
        self.assertEqual((out2["playback"], out2["play_requested"]), ("launched", True))

    def test_abuse_is_refused_by_server(self):
        """R29-03: 금지 문구·호출량·저장량을 서버가 막아요(안내 글이 아니라 코드로)."""
        out, _, _ = self.m.speak_core("지금 당장 입금하세요. 송금하지 않으면 큰일 나요.", play=False)
        self.assertFalse(out["ok"])
        self.assertEqual(self.calls, [])
        (self.vd / "blocklist.txt").write_text("# 내 금지어\n특별 금지어\n", encoding="utf-8")
        self.assertFalse(self.m.speak_core("이건 특별  금지어 예요", play=False)[0]["ok"])
        self.assertTrue(self.m.speak_core("안녕하세요", play=False)[0]["ok"])

    def test_rate_limit(self):
        os.environ["DIDO_MCP_PER_MIN"] = "2"
        r = [self.m.speak_core(f"안녕 {i}", play=False)[0]["ok"] for i in range(4)]
        self.assertEqual(r, [True, True, False, False])
        lim = self.m.RateLimit()
        os.environ["DIDO_MCP_PER_DAY"] = "3"
        os.environ["DIDO_MCP_PER_MIN"] = "100"
        self.assertEqual([lim.allow(now=1000 + i * 100) for i in range(5)], [True, True, True, False, False])
        self.assertTrue(lim.allow(now=1000 + 90000))  # 하루가 지나면 다시 돼요

    def test_output_folder_is_capped_and_audit_has_no_text(self):
        out = self.vd / "out"
        out.mkdir()
        for i in range(self.m.MAX_OUT_FILES + 10):
            (out / f"dido-old-{i:03d}.wav").write_bytes(b"x")
            os.utime(out / f"dido-old-{i:03d}.wav", (1000 + i, 1000 + i))
        res, _, _ = self.m.speak_core("비밀 문장이에요", play=False)
        self.assertLessEqual(len(list(out.glob("dido-*"))), self.m.MAX_OUT_FILES)
        self.assertTrue((out / (res["result_id"] + ".wav")).exists())
        log = (out / "audit.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("비밀", log)
        self.assertEqual(json.loads(log.splitlines()[-1])["chars"], len("비밀 문장이에요"))

    def test_first_synthesis_over_budget_says_preparing_then_cached(self):
        """R29-09: 도구 제한 시간 안에 못 끝나면 '준비 중'으로 답하고, 뒤에서 만든 결과로 다시 부르면 바로 나와요."""
        import threading
        release = threading.Event()
        done = []

        def slow(text):
            release.wait(5)
            done.append(text)
            return b"RIFFslow"

        self.eng.synth = slow
        os.environ["DIDO_MCP_BUDGET"] = "0.2"
        out, _, _ = self.m.speak_core("처음 문장", play=False)
        self.assertEqual((out["ok"], out.get("status"), out.get("retry")), (False, "preparing", True))
        release.set()
        for _ in range(50):
            if done:
                break
            time.sleep(0.05)
        self.assertEqual(done, ["처음 문장"])
        os.environ["DIDO_MCP_BUDGET"] = "5"
        self.assertTrue(self.m.speak_core("처음 문장", play=False)[0]["ok"])

    def test_remote_returns_audio_not_paths_and_never_plays(self):
        """R29-12: 주소 연결에서는 서버 경로 대신 소리를 응답에 실어요."""
        from unittest import mock
        with mock.patch.object(self.m, "REMOTE", True), mock.patch.object(self.m, "_play", side_effect=AssertionError("서버 스피커")):
            out, audio, mime = self.m.speak_core("안녕하세요", play=True)
            st = self.m.dido_voice_status()
        self.assertEqual((out["ok"], audio, mime, out["audio_included"], out["playback"]), (True, b"RIFFfake", "audio/wav", True, "not_requested"))
        text = json.dumps(out, ensure_ascii=False) + json.dumps(st, ensure_ascii=False)
        self.assertNotIn(self.tmp.name, text)
        self.assertNotIn("voice_folder", st)
        local, audio2, _ = self.m.speak_core("안녕하세요", play=False)  # 이 컴퓨터용은 기본으로 싣지 않아요
        self.assertEqual((audio2, local["audio_included"]), (None, False))

    def test_browser_engine_refused_without_synthesis(self):
        from tts import BrowserEngine
        self.m.ENGINE = BrowserEngine()
        out, audio, _ = self.m.speak_core("안녕하세요")
        self.assertFalse(out["ok"])
        self.assertIsNone(audio)

    def test_tool_descriptions_state_behavior(self):
        """R29-10: 형식·저장·전송·읽기 전용 여부를 설명에 적어요."""
        for fn in (self.m.read_numbers_like_dido, self.m.check_script_numbers):
            self.assertIn("저장하지 않아요", fn.__doc__)
        self.assertIn("소리는 만들지 않아요", self.m.dido_voice_status.__doc__)
        doc = self.m.speak_as_dido.__doc__
        for word in ("WAV 또는 MP3", "파일을 만들고", "클라우드", "preparing", "read_numbers_like_dido"):
            self.assertIn(word, doc)

    def test_token_gate(self):
        import asyncio
        sent, reached = [], []

        async def app(scope, receive, send):
            reached.append(scope["type"])

        async def send(msg):
            sent.append(msg)

        gate = self.m.TokenGate(app, "t" * 20)

        def run(headers, typ="http"):
            sent.clear()
            asyncio.run(gate({"type": typ, "headers": headers}, None, send))

        run([])
        run([(b"authorization", b"Bearer wrong")])
        run([(b"authorization", ("Bearer " + "t" * 19).encode())])
        self.assertEqual(reached, [])
        self.assertEqual(sent[0]["status"], 401)
        run([(b"authorization", ("Bearer " + "t" * 20).encode())])
        run([], typ="lifespan")
        self.assertEqual(reached, ["http", "lifespan"])

    def test_http_mode_refuses_without_token(self):
        from unittest import mock
        with mock.patch.dict(os.environ, {"DIDO_MCP_TOKEN": "짧음"}):
            with self.assertRaises(SystemExit) as cm:
                self.m.main(["--http"])
        self.assertIn("DIDO_MCP_TOKEN", str(cm.exception))
        self.assertFalse(self.m.REMOTE)


if __name__ == "__main__":
    unittest.main()
