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

core 52개(JS 비교 2개는 node가 있을 때) + Streamlit AppTest 6개 = 58개 통과(2026-10-03). 개발용 브라우저 검사 `tests/browser_check.py`는 Playwright가 따로 필요합니다. WAV는 16·24·32bit PCM, 32bit float, EXTENSIBLE을 받고 10분·231MB 이하입니다. A/B 비교는 말소리 구간과 쉼을 측정값으로 보여 주며 점수가 아닙니다.

## 하는 일과 하지 않는 일

- 기본값은 원문 그대로입니다. 등록된 표현만 쉽게 바꾸고, 바꾼 위치와 규칙을 기록해 다시 실행해 확인합니다.
- 숫자·시간·연락처, 따옴표 안 이름, 코드, URL, 버튼·메뉴·탭 줄은 바꾸지 않습니다.
- 입력이 바뀌면 이전 결과와 녹음을 숨깁니다.
- A/B 녹음(마이크 또는 WAV: 16·24·32bit PCM, 32bit float, 10분·48MB 이하), 재생, 파일 길이, 샘플 진폭, 직접 들은 확인, 비교 메모, JSON·TXT·ZIP 저장과 검증 후 복원.
- A/B 표: 말소리 시작·끝, 말한 시간, 쉼 개수·중간값·가장 긴 쉼을 녹음 소리 크기로 잽니다(낭독 코치와 같은 기준). B의 쉼 설계값은 참고로만 나란히 둡니다. 점수나 이해도가 아닙니다.
- 감정 인식, AI 재작성, TTS 합성, 자동 따뜻함·이해도 평가는 하지 않습니다. 속도·쉼은 사람이 참고하는 설계값입니다.
- 녹음은 실행 서버의 Streamlit 세션에서 처리됩니다. 자동 영구 저장은 없습니다.

## 지켜야 할 회귀 사례

원래 데모에서 `파일 업로드가 실패했습니다. 파일은 삭제되지 않았습니다. '다시 업로드'를 눌러 주세요.`를 시각장애인·오류 상황으로 바꾸자 "지문 인증 3회 실패로 계정이 잠겼습니다"가 되고, 원문에 없는 전화번호·즉시 처리 약속·버튼 위치가 붙었습니다. `tests/test_core.py`의 `test_upload_never_becomes_account_lock`이 이 사례를 지킵니다.

개발 원칙과 남은 일은 `HANDOFF.md`에 있습니다.

## 화면 흐름 (2026-10-03 개편)

위쪽 단계 표시(1 읽을 문장 넣기 → 2 원고 확인 → 3 두 가지로 녹음 → 4 비교하고 기록 → 5 저장)가 지금 어디인지 보여 줍니다. 예문 버튼으로 바로 해 볼 수 있고, 녹음 단계에 읽을 원고가 크게 다시 나와 위로 올라가지 않아도 됩니다. 비교 단계는 '한눈에 보기'에서 말한 시간·쉼 차이를 한 문장씩 알려 주고, 자세한 값은 표로 보여 줍니다. 기술 정보(JSON)는 맨 아래 '개발자용 정보'로 옮겼습니다.

## Streamlit Community Cloud에 올리기

1. share.streamlit.io에서 앱 설정을 엽니다(기존 앱이면 Settings, 새 앱이면 Create app).
2. 저장소 `ddddvoice-hash/dido2580`, 브랜치는 이 작업이 있는 브랜치, **Main file path는 `apps/voice-persona/app.py`**로 정합니다.
3. 패키지는 이 폴더의 `requirements.txt`(streamlit 1.50.0)를 씁니다. Python은 3.11 이상을 고르세요.
4. Community Cloud는 저장소 **맨 위의 `.streamlit/config.toml`만** 읽습니다. 그래서 같은 내용을 맨 위에도 두었고, CI가 두 파일이 같은지 확인합니다. 색이나 업로드 한도를 바꿀 때는 두 파일을 함께 바꿔 주세요.
5. Cloud는 저장소 맨 위에서 앱을 실행합니다. 2026-10-03에 같은 방식(`streamlit run apps/voice-persona/app.py`)으로 띄워 첫 화면과 원고 만들기까지 오류 없음을 확인했습니다.

API 키는 필요 없습니다. 나중에 AI를 붙이더라도 키는 Cloud의 Secrets에만 넣고 코드에는 넣지 않습니다(HANDOFF.md).
