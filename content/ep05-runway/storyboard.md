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
