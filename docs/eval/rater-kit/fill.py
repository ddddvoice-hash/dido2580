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

HERE = pathlib.Path(__file__).resolve().parent
TOKEN = re.compile(r"\{\{([^{}]+)\}\}")


def fill(text, values):
    missing = set()

    def sub(m):
        key = m.group(1).strip()
        val = str(values.get(key, "")).strip()
        if not val or "__" in val:
            missing.add(key)
            return m.group(0)
        return val

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
    out_dir = HERE / "out" / values.get("평가자_코드", "R-__")
    results, missing = {}, set()
    for tpl in sorted((HERE / "templates").glob("*.md")):
        text, miss = fill(tpl.read_text(encoding="utf-8"), values)
        results[tpl.name] = text
        missing |= miss
    if missing:
        print("아직 비어 있는 칸이 있어요. values 파일에서 채워 주세요:")
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
