"""릴스 생성기 검증. 네트워크와 API 키 없이 돈다."""

from __future__ import annotations

import json
import shutil
import subprocess
from types import SimpleNamespace

import pytest

pytest.importorskip("PIL")
pytest.importorskip("pydantic")

from reelgen import content, publish
from reelgen.cli import main
from reelgen.models import Item, ReelScript
from reelgen.pipeline import BuildSettings, load_script, produce
from reelgen.render import H, W, CardOptions, render_card, render_cta, wrap, body_font
from reelgen.samples import SAMPLES
from reelgen.topics import History, unused_seeds
from reelgen.video import Timing, make_video, resolve_order, reveal_steps


def tiny_script(n: int = 4, layout: str = "list") -> ReelScript:
    return ReelScript(
        hook="테스트용 훅", title="테스트 순위 TOP4", highlight="TOP4", layout=layout,
        items=[Item(label=f"항목{i}", note="설명", tag=f"{i + 1}위") for i in range(n)],
        cta="나는 몇 위?", caption="본문", hashtags=["테스트", "#릴스"], source_note="재미로 보는 콘텐츠예요",
    )


# ── 대본 ──

def test_validate_shape_catches_problems():
    assert tiny_script().validate_shape() == []
    bad = tiny_script(2).model_copy(update={"highlight": "없는말"})
    problems = bad.validate_shape()
    assert len(problems) == 2


def test_full_caption_has_note_and_hashtags():
    text = tiny_script().full_caption()
    assert "※ 재미로 보는 콘텐츠예요" in text
    assert text.endswith("#테스트 #릴스")


# ── 렌더 ──

@pytest.mark.parametrize("name", list(SAMPLES))
def test_samples_render_at_reel_size(name):
    script = SAMPLES[name]()
    assert script.validate_shape() == []
    img = render_card(script, None, CardOptions(handle="me"))
    assert img.size == (W, H)


def test_hidden_items_change_the_image():
    script = tiny_script()
    assert render_card(script, set()).tobytes() != render_card(script, None).tobytes()
    assert render_cta(script).size == (W, H)


def test_illustration_slot(tmp_path):
    from PIL import Image
    art = tmp_path / "art.png"
    Image.new("RGBA", (300, 600), (255, 0, 0, 255)).save(art)
    img = render_card(tiny_script(), None, CardOptions(illustration=art))
    assert img.size == (W, H)


def test_wrap_breaks_long_text():
    font = body_font(40)
    lines = wrap(font, "아주 긴 문장을 여러 줄로 나눠야 하는 상황입니다 " * 3, 400)
    assert len(lines) > 1


# ── 영상 ──

def test_reveal_orders():
    assert reveal_steps(3, "countdown") == [{2}, {1, 2}, {0, 1, 2}]
    assert reveal_steps(3, "forward") == [{0}, {0, 1}, {0, 1, 2}]
    assert resolve_order(tiny_script(layout="grid"), "auto") == "forward"
    assert resolve_order(tiny_script(), "auto") == "countdown"


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg 없음")
def test_video_duration(tmp_path):
    timing = Timing(hook=0.5, reveal_total=1.0, reveal_min=0.25, reveal_max=0.25, hold=0.5, cta=0.5)
    video = make_video(tiny_script(), tmp_path, timing=timing)
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(video)],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "1080,1920" in out
    assert not (tmp_path / "frames").exists()


# ── 파이프라인과 기록 ──

def test_produce_and_rerender(tmp_path):
    history = History(tmp_path / "history.json")
    folder = produce(tiny_script(), BuildSettings(out_root=tmp_path, video=False), "테스트 주제", history)
    assert {p.name for p in folder.iterdir()} == {"script.json", "caption.txt", "cover.png"}
    script, topic = load_script(folder / "script.json")
    assert topic == "테스트 주제" and script.title == "테스트 순위 TOP4"
    assert History(tmp_path / "history.json").has("테스트  주제")


def test_unused_seeds_skip_history(tmp_path):
    history = History(tmp_path / "h.json")
    before = unused_seeds(history)
    history.add(before[0], "t", "f")
    assert before[0] not in unused_seeds(history)
    assert unused_seeds(history, "영어") and all("영어" in t for t in unused_seeds(history, "영어"))


def test_cli_demo_without_video(tmp_path, capsys):
    assert main(["demo", "--sample", "top_traits", "--no-video", "--out", str(tmp_path)]) == 0
    assert "완성" in capsys.readouterr().out
    folder = next(tmp_path.iterdir())
    assert main(["render", str(folder / "script.json"), "--no-video", "--out", str(tmp_path)]) == 0


# ── Claude 호출 (가짜 클라이언트) ──

class FakeClient:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self._parse))

    def _parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(stop_reason="end_turn", parsed_output=self.outputs.pop(0))


def test_write_script_retries_bad_shape():
    bad = tiny_script().model_copy(update={"highlight": "없음"})
    client = FakeClient([bad, tiny_script()])
    script = content.write_script("주제", english=True, client=client)
    assert script.highlight == "TOP4"
    assert len(client.calls) == 2
    assert "이전 시도의 문제" in client.calls[1]["messages"][0]["content"]
    assert client.calls[0]["fallbacks"] == "default"


def test_refusal_raises():
    client = FakeClient([])
    client.beta.messages.parse = lambda **kw: SimpleNamespace(stop_reason="refusal", parsed_output=None)
    with pytest.raises(RuntimeError):
        content.write_script("주제", client=client)


# ── 업로드 (가짜 HTTP) ──

def test_publish_resumable_flow(tmp_path, monkeypatch):
    video = tmp_path / "reel.mp4"
    video.write_bytes(b"0123456789")
    calls = []
    statuses = iter(["IN_PROGRESS", "FINISHED"])

    def fake_request(url, *, data=None, body=None, headers=None, method=None):
        calls.append((url, data, headers))
        if url.endswith("/media"):
            return {"id": "C1"}
        if "rupload" in url:
            return {"success": True}
        if "status_code" in url:
            return {"status_code": next(statuses)}
        if url.endswith("/media_publish"):
            return {"id": "M1"}
        raise AssertionError(url)

    monkeypatch.setattr(publish, "_request", fake_request)
    creds = publish.Credentials("U1", "TOKEN")
    assert publish.publish_reel(video, "캡션", creds=creds, sleep=lambda s: None) == "M1"
    assert calls[0][1]["upload_type"] == "resumable"
    assert calls[1][2]["file_size"] == "10"
    assert calls[-1][1]["creation_id"] == "C1"


def test_publish_with_url_skips_upload(monkeypatch):
    seen = []

    def fake_request(url, *, data=None, **_):
        seen.append(url)
        if url.endswith("/media"):
            assert data["video_url"] == "https://x/v.mp4"
            return {"id": "C2"}
        if "status_code" in url:
            return {"status_code": "FINISHED"}
        return {"id": "M2"}

    monkeypatch.setattr(publish, "_request", fake_request)
    creds = publish.Credentials("U1", "T")
    assert publish.publish_reel(None, "c", creds=creds, video_url="https://x/v.mp4") == "M2"
    assert not any("rupload" in u for u in seen)
