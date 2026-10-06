"""성우 김디도 음성 비서를 AI 앱에 연결해요(Claude·GPT·Gemini).

    python apps/dido-assistant/connect.py            # 연결(바꾸기 전에 원래 설정을 .bak으로 남겨요)
    python apps/dido-assistant/connect.py --dry-run  # 무엇을 바꿀지만 보여 줘요

연결하는 곳(설치된 앱만):
- Claude 데스크톱  : %APPDATA%\\Claude\\claude_desktop_config.json 의 mcpServers
- Claude Code     : `claude mcp add` 명령
- Gemini CLI      : ~/.gemini/settings.json 의 mcpServers
- GPT(Codex CLI)  : ~/.codex/config.toml 의 [mcp_servers.…]
ChatGPT 웹은 이 컴퓨터의 설정 파일로는 붙지 않아요. 공개 HTTPS 주소 또는 Secure MCP Tunnel(비공개 서버용)이 필요해요(README).

설정 파일을 다루는 규칙(사용자의 기존 설정을 망가뜨리지 않기 위해)
- 우리 항목(NAME)의 command·args만 바꾸고, 그 항목의 env·timeout 같은 다른 키와 다른 서버·다른 설정은 그대로 둬요.
- 쓰기 전에 읽어서 구조를 검사하고, 이상하면(깨진 파일·예상 밖 구조) 손대지 않고 실패로 알려요.
- 바꾸기 전에 .bak(이미 있으면 .bak-날짜시각)을 남기고, 임시 파일에 쓴 뒤 바꿔치기(원자적)해요.
- TOML은 표준 라이브러리 tomllib로 읽어 검증하고, 저장 전에 결과를 다시 읽어 다른 설정이 그대로인지 확인해요.
- 연결에 실패한 앱이 하나라도 있으면 종료 코드 1이에요(setup-voice.cmd가 확인해요).
"""
from __future__ import annotations

import argparse
import copy
import datetime as _dt
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

try:
    import tomllib
except ImportError:  # 파이썬 3.10 이하
    tomllib = None

HERE = pathlib.Path(__file__).resolve().parent
NAME = "seongwoo-kimdido-voice"
TOOL_TIMEOUT_SEC = 120  # 처음 목소리를 준비할 때 오래 걸릴 수 있어서(Codex 기본은 60초)
LF, CRLF = chr(10), chr(13) + chr(10)
OK, SKIP, FAIL = "ok", "skip", "fail"  # 결과 종류: 연결됨/이미 됨·건너뜀(문제 아님)·실패


def server_cmd() -> tuple[str, list[str]]:
    return sys.executable, [str(HERE / "mcp_server.py")]


def home() -> pathlib.Path:
    return pathlib.Path(os.environ.get("DIDO_HOME_OVERRIDE") or pathlib.Path.home())


def appdata() -> pathlib.Path:
    return pathlib.Path(os.environ.get("DIDO_APPDATA_OVERRIDE") or os.environ.get("APPDATA") or home() / "AppData" / "Roaming")


def _backup(p: pathlib.Path):
    """원래 파일을 .bak으로 남겨요. .bak이 이미 있으면 덮어쓰지 않고 날짜시각을 붙여요."""
    if not p.exists():
        return
    bak = p.with_suffix(p.suffix + ".bak")
    if bak.exists():
        bak = p.with_suffix(p.suffix + f".bak-{_dt.datetime.now():%Y%m%d-%H%M%S-%f}")
    shutil.copy2(p, bak)


def _atomic_write(p: pathlib.Path, data: bytes):
    """같은 폴더의 임시 파일에 다 쓴 뒤 바꿔치기해요. 중간에 끊겨도 원래 파일은 온전해요."""
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + f".{os.getpid()}.tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, p)
    finally:
        if tmp.exists():
            tmp.unlink()


def _done(dry: bool, path) -> str:
    return f"{'바꿀 예정' if dry else '연결함'}: {path}"


# ---------------------------------------------------------------- JSON (Claude 데스크톱, Gemini CLI)

def merge_json(path: pathlib.Path, dry: bool) -> tuple[str, str]:
    cmd, args = server_cmd()
    raw = None
    data = {}
    if path.exists():
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8-sig")
            data = json.loads(text) if text.strip() else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            return FAIL, f"건너뜀: {path} 을 읽지 못했어요(JSON 형식 오류). 손대지 않았어요."
    if not isinstance(data, dict):
        return FAIL, f"건너뜀: {path} 의 맨 위가 JSON 객체가 아니에요. 손대지 않았어요."
    servers = data.get("mcpServers", {}) if "mcpServers" in data else {}
    if not isinstance(servers, dict):
        return FAIL, f"건너뜀: {path} 의 mcpServers 가 객체가 아니에요. 손대지 않았어요."
    new = copy.deepcopy(data)
    new_servers = new.setdefault("mcpServers", {})
    mine = new_servers.get(NAME, {})
    if not isinstance(mine, dict):
        return FAIL, f"건너뜀: {path} 의 {NAME} 항목이 객체가 아니에요. 손대지 않았어요."
    mine["command"], mine["args"] = cmd, args  # 우리 항목에서도 이 두 키만 바꿔요(env·timeout 등은 그대로)
    new_servers[NAME] = mine
    if new == data and path.exists():
        return OK, f"이미 연결됨: {path}"
    if not dry:
        _backup(path)
        out = json.dumps(new, ensure_ascii=False, indent=2).encode("utf-8")
        try:
            _atomic_write(path, out)
        except OSError as e:
            return FAIL, f"실패: {path} 에 쓰지 못했어요({type(e).__name__})."
    return OK, _done(dry, path)


# ---------------------------------------------------------------- TOML (Codex CLI)

def _q(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)  # TOML 기본 문자열은 JSON 문자열과 같은 꼴


def toml_block(nl: str = "\n") -> str:
    cmd, args = server_cmd()
    return nl.join(["", f"[mcp_servers.{NAME}]", f"command = {_q(cmd)}",
                    f"args = [{', '.join(_q(a) for a in args)}]",
                    f"tool_timeout_sec = {TOOL_TIMEOUT_SEC}", ""])


def _seg(s: str) -> str:
    return rf'(?:{re.escape(s)}|"{re.escape(s)}"|\'{re.escape(s)}\')'


_HEADER = re.compile(rf"^[ \t]*\[[ \t]*{_seg('mcp_servers')}[ \t]*\.[ \t]*{_seg(NAME)}[ \t]*\][ \t]*(?:#[^\r\n]*)?\r?$", re.M)
_ANY_HEADER = re.compile(r"^[ \t]*\[", re.M)


def _value_end(text: str, i: int) -> int:
    """text[i:]에서 시작하는 TOML 값(한 줄 값이나 여러 줄 배열)의 끝 위치. 문자열 안의 괄호는 세지 않아요."""
    depth, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in "\"'":
            q = c * 3 if text.startswith(c * 3, i) else c
            i += len(q)
            while i < n and not text.startswith(q, i):
                i += 2 if (q[0] == '"' and text[i] == "\\") else 1
            i += len(q)
            continue
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
        elif c == "#":
            while i < n and text[i] != "\n":
                i += 1
            continue
        elif c == "\n" and depth <= 0:
            return i - 1 if text[i - 1:i] == "\r" else i  # CRLF의 \r은 값에 넣지 않아요
        i += 1
    return n


def _set_key(section: str, key: str, value: str, nl: str) -> str:
    """section(헤더 줄 다음부터 다음 표 머리글 전까지)에서 key 한 줄(또는 여러 줄 배열)을 value로 바꿔요. 없으면 맨 앞에 넣어요."""
    m = re.search(rf"^[ \t]*{_seg(key)}[ \t]*=[ \t]*", section, re.M)
    if not m:
        return f"{key} = {value}{nl}" + section
    end = _value_end(section, m.end())
    return section[:m.start()] + f"{key} = {value}" + section[end:]


def _toml_edit(text: str, nl: str) -> str:
    """text에서 우리 표를 갱신하거나 끝에 더한 새 text를 돌려줘요. 못 하면 ValueError."""
    cmd, args = server_cmd()
    m = _HEADER.search(text)
    if not m:
        if not text.strip():
            return toml_block(nl).lstrip(CRLF)
        return text.rstrip(CRLF) + nl + toml_block(nl)
    if LF not in text[m.end():]:
        text += nl  # 머리글이 파일 맨 끝 줄이면 줄바꿈부터 더해요
    head_end = text.index(LF, m.end()) + 1
    nxt = _ANY_HEADER.search(text, head_end)
    body_end = nxt.start() if nxt else len(text)
    body = text[head_end:body_end]
    if body and not body.endswith(LF):
        body += nl
    body = _set_key(body, "args", f"[{', '.join(_q(a) for a in args)}]", nl)
    body = _set_key(body, "command", _q(cmd), nl)
    if not re.search(rf"^[ \t]*{_seg('tool_timeout_sec')}[ \t]*=", body, re.M):
        body = f"tool_timeout_sec = {TOOL_TIMEOUT_SEC}{nl}" + body
    return text[:head_end] + body + text[body_end:]


def merge_codex(path: pathlib.Path, dry: bool) -> tuple[str, str]:
    cmd, args = server_cmd()
    raw = path.read_bytes() if path.exists() else b""
    bom = raw.startswith(b"\xef\xbb\xbf")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return FAIL, f"건너뜀: {path} 을 읽지 못했어요(UTF-8이 아니에요). 손대지 않았어요."
    if text.strip() and tomllib is None:
        return FAIL, f"건너뜀: 이 파이썬({sys.version_info.major}.{sys.version_info.minor})에는 TOML 검사 기능이 없어요(3.11 이상 필요). 손대지 않았어요."
    try:
        before = tomllib.loads(text) if text.strip() else {}
    except tomllib.TOMLDecodeError:
        return FAIL, f"건너뜀: {path} 을 읽지 못했어요(TOML 형식 오류). 손대지 않았어요."
    servers = before.get("mcp_servers", {})
    if not isinstance(servers, dict) or not isinstance(servers.get(NAME, {}), dict):
        return FAIL, f"건너뜀: {path} 의 mcp_servers 구조가 예상과 달라요. 손대지 않았어요."
    nl = "\r\n" if "\r\n" in text else "\n"
    try:
        new_text = _toml_edit(text, nl)
        after = tomllib.loads(new_text)
    except (tomllib.TOMLDecodeError, ValueError):
        return FAIL, f"건너뜀: {path} 에 안전하게 쓸 수 없어요(우리 항목이 특이한 모양이에요). 손대지 않았어요."
    # 검증: 다른 설정은 그대로이고, 우리 항목은 command·args가 새 값이어야 해요
    want = copy.deepcopy(before)
    mine = want.setdefault("mcp_servers", {}).setdefault(NAME, {})
    mine["command"], mine["args"] = cmd, args
    mine.setdefault("tool_timeout_sec", TOOL_TIMEOUT_SEC)
    if after != want:
        return FAIL, f"건너뜀: {path} 의 다른 설정이 바뀔 것 같아요. 손대지 않았어요."
    if new_text == text and path.exists():
        return OK, f"이미 연결됨: {path}"
    if not dry:
        _backup(path)
        out = ("﻿" if bom else "") + new_text
        try:
            _atomic_write(path, out.encode("utf-8"))
        except OSError as e:
            return FAIL, f"실패: {path} 에 쓰지 못했어요({type(e).__name__})."
    return OK, _done(dry, path)


# ---------------------------------------------------------------- Claude Code

def claude_code(dry: bool) -> tuple[str, str]:
    exe = shutil.which("claude")
    cmd, args = server_cmd()
    line = ["claude", "mcp", "add", "--scope", "user", NAME, "--", cmd, *args]
    if not exe:
        return SKIP, "Claude Code 없음: 설치 뒤 다시 실행하면 연결돼요."
    if dry:
        return OK, "바꿀 예정: " + " ".join(line)
    try:
        r = subprocess.run([exe, *line[1:]], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return FAIL, f"Claude Code 연결 실패({type(e).__name__})"
    out = (r.stdout + r.stderr).strip()
    if r.returncode == 0:
        return OK, "연결함: Claude Code"
    if "already exists" in out:  # 오래된 경로가 남았을 수 있어서 이미 있다고만 말하지 않고 확인 방법을 알려요
        return OK, (f"이미 등록돼 있어요: Claude Code. 설치 위치를 옮겼다면 PowerShell에서 "
                    f"claude mcp remove --scope user {NAME} 을 한 번 하고 이 파일을 다시 실행해 주세요.")
    return FAIL, f"Claude Code 연결 실패: {out[:200]}"


def targets():
    return [
        ("Claude 데스크톱", appdata() / "Claude" / "claude_desktop_config.json", merge_json, appdata() / "Claude"),
        ("Gemini CLI", home() / ".gemini" / "settings.json", merge_json, home() / ".gemini"),
        ("GPT(Codex CLI)", home() / ".codex" / "config.toml", merge_codex, home() / ".codex"),
    ]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--all", action="store_true", help="설치 흔적이 없어도 설정 파일을 만들어요")
    a = ap.parse_args(argv)
    try:
        import mcp  # noqa: F401
    except ImportError:
        print("[먼저] pip install mcp 를 해 주세요(setup-voice.cmd가 해 줘요).")
    lines, failed = [], 0
    for label, path, fn, app_dir in targets():
        if not a.all and not app_dir.exists():
            lines.append(f"{label}: 설치 흔적이 없어 건너뜀")
            continue
        status, msg = fn(path, a.dry_run)
        failed += status == FAIL
        lines.append(f"{label}: {msg}")
    status, msg = claude_code(a.dry_run)
    failed += status == FAIL
    lines.append("Claude Code: " + msg)
    print("\n".join(lines))
    if failed:
        print(f"\n[연결 실패 {failed}곳] 위 안내를 확인해 주세요. 손대지 않은 설정 파일은 그대로예요.")
        return 1
    print("\n연결한 앱은 껐다 켜면 '성우 김디도 음성 비서' 도구가 보여요. 예: \"김디도 목소리로 '오전 9시 30분에 출발해요' 읽어 줘\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
