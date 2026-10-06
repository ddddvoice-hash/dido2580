"""한국어 숫자를 사람이 읽듯 풀어 쓰기 · 성우 김디도 AI 비서.

어떤 음성 합성 엔진을 쓰든 그 앞에 두는 전처리 층이에요. 숫자를 글자로 풀고,
사람이 끊어 읽는 자리에 쉼표를 넣어 엔진이 덩어리를 나누게 해요.
규칙의 근거와 시험 문장은 docs/case/numbers-case-plan.md (성우 김디도 숫자 읽기 사례).

    >>> normalize("오전 9시 30분에 출발해요.")
    '오전 아홉 시 삼십 분에 출발해요.'
"""
import re

SINO_DIGIT = ["", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]
DIGIT_ONE = ["영", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]
SMALL_UNITS = ["", "십", "백", "천"]
BIG_UNITS = ["", "만", "억", "조", "경"]
NATIVE_ONES = ["", "한", "두", "세", "네", "다섯", "여섯", "일곱", "여덟", "아홉"]
NATIVE_TENS = ["", "열", "스물", "서른", "마흔", "쉰", "예순", "일흔", "여든", "아흔"]
MONTHS = {6: "유월", 10: "시월"}

# 고유어로 세는 단위(1~99). 그 밖의 단위는 한자어.
NATIVE_COUNTERS = ("시간", "시", "개", "명", "살", "장", "마리", "권", "잔", "벌", "켤레", "그릇")


def sino(n: int) -> str:
    """한자어 수: 12500 → 만 이천오백, 1234500 → 백이십삼만 사천오백. 경(10의 20제곱) 이상은 한 자리씩."""
    if n == 0:
        return "영"
    if n >= 10 ** 20:
        return digits(str(n))
    groups = []
    while n > 0:
        groups.append(n % 10000)
        n //= 10000
    words = []
    for i in range(len(groups) - 1, -1, -1):
        g = groups[i]
        if g == 0:
            continue
        part = ""
        for j in range(3, -1, -1):
            d = (g // 10 ** j) % 10
            if d == 0:
                continue
            # 십·백·천 앞의 '일'은 읽지 않아요(십오, 백일). 만 앞의 1도 '만'으로(일만 아님).
            part += ("" if (d == 1 and j > 0) else SINO_DIGIT[d]) + SMALL_UNITS[j]
        if i == 1 and g == 1:
            part = ""
        words.append(part + BIG_UNITS[i])
    return " ".join(words)


def native(n: int) -> str:
    """고유어 수 관형사(1~99): 20 → 스무, 21 → 스물한, 3 → 세."""
    if not 1 <= n <= 99:
        return sino(n)
    t, o = divmod(n, 10)
    if t == 2 and o == 0:
        return "스무"
    return NATIVE_TENS[t] + NATIVE_ONES[o]


def digits(s: str) -> str:
    """번호는 한 자리씩: 4719 → 사칠일구."""
    return "".join(DIGIT_ONE[int(c)] for c in s)


def ordinal(n: int) -> str:
    """번째 앞: 1 → 첫, 2 → 두, 20 → 스무, 100 이상은 한자어."""
    if n == 1:
        return "첫"
    return native(n) if n < 100 else sino(n)


def decimal(s: str) -> str:
    """38.5 → 삼십팔 점 오, 0.05 → 영 점 영 오, 1,234.56 → 천이백삼십사 점 오 육."""
    whole, frac = s.split(".")
    return sino(int(whole.replace(",", ""))) + " 점 " + " ".join(DIGIT_ONE[int(c)] for c in frac)


def _int(s: str) -> int:
    return int(s.replace(",", ""))


INT = r"(?:\d{1,3}(?:,\d{3})+|\d+)"      # 1,234,500 또는 1234500
DEC = INT + r"\.\d+"                    # 1,234.56 또는 38.5

RULES = [
    # 날짜 2026-10-06 → 이천이십육 년 시월 육 일
    (re.compile(r"(?<![\d.-])(\d{4})-(\d{1,2})-(\d{1,2})(?![\d-])"),
     lambda m: f"{sino(int(m.group(1)))} 년 {MONTHS.get(int(m.group(2)), sino(int(m.group(2))) + '월')} {sino(int(m.group(3)))} 일"),
    # 번호(하이픈으로 이은 숫자 덩어리): 덩어리 사이에 쉼표 → 끊어 읽기
    (re.compile(r"(?<![\d.])(\d{2,})(?:-(\d{2,}))+(?![\d.])"),
     lambda m: ", ".join(digits(p) for p in m.group(0).split("-"))),
    # 분수 2/5 → 오분의 이
    (re.compile(r"(\d+)/(\d+)"), lambda m: f"{sino(int(m.group(2)))}분의 {sino(int(m.group(1)))}"),
    # 소수 + 단위/기호
    (re.compile("(" + DEC + r")\s*%"), lambda m: decimal(m.group(1)) + " 퍼센트"),
    (re.compile("(" + DEC + r")\s*kg"), lambda m: decimal(m.group(1)) + " 킬로그램"),
    (re.compile("(" + DEC + r")\s*km"), lambda m: decimal(m.group(1)) + " 킬로미터"),
    (re.compile("(" + DEC + r")\s*(도|초|점|배|원)"), lambda m: decimal(m.group(1)) + " " + m.group(2)),
    (re.compile("(" + DEC + ")"), lambda m: decimal(m.group(1))),
    # 기호 단위
    (re.compile("(" + INT + r")\s*%"), lambda m: sino(_int(m.group(1))) + " 퍼센트"),
    (re.compile("(" + INT + r")\s*kg"), lambda m: sino(_int(m.group(1))) + " 킬로그램"),
    (re.compile("(" + INT + r")\s*km"), lambda m: sino(_int(m.group(1))) + " 킬로미터"),
    # 날짜: 달은 유월·시월 특수 읽기
    (re.compile(r"(\d{1,2})월"), lambda m: MONTHS.get(int(m.group(1)), sino(int(m.group(1))) + "월")),
    # 개월은 한자어
    (re.compile(r"(\d+)\s*개월"), lambda m: sino(int(m.group(1))) + " 개월"),
    # 조·항
    (re.compile(r"제(\d+)조"), lambda m: "제" + sino(int(m.group(1))) + "조"),
    # 순서: 1번째 → 첫 번째
    (re.compile("(" + INT + r")\s*번째"), lambda m: ordinal(_int(m.group(1))) + " 번째"),
    # 고유어 단위(1~99)
    (re.compile("(" + INT + r")\s*(" + "|".join(NATIVE_COUNTERS) + r")"),
     lambda m: (native(_int(m.group(1))) if _int(m.group(1)) < 100 else sino(_int(m.group(1)))) + " " + m.group(2)),
    # 나머지 단위가 붙은 수는 한자어
    (re.compile("(" + INT + r")\s*(분|초|일|원|도|번|층|항|동|호|년|점)"), lambda m: sino(_int(m.group(1))) + " " + m.group(2)),
    # 홀로 선 수
    (re.compile(INT), lambda m: sino(_int(m.group(0)))),
]


def normalize(text: str) -> str:
    """문장 속 숫자를 사람이 읽는 말로 풀어요."""
    for pattern, repl in RULES:
        text = pattern.sub(repl, text)
    return re.sub(r"[ ]{2,}", " ", text)


if __name__ == "__main__":
    import sys
    for line in sys.argv[1:] or sys.stdin:
        print(normalize(line.rstrip("\n")))
