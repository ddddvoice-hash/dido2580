# reelgen — 정보 카드 릴스 자동 생성기

오영완(@daily5english) 계정처럼 **순위표·체크리스트·월별 정리 카드**를 세로 릴스 영상으로 자동 생산합니다.

```
주제 고르기 ──▶ Claude가 대본 작성 ──▶ 카드 렌더 ──▶ 릴스 영상 합성 ──▶ 인스타그램 게시
 (topics.py)      (content.py)       (render.py)     (video.py)        (publish.py)
```

결과물은 한 편당 폴더 하나입니다.

```
output/20261016-084700-제철회-총정리/
  script.json   대본 (고쳐서 다시 렌더 가능)
  cover.png     완성 카드 (릴스 커버, 피드 이미지로 재활용)
  reel.mp4      1080×1920, 30fps, 약 15초
  caption.txt   본문 + 근거 표기 + 해시태그
```

## 영상 구성

| 장면 | 길이 | 역할 |
|---|---|---|
| 훅 | 2초 | 제목 + 가려진 `???` 목록. 끝까지 보게 만든다 |
| 공개 | 약 7초 | 하나씩 연다. 순위는 꼴찌→1위 카운트다운, 월별 표는 1월부터 |
| 완성 | 3.5초 | 전체 카드 정지. 캡처·저장 유도 |
| 행동 유도 | 2.5초 | "나는 몇 위? 댓글로!" + 저장·공유·팔로우 |

카드 내용은 화면 위 210px, 아래 400px을 비워 인스타 UI(계정명, 캡션, 버튼)에 가리지 않게 했습니다.

## 설치

```bash
pip install -e ".[reels]"          # anthropic, pillow, pydantic
sudo apt install ffmpeg fonts-nanum  # macOS: brew install ffmpeg
export ANTHROPIC_API_KEY=sk-ant-...
```

## 쓰는 법

```bash
# API 키 없이 예시 3편 만들어 보기
python -m reelgen demo --handle my_account

# 주제 하나로 만들기
python -m reelgen make "월별 제철 과일 총정리" --handle my_account

# 영어 계정 컨셉: 항목마다 영어 표현을 붙인다
python -m reelgen make "여자들이 의외로 좋아하는 남자 특징" --english

# 아직 안 만든 주제를 골라 3편 (주제 은행이 바닥나면 Claude가 새 주제를 뽑는다)
python -m reelgen auto --count 3
python -m reelgen auto --count 5 --brainstorm --category "연애"

# 대본을 손으로 고친 뒤 다시 렌더
python -m reelgen render output/20261016-…/script.json

# 인스타그램에 올리기
python -m reelgen publish output/20261016-…
```

꾸미기 옵션 (make·auto·demo·render 공통)

| 옵션 | 설명 |
|---|---|
| `--theme pink\|sky\|mint\|lemon\|lavender` | 색 테마. 기본은 제목에 따라 자동 |
| `--illustration 그림.png` | 카드 오른쪽에 일러스트 배치 (투명 배경 PNG 권장) |
| `--bgm 음악.mp3` | 배경 음악. 끝 1.5초 페이드아웃 |
| `--order auto\|countdown\|forward` | 공개 순서 |
| `--no-video` | 카드 이미지만 |
| `--publish` | 만든 뒤 바로 게시 |

## 자동 운영 (GitHub Actions)

`.github/workflows/reels.yml`이 매일 한국시간 08:47에 돌면서

1. 안 만든 주제 하나를 골라 릴스를 만들고
2. 결과물을 Actions 아티팩트로 남기고 (14일 보관)
3. `IG_ACCESS_TOKEN`이 설정돼 있으면 바로 게시하고
4. `reels/history.json`을 커밋해 같은 주제를 다시 만들지 않습니다.

저장소 Settings → Secrets에 `ANTHROPIC_API_KEY`(필수), `IG_USER_ID`·`IG_ACCESS_TOKEN`(자동 게시용)을 넣으세요.
처음에는 토큰 없이 돌려 아티팩트로 결과를 검수하고, 품질이 안정되면 토큰을 넣어 자동 게시로 넘어가는 순서를 권합니다.

## 인스타그램 게시 준비

- 계정을 **프로페셔널(비즈니스·크리에이터)** 으로 전환하고 Facebook 페이지에 연결
- Meta 개발자 앱에서 `instagram_content_publish` 권한과 **장기 액세스 토큰** 발급
- `IG_USER_ID`(인스타 비즈니스 계정 ID), `IG_ACCESS_TOKEN` 설정
- 로컬 파일은 재개형 업로드로 바로 보냅니다. 영상을 S3·R2 같은 공개 주소에 올려 두었다면 `--video-url`을 쓰세요.
- Graph API에는 계정당 24시간 게시 한도가 있습니다.

## 품질과 안전장치

- **사실 규칙**: 대본 프롬프트가 "모르는 통계는 지어내지 말고 `source_note`에 '재미로 보는 콘텐츠'라고 적으라"고 지시합니다. 캡션 끝에 `※ 근거` 줄이 자동으로 붙습니다.
- **형식 검사**: 항목 수(3~12)와 강조어 위치를 확인하고, 틀리면 문제를 알려 주며 한 번 더 쓰게 합니다.
- **거절 처리**: 안전 분류기가 거절하면 서버 쪽 대체 모델(`fallbacks="default"`)로 재시도하고, 그래도 거절되면 그 주제만 건너뜁니다.
- **중복 방지**: `history.json`으로 만든 주제를 기록합니다.
- 기본 모델은 `claude-opus-5-5`입니다. 비용을 줄이려면 `REELGEN_MODEL=claude-sonnet-5-5`처럼 바꾸세요.

## 운영 팁

- 처음 2주는 하루 2~3편을 올리고, 인사이트의 **공유·저장·비팔로워 도달**이 높은 포맷(제목 공식, 테마, 순서)만 남기세요.
- 같은 대본으로 `cover.png`는 피드 캐러셀로, `reel.mp4`는 릴스로 두 번 씁니다.
- 일러스트는 ChatGPT·Gemini 이미지 생성으로 "파스텔 웹툰풍 인물, 투명 배경"을 만들어 `--illustration`으로 넣으면 오영완 느낌에 가까워집니다. 실존 인물이나 캐릭터 IP를 닮게 만들지는 마세요.
- 배경 음악은 저작권 문제없는 음원만 쓰세요. 인스타 앱에서 트렌드 음원을 입혀 올리는 쪽이 도달에 더 유리할 때가 많습니다.
- 인스타그램은 남의 콘텐츠를 베낀 게시물의 노출을 줄입니다. 포맷만 참고하고 주제와 문구는 직접 다듬으세요.
