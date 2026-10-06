"""평가자 안내문·동의서 채우기 (성우 김디도 평가 키트).

    python docs/eval/rater-kit/fill.py <채운 values 파일>
    python docs/eval/rater-kit/fill.py --check   (템플릿의 모든 칸이 values.json에 있는지만 검사)

templates/의 {{이름}} 자리를 values 파일의 값으로 바꿔 out/<평가자 코드>/에 써요.
빈 값이나 남은 {{...}}가 있으면 무엇이 비었는지 알려 주고 멈춰요.
"""
import json
import pathlib
import re
import sys
import unicodedata

HERE = pathlib.Path(__file__).resolve().parent
TOKEN = re.compile(r"\{\{([^{}]+)\}\}")
CODE = re.compile(r"R-[A-Za-z0-9]{2,8}")
PLACEHOLDERS = {"해당없음", "없음", "미정", "추후", "추후공지", "추후안내", "나중에", "tbd", "todo",
                "na", "n/a", "null", "none", "해당사항없음", "작성예정"}
ZERO_AMOUNT = re.compile(r"0+(\.0+)?(원|krw)?")
CODE_ERROR = "평가자 코드는 R- 뒤에 영문과 숫자로 입력해 주세요. 경로는 입력할 수 없어요."


def is_empty(val):
    """문자열이 아니거나, 눈에 보이는 내용이 없거나, 자리표시면 True."""
    if not isinstance(val, str):
        return True
    if "__" in val or "{{" in val or "}}" in val:
        return True
    visible = "".join(ch for ch in val
                      if not ch.isspace() and unicodedata.category(ch) not in ("Cf", "Cc", "Zs", "Zl", "Zp"))
    if not any(ch.isalnum() for ch in visible):
        return True
    compact = visible.lower()
    return compact in PLACEHOLDERS or bool(ZERO_AMOUNT.fullmatch(compact))


def fill(text, values):
    missing = set()

    def sub(m):
        key = m.group(1).strip()
        val = values.get(key, "")
        if is_empty(val):
            missing.add(key)
            return m.group(0)
        return val.strip()

    return TOKEN.sub(sub, text), missing


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    if argv[1] == "--check":
        keys = set(json.loads((HERE / "values.json").read_text(encoding="utf-8")))
        used = {m.strip() for tpl in (HERE / "templates").glob("*.md")
                for m in TOKEN.findall(tpl.read_text(encoding="utf-8"))}
        unknown = sorted(used - keys)
        if unknown:
            print("values.json에 없는 칸:", ", ".join(unknown))
            return 1
        print(f"통과: 템플릿 칸 {len(used)}개가 모두 values.json에 있어요")
        return 0
    values = json.loads(pathlib.Path(argv[1]).read_text(encoding="utf-8"))
    if not isinstance(values, dict):
        print("값이 비어 있거나 형식이 맞지 않아요. 표시된 항목을 확인해 주세요.")
        return 1
    code = values.get("평가자_코드")
    if not isinstance(code, str) or not CODE.fullmatch(code):
        print(CODE_ERROR)
        return 1
    base = (HERE / "out").resolve()
    out_dir = (base / code).resolve()
    if out_dir.parent != base:
        print(CODE_ERROR)
        return 1
    results, missing = {}, set()
    for tpl in sorted((HERE / "templates").glob("*.md")):
        text, miss = fill(tpl.read_text(encoding="utf-8"), values)
        results[tpl.name] = text
        missing |= miss
    for name, text in results.items():
        if not missing and TOKEN.search(text):
            missing.add(f"{name}에 남은 {{{{...}}}}")
    if missing:
        print("값이 비어 있거나 형식이 맞지 않아요. 표시된 항목을 확인해 주세요:")
        for k in sorted(missing):
            print(" -", k)
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in results.items():
        (out_dir / name).write_text(text, encoding="utf-8")
    print(f"만들었어요: {out_dir} ({len(results)}개 파일)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
