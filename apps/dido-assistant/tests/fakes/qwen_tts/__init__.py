"""시험용 가짜 qwen_tts: 진짜 모델 없이 '음성만 있으면 바로 구동' 경로를 끝까지 확인해요."""
import os


class _Model:
    def generate_voice_clone(self, text, language, ref_audio, ref_text):
        assert language == "Korean" and os.path.isfile(ref_audio) and ref_text
        log = os.environ.get("FAKE_TTS_LOG")
        if log:
            with open(log, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        return [b"fake-pcm:" + text.encode("utf-8")], 24000


class Qwen3TTSModel:
    @classmethod
    def from_pretrained(cls, model_id, **kw):
        return _Model()
