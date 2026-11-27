"""만개의레시피(10000recipe.com) 레시피 목록 수집.

- 카테고리별 검색어로 레시피 id를 모아 후보 목록(candidates.json)을 만든다.
- 페이지 단위로 라운드로빈(1페이지 → 2페이지 …)으로 모아서, 어느 시점에 멈춰도
  카테고리별로 고르게 확보되도록 한다.

사용법:
  python3 tools/discover.py --pages 5
"""
import argparse
import json
import pathlib
import re
import sys
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from collect_net import fetch  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
HERE = ROOT / "scratch"

# 카테고리 → 검색어 목록
SEEDS = {
    "밥·죽": [
        "김치볶음밥", "볶음밥", "새우볶음밥", "오므라이스", "비빔밥", "참치마요덮밥",
        "카레라이스", "콩나물밥", "닭죽", "야채죽", "전복죽", "호박죽", "주먹밥",
        "덮밥", "리조또", "잡채밥", "제육덮밥", "오징어덮밥", "보리밥", "누룽지",
        "규동", "가츠동", "사케동", "연어덮밥", "명란밥", "버터간장밥", "마파두부덮밥",
        "차슈덮밥", "파에야", "영양밥", "곤드레밥", "단호박죽", "전복죽", "팥죽",
    ],
    "국·찌개": [
        "김치찌개", "된장찌개", "순두부찌개", "부대찌개", "청국장", "동태찌개",
        "미역국", "소고기무국", "콩나물국", "계란국", "북엇국", "시래기국", "육개장",
        "감자탕", "갈비탕", "삼계탕", "닭곰탕", "만둣국", "떡국", "수제비",
        "바지락국", "매운탕", "아욱국", "배추된장국", "참치김치찌개",
        "샤브샤브", "마라탕", "훠궈", "똠얌꿍", "미소시루", "된장국", "짜글이",
        "닭한마리", "추어탕", "선지국", "콩나물해장국", "황태해장국", "떡만둣국",
    ],
    "면·파스타": [
        "잡채", "비빔국수", "칼국수", "잔치국수", "콩국수", "막국수", "냉면",
        "쫄면", "라볶이", "알리오올리오", "토마토파스타", "크림파스타", "로제파스타",
        "짬뽕", "우동", "짜장면", "마라탕", "스파게티", "당면", "카르보나라",
        "봉골레", "페스토", "라자냐", "뇨끼", "쌀국수", "팟타이", "분짜", "반미",
        "소바", "텐푸라", "미고랭", "나시고랭", "울면", "중국냉면", "평양냉면",
    ],
    "반찬": [
        "감자조림", "두부조림", "연근조림", "우엉조림", "장조림", "멸치볶음",
        "어묵볶음", "진미채볶음", "오이무침", "무생채", "가지무침", "도라지무침",
        "시금치나물", "콩나물무침", "고사리나물", "깍두기", "오이소박이", "열무김치",
        "백김치", "총각김치", "배추겉절이", "장아찌", "미역초무침", "브로콜리무침",
        "감자조림", "메추리알장조림",
        "무말랭이", "파김치", "김자반", "숙주나물", "감자샐러드", "오이소박이",
    ],
    "볶음·구이": [
        "제육볶음", "오징어볶음", "낙지볶음", "주꾸미볶음", "닭갈비", "김치볶음",
        "버섯볶음", "애호박볶음", "감자채볶음", "불고기", "삼겹살구이", "갈비구이",
        "고등어구이", "갈치구이", "조기구이", "삼치구이", "떡갈비", "함박스테이크",
        "두부구이", "파프리카볶음", "새송이버섯구이", "닭볶음탕", "안심스테이크",
        "마라샹궈", "깐풍기", "꿔바로우", "마파두부", "돼지갈비", "LA갈비", "찜닭",
        "치킨스테이크", "미트볼", "함박스테이크",
    ],
    "전·부침": [
        "김치전", "해물파전", "부추전", "감자전", "호박전", "동그랑땡",
        "버섯전", "녹두전", "배추전", "깻잎전", "새우전", "오징어전",
        "부침개", "빈대떡", "육전", "계란말이", "계란찜",
        "고추전", "가지전", "버섯전", "달걀찜",
    ],
    "분식·야식": [
        "떡볶이", "로제떡볶이", "치즈떡볶이", "순대", "김밥", "참치김밥",
        "야채김밥", "튀김", "오징어튀김", "고구마튀김", "핫도그", "토스트",
        "떡꼬치", "어묵꼬치", "군만두", "만두", "감자튀김", "양념치킨", "닭강정",
        "치즈볼", "라면", "짜파게티", "컵떡볶이", "어묵탕",
        "닭발", "곱창", "막창", "오돌뼈", "유부초밥", "쫄볶이", "국물떡볶이",
    ],
    "양식·기타": [
        "스테이크", "돈까스", "샌드위치", "샐러드", "오믈렛", "감바스",
        "그라탕", "크림수프", "카레", "하이라이스", "햄버거", "피자",
        "와플", "팬케이크", "프렌치토스트", "머핀", "쿠키", "브라우니",
        "타코", "부리또",
        "브런치", "에그베네딕트", "오픈샌드위치", "파니니", "감바스", "그라탕",
        "크림수프", "오믈렛", "스크램블에그", "와플", "크로플", "머핀", "스콘",
        "쿠키", "브라우니", "티라미수", "치즈케이크", "푸딩", "마들렌", "롤케이크",
        "포케", "퀘사디아", "나초", "인도커리", "치킨티카", "난", "딤섬", "완탕",
        "오코노미야키", "타코야키", "곤약면", "두부면", "오트밀", "스무디볼",
        "닭가슴살샐러드", "단호박샐러드", "그릭요거트",
    ],
}

ID_RE = re.compile(r'href="/recipe/(\d+)"')


def discover(pages):
    # (cat, kw) 목록을 검색어 순서대로, 같은 카테고리가 몰리지 않게 섞는다
    jobs = []
    kws = []
    for cat, words in SEEDS.items():
        for w in words:
            kws.append((cat, w))
    seen_kw = set()
    uniq = []
    for cat, w in kws:
        if (cat, w) in seen_kw:
            continue
        seen_kw.add((cat, w))
        uniq.append((cat, w))

    for page in range(1, pages + 1):
        for cat, kw in uniq:
            jobs.append((cat, kw, page))

    by_id = {}
    order = []
    for i, (cat, kw, page) in enumerate(jobs, 1):
        q = urllib.parse.quote(kw)
        url = f"https://www.10000recipe.com/recipe/list.html?q={q}&page={page}"
        try:
            status, html = fetch(url)
        except Exception as e:  # noqa: BLE001
            print("ERR", kw, page, e)
            continue
        ids = []
        for rid in ID_RE.findall(html):
            if len(rid) < 6:
                continue
            if rid not in ids:
                ids.append(rid)
        new = 0
        for rank, rid in enumerate(ids):
            if rid in by_id:
                continue
            by_id[rid] = {"id": rid, "cat": cat, "kw": kw, "page": page, "rank": rank}
            order.append(rid)
            new += 1
        if i % 25 == 0 or i == len(jobs):
            print(f"[{i}/{len(jobs)}] {kw} p{page}: {len(ids)}개 (신규 {new}) · 누적 {len(order)}", flush=True)
            (HERE / "candidates.json").write_text(
                json.dumps([by_id[x] for x in order], ensure_ascii=False), encoding="utf-8")

    (HERE / "candidates.json").write_text(
        json.dumps([by_id[x] for x in order], ensure_ascii=False), encoding="utf-8")
    print("후보", len(order))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=4)
    a = ap.parse_args()
    discover(a.pages)
