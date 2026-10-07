"""G18b 숫자 정답표를 짧게 보여 줘요(GPT가 큰 JSON을 통째로 읽다 PC 메모리가 모자라지 않게) · 성우 김디도.

    python tools/g18b_compact.py            # 대표 확인이 필요한 구간만, 한 줄에 하나
    python tools/g18b_compact.py --all      # 모든 구간
    python tools/g18b_compact.py --q        # 대표 질문 칸도(길어요)
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main(argv):
    d = json.loads((ROOT / "docs" / "gpt" / "G18b-number-golden.json").read_text(encoding="utf-8"))
    show_all, with_q = "--all" in argv, "--q" in argv
    print("id\t분류\t숫자\t기대 읽기" + ("\t대표 질문" if with_q else ""))
    n = 0
    for it in d["items"]:
        for s in it["spans"]:
            if not show_all and not (s.get("needs_owner") or it.get("needs_owner")):
                continue
            q = s.get("owner_question") or it.get("owner_question") or ""
            row = [it["id"], s["category"], s["text"], s["expected"]] + ([q.replace("\n", " ")] if with_q else [])
            print("\t".join(row))
            n += 1
    print(f"# {n}개 구간 · 문항 {len(d['items'])}개", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
