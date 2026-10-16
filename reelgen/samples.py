"""API 키 없이 파이프라인을 돌려 볼 수 있는 예시 대본."""

from __future__ import annotations

from .models import Item, ReelScript


def seasonal_fish() -> ReelScript:
    months = [
        ("방어", "겨울 바다가 채운 진한 고소함"), ("숭어", "탱글한 식감에 깔끔한 맛"),
        ("도다리", "봄이 오면 생각나는 담백함"), ("참돔", "쫄깃함 속 은은한 단맛"),
        ("농어", "씹을수록 퍼지는 산뜻함"), ("병어", "입안에서 사르르 녹는 맛"),
        ("민어", "여름 보양 회의 대표"), ("전어", "가을 전어 머리엔 깨가 서 말"),
        ("전어", "씹을수록 고소한 가을 맛"), ("광어", "탄탄한 식감, 깔끔한 뒷맛"),
        ("대방어", "기름진 겨울 회의 시작"), ("대방어", "두툼한 한 점, 겨울 맛 가득"),
    ]
    return ReelScript(
        hook="월별로 꼭 먹어봐야 할",
        title="제철회 총정리",
        highlight="제철회",
        layout="grid",
        items=[Item(label=n, note=d, tag=f"{i + 1}월") for i, (n, d) in enumerate(months)],
        cta="저장해두고 달마다 꺼내보기",
        caption="달마다 제일 맛있는 회, 저장해두고 횟집 갈 때 꺼내 보세요!\n여러분 최애 회는 몇 월인가요? 댓글로 알려주세요 👇",
        hashtags=["제철회", "제철음식", "회", "방어", "전어", "맛집", "생활정보", "꿀팁", "저장각", "매일정보"],
        source_note="지역·해마다 제철은 조금씩 달라요",
    )


def top_traits() -> ReelScript:
    traits = [
        "담배 핀 적 없음", "술과 술자리 즐기지 않음", "게임 안 함", "주 3회 이상 운동",
        "건강 생각한 식단 관리", "매일 샤워 함", "기초화장품 바름", "외출시 선크림 바름",
        "콧털, 눈썹, 손톱 관리", "월 1회 미용실 머리커트",
    ]
    return ReelScript(
        hook="여자들이 꼽은",
        title="상위3% 남자 특징",
        highlight="상위3%",
        layout="list",
        items=[Item(label=t) for t in traits],
        cta="나는 몇 개 해당? 댓글로!",
        caption="몇 개나 해당되시나요? 🙋‍♂️\n남친·남사친한테 공유해서 체크해보세요!",
        hashtags=["남자특징", "자기관리", "연애", "연애팁", "공감", "생활정보", "저장각", "매일정보"],
        source_note="재미로 보는 콘텐츠예요",
    )


def english_ranking() -> ReelScript:
    rows = [
        ("I'm down", "나 콜이야", "좋아, 할래"), ("No cap", "진심으로", "거짓말 아님"),
        ("It slaps", "완전 좋다", "음악·음식 칭찬"), ("I'm beat", "완전 지쳤어", "피곤할 때"),
        ("My bad", "내 실수", "가볍게 사과"),
    ]
    return ReelScript(
        hook="원어민이 매일 쓰는",
        title="찐 영어표현 TOP5",
        highlight="TOP5",
        layout="list",
        items=[Item(label=e, english="", note=f"{k} · {d}", tag=f"{i + 1}위") for i, (e, k, d) in enumerate(rows)],
        cta="오늘 하나 골라 써먹기!",
        caption="교과서엔 없는데 원어민은 매일 쓰는 표현 5개 🔥\n저장하고 하루 하나씩 써보세요!",
        hashtags=["영어회화", "영어표현", "생활영어", "영어공부", "매일영어", "매일정보"],
        source_note="미국 일상 회화 기준",
    )


SAMPLES = {"seasonal_fish": seasonal_fish, "top_traits": top_traits, "english": english_ranking}
