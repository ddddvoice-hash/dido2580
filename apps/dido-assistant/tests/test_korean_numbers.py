"""성우 김디도 숫자 읽기 사례(docs/case/numbers-case-plan.md)의 20문장으로 확인해요.

    python apps/dido-assistant/tests/test_korean_numbers.py
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from korean_numbers import native, normalize, sino  # noqa: E402

CASES = [
    # 시연 12개
    ("오전 9시 30분에 출발해요.", "오전 아홉 시 삼십 분에 출발해요."),
    ("오전 4시 25분에 시작해 2시간 10분 동안 진행해요.", "오전 네 시 이십오 분에 시작해 두 시간 십 분 동안 진행해요."),
    ("가상 전시는 10월 6일에 시작해 6개월 동안 열려요.", "가상 전시는 시월 육 일에 시작해 육 개월 동안 열려요."),
    ("총 1,234,500원이 결제됐어요.", "총 백이십삼만 사천오백 원이 결제됐어요."),
    ("예약 번호는 4719-2386이에요.", "예약 번호는 사칠일구, 이삼팔육이에요."),
    ("3시가 아니라 4시에 만나요.", "세 시가 아니라 네 시에 만나요."),
    ("몇 개 남았어요? 2개요.", "몇 개 남았어요? 두 개요."),
    ("1번, 4번, 7번 문항을 다시 보세요.", "일 번, 사 번, 칠 번 문항을 다시 보세요."),
    ("체온이 38.5도예요.", "체온이 삼십팔 점 오 도예요."),
    ("연습용 측정값은 0.05예요.", "연습용 측정값은 영 점 영 오예요."),
    ("상자 20개와 봉투 21개를 준비해요.", "상자 스무 개와 봉투 스물한 개를 준비해요."),
    ("배터리가 15% 남았고 5km 남았어요.", "배터리가 십오 퍼센트 남았고 오 킬로미터 남았어요."),
    # 검증 8개
    ("연습용 가격은 23,040원이에요.", "연습용 가격은 이만 삼천사십 원이에요."),
    ("연습용 비율은 0.08%예요.", "연습용 비율은 영 점 영 팔 퍼센트예요."),
    ("도형의 2/5만 색칠해요.", "도형의 오분의 이만 색칠해요."),
    ("4번째 상자에 카드 21장을 넣어요.", "네 번째 상자에 카드 스물한 장을 넣어요."),
    ("가상 규칙의 제4조 3항을 읽어요.", "가상 규칙의 제사조 삼 항을 읽어요."),
    ("연습용 상자의 질량은 1.06kg이에요.", "연습용 상자의 질량은 일 점 영 육 킬로그램이에요."),
    ("2시 5분, 2시 15분, 2시 50분 중에 고르세요.", "두 시 오 분, 두 시 십오 분, 두 시 오십 분 중에 고르세요."),
    ("오늘 기온은 영하 3도에서 영상 12도까지 올라가요.", "오늘 기온은 영하 삼 도에서 영상 십이 도까지 올라가요."),
]


class Numbers(unittest.TestCase):
    def test_case_sentences(self):
        for src, want in CASES:
            with self.subTest(src=src):
                self.assertEqual(normalize(src), want)

    def test_sino(self):
        self.assertEqual(sino(12500), "만 이천오백")
        self.assertEqual(sino(10000), "만")
        self.assertEqual(sino(101), "백일")
        self.assertEqual(sino(1203), "천이백삼")
        self.assertEqual(sino(100000000), "일억")  # 만만 앞의 일을 빼고, 억은 일억

    def test_native(self):
        self.assertEqual([native(n) for n in (1, 3, 20, 21, 30, 99)], ["한", "세", "스무", "스물한", "서른", "아흔아홉"])

    def test_r28_counterexamples(self):
        """GPT 아스트라 R28이 찾은 반례(예외·값 바뀜)."""
        self.assertEqual(normalize("1,234.56원이에요."), "천이백삼십사 점 오 육 원이에요.")
        self.assertEqual(normalize("1번째예요."), "첫 번째예요.")
        self.assertEqual(normalize("시험 번호는 12-12예요."), "시험 번호는 일이, 일이예요.")
        self.assertEqual(normalize("날짜는 2026-10-06이에요."), "날짜는 이천이십육 년 시월 육 일이에요.")
        self.assertEqual(normalize("10000000000000000원이에요."), "일경 원이에요.")
        self.assertEqual(normalize("20번째 줄"), "스무 번째 줄")
        for s in ("1,2,3", "12,34,5", ",,,", "1, 2, 3번", "9" * 30 + "원"):
            normalize(s)  # 예외 없이 끝나야 해요

    def test_no_digits_left(self):
        for src, _ in CASES:
            self.assertFalse(any(c.isdigit() for c in normalize(src)), src)


if __name__ == "__main__":
    unittest.main()
