# 보이스 페르소나 실험실

디도님이 만든 Streamlit 앱(https://dido2580-4panybpknowxf3t9dfksqz.streamlit.app/)을 공개 화면 기준으로 평가한 뒤 Codex가 만든 **독립 대체 실행본**입니다. 원래 서버 소스는 이 저장소에 없습니다. 기존 서비스는 바꾸거나 다시 배포하지 않았습니다.

안내 문장의 사실(숫자·실패 상태·금지 행동·버튼 이름)을 지키면서, 같은 원고를 A(기본 낭독)와 B(페르소나 낭독)로 직접 녹음해 비교합니다.

## 실행 (Windows PowerShell)

```
cd ~/dido2580/apps/voice-persona; if ($?) { python -m venv .venv }; if ($?) { .venv\Scripts\pip install -r requirements.txt }; if ($?) { .venv\Scripts\streamlit run app.py }
```

## 테스트

```
cd ~/dido2580/apps/voice-persona; if ($?) { .venv\Scripts\python -m unittest discover -s tests -p "test_*.py" -v }
```

core 39개 + Streamlit AppTest 4개 = 43개 통과(2026-10-03). WAV는 16·24·32bit PCM, 32bit float, EXTENSIBLE을 받고 10분·231MB 이하입니다. A/B 비교는 말소리 구간과 쉼을 측정값으로 보여 주며 점수가 아닙니다.

## 하는 일과 하지 않는 일

- 기본값은 원문 그대로입니다. 등록된 표현만 쉽게 바꾸고, 바꾼 위치와 규칙을 기록해 다시 실행해 확인합니다.
- 숫자·시간·연락처, 따옴표 안 이름, 코드, URL, 버튼·메뉴·탭 줄은 바꾸지 않습니다.
- 입력이 바뀌면 이전 결과와 녹음을 숨깁니다.
- A/B 녹음(마이크 또는 WAV), 재생, 파일 길이, 샘플 진폭, 직접 들은 확인, 비교 메모, JSON·TXT·ZIP 저장과 검증 후 복원.
- 감정 인식, AI 재작성, TTS 합성, 자동 따뜻함·이해도 평가는 하지 않습니다. 속도·쉼은 사람이 참고하는 설계값입니다.
- 녹음은 실행 서버의 Streamlit 세션에서 처리됩니다. 자동 영구 저장은 없습니다.

## 지켜야 할 회귀 사례

원래 데모에서 `파일 업로드가 실패했습니다. 파일은 삭제되지 않았습니다. '다시 업로드'를 눌러 주세요.`를 시각장애인·오류 상황으로 바꾸자 "지문 인증 3회 실패로 계정이 잠겼습니다"가 되고, 원문에 없는 전화번호·즉시 처리 약속·버튼 위치가 붙었습니다. `tests/test_core.py`의 `test_upload_never_becomes_account_lock`이 이 사례를 지킵니다.

개발 원칙과 남은 일은 `HANDOFF.md`에 있습니다.
