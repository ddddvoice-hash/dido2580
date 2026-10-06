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
import unittest

HERE = pathlib.Path(__file__).resolve().parents[1]
FAKES = HERE / "tests" / "fakes"

try:
    import anyio
    from mcp import StdioServerParameters
    from mcp.client import Client
    HAVE_MCP = True
except ImportError:
    HAVE_MCP = False


def run_session(env, steps):
    async def go():
        params = StdioServerParameters(command=sys.executable, args=[str(HERE / "mcp_server.py")], env=env)
        async with Client(params) as c:
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
            self.assertTrue(pathlib.Path(ra["file"]).read_bytes().startswith(b"RIFF"))
            self.assertIn("AI", ra["notice"])
            # 같은 문장은 저장해 둔 것을 써서 모델을 한 번만 불러요
            self.assertEqual(log.read_text(encoding="utf-8").splitlines(), ["체온이 삼십팔 점 오 도예요."])
            self.assertTrue(json.loads(b)["ok"])


if __name__ == "__main__":
    unittest.main()
