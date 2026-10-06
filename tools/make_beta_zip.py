"""윈도우용 베타테스트 묶음(zip) 만들기 · 성우 김디도.

    python tools/make_beta_zip.py [출력 폴더]

apps/ 작업실(허용한 확장자만; 테스트·녹음 파일·캐시·가상환경은 뺌)에 베타 채점 페이지와 조정용 평가 묶음을 더해
`seongwoo-kimdido-beta-v0.1.zip`을 만들어요. 답 열쇠(*.key.json)와 녹음(.wav 등)은 절대 넣지 않아요.
zip 파일은 저장소에 올리지 않아요.
"""
import importlib.util
import json
import os
import pathlib
import re
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION = "v0.2"
TOP = f"성우김디도-베타-{VERSION}"
# 허용 목록: 이 확장자의 파일만 넣어요. 그 밖의 것(가상환경 속 파일, 녹음, 캐시, 설정 조각 등)은 기본으로 안 들어가요.
ALLOW_EXT = {".html", ".js", ".mjs", ".css", ".json", ".md", ".py", ".cmd", ".txt", ".toml", ".svg", ".png", ".ico"}
# 탐색 단계에서 아예 들어가지 않는 폴더(이름이 같으면 어디서든). 점(.)으로 시작하는 폴더는 .streamlit만 허용.
SKIP_DIRS = {"tests", "__pycache__", "node_modules", "venv", "env", "site-packages", "dist", "build", "scratch"}
ALLOW_DOT_DIRS = {".streamlit"}
SKIP_NAMES = {"GPT_PROMPT.md"}
FORBIDDEN_RE = re.compile(r"(\.key\.json$|(^|/)\.venv/|(^|/)venv/|pyvenv\.cfg$|(^|/)docs/gpt/|(^|/)G\d+[-\w]*\.(json|md)$|\.(wav|mp3|m4a|flac|ogg|webm|pyc)$)", re.I)


README = f"""성우 김디도 · 인간에 가까운 AI 목소리 평가 키트 · 베타테스트 {VERSION}

[가장 쉬운 방법] 베타-채점.html 을 두 번 눌러 브라우저로 여세요.
  - 인터넷 없이 돼요. 채점은 이 컴퓨터의 브라우저에만 저장돼요.
  - 다 끝나면 맨 아래 "운영자에게 보낼 것"에서 ① 채점 기록 ② 의견 기록을 각각 [복사]하거나 [파일로 저장]해 운영자(성우 김디도)에게 보내 주세요.
  - 평가자 코드는 운영자에게 받은 것(예: R-K7)을 써요. 이름은 쓰지 않아요. 한 컴퓨터를 여럿이 쓰면 사람마다 다른 브라우저 프로필을 써 주세요.

[작업실 전체] 작업실\\start.cmd 를 두 번 누르면 작업실이 앱 창으로 열려요(Python 필요).
  - 따뜻함 채점기에서 [평가 묶음 열기] → 평가묶음\\calibration-v0.json 을 고르면 같은 10문항을 채점할 수 있어요.
  - 낭독 코치 등 다른 도구도 함께 들어 있어요. 녹음은 이 컴퓨터 밖으로 나가지 않아요.

[알아 두기]
  - 답변 28개는 GPT가 쓴 예시예요. 실제 서비스 답변이 아니에요.
  - 위기 문항(c07)은 본문이 접혀 있어요. 읽기·건너뛰기·오늘은 마치기를 먼저 골라요. 건너뛰면 '평가하지 않음'으로 남아요.
  - 힘들 때: 109 자살예방상담전화, 긴급하면 112·119.
  - 다른 평가자와 상의하지 말고 혼자 채점해 주세요. 정답(답 열쇠)은 이 묶음에 없어요.
"""

HEAD = ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"></head><body>')


def load_build():
    spec = importlib.util.spec_from_file_location("beta_build", ROOT / "docs/beta/build.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def walk(base):
    """폴더를 훑으면서 제외 폴더는 아예 들어가지 않아요(허용 목록 방식)."""
    for entry in sorted(base.iterdir(), key=lambda e: e.name):
        if entry.is_dir():
            if entry.name in SKIP_DIRS or entry.name.lower().startswith(".venv"):
                continue
            if entry.name.startswith(".") and entry.name not in ALLOW_DOT_DIRS:
                continue
            yield from walk(entry)
        elif (entry.suffix.lower() in ALLOW_EXT and entry.name not in SKIP_NAMES
              and not entry.name.startswith(".") and not FORBIDDEN_RE.search(entry.name)):
            yield entry


def files():
    for p in walk(ROOT / "apps"):
        yield p, f"{TOP}/작업실/{p.relative_to(ROOT / 'apps').as_posix()}"


def check_candidates(cands, beta_html, pack_path):
    """압축을 만들기 전에 후보를 모두 검사해요. 하나라도 걸리면 압축 파일을 만들지 않아요."""
    names = [n for _, n in cands]
    bad = [n for n in names if FORBIDDEN_RE.search(n)]
    assert not bad, f"넣으면 안 되는 파일: {bad}"
    b = load_build()
    # 베타 페이지에 들어간 데이터는 허용 필드만(낱말 검사가 아니라 목록 검사)
    m = re.search(r"var DATA = (\{.*?\});\r?\n", beta_html, re.S)
    assert m, "베타 페이지에서 데이터를 찾지 못했어요"
    b.check_data(json.loads(m.group(1).replace("<\\/", "</")))
    # 평가 묶음 파일도 허용 필드만
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    assert set(pack) <= {"pack", "test_only", "notice", "items"}, set(pack)
    for it in pack["items"]:
        extra = set(it) - b.ITEM_SOURCE_KEYS
        assert not extra, (it.get("id"), sorted(extra))
        for a in it["answers"]:
            assert set(a) <= b.ANSWER_SOURCE_KEYS, (it.get("id"), sorted(set(a)))


def main(argv):
    out_dir = pathlib.Path(argv[1]) if len(argv) > 1 else ROOT / "dist"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"seongwoo-kimdido-beta-{VERSION}.zip"
    beta = (ROOT / "docs/beta/index.html").read_text(encoding="utf-8")
    pack = ROOT / "docs/eval/packs/calibration-v0.json"
    cands = list(files())
    check_candidates(cands, beta, pack)          # 1) 검사를 먼저
    fd, tmp = tempfile.mkstemp(suffix=".zip.part", dir=out_dir)
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:   # 2) 임시 이름으로 압축
            z.writestr(f"{TOP}/읽어 주세요.txt", README.replace("\n", "\r\n").encode("utf-8-sig"))
            z.writestr(f"{TOP}/베타-채점.html", HEAD + beta + "</body></html>")
            z.write(pack, f"{TOP}/평가묶음/calibration-v0.json")
            for p, arc in cands:
                z.write(p, arc)
        with zipfile.ZipFile(tmp) as z:                              # 3) 만든 압축을 다시 열어 확인
            names = z.namelist()
        bad = [n for n in names if FORBIDDEN_RE.search(n)]
        assert not bad, bad
        os.replace(tmp, out)                                         # 4) 통과한 것만 배포 이름으로
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    print(f"만들었어요: {out} ({len(names)}개 파일, {out.stat().st_size // 1024}KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
