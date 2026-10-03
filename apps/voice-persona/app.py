"""배리어프리 보이스 페르소나: 사실 보존과 직접 녹음 A/B 비교 실행본."""
from __future__ import annotations
import hashlib
import html
import io
import zipfile
import pandas as pd
import streamlit as st
from core import (MAX_SESSION_AUDIO, MODES, PERSONAS, SCENARIOS, analyze_wav, audio_total, build_result,
                  drop_other_audio, load_bundle, make_bundle, result_is_current)

st.set_page_config(page_title="보이스 페르소나 실험실", page_icon="🎙️", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown("""
<style>
html,body,[data-testid="stApp"]{font-size:18px;color:#142b34}
.block-container{max-width:1100px;padding-top:1.4rem;padding-bottom:3rem}
h1{font-size:2rem!important;line-height:1.35!important}
h2{font-size:1.45rem!important}h3{font-size:1.12rem!important}
p,[data-testid="stText"],label,[data-testid="stCaptionContainer"]{font-size:1rem!important;line-height:1.7}
textarea,input,[data-baseweb="select"]{font-size:1rem!important}
button,[data-testid="stDownloadButton"] button{min-height:48px!important;font-size:1rem!important;white-space:normal}
[data-testid="stText"]{white-space:pre-wrap;overflow-wrap:anywhere}
[data-testid="stMetricValue"]{font-size:1.4rem}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{color:#4b6068!important;opacity:1!important}
[data-testid="stSidebarCollapsedControl"],[data-testid="stExpandSidebarButton"],[data-testid="stBaseButton-headerNoPadding"]{display:none!important}
button:focus-visible,input:focus-visible,textarea:focus-visible{outline:3px solid #176b67!important;outline-offset:3px}
[data-testid="stSidebar"]{display:none}
[data-testid="stAudio"]{min-height:54px}
@media(max-width:650px){
 .block-container{padding:1rem!important}h1{font-size:1.5rem!important}
 [data-testid="stHorizontalBlock"]{flex-direction:column;align-items:stretch}
 [data-testid="stColumn"]{width:100%!important;flex:1 1 100%!important;min-width:0!important}
 [data-testid="stFileUploader"]{min-width:0!important}
}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.steps{display:flex;flex-wrap:wrap;gap:.4rem;margin:.2rem 0 1rem;padding:0;list-style:none}
.steps li{display:flex;align-items:center;gap:.45rem;padding:.45rem .8rem;border-radius:999px;border:1px solid #c9d6da;background:#fff;color:#4b6068;font-size:.95rem}
.steps li b{display:inline-grid;place-items:center;width:1.6rem;height:1.6rem;border-radius:50%;background:#e4ecee;color:#142b34;font-size:.85rem}
.steps li.done{border-color:#9cc8c2;color:#176b67}.steps li.done b{background:#176b67;color:#fff}
.steps li.now{border:2px solid #176b67;color:#142b34;font-weight:600}.steps li.now b{background:#f2b632;color:#142b34}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>""", unsafe_allow_html=True)

DEFAULT_SOURCE = "에러 코드 404: 지문 생체 인증에 3회 연속 실패하여 계정이 잠겼습니다. 고객센터로 문의하십시오."
for key, value in {"source_input": DEFAULT_SOURCE, "persona_input": "senior", "scenario_input": "error",
                   "mode_input": "original", "rate_input": .85, "pause_input": 850,
                   "result": None, "audio_by_result": {}, "checks_by_result": {}, "cleanup_notice": ""}.items():
    if key not in st.session_state:
        st.session_state[key] = value


def cached_meta(data):
    """큰 녹음을 rerun마다 다시 분석하지 않도록 내용 해시로 결과를 세션에 둔다(최대 4개)."""
    cache = st.session_state.setdefault("meta_cache", {})
    key = hashlib.sha256(data).hexdigest()
    if key not in cache:
        if len(cache) >= 4:
            cache.pop(next(iter(cache)))
        cache[key] = analyze_wav(data)
    return cache[key]


def seconds(value):
    return "-" if value is None else f"{value:.2f}초"


def persona_defaults():
    persona = PERSONAS[st.session_state.persona_input]
    st.session_state.rate_input = persona.rate
    st.session_state.pause_input = persona.pause_ms


def set_result(new):
    """결과를 바꾼다. 다른 작업이 되면 이전 작업의 녹음·확인 표시·메모를 지워 서버 메모리에 쌓지 않는다."""
    old = st.session_state.result
    st.session_state.result = new
    if old is None or old.fingerprint == new.fingerprint:
        return
    st.session_state.pop("export_cache", None)
    dropped, count = drop_other_audio(st.session_state.audio_by_result, new.fingerprint)
    for fp in dropped:
        st.session_state.checks_by_result.pop(fp, None)
    for fp in set(dropped) | {old.fingerprint}:
        for key in [k for k in st.session_state if isinstance(k, str) and fp in k and k.startswith(("loaded_", "check_", "notes_"))]:
            del st.session_state[key]
    st.session_state.cleanup_notice = (f"이전 작업의 녹음 {count}개를 서버 메모리에서 지웠습니다. "
                                       "필요하면 작업 JSON으로 먼저 저장해 두세요.") if count else ""


def restore_workshop():
    uploaded = st.session_state.get("workshop_file")
    if uploaded is None or not st.session_state.get("replace_confirm"):
        st.session_state.restore_error = "저장한 작업 파일을 고르고, 바꾼다는 확인 칸에 체크해 주세요."
        return
    try:
        result, audio, checks, notes = load_bundle(uploaded.getvalue())
    except ValueError as e:
        st.session_state.restore_error = str(e)
        return
    # 모든 검증이 끝난 후에만 현재 세션을 바꾼다. 콜백은 위젯 생성 전에 실행된다.
    for name, value in result.inputs.items():
        widget = {"source":"source_input", "persona":"persona_input", "scenario":"scenario_input",
                  "mode":"mode_input", "rate":"rate_input", "pause_ms":"pause_input"}[name]
        st.session_state[widget] = value
    set_result(result)
    st.session_state.audio_by_result[result.fingerprint] = audio
    st.session_state.checks_by_result[result.fingerprint] = checks
    st.session_state[f"notes_{result.fingerprint}"] = notes
    for slot in ("A", "B"):
        st.session_state[f"check_{slot}_{result.fingerprint}"] = checks.get(slot, False)
    st.session_state.restore_error = ""
    st.session_state.restore_done = True


STEP_NAMES = ["읽을 문장 넣기", "원고 확인", "두 가지로 녹음", "비교하고 기록", "저장"]
MODE_LABELS = {"original": "그대로 읽기", "terms": "어려운 표현만 쉽게 (등록된 표현만 쉽게 바꾸기)"}
EXAMPLES = {
    "error": ("오류 안내 예문", "파일 업로드가 실패했습니다. 파일은 삭제되지 않았습니다. '다시 업로드'를 눌러 주세요."),
    "progress": ("진행 안내 예문", "파일을 올리는 중입니다. 약 30초 걸립니다. 창을 닫지 마십시오."),
    "complete": ("완료 안내 예문", "결제가 완료되었습니다. 영수증은 '내 주문' 메뉴에서 확인하십시오."),
}


def show_steps(slot, now: int):
    """지금 단계를 위쪽 줄에 표시한다. now보다 앞은 끝난 단계."""
    items = []
    for i, name in enumerate(STEP_NAMES):
        state = "done" if i < now else "now" if i == now else ""
        label = " (지금)" if i == now else " (끝)" if i < now else ""
        items.append(f'<li class="{state}"><b>{i + 1}</b>{name}<span class="sr-only">{label}</span></li>')
    slot.markdown('<ol class="steps" aria-label="진행 단계">' + "".join(items) + "</ol>", unsafe_allow_html=True)


def use_example(scenario: str):
    st.session_state.source_input = EXAMPLES[scenario][1]
    st.session_state.scenario_input = scenario


def compare_line(name: str, a, b, same: float = .05) -> str:
    """측정값 둘을 한 문장으로. 점수가 아니라 차이만 말한다."""
    if a is None or b is None:
        return f"{name}: A {seconds(a)}, B {seconds(b)}"
    gap = b - a
    if abs(gap) < same:
        how = "거의 같습니다"
    else:
        how = f"B가 {abs(gap):.2f}초 {'더 깁니다' if gap > 0 else '더 짧습니다'}"
    return f"{name}: A {a:.2f}초, B {b:.2f}초 → {how}"


st.title("🎙️ 보이스 페르소나 실험실")
st.write("안내 문장을 한 글자도 바꾸지 않고 지키면서, 두 가지 방식으로 읽어 보고 어느 쪽이 더 잘 들리는지 비교합니다.")
steps_slot = st.empty()
show_steps(steps_slot, 0)
st.caption("이 앱은 문장을 새로 지어내지 않습니다. 감정 인식, AI 다시 쓰기, 음성 합성은 하지 않습니다.")

with st.expander("저장해 둔 작업 불러오기"):
    st.file_uploader("저장한 작업 파일 (JSON)", type=["json"], key="workshop_file")
    st.checkbox("지금 화면의 내용을 불러온 작업으로 바꿉니다", key="replace_confirm")
    st.button("불러오기", key="restore_button", on_click=restore_workshop)
    if st.session_state.get("restore_error"):
        st.error(st.session_state.restore_error)
    if st.session_state.get("restore_done"):
        st.success("문장, 낭독 목표, 녹음, 메모를 불러왔습니다.")
        st.session_state.restore_done = False

st.header("1. 읽을 문장 넣기")
st.write("예문으로 바로 해 보거나, 직접 안내 문장을 붙여 넣으세요.")
for column, (scenario, (label, _)) in zip(st.columns(len(EXAMPLES)), EXAMPLES.items()):
    column.button(label, key=f"example_{scenario}", on_click=use_example, args=(scenario,), width="stretch")
st.text_area("읽을 안내 문장", key="source_input", height=140, max_chars=5000,
             help="전화번호·시간·다음 행동·버튼 이름은 이 문장에 있는 것만 씁니다. 새로 덧붙이지 않습니다.")
left, right = st.columns(2)
with left:
    st.selectbox("누가 듣나요?", options=list(PERSONAS), format_func=lambda k: PERSONAS[k].label,
                 key="persona_input", on_change=persona_defaults)
with right:
    st.selectbox("어떤 안내인가요?", options=list(SCENARIOS), format_func=lambda k: SCENARIOS[k], key="scenario_input")
st.radio("문장 다듬기", options=list(MODES), format_func=lambda k: MODE_LABELS[k], key="mode_input", horizontal=True)

persona = PERSONAS[st.session_state.persona_input]
with st.expander(f"B 낭독 목표 조정 · 지금: 속도 {st.session_state.rate_input:.2f}배, 문장 사이 쉼 {st.session_state.pause_input / 1000:.2f}초"):
    st.write(persona.direction)
    st.write(persona.breath)
    st.slider("B 속도 (평소 낭독 = 1.00배)", min_value=.6, max_value=1.3, step=.05, key="rate_input")
    st.slider("B 문장 사이 쉼 (밀리초, 1000 = 1초)", min_value=250, max_value=1800, step=50, key="pause_input")
    st.caption("사람이 읽을 때 참고하는 목표입니다. 녹음에 자동으로 적용되지 않고, 이해도를 잰 값도 아닙니다. 실제로 듣는 분의 취향에 맞춰 바꾸세요.")

inputs = {"source": st.session_state.source_input, "persona": st.session_state.persona_input,
          "scenario": st.session_state.scenario_input, "mode": st.session_state.mode_input,
          "rate": st.session_state.rate_input, "pause_ms": st.session_state.pause_input}
if st.button("원고 만들기 →", type="primary", key="prepare", width="stretch"):
    try:
        set_result(build_result(inputs))
    except ValueError as e:
        st.error(str(e))

result = st.session_state.result
if result is None:
    st.caption("문장을 넣고 '원고 만들기'를 누르면 녹음 단계가 열립니다.")
    st.stop()
if not result_is_current(result, inputs):
    st.warning("입력이 바뀌었습니다. 이전 원고와 녹음은 숨겼습니다. '원고 만들기'를 다시 눌러 주세요.")
    st.stop()

st.header("2. 원고 확인")
col_a, col_b = st.columns(2)
with col_a:
    st.subheader("넣은 문장")
    with st.container(border=True):
        st.text(result.source)
with col_b:
    st.subheader("읽을 원고")
    with st.container(border=True):
        st.text(result.text)
if result.edits:
    st.success(f"정해 둔 쉬운 표현으로 {len(result.edits)}곳만 바꿨습니다. 숫자·전화번호·버튼 이름은 그대로입니다.")
    with st.expander("바뀐 곳 보기"):
        for edit in result.edits:
            st.text(f"{edit.before} → {edit.after}")
        st.caption("미리 등록한 표현만 바꿨는지 확인한 결과입니다. 문장 뜻이 완전히 같은지까지 자동으로 보증하지는 않습니다.")
else:
    st.success("넣은 문장을 그대로 씁니다. 새 전화번호·위치·행동은 덧붙이지 않았습니다.")
    if inputs["mode"] == "terms":
        st.caption("이 문장에는 쉽게 바꿀 등록 표현이 없어서 그대로 두었습니다.")

st.header("3. 두 가지로 녹음")
st.write("같은 원고를 두 번 읽습니다. **A는 평소처럼**, **B는 아래 목표대로** 읽으세요.")
st.html('<div style="font-size:1.35rem;line-height:1.8;padding:1rem 1.2rem;border-radius:12px;'
        'background:#fff8e6;border:1px solid #f2d27a;color:#142b34;white-space:pre-wrap;overflow-wrap:anywhere">'
        f'<div style="font-size:.85rem;color:#6b5a1f;margin-bottom:.3rem">읽을 원고</div>{html.escape(result.text)}</div>')
st.caption("마이크는 브라우저에서 권한을 허락해야 켜집니다(HTTPS 주소에서만). 마이크 대신 녹음 파일(WAV)을 올려도 됩니다. MP3·M4A는 WAV로 바꿔 올려 주세요. 파일은 10분·48MB까지입니다.")
if st.session_state.cleanup_notice:
    st.info(st.session_state.cleanup_notice)
current_audio = st.session_state.audio_by_result.setdefault(result.fingerprint, {})
current_checks = st.session_state.checks_by_result.setdefault(result.fingerprint, {})

for slot, column in zip(("A", "B"), st.columns(2)):
    with column:
        st.subheader("A · 평소처럼 읽기" if slot == "A" else f"B · {persona.title}")
        if slot == "B":
            st.info(f"{persona.direction} 목표: 속도 {inputs['rate']:.2f}배, 문장 사이 쉼 {inputs['pause_ms'] / 1000:.2f}초.")
        recorded = st.audio_input(f"{slot} 마이크로 녹음하기", sample_rate=24000, key=f"mic_{slot}_{result.fingerprint}")
        uploaded = st.file_uploader(f"{slot} 녹음 파일(WAV) 올리기", type=["wav"], key=f"wav_{slot}_{result.fingerprint}")
        candidates = [("마이크", recorded), ("파일", uploaded)]
        for source_kind, file in candidates:
            if file is None:
                continue
            data = file.getvalue()
            signature = (source_kind, len(data), file.name)
            source_key = f"loaded_{slot}_{result.fingerprint}_{source_kind}"
            # 같은 업로드를 매 rerun마다 덮어쓰지 않는다. 서로 같은 크기 파일도 해시로 구분한다.
            signature = (*signature, hashlib.sha256(data).hexdigest())
            error_key = source_key + "_error"
            if st.session_state.get(source_key) == signature:
                if st.session_state.get(error_key):
                    st.error(st.session_state[error_key])
                continue
            try:
                # 세션 전체 녹음 용량을 넘지 않게 한다(이 슬롯의 기존 녹음은 교체되므로 뺀다).
                if audio_total(st.session_state.audio_by_result) - len(current_audio.get(slot, b"")) + len(data) > MAX_SESSION_AUDIO:
                    raise ValueError(f"한 번에 둘 수 있는 녹음은 모두 {MAX_SESSION_AUDIO // 1_000_000}MB까지입니다.")
                cached_meta(data)
            except ValueError as e:
                message = f"새 {source_kind} 녹음을 쓰지 못했습니다: {e} 전에 넣은 녹음은 그대로 있습니다."
                st.session_state[error_key] = message
                st.error(message)
                st.session_state[source_key] = signature
                continue
            st.session_state.pop(error_key, None)
            current_audio[slot] = data
            current_checks[slot] = False
            st.session_state[f"check_{slot}_{result.fingerprint}"] = False
            st.session_state[source_key] = signature
        data = current_audio.get(slot)
        if data:
            meta = cached_meta(data)
            st.audio(data, format="audio/wav")
            st.write(f"길이 {meta['duration']:.2f}초 · {meta['sample_rate']:,}Hz · {'모노' if meta['channels'] == 1 else '스테레오'}")
            st.line_chart(meta["envelope"], height=110, y_label="소리 크기")
            st.caption("녹음의 실제 소리 크기를 그린 것입니다. 점수가 아닙니다.")
            if meta["rms_dbfs"] is None or meta["rms_dbfs"] < -55:
                st.warning("소리가 아주 작습니다. 들어 보고 필요하면 다시 녹음하세요.")
            current_checks[slot] = st.checkbox(f"{slot} 녹음을 들어 보니 원고와 같습니다",
                    key=f"check_{slot}_{result.fingerprint}")
            st.download_button(f"{slot} 녹음 받기 (WAV)", data=data, file_name=f"persona-{slot}.wav", mime="audio/wav")
        else:
            st.caption("녹음하거나 파일을 올리면 여기에서 바로 들을 수 있습니다.")

st.header("4. 비교하고 기록")
if len(current_audio) == 2:
    meta_a, meta_b = cached_meta(current_audio["A"]), cached_meta(current_audio["B"])
    sp_a, sp_b = meta_a["speech"], meta_b["speech"]
    for slot, sp in (("A", sp_a), ("B", sp_b)):
        if not sp["found"]:
            st.warning(f"{slot} 녹음에서 말소리를 찾지 못했습니다. 소리가 너무 작거나 잡음만 있는지 들어 보세요.")
    target = inputs["pause_ms"] / 1000
    if sp_a["found"] and sp_b["found"]:
        lines = [compare_line("말한 시간", sp_a["spoken"], sp_b["spoken"])]
        if sp_a["pause_count"] and sp_b["pause_count"]:
            lines.append(compare_line("쉼(중간값)", sp_a["pause_median"], sp_b["pause_median"]))
        else:
            lines.append(f"쉼: A {sp_a['pause_count']}개, B {sp_b['pause_count']}개 (0.25초 넘게 쉰 곳이 없는 녹음이 있습니다)")
        if sp_b["pause_count"]:
            gap = sp_b["pause_median"] - target
            lines.append(f"B 쉼과 목표 {target:.2f}초의 차이: {'거의 같습니다' if abs(gap) < .05 else f'{abs(gap):.2f}초 ' + ('더 깁니다' if gap > 0 else '더 짧습니다')} (참고)")
        st.success("**한눈에 보기**\n\n" + "\n".join(f"- {line}" for line in lines))

    def cell(sp, key):
        return seconds(sp[key]) if sp["found"] else "말소리를 찾지 못했습니다"

    def count(sp):
        return f"{sp['pause_count']}개" if sp["found"] else "말소리를 찾지 못했습니다"

    def pause_cell(sp, key):
        if not sp["found"]:
            return "말소리를 찾지 못했습니다"
        return seconds(sp[key]) if sp["pause_count"] else "쉼 없음"

    table = pd.DataFrame({"항목": ["파일 길이", "말소리 시작", "말소리 끝", "말한 시간", "쉼 개수", "쉼 중간값", "가장 긴 쉼"],
              "A": [seconds(meta_a["duration"]), cell(sp_a, "speech_start"), cell(sp_a, "speech_end"), cell(sp_a, "spoken"),
                    count(sp_a), pause_cell(sp_a, "pause_median"), pause_cell(sp_a, "pause_longest")],
              "B": [seconds(meta_b["duration"]), cell(sp_b, "speech_start"), cell(sp_b, "speech_end"), cell(sp_b, "spoken"),
                    count(sp_b), pause_cell(sp_b, "pause_median"), pause_cell(sp_b, "pause_longest")],
              "B 목표(참고)": ["", "", "", "", "", f"문장 사이 쉼 {target:.2f}초", ""]})
    st.table(table.style.hide(axis="index"))
    st.caption("녹음 소리 크기로 잰 값입니다. 0.25초 넘게 조용한 곳을 쉼으로 셉니다(숨 고르기도 들어갑니다). 파일 길이에는 앞뒤 여백이 들어 있습니다. 점수나 이해도가 아니니, 꼭 두 녹음을 직접 들어 보고 판단하세요.")
    if all(current_checks.get(slot) for slot in ("A", "B")):
        st.success("두 녹음 모두 원고와 같다고 확인했습니다. 어느 쪽이 더 잘 들렸는지 아래에 남겨 주세요.")
else:
    missing = " · ".join(slot for slot in ("A", "B") if slot not in current_audio)
    st.info(f"아직 {missing} 녹음이 없습니다. A와 B를 모두 넣으면 여기에 비교가 나옵니다.")
notes = st.text_area("더 잘 전달된 낭독과 그 이유", key=f"notes_{result.fingerprint}", height=120, max_chars=10000,
                   placeholder="예: B는 다음 행동 앞에서 쉬어 버튼 이름이 더 잘 들렸습니다.")

st.header("5. 저장")
st.caption("이 화면의 내용은 창을 닫거나 새로고침하면 사라질 수 있습니다. 이어서 하려면 '작업 전체 저장'으로 파일을 받아 두세요. 올린 녹음은 이 앱이 돌아가는 서버에서 처리됩니다.")
def build_exports():
    """작업 JSON과 ZIP. 녹음 해시·확인 표시·원문·메모가 같으면 다시 만들지 않는다(최근 1개만 보관)."""
    key = (result.fingerprint, tuple((slot, cached_meta(d)["sha256"]) for slot, d in sorted(current_audio.items())),
           tuple(sorted(current_checks.items())), notes)
    cache = st.session_state.get("export_cache")
    if cache and cache[0] == key:
        return cache[1], cache[2], cache[3]
    try:
        bundle, error = make_bundle(result, current_audio, current_checks, notes), None
    except ValueError as e:
        bundle, error = None, str(e)
    audio_zip = None
    if current_audio:
        buffer = io.BytesIO()
        # WAV는 압축이 거의 안 되므로 그대로 담는다.
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as archive:
            for slot, data in current_audio.items():
                archive.writestr(f"persona-{slot}.wav", data)
            archive.writestr("script.txt", result.text)
            archive.writestr("notes.txt", notes)
        audio_zip = buffer.getvalue()
    st.session_state.export_cache = (key, bundle, error, audio_zip)
    return bundle, error, audio_zip


bundle, bundle_error, audio_zip = build_exports()
save_cols = st.columns(3)
if bundle_error:
    st.error(bundle_error)
else:
    save_cols[0].download_button("작업 전체 저장", data=bundle, file_name="voice-persona-workshop.json",
                                 mime="application/json", type="primary", width="stretch",
                                 help="문장·목표·녹음·메모를 파일 하나로. 나중에 '저장해 둔 작업 불러오기'로 이어서 합니다.")
save_cols[1].download_button("원고만 받기 (TXT)", data=result.text.encode(), file_name="narration-script.txt",
                             mime="text/plain", width="stretch")
if audio_zip:
    save_cols[2].download_button("녹음과 원고 묶음 받기 (ZIP)", data=audio_zip, file_name="persona-comparison.zip",
                                 mime="application/zip", width="stretch")

show_steps(steps_slot, 2 if len(current_audio) < 2 else 3 if not notes.strip() else 4)

with st.expander("개발자용 정보"):
    st.json({"persona": persona.title, "scenario": SCENARIOS[inputs["scenario"]],
             "speech_rate_design": inputs["rate"], "sentence_gap_design_ms": inputs["pause_ms"],
             "delivery_direction": persona.direction, "breath_direction": persona.breath,
             "emotion_recognition_performed": False, "llm_rewrite_performed": False,
             "tts_synthesis_performed": False, "source_fingerprint": result.fingerprint})
