"""목소리 층 · 성우 김디도 목소리 AI 비서. 엔진을 바꿔 끼울 수 있어요.

DIDO_TTS 환경 변수로 골라요.
- browser (기본): 소리는 화면(브라우저)의 한국어 합성음으로 내요. 설치·서버 없이 바로 돼요.
- http: 그래픽카드 서버(tts_server/server.py, Qwen3-TTS 목소리 복제)에 글을 보내 WAV를 받아요.
  DIDO_TTS_URL=http://서버주소:8771/tts
어느 엔진이든 받는 글은 말 다듬기 층을 이미 거친 글이에요.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class BrowserEngine:
    name = "browser"
    label = "브라우저 기본 목소리(대표 목소리 아님)"

    def synth(self, text: str):
        return None  # 화면이 직접 읽어요


class HttpEngine:
    name = "http"
    label = "성우 김디도 목소리(복제 서버)"

    def __init__(self, url: str, timeout: float = 60.0):
        self.url = url
        self.timeout = timeout

    def synth(self, text: str) -> bytes:
        body = json.dumps({"text": text}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        token = os.environ.get("DIDO_TTS_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(self.url, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            if r.headers.get("Content-Type", "").split(";")[0] != "audio/wav":
                raise RuntimeError("목소리 서버가 WAV가 아닌 것을 보냈어요")
            return r.read()


def make_engine():
    kind = os.environ.get("DIDO_TTS", "browser")
    if kind == "http":
        url = os.environ.get("DIDO_TTS_URL", "")
        if url:
            return HttpEngine(url)
    return BrowserEngine()


def synth_or_none(engine, text: str):
    """소리 바이트 또는 None(화면이 읽음)과 오류 메시지."""
    try:
        return engine.synth(text), None
    except (urllib.error.URLError, OSError, RuntimeError) as e:
        return None, f"목소리 서버에 닿지 못해 기본 목소리로 읽어요({e})"
