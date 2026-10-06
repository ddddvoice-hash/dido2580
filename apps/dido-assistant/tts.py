"""목소리 층 · 성우 김디도 목소리 AI 비서. 엔진을 바꿔 끼울 수 있어요.

DIDO_TTS 환경 변수로 고르고, 정하지 않으면(auto) 이 순서로 스스로 골라요.
0. eleven: ELEVENLABS_API_KEY와 DIDO_ELEVEN_VOICE_ID가 있으면 클라우드 맞춤 목소리(그래픽카드 불필요, 빠름).
1. http  : DIDO_TTS_URL이 있으면 그래픽카드 서버(tts_server/server.py)에 글을 보내 WAV를 받아요.
2. local : voice/ref.wav + voice/ref.txt(대표 목소리 참고 녹음과 그 문장)가 있고 qwen-tts가 설치돼 있으면
           이 컴퓨터에서 바로 대표 목소리로 만들어요(그래픽카드가 없으면 CPU로, 느려요).
3. browser: 둘 다 없으면 화면(브라우저)의 기본 한국어 합성음으로 읽어요.
→ "음성만 있으면 바로 구동": voice 폴더에 참고 녹음 두 파일만 넣고 setup-voice.cmd를 한 번 실행하면 돼요.
어느 엔진이든 받는 글은 말 다듬기 층을 이미 거친 글이에요.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request

LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """목소리 서버가 다른 곳으로 보내도 따라가지 않아요(접근 토큰이 다른 주소로 새지 않게)."""

    def redirect_request(self, *a, **kw):
        return None


def check_url(url: str) -> str:
    """목소리 서버 주소 검사: 이 컴퓨터는 http도 되고, 밖은 https만. 맞지 않으면 ValueError."""
    u = urllib.parse.urlsplit(url)
    if u.scheme not in ("http", "https") or not u.hostname or u.username or u.password:
        raise ValueError("목소리 서버 주소가 올바르지 않아요")
    if u.scheme == "http" and u.hostname not in LOCAL_HOSTS:
        raise ValueError("이 컴퓨터 밖의 목소리 서버는 https 주소만 쓸 수 있어요")
    return url


class BrowserEngine:
    mime = None
    name = "browser"
    label = "브라우저 기본 목소리(대표 목소리 아님)"

    def synth(self, text: str):
        return None  # 화면이 직접 읽어요


_NO_REDIRECT = urllib.request.build_opener(_NoRedirect)  # 클라우드 목소리용


class HttpEngine:
    mime = "audio/wav"
    name = "http"
    label = "성우 김디도 목소리(복제 서버)"

    def __init__(self, url: str, timeout: float = 60.0):
        self.url = check_url(url)
        self.timeout = timeout

    def synth(self, text: str) -> bytes:
        body = json.dumps({"text": text}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        token = os.environ.get("DIDO_TTS_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(self.url, data=body, headers=headers)
        handlers = [_NoRedirect()]
        if urllib.parse.urlsplit(self.url).hostname in LOCAL_HOSTS:
            handlers.append(urllib.request.ProxyHandler({}))  # 이 컴퓨터 안 주소는 프록시를 거치지 않아요
        with urllib.request.build_opener(*handlers).open(req, timeout=self.timeout) as r:
            if r.headers.get("Content-Type", "").split(";")[0] != "audio/wav":
                raise RuntimeError("목소리 서버가 WAV가 아닌 것을 보냈어요")
            return r.read()


VOICE_DIR = pathlib.Path(os.environ.get("DIDO_VOICE_DIR", str(pathlib.Path(__file__).resolve().parent / "voice")))
DEFAULT_MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"  # Qwen3-TTS 공식 README의 목소리 복제 예시 모델


def voice_ready() -> tuple[bool, str]:
    """참고 녹음 두 파일이 제대로 있는지."""
    wav, txt = VOICE_DIR / "ref.wav", VOICE_DIR / "ref.txt"
    if not wav.is_file():
        return False, f"{wav} 가 없어요"
    if not txt.is_file() or not txt.read_text(encoding="utf-8").strip():
        return False, f"{txt} 가 없거나 비었어요(참고 녹음에서 읽은 문장 그대로)"
    return True, "준비됨"


class LocalCloneEngine:
    """이 컴퓨터에서 Qwen3-TTS로 대표 목소리를 만들어요. 같은 글은 voice/cache에 저장해 두고 바로 꺼내요."""
    mime = "audio/wav"
    name = "local"
    label = "성우 김디도 목소리(이 컴퓨터에서 복제)"

    def __init__(self):
        self.ref_audio = str(VOICE_DIR / "ref.wav")
        self.ref_text = (VOICE_DIR / "ref.txt").read_text(encoding="utf-8").strip()
        self.cache = VOICE_DIR / "cache"
        self._model = None

    def _load(self):
        if self._model is None:
            import torch
            from qwen_tts import Qwen3TTSModel
            gpu = torch.cuda.is_available()
            self._model = Qwen3TTSModel.from_pretrained(
                os.environ.get("DIDO_TTS_MODEL", DEFAULT_MODEL),
                device_map="cuda:0" if gpu else "cpu",
                dtype=torch.bfloat16 if gpu else torch.float32,
            )
        return self._model

    def synth(self, text: str) -> bytes:
        key = hashlib.sha256((self.ref_text + "\n" + text).encode("utf-8")).hexdigest()[:24]
        hit = self.cache / f"{key}.wav"
        if hit.is_file():
            return hit.read_bytes()
        import io

        import soundfile as sf
        wavs, sr = self._load().generate_voice_clone(
            text=text, language="Korean", ref_audio=self.ref_audio, ref_text=self.ref_text)
        buf = io.BytesIO()
        sf.write(buf, wavs[0], sr, format="WAV")
        data = buf.getvalue()
        self.cache.mkdir(parents=True, exist_ok=True)
        hit.write_bytes(data)
        return data


class ElevenEngine:
    """클라우드 맞춤 목소리(그래픽카드 필요 없음). GPT 아스트라 Q14 조사의 1순위 방식.
    대표가 서비스 웹사이트에서 voice 폴더의 녹음으로 목소리 복제를 만든 뒤, 그 목소리 ID와 API 키를
    본인 PC 환경 변수에 넣어요: ELEVENLABS_API_KEY, DIDO_ELEVEN_VOICE_ID (저장소에는 절대 넣지 않음).
    모델은 DIDO_ELEVEN_MODEL로 바꿔요(기본은 API 문서의 기본 다국어 모델). 숫자는 말 다듬기 층이 먼저 풀어요."""
    mime = "audio/mpeg"
    name = "eleven"
    label = "성우 김디도 목소리(클라우드 복제)"
    API = "https://api.elevenlabs.io/v1/text-to-speech/"

    def __init__(self, key: str, voice_id: str, timeout: float = 60.0):
        self.key, self.voice_id, self.timeout = key, voice_id, timeout
        self.model = os.environ.get("DIDO_ELEVEN_MODEL", "eleven_multilingual_v2")
        self.api = os.environ.get("DIDO_ELEVEN_API", self.API)  # 시험할 때만 바꿔요

    def synth(self, text: str) -> bytes:
        body = json.dumps({"text": text, "model_id": self.model}).encode("utf-8")
        req = urllib.request.Request(self.api + urllib.parse.quote(self.voice_id, safe=""), data=body,
                                     headers={"Content-Type": "application/json", "Accept": "audio/mpeg",
                                              "xi-api-key": self.key})
        with _NO_REDIRECT.open(req, timeout=self.timeout) as r:
            if not r.headers.get("Content-Type", "").startswith("audio/"):
                raise RuntimeError("목소리 서비스가 소리가 아닌 것을 보냈어요")
            return r.read()


def local_available() -> bool:
    ok, _ = voice_ready()
    if not ok:
        return False
    try:
        import qwen_tts  # noqa: F401
        import soundfile  # noqa: F401
    except ImportError:
        return False
    return True


def make_engine():
    kind = os.environ.get("DIDO_TTS", "auto")
    url = os.environ.get("DIDO_TTS_URL", "")
    if kind in ("http", "auto") and url:
        try:
            return HttpEngine(url)  # 주소 검사는 HttpEngine 안에서 해요
        except ValueError:
            e = BrowserEngine()
            e.label = "브라우저 기본 목소리(목소리 서버 주소가 안전하지 않아 쓰지 않았어요)"
            return e
    key, vid = os.environ.get("ELEVENLABS_API_KEY", ""), os.environ.get("DIDO_ELEVEN_VOICE_ID", "")
    if kind in ("eleven", "auto") and key and vid:
        return ElevenEngine(key, vid)
    if kind in ("local", "auto") and local_available():
        return LocalCloneEngine()
    return BrowserEngine()


def synth_or_none(engine, text: str):
    """소리 바이트 또는 None(화면이 읽음)과 오류 메시지."""
    try:
        return engine.synth(text), None
    except (urllib.error.URLError, OSError, RuntimeError) as e:
        return None, f"목소리 서버에 닿지 못해 기본 목소리로 읽어요({type(e).__name__})"
    except Exception as e:  # 이 컴퓨터 목소리 모델 오류도 대화를 멈추지 않게(비밀값이 섞일 수 있는 원문은 빼요)
        return None, f"대표 목소리를 만들지 못해 기본 목소리로 읽어요({type(e).__name__})"
