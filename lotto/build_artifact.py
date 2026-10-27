"""index.html 에서 문서 뼈대(doctype/html/head/body)와 설치용 링크를 떼어 claude.ai 아티팩트용 파일을 만듭니다.

사용법: python lotto/build_artifact.py <출력 경로>
"""

import re
import sys
from pathlib import Path

PATTERNS = [
    r"<!doctype html>\n", r'<html lang="ko">\n', r"<head>\n", r'<meta charset="utf-8">\n',
    r'<meta name="viewport"[^\n]*\n', r'<meta name="theme-color"[^\n]*\n', r'<link rel="manifest"[^\n]*\n',
    r'<link rel="icon"[^\n]*\n', r"</head>\n", r"<body>\n", r"</body>\n", r"</html>\n?",
]

s = Path(__file__).with_name("index.html").read_text(encoding="utf-8")
for pat in PATTERNS:
    s, n = re.subn(pat, "", s, count=1)
    if n != 1:
        raise SystemExit(f"찾지 못함: {pat}")
Path(sys.argv[1]).write_text(s, encoding="utf-8")
print("아티팩트 파일:", sys.argv[1])
