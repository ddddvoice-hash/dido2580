"""GPT 협의 결과가 모두 아스트라 모델로 나왔는지 검사 · 성우 김디도.

    python tools/check_astra.py

docs/gpt/ 아래 결과 파일(README 제외)마다 앞부분의 실행 기록에 `gpt-6-astra`가 있어야 해요.
없으면 파일 이름을 알려 주고 실패해요. 대표 지시: "꼭 아스트라로 협의해" (2026-10-06).
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODEL = "gpt-6-astra"


def main():
    bad, n = [], 0
    for p in sorted((ROOT / "docs" / "gpt").iterdir()):
        if p.name == "README.md" or p.suffix not in {".md", ".json"}:
            continue
        n += 1
        if MODEL not in p.read_text(encoding="utf-8")[:3000]:
            bad.append(p.name)
    if bad:
        print(f"아스트라({MODEL}) 실행 기록이 없는 GPT 결과: " + ", ".join(bad))
        return 1
    print(f"통과: GPT 결과 {n}개 모두 {MODEL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
