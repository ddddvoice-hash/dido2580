"""배리어프리 보이스 페르소나: 사실 보존과 직접 녹음 A/B 비교 실행본."""
from __future__ import annotations
import io
import zipfile
import streamlit as st
from core import (MODES, PERSONAS, SCENARIOS, analyze_wav, build_result,
                  load_bundle, make_bundle, result_is_current)

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
button:focus-visible,input:focus-visible,textarea:focus-visible{outline:3px solid #176b67!important;outline-offset:3px}
[data-testid="stSidebar"]{display:none}
[data-testid="stAudio"]{min-height:54px}
@media(max-width:650px){
 .block-container{padding:1rem!important}h1{font-size:1.5rem!important}
 [data-testid="stHorizontalBlock"]{flex-direction:column;align-items:stretch}
 [data-testid="stColumn"]{width:100%!important;flex:1 1 100%!important;min-width:0!important}
 [data-testid="stFileUploader"]{min-width:0!important}
}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>""", unsafe_allow_html=True)

DEFAULT_SOURCE = "에러 코드 404: 지문 생체 인증에 3회 연속 실패하여 계정이 잠겼습니다. 고객센터로 문의하십시오."
for key, value in {"source_input": DEFAULT_SOURCE, "persona_input": "senior", "scenario_input": "error",
                   "mode_input": "original", "rate_input": .85, "pause_input": 850,
                   "result": None, "audio_by_result": {}, "checks_by_result": {}}.items():
    if key not in st.session_state:
        st.session_state[key] = value


def persona_defaults():
    persona = PERSONAS[st.session_state.persona_input]
    st.session_state.rate_input = persona.rate
    st.session_state.pause_input = persona.pause_ms


def restore_workshop():
    uploaded = st.session_state.get("workshop_file")
    if uploaded is None or not st.session_state.get("replace_confirm"):
        st.session_state.restore_error = "작업 JSON을 선택하고 교체 확인에 체크해 주세요."
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
    st.session_state.result = result
    st.session_state.audio_by_result[result.fingerprint] = audio
    st.session_state.checks_by_result[result.fingerprint] = checks
    st.session_state[f"notes_{result.fingerprint}"] = notes
    for slot in ("A", "B"):
        st.session_state[f"check_{slot}_{result.fingerprint}"] = checks.get(slot, False)
    st.session_state.restore_error = ""
    st.session_state.restore_done = True


st.title("🎙️ 보이스 페르소나 실험실")
st.write("안내의 사실을 지키고, 같은 문장을 두 가지 낭독으로 비교하세요.")
st.info("현재 기능: 원문 보존·등록 표현 치환·직접 녹음 비교. 감정 인식이나 자동 AI 재작성·TTS 합성은 수행하지 않습니다.")

with st.expander("저장한 작업 가져오기"):
    st.file_uploader("작업 JSON 선택", type=["json"], key="workshop_file")
    st.checkbox("현재 입력과 결과를 이 작업으로 교체합니다", key="replace_confirm")
    st.button("작업 가져오기", key="restore_button", on_click=restore_workshop)
    if st.session_state.get("restore_error"):
        st.error(st.session_state.restore_error)
    if st.session_state.get("restore_done"):
        st.success("원문·낭독 설계·녹음·메모를 복원했습니다.")
        st.session_state.restore_done = False

st.header("1. 안내 원문과 듣는 상황")
left, right = st.columns(2)
with left:
    st.selectbox("듣는 사용자", options=list(PERSONAS), format_func=lambda k: PERSONAS[k].label,
                 key="persona_input", on_change=persona_defaults)
with right:
    st.selectbox("발화 상황", options=list(SCENARIOS), format_func=lambda k: SCENARIOS[k], key="scenario_input")
st.text_area("변환할 안내 원문", key="source_input", height=140, max_chars=5000,
             help="전화번호·시간·다음 행동·버튼 이름은 원문에 있는 정보만 사용합니다.")
st.radio("표현 방식", options=list(MODES), format_func=lambda k: MODES[k], key="mode_input", horizontal=True)

persona = PERSONAS[st.session_state.persona_input]
with st.expander("낭독 설계 조정 · 실제 청자의 선호에 맞춰 바꾸세요"):
    st.write(persona.direction)
    st.write(persona.breath)
    st.slider("기본 낭독 대비 속도 설계값", min_value=.6, max_value=1.3, step=.05, key="rate_input")
    st.slider("문장 사이 쉼 설계값 (ms)", min_value=250, max_value=1800, step=50, key="pause_input")
    st.caption("설계값은 사람이 낭독할 때 참고하는 값입니다. 음성에 자동 적용되거나 청자의 이해도를 측정한 값이 아닙니다.")

inputs = {"source": st.session_state.source_input, "persona": st.session_state.persona_input,
          "scenario": st.session_state.scenario_input, "mode": st.session_state.mode_input,
          "rate": st.session_state.rate_input, "pause_ms": st.session_state.pause_input}
if st.button("원문 확인하고 낭독 원고 준비", type="primary", key="prepare"):
    try:
        st.session_state.result = build_result(inputs)
    except ValueError as e:
        st.error(str(e))

result = st.session_state.result
if result is None:
    st.caption("원문을 확인한 뒤 녹음 A/B 비교를 시작하세요.")
    st.stop()
if not result_is_current(result, inputs):
    st.warning("입력이 바뀌었습니다. 이전 결과와 녹음은 숨겼습니다. 원고 준비를 다시 누르세요.")
    st.stop()

st.header("2. 변경 내용 확인")
col_a, col_b = st.columns(2)
with col_a:
    st.subheader("입력 원문")
    with st.container(border=True):
        st.text(result.source)
with col_b:
    st.subheader("낭독할 원고")
    with st.container(border=True):
        st.text(result.text)
if result.edits:
    st.success(f"등록된 표현 {len(result.edits)}곳만 바꿨습니다. 원문 위치와 편집 기록을 대조했습니다.")
    with st.expander("바뀐 표현과 검사 범위"):
        for edit in result.edits:
            st.text(f"{edit.before} → {edit.after}")
        st.caption("이 검사는 등록된 편집만 수행했는지 확인합니다. 일반적인 문장 의미 동등성이나 이해도를 자동 보증하지 않습니다.")
else:
    st.success("원문 그대로 보존했습니다. 새 전화번호·위치·행동은 추가하지 않았습니다.")
    if inputs["mode"] == "terms":
        st.caption("이 원문에는 등록된 치환 표현이 없어 그대로 유지했습니다.")

with st.expander("낭독 설계 JSON · 실제 처리 결과와 구분"):
    st.json({"persona": persona.title, "scenario": SCENARIOS[inputs["scenario"]],
             "speech_rate_design": inputs["rate"], "sentence_gap_design_ms": inputs["pause_ms"],
             "delivery_direction": persona.direction, "breath_direction": persona.breath,
             "emotion_recognition_performed": False, "llm_rewrite_performed": False,
             "tts_synthesis_performed": False, "source_fingerprint": result.fingerprint})

st.header("3. 같은 원고로 A/B 녹음")
st.write("A는 기본 낭독, B는 쉼·강조·속도를 조정한 낭독입니다. 두 녹음 모두 위의 같은 원고를 읽으세요.")
st.caption("마이크는 HTTPS 또는 localhost에서 브라우저 권한이 필요합니다. 오디오 파일을 올려도 됩니다. WAV는 각 16MB·5분 이하입니다.")
current_audio = st.session_state.audio_by_result.setdefault(result.fingerprint, {})
current_checks = st.session_state.checks_by_result.setdefault(result.fingerprint, {})

for slot, column in zip(("A", "B"), st.columns(2)):
    with column:
        st.subheader(f"{slot} · {'기본 낭독' if slot == 'A' else persona.title}")
        if slot == "B":
            st.write(persona.direction)
        recorded = st.audio_input(f"{slot} 마이크 녹음", sample_rate=24000, key=f"mic_{slot}_{result.fingerprint}")
        uploaded = st.file_uploader(f"{slot} WAV 파일 올리기", type=["wav"], key=f"wav_{slot}_{result.fingerprint}")
        candidates = [("마이크", recorded), ("파일", uploaded)]
        for source_kind, file in candidates:
            if file is None:
                continue
            data = file.getvalue()
            signature = (source_kind, len(data), file.name)
            source_key = f"loaded_{slot}_{result.fingerprint}_{source_kind}"
            # 같은 업로드를 매 rerun마다 덮어쓰지 않는다. 서로 같은 크기 파일도 해시로 구분한다.
            import hashlib
            signature = (*signature, hashlib.sha256(data).hexdigest())
            error_key = source_key + "_error"
            if st.session_state.get(source_key) == signature:
                if st.session_state.get(error_key):
                    st.error(st.session_state[error_key])
                continue
            try:
                analyze_wav(data)
            except ValueError as e:
                message = f"새 {source_kind} 녹음을 적용하지 못했습니다: {e} 기존 유효 녹음은 유지됩니다."
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
            meta = analyze_wav(data)
            st.audio(data, format="audio/wav")
            st.write(f"파일 길이 {meta['duration']:.2f}초 · {meta['sample_rate']:,}Hz · {meta['channels']}채널")
            st.line_chart(meta["envelope"], height=120, y_label="샘플 진폭")
            st.caption("파형은 녹음 파일의 샘플 진폭입니다. 따뜻함·감정 점수나 발화 속도가 아닙니다.")
            if meta["rms_dbfs"] is None or meta["rms_dbfs"] < -55:
                st.warning("녹음 소리가 매우 작습니다. 재생해서 확인하고 필요하면 다시 녹음하세요.")
            current_checks[slot] = st.checkbox(f"{slot} 녹음이 위 원고와 일치하는지 직접 들었습니다",
                    key=f"check_{slot}_{result.fingerprint}")
            st.download_button(f"{slot} 원본 WAV 받기", data=data, file_name=f"persona-{slot}.wav", mime="audio/wav")
        else:
            st.caption("새로 녹음하거나 WAV를 올리면 여기에 재생기가 나타납니다.")

st.header("4. 차이를 듣고 기록")
if len(current_audio) == 2:
    duration_a = analyze_wav(current_audio["A"])["duration"]
    duration_b = analyze_wav(current_audio["B"])["duration"]
    st.write(f"파일 길이: A {duration_a:.2f}초 / B {duration_b:.2f}초 · 차이 {duration_b-duration_a:+.2f}초")
    st.caption("파일 길이에는 앞뒤 여백이 포함됩니다. 길이 차이만으로 말하기 속도나 이해도를 판단하지 않습니다.")
    if all(current_checks.get(slot) for slot in ("A", "B")):
        st.success("같은 원고인지 직접 확인했습니다. 어떤 낭독이 더 잘 전달됐는지 이유를 남겨 주세요.")
else:
    st.info("A와 B를 모두 녹음하면 파일 길이를 나란히 보여드립니다.")
notes = st.text_area("더 잘 전달된 낭독과 그 이유", key=f"notes_{result.fingerprint}", height=120, max_chars=10000,
                   placeholder="예: B는 다음 행동 앞에서 쉬어 버튼 이름이 더 잘 들렸습니다.")

st.header("5. 작업 보관")
st.caption("입력·녹음은 현재 Streamlit 세션에 있습니다. 연결 종료·새로고침·서버 재시작으로 사라질 수 있으니 작업 JSON을 내려받으세요. 배포한 서버는 업로드한 음성을 처리합니다.")
try:
    bundle = make_bundle(result, current_audio, current_checks, notes)
    st.download_button("원문·설계·녹음·메모 전체 저장", data=bundle, file_name="voice-persona-workshop.json", mime="application/json")
except ValueError as e:
    st.error(str(e))
st.download_button("낭독 원고 TXT 받기", data=result.text.encode(), file_name="narration-script.txt", mime="text/plain")
if current_audio:
    audio_zip = io.BytesIO()
    with zipfile.ZipFile(audio_zip, "w", zipfile.ZIP_DEFLATED) as archive:
        for slot, data in current_audio.items():
            archive.writestr(f"persona-{slot}.wav", data)
        archive.writestr("script.txt", result.text)
        archive.writestr("notes.txt", notes)
    st.download_button("녹음과 원고 ZIP 받기", data=audio_zip.getvalue(), file_name="persona-comparison.zip", mime="application/zip")
