"""성우 김디도 목소리 서버 (그래픽카드 서버용) · Qwen3-TTS 목소리 복제.

엔비디아 그래픽카드(메모리 약 6GB 이상)가 있는 클라우드 서버에서 돌려요. 대표 PC(내장 그래픽)에서는 돌지 않아요.

    pip install -U qwen-tts soundfile torch
    DIDO_REF_AUDIO=ref/dido.wav       대표 목소리 참고 녹음(저장소에 올리지 않음)
    DIDO_REF_TEXT=참고 녹음에서 읽은 문장 그대로
    python tts_server/server.py --port 8771

비서 쪽: DIDO_TTS=http, DIDO_TTS_URL=http://서버주소:8771/tts
사용법 출처: Qwen3-TTS 공식 저장소 README(github.com/QwenLM/Qwen3-TTS)의 generate_voice_clone 예시.
기본으로 127.0.0.1에만 열려요. 다른 컴퓨터에서 부르려면 --host 0.0.0.0과 접근 토큰(DIDO_TTS_TOKEN)을 꼭 정해요.
아무나 대표 목소리를 만들 수 있으면 안 돼요.
"""
from __future__ import annotations

import argparse
import io
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL_ID = os.environ.get("DIDO_TTS_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-Base")
MAX_CHARS = 400
_model = None


def load():
    global _model
    import torch
    from qwen_tts import Qwen3TTSModel
    _model = Qwen3TTSModel.from_pretrained(MODEL_ID, device_map="cuda:0", dtype=torch.bfloat16)


def synth(text: str) -> bytes:
    import soundfile as sf
    wavs, sr = _model.generate_voice_clone(
        text=text,
        language="Korean",
        ref_audio=os.environ["DIDO_REF_AUDIO"],
        ref_text=os.environ["DIDO_REF_TEXT"],
    )
    buf = io.BytesIO()
    sf.write(buf, wavs[0], sr, format="WAV")
    return buf.getvalue()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _err(self, code, msg):
        data = json.dumps({"error": msg}, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/tts":
            return self._err(404, "없는 주소예요")
        token = os.environ.get("DIDO_TTS_TOKEN")
        if token and self.headers.get("Authorization") != f"Bearer {token}":
            return self._err(401, "접근 토큰이 맞지 않아요")
        n = int(self.headers.get("Content-Length") or 0)
        try:
            text = str(json.loads(self.rfile.read(n).decode("utf-8")).get("text", "")).strip()
        except (ValueError, UnicodeDecodeError, AttributeError):
            return self._err(400, "보낸 내용을 읽지 못했어요")
        if not text or len(text) > MAX_CHARS:
            return self._err(400, f"글이 비었거나 {MAX_CHARS}자를 넘어요")
        audio = synth(text)
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(audio)))
        self.end_headers()
        self.wfile.write(audio)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8771)
    a = ap.parse_args()
    for k in ("DIDO_REF_AUDIO", "DIDO_REF_TEXT"):
        if not os.environ.get(k):
            raise SystemExit(f"{k}를 먼저 정해 주세요(대표 목소리 참고 녹음과 그 문장).")
    if a.host != "127.0.0.1" and not os.environ.get("DIDO_TTS_TOKEN"):
        raise SystemExit("밖에서 부르게 열 때는 DIDO_TTS_TOKEN을 꼭 정해 주세요.")
    load()
    print(f"성우 김디도 목소리 서버: http://{a.host}:{a.port}/tts  (모델 {MODEL_ID})")
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
