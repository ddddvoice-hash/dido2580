# 성우 김디도 목소리 AI 비서

설계: `docs/assistant/plan.md`. 지금 있는 것은 **말 다듬기 층**이에요.

- `korean_numbers.py`: 숫자·기호를 사람이 읽는 말로 풀고, 번호 덩어리 사이에 쉼표를 넣어요. 어떤 음성 엔진 앞에도 둘 수 있어요.
- 확인: `python apps/dido-assistant/tests/test_korean_numbers.py` (성우 김디도 숫자 사례 20문장)
- 한 줄 써 보기: `python apps/dido-assistant/korean_numbers.py "총 1,234,500원이 결제됐어요."`
