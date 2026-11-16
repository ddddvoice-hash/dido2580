# EP.05 런웨이판 — 「잔향의 카나리아」 오프닝

디도 님 지시(11/17): GPT 일러스트를 그림체 기준으로, 스토리보드는 Claude의 애니마틱 구성 그대로, GPT와 상의해 Runway로 생성.

## 방식
1. **장면별 첫 장면 이미지**: Runway `gen4_image`(720:1280), 참조 이미지 = GPT 일러스트(`@poster`). 그림체·캐릭터·색감을 포스터에 맞춤
2. **5초 영상**: Runway `gen4_turbo` image_to_video, 위 이미지가 첫 장면
3. **편집**: ffmpeg으로 6컷 이음, 자막·타이틀은 후편집 글자(AI가 그린 글자 쓰지 않음), 소리는 애니마틱 원곡 가이드 트랙(코드 합성 재즈)을 박자 위에서 자름
4. **표기**: 캡션에 "영상은 Runway로 생성" 명시, isAiGenerated=true

## 샷 리스트 (애니마틱 구성 순서 그대로)

| # | 애니마틱 장면 | 이미지 프롬프트 (gen4_image, 참조 @poster) | 움직임 프롬프트 (gen4_turbo) | 자막 |
|---|---|---|---|---|
| 1 | 0:33 레조넌스 | @poster style. Close-up of the golden mecha head from @poster, visor glowing blue, golden mechanical wings half-folded behind it, purple dusk sky, cel-shaded anime, dramatic rim light | The golden wings unfold outward and light up gold, the blue eye flares, slow push-in, sparks drift upward | AI와 애니메이션 오프닝을 만들어봤다 |
| 2 | 0:05 타이틀 | @poster style. Wide view of a coastal city at sunset with a large steel suspension bridge, purple and orange sky, empty space in the upper third for a title, cel-shaded anime background art | Slow aerial push toward the bridge, clouds drifting, city lights flicker on | ECHO CANARY · 잔향의 카나리아 (후편집 타이틀) |
| 3 | 0:11 크루 | @poster style. The crew from @poster lined up shoulder to shoulder on a rooftop at dusk: dark-haired boy with goggles and red scarf in the center, silver-haired girl with headphones, navy-haired woman with glasses, pink-haired girl with goggles, silver-haired young man in a suit | Camera trucks left to right across their faces, wind moves hair and the red scarf, each looks up toward the sky | 캐릭터 다섯 명 |
| 4 | 0:42 무타 (2초 무음) | @poster style. A gigantic translucent silver whale-shaped creature whose body is made of sound-wave bars, floating above the night city, stars, eerie calm | The whale drifts slowly across the sky, its waveform body pulses once and then freezes still | 소리를 끈 2초 |
| 5 | 0:51 라이벌 | @poster style. Split composition: the golden mecha from @poster on the left facing a sleek black mecha with white slit eyes on the right, sparks between them, night sky | Both mechas lunge toward each other, camera shakes slightly, sparks burst at the center | 라이벌 |
| 6 | 0:56 엔드 카드 | @poster style. The crew seen from behind standing on the suspension bridge at dusk, a saxophone player silhouette at the railing, golden mecha silhouette in the clouds | Slow pull-back, the saxophone player sways, sunset light fades to purple | 이 오프닝에 어울리는 노래는? |

## 지킬 것
- 다른 작품명·실존 인물·로고를 프롬프트에 넣지 않는다
- 화면 속 글자는 AI 생성 금지, 후편집 글자만
- 캐릭터는 포스터 속 가상 인물만. 미성년으로 보이는 인물(카나 등)은 위험하거나 선정적인 연출 금지
- 이 판은 "코드로만 그렸다"가 아니므로 기존 EP.05 문구("그림 파일 한 장 없이")를 쓰지 않는다

## 비용 추정 (확인 필요)
이미지 6장 + 5초 영상 6개. Runway 공시 단가 기준 대략 이미지 1장 5~8 크레딧, gen4_turbo 초당 5 크레딧 → 약 180~200 크레딧. 실제 차감은 생성 후 계정에서 확인.

---

## v2 (11/17) — 포스터 일치 최우선 방식 (디도 님 승인)

원칙: AI에게 포스터를 다시 그리게 하지 않는다. **포스터 그림 자체를 첫 장면으로** 쓰고, 포스터에 없는 장면만 새로 만든다.

| # | 장면 | 첫 장면 | 움직임 프롬프트 (생김새는 쓰지 않고 움직임만) |
|---|---|---|---|
| 1 | 레조넌스 | **포스터 잘라냄** `firstframes/shot1_mecha_720x1280.jpg` (지금 포스터에서 글자 피해 잘라 둠) | Slow push-in toward the golden mecha's glowing blue eye, the eye flares brighter, faint sparks drift upward, hair moves slightly in the wind |
| 2 | 타이틀 배경 | **글자 없는 원본 필요**: 포스터 아래 도시·다리 부분 | Slow aerial drift toward the bridge, clouds move, city lights flicker on |
| 3 | 크루 | **포스터 잘라냄** `firstframes/shot3_crew_720x1280.jpg` | The boy slowly lifts his gaze to the sky, the red scarf and hair flutter in the wind, gentle camera drift to the right |
| 4 | 무타 (2초 무음) | **새로 생성** (참조: 포스터 하늘·도시 색) — 파형 몸통의 반투명 은빛 고래가 밤 도시 위에 떠 있음 | The whale drifts slowly, its body pulses once, then everything holds still |
| 5 | 라이벌 | **새로 생성** (참조: 포스터에서 금색 로봇만 잘라 사용) — 왼쪽 금색 로봇, 오른쪽 흰 눈 두 줄의 검은 로봇 | Both mechas lunge toward each other, slight camera shake, sparks burst at the center |
| 6 | 엔드 카드 | **글자 없는 원본 필요**: 포스터 전체 | Very slow pull-back revealing the whole poster scene, hair and clouds move gently |

- 영상은 5초씩 만들되 편집에서 앞쪽 3~4초만 쓴다(뒤로 갈수록 원본과 멀어짐)
- 큰 몸동작·고개 돌리기 금지(얼굴 무너짐 주원인). 카메라 이동과 바람 정도만
- 편집 때 Claude가 모든 컷의 색 분포를 포스터에 맞춤(히스토그램 매칭)·입자감 통일, 첫 장면 대비 많이 변한 컷은 자르거나 뺀다
- 새 이미지는 6장 → 2장(샷 4·5)으로 줄어든다
