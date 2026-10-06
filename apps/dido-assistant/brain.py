"""생각 층 · 성우 김디도 목소리 AI 비서.

- Claude(claude-opus-5-5)가 대답을 정하고, 필요하면 비서 도구를 불러요.
- 자격 증명이 없거나 anthropic 패키지가 없으면 '오프라인 모드'로 돌아요.
  오프라인 모드는 시각·날짜·숫자 읽기·대본 점검처럼 정해진 일만 해요.
- 대답 글은 그대로 두고, 말할 글(speak)은 말 다듬기 층(korean_numbers)을 거쳐요.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import pathlib
import re
import subprocess

from korean_numbers import normalize

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODEL = "claude-opus-5-5"
GREETING = "안녕하세요, 저는 성우 김디도의 목소리로 말하는 AI 비서예요. 무엇을 도와드릴까요?"

SYSTEM = """너는 성우 김디도의 목소리로 말하는 한국어 AI 음성 비서다.
- 너는 AI다. 사람인 척하지 않는다. 누가 물으면 "성우 김디도의 목소리로 말하는 AI 비서"라고 밝힌다.
- 대답은 소리로 읽힌다. 짧게(보통 1~3문장), 해요체로, 표·목록·기호·이모지 없이 말하듯 쓴다.
- 숫자는 아라비아 숫자 그대로 써도 된다. 읽기용으로 따로 풀어 준다.
- 모르는 것은 모른다고 한다. 날씨·뉴스처럼 확인할 수 없는 바깥 정보는 지어내지 않는다.
- 위기 신호(스스로 해치려 함 등)가 보이면 먼저 안전을 묻고, 자살예방상담전화 109, 긴급하면 112·119를 안내한다.
- 도구가 맞으면 도구를 쓴다: 지금 시각, 숫자를 사람처럼 읽는 법, 대본 숫자 점검, 녹음 검사."""

TOOLS = [
    {
        "name": "get_datetime",
        "description": "지금 한국 시각과 날짜·요일을 알려 준다. 시간이나 날짜를 물으면 쓴다.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "strict": True,
    },
    {
        "name": "read_numbers",
        "description": "문장 속 숫자를 성우 김디도의 숫자 읽기 규칙으로 사람이 읽는 말로 풀어 준다. '이거 어떻게 읽어?' 같은 질문에 쓴다.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "숫자가 든 문장"}},
            "required": ["text"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "check_script",
        "description": "녹음할 대본에서 숫자·기호가 든 문장을 모두 찾아 문장마다 읽는 법을 알려 준다. 대본 점검을 부탁받으면 쓴다.",
        "input_schema": {
            "type": "object",
            "properties": {"script": {"type": "string", "description": "대본 전체"}},
            "required": ["script"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "check_recordings",
        "description": "대표의 녹음 폴더를 녹음 검사기(반려 코드 V02 찢어짐·V05 여백·V08 가공 흔적)로 검사하고 요약한다. 폴더 이름은 녹음 기본 폴더 안의 하위 폴더 이름만 받는다(비우면 기본 폴더).",
        "input_schema": {
            "type": "object",
            "properties": {"folder": {"type": "string", "description": "녹음 기본 폴더 안의 하위 폴더 이름, 비우면 기본 폴더"}},
            "required": ["folder"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]

WEEKDAYS = "월화수목금토일"


def now_kst() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=9)))


def tool_get_datetime(_args: dict) -> str:
    t = now_kst()
    ampm = "오전" if t.hour < 12 else "오후"
    h = t.hour % 12 or 12
    return f"{t.year}년 {t.month}월 {t.day}일 {WEEKDAYS[t.weekday()]}요일 {ampm} {h}시 {t.minute}분"


def tool_read_numbers(args: dict) -> str:
    return normalize(str(args.get("text", "")))


NUM_RE = re.compile(r"\d")


def tool_check_script(args: dict) -> str:
    lines = [ln.strip() for ln in re.split(r"(?<=[.?!。])\s+|\n", str(args.get("script", ""))) if ln.strip()]
    found = [(i + 1, ln, normalize(ln)) for i, ln in enumerate(lines) if NUM_RE.search(ln)]
    if not found:
        return "숫자가 든 문장이 없어요."
    return "\n".join(f"{n}번째 문장: {src} → {read}" for n, src, read in found)


def recordings_root() -> pathlib.Path:
    default = pathlib.Path.home() / "Documents" / "voice-raw"
    return pathlib.Path(os.environ.get("DIDO_RECORDINGS", str(default))).resolve()


def tool_check_recordings(args: dict) -> str:
    root = recordings_root()
    sub = str(args.get("folder", "")).strip()
    target = (root / sub).resolve() if sub else root
    if root != target and root not in target.parents:
        return "녹음 기본 폴더 밖은 검사하지 않아요."
    if not target.is_dir():
        return f"폴더를 찾지 못했어요: {target.name or target}"
    checker = ROOT / "apps" / "voice-check" / "check.js"
    try:
        out = subprocess.run(["node", str(checker), str(target)], capture_output=True, text=True,
                             timeout=300, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return "Node.js를 찾지 못해 녹음 검사기를 실행하지 못했어요."
    except subprocess.TimeoutExpired:
        return "녹음 검사가 5분 안에 끝나지 않았어요."
    text = (out.stdout or "") + (out.stderr or "")
    tail = "\n".join(text.strip().splitlines()[-15:])
    return tail or "검사 결과가 비어 있어요."


HANDLERS = {
    "get_datetime": tool_get_datetime,
    "read_numbers": tool_read_numbers,
    "check_script": tool_check_script,
    "check_recordings": tool_check_recordings,
}


def run_tool(name: str, args: dict) -> tuple[str, bool]:
    fn = HANDLERS.get(name)
    if fn is None:
        return f"알 수 없는 도구: {name}", True
    if not isinstance(args, dict):
        return "도구 입력이 올바르지 않아요.", True
    try:
        return fn(args), False
    except Exception as e:  # 도구 하나의 실패가 대화를 멈추지 않게
        return f"도구 실행 중 문제가 생겼어요: {e}", True


# ---- 오프라인 모드 -----------------------------------------------------------

def offline_reply(text: str) -> tuple[str, list[dict]]:
    t = text.strip()
    events: list[dict] = []
    if re.search(r"(몇 ?시|시간|날짜|며칠|무슨 ?요일|오늘)", t):
        r = tool_get_datetime({})
        events.append({"tool": "get_datetime", "result": r})
        return f"지금은 {r}이에요.", events
    if t.startswith(("대본", "점검")) or "대본 점검" in t:
        script = re.sub(r"^(대본\s*점검|대본|점검)\s*[:：]?\s*", "", t)
        r = tool_check_script({"script": script})
        events.append({"tool": "check_script", "result": r})
        return r, events
    if NUM_RE.search(t):
        t = re.sub(r"\s*(은|는|을|를)?\s*(어떻게\s*)?(읽어\s*줘|읽어요|읽어|읽나요|읽지|읽니)\s*[?？]?$", "", t)
        r = tool_read_numbers({"text": t})
        events.append({"tool": "read_numbers", "result": r})
        return f"이렇게 읽으면 돼요. {r}", events
    if re.search(r"(누구|이름|사람이)", t):
        return GREETING, events
    return ("지금은 오프라인 모드라서 시각, 숫자 읽기, 대본 숫자 점검만 할 수 있어요. "
            "AI 연결을 켜면 무엇이든 물어볼 수 있어요."), events


# ---- Claude ------------------------------------------------------------------

class Brain:
    """대화 하나를 맡아요. history에는 응답 content를 통째로 넣어요(생각 블록 보존)."""

    def __init__(self):
        self.history: list = []
        self.client = None
        self.mode = "offline"
        if os.environ.get("DIDO_OFFLINE") == "1":
            return
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return
        if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                or pathlib.Path.home().joinpath(".config", "anthropic").exists()):
            return
        import anthropic
        self.client = anthropic.Anthropic()
        self.mode = "claude"

    def reply(self, text: str) -> dict:
        if self.mode != "claude":
            answer, events = offline_reply(text)
            return {"text": answer, "speak": normalize(answer), "events": events, "mode": self.mode}
        return self._claude(text)

    def _claude(self, text: str) -> dict:
        import anthropic

        start = len(self.history)
        self.history.append({"role": "user", "content": text})
        events: list[dict] = []
        try:
            for _ in range(6):  # 도구 왕복은 여섯 번까지
                resp = self.client.beta.messages.create(
                    model=MODEL,
                    max_tokens=16000,
                    betas=["server-side-fallback-2026-07-01"],
                    fallbacks="default",
                    output_config={"effort": "low"},  # 음성 대화는 빠르게
                    system=SYSTEM,
                    tools=TOOLS,
                    messages=self.history,
                )
                self.history.append({"role": "assistant", "content": resp.content})
                if resp.stop_reason == "refusal":
                    msg = "그 부탁은 도와드리기 어려워요."
                    return {"text": msg, "speak": msg, "events": events, "mode": self.mode}
                if resp.stop_reason != "tool_use":
                    break
                results = []
                for block in resp.content:
                    if block.type != "tool_use":
                        continue
                    out, err = run_tool(block.name, block.input if isinstance(block.input, dict) else json.loads(block.input))
                    events.append({"tool": block.name, "result": out})
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": out, "is_error": err})
                self.history.append({"role": "user", "content": results})
            answer = " ".join(b.text for b in resp.content if b.type == "text").strip() or "음, 다시 말씀해 주세요."
        except anthropic.AuthenticationError:
            del self.history[start:]
            self.mode = "offline"
            return self.reply(text) | {"note": "AI 연결 정보가 맞지 않아 오프라인 모드로 바꿨어요."}
        except anthropic.RateLimitError:
            del self.history[start:]
            msg = "지금 요청이 많아요. 잠시 뒤에 다시 말씀해 주세요."
            return {"text": msg, "speak": msg, "events": events, "mode": self.mode}
        except anthropic.APIConnectionError:
            del self.history[start:]
            answer, ev = offline_reply(text)
            return {"text": answer, "speak": normalize(answer), "events": ev, "mode": "offline",
                    "note": "인터넷 연결이 없어 오프라인으로 대답했어요."}
        except anthropic.APIStatusError as e:
            del self.history[start:]
            msg = f"AI 연결에 문제가 생겼어요({e.status_code}). 잠시 뒤에 다시 해 주세요."
            return {"text": msg, "speak": msg, "events": events, "mode": self.mode}
        return {"text": answer, "speak": normalize(answer), "events": events, "mode": self.mode}

    def reset(self):
        self.history = []
