"""connect.py가 다른 설정을 지키면서 성우 김디도 음성 비서만 더하는지 확인해요.

    python apps/dido-assistant/tests/test_connect.py
"""
import contextlib
import io
import json
import os
import pathlib
import sys
import tempfile
import tomllib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import connect  # noqa: E402


class Connect(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = pathlib.Path(self.tmp.name)
        self.home, self.appdata = t / "home", t / "appdata"
        (self.appdata / "Claude").mkdir(parents=True)
        (self.home / ".gemini").mkdir(parents=True)
        (self.home / ".codex").mkdir(parents=True)
        (self.appdata / "Claude" / "claude_desktop_config.json").write_text(
            json.dumps({"mcpServers": {"other": {"command": "x"}}, "theme": "dark"}), encoding="utf-8")
        (self.home / ".codex" / "config.toml").write_text('model = "gpt-6-astra"\n', encoding="utf-8")
        os.environ.update(DIDO_HOME_OVERRIDE=str(self.home), DIDO_APPDATA_OVERRIDE=str(self.appdata), PATH="")

    def tearDown(self):
        for k in ("DIDO_HOME_OVERRIDE", "DIDO_APPDATA_OVERRIDE"):
            os.environ.pop(k)
        self.tmp.cleanup()

    def run_connect(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            connect.main(list(args))
        return buf.getvalue()

    def test_dry_run_changes_nothing(self):
        before = (self.home / ".codex" / "config.toml").read_text(encoding="utf-8")
        out = self.run_connect("--dry-run")
        self.assertIn("바꿀 예정", out)
        self.assertEqual((self.home / ".codex" / "config.toml").read_text(encoding="utf-8"), before)
        self.assertFalse((self.home / ".gemini" / "settings.json").exists())

    def test_connect_keeps_other_settings_and_is_idempotent(self):
        self.run_connect()
        out2 = self.run_connect()
        claude = json.loads((self.appdata / "Claude" / "claude_desktop_config.json").read_text(encoding="utf-8"))
        self.assertEqual(claude["theme"], "dark")
        self.assertIn("other", claude["mcpServers"])
        self.assertTrue(claude["mcpServers"][connect.NAME]["args"][0].endswith("mcp_server.py"))
        gem = json.loads((self.home / ".gemini" / "settings.json").read_text(encoding="utf-8"))
        self.assertIn(connect.NAME, gem["mcpServers"])
        codex = tomllib.loads((self.home / ".codex" / "config.toml").read_text(encoding="utf-8"))
        self.assertEqual(codex["model"], "gpt-6-astra")
        self.assertTrue(codex["mcp_servers"][connect.NAME]["args"][0].endswith("mcp_server.py"))
        self.assertTrue((self.appdata / "Claude" / "claude_desktop_config.json.bak").exists())
        self.assertEqual(out2.count("이미 연결됨"), 3)
        self.assertIn("Claude Code 없음", out2)

    def test_broken_json_untouched(self):
        p = self.home / ".gemini" / "settings.json"
        p.write_text("{not json", encoding="utf-8")
        out = self.run_connect()
        self.assertIn("JSON 형식 오류", out)
        self.assertEqual(p.read_text(encoding="utf-8"), "{not json")

    def test_skip_missing_apps(self):
        import shutil
        shutil.rmtree(self.home / ".gemini")
        out = self.run_connect()
        self.assertIn("Gemini CLI: 설치 흔적이 없어 건너뜀", out)


if __name__ == "__main__":
    unittest.main()
