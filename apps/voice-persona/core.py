"""문구 보존, 낭독 설계와 WAV 검사를 담당하는 표준 라이브러리 모듈.

자유로운 AI 재작성이나 감정 인식을 수행하지 않는다. 용어 치환은 아래의
명시적 허용 목록만 사용하며, 검증은 그 편집 기록을 재실행하는 범위다.
"""
from __future__ import annotations
import array
import base64
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import re
import operator
import statistics
import struct
import sys

MAX_TEXT = 5000
MAX_BACKUP = 48 * 1024 * 1024
SCENARIOS = {"error": "오류 안내", "progress": "진행 안내", "complete": "완료 안내"}
MODES = {"original": "원문 그대로", "terms": "등록된 표현만 쉽게 바꾸기"}

@dataclass(frozen=True)
class Persona:
    id: str
    label: str
    title: str
    rate: float
    pause_ms: int
    direction: str
    breath: str

PERSONAS = {
    "senior": Persona("senior", "기기 사용이 익숙하지 않은 사용자", "천천히 또렷한 안내", .85, 850,
        "존중하는 평소 말투를 유지하세요. 한 문장에 한 가지 정보를 담고, 다음 행동 앞에서 충분히 쉬세요.",
        "필요한 만큼 자연스럽게 숨을 쉬세요. 한숨이나 유아적인 말투를 기본값으로 넣지 않습니다."),
    "visual": Persona("visual", "화면을 보지 않고 듣는 사용자", "명확한 음성 안내", .95, 650,
        "원문에 적힌 기능·버튼 이름과 다음 행동을 또렷하게 읽으세요. 화면 위치를 추측해 덧붙이지 마세요.",
        "문장 사이의 자연스러운 호흡을 사용하세요. 중요한 이름 앞의 쉼을 비교해 보세요."),
    "cognitive": Persona("cognitive", "짧은 단계별 설명이 필요한 사용자", "한 단계씩 차분한 안내", .8, 1000,
        "내용을 생략하지 않고 한 문장씩 읽으세요. 새 행동을 추가하지 말고, 이해할 시간을 주세요.",
        "짧은 문장 사이에 쉬세요. 실제 청자의 선호를 듣고 속도를 조정하세요."),
}

# 승인된 정확한 표현만 바꾼다. 숫자, 연락처, 위치, 시간, 금지 행동을 추가하는 규칙은 없다.
RULES = {
    "upload_failed": ("파일 업로드가 실패했습니다.", "파일을 올리지 못했습니다."),
    "upload_term": ("파일 업로드", "파일 올리기"),
    "fingerprint_term": ("지문 생체 인증", "지문 확인"),
    "error_term": ("에러 코드", "오류 코드"),
    "three_attempts": ("3회 연속", "3번 연속"),
    "contact_center": ("고객센터로 문의하십시오.", "고객센터에 문의해 주세요."),
    "contact_polite": ("문의하십시오.", "문의해 주세요."),
    "retry_polite": ("재시도하십시오.", "다시 시도해 주세요."),
    "input_polite": ("입력하십시오.", "입력해 주세요."),
    "check_polite": ("확인하십시오.", "확인해 주세요."),
    "press_polite": ("누르십시오.", "눌러 주세요."),
    "error_polite": ("오류가 발생하였습니다.", "오류가 발생했습니다."),
}
LABEL_LINE = r"[^\n]*(?:버튼|메뉴|탭|라벨|화면명|링크)[^\n]*"
PROTECTED = r'''```[\s\S]*?```|`[^`\n]*`|"[^"\n]*"|'[^'\n]*'|“[^”\n]*”|‘[^’\n]*’|https?://[^\s]+'''
TERMS = "|".join(re.escape(before) for before, _ in sorted(RULES.values(), key=lambda x: -len(x[0])))
PATTERN = re.compile(f"(?P<protected>{LABEL_LINE}|{PROTECTED})|(?P<term>{TERMS})")
LOOKUP = {before: (rule_id, after) for rule_id, (before, after) in RULES.items()}

@dataclass(frozen=True)
class Edit:
    start: int
    end: int
    before: str
    after: str
    rule_id: str

@dataclass(frozen=True)
class Result:
    inputs: dict
    fingerprint: str
    source: str
    text: str
    edits: tuple[Edit, ...]
    created_at: str

    def to_dict(self):
        return asdict(self)


def validate_inputs(inputs: dict) -> dict:
    required = {"source", "persona", "scenario", "mode", "rate", "pause_ms"}
    if not isinstance(inputs, dict) or set(inputs) != required:
        raise ValueError("작업 입력 형식이 맞지 않습니다.")
    source = inputs["source"]
    if not isinstance(source, str) or not source.strip():
        raise ValueError("안내할 원문을 입력해 주세요.")
    if len(source) > MAX_TEXT:
        raise ValueError(f"원문은 {MAX_TEXT:,}자 이하로 입력해 주세요.")
    if any(type(inputs[k]) is not str for k in ("persona", "scenario", "mode")) or inputs["persona"] not in PERSONAS or inputs["scenario"] not in SCENARIOS or inputs["mode"] not in MODES:
        raise ValueError("사용자·상황·표현 방식을 확인해 주세요.")
    if type(inputs["rate"]) not in (float, int) or not math.isfinite(inputs["rate"]) or not .6 <= inputs["rate"] <= 1.3:
        raise ValueError("낭독 속도 설계값은 0.60~1.30 사이여야 합니다.")
    if type(inputs["pause_ms"]) is not int or not 250 <= inputs["pause_ms"] <= 1800:
        raise ValueError("문장 사이 쉼 설계값은 250~1800ms여야 합니다.")
    return dict(inputs)


def fingerprint(inputs: dict) -> str:
    return hashlib.sha256(json.dumps(inputs, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def simplify(source: str) -> tuple[str, tuple[Edit, ...]]:
    edits = []
    def replace(match):
        if match.group("protected") is not None:
            return match.group(0)
        before = match.group(0)
        rule_id, after = LOOKUP[before]
        edits.append(Edit(match.start(), match.end(), before, after, rule_id))
        return after
    return PATTERN.sub(replace, source), tuple(edits)


def verify_edits(source: str, text: str, edits: tuple[Edit, ...]) -> None:
    """허용된 정확한 편집의 재실행. 일반적 의미 동등성 판정기가 아니다."""
    chunks, position = [], 0
    for edit in edits:
        if edit.rule_id not in RULES or RULES[edit.rule_id] != (edit.before, edit.after):
            raise ValueError("등록되지 않은 변경을 발견했습니다.")
        if not (position <= edit.start < edit.end <= len(source)) or source[edit.start:edit.end] != edit.before:
            raise ValueError("변경 위치가 원문과 일치하지 않습니다.")
        chunks.extend([source[position:edit.start], edit.after])
        position = edit.end
    chunks.append(source[position:])
    if "".join(chunks) != text:
        raise ValueError("결과에 편집 기록 밖의 정보가 있습니다.")
    if re.findall(r"\d+(?:[.:/-]\d+)*", source) != re.findall(r"\d+(?:[.:/-]\d+)*", text):
        raise ValueError("숫자·시간·연락처의 변경을 발견했습니다.")


def build_result(inputs: dict, created_at: str | None = None) -> Result:
    inputs = validate_inputs(inputs)
    source = inputs["source"]
    text, edits = simplify(source) if inputs["mode"] == "terms" else (source, ())
    verify_edits(source, text, edits)
    return Result(inputs, fingerprint(inputs), source, text, edits,
                  created_at or datetime.now(timezone.utc).isoformat())


def result_is_current(result: Result | None, inputs: dict) -> bool:
    return result is not None and result.fingerprint == fingerprint(inputs)


# 파일 크기 상한 근거: 48kHz·32bit·스테레오로 10분이면 48,000 × 8바이트 × 600초 = 230,400,000바이트.
# 헤더·부가 청크 여유를 더해 231,000,000바이트(약 231MB)로 둔다.
MAX_AUDIO = 231_000_000
MAX_SECONDS = 600
PCM_GUID_TAIL = bytes.fromhex("0000" "0000" "1000" "8000" "00aa00389b71")
FRAME_MS, MIN_PAUSE_MS, MIN_SPEECH_MS = 20, 250, 80
FORMAT_HELP = "8~192kHz, 16·24·32bit PCM 또는 32bit float, 모노·스테레오 WAV를 사용해 주세요."


def _parse_wav(data: bytes) -> dict:
    """RIFF 청크를 직접 읽는다(fmt·data 순서 무관, 홀수 크기 청크 패딩 처리). 기준은 apps/voice-check/check.js."""
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("WAV 파일이 아닙니다. 지원하는 WAV를 선택하거나 마이크로 새로 녹음해 주세요.")
    pos, fmt, chunk = 12, None, None
    while pos + 8 <= len(data) and (fmt is None or chunk is None):
        tag, size = data[pos:pos + 4], int.from_bytes(data[pos + 4:pos + 8], "little")
        body = pos + 8
        if tag == b"fmt ":
            if size < 16 or body + size > len(data):
                raise ValueError("WAV 헤더가 잘렸거나 올바르지 않습니다. 원본 파일을 다시 선택해 주세요.")
            code, channels, rate, _, align, bits = struct.unpack_from("<HHIIHH", data, body)
            if code == 0xFFFE:
                if size < 40 or int.from_bytes(data[body + 16:body + 18], "little") < 22 or data[body + 26:body + 40] != PCM_GUID_TAIL:
                    raise ValueError("지원하지 않는 확장 WAV 형식입니다. " + FORMAT_HELP)
                code = int.from_bytes(data[body + 24:body + 26], "little")
            fmt = (code, channels, rate, align, bits)
        elif tag == b"data" and chunk is None:
            if size > len(data) - body:
                raise ValueError("WAV 데이터가 잘렸습니다. 원본 파일을 다시 선택해 주세요.")
            chunk = (body, size)
        pos = body + size + (size & 1)
    if fmt is None or chunk is None:
        raise ValueError("WAV의 fmt 또는 data 구간을 찾지 못했습니다. 원본 파일을 다시 선택해 주세요.")
    code, channels, rate, align, bits = fmt
    if channels not in (1, 2) or not 8000 <= rate <= 192000 or not ((code == 1 and bits in (16, 24, 32)) or (code == 3 and bits == 32)):
        raise ValueError(FORMAT_HELP)
    if align != channels * bits // 8:
        raise ValueError("WAV 블록 크기가 채널 수와 비트 수에 맞지 않습니다. 원본 파일을 다시 선택해 주세요.")
    frames = chunk[1] // align
    if frames <= 0 or frames / rate > MAX_SECONDS:
        raise ValueError("녹음은 0초보다 길고 10분 이하여야 합니다.")
    return {"code": code, "channels": channels, "rate": rate, "bits": bits, "start": chunk[0], "frames": frames, "align": align}


def _decode(data: bytes, h: dict):
    """(샘플 배열, 정규화 나눗수). 배열은 채널이 섞인 원래 순서이며 값 / 나눗수가 -1~1이다."""
    raw = memoryview(data)[h["start"]:h["start"] + h["frames"] * h["align"]]
    bits = h["bits"]
    if bits == 24:
        padded = bytearray(h["frames"] * h["channels"] * 4)
        padded[1::4], padded[2::4], padded[3::4] = raw[0::3], raw[1::3], raw[2::3]
        values, scale = array.array("i"), 2147483648
        values.frombytes(padded)
    else:
        values = array.array({16: "h", 32: "f" if h["code"] == 3 else "i"}[bits])
        scale = 1 if h["code"] == 3 else 2 ** (bits - 1)
        values.frombytes(raw)
    if sys.byteorder != "little":
        values.byteswap()
    return values, scale


def _frame_rms(values, per_frame: int, scale) -> list:
    """20ms 프레임마다 RMS. 전체 샘플을 한 번에 훑되 프레임 값만 모아 메모리를 아낀다."""
    sumsq = getattr(math, "sumprod", None) or (lambda a, b: sum(map(operator.mul, a, b)))
    out = []
    for start in range(0, len(values) - per_frame + 1, per_frame):
        seg = values[start:start + per_frame]
        out.append(math.sqrt(sumsq(seg, seg) / per_frame) / scale)
    return out


def _percentile(sorted_values, p):
    return sorted_values[min(len(sorted_values) - 1, int(p * len(sorted_values)))] if sorted_values else 0


def _measure_frames(env: list) -> dict:
    """analysis.js와 같은 기준: 바닥=하위 10%, 말소리=상위 90%, 기준=바닥+(말소리-바닥)×0.15."""
    none = {"found": False, "speech_start": None, "speech_end": None, "spoken": None,
            "pause_count": 0, "pause_median": None, "pause_longest": None}
    ordered = sorted(env)
    floor, loud = _percentile(ordered, .1), _percentile(ordered, .9)
    if not env or loud < .01 or loud < floor * 3:
        return none
    limit = floor + (loud - floor) * .15
    min_speech, min_pause = math.ceil(MIN_SPEECH_MS / FRAME_MS), math.ceil(MIN_PAUSE_MS / FRAME_MS)
    runs, start = [], -1
    for i in range(len(env) + 1):
        is_loud = i < len(env) and env[i] > limit
        if is_loud and start < 0:
            start = i
        elif not is_loud and start >= 0:
            if i - start >= min_speech:
                runs.append((start, i))
            start = -1
    if not runs:
        return none
    sec = FRAME_MS / 1000
    gaps = [(b[0] - a[1]) * sec for a, b in zip(runs, runs[1:]) if b[0] - a[1] >= min_pause]
    return {"found": True, "speech_start": runs[0][0] * sec, "speech_end": runs[-1][1] * sec,
            "spoken": sum(e - s for s, e in runs) * sec, "pause_count": len(gaps),
            "pause_median": statistics.median(gaps) if gaps else None, "pause_longest": max(gaps) if gaps else None}


def measure_speech(samples, rate: int) -> dict:
    """모노 샘플(-1~1)의 말소리 구간과 쉼을 잰다. 점수가 아니라 측정값이다. 시간 단위는 초."""
    return _measure_frames(_frame_rms(samples, max(1, round(rate * FRAME_MS / 1000)), 1))


_ANALYZED: dict = {}


def analyze_wav(data: bytes) -> dict:
    """WAV 검사·측정. 같은 내용(SHA-256)은 다시 디코딩하지 않는다(최근 4개). 돌려주는 값은 복사본이다."""
    if not isinstance(data, bytes) or not data:
        raise ValueError("녹음 파일이 비어 있습니다.")
    key = hashlib.sha256(data).hexdigest()
    if key not in _ANALYZED:
        if len(_ANALYZED) >= 4:
            _ANALYZED.pop(next(iter(_ANALYZED)))
        _ANALYZED[key] = _analyze_wav(data)
    meta = _ANALYZED[key]
    return {**meta, "envelope": list(meta["envelope"]), "speech": dict(meta["speech"])}


def _analyze_wav(data: bytes) -> dict:
    if not isinstance(data, bytes) or not data:
        raise ValueError("녹음 파일이 비어 있습니다.")
    if len(data) > MAX_AUDIO:
        raise ValueError("각 녹음은 231MB 이하 WAV 파일을 선택해 주세요.")
    h = _parse_wav(data)
    values, scale = _decode(data, h)
    per_frame = max(1, round(h["rate"] * FRAME_MS / 1000)) * h["channels"]
    env = _frame_rms(values, per_frame, scale)
    if h["code"] == 3:
        tail = values[len(env) * per_frame:]
        if not all(map(math.isfinite, env)) or not all(map(math.isfinite, tail)):
            raise ValueError("녹음에 유효하지 않은 샘플(NaN·무한대)이 있습니다. 원본 파일을 다시 선택해 주세요.")
    # 큰 파일의 화면 분석(파형·크기)은 최대 65,536개 샘플로 제한한다. 말소리·쉼 측정은 전체 샘플로 한다.
    stride = max(1, math.ceil(len(values) / 65536))
    sampled = values[::stride]
    rms = math.sqrt(sum((v / scale) ** 2 for v in sampled) / len(sampled))
    peak = max(abs(v) for v in sampled) / scale
    bin_size = max(1, math.ceil(len(sampled) / 128))
    envelope = [max(abs(v) for v in sampled[i:i+bin_size]) / scale for i in range(0, len(sampled), bin_size)]
    return {"duration": h["frames"] / h["rate"], "sample_rate": h["rate"], "channels": h["channels"],
            "rms_dbfs": round(20 * math.log10(rms), 1) if rms else None,
            "sampled_peak": peak, "envelope": envelope, "speech": _measure_frames(env),
            "sha256": hashlib.sha256(data).hexdigest()}


def make_bundle(result: Result, audio: dict, checks: dict, notes: str) -> bytes:
    if type(notes) is not str or len(notes) > 10000:
        raise ValueError("비교 메모는 10,000자 이하로 입력해 주세요.")
    # 녹음 둘이 base64로 JSON에 들어가므로 커지면 분석 전에 먼저 거부한다.
    if sum(4 * ((len(d) + 2) // 3) for d in audio.values() if isinstance(d, bytes)) > MAX_BACKUP:
        raise ValueError("녹음이 커서 작업 JSON에 넣을 수 없습니다(JSON 한도 48MB). 원본 WAV를 각각 보관해 주세요.")
    out_audio = {}
    for slot, data in audio.items():
        if slot not in ("A", "B"):
            raise ValueError("알 수 없는 녹음 슬롯입니다.")
        meta = analyze_wav(data)
        out_audio[slot] = {"base64": base64.b64encode(data).decode(), "sha256": meta["sha256"]}
    if set(checks) - {"A", "B"} or any(type(v) is not bool for v in checks.values()):
        raise ValueError("원고 확인 표시가 올바르지 않습니다.")
    packet = {"format": "voice-persona-workshop", "version": 1, "result": result.to_dict(),
              "audio": out_audio, "checks": checks, "notes": notes}
    encoded = json.dumps(packet, ensure_ascii=False, indent=2).encode()
    if len(encoded) > MAX_BACKUP:
        raise ValueError("작업 JSON이 48MB를 넘습니다. 원본 WAV를 각각 보관해 주세요.")
    return encoded


def load_bundle(encoded: bytes) -> tuple[Result, dict, dict, str]:
    if len(encoded) > MAX_BACKUP:
        raise ValueError("48MB 이하의 작업 JSON을 선택해 주세요.")
    try:
        packet = json.loads(encoded)
        if not isinstance(packet, dict) or packet.get("format") != "voice-persona-workshop" or packet.get("version") != 1:
            raise ValueError("이 앱에서 내보낸 작업 JSON을 선택해 주세요.")
        raw_result = packet["result"]
        if not isinstance(raw_result, dict) or not isinstance(raw_result.get("created_at"), str):
            raise ValueError("작업 기록이 올바르지 않습니다.")
        datetime.fromisoformat(raw_result["created_at"])
        result = build_result(raw_result["inputs"], raw_result["created_at"])
        # 원문이나 변환 결과를 꾸며 저장한 백업은 거부한다.
        if json.loads(json.dumps(result.to_dict(), ensure_ascii=False)) != raw_result:
            raise ValueError("저장된 변환 기록이 원문·등록 규칙과 일치하지 않습니다.")
        if not isinstance(packet["audio"], dict) or not isinstance(packet["checks"], dict):
            raise ValueError("녹음 기록 형식이 올바르지 않습니다.")
        audio = {}
        for slot, item in packet["audio"].items():
            if slot not in ("A", "B") or not isinstance(item, dict) or not isinstance(item.get("base64"), str):
                raise ValueError("녹음 슬롯을 확인해 주세요.")
            data = base64.b64decode(item["base64"], validate=True)
            meta = analyze_wav(data)
            if meta["sha256"] != item.get("sha256"):
                raise ValueError("녹음 파일의 체크섬이 일치하지 않습니다.")
            audio[slot] = data
        checks, notes = packet["checks"], packet["notes"]
        if set(checks) - {"A", "B"} or any(type(v) is not bool for v in checks.values()) or not isinstance(notes, str) or len(notes) > 10000:
            raise ValueError("메모·확인 표시를 읽을 수 없습니다.")
        return result, audio, checks, notes
    except (KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError, OverflowError) as e:
        raise ValueError("작업 JSON의 형식을 확인해 주세요. 현재 작업은 유지됩니다.") from e
