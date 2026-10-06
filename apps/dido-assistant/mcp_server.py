"""성우 김디도 음성 비서 MCP 서버 — Claude·GPT·Gemini가 이 비서를 불러 쓰게 해요.

MCP(Model Context Protocol)는 AI 앱이 바깥 도구를 부르는 공통 규격이에요. 이 서버 하나로
Claude(데스크톱·Claude Code), GPT(Codex CLI, ChatGPT 개발자 모드 연결), Gemini(Gemini CLI)가
같은 도구를 써요. 연결 설정은 connect.py가 써 줘요.

    python apps/dido-assistant/mcp_server.py              # 이 컴퓨터의 AI 앱용(stdio)
    DIDO_MCP_TOKEN=... python apps/dido-assistant/mcp_server.py --http   # 주소용 http://127.0.0.1:8772/mcp (토큰 필수)

필요: pip install mcp   (mcp 2.x의 MCPServer, 1.x의 FastMCP 둘 다 돼요)

악용 막기는 이 서버가 직접 강제해요(AI에게 주는 안내 글에만 맡기지 않아요).
- 글 길이 상한(입력 400자, 다듬은 뒤 600자), 분당·하루 호출 상한, 만든 파일 개수·용량 상한
- 사기·협박·정치 광고로 보이는 문구는 목소리로 만들기를 거절(최소한의 바닥선. 대표가 voice/blocklist.txt에 줄마다 더할 수 있어요)
- 만들 때마다 voice/out/audit.jsonl에 기록(글 원문은 남기지 않고 길이·해시만)
- --http는 접근 토큰(DIDO_MCP_TOKEN, 16자 이상)이 없으면 켜지지 않고, 이 컴퓨터(127.0.0.1)에만 열어요.
  밖에서 부르려면 HTTPS 역방향 프록시나 Secure MCP Tunnel 뒤에 두세요(README).
"""
from __future__ import annotations

import argparse
import base64
import collections
import datetime as _dt
import hashlib
import hmac
import json
import os
import pathlib
import sys
import threading
import time
import unicodedata

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from brain import tool_check_script  # noqa: E402
from korean_numbers import normalize  # noqa: E402
from tts import VOICE_DIR, make_engine, synth_or_none, voice_ready  # noqa: E402

try:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:
    try:  # mcp 1.x
        from mcp.server.fastmcp import FastMCP as _Server
    except ImportError:  # mcp가 없어도 도구 함수는 불러서 시험할 수 있게 해요
        class _Server:  # type: ignore[no-redef]
            def __init__(self, **kw):
                pass

            def tool(self, *a, **kw):
                return lambda fn: fn

            def run(self, *a, **kw):
                raise SystemExit("먼저 pip install mcp 를 해 주세요.")

INSTRUCTIONS = (
    "성우 김디도의 목소리로 말하는 AI 음성 비서의 도구예요. 사용자가 '김디도 목소리로', '디도 비서로 말해 줘', "
    "'이 대본 숫자 점검해 줘'라고 하면 써요. 만든 소리는 AI 목소리예요. 성우 김디도가 하지 않은 말을 "
    "그의 말처럼 속이는 데 쓰지 말고, 사칭·사기·혐오·정치 광고에 쓰지 않아요. "
    "(이 서버가 길이·호출량·금지 문구를 따로 검사하니, 거절되면 이유를 사용자에게 그대로 알려 주세요.)"
)

mcp = _Server(name="seongwoo-kimdido-voice", instructions=INSTRUCTIONS)
ENGINE = None
OUT_DIR = VOICE_DIR / "out"
MAX_CHARS = 400            # 받는 글
MAX_SPOKEN_CHARS = 600     # 숫자를 풀어 읽은 뒤의 글(목소리 서버 상한 800자 안쪽)
MAX_NUMBERS_CHARS = 2000   # read_numbers_like_dido 입력
MAX_SCRIPT_CHARS = 20000   # check_script_numbers 입력
MAX_OUT_FILES = 50         # voice/out에 남기는 파일 수
MAX_OUT_BYTES = 100 * 1024 * 1024
MAX_ATTACH_BYTES = 3 * 1024 * 1024  # 소리를 응답에 직접 실을 때의 상한
MAX_AUDIT_BYTES = 1024 * 1024
MAX_SYNTH_JOBS = 2         # 동시에 도는 합성 수(시간이 지나도 누적되지 않게)
REMOTE = False             # --http로 열렸는지(이 서버의 스피커는 사용자 것이 아니에요)


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, default)))
    except ValueError:
        return default


def engine():
    global ENGINE
    if ENGINE is None:
        ENGINE = make_engine()
    return ENGINE


# ---------------------------------------------------------------- 악용 막기(서버가 강제)

BUILTIN_BLOCKED = ("송금하지않으면", "납치했", "아들을납치", "당장입금", "투표해주세요", "지지해주세요", "보이스피싱")


def _fold(text: str) -> str:
    """금지 문구 비교용으로 글을 같은 꼴로 맞춰요: NFKC(전각·호환 문자·한글 분해형), 소문자,
    보이지 않는 글자(제로폭 등 Cf)와 모든 공백 제거."""
    t = unicodedata.normalize("NFKC", text or "").casefold()
    return "".join(ch for ch in t if not ch.isspace() and unicodedata.category(ch) != "Cf")


def check_policy(text: str):
    """목소리로 만들면 안 되는 문구면 이유를, 아니면 None을 돌려줘요(정규화하고 공백을 빼고 견줘요)."""
    flat = _fold(text)
    terms = [_fold(t) for t in BUILTIN_BLOCKED]
    try:
        extra = (VOICE_DIR / "blocklist.txt").read_text(encoding="utf-8").splitlines()
        terms += [_fold(t) for t in extra if t.strip() and not t.lstrip().startswith("#")]
    except OSError:
        pass
    for t in terms:
        if t and t in flat:
            return "사기·협박·정치 광고로 쓰일 수 있는 문구라 만들지 않아요."
    return None


class RateLimit:
    """분당·하루 호출 상한(이 서버 프로세스 기준)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.calls = collections.deque()

    def allow(self, now=None) -> bool:
        now = time.time() if now is None else now
        per_min, per_day = _env_int("DIDO_MCP_PER_MIN", 10), _env_int("DIDO_MCP_PER_DAY", 300)
        with self.lock:
            while self.calls and now - self.calls[0] > 86400:
                self.calls.popleft()
            minute = sum(1 for t in self.calls if now - t <= 60)
            if minute >= per_min or len(self.calls) >= per_day:
                return False
            self.calls.append(now)
            return True


LIMIT = RateLimit()


OUT_LOCK = threading.Lock()


def _prune_out(incoming: int = 0) -> bool:
    """새 파일(incoming 바이트)을 넣어도 상한 안이 되도록 오래된 파일부터 지워요.
    규칙: (기존 + 새 파일) 용량이 MAX_OUT_BYTES 이하, 파일 수가 새 파일 포함 MAX_OUT_FILES 이하.
    새 파일 하나가 상한보다 크거나 지워도 못 맞추면 False(저장하지 않아요)."""
    if incoming > MAX_OUT_BYTES:
        return False
    try:
        files = sorted((p for p in OUT_DIR.glob("dido-*") if p.is_file()), key=lambda p: p.stat().st_mtime)
    except OSError:
        return False
    total = sum(p.stat().st_size for p in files)
    while files and (len(files) >= MAX_OUT_FILES or total + incoming > MAX_OUT_BYTES):
        old = files.pop(0)
        try:
            size = old.stat().st_size
            old.unlink()
            total -= size
        except OSError:
            pass
    return len(files) < MAX_OUT_FILES and total + incoming <= MAX_OUT_BYTES


def _audit(spoken: str, ok: bool, eng_name: str, why: str = ""):
    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        log = OUT_DIR / "audit.jsonl"
        if log.exists() and log.stat().st_size > MAX_AUDIT_BYTES:
            os.replace(log, OUT_DIR / "audit.jsonl.old")
        rec = {"at": _dt.datetime.now().isoformat(timespec="seconds"), "engine": eng_name, "ok": ok,
               "chars": len(spoken), "sha": hashlib.sha256(spoken.encode("utf-8")).hexdigest()[:12], "why": why}
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass  # 기록이 안 돼도 합성 결과는 돌려줘요


# ---------------------------------------------------------------- 만들기·재생

def _play(path: pathlib.Path) -> bool:
    """윈도우면 바로 틀어요(실행을 요청할 뿐, 실제 재생 여부는 확인하지 못해요). 다른 곳에서는 False."""
    if sys.platform != "win32":
        return False
    if path.suffix == ".wav":
        import winsound
        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
    else:
        os.startfile(str(path))  # mp3는 기본 재생 프로그램으로
    return True


BUSY = object()            # 동시 합성 상한을 넘어 새로 시작하지 않았다는 표시
_JOBS: dict = {}           # 글 해시 -> (줄기, 결과 상자). 도는 중인 합성만 들어 있어요
_JOBS_LOCK = threading.Lock()


def _synth_with_budget(eng, spoken: str):
    """합성을 별도 줄기에서 돌려 시간 안에 안 끝나면 '준비 중'으로 답해요(AI 앱의 도구 제한 시간 대비).
    줄기는 계속 돌아 결과를 저장해 두니, 같은 글로 다시 요청하면 바로 나와요.
    동시에 도는 합성은 MAX_SYNTH_JOBS개까지고, 같은 글이 이미 도는 중이면 그 줄기를 기다려요.
    상한을 넘으면 새로 시작하지 않고 BUSY를 돌려줘요."""
    budget = float(os.environ.get("DIDO_MCP_BUDGET", "45"))
    key = hashlib.sha256(spoken.encode("utf-8")).hexdigest()
    with _JOBS_LOCK:
        job = _JOBS.get(key)
        if job is None:
            if len(_JOBS) >= MAX_SYNTH_JOBS:
                return BUSY
            box = {}

            def work():
                try:
                    box["r"] = synth_or_none(eng, spoken)
                finally:
                    with _JOBS_LOCK:
                        _JOBS.pop(key, None)

            t = threading.Thread(target=work, daemon=True)
            job = _JOBS[key] = (t, box)
            t.start()
    t, box = job
    t.join(budget)
    return box.get("r")  # None이면 아직 만드는 중


def speak_core(text: str, play: bool = True, return_audio=None):
    """(결과 dict, 소리 바이트 또는 None, mime). MCP 없이도 시험할 수 있게 도구 함수와 나눠 뒀어요."""
    text = (text or "").strip()
    if not text or len(text) > MAX_CHARS:
        return {"ok": False, "error": f"글이 비었거나 {MAX_CHARS}자를 넘어요."}, None, None
    why = check_policy(text)
    if why:
        _audit(text, False, "-", "policy")
        return {"ok": False, "error": why}, None, None
    if not LIMIT.allow():
        return {"ok": False, "error": "요청이 너무 잦아요. 잠시 뒤에 다시 해 주세요."}, None, None
    spoken = normalize(text)
    why = check_policy(spoken)  # 숫자를 풀어 읽은 뒤 생기는 문구도 막아요(원문·풀어 읽은 글 둘 다 검사)
    if why:
        _audit(spoken, False, "-", "policy")
        return {"ok": False, "error": why}, None, None
    if len(spoken) > MAX_SPOKEN_CHARS:
        return {"ok": False, "spoken_text": spoken[:80] + "…",
                "error": f"숫자를 풀어 읽으면 {MAX_SPOKEN_CHARS}자를 넘어요. 글을 나눠 주세요."}, None, None
    eng = engine()
    if eng.name == "browser":
        ok, why = voice_ready()
        return {"ok": False, "spoken_text": spoken,
                "error": "아직 성우 김디도 목소리 엔진이 없어요. "
                         + ("voice 폴더는 준비됐으니 setup-voice.cmd를 실행해 주세요." if ok else f"voice 폴더: {why}")}, None, None
    res = _synth_with_budget(eng, spoken)
    if res is BUSY:
        return {"ok": False, "status": "busy", "retry": True,
                "error": "지금 다른 소리를 만드는 중이라 바빠요. 잠시 뒤 같은 글로 다시 요청해 주세요."}, None, None
    if res is None:
        return {"ok": False, "status": "preparing", "retry": True, "spoken_text": spoken,
                "error": "목소리를 처음 준비하는 중이에요(이 컴퓨터는 처음에 오래 걸려요). "
                         "1~2분 뒤 같은 글로 다시 요청해 주세요."}, None, None
    audio, warn = res
    if not audio:
        _audit(spoken, False, eng.name, "synth")
        return {"ok": False, "spoken_text": spoken, "error": warn}, None, None
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mime = getattr(eng, "mime", "") or "audio/wav"
    ext = ".mp3" if mime == "audio/mpeg" else ".wav"
    result_id = f"dido-{_dt.datetime.now():%Y%m%d-%H%M%S-%f}"
    path = OUT_DIR / (result_id + ext)
    with OUT_LOCK:  # 정리와 저장을 한 묶음으로(동시에 저장해도 상한을 안 넘게)
        if not _prune_out(len(audio)):
            _audit(spoken, False, eng.name, "storage_full")
            return {"ok": False, "spoken_text": spoken,
                    "error": "저장 공간 상한(파일 수·용량)을 넘어서 소리를 저장하지 않았어요."}, None, None
        path.write_bytes(audio)
    _audit(spoken, True, eng.name)
    # 만들기와 틀기는 따로예요: 틀기가 실패해도 만든 결과는 그대로 돌려줘요
    if REMOTE:
        play = False  # 이 서버의 스피커는 사용자 것이 아니에요
    playback, play_error, launched = "not_requested", None, False
    if play:
        try:
            launched = _play(path)
            playback = "launched" if launched else "unavailable"
        except Exception as e:  # winsound·startfile 오류(OSError 등)
            playback, play_error = "failed", f"소리를 틀지 못했어요({type(e).__name__}). 만든 소리는 저장돼 있어요."
    attach = REMOTE if return_audio is None else bool(return_audio)
    if attach and len(audio) > MAX_ATTACH_BYTES:
        attach = False
    out = {"ok": True, "spoken_text": spoken, "result_id": result_id, "audio_format": ext[1:],
           "saved_on": "소리를 만든 컴퓨터의 voice/out 폴더", "engine": eng.label,
           "play_requested": bool(play), "playback": playback, "played": launched,
           "audio_included": attach, "notice": "AI로 만든 성우 김디도 목소리예요."}
    if play_error:
        out["play_error"] = play_error
    return out, (audio if attach else None), mime


def _tool(**hints):
    """도구 등록. 읽기 전용 여부 같은 힌트(annotations)를 지원하는 mcp 버전이면 함께 달아요."""
    def deco(fn):
        try:
            from mcp.types import ToolAnnotations
            return mcp.tool(annotations=ToolAnnotations(**hints))(fn)
        except (ImportError, TypeError):
            return mcp.tool()(fn)
    return deco


@_tool(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True)
def speak_as_dido(text: str, play: bool = True, return_audio: bool | None = None):
    """글을 성우 김디도의 목소리(AI)로 읽은 소리 파일(WAV 또는 MP3)을 만들어요. 소리를 만들어 달라는 요청에만 써요.

    숫자는 사람처럼 풀어 읽어요. 이 도구는 파일을 만들고(voice/out 폴더, 오래된 것은 지워요) 글을 목소리 엔진에
    보내요(엔진이 클라우드면 그 서비스로 글이 나가요). 숫자만 풀어 달라거나 대본만 점검해 달라는 요청에는
    read_numbers_like_dido나 check_script_numbers를 써요. 준비가 안 되면 이유를 알려 줘요.

    text: 읽을 한국어 글(400자 이하, 숫자를 풀면 600자 이하).
    play: 소리를 만든 컴퓨터의 스피커로 틀지(이 컴퓨터용 stdio 연결에서만 틀어요. 틀기를 요청할 뿐 실제 재생은 확인하지 못해요).
    return_audio: 소리를 응답에 직접 실을지(비우면 주소(--http)로 연결됐을 때만 실어요). 결과의 result_id는 파일 이름이에요.
    돌려주는 것: ok, spoken_text(풀어 읽은 글), result_id, playback(not_requested·launched·unavailable·failed).
    status가 preparing이면 목소리를 처음 준비하는 중이니 잠시 뒤 같은 글로 다시 불러요.
    """
    out, audio, mime = speak_core(text, play, return_audio)
    if audio is None:
        return out
    try:
        from mcp.types import AudioContent, TextContent
    except ImportError:
        return out
    return [TextContent(type="text", text=json.dumps(out, ensure_ascii=False)),
            AudioContent(type="audio", data=base64.b64encode(audio).decode("ascii"), mimeType=mime)]


@_tool(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
def read_numbers_like_dido(text: str) -> str:
    """문장 속 숫자를 성우 김디도의 숫자 읽기 기준으로 사람이 읽는 말로 풀어서 글로 돌려줘요(예: 4719-2386 → 사칠일구, 이삼팔육).

    소리는 만들지 않고 아무것도 저장하지 않아요. 숫자를 어떻게 읽는지만 물을 때 써요. 2000자 이하.
    """
    text = text or ""
    if len(text) > MAX_NUMBERS_CHARS:
        return f"글이 {MAX_NUMBERS_CHARS}자를 넘어요. 나눠서 보내 주세요."
    return normalize(text)


@_tool(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
def check_script_numbers(script: str) -> str:
    """녹음할 대본(글)에서 숫자·기호가 든 문장을 모두 찾아 문장마다 읽는 법을 글로 알려 줘요.

    소리는 만들지 않고 아무것도 저장하지 않아요. 대본을 녹음하기 전에 점검할 때 써요. 20000자 이하.
    """
    script = script or ""
    if len(script) > MAX_SCRIPT_CHARS:
        return f"대본이 {MAX_SCRIPT_CHARS}자를 넘어요. 나눠서 보내 주세요."
    return tool_check_script({"script": script})


@_tool(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
def dido_voice_status() -> dict:
    """성우 김디도 음성 비서의 현재 상태를 알려 줘요: 쓰는 목소리 엔진, 참고 녹음 폴더 준비 여부. 소리는 만들지 않아요.

    소리를 만들기 전에 준비가 됐는지 볼 때 써요. 엔진이 browser면 대표 목소리가 아니라서 speak_as_dido가 거절해요.
    """
    ok, why = voice_ready()
    eng = engine()
    out = {"engine": eng.name, "engine_label": eng.label, "voice_ready": ok,
           "voice_detail": why if not REMOTE else ("준비됨" if ok else "참고 녹음이 준비되지 않았어요"),
           "notice": "이 도구가 만드는 소리는 AI 목소리예요."}
    if not REMOTE:
        out["voice_folder"] = str(VOICE_DIR)  # 이 컴퓨터용 연결에서만 경로를 알려요
    return out


# ---------------------------------------------------------------- 주소(--http) 접근 토큰

class TokenGate:
    """ASGI 앱 앞에서 'Authorization: Bearer 토큰'이 맞는 요청만 통과시켜요."""

    def __init__(self, app, token: str):
        self.app, self.token = app, token

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            got = dict(scope.get("headers") or []).get(b"authorization", b"").decode("latin-1")
            if not hmac.compare_digest(got.encode("utf-8"), f"Bearer {self.token}".encode("utf-8")):
                body = json.dumps({"error": "접근 토큰이 맞지 않아요"}, ensure_ascii=False).encode("utf-8")
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"application/json; charset=utf-8"),
                                        (b"content-length", str(len(body)).encode())]})
                await send({"type": "http.response.body", "body": body})
                return
        elif scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        await self.app(scope, receive, send)


def main(argv=None):
    global REMOTE
    ap = argparse.ArgumentParser()
    ap.add_argument("--http", action="store_true", help="주소(http://127.0.0.1:포트/mcp)로 열기(DIDO_MCP_TOKEN 필요)")
    ap.add_argument("--port", type=int, default=8772)
    a = ap.parse_args(argv)
    if not a.http:
        mcp.run()
        return
    token = os.environ.get("DIDO_MCP_TOKEN", "")
    if len(token) < 16:
        raise SystemExit("--http로 열려면 DIDO_MCP_TOKEN(16자 이상의 임의 글자)을 먼저 정해 주세요. 토큰 없이는 켜지지 않아요.")
    REMOTE = True
    try:
        import uvicorn
        app = mcp.streamable_http_app()
    except (ImportError, AttributeError):
        raise SystemExit("이 mcp 버전은 토큰을 거는 주소 연결을 지원하지 않아요. pip install -U mcp 를 해 주세요.")
    try:  # mcp 1.x는 설정으로 포트를 받아요
        mcp.settings.host, mcp.settings.port = "127.0.0.1", a.port
    except AttributeError:
        pass
    uvicorn.run(TokenGate(app, token), host="127.0.0.1", port=a.port)


if __name__ == "__main__":
    main()
