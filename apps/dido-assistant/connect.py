"""성우 김디도 음성 비서를 AI 앱에 연결해요(Claude·GPT·Gemini).

    python apps/dido-assistant/connect.py            # 연결(바꾸기 전에 원래 설정을 .bak으로 남겨요)
    python apps/dido-assistant/connect.py --dry-run  # 무엇을 바꿀지만 보여 줘요

연결하는 곳(설치된 앱만):
- Claude 데스크톱  : %APPDATA%\\Claude\\claude_desktop_config.json 의 mcpServers
- Claude Code     : `claude mcp add` 명령
- Gemini CLI      : ~/.gemini/settings.json 의 mcpServers
- GPT(Codex CLI)  : ~/.codex/config.toml 의 [mcp_servers.…]
ChatGPT 웹은 인터넷 주소(HTTPS)가 있는 MCP 서버만 붙일 수 있어서, 공개 서버를 연 뒤에 연결해요(README).
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
NAME = "seongwoo-kimdido-voice"


def server_cmd() -> tuple[str, list[str]]:
    return sys.executable, [str(HERE / "mcp_server.py")]


def home() -> pathlib.Path:
    return pathlib.Path(os.environ.get("DIDO_HOME_OVERRIDE") or pathlib.Path.home())


def appdata() -> pathlib.Path:
    return pathlib.Path(os.environ.get("DIDO_APPDATA_OVERRIDE") or os.environ.get("APPDATA") or home() / "AppData" / "Roaming")


def _backup(p: pathlib.Path):
    if p.exists():
        shutil.copy2(p, p.with_suffix(p.suffix + ".bak"))


def merge_json(path: pathlib.Path, dry: bool) -> str:
    cmd, args = server_cmd()
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            return f"건너뜀: {path} 을 읽지 못했어요(JSON 형식 오류). 손대지 않았어요."
    servers = data.setdefault("mcpServers", {})
    want = {"command": cmd, "args": args}
    if servers.get(NAME) == want:
        return f"이미 연결됨: {path}"
    servers[NAME] = want
    if not dry:
        path.parent.mkdir(parents=True, exist_ok=True)
        _backup(path)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return f"{'바꿀 예정' if dry else '연결함'}: {path}"


def toml_block() -> str:
    cmd, args = server_cmd()
    q = lambda s: json.dumps(s, ensure_ascii=False)  # TOML 기본 문자열은 JSON 문자열과 같은 꼴
    return f"\n[mcp_servers.{NAME}]\ncommand = {q(cmd)}\nargs = [{', '.join(q(a) for a in args)}]\n"


def merge_codex(path: pathlib.Path, dry: bool) -> str:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if f"[mcp_servers.{NAME}]" in text:
        return f"이미 연결됨: {path}"
    if not dry:
        path.parent.mkdir(parents=True, exist_ok=True)
        _backup(path)
        path.write_text(text.rstrip("\n") + "\n" + toml_block(), encoding="utf-8")
    return f"{'바꿀 예정' if dry else '연결함'}: {path}"


def claude_code(dry: bool) -> str:
    exe = shutil.which("claude")
    cmd, args = server_cmd()
    line = ["claude", "mcp", "add", "--scope", "user", NAME, "--", cmd, *args]
    if not exe:
        return "Claude Code 없음: 설치 뒤 다시 실행하면 연결돼요."
    if dry:
        return "바꿀 예정: " + " ".join(line)
    r = subprocess.run([exe, *line[1:]], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if r.returncode == 0 or "already exists" in out:
        return "연결함: Claude Code"
    return f"Claude Code 연결 실패: {out[:200]}"


def targets():
    return [
        ("Claude 데스크톱", appdata() / "Claude" / "claude_desktop_config.json", merge_json, appdata() / "Claude"),
        ("Gemini CLI", home() / ".gemini" / "settings.json", merge_json, home() / ".gemini"),
        ("GPT(Codex CLI)", home() / ".codex" / "config.toml", merge_codex, home() / ".codex"),
    ]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--all", action="store_true", help="설치 흔적이 없어도 설정 파일을 만들어요")
    a = ap.parse_args(argv)
    try:
        import mcp  # noqa: F401
    except ImportError:
        print("[먼저] pip install mcp 를 해 주세요(setup-voice.cmd가 해 줘요).")
    lines = []
    for label, path, fn, app_dir in targets():
        if not a.all and not app_dir.exists():
            lines.append(f"{label}: 설치 흔적이 없어 건너뜀")
            continue
        lines.append(f"{label}: " + fn(path, a.dry_run))
    lines.append("Claude Code: " + claude_code(a.dry_run))
    print("\n".join(lines))
    print("\n연결한 앱은 껐다 켜면 '성우 김디도 음성 비서' 도구가 보여요. 예: \"김디도 목소리로 '오전 9시 30분에 출발해요' 읽어 줘\"")


if __name__ == "__main__":
    main()
