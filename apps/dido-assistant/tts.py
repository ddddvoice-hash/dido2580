"""목소리 층 · 성우 김디도 목소리 AI 비서. 엔진을 바꿔 끼울 수 있어요.

DIDO_TTS 환경 변수로 고르고, 정하지 않으면(auto) 아래 순서로 **쓸 수 있는 첫 번째**를 골라요.
쓸 수 없는 후보(주소가 안전하지 않음, 설치 안 됨 등)는 건너뛰고 다음 후보로 가요.
1. eleven: ELEVENLABS_API_KEY와 DIDO_ELEVEN_VOICE_ID가 있으면 클라우드 맞춤 목소리(그래픽카드 불필요, 빠름).
           주소는 공식 https://api.elevenlabs.io 로 고정이에요(시험용 127.0.0.1 주소만 예외).
2. http  : DIDO_TTS_URL이 있으면 그래픽카드 서버(tts_server/server.py)에 글을 보내 WAV를 받아요.
3. local : voice/ref.wav + voice/ref.txt(대표 목소리 참고 녹음과 그 문장)가 있고 qwen-tts가 설치돼 있으면
           이 컴퓨터에서 바로 대표 목소리로 만들어요(그래픽카드가 없으면 CPU로, 느려요).
4. browser: 모두 없으면 화면(브라우저)의 기본 한국어 합성음으로 읽어요.
DIDO_TTS=eleven|http|local처럼 직접 고르면 그 엔진만 써 보고, 안 되면 이유를 label에 적어 browser로 가요.
→ "음성만 있으면 바로 구동": voice 폴더에 참고 녹음 두 파일만 넣고 setup-voice.cmd를 한 번 실행하면 돼요.
어느 엔진이든 받는 글은 말 다듬기 층을 이미 거친 글이에요.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import threading
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
    """이 컴퓨터에서 Qwen3-TTS로 대표 목소리를 만들어요. 같은 글은 voice/cache에 저장해 두고 바로 꺼내요.
    저장 열쇠에는 참고 녹음 내용(해시)·참고 문장·모델 이름·언어가 함께 들어가서, 이 중 하나를 바꾸면 새로 만들어요."""
    mime = "audio/wav"
    name = "local"
    label = "성우 김디도 목소리(이 컴퓨터에서 복제)"
    CACHE_VERSION = "v2"

    def __init__(self, voice_dir=None):
        self.dir = pathlib.Path(voice_dir) if voice_dir else VOICE_DIR
        self.ref_audio = str(self.dir / "ref.wav")
        self.cache = self.dir / "cache"
        self._model, self._model_id = None, None
        self._lock = threading.Lock()  # 모델 불러오기·만들기는 한 번에 하나만

    @property
    def ref_text(self) -> str:
        return (self.dir / "ref.txt").read_text(encoding="utf-8").strip()  # 파일을 고치면 다음 요청부터 반영

    @staticmethod
    def model_id() -> str:
        return os.environ.get("DIDO_TTS_MODEL", DEFAULT_MODEL)

    def _load(self):
        mid = self.model_id()
        if self._model is None or self._model_id != mid:
            import torch
            from qwen_tts import Qwen3TTSModel
            gpu = torch.cuda.is_available()
            self._model = Qwen3TTSModel.from_pretrained(
                mid,
                device_map="cuda:0" if gpu else "cpu",
                dtype=torch.bfloat16 if gpu else torch.float32,
            )
            self._model_id = mid
        return self._model

    def warm(self):
        """모델을 미리 내려받아 불러 둬요(첫 대화가 오래 걸리지 않게). setup-voice.cmd가 불러요."""
        with self._lock:
            self._load()

    def cache_key(self, text: str) -> str:
        ref_hash = hashlib.sha256(pathlib.Path(self.ref_audio).read_bytes()).hexdigest()
        payload = json.dumps([self.CACHE_VERSION, self.model_id(), "Korean", ref_hash, self.ref_text, text],
                             ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]

    def synth(self, text: str) -> bytes:
        hit = self.cache / f"{self.cache_key(text)}.wav"
        if hit.is_file():
            return hit.read_bytes()
        import io

        import soundfile as sf
        with self._lock:
            if hit.is_file():  # 기다리는 사이 다른 요청이 만들어 뒀을 수 있어요
                return hit.read_bytes()
            wavs, sr = self._load().generate_voice_clone(
                text=text, language="Korean", ref_audio=self.ref_audio, ref_text=self.ref_text)
            buf = io.BytesIO()
            sf.write(buf, wavs[0], sr, format="WAV")
            data = buf.getvalue()
            self.cache.mkdir(parents=True, exist_ok=True)
            tmp = hit.with_name(hit.name + f".{os.getpid()}.tmp")
            tmp.write_bytes(data)
            os.replace(tmp, hit)  # 반쯤 쓴 파일이 남지 않게
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
    FORMAT = "mp3_44100_128"  # API 기본값을 그대로 적어 두어요(audio/mpeg)

    def __init__(self, key: str, voice_id: str, timeout: float = 60.0):
        self.key, self.voice_id, self.timeout = key, voice_id, timeout
        self.model = os.environ.get("DIDO_ELEVEN_MODEL", "eleven_multilingual_v2")
        self.api = eleven_api()

    def synth(self, text: str) -> bytes:
        body = json.dumps({"text": text, "model_id": self.model}).encode("utf-8")
        url = self.api + urllib.parse.quote(self.voice_id, safe="") + "?output_format=" + self.FORMAT
        req = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json", "Accept": "audio/mpeg",
                                              "xi-api-key": self.key})
        with _NO_REDIRECT.open(req, timeout=self.timeout) as r:
            if not r.headers.get("Content-Type", "").startswith("audio/"):
                raise RuntimeError("목소리 서비스가 소리가 아닌 것을 보냈어요")
            return r.read()


def eleven_api() -> str:
    """클라우드 목소리 주소. 키가 가는 곳이라 공식 주소로 고정하고, 시험용 이 컴퓨터 주소만 예외로 둬요."""
    env = os.environ.get("DIDO_ELEVEN_API", "").strip()
    if not env or env == ElevenEngine.API:
        return ElevenEngine.API
    u = urllib.parse.urlsplit(env)
    if u.scheme == "http" and u.hostname in LOCAL_HOSTS and not (u.username or u.password):
        return env  # 시험용: 이 컴퓨터 밖으로는 키가 나가지 않아요
    raise ValueError("클라우드 목소리 주소는 공식 주소만 쓸 수 있어요")


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


def _build(kind: str):
    """kind 엔진을 만들어요. 설정이 없으면 None, 설정은 있는데 안전하지 않으면 ValueError."""
    if kind == "eleven":
        key, vid = os.environ.get("ELEVENLABS_API_KEY", ""), os.environ.get("DIDO_ELEVEN_VOICE_ID", "")
        return ElevenEngine(key, vid) if key and vid else None
    if kind == "http":
        url = os.environ.get("DIDO_TTS_URL", "")
        return HttpEngine(url) if url else None  # 주소 검사는 HttpEngine 안에서 해요
    if kind == "local":
        return LocalCloneEngine() if local_available() else None
    return None


_WHY = {"eleven": "클라우드 목소리 주소가 올바르지 않아", "http": "목소리 서버 주소가 안전하지 않아"}
_MISSING = {"eleven": "클라우드 키·목소리 ID가 없어", "http": "목소리 서버 주소가 없어",
            "local": "참고 녹음이나 qwen-tts가 준비되지 않아"}


def make_engine():
    kind = os.environ.get("DIDO_TTS", "auto").strip().lower() or "auto"
    order = ["eleven", "http", "local"] if kind == "auto" else [kind]
    notes = []
    for k in order:
        try:
            e = _build(k)
        except ValueError:
            notes.append(_WHY.get(k, "설정이 올바르지 않아"))
            continue
        if e is not None:
            return e
        if kind != "auto" and k in _MISSING:
            notes.append(_MISSING[k])
    b = BrowserEngine()
    if notes:
        b.label = f"브라우저 기본 목소리({', '.join(notes)} 쓰지 않았어요)"
    return b


def synth_or_none(engine, text: str):
    """소리 바이트 또는 None(화면이 읽음)과 오류 메시지."""
    try:
        return engine.synth(text), None
    except (urllib.error.URLError, OSError, RuntimeError) as e:
        return None, f"목소리 서버에 닿지 못해 기본 목소리로 읽어요({type(e).__name__})"
    except Exception as e:  # 이 컴퓨터 목소리 모델 오류도 대화를 멈추지 않게(비밀값이 섞일 수 있는 원문은 빼요)
        return None, f"대표 목소리를 만들지 못해 기본 목소리로 읽어요({type(e).__name__})"


def main(argv=None) -> int:
    """python tts.py --warm : 이 컴퓨터 목소리 모델을 미리 내려받아 불러 둬요(setup-voice.cmd 3단계)."""
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--warm", action="store_true")
    ap.parse_args(argv)
    e = make_engine()
    if not isinstance(e, LocalCloneEngine):
        print(f"미리 준비할 것이 없어요(목소리: {e.label}).")
        return 0
    try:
        e.warm()
    except Exception as ex:  # 원문은 비밀값이 섞일 수 있어 종류만
        print(f"[준비 실패] 목소리 모델을 불러오지 못했어요({type(ex).__name__}).", file=sys.stderr)
        return 1
    print("목소리 모델 준비 끝.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
