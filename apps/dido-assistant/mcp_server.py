"""성우 김디도 음성 비서 MCP 서버 — Claude·GPT·Gemini가 이 비서를 불러 쓰게 해요.

MCP(Model Context Protocol)는 AI 앱이 바깥 도구를 부르는 공통 규격이에요. 이 서버 하나로
Claude(데스크톱·Claude Code), GPT(Codex CLI, ChatGPT 개발자 모드 연결), Gemini(Gemini CLI)가
같은 도구를 써요. 연결 설정은 connect.py가 써 줘요.

    python apps/dido-assistant/mcp_server.py              # 이 컴퓨터의 AI 앱용(stdio)
    python apps/dido-assistant/mcp_server.py --http       # 주소로 부르는 AI용 http://127.0.0.1:8772/mcp

필요: pip install mcp   (mcp 2.x의 MCPServer, 1.x의 FastMCP 둘 다 돼요)
"""
from __future__ import annotations

import argparse
import datetime as _dt
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from brain import tool_check_script  # noqa: E402
from korean_numbers import normalize  # noqa: E402
from tts import VOICE_DIR, make_engine, synth_or_none, voice_ready  # noqa: E402

try:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

INSTRUCTIONS = (
    "성우 김디도의 목소리로 말하는 AI 음성 비서의 도구예요. 사용자가 '김디도 목소리로', '디도 비서로 말해 줘', "
    "'이 대본 숫자 점검해 줘'라고 하면 써요. 만든 소리는 AI 목소리예요. 성우 김디도가 하지 않은 말을 "
    "그의 말처럼 속이는 데 쓰지 말고, 사칭·사기·혐오·정치 광고에 쓰지 않아요."
)

mcp = _Server(name="seongwoo-kimdido-voice", instructions=INSTRUCTIONS)
ENGINE = None
OUT_DIR = VOICE_DIR / "out"
MAX_CHARS = 400


def engine():
    global ENGINE
    if ENGINE is None:
        ENGINE = make_engine()
    return ENGINE


def _play(path: pathlib.Path) -> bool:
    """윈도우면 바로 틀어요. 다른 곳에서는 파일만 남겨요."""
    if sys.platform != "win32":
        return False
    import winsound
    winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
    return True


@mcp.tool()
def speak_as_dido(text: str, play: bool = True) -> dict:
    """글을 성우 김디도의 목소리(AI)로 읽어요. 숫자는 사람처럼 풀어 읽고, WAV 파일을 만들어 이 컴퓨터에서 틀어요.

    text: 읽을 한국어 글(400자 이하). play: 이 컴퓨터 스피커로 바로 틀지.
    """
    text = (text or "").strip()
    if not text or len(text) > MAX_CHARS:
        return {"ok": False, "error": f"글이 비었거나 {MAX_CHARS}자를 넘어요."}
    spoken = normalize(text)
    eng = engine()
    if eng.name == "browser":
        ok, why = voice_ready()
        return {"ok": False, "spoken_text": spoken,
                "error": "아직 성우 김디도 목소리 엔진이 없어요. "
                         + ("voice 폴더는 준비됐으니 setup-voice.cmd를 실행해 주세요." if ok else f"voice 폴더: {why}")}
    audio, warn = synth_or_none(eng, spoken)
    if not audio:
        return {"ok": False, "spoken_text": spoken, "error": warn}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"dido-{_dt.datetime.now():%Y%m%d-%H%M%S-%f}.wav"
    path.write_bytes(audio)
    played = _play(path) if play else False
    return {"ok": True, "spoken_text": spoken, "file": str(path), "played": played,
            "engine": eng.label, "notice": "AI로 만든 성우 김디도 목소리예요."}


@mcp.tool()
def read_numbers_like_dido(text: str) -> str:
    """문장 속 숫자를 성우 김디도의 숫자 읽기 기준으로 사람이 읽는 말로 풀어요(예: 4719-2386 → 사칠일구, 이삼팔육)."""
    return normalize(text or "")


@mcp.tool()
def check_script_numbers(script: str) -> str:
    """녹음할 대본에서 숫자·기호가 든 문장을 모두 찾아 문장마다 읽는 법을 알려 줘요."""
    return tool_check_script({"script": script or ""})


@mcp.tool()
def dido_voice_status() -> dict:
    """성우 김디도 음성 비서의 현재 상태(쓰는 목소리 엔진, 목소리 폴더 준비)를 알려 줘요."""
    ok, why = voice_ready()
    eng = engine()
    return {"engine": eng.name, "engine_label": eng.label, "voice_folder": str(VOICE_DIR),
            "voice_ready": ok, "voice_detail": why,
            "notice": "이 도구가 만드는 소리는 AI 목소리예요."}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--http", action="store_true", help="주소(http://127.0.0.1:포트/mcp)로 열기")
    ap.add_argument("--port", type=int, default=8772)
    a = ap.parse_args(argv)
    if a.http:
        try:  # mcp 2.x
            mcp.run(transport="streamable-http", host="127.0.0.1", port=a.port)
        except TypeError:  # mcp 1.x는 설정으로 받아요
            mcp.settings.host, mcp.settings.port = "127.0.0.1", a.port
            mcp.run(transport="streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
