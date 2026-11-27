"""레시피 제목·조리 순서를 표준 조리 문장으로 다시 쓰는 모듈.

무엇을 하는가
 1) 제목: 블로거·방송 이름, 홍보성 수식어, 사이트식 꼬리말을 걷어내고
    '음식 이름'만 남긴다. ("백종원 7분김치찌개 황금레시피" → "7분 김치찌개")
 2) 조리 순서: 개인적인 감상·홍보 문구·이모티콘·출처를 지우고,
    모든 문장을 '~하세요 / ~해 주세요' 형태의 짧은 표준 조리 문장으로 바꾼다.
 3) 같은 재료를 두 번 말하거나, 문장이 토막 난 곳은 앞뒤 문장과 합쳐 읽히게 만든다.

원칙
 - 재료·분량·시간·불 세기 같은 사실 정보는 그대로 둔다.
 - 문장의 표현만 우리 문체로 다시 쓴다 (원문 문장을 그대로 옮기지 않는다).
 - 결과는 결정적(deterministic)이다. 같은 입력이면 항상 같은 출력이 나온다.

이 모듈은 tools/build_recipes.py 에서 불러 쓴다.
"""

import re
import unicodedata

# ---------------------------------------------------------------------------
# 1. 지워야 할 이름·문구
# ---------------------------------------------------------------------------

# 블로거·방송·요리 연구가 이름 (제목과 조리 순서 양쪽에서 제거)
PERSON_WORDS = [
    "백종원", "백선생", "백주부", "이연복", "최현석", "미카엘", "승우아빠", "승우",
    "수미", "김수미", "류수영", "편스토랑", "집밥백선생", "집밥 백선생", "삼시세끼",
    "윤스테이", "수미네반찬", "수미네 반찬", "요리비책", "쿡방", "냉부해", "냉장고를 부탁해",
    "만개의레시피", "만개", "오늘의 요리", "집밥연구소", "요리하는 남자", "쿠킹클래스",
    "대가", "쉐프", "셰프", "이상순", "이효리", "효리네민박", "비룡", "요리다나와",
    "효리네", "효리", "빛이난다", "박나래", "정호영", "성시경", "김풍", "안성재", "최강록", "백일섭", "이경규",
    "강호동", "이영자", "홍석천", "최자", "쯔양", "문세윤", "김종민", "전현무",
]

# 브랜드·제품 이름 (조리 순서에서만 제거 — 재료 이름까지 지우면 내용이 사라진다)
BRAND_WORDS = [
    "오뚜기", "청정원", "비비고", "종가집", "풀무원", "곰곰", "하림", "대상", "백설",
    "삼양", "농심", "오리온", "롯데", "매일", "서울우유", "남양", "CJ", "해표", "사조",
    "동원", "한성", "스팸클래식", "청우", "샘표", "새미네", "맥코믹", "하인즈", "KFC",
    "맥도날드", "버거킹", "이마트", "홈플러스", "쿠팡", "마켓컬리",
]

# 사이트 안내 문구·홍보 문구
SITE_PHRASES = [
    "이미지크게보기", "텍스트만보기", "이미지작게보기", "원본보기", "이미지 크게",
    "동영상", "바로가기", "더보기", "레시피 보기", "재료 준비", "요리 순서",
    "구매", "배송", "광고", "협찬", "제공받", "공동구매", "이벤트", "구독", "팔로우",
    "블로그", "인플루언서", "업체", "판매", "주문", "전화", "카톡", "링크", "상품",
    "황금레시피", "레시피", "꿀팁", "비법",
]

# 제목에서 걷어낼 수식어 (음식 이름과关系 없는 말)
TITLE_NOISE = [
    "황금레시피", "황금 레시피", "초간단", "초 스피드", "초스피드", "간단", "쉽게",
    "쉬운", "실패 없는", "실패없는", "실패없이", "맛보장", "맛 보장", "인생", "최고",
    "강추", "추천", "비법", "꿀팁", "포인트", "핵심", "정석", "완벽", "대박", "극찬",
    "만드는 법", "만드는법", "만들기", "끓이는 법", "끓이는법", "끓이기", "만드는 방법",
    "만드는방법", "레시피", "요리", "집밥", "혼밥", "도시락 메뉴", "도시락메뉴",
    "후기", "리뷰", "매콤한", "얼큰한", "담백한", "고소한", "칼칼한", "시원한",
    "황금비율", "황금 비율", "끓이법", "끓이는법", "만들법", "하는법",
    "진한", "든든한", "간단한", "쉬운", "정말", "진짜", "너무", "정말로",
]

# 제목에서 지울 조합 표현 (조사가 붙은 형태까지)
TITLE_PHRASE_NOISE = [
    "로 만든", "으로 만든", "로만든", "으로만든", "만든", "표 ", "스타일", "버전",
    "응용", "변형", "기본", "기초", "정말", "진짜", "너무", "완전", "아주",
]

# 제목 맨 앞에 붙는 맛 수식어
TITLE_ADJ = [
    "매콤", "매콤한", "얼큰", "얼큰한", "칼칼", "칼칼한", "담백", "담백한",
    "고소", "고소한", "시원", "시원한", "진한", "든든", "든든한", "간단", "간단한",
    "쉬운", "쉽게", "정갈한", "정갈", "바삭", "바삭한", "쫄깃", "쫄깃한",
    "부드러운", "부드럽", "달콤", "달콤한", "새콤", "새콤한", "알싸한", "알싸",
    "구수한", "구수", "깔끔한", "깔끔", "풍미", "풍미가득", "초간단", "간편",
]

# 제목이 이렇게 끝나면 잘라 낸다
TITLE_TAIL = [
    "만드는 법", "만드는법", "만들기", "끓이는 법", "끓이는법", "레시피", "황금레시피",
    "만드는 방법", "조리법", "비법", "꿀팁", "후기", "완성", "도전", "입니다", "이에요",
    "예요", "합니다", "했어요", "먹어요", "좋아요", "최고", "대박",
    "맛있어요", "맛있다", "맛있네요", "은 덤", "는 덤", "덤",
]

# 조리 문장에서는 지우면 안 되는, 요리에 실제로 쓰이는 '대가' 같은 낱말
KEEP_WORDS = {"대가", "셰프", "쉐프"}

# 문장이 이 낱말로 끝나면 감상·설명 문장으로 보고 버린다
SKIP_ENDINGS = (
    "좋아요", "좋습니다", "좋아", "맛있어요", "맛있습니다", "맛있다", "맛있네요",
    "쉽습니다", "쉬워요", "어렵지 않아요", "어렵지않아요", "어렵습니다", "같아요",
    "같습니다", "있습니다", "있어요", "없습니다", "없어요", "입니다", "이에요",
    "예요", "아니에요", "아닙니다", "됩니다", "되요", "돼요", "필요해요", "필요합니다",
    "중요합니다", "중요해요", "포인트에요", "포인트입니다", "비법이에요", "비법입니다",
    "꿀팁이에요", "꿀팁입니다", "거든요", "답니다", "잖아요", "네요", "군요", "죠",
    "는데요", "나요", "다죠", "성공", "완성이에요", "끝이에요", "끝입니다",
)

# 문장 첫머리의 군더더기
FILLER_HEAD = [
    "제일 먼저", "제일먼저", "가장 먼저", "우선", "먼저", "이제", "그다음", "그 다음",
    "다음으로", "그리고", "그럼", "그러면", "자,", "자 ", "이렇게", "요렇게", "저렇게",
    "마지막으로", "끝으로", "다시", "또", "그 후", "그후", "그 뒤", "그뒤",
]

# 자주 나오는 오타·비표준 표기
TYPO_FIX = [
    ("담궈", "담가"), ("담구", "담가"), ("깨끗히", "깨끗이"), ("설겆이", "설거지"),
    ("되요", "돼요"), ("안되요", "안 돼요"), ("웬지", "왠지"), ("오랫만", "오랜만"),
    ("볼게", "볼에"), ("볼게요", "볼에"), ("믹서기", "믹서기"), ("후라이팬", "팬"),
    ("프라이팬", "팬"), ("달구어진", "달궈진"), ("끓어오르면", "끓어오르면"),
    ("적당히", "적당히"), ("타지않게", "타지 않게"), ("골고루", "골고루"),
    ("조물조물", "조물조물"), ("숭숭", "송송"), ("쫑쫑", "송송"), ("짤랑", "살짝"),
    ("살짝살짝", "살짝"), ("듬뿍듬뿍", "듬뿍"),
]

# 재료별 '포인트'를 우리 말로 다시 쓴 안내 (분량·시간은 그대로 두고 문장만 바꾼다)
ACTION_WORDS = [
    "볶아", "볶", "끓여", "끓이", "넣어", "넣", "썰어", "썰", "다져", "다지",
    "섞어", "섞", "부쳐", "부치", "구워", "굽", "데쳐", "데치", "삶아", "삶",
    "튀겨", "튀기", "졸여", "졸이", "무쳐", "무치", "버무려", "버무리", "절여", "절이",
    "헹궈", "헹구", "담아", "담", "올려", "올리", "뿌려", "뿌리", "끼얹어", "끼얹",
    "부어", "붓", "풀어", "풀", "개어", "개", "말아", "말", "잡아", "잡",
    "재워", "재우", "간해", "간하", "익혀", "익히", "식혀", "식히", "불려", "불리",
    "빼", "걷어", "거둬", "걸러", "갈아", "갈", "으깨", "으깨", "찌", "돌려", "돌리",
    "둘러", "두르", "발라", "바르", "싸", "비벼", "비비", "젓", "들이", "붙여", "붙이",
    "떼어", "떼", "흔들어", "흔들", "눌러", "누르", "펴", "펴", "채워", "채우",
    "덮어", "덮", "열어", "열", "닫아", "닫", "씻어", "씻", "닦아", "닦",
    "손질해", "손질하", "준비해", "준비하", "완성해", "완성하", "마무리해", "마무리하",
    "데워", "데우", "녹여", "녹이", "뜨거", "차가", "섞이", "우려", "우리", "배어",
    "베어", "배", "베", "잘라", "자르", "찢어", "찢", "짜", "짜내", "걸",
]


def _clean_spaces(text):
    text = re.sub(r"\s+", " ", text or "")
    return text.strip(" ,·:;-\u00b7")


def strip_emoji(text):
    """이모지·이모티콘·특수문자를 남기지 않는다."""
    text = text or ""
    keep = {"~", "·", "(", ")", "[", "]", "%", "+", "/", "-", ".", ","}
    out = []
    for ch in text:
        cat = unicodedata.category(ch)
        if ch in keep:
            out.append(ch)
        elif cat[0] in ("S", "C", "M"):
            out.append(" ")
        else:
            out.append(ch)
    text = "".join(out)
    text = re.sub(r"[♬♪♡♥★☆→←↑↓⇒※]", " ", text)
    text = re.sub(r"(\^\^|ㅎㅎ+|ㅋㅋ+|ㅠㅠ+|;\)|:\)|:-\)|:D)", " ", text)
    return text


def strip_names(text, include_brand=True):
    for name in PERSON_WORDS:
        if name in KEEP_WORDS:
            continue
        text = text.replace(name, " ")
    if include_brand:
        for name in BRAND_WORDS:
            text = text.replace(name, " ")
    return text


def strip_site_phrases(text, keep=()):
    for phrase in SITE_PHRASES:
        if phrase in keep:
            continue
        text = text.replace(phrase, " ")
    return text


def fix_typos(text):
    for wrong, right in TYPO_FIX:
        text = text.replace(wrong, right)
    return text


def squeeze_lists(text):
    """'양파, 당근, 대파' 같은 나열은 그대로 두고, 쉼표 뒤 공백만 정리한다."""
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r",\s*,", ",", text)
    return _clean_spaces(text)


def clean_step_text(raw):
    """조리 단계 한 줄에서 화면 문구·이름·이모티콘을 걷어낸다."""
    text = raw or ""
    text = re.sub(r"<[^>]*>", " ", text)
    text = (text.replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("\u200b", "").replace("\ufeff", "").replace("\xa0", " "))
    text = re.sub(r"^[\s*•·○●▶►\-–—①-⑳0-9.\[\]]+", "", text)
    text = strip_emoji(text)
    text = strip_names(text)
    text = fix_typos(text)
    text = re.sub(r"(저는|제가|저희|내가|제 입맛에는|제 입맛엔|제 기준엔|제 기준으로)",
                  " ", text)
    text = re.sub(r"(^|[,.!?]\s*)전\s+", r"\1", text)
    text = re.sub(r"(^|[,.!?]\s*)제\s+(?=[가-힣])", r"\1", text)
    text = strip_site_phrases(text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"www\.\S+", " ", text)
    text = re.sub(r"[!?]{2,}", ".", text)
    text = re.sub(r"[!?]", ".", text)
    text = re.sub(r"(?:\.\s*){2,}", ". ", text)
    text = re.sub(r"~{1,}", " ", text)
    text = squeeze_lists(text)
    return _clean_spaces(text)


# ---------------------------------------------------------------------------
# 2-1. 제목 다듬기
# ---------------------------------------------------------------------------

# 음식 이름처럼 끝나는 말 (제목에서 이 말이 마지막에 오면 앞 수식어를 덜어 낸다)
DISH_TAIL = (
    "볶음", "찌개", "전골", "조림", "구이", "무침", "부침", "튀김", "나물", "김치",
    "국", "탕", "밥", "죽", "면", "국수", "수제비", "만두", "떡볶이", "라볶이",
    "파스타", "스파게티", "리조또", "카레", "스프", "샐러드", "덮밥", "김밥", "주먹밥",
    "전", "찜", "스테이크", "커리", "오믈렛", "토스트", "샌드위치", "피자", "그라탕",
    "우동", "냉면", "칼국수", "짬뽕", "탕수육", "깍두기", "장아찌", "피클", "쌈",
    "볶음면", "찌", "떡",
)

# 제목에서 통째로 지우는 낱말 (수식어·안내말)
TITLE_TOKEN_NOISE = set(TITLE_NOISE + TITLE_ADJ + [
    "꿀맛", "황금", "레시피", "방법", "순서", "비율", "양념", "소스",
    "만능", "기본", "초보", "누구나", "한번", "한 번", "다시", "오늘", "우리집",
    "집에서", "혼자", "간단히", "쉽게", "맛있게", "예쁘게", "이쁘게", "정성껏",
    "실패", "성공", "비주얼", "맛", "폼", "완성", "요리", "음식", "메뉴", "한그릇",
    "법", "st",
])

# 수식어처럼 쓰인 낱말 (음식 이름 앞에서 덜어 낸다)
VERBISH_TAIL = ("게", "는", "한", "된", "할", "하는", "스러운", "다운", "같은", "듯한",
                "려", "켜", "이면", "으면", "라면", "정도", "만큼")

DISH_EXACT = {"탕", "국", "밥", "면", "전", "죽", "찌", "떡", "만두", "김치"}
DISH_NOT = {"설탕", "간장", "소금", "후추", "물엿", "식초"}


def _is_dish(word):
    """낱말이 음식 이름처럼 끝나는지 (설탕·간장 같은 재료 이름은 제외)."""
    if word in DISH_NOT or len(word) < 2:
        return False
    if word in DISH_EXACT:
        return True
    for tail in DISH_TAIL:
        if tail and word.endswith(tail) and len(word) > len(tail):
            return True
    return False


COMMENT_TOKEN = re.compile(
    r"(맛있|좋아|고소|간단|쉬워|쉽|알려|즐겨|없어|드려|드릴|해요|어요|아요|께요|네요|죠|"
    r"좋네|최고|대박|해$|요$)")


def _comment_like(word):
    return bool(COMMENT_TOKEN.search(word)) and len(word) <= 12


def _title_core(segment):
    text = segment
    # 괄호 설명·따옴표·기호 제거
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"【[^】]*】", " ", text)
    text = re.sub(r"[\"'“”‘’&♬♪★☆→·#+]", " ", text)
    text = re.sub(r"[!?~]+", " ", text)
    for phrase in TITLE_PHRASE_NOISE:
        text = text.replace(phrase, " ")

    words = []
    for word in re.split(r"[\s,/]+", text):
        word = word.strip(" ,·:;-.")
        if not word:
            continue
        # 꼬리말이 붙은 낱말은 꼬리말을 떼어 낸다 ("레시피로" → "", "만들기" → "")
        bare = word
        changed = True
        while changed:
            changed = False
            for tail in sorted(TITLE_TAIL, key=len, reverse=True):
                if bare.endswith(tail) and len(bare) > len(tail):
                    bare = bare[: -len(tail)].strip()
                    changed = True
                    break
        if bare in TITLE_TOKEN_NOISE or bare == "":
            continue
        if re.fullmatch(r"[0-9]+(분|인분|개|가지|컵|큰술|스푼|g|ml|L)?", bare):
            continue
        if re.match(r"^[0-9]+", bare):
            continue
        if bare.endswith(VERBISH_TAIL) and len(bare) > 1:
            continue
        if bare.endswith(("에서", "부터", "까지", "으로", "으로도", "로는", "보다", "처럼")) and len(bare) > 2:
            continue
        words.append(bare)

    if not words:
        return ""
    # 끝에 붙은 감상 표현(맛있어요·좋아해요·알려드릴께요 …)은 덜어 낸다
    while words and _comment_like(words[-1]):
        words.pop()
    while len(words) > 1 and _comment_like(words[0]):
        words.pop(0)
    if not words:
        return ""

    # 음식 이름처럼 끝나는 낱말을 기준으로, 그 뒤의 잡다한 말과 앞의 다른 음식 이름은 버린다
    for i in range(len(words) - 1, -1, -1):
        if _is_dish(words[i]):
            earlier = [k for k in range(i) if _is_dish(words[k])]
            start = earlier[-1] + 1 if earlier else 0
            words = words[start: i + 1]
            break
    while len(words) > 3:
        words.pop(0)
    while len(" ".join(words)) > 18 and len(words) > 1:
        words.pop(0)
    return " ".join(words).strip(" ,·:;-")


def clean_title(name):
    """제목에서 이름·수식어·꼬리말을 걷어내고 음식 이름만 남긴다."""
    title = name or ""
    title = strip_emoji(title)
    title = strip_names(title)
    title = strip_site_phrases(title)
    title = re.sub(r"https?://\S+", " ", title)
    title = re.sub(r"^\s*(그|이|저|우리|나의|내)\s+", " ", title)
    title = re.sub(r"^[0-9]+\.\s*", "", title)
    title = re.sub(r"\.{2,}", " ", title)

    # '::' '|' ' - ' '/' 같은 구분자로 나눠, 남는 조각 중 첫 번째를 음식 이름으로 본다
    segments = [seg for seg in re.split(
        r"\s*(?:::?\s*|\||｜|\s+-\s+|//|/|…)\s*", title) if seg.strip()]
    # 쉼표로 이어 붙은 긴 제목은 첫 조각이 음식 이름인 경우가 많다
    if len(segments) == 1 and len(segments[0]) > 20 and "," in segments[0]:
        segments = [segments[0].split(",")[0]] + segments[0].split(",")[1:]

    segments = [re.sub(r"^(에|은|는|이|가|을|를|의|와|과|도|만|로|으로|에서)\s+", "", seg.strip())
                for seg in segments]
    candidates = [_title_core(seg) for seg in segments]
    candidates = [c for c in candidates if len(c) >= 2]
    if not candidates:
        return ""
    good = [c for c in candidates
            if not re.search(r"(어요|습니다|입니다|이에요|예요|하세요|주세요|좋아|맛있|쉽|까요|네요|죠)$", c)]
    return (good or candidates)[0]


# ---------------------------------------------------------------------------
# 3. 문장을 '~하세요'체로 바꾸는 규칙
# ---------------------------------------------------------------------------

HANGUL_START, HANGUL_END = 0xAC00, 0xD7A3
JONG_NIEUN = 4      # 종성 'ㄴ' 번호
JONG_RIEUL = 8      # 종성 'ㄹ' 번호

# 활용이 불규칙한 동사 어간 → 명령형 어간
IRREGULAR = {
    "굽": "구우",   # 굽다 → 구우세요
    "붓": "부",     # 붓다 → 부으세요
    "젓": "저",     # 젓다 → 저으세요
    "긋": "그",
    "잇": "이",
    "줍": "주우",
    "돕": "도우",
    "누": "누",     # 눕다 는 요리에서 거의 쓰이지 않는다
}

# ㄹ 받침이 ㄴ 앞에서 줄어든 형태 (썬 ← 썰, 만든 ← 만들 …)
RIEUL_STEM = {
    "써": "썰", "만드": "만들", "아": "알", "부": "불", "풀어": "풀",
    "갈아": "갈", "말아": "말", "밀어": "밀", "빨아": "빨", "살아": "살",
    "팔아": "팔", "놀아": "놀", "돌아": "돌", "흘러": "흘", "늘어": "늘",
    "다": "달", "따": "딸", "차": "찰", "재": "잴", "저": "절",
}

# 자동사 (명령형 대신 '~도록 하세요')
INTRANSITIVE = (
    "익", "되", "끓", "타", "마르", "식", "불", "우러나", "배", "베", "잦아들",
    "눌어붙", "부풀", "뜨", "흐르", "녹", "엉기", "굳", "생기", "걸쭉해지",
    "노릇해지", "투명해지", "흐물러지", "퍼지", "떠오르", "솟", "넘치", "줄어",
    "여물", "부드러워지", "단단해지", "딱딱해지", "노릇해", "갈색이", "놀",
)

# 문장이 이렇게 끝나면 감상·설명 문장 → 버린다
COMMENTARY_END = (
    "좋아요", "좋습니다", "좋아", "맛있어요", "맛있습니다", "맛있다", "맛있네요",
    "쉽습니다", "쉬워요", "어렵지 않아요", "어렵지않아요", "어렵습니다", "같아요",
    "같습니다", "있습니다", "있어요", "없습니다", "없어요", "아니에요", "아닙니다",
    "중요합니다", "중요해요", "거든요", "답니다", "잖아요", "네요", "군요", "죠",
    "데요", "나요", "더라구요", "구요", "겠습니다", "다죠",
    "포인트에요", "비법이에요", "돼요", "되요", "괜찮아요", "가능해요", "가능합니다",
    "볼까요", "까요", "을까요", "ㄹ까요", "죠?", "있을 거예요", "될 거예요",
)

# 요리 동사 어간으로 끝나는지 판별할 때 쓰는 목록
VERB_STEMS = (
    "하", "되", "볶", "끓이", "끓", "넣", "썰", "다지", "섞", "부치", "굽", "데치",
    "삶", "튀기", "졸이", "졸", "무치", "버무리", "절이", "헹구", "담그", "담",
    "올리", "뿌리", "끼얹", "붓", "풀", "개", "말", "잡", "재우", "간하", "익히",
    "식히", "불리", "빼", "걷어", "거르", "갈", "으깨", "찌", "돌리", "두르",
    "바르", "싸", "비비", "젓", "붙이", "떼", "흔들", "누르", "펴", "채우", "덮",
    "열", "닫", "씻", "닦", "손질하", "준비하", "완성하", "마무리하", "데우",
    "녹이", "우리", "자르", "찢", "짜", "올리", "내리", "섞이", "어우러지",
    "우러나", "잦아들", "눌어붙", "부풀", "흐르", "엉기", "굳", "생기", "퍼지",
    "넘치", "줄어", "여물", "타", "마르", "식", "익", "놓", "두", "높이",
)


PARTICLE_END = ("을", "를", "에", "로", "은", "는", "이", "가", "도", "와", "과",
                "서", "만", "께", "께서", "에서", "으로")


def _append_haseyo(head):
    """'간을' + '하세요' 처럼 조사로 끝나면 띄어 쓴다."""
    last = head.split(" ")[-1]
    if last.endswith(PARTICLE_END):
        return head + " 하세요"
    return head + "하세요"


def _verb_like(word):
    if not word:
        return False
    for stem in VERB_STEMS:
        if word.endswith(stem):
            return True
    return False


# 그대로 두어도 되는 명령형 끝맺음
POLITE_END = ("하세요", "주세요", "으세요", "세요", "보세요")

# 정형 문장 (그대로 치환)
TAIL_RULES = [
    (("해 주시면 됩니다", "해주시면 됩니다", "해 주시면 돼요", "해주시면 돼요",
      "하시면 됩니다", "하시면 돼요", "하시면 되요", "하면 됩니다", "하면 돼요",
      "하면 되요", "해도 좋아요", "해도 좋습니다", "해도 괜찮아요", "해도 돼요",
      "해 주시기 바랍니다", "하시기 바랍니다"), "하세요"),
    (("주시면 돼요", "주시면 됩니다", "주면 돼요", "주면 됩니다"), "주세요"),
    (("주시구요", "주시고요", "주시고", "주시면", "주시길", "주십시오", "주십시요",
      "주세용", "주셔요", "주셔", "주시는", "주심", "주네요", "주거든요", "주죠",
      "줍니다", "줘요", "주렴"), "주세요"),
    (("완성입니다", "완성됩니다", "완성이에요", "완성이다", "완성이다!", "완성",
      "끝입니다", "끝이에요", "끝"), "완성됩니다"),
]

# '~면 되요 / ~면 됩니다' → '~면 됩니다'
_OK_TAIL = ("면 되요", "면 돼요", "면 됩니다", "면 되고요")


def _syllable_parts(ch):
    code = ord(ch)
    if not (HANGUL_START <= code <= HANGUL_END):
        return None
    idx = code - HANGUL_START
    return idx // 588, (idx % 588) // 28, idx % 28      # 초성, 중성, 종성


def _compose(cho, jung, jong=0):
    return chr(HANGUL_START + (cho * 21 + jung) * 28 + jong)


def _has_jong(ch):
    parts = _syllable_parts(ch)
    return bool(parts and parts[2])


def _jong(ch):
    parts = _syllable_parts(ch)
    return parts[2] if parts else 0


def _imperative(stem):
    """어간 '볶' / '끓이' / '썰' / '굽' → '볶으세요' / '끓이세요' / '썰으세요' / '구우세요'."""
    if not stem:
        return ""
    last = stem[-1]
    if last in IRREGULAR:
        return stem[:-1] + IRREGULAR[last] + "세요"
    if last in "하" and len(stem) >= 1:
        return stem + "세요"
    if _has_jong(last):
        return stem + "으세요"
    return stem + "세요"


def _intransitive(stem):
    tail = stem.split(" ")[-1]
    for verb in INTRANSITIVE:
        if tail.endswith(verb):
            return True
    return False


def _join_last(sentence, new_last):
    """마지막 어절만 바꿔 문장을 다시 만든다."""
    parts = sentence.split(" ")
    return " ".join(parts[:-1] + [new_last]) if len(parts) > 1 else new_last


def _declarative_to_imperative(sentence):
    """'~한다 / ~는다 / ~ㅂ니다 / ~습니다 / ~았어요' 같은 서술형을 명령형으로."""
    s = sentence
    # '~됩니다' → '~되도록 하세요' (완성됩니다 는 그대로)
    if s.endswith("됩니다"):
        head = s[:-3].rstrip()
        if not head:
            return None
        if head.endswith("완성"):
            return None          # '완성됩니다'는 그대로 두고 정형 규칙에서 처리
        return _clean_spaces(head + " 되도록 하세요")
    # '~입니다 / ~이에요' : 앞말이 동사 어간이면 명령형, 아니면 설명문
    for tail in ("입니다", "이에요"):
        if s.endswith(tail):
            head = s[: -len(tail)].rstrip()
            if not head:
                return None
            last = head.split(" ")[-1]
            if last.endswith("끓"):
                return _clean_spaces(_join_last(head, "끓이세요"))
            if _verb_like(last):
                return _imperative_sentence(head)
            return None
    # 과거형: 넣었어요 → 넣으세요 / 했습니다 → 하세요
    for past in ("았습니다", "었습니다", "였습니다", "했습니다", "했어요", "했네요",
                 "았어요", "었어요", "였어요", "았고", "었고"):
        if s.endswith(past):
            stem = s[: -len(past)].rstrip()
            if not stem:
                return None
            if past.startswith("했"):
                return _join_last(stem + " 하", "하세요") if False else \
                    _clean_spaces(stem + " 하세요")
            return _imperative_sentence(stem)

    # '~ㅂ니다 / ~습니다' : 받침 ㅂ + 니 다 (합니다 / 볶습니다 / 재웁니다 / 끓입니다)
    if s.endswith("니다") and len(s) >= 3:
        pre = s[-3]
        if _jong(pre) == 17:            # 종성 'ㅂ'
            stem = s[:-2]               # '합니다' → '합'
            parts = _syllable_parts(stem[-1])
            if parts:
                cho, jung, _ = parts
                bare = stem[:-1] + _compose(cho, jung, 0)
                # '볶습니다' 처럼 '으/스' 가 끼어든 형태는 걷어 낸다
                if bare[-1:] in ("스", "으") and len(bare) > 1 and _has_jong(bare[-2]):
                    bare = bare[:-1]
                if bare.endswith("하"):
                    return _clean_spaces(bare + "세요")
                if _verb_like(bare.split(" ")[-1]):
                    return _imperative_sentence(bare)
                return None

    # '~는다 / ~ㄴ다' (볶는다 / 넣는다 / 준비한다 / 만든다)
    if s.endswith("는다"):
        stem = s[:-2].rstrip()
        if not stem:
            return None
        if _intransitive(stem):
            return _clean_spaces(stem + "도록 하세요")
        return _clean_spaces(stem + "으세요")

    if s.endswith("한다"):
        stem = s[:-2].rstrip()
        if not stem:
            return None
        return _clean_spaces(_append_haseyo(stem))

    if s.endswith("다") and len(s) >= 2:
        body = s[:-1].rstrip()
        parts = _syllable_parts(body[-1]) if body else None
        if parts and parts[2] == JONG_NIEUN:      # 준비한·만든·썬·간
            cho, jung, _ = parts
            bare = body[:-1] + _compose(cho, jung, 0)
            if bare.endswith("하"):
                return _clean_spaces(bare + "세요")
            # ㄹ 받침이 줄어든 형태 보정
            for short, full in RIEUL_STEM.items():
                if bare.endswith(short) and (bare[:-len(short)] + full) != bare:
                    cand = bare[:-len(short)] + full
                    if len(short) >= 1 and len(bare) - len(short) >= 0:
                        if _is_cooking_stem(cand):
                            return _clean_spaces(cand + "으세요")
            if _intransitive(bare):
                return _clean_spaces(bare + "도록 하세요")
            return _imperative_sentence(bare)
        if body.endswith("아") or body.endswith("어") or body.endswith("여"):
            return _clean_spaces(body + " 주세요")
        if _intransitive(body):
            return _clean_spaces(body + "도록 하세요")
        return _imperative_sentence(body)

    return None


# ㄹ 받침 동사 어간 (보정용)
RIEUL_VERBS = {
    "썰", "만들", "알", "불", "풀", "갈", "말", "밀", "빨", "살", "팔", "놀", "돌",
    "흘", "늘", "달", "딸", "찰", "잴", "절", "졸", "얼", "덜", "훑", "둘", "벌",
}


def _is_cooking_stem(stem):
    return stem.split(" ")[-1] in RIEUL_VERBS


def _imperative_sentence(stem_text):
    """어간으로 끝나는 문장 조각을 명령형 문장으로."""
    last = stem_text.split(" ")[-1]
    if _intransitive(stem_text):
        return _clean_spaces(stem_text + "도록 하세요")
    return _clean_spaces(_join_last(stem_text, _imperative(last)))


def _normalize_polite(text):
    """이미 명령형인 문장의 띄어쓰기·표기만 다듬는다."""
    t = text
    t = re.sub(r"([가-힣])(주세요)$", r"\1 주세요", t) if False else t
    t = re.sub(r"([가-힣]{1})주세요$", r"\1 주세요", t)
    t = re.sub(r"(?<![가-힣])(해|하)\s*세요", "하세요", t)
    t = re.sub(r"(하|해)\s*주세요", "해 주세요", t)
    t = re.sub(r"\s+하세요", "하세요", t)
    t = re.sub(r"\s+주세요", " 주세요", t)
    t = re.sub(r"세요\s+주세요$", "세요", t)
    t = re.sub(r"(?<=[가-힣])해 주세요$", "하세요", t)
    return _clean_spaces(t)


def to_imperative(sentence):
    """한 문장을 '~하세요 / ~해 주세요' 형태로 바꾼다.

    바꿀 수 없는 감상·설명 문장이면 None 을 돌려준다.
    """
    s = _clean_spaces(sentence.strip(" ."))
    if not s:
        return None

    # 1) 이미 명령형이면 표기만 다듬는다
    if s.endswith(POLITE_END):
        return _normalize_polite(s)

    # 2) '~면 완성' / '~면 끝'
    m = re.match(r"^(.*?)(으면|라면|면)\s*(완성|끝)$", s)
    if m and m.group(1):
        return _clean_spaces(m.group(1) + m.group(2) + " 완성됩니다")

    # 3) 정형 표현
    for tails, repl in TAIL_RULES:
        for tail in tails:
            if s.endswith(tail):
                head = s[: -len(tail)].rstrip()
                if not head:
                    return repl if repl == "완성됩니다" else None
                return _clean_spaces(head + " " + repl)

    # 4) '~면 됩니다 / ~면 되요'
    for tail in _OK_TAIL:
        if s.endswith(tail):
            head = s[: -len(tail)].rstrip()
            if not head:
                return None
            return _clean_spaces(head + "면 됩니다")

    # 5) 감상·설명 문장은 버린다
    for tail in COMMENTARY_END:
        if s.endswith(tail):
            return None

    # 5-0) '~이에요 / ~예요' 는 설명문 (동사 어간이 붙은 경우만 명령형)
    if s.endswith("이에요") or s.endswith("예요"):
        head = s[:-2] if s.endswith("예요") else s[:-3]
        head = head.rstrip()
        if head and _verb_like(head.split(" ")[-1]):
            return _imperative_sentence(head)
        return None

    # 5-1) 과거형 '~았/었어요' 는 이미 끝난 동작 → 명령형
    for past in ("줬어요", "줬습니다", "줬다"):
        if s.endswith(past):
            stem = s[: -len(past)].rstrip()
            return _clean_spaces(stem + " 주세요")

    for past in ("았어요", "었어요", "였어요", "했어요"):
        if s.endswith(past):
            stem = s[: -len(past)].rstrip()
            if not stem:
                return None
            if past.startswith("했"):
                return _clean_spaces(stem + " 하세요")
            return _imperative_sentence(stem)

    # 5-2) '~합니다' → '~하세요'
    if s.endswith("합니다"):
        head = s[:-3].rstrip()
        if not head:
            return None
        return _clean_spaces(_append_haseyo(head))

    # 6) '~아요 / ~어요 / ~여요' → '~아/어 주세요'
    if s.endswith("요"):
        stem = s[:-1].rstrip()
        if not stem:
            return None
        last = stem.split(" ")[-1]
        if last.endswith("주어") or last.endswith("주었"):
            return _clean_spaces(stem[:-2] + " 주세요")
        if last.endswith("하"):
            return _clean_spaces(stem + "세요")
        if _intransitive(last):
            return _clean_spaces(stem + "도록 하세요")
        return _clean_spaces(stem + " 주세요")

    # 7) 서술형 → 명령형
    got = _declarative_to_imperative(s)
    if got:
        return got

    return None


def _join_frag(frag, step):
    """'김치를 넣고' + '볶아 주세요.' → '김치를 넣고 볶아 주세요.'"""
    frag = frag.rstrip(" .")
    if step.endswith(POLITE_END):
        return _clean_spaces(frag + " " + step)
    body = to_imperative(step)
    if body:
        return _clean_spaces(frag + " " + body + ".")
    return _clean_spaces(frag + " " + step)


# ---------------------------------------------------------------------------
# 3. 조리 순서 다시 쓰기
# ---------------------------------------------------------------------------

SPLIT_RE = re.compile(
    r"(?<=[.!?])\s*"
    r"|(?<=주세요)\s+"
    r"|(?<=하세요)\s+"
    r"|(?<=습니다)\s+"
    r"|(?<=니다)\s+"
    r"|(?<=해요)\s+"
)
CONNECTIVE_END = ("고", "서", "면", "다가", "며", "면서", "뒤", "후", "때", "채",
                  "까지", "부터", "라고", "지만", "는데", "은데")


def split_sentences(text):
    parts = [p.strip() for p in SPLIT_RE.split(text) if p.strip()]
    out = []
    for part in parts:
        if len(part) > 85:
            chunks = re.split(r"(?<=고)\s+|(?<=서)\s+|(?<=면)\s+|,\s+(?=[가-힣]{2,})", part)
            out.extend([c.strip(" ,") for c in chunks if c.strip()])
        else:
            out.append(part)
    return out


def _strip_head(sentence):
    """문장 앞의 군더더기를 덜어 낸다. 단어 중간은 건드리지 않는다
    ('다시마는' 의 '다시' 를 지우면 안 된다)."""
    s = sentence
    changed = True
    while changed:
        changed = False
        for filler in FILLER_HEAD:
            if not s.startswith(filler):
                continue
            after = s[len(filler):len(filler) + 1]
            if after and after not in " ,.다요":
                continue
            s = s[len(filler):].lstrip(" ,")
            changed = True
            break
    return s


def rewrite_sentence(raw):
    """한 문장 → 표준 조리 문장. 연결형으로 끝나면 '~' 를 붙여 돌려준다."""
    s = clean_step_text(raw)
    if not s:
        return None
    s = _strip_head(s).strip(" ,.")
    s = re.sub(r"^(은|는|을|를|과|와|도|만|에는|에서)\s+", "", s)
    if len(s) < 4:
        return None
    # 감상·홍보 문장 걸러 내기
    if re.search(r"(맛있|꿀팁|비법|포인트|성공|실패|감사|사랑|행복|여러분|다들|제 블로그|제 채널)", s) \
            and not re.search(r"(하세요|주세요|볶|끓|넣|썰|섞|구워|삶|데치)", s):
        return None
    out = to_imperative(s)
    if out:
        out = _strip_head(out)
        out = _clean_spaces(out)
        return out + "."
    if s.endswith(CONNECTIVE_END):
        return "~" + s
    return None


def rewrite_steps(raw_steps, max_steps=12):
    """조리 순서 목록 → 다시 쓴 표준 문장 목록."""
    pieces = []
    for raw in raw_steps or []:
        for sentence in split_sentences(str(raw)):
            got = rewrite_sentence(sentence)
            if got:
                pieces.append(got)

    merged = []
    carry = ""
    for piece in pieces:
        if piece.startswith("~"):
            frag = piece[1:].strip()
            if not carry:
                carry = frag
            else:
                carry = carry + " " + frag
            continue
        if carry:
            merged.append(_join_frag(carry, piece))
            carry = ""
        else:
            merged.append(piece)
    if carry:
        body = to_imperative(carry)
        merged.append(body + "." if body else None)
        merged = [m for m in merged if m]

    # 너무 짧은 문장은 앞 문장에 붙인다
    tight = []
    for sentence in merged:
        body = sentence.rstrip(".")
        if tight and len(body) < 12:
            prev = tight[-1].rstrip(".")
            if len(prev) + len(body) < 110:
                tight[-1] = prev + " " + body + "."
                continue
        tight.append(sentence)

    dedup = []
    for sentence in tight:
        if dedup and dedup[-1] == sentence:
            continue
        dedup.append(sentence)

    return dedup[:max_steps]


def rewrite_recipe(rec):
    """레시피 dict 하나를 제자리에서 고친다 (제목·조리순서·출처 제거)."""
    rec["name"] = clean_title(rec.get("name", ""))
    rec["steps"] = rewrite_steps(rec.get("steps") or [])
    rec.pop("src", None)
    rec.pop("author", None)
    rec.pop("rating", None)
    rec.pop("reviews", None)
    return rec


# ---------------------------------------------------------------------------
# 4. 점검용 도우미
# ---------------------------------------------------------------------------

BANNED_IN_TEXT = PERSON_WORDS + [
    "http://", "https://", "www.", "10000recipe", "만개", "쿠팡", "배송", "구매",
    "광고", "협찬", "이미지크게보기", "텍스트만보기", "원본보기", "블로그", "구독",
    "팔로우", "^^", "ㅋㅋ", "ㅎㅎ", "!!", "레시피",
]


def banned_hits(text):
    return [w for w in BANNED_IN_TEXT if w and w in (text or "")]
