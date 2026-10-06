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
NATIVE_COUNTERS = ("시간", "시", "개", "명", "살", "장", "마리", "권", "잔", "벌", "켤레", "그릇", "자루", "송이", "병", "그루", "채")


def sino(n: int) -> str:
    """한자어 수: 12500 → 만 이천오백, 1234500 → 백이십삼만 사천오백."""
    if n < 0 or n >= 10 ** 16:
        raise ValueError("읽을 수 있는 범위(0 이상 1경 미만)를 넘어요")
    if n == 0:
        return "영"
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


def decimal(s: str) -> str:
    """38.5 → 삼십팔 점 오, 0.05 → 영 점 영 오, 1,234.56 → 천이백삼십사 점 오 육."""
    whole, frac = s.split(".")
    return sino(int(whole.replace(",", ""))) + " 점 " + " ".join(DIGIT_ONE[int(c)] for c in frac)


def _int(s: str) -> int:
    return int(s.replace(",", ""))


def ordinal(n: int) -> str:
    """순서: 1 → 첫 번째, 2 → 두 번째, 21 → 스물한 번째."""
    return ("첫" if n == 1 else native(n)) + " 번째"


def _safe(fn):
    """바꾸지 못하는 숫자(너무 큰 수 등)는 원문을 그대로 남겨요. 요청 전체를 깨지 않아요."""
    def wrapper(m):
        try:
            return fn(m)
        except (ValueError, IndexError, OverflowError):
            return m.group(0)
    return wrapper


# 숫자 한 덩어리: 천 단위 쉼표는 3자리씩 맞을 때만 한 수로 봐요(1,234 → 한 수, 1,2 → 둘).
NUM = r"(?<!\d)(?:\d{1,3}(?:,\d{3})+|\d+)"
DEC = NUM + r"\.\d+"

# 단위 기호(호환 문자)는 먼저 풀어 써요: ㎞ → km, ㎏ → kg, ㎡ → m², ℃ → °C
_UNIT_CHARS = {"㎞": "km", "㎏": "kg", "㎡": "m²", "㎢": "km²", "℃": "°C"}


def _clock(h: int, mi: int, s=None) -> str:
    """시각: 0시 5분 → 영 시 오 분, 2시 30분 → 두 시 삼십 분. 0분·0초는 말하지 않아요."""
    if h > 24 or mi > 59 or (s is not None and s > 59):
        raise ValueError("시각이 아니에요")
    out = ("영" if h == 0 else native(h)) + " 시"
    if mi:
        out += " " + sino(mi) + " 분"
    if s:
        out += " " + sino(s) + " 초"
    return out


def _digit_id(m):
    """하이픈 번호: 번호·전화 말이 앞에 있거나, 0으로 시작하거나, 덩어리가 3자리 이상이면 한 자리씩.
    그 밖(20-10 같은 뺄셈·범위일 수도 있는 것)은 애매하니 원문을 남겨요."""
    parts = m.group(0).split("-")
    before = m.string[max(0, m.start() - 12):m.start()]
    if "번호" in before or "전화" in before or parts[0].startswith("0") or all(len(p) >= 3 for p in parts):
        return ", ".join(digits(p) for p in parts)
    return m.group(0)


_DATE = lambda y, mo, d: f"{sino(int(y))} 년 {MONTHS.get(int(mo), sino(int(mo)) + '월')} {sino(int(d))} 일"
_UNITS_SINO = "분|초|일|원|도|번|층|항|동|호|년|점|세"

_RULES = [
    # 날짜 2026-10-06, 2026/10/06, 2026.10.06 → 이천이십육 년 시월 육 일
    (re.compile(r"(?<![\d./-])(\d{4})([-/])(\d{1,2})\2(\d{1,2})(?![\d/-]|\.\d)"),
     lambda m: _DATE(m.group(1), m.group(3), m.group(4))),
    (re.compile(r"(?<![\d./-])(\d{4})\.(\d{1,2})\.(\d{1,2})(?!\d|\.\d)"),
     lambda m: _DATE(m.group(1), m.group(2), m.group(3))),
    # 버전 번호 2.10.3 → 이 점 십 점 삼 (점 사이를 각각 수로)
    (re.compile(r"(?<![\d.])(\d+(?:\.\d+){2,})(?![\d]|\.\d)"),
     lambda m: " 점 ".join(sino(int(p)) for p in m.group(1).split("."))),
    # 시각 00:05, 2:30:15 (분이 두 자리일 때만) → 영 시 오 분 / 두 시 삼십 분 십오 초
    (re.compile(r"(?<![\d:])(\d{1,2}):(\d{2})(?::(\d{2}))?(?![\d:])(예요)?"),
     lambda m: _clock(int(m.group(1)), int(m.group(2)), int(m.group(3)) if m.group(3) else None)
     + (("이에요" if (m.group(2) != "00" or m.group(3)) else "예요") if m.group(4) else "")),
    # 점수 0:2 → 영 대 이
    (re.compile(r"(?<![\d:])(\d{1,3}):(\d{1,3})(?![\d:])"),
     lambda m: f"{sino(int(m.group(1)))} 대 {sino(int(m.group(2)))}"),
    # 도로명 건물 번호 12-3 → 십이 다시 삼
    (re.compile(r"([로길]\s?)(\d+)-(\d+)(?![\d-])"),
     lambda m: f"{m.group(1)}{sino(int(m.group(2)))} 다시 {sino(int(m.group(3)))}"),
    # 번호(하이픈으로 이은 숫자 덩어리): 덩어리 사이에 쉼표 → 끊어 읽기
    (re.compile(r"(?<![\d.\-])(\d{2,})(?:-(\d{2,}))+(?![\d.]|-\d)"), _digit_id),
    # 대분수 1 1/2 → 일과 이분의 일
    (re.compile(r"(?<![\d/.,])(\d{1,3}) (\d+)/(\d+)(?![\d/])"),
     lambda m: f"{sino(int(m.group(1)))}과 {sino(int(m.group(3)))}분의 {sino(int(m.group(2)))}"),
    # 분수 2/5 → 오분의 이 (1/2/3 같은 것은 원문)
    (re.compile(r"(?<![\d/.])(\d+)/(\d+)(?![\d/])"), lambda m: f"{sino(int(m.group(2)))}분의 {sino(int(m.group(1)))}"),
    # 섭씨(음수 포함) -3°C → 섭씨 영하 삼 도
    (re.compile(r"(?<![\d\w])(-?)(" + DEC + "|" + NUM + r")\s*°C"),
     lambda m: "섭씨 " + ("영하 " if m.group(1) else "") + (decimal(m.group(2)) if "." in m.group(2) else sino(_int(m.group(2)))) + " 도"),
    # 넓이 단위
    (re.compile("(" + DEC + "|" + NUM + r")\s*km²"), lambda m: (decimal(m.group(1)) if "." in m.group(1) else sino(_int(m.group(1)))) + " 제곱킬로미터"),
    (re.compile("(" + DEC + "|" + NUM + r")\s*m²"), lambda m: (decimal(m.group(1)) if "." in m.group(1) else sino(_int(m.group(1)))) + " 제곱미터"),
    # 소수 + 단위/기호
    (re.compile("(" + DEC + r")\s*%"), lambda m: decimal(m.group(1)) + " 퍼센트"),
    (re.compile("(" + DEC + r")\s*kg"), lambda m: decimal(m.group(1)) + " 킬로그램"),
    (re.compile("(" + DEC + r")\s*km"), lambda m: decimal(m.group(1)) + " 킬로미터"),
    (re.compile("(" + DEC + r")\s*(도|초|점|배|원|분|일|년|번|층|호|동|항)"), lambda m: decimal(m.group(1)) + " " + m.group(2)),
    (re.compile("(" + DEC + ")"), lambda m: decimal(m.group(1))),
    # 기호 단위
    (re.compile("(" + NUM + r")\s*%"), lambda m: sino(_int(m.group(1))) + " 퍼센트"),
    (re.compile("(" + NUM + r")\s*kg"), lambda m: sino(_int(m.group(1))) + " 킬로그램"),
    (re.compile("(" + NUM + r")\s*km"), lambda m: sino(_int(m.group(1))) + " 킬로미터"),
    # 날짜: 달은 유월·시월 특수 읽기 (6 월처럼 띄어도)
    (re.compile(r"(?<!\d)(\d{1,2})\s*월"), lambda m: MONTHS.get(int(m.group(1)), sino(int(m.group(1))) + "월")),
    # 개월은 한자어
    (re.compile(r"(?<!\d)(\d+)\s*개월"), lambda m: sino(int(m.group(1))) + " 개월"),
    # 제N조·장·권… : 제삼 조, 제일 장 (고유어 단위 규칙보다 먼저)
    (re.compile(r"제\s?(\d+)\s?(조|장|권|편|절|항|과|회|관|부)"), lambda m: "제" + sino(int(m.group(1))) + " " + m.group(2)),
    # 순서: 첫 번째, 두 번째… (개수 규칙과 따로)
    (re.compile("(" + NUM + r")\s*번째"), lambda m: ordinal(_int(m.group(1)))),
    # 억·만이 섞인 금액: 1억 2500만 원 → 일억 이천오백만 원 (억 앞의 일도 읽어요)
    (re.compile(r"(?<![\d,])(\d+)억(?:\s*(\d+)만)?(?:\s*(\d+)(?!\d))?"),
     lambda m: sino(int(m.group(1))) + "억" + (" " + sino(int(m.group(2))) + "만" if m.group(2) else "")
     + (" " + sino(int(m.group(3))) if m.group(3) else "")),
    # 고유어 단위(1~99)
    (re.compile("(" + NUM + r")\s*(" + "|".join(NATIVE_COUNTERS) + ")"),
     lambda m: (native(_int(m.group(1))) if _int(m.group(1)) < 100 else sino(_int(m.group(1)))) + " " + m.group(2)),
    # 나머지 단위가 붙은 수는 한자어
    (re.compile("(" + NUM + r")\s*(" + _UNITS_SINO + ")"), lambda m: sino(_int(m.group(1))) + " " + m.group(2)),
    # 홀로 선 수 (영문자에 붙은 숫자 0X0, 3D 같은 것은 애매하니 원문)
    (re.compile(r"(?<![A-Za-z])(?<!\d-)(?<!\d/)(?<!\d:)" + NUM + r"(?![A-Za-z\d]|-\d|/\d|:\d)"), lambda m: sino(_int(m.group(0)))),
]
RULES = [(pat, _safe(fn)) for pat, fn in _RULES]


def normalize(text: str) -> str:
    """문장 속 숫자를 사람이 읽는 말로 풀어요."""
    for ch, rep in _UNIT_CHARS.items():
        text = text.replace(ch, rep)
    for pattern, repl in RULES:
        text = pattern.sub(repl, text)
    return re.sub(r"[ ]{2,}", " ", text)


if __name__ == "__main__":
    import sys
    for line in sys.argv[1:] or sys.stdin:
        print(normalize(line.rstrip("\n")))
