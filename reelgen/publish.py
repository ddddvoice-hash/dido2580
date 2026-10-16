"""인스타그램 Graph API로 릴스를 올린다.

필요한 것
- 프로페셔널(비즈니스·크리에이터) 인스타그램 계정
- instagram_content_publish 권한이 있는 앱과 장기 액세스 토큰
- 환경변수 IG_USER_ID, IG_ACCESS_TOKEN

영상을 공개 URL에 올려 두었다면 video_url로, 아니면 로컬 파일을 재개형 업로드로 보낸다.
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

GRAPH = "https://graph.facebook.com"
RUPLOAD = "https://rupload.facebook.com/ig-api-upload"


@dataclass
class Credentials:
    user_id: str
    token: str
    version: str = "v23.0"

    @classmethod
    def from_env(cls) -> "Credentials":
        user_id = os.environ.get("IG_USER_ID")
        token = os.environ.get("IG_ACCESS_TOKEN")
        if not user_id or not token:
            raise RuntimeError("IG_USER_ID와 IG_ACCESS_TOKEN 환경변수를 설정하세요")
        return cls(user_id, token, os.environ.get("IG_API_VERSION", "v23.0"))


def _request(url: str, *, data: dict | None = None, body: bytes | None = None,
             headers: dict | None = None, method: str | None = None) -> dict:
    payload = body
    if data is not None:
        payload = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=payload, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"Instagram API 오류 {e.code}: {detail}") from None


def create_container(creds: Credentials, caption: str, *, video_url: str | None = None,
                     cover_url: str | None = None, share_to_feed: bool = True) -> dict:
    params = {
        "media_type": "REELS",
        "caption": caption,
        "share_to_feed": "true" if share_to_feed else "false",
        "access_token": creds.token,
    }
    if video_url:
        params["video_url"] = video_url
    else:
        params["upload_type"] = "resumable"
    if cover_url:
        params["cover_url"] = cover_url
    return _request(f"{GRAPH}/{creds.version}/{creds.user_id}/media", data=params)


def upload_file(creds: Credentials, container_id: str, video: Path) -> dict:
    blob = Path(video).read_bytes()
    return _request(
        f"{RUPLOAD}/{creds.version}/{container_id}",
        body=blob,
        method="POST",
        headers={
            "Authorization": f"OAuth {creds.token}",
            "offset": "0",
            "file_size": str(len(blob)),
        },
    )


def wait_until_ready(creds: Credentials, container_id: str, *, timeout: float = 600,
                     interval: float = 10, sleep=time.sleep) -> str:
    deadline = time.monotonic() + timeout
    while True:
        query = urllib.parse.urlencode({"fields": "status_code,status", "access_token": creds.token})
        status = _request(f"{GRAPH}/{creds.version}/{container_id}?{query}")
        code = status.get("status_code")
        if code == "FINISHED":
            return code
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"영상 처리 실패: {status}")
        if time.monotonic() > deadline:
            raise TimeoutError(f"영상 처리 대기 시간 초과 (마지막 상태 {code})")
        sleep(interval)


def publish_container(creds: Credentials, container_id: str) -> str:
    result = _request(
        f"{GRAPH}/{creds.version}/{creds.user_id}/media_publish",
        data={"creation_id": container_id, "access_token": creds.token},
    )
    return result["id"]


def publish_reel(video: Path, caption: str, *, creds: Credentials | None = None,
                 video_url: str | None = None, cover_url: str | None = None,
                 sleep=time.sleep) -> str:
    """릴스를 올리고 게시물 ID를 돌려준다."""
    creds = creds or Credentials.from_env()
    container = create_container(creds, caption, video_url=video_url, cover_url=cover_url)
    container_id = container["id"]
    if not video_url:
        upload_file(creds, container_id, video)
    wait_until_ready(creds, container_id, sleep=sleep)
    return publish_container(creds, container_id)
