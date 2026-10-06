"""윈도우용 베타테스트 묶음(zip) 만들기 · 성우 김디도.

    python tools/make_beta_zip.py [출력 폴더]

apps/ 작업실 전체(테스트·녹음 파일·캐시는 뺌)에 베타 채점 페이지와 조정용 평가 묶음을 더해
`seongwoo-kimdido-beta-v0.1.zip`을 만들어요. 답 열쇠(*.key.json)와 녹음(.wav 등)은 절대 넣지 않아요.
zip 파일은 저장소에 올리지 않아요.
"""
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION = "v0.1"
TOP = f"성우김디도-베타-{VERSION}"
SKIP_DIRS = {"tests", "__pycache__", "node_modules", ".pytest_cache"}
SKIP_EXT = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm", ".pyc"}

README = f"""성우 김디도 · 인간에 가까운 AI 목소리 평가 키트 · 베타테스트 {VERSION}

[가장 쉬운 방법] 베타-채점.html 을 두 번 눌러 브라우저로 여세요.
  - 인터넷 없이 돼요. 채점은 이 컴퓨터의 브라우저에만 저장돼요.
  - 다 끝나면 맨 아래 "기록 내보내기"에서 [복사]를 눌러 운영자(성우 김디도)에게 보내 주세요.
  - 평가자 코드는 운영자에게 받은 것(예: R-K7)을 써요. 이름은 쓰지 않아요.

[작업실 전체] 작업실\\start.cmd 를 두 번 누르면 작업실이 앱 창으로 열려요(Python 필요).
  - 따뜻함 채점기에서 [평가 묶음 열기] → 평가묶음\\calibration-v0.json 을 고르면 같은 10문항을 채점할 수 있어요.
  - 낭독 코치 등 다른 도구도 함께 들어 있어요. 녹음은 이 컴퓨터 밖으로 나가지 않아요.

[알아 두기]
  - 답변 28개는 GPT가 쓴 예시예요. 실제 서비스 답변이 아니에요.
  - 위기 문항(c07)은 본문이 접혀 있어요. 읽기·건너뛰기를 먼저 골라요. 건너뛰면 '평가하지 않음'으로 남아요.
  - 힘들 때: 109 자살예방상담전화, 긴급하면 112·119.
  - 다른 평가자와 상의하지 말고 혼자 채점해 주세요. 정답(답 열쇠)은 이 묶음에 없어요.
"""

HEAD = ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"></head><body>')


def files():
    for p in sorted((ROOT / "apps").rglob("*")):
        rel = p.relative_to(ROOT / "apps")
        if p.is_dir() or SKIP_DIRS & set(rel.parts) or p.suffix.lower() in SKIP_EXT:
            continue
        yield p, f"{TOP}/작업실/{rel.as_posix()}"


def main(argv):
    out_dir = pathlib.Path(argv[1]) if len(argv) > 1 else ROOT / "dist"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"seongwoo-kimdido-beta-{VERSION}.zip"
    beta = (ROOT / "docs/beta/index.html").read_text(encoding="utf-8")
    pack = ROOT / "docs/eval/packs/calibration-v0.json"
    names = []
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{TOP}/읽어 주세요.txt", README.replace("\n", "\r\n").encode("utf-8-sig"))
        z.writestr(f"{TOP}/베타-채점.html", HEAD + beta + "</body></html>")
        z.write(pack, f"{TOP}/평가묶음/calibration-v0.json")
        for p, arc in files():
            z.write(p, arc)
        names = z.namelist()
    bad = [n for n in names if n.endswith(".key.json") or pathlib.PurePosixPath(n).suffix.lower() in SKIP_EXT]
    assert not bad, bad
    print(f"만들었어요: {out} ({len(names)}개 파일, {out.stat().st_size // 1024}KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
