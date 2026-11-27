"""수집한 레시피(raw.jsonl)를 앱 데이터(data/recipes-data.js)로 정리한다.

하는 일
 1) 이름·재료·조리순서가 비어 있거나 부실한 레시피 제거
 2) 제목 중복 제거(같은 요리는 후기 많은 쪽만 남김), 기존 큐레이션 요리와 겹치는 제목 제외
 3) 재료 문자열을 재료 분류(taxonomy)에 매핑 → 냉장고 매칭용 req(필수)/opt(선택)
 4) 카테고리별 상한을 두고 고르게 추림
 5) data/recipes-data.js 생성

사용법: python3 tools/build_recipes.py
"""
import io
import json
import pathlib
import re
import sys
import time
import zlib
from collections import Counter, OrderedDict

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import recipe_taxonomy as T  # noqa: E402
import delivery_menus as D     # noqa: E402
import food_tips as F          # noqa: E402
import recipe_rewriter as RW   # noqa: E402

RAW = [ROOT / "scratch" / "raw.jsonl", ROOT / "scratch" / "raw2.jsonl"]
OUT = ROOT / "data" / "recipes-data.js"

# 카테고리별 최대 수 (고르게 담기)
CAP = OrderedDict([
    ("밥·죽", 195),
    ("국·찌개", 190),
    ("반찬", 200),
    ("볶음·구이", 185),
    ("면·파스타", 178),
    ("분식·야식", 178),
    ("전·부침", 152),
    ("양식·기타", 162),
])

# 요리 이름 키워드 팁 (긴 키워드 먼저 확인해야 '김치볶음밥'이 '볶음밥'보다 먼저 걸린다)
TIP_KEYS = sorted(F.RULES.items(), key=lambda kv: -len(kv[0]))

DROP_PAT = re.compile(
    r"(http|www\.|배송|구매|쿠팡|문의|광고|이벤트|공동구매|상품|리뷰|구독|팔로우|블로그|"
    r"인플루언서|제공받|업체|협찬|판매|가격|주문|전화|카톡|링크|"
    r"이미지크게보기|텍스트만보기|이미지작게보기|원본보기|이미지 크게|동영상|바로가기|더보기)")

PREP_PREFIX = [
    "곱게다진", "곱게간", "잘게썬", "잘게다진", "채썬", "송송썬", "어슷썬", "반달썬",
    "납작썬", "깍둑썬", "먹기좋게썬", "한입크기로썬", "삶은", "데친", "익힌", "볶은",
    "구운", "튀긴", "불린", "손질한", "다진", "절인", "다진것", "갈은", "송송썰은", "송송썬", "잘게썰은",
]

ALIAS = []
for item in T.ITEMS:
    for a in item["aliases"] + [item["label"]]:
        key = re.sub(r"\s+", "", a).lower()
        if key:
            ALIAS.append((key, item))
ALIAS.sort(key=lambda x: -len(x[0]))

BY_ID = {i["id"]: i for i in T.ITEMS}


def norm_title(t):
    return re.sub(r"[^0-9a-z가-힣]", "", (t or "").lower())


def clean_step(s):
    s = re.sub(r"<[^>]*>", " ", s or "")
    s = s.replace("&nbsp;", " ").replace("\u200b", "").replace("\ufeff", "")
    s = re.sub(r"^[\s\-•·○●▶►*①-⑳]+", "", s)          # 앞 불릿 제거
    s = re.sub(r"^\d{1,2}[.)]\s*", "", s)               # 앞 목록 번호만 제거 ("2분이"는 유지)
    s = re.sub(r"\s+", " ", s).strip()
    s = DROP_PAT.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) < 5:
        return ""
    if len(s) > 260:
        cut = s[:260]
        for sep in (". ", "다. ", "요. ", "! ", "? "):
            idx = cut.rfind(sep)
            if idx > 120:
                return cut[: idx + len(sep)].strip()
        return cut.rsplit(" ", 1)[0].strip()
    return s


def clean_ingredient(raw):
    s = raw or ""
    s = re.sub(r"\([^)]*\)", " ", s)      # 괄호 설명 제거
    s = re.sub(r"\[[^\]]*\]", " ", s)
    s = re.sub(r"(※|★|☞|->|⇒).*$", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" ,·-")
    if len(s) > 24:
        s = s[:24].strip()
    return s


AMOUNT_HINT = re.compile(
    r"(약간|조금|적당|적당량|한줌|한움큼|톡톡|취향껏|기호에|반컵|한컵|한공기|한대|한개|한모|한장)")


def normalize_amount(amount):
    """'1 큰 술' → '1큰술', '1/2 개' → '1/2개' 처럼 분량 표기를 붙여 쓴다."""
    a = (amount or "").strip()
    if not a:
        return ""
    a = re.sub(r"\s+", " ", a)
    a = re.sub(r"(\d)\s+(큰술|작은술|숟가락|스푼|티스푼|컵|개|대|모|장|쪽|줌|꼬집|방울|국자|인분|g|kg|ml|L|Ts|ts|T|t)\b", r"\1\2", a)
    a = re.sub(r"\b(한|두|세|네|반)\s+(큰술|작은술|숟가락|스푼|컵|개|대|모|장|쪽|줌|꼬집|국자)", r"\1\2", a)
    return a.strip()


def split_amount(text):
    """'김치 1/4밥그릇' → ('김치', '1/4밥그릇')"""
    s = text.strip()
    m = re.search(r"[0-9½⅓⅔¼¾]", s)
    m2 = AMOUNT_HINT.search(s)
    idx = None
    if m:
        idx = m.start()
    if m2 and (idx is None or m2.start() < idx):
        idx = m2.start()
    if idx is None:
        return s, ""
    name = s[:idx].strip(" ,·-")
    amount = s[idx:].strip()
    if not name:
        return s, ""
    return name, amount


def match_ingredient(raw):
    """재료 문자열 → taxonomy 항목 (없으면 None)."""
    s = re.sub(r"\([^)]*\)", " ", raw or "")
    s = re.sub(r"\s+", "", s).lower()
    if not s or len(s) < 1:
        return None
    for prefix in PREP_PREFIX:
        if s.startswith(prefix) and len(s) > len(prefix):
            s = s[len(prefix):]
            break
    for key, item in ALIAS:
        if s.startswith(key):
            return item
    for key, item in ALIAS:
        if len(key) >= 2 and key in s[:6]:
            return item
    return None


def parse_time(txt, iso):
    m = re.search(r"(\d+)\s*분", txt or "")
    if m:
        return int(m.group(1))
    if txt and "시간" in txt:
        h = re.search(r"(\d+)\s*시간", txt)
        return int(h.group(1)) * 60 if h else 90
    if iso:
        m = re.search(r"PT(?:(\d+)H)?(?:(\d+)M)?", iso)
        if m:
            return int(m.group(1) or 0) * 60 + int(m.group(2) or 0)
    return 30


def parse_level(lv):
    return {"아무나": 1, "초급": 1, "중급": 2, "고급": 3, "신의경지": 3}.get(lv, 1)


MOOD_RULES = {
    "밥·죽": ["hearty", "alone"],
    "국·찌개": ["hearty", "hangover"],
    "반찬": ["light"],
    "볶음·구이": ["hearty", "hangover"],
    "면·파스타": ["hearty", "alone"],
    "분식·야식": ["night", "alone"],
    "전·부침": ["night", "light", "hangover"],
    "양식·기타": ["hearty"],
}
KEY_MOOD = [
    (("해장", "숙취", "해소"), "hangover"),
    (("다이어트", "샐러드", "가벼", "저칼로리", "건강"), "light"),
    (("야식", "안주", "술"), "night"),
    (("혼밥", "1인", "간단"), "alone"),
]
BUDGET_HIGH = ("소고기", "갈비", "스테이크", "장어", "전복", "삼겹", "차돌", "연어", "대게", "꽃게")

EMOJI_BY_ING = {
    "beef": "🥩", "pork": "🥩", "chicken": "🍗", "ham": "🥓", "fish": "🐟", "shrimp": "🦐",
    "squid": "🦑", "clam": "🐚", "egg": "🥚", "tofu": "🧊", "sundubu": "🍲", "rice": "🍚",
    "tteok": "🍡", "ramen": "🍜", "pasta": "🍝", "bread": "🍞", "dumpling": "🥟", "cheese": "🧀",
    "mushroom": "🍄", "potato": "🥔", "kimchi": "🌶️", "sweetpotato": "🍠", "corn": "🌽",
}
EMOJI_BY_CAT = {
    "밥·죽": "🍚", "국·찌개": "🍲", "면·파스타": "🍜", "반찬": "🥢", "볶음·구이": "🍳",
    "전·부침": "🥞", "분식·야식": "🍢", "양식·기타": "🍽️",
}


CAT_EMOJI_FIRST = ("국·찌개", "밥·죽")


def pick_emoji(rec, req_ids):
    cat = rec.get("cat")
    if cat in CAT_EMOJI_FIRST:
        return EMOJI_BY_CAT[cat]
    for rid in req_ids:
        if rid in EMOJI_BY_ING:
            return EMOJI_BY_ING[rid]
    return EMOJI_BY_CAT.get(cat, "🍽️")


def make_tip(name, req, cat, rid):
    """요리별 팁: (이름 키워드 → 주재료 → 카테고리) 핵심 팁 + 보조 팁."""
    base = None
    for kw, tip in TIP_KEYS:
        if kw in name:
            base = tip
            break
    main_id = None
    # 이름에 나온 재료를 우선 (예: '새우 크림 리조또' → 새우)
    named = [i for i in req if BY_ID.get(i) and BY_ID[i]["label"] in name]
    order = named + [i for i in req if i not in named]
    for rid_ in order:
        if base is None and rid_ in F.ING_TIPS:
            base = F.ING_TIPS[rid_]
        if main_id is None and (rid_ in F.ING_EXTRAS or rid_ in F.ING_TIPS):
            main_id = rid_
    if base is None:
        base = F.CAT_RULES.get(cat, "간은 마지막에 맞추면 재료 맛이 살아요.")

    pool = []
    if main_id in F.ING_EXTRAS:
        pool.append(F.ING_EXTRAS[main_id])
    pool.extend(F.EXTRAS.get(cat, []))
    for cats, tip in F.TECHNIQUE:
        if cats is None or cat in cats:
            pool.append(tip)
    h = zlib.crc32((rid + name).encode("utf-8"))
    extra = pool[h % len(pool)]
    if extra == base:
        extra = pool[(h + 1) % len(pool)]
    return base + " " + extra


def curated_names():
    """app.js 의 큐레이션 요리 이름을 quickjs로 읽어 온다."""
    src = io.open(ROOT / "app.js", encoding="utf-8").read()
    idx = src.rstrip().rfind("})();")
    probe = "\nglobalThis.__names = DISHES.map(function(d){return d.name;});\n"
    js = src[:idx] + probe + "})();\n"
    prelude = """
    var document={readyState:"loading",addEventListener:function(){},querySelector:function(){return null},
      querySelectorAll:function(){return [];},createElement:function(){return {style:{},classList:{add:function(){},remove:function(){},toggle:function(){}},appendChild:function(){},addEventListener:function(){},setAttribute:function(){},dataset:{}}},
      body:{style:{},appendChild:function(){},removeChild:function(){}}};
    var window={addEventListener:function(){},scrollTo:function(){}};
    var navigator={}; var location={protocol:"http:",href:""};
    var localStorage={getItem:function(){return null;},setItem:function(){}};
    """
    try:
        import quickjs
        ctx = quickjs.Context()
        ctx.eval(prelude)
        ctx.eval(js)
        return json.loads(ctx.eval("JSON.stringify(__names)"))
    except Exception as e:  # noqa: BLE001
        print("quickjs 사용 실패, 정규식으로 대체:", e)
        return re.findall(r'name:\s*"([^"]+)"', src)


CAT_SHAPE = {
    "밥·죽": "밥", "국·찌개": "찌개", "면·파스타": "파스타", "볶음·구이": "볶음",
    "반찬": "반찬", "전·부침": "전", "분식·야식": "분식", "양식·기타": "요리",
}


def fallback_name(req, cat):
    """제목을 남길 수 없을 때: 주재료 + 요리 형태로 이름을 만든다."""
    pick = None
    for rid in req:
        item = BY_ID.get(rid)
        if not item or item.get("pantry") or item.get("always"):
            continue
        pick = item["label"]
        break
    if pick is None and req:
        pick = BY_ID.get(req[0], {}).get("label")
    shape = CAT_SHAPE.get(cat, "요리")
    return (pick + " " + shape).strip() if pick else shape


def name_variants(name, req, used_keys):
    """같은 이름이 이미 있으면 주재료를 앞에 붙여 구분한다."""
    out = []
    for rid in req:
        item = BY_ID.get(rid)
        if not item or item.get("pantry") or item.get("always"):
            continue
        label = item["label"]
        if label in name:
            continue
        out.append(label + " " + name)
    return out


def dedupe_key(name):
    return re.sub(r"[^0-9a-z가-힣]", "", (name or "").lower())


def load_records():
    recs = []
    for path in RAW:
        if not path.exists():
            continue
        for line in io.open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except Exception:  # noqa: BLE001
                pass
    return recs


def build():
    errs = T.validate()
    if errs:
        raise SystemExit("재료 분류 오류:\n" + "\n".join(errs))
    recs = load_records()
    cur = {norm_title(n) for n in curated_names()}
    print(f"수집 원본 {len(recs)}건 · 큐레이션 제목 {len(cur)}개")

    unmatched = Counter()
    per_cat = Counter()
    kept = []
    seen_titles = set()
    dropped = Counter()

    for rec in recs:
        raw_name = (rec.get("name") or "").strip()
        raw_steps = [str(x) for x in (rec.get("steps") or [])]
        ings_raw = [clean_ingredient(s) for s in rec.get("ingredients") or []]
        ings_raw = [s for s in ings_raw if s]
        if not raw_name or len(raw_steps) < 2 or len(ings_raw) < 2:
            dropped["부실"] += 1
            continue

        req, opt = [], []
        ing_pairs = []
        for raw in ings_raw:
            item = match_ingredient(raw)
            nm, amt = split_amount(raw)
            if item is None:
                unmatched[re.sub(r"[\d/.,]+.*$", "", raw).strip()[:12]] += 1
                ing_pairs.append([nm, amt, ""])
                continue
            ing_pairs.append([nm, amt, item["id"]])
            if item.get("always"):
                continue
            if item.get("pantry"):
                if item["id"] not in opt:
                    opt.append(item["id"])
            elif item["id"] not in req:
                req.append(item["id"])

        if len(req) < 2:
            dropped["재료 매핑 부족"] += 1
            continue
        if len(req) > 10:
            opt = req[10:] + opt
            req = req[:10]
        opt = [x for x in opt if x not in req][:10]

        cat = rec.get("cat") or "양식·기타"
        if cat not in CAP:
            cat = "양식·기타"

        # --- 제목·조리 순서를 표준 문장으로 다시 쓴다 ---
        title = RW.clean_title(raw_name)
        if not title or not any(RW._is_dish(w) for w in title.split()):
            title = fallback_name(req, cat)
        steps = RW.rewrite_steps(raw_steps)
        if len(steps) < 2 or sum(len(x) for x in steps) < 40:
            dropped["조리순서 빈약"] += 1
            continue

        # 제목 중복: 주재료를 붙여 구분하고, 그래도 겹치면 버린다
        key = dedupe_key(title)
        if not key or key in cur or key in seen_titles:
            picked_name = None
            for alt in name_variants(title, req, seen_titles):
                alt_key = dedupe_key(alt)
                if alt_key and alt_key not in cur and alt_key not in seen_titles:
                    picked_name = alt
                    break
            if not picked_name:
                dropped["제목 중복"] += 1
                continue
            title = picked_name
            key = dedupe_key(title)
        seen_titles.add(key)

        text = title + " " + " ".join(steps)
        moods = list(MOOD_RULES.get(cat, ["hearty"]))
        for keys, mood in KEY_MOOD:
            if any(k in text for k in keys) and mood not in moods:
                moods.append(mood)
        moods = moods[:3]

        budget = "mid" if any(k in title for k in BUDGET_HIGH) else "low"
        servings = re.sub(r"[^0-9인분]", "", rec.get("servings") or "")
        if not re.fullmatch(r"[1-8]인분", servings):
            servings = ""

        kept.append({
            "id": "r" + str(rec["id"]),
            "name": title,
            "cat": cat,
            "emoji": pick_emoji(rec, req),
            "time": parse_time(rec.get("time_text"), rec.get("total_time")),
            "level": parse_level(rec.get("level")),
            "servings": servings,
            "req": req,
            "opt": opt,
            "moods": moods,
            "budget": budget,
            "ing": [[n, normalize_amount(a), i] for n, a, i in ing_pairs[:20]],
            "steps": steps[:12],
            "tip": make_tip(title, req, cat, "r" + str(rec["id"])),
            "_reviews": rec.get("reviews") or 0,
        })
        per_cat[cat] += 1

    # 카테고리별 상한 적용 (후기 많은 순)
    kept.sort(key=lambda r: (-r["_reviews"], -len(r["steps"])))
    picked, cnt = [], Counter()
    for r in kept:
        if cnt[r["cat"]] >= CAP[r["cat"]]:
            continue
        cnt[r["cat"]] += 1
        picked.append(r)
    # ---- 희귀 재료 커버리지: 아무 레시피에도 안 남은 재료가 있으면
    #      같은 카테고리의 후보(상한에 밀린 것) 중 그 재료를 쓰는 것으로 바꿔 넣는다.
    picked_ids = {r["id"] for r in picked}
    overflow = [r for r in kept if r["id"] not in picked_ids]
    by_ing = {}
    for r in overflow:
        for iid in r["req"] + r["opt"]:
            by_ing.setdefault(iid, []).append(r)
    covered = set()
    for r in picked:
        covered.update(r["req"])
        covered.update(r["opt"])
    swaps = 0
    for item in T.ITEMS:
        if item.get("always") or item["id"] in covered:
            continue
        cands = [r for r in by_ing.get(item["id"], []) if r["id"] not in picked_ids]
        if not cands:
            continue
        cands.sort(key=lambda r: (-r["_reviews"], -len(r["steps"])))
        cand = cands[0]
        same_cat = [r for r in picked if r["cat"] == cand["cat"]]
        if not same_cat:
            continue
        victim = same_cat[-1]
        picked.remove(victim)
        picked_ids.discard(victim["id"])
        picked.append(cand)
        picked_ids.add(cand["id"])
        covered.update(cand["req"])
        covered.update(cand["opt"])
        swaps += 1
    if swaps:
        print(f"희귀 재료 커버리지로 교체 {swaps}건")

    for r in picked:
        r.pop("_reviews", None)
    picked.sort(key=lambda r: (r["cat"], r["name"]))

    print("카테고리별 최종:", dict(cnt), "합계", len(picked))
    print("제외 사유:", dict(dropped))
    print("매핑 안 된 재료 상위:", unmatched.most_common(25))

    menus = D.rows()
    for i, m in enumerate(menus, 1):
        m["id"] = "o" + str(i)
        m["method"] = "out"
        m["level"] = 1

    data = {
        "generatedAt": time.strftime("%Y-%m-%d"),
        "source": "직접 정리한 표준 조리 안내",
        "count": len(picked),
        "counts": {"home": len(picked), "out": len(menus), "total": len(picked) + len(menus)},
        "taxonomy": [
            {
                "id": i["id"], "label": i["label"], "emoji": i["emoji"], "group": i["group"],
                "common": bool(i.get("common")), "pantry": bool(i.get("pantry")),
                "always": bool(i.get("always")), "aliases": i["aliases"],
            }
            for i in T.ITEMS
        ],
        "recipes": picked,
        "out": menus,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    js = (
        "/* 자동 생성 파일입니다. tools/build_recipes.py 로 다시 만드세요.\n"
        f"   집밥 {len(picked)}개 · 배달·외식 {len(menus)}개 · {data['generatedAt']} */\n"
        "window.RECIPE_DB = " + body + ";\n"
    )
    io.open(OUT, "w", encoding="utf-8").write(js)
    print(f"저장: {OUT} ({OUT.stat().st_size / 1024:.0f}KB, 집밥 {len(picked)}개 + 배달·외식 {len(menus)}개)")


if __name__ == "__main__":
    build()
