# 디도 녹음 부스

시티 도미니언 대본 96줄을 한 줄씩 녹음하고, 올린 WAV를 바로 검사하고, 시선·동선·호흡·동작·감정 세기를 적는 정적 웹앱입니다. 서버와 외부 라이브러리가 없고, 녹음 파일은 브라우저 밖으로 나가지 않습니다.

## 여는 법 (Windows PowerShell)

```
cd ~/dido2580; if ($?) { git pull }; if ($?) { start apps/voice-studio/index.html }
```

## 하는 일

- **큐 시트:** 대본 96줄. 점 색은 통과(초록), 다시 녹음(빨강), 대기(빈 원)입니다.
- **큐 카드:** 지금 줄의 대사, 대본 감정, 감정 묶음 색, 다음에 저장할 파일 이름(`001_welcome_take01.wav`).
- **테이크:** WAV를 여러 개 한꺼번에 올리면 파일 이름 앞 세 자리로 줄을 찾아 넣고 검사합니다. 파형에 앞 10초 룸톤 자리, 말소리, 완전 0 구간이 표시됩니다.
- **연기 메모:** 시선, 동선, 호흡, 동작, 감정 세기(1–5), 메모. 이 브라우저에 자동 저장됩니다.
- **내보내기:** 연기 메모 CSV(`voice/city-dominion/annotation.csv`와 같은 열), 검사 결과 CSV(`apps/voice-check/check.js --csv`와 같은 열).

## 검사 기준

`wav-check.js`는 팀 검사기 `apps/voice-check/check.js`를 브라우저용으로 옮긴 것이라 판정이 같습니다. 반려는 V02(찢어짐), V05(뒤 여백), V08(완전 0 구간)이고, 경고는 FORMAT, PEAK, ROOM, NOISE, NAME, TRUNC, TAIL_EDGE, NOSPEECH입니다. 뜻은 `apps/voice-check/README.md`에 있습니다. 기준을 바꾸면 두 파일을 같이 바꿔야 합니다.

## 왼손 단축키

| 키 | 하는 일 |
|---|---|
| Q / E | 이전 줄 / 다음 줄 |
| 1–5 | 감정 세기 |
| Space | 마지막 테이크 듣기·멈춤 |
| A | WAV 올리기 |
| W | 시선 칸으로 (Tab으로 다음 칸) |
| C | 다음 파일 이름 복사 |
| R | 다음 반려 줄로 |
| Esc | 입력 칸에서 나오기 |

## 테스트

```
node apps/voice-studio/tests/parity.test.js; node apps/voice-studio/tests/lines.test.js; node apps/voice-studio/tests/browser.test.js
```

- `parity.test.js`: 합성 WAV 11종으로 앱 검사기와 팀 검사기의 판정·수치가 같은지 확인.
- `lines.test.js`: `lines.js`가 주석 표 96줄과 같은지 확인. 주석 표의 대사를 바꾸면 `lines.js`도 바꿔야 합니다.
- `browser.test.js`: 헤드리스 Chromium(Playwright 필요)으로 키보드 조작, 파일 올리기, 판정, 저장, CSV, 어두운 화면, 휴대폰 폭을 32가지 확인.

## 한계

- 저장은 이 브라우저(localStorage)에만 됩니다. 다른 컴퓨터로 옮기려면 CSV로 내보내 주세요.
- 소리 파일은 저장하지 않습니다. 새로고침하면 판정 기록은 남고, 듣기와 파형은 파일을 다시 올려야 나옵니다.
- 처음 열면 001번 줄에 예시 테이크(합성음)가 하나 보입니다. 진행률에 세지 않고 저장하지도 않습니다.
- 마이크로 직접 녹음하는 기능은 없습니다. 녹음 프로그램으로 녹음한 WAV를 올려 주세요.
