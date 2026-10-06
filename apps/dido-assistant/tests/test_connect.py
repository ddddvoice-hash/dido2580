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


class ConnectSafety(Connect):
    """R29-01·02·04: 사용자의 기존 설정을 망가뜨리지 않고, 실패는 종료 코드로 알려요(임시 폴더에서만)."""

    def codex(self):
        return self.home / ".codex" / "config.toml"

    def write_codex(self, text):
        self.codex().write_bytes(text.encode("utf-8"))

    def codex_data(self):
        return tomllib.loads(self.codex().read_text(encoding="utf-8"))

    def run_connect_code(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = connect.main(list(args))
        return buf.getvalue(), code

    def test_quoted_header_is_updated_not_duplicated(self):
        """R29-01 재현: 따옴표 머리글이 있어도 같은 표를 또 더하지 않아요(TOMLDecodeError 없음)."""
        self.write_codex('model = "m"\n\n[mcp_servers."seongwoo-kimdido-voice"]\ncommand = "old.exe"\n'
                         'args = ["old.py"]\nenv = { A = "1" }\n\n[other]\nx = 1\n')
        self.run_connect()
        d = self.codex_data()
        mine = d["mcp_servers"][connect.NAME]
        self.assertTrue(mine["args"][0].endswith("mcp_server.py"))
        self.assertNotEqual(mine["command"], "old.exe")
        self.assertEqual(mine["env"], {"A": "1"})
        self.assertEqual((d["model"], d["other"]), ("m", {"x": 1}))
        self.assertEqual(self.codex().read_text(encoding="utf-8").count("seongwoo-kimdido-voice"), 1)

    def test_stale_plain_header_is_refreshed(self):
        """R29-01 재현: 머리글이 같아도 경로가 오래됐으면 '이미 연결됨'으로 넘기지 않고 고쳐요."""
        self.write_codex('[mcp_servers.seongwoo-kimdido-voice]\ncommand = "old.exe"\nargs = [\n  "a",  # ] 주석\n  "b]",\n]\n'
                         'startup_timeout_sec = 5\n[mcp_servers.keep]\ncommand = "k"\n')
        out = self.run_connect()
        self.assertNotIn("GPT(Codex CLI): 이미 연결됨", out)
        d = self.codex_data()
        mine = d["mcp_servers"][connect.NAME]
        self.assertTrue(mine["args"][0].endswith("mcp_server.py"))
        self.assertEqual(len(mine["args"]), 1)
        self.assertEqual(mine["startup_timeout_sec"], 5)
        self.assertEqual(d["mcp_servers"]["keep"], {"command": "k"})
        self.assertIn("GPT(Codex CLI): 이미 연결됨", self.run_connect())  # 두 번째는 정말 같아요

    def test_unsupported_toml_shapes_untouched(self):
        for text in ('mcp_servers = { "seongwoo-kimdido-voice" = { command = "x" } }\n',
                     'mcp_servers.seongwoo-kimdido-voice.command = "x"\n',
                     "model = \n", 'mcp_servers = 3\n'):
            self.write_codex(text)
            self.assertEqual(self.run_connect_code()[1], 1, text)
            self.assertEqual(self.codex().read_text(encoding="utf-8"), text)
        self.assertFalse(self.codex().with_suffix(".toml.bak").exists())

    def test_crlf_and_comments_kept(self):
        self.write_codex('# 내 설정\r\nmodel = "m"  # 모델\r\n')
        self.run_connect()
        raw = self.codex().read_bytes().decode("utf-8")
        self.assertTrue(raw.startswith('# 내 설정\r\nmodel = "m"  # 모델\r\n'))
        self.assertEqual(raw.count("\n"), raw.count("\r\n"))
        self.assertEqual(self.codex_data()["model"], "m")
        self.assertIn("GPT(Codex CLI): 이미 연결됨", self.run_connect())

    def test_json_keeps_extra_server_fields(self):
        """R29-02 재현: 같은 서버의 env·timeout이 사라지지 않아요."""
        p = self.home / ".gemini" / "settings.json"
        p.write_text(json.dumps({"mcpServers": {connect.NAME: {"command": "old", "args": ["x"],
                     "env": {"K": "v"}, "timeout": 5000}, "z": {"command": "z"}}, "ui": {"a": 1}}), encoding="utf-8")
        self.run_connect()
        d = json.loads(p.read_text(encoding="utf-8"))
        m = d["mcpServers"][connect.NAME]
        self.assertEqual((m["env"], m["timeout"]), ({"K": "v"}, 5000))
        self.assertTrue(m["args"][0].endswith("mcp_server.py"))
        self.assertEqual((d["mcpServers"]["z"], d["ui"]), ({"command": "z"}, {"a": 1}))

    def test_json_odd_shapes_do_not_crash(self):
        """R29-02 재현: [] · null · mcpServers가 null이어도 예외 없이 건너뛰고 파일은 그대로예요."""
        p = self.home / ".gemini" / "settings.json"
        for text in ("[]", "null", '{"mcpServers": null}', '{"mcpServers": []}',
                     json.dumps({"mcpServers": {connect.NAME: "x"}})):
            p.write_text(text, encoding="utf-8")
            out, code = self.run_connect_code()
            self.assertEqual(code, 1, text)
            self.assertEqual(p.read_text(encoding="utf-8"), text)

    def test_exit_code_zero_on_success_and_one_on_failure(self):
        self.assertEqual(self.run_connect_code()[1], 0)
        (self.home / ".gemini" / "settings.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(self.run_connect_code()[1], 1)

    def test_backup_never_overwritten_and_no_temp_left(self):
        c = self.appdata / "Claude" / "claude_desktop_config.json"
        original = c.read_text(encoding="utf-8")
        self.run_connect()
        bak = c.with_name(c.name + ".bak")
        self.assertEqual(bak.read_text(encoding="utf-8"), original)
        d = json.loads(c.read_text(encoding="utf-8"))
        d["mcpServers"][connect.NAME]["command"] = "stale"
        c.write_text(json.dumps(d), encoding="utf-8")
        self.run_connect()
        self.assertEqual(bak.read_text(encoding="utf-8"), original)  # 처음 백업은 그대로
        self.assertEqual(len(list(c.parent.glob("*.bak-*"))), 1)  # 새 백업은 따로
        self.assertEqual(list(self.home.rglob("*.tmp")) + list(self.appdata.rglob("*.tmp")), [])

    def test_write_failure_keeps_original(self):
        from unittest import mock
        before = self.codex().read_bytes()
        with mock.patch.object(connect.os, "replace", side_effect=OSError("disk")):
            out, code = self.run_connect_code()
        self.assertEqual(code, 1)
        self.assertEqual(self.codex().read_bytes(), before)
        self.assertEqual(list(self.home.rglob("*.tmp")), [])

    def test_claude_code_failure_is_exit_code(self):
        from unittest import mock
        r = mock.Mock(returncode=1, stdout="", stderr="boom")
        with mock.patch.object(connect.shutil, "which", return_value="claude"), \
                mock.patch.object(connect.subprocess, "run", return_value=r):
            out, code = self.run_connect_code()
        self.assertEqual(code, 1)
        self.assertIn("Claude Code 연결 실패", out)

    def test_claude_code_already_exists_gives_hint(self):
        from unittest import mock
        r = mock.Mock(returncode=1, stdout="", stderr="MCP server already exists")
        with mock.patch.object(connect.shutil, "which", return_value="claude"), \
                mock.patch.object(connect.subprocess, "run", return_value=r):
            out, code = self.run_connect_code()
        self.assertEqual(code, 0)
        self.assertIn("claude mcp remove", out)

    def test_tool_timeout_added_for_codex(self):
        self.run_connect()
        self.assertEqual(self.codex_data()["mcp_servers"][connect.NAME]["tool_timeout_sec"], connect.TOOL_TIMEOUT_SEC)


if __name__ == "__main__":
    unittest.main()
