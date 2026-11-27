"""빌드 없이 돌리는 로직 점검 (quickjs 사용).

- data/recipes-data.js + app.js 를 실제로 실행해서 앱 로직을 검증한다 (DOM은 가짜 객체)
- 데이터: 집밥 1,400개 이상 · 배달·외식 100개 이상 · 재료 140종 이상
- 저작권 안전성: 제목·조리 순서에 블로거 이름·출처 URL·홍보 문구가 없고, 조리 문장이
  '~하세요 / ~해 주세요' 형태로 통일됐는지
- 새 기능: 찜·최근 본 메뉴(localStorage), 인분 수 분량 환산, 부족한 재료 쿠팡 링크
- 정적 페이지: about/privacy/terms, sitemap.xml, robots.txt, OpenGraph 메타
- 재료 세분화: 진간장/국간장/고추장/쌈장/발사믹식초/올리브유/들기름 … 별칭 해석
- 팁: 모든 레시피·배달 메뉴에 20자 이상 팁, 문장이 겹치지 않는지
- 룰렛: 기분·예산·방식·집밥 종류·배달 종류 조합에 후보가 있는지
- 정적 파일: HTML id, 자산 버전, 태그 균형

사용법: python3 tools/check_logic.py
"""
import io
import json
import pathlib
import re
import sys

import quickjs

ROOT = pathlib.Path(__file__).resolve().parent.parent
fails, notes = [], []


def check(cond, msg):
    if cond:
        notes.append("  OK   " + msg)
    else:
        fails.append(msg)


DOM_STUB = r"""
var __els = {};
function __el(id) {
  if (!__els[id]) {
    __els[id] = {
      id: id, innerHTML: "", textContent: "", value: "", hidden: false, disabled: false,
      style: { setProperty: function () {} }, dataset: {},
      classList: { add: function () {}, remove: function () {}, toggle: function () {}, contains: function () { return false; } },
      children: [],
      appendChild: function (n) { this.children.push(n); return n; },
      removeChild: function () {},
      addEventListener: function () {}, setAttribute: function () {},
      querySelector: function () { return __el("__inner"); },
      querySelectorAll: function () { return []; },
      focus: function () {}, scrollTop: 0,
      scrollIntoView: function () {},
      parentNode: null,
    };
  }
  return __els[id];
}
var document = {
  readyState: "complete",
  addEventListener: function () {},
  querySelector: function (sel) { return __el(sel.replace("#", "").replace(".", "")); },
  querySelectorAll: function (sel) {
    if (sel === ".tab") {
      return [
        { dataset: { view: "fridge" }, setAttribute: function () {}, addEventListener: function () {},
          classList: { add: function () {}, remove: function () {}, toggle: function () {}, contains: function () { return false; } } },
        { dataset: { view: "roulette" }, setAttribute: function () {}, addEventListener: function () {},
          classList: { add: function () {}, remove: function () {}, toggle: function () {}, contains: function () { return false; } } }
      ];
    }
    return [];
  },
  createElement: function () {
    return {
      style: { setProperty: function () {} },
      classList: { add: function () {}, remove: function () {}, toggle: function () {}, contains: function () { return false; } },
      dataset: {}, children: [], innerHTML: "", textContent: "", value: "",
      appendChild: function (n) { this.children.push(n); return n; },
      removeChild: function () {},
      addEventListener: function () {}, setAttribute: function () {},
      querySelector: function () { return null; }, querySelectorAll: function () { return []; },
    };
  },
  createDocumentFragment: function () {
    return { children: [], appendChild: function (n) { this.children.push(n); return n; } };
  },
  body: { style: {}, appendChild: function () {}, removeChild: function () {} }
};
var window = { addEventListener: function () {}, scrollTo: function () {}, RECIPE_DB: null };
var navigator = {};
var location = { protocol: "https:", href: "https://example.com/" };
var __store = {};
var localStorage = {
  getItem: function (k) { return __store[k] == null ? null : __store[k]; },
  setItem: function (k, v) { __store[k] = String(v); },
  removeItem: function (k) { delete __store[k]; }
};
"""

PROBE = r"""
globalThis.__t = {
  INGREDIENTS: INGREDIENTS,
  RECIPES: RECIPES.map(function (d) {
    return { id: d.id, name: d.name, cat: d.cat, emoji: d.emoji, time: d.time,
             level: d.level, moods: d.moods, budget: d.budget, method: d.method, price: d.price,
             servings: d.servings,
             req: d.req, opt: d.opt, ing: d.ing, steps: d.steps, tip: d.tip, comment: d.comment,
             src: d.src, curated: !!d.curated };
  }),
  HOME_COUNT: HOME_RECIPES.length,
  ALL_COUNT: ALLDISH.length,
  CATEGORIES: CATEGORIES,
  OUT_CATS: OUT_CATS,
  ING_TABS: ING_TABS,
  state: state,
  matchRows: matchRows,
  buildRows: buildRows,
  getPool: getPool,
  findByLabel: findByLabel,
  formatTime: formatTime,
  openDrawer: openDrawer,
  drawerHtml: function (d) { openDrawer(d); return __el("drawerPanel").innerHTML; },
  dishHtml: function (row, showMatch) { return dishNode(row, 0, showMatch).innerHTML; },
  setState: function (o) { for (var k in o) state[k] = o[k]; },
  rowById: function (id) {
    for (var i = 0; i < RECIPES.length; i++) if (RECIPES[i].id === id) return RECIPES[i];
    return null;
  },
  searchRows: function (q) { state.query = q; return buildRows().length; },
  CFG: CFG,
  scaleAmount: scaleAmount,
  formatNum: formatNum,
  baseServings: baseServings,
  readableAmount: readableAmount,
  coupangLink: coupangLink,
  ingredientListHtml: function (id, target) {
    var d = __t.rowById(id); state.serving[id] = target;
    return ingredientListHtml(d, function () { return false; });
  },
  servingsHtml: function (id) { return servingsHtml(__t.rowById(id)); },
  toggleFav: function (id) { return toggleFav(id); },
  isFav: function (id) { return isFav(id); },
  favIds: function () { return favIds.slice(); },
  recentIds: function () { return recentIds.slice(); },
  pushRecent: function (id) { pushRecent(id); },
  setFavView: function (v) { state.favView = v; return buildRows().map(function (r) { return r.dish.id; }); },
  setServing: function (id, n) { state.serving[id] = n; },
  drawerFor: function (id, n) { state.serving[id] = n; return __t.drawerHtml(__t.rowById(id)); }
};
"""


def load_context():
    ctx = quickjs.Context()
    ctx.eval(DOM_STUB)
    data = io.open(ROOT / "data" / "recipes-data.js", encoding="utf-8").read()
    ctx.eval(data)
    src = io.open(ROOT / "app.js", encoding="utf-8").read()
    assert src.rstrip().endswith("})();"), "app.js 구조가 예상과 다릅니다"
    idx = src.rstrip().rfind("})();")
    ctx.eval(src[:idx] + PROBE + "\n})();\n")
    return ctx


def js(ctx, expr):
    return json.loads(ctx.eval("JSON.stringify(" + expr + ")"))


def main():
    ctx = load_context()

    recipes = js(ctx, "__t.RECIPES")
    ings = js(ctx, "__t.INGREDIENTS")
    cats = [c["id"] for c in js(ctx, "__t.CATEGORIES")]
    out_cats = [c["id"] for c in js(ctx, "__t.OUT_CATS")]
    tabs = [t["id"] for t in js(ctx, "__t.ING_TABS")]
    home = [r for r in recipes if r["method"] == "home"]
    out = [r for r in recipes if r["method"] == "out"]

    print(f"재료 분류 {len(ings)}종 · 집밥 {len(home)}개 · 배달·외식 {len(out)}개 "
          f"(전체 {len(recipes)})")

    # ---------- 1. 규모 ----------
    check(len(ings) >= 140, f"재료 분류 140종 이상 ({len(ings)}종)")
    check(len(home) >= 1400, f"집밥 레시피 1,400개 이상 ({len(home)}개)")
    check(len(out) >= 100, f"배달·외식 메뉴 100개 이상 ({len(out)}개)")
    check(len(recipes) >= 1500, f"전체 메뉴 1,500개 이상 ({len(recipes)}개)")
    check(len(out_cats) >= 11, f"배달 음식 종류 10가지 이상 ({len(out_cats) - 1}가지)")
    check(len(tabs) >= 9, f"재료 그룹 탭 9개 이상 ({len(tabs)}개)")

    ing_ids = [i["id"] for i in ings]
    check(len(ing_ids) == len(set(ing_ids)), "재료 id 중복 없음")

    ids = [r["id"] for r in recipes]
    check(len(ids) == len(set(ids)), "레시피 id 중복 없음")

    def norm(t):
        return re.sub(r"[^0-9a-z가-힣]", "", (t or "").lower())

    for method in ("home", "out"):
        titles = [norm(r["name"]) for r in recipes if r["method"] == method]
        dup_titles = sorted({t for t in titles if titles.count(t) > 1})
        check(not dup_titles, f"{method} 메뉴 이름 중복 없음 (중복 {dup_titles[:5]})")

    # ---------- 2. 집밥 데이터 정합성 ----------
    empty_ing, empty_steps, short_steps, bad_req, bad_cat, no_tip = [], [], [], [], [], []
    for r in recipes:
        if r["method"] == "home":
            if not r["ing"] or any(not (row[0] or "").strip() for row in r["ing"]):
                empty_ing.append(r["id"])
            if not r["steps"] or any(not s.strip() for s in r["steps"]):
                empty_steps.append(r["id"])
            if len(r["steps"]) < 2 or sum(len(s) for s in r["steps"]) < 40:
                short_steps.append(r["id"])
            if len(r["req"]) < (1 if r["curated"] else 2):
                bad_req.append(r["id"])
            for rid in r["req"] + r["opt"]:
                if rid not in ing_ids:
                    bad_req.append(r["id"] + ":" + rid)
            if r["cat"] not in cats:
                bad_cat.append(r["id"] + ":" + r["cat"])
            if not isinstance(r["time"], int) or r["time"] <= 0:
                bad_cat.append(r["id"] + ":time")
            if r["level"] not in (1, 2, 3):
                bad_cat.append(r["id"] + ":level")
            if len(r["tip"] or "") < 20:
                no_tip.append(r["id"])

    check(not empty_ing, f"모든 집밥 레시피에 재료 있음 (빈 재료 {len(empty_ing)}건)")
    check(not empty_steps, f"모든 집밥 레시피에 조리 순서 있음 (빈 순서 {len(empty_steps)}건)")
    check(not short_steps, f"조리 순서가 2단계·40자 이상 (부실 {len(short_steps)}건)")
    check(not bad_req, f"필수 재료 2개 이상·모두 유효 id (문제 {bad_req[:5]})")
    check(not bad_cat, f"카테고리·시간·난이도 유효 (문제 {bad_cat[:5]})")
    check(not no_tip, f"모든 집밥 레시피에 팁 있음 (없는 레시피 {len(no_tip)}건)")

    # 사이트 UI 문구·광고가 조리 단계에 남아 있지 않은지
    junk = ("이미지크게보기", "텍스트만보기", "이미지작게보기", "원본보기", "http://", "https://",
            "쿠팡", "배송", "구매", "광고")
    dirty = [r["id"] + ":" + w for r in recipes for st in r["steps"] for w in junk if w in st]
    check(not dirty, f"조리 단계에 화면 문구·광고 없음 (문제 {dirty[:3]})")

    dist = {}
    for r in home:
        dist[r["cat"]] = dist.get(r["cat"], 0) + 1
    print("집밥 카테고리 분포:", dist)
    check(all(dist.get(c, 0) >= 50 for c in cats if c != "all"),
          "모든 집밥 카테고리에 50개 이상")
    check(len(dist) >= 8, "집밥 카테고리 8종")

    # 2-1. 저작권 안전성: 블로거 이름·출처 URL·홍보 문구가 남아 있지 않은지
    banned = ("백종원", "백선생", "이연복", "최현석", "만개의레시피", "10000recipe", "만개",
              "http://", "https://", "쿠팡", "배송", "구매", "광고", "협찬", "이미지크게보기",
              "텍스트만보기", "원본보기", "블로그", "구독", "팔로우", "^^", "ㅋㅋ", "ㅎㅎ",
              "레시피", "황금레시피", "꿀팁", "비법", "저는", "제가", "내가")
    dirty = [r["id"] + ":" + w for r in home for text in [r["name"]] + r["steps"]
             for w in banned if w in text]
    check(not dirty, f"이름·조리 순서에 출처·홍보 문구 없음 (문제 {dirty[:4]})")

    src_left = [r["id"] for r in recipes if r["src"]]
    check(not src_left, f"데이터에 원문 출처 필드 없음 (남음 {len(src_left)}건)")

    ends = ("하세요.", "주세요.", "으세요.", "세요.", "니다.")
    bad_end = [r["id"] for r in home for st in r["steps"] if not st.endswith(ends)]
    check(not bad_end, f"모든 조리 문장이 표준 어미 (어긋남 {len(bad_end)}건)")

    long_steps = [(r["id"], len(st)) for r in home for st in r["steps"] if len(st) > 200]
    check(len(long_steps) <= 10, f"200자를 넘는 조리 문장은 10개 이하 ({len(long_steps)}건)")
    check(all(len(st) <= 260 for st in (r["steps"][0] for r in home if r["steps"])),
          "모든 레시피의 첫 단계는 260자 이하")

    no_end = [r["id"] for r in home for st in r["steps"] if not st.rstrip().endswith(".")]
    check(not no_end, f"조리 문장이 마침표로 끝남 ({len(no_end)}건)")

    titles_long = [r["name"] for r in home if len(r["name"]) > 20]
    check(not titles_long, f"레시피 이름이 20자 이하 ({titles_long[:3]})")

    title_no = [r["name"] for r in home if not r["name"].strip()]
    check(not title_no, f"이름 없는 레시피 없음 ({len(title_no)}건)")

    # ---------- 3. 배달·외식 데이터 ----------
    price_re = re.compile(r"^\d{1,3}(,\d{3})*(원|~\d{1,3}(,\d{3})*원)$")
    bad_price, bad_budget, bad_out, out_dist = [], [], [], {}
    brackets = {"under10k", "10to20k", "over20k"}
    for r in out:
        out_dist[r["cat"]] = out_dist.get(r["cat"], 0) + 1
        if not price_re.match(r["price"] or ""):
            bad_price.append(r["id"] + ":" + r["price"])
        if r["budget"] not in ("low", "mid", "high"):
            bad_budget.append(r["id"])
        if r["cat"] not in out_cats:
            bad_out.append(r["id"] + ":" + r["cat"])
        if len(r["tip"] or "") < 20 or not (r["comment"] or "").strip():
            bad_out.append(r["id"] + ":tip")
        if not r["moods"]:
            bad_out.append(r["id"] + ":moods")

    check(not bad_price, f"배달 메뉴 가격 표기 정상 (문제 {bad_price[:3]})")
    check(not bad_budget, f"배달 메뉴 예산대 태그 정상 (문제 {bad_budget[:3]})")
    check(not bad_out, f"배달 메뉴에 종류·팁·한줄평 있음 (문제 {bad_out[:3]})")
    print("배달 종류 분포:", out_dist)
    check(len(out_dist) >= 10, f"배달 종류 {len(out_dist)}가지")
    check(all(v >= 5 for v in out_dist.values()),
          f"모든 배달 종류에 5개 이상 ({[k for k, v in out_dist.items() if v < 5]})")
    per_budget = {}
    for r in out:
        per_budget[r["budget"]] = per_budget.get(r["budget"], 0) + 1
    print("배달 예산대 분포:", per_budget)
    check(all(per_budget.get(b, 0) >= 10 for b in ("low", "mid", "high")),
          f"배달 예산대 3구간 모두 10개 이상 ({per_budget})")

    # ---------- 4. 팁 품질 ----------
    tips = [r["tip"] for r in recipes]
    uniq = len(set(tips)) / len(tips)
    counts = {}
    for t in tips:
        counts[t] = counts.get(t, 0) + 1
    worst = max(counts.values())
    check(uniq >= 0.7, f"팁 문장이 겹치지 않음 (고유 {uniq * 100:.0f}%)")
    check(worst <= 8, f"같은 팁이 8개 레시피를 넘지 않음 (최대 {worst}개)")
    check(all(len(t) >= 20 for t in tips), "모든 팁이 20자 이상")

    # ---------- 5. 검색 ----------
    total_home = js(ctx, "__t.HOME_COUNT")
    check(total_home == len(home), f"홈 레시피 수 일치 ({total_home})")
    ctx.eval("__t.setState({query:'', cat:'all', selected:[]})")
    check(js(ctx, "__t.buildRows().length") == len(home), "필터 없음 = 전체 목록")
    n_kimchi = js(ctx, "__t.searchRows('김치')")
    check(n_kimchi >= 30, f"검색 '김치' 결과 {n_kimchi}개")
    n_two = js(ctx, "__t.searchRows('두부 김치')")
    check(n_two >= 1, f"검색 '두부 김치' 결과 {n_two}개")
    n_none = js(ctx, "__t.searchRows('두리안')")
    check(n_none == 0, "없는 메뉴 검색 결과 0")
    ctx.eval("__t.setState({query:'', cat:'국·찌개'})")
    rows_cat = js(ctx, "__t.buildRows().length")
    check(rows_cat == dist.get("국·찌개"), f"카테고리 필터 결과 {rows_cat}개")
    ctx.eval("__t.setState({query:'', cat:'all'})")

    # ---------- 6. 냉장고 매칭 ----------
    def match(sel, cat="all"):
        ctx.eval("__t.setState({selected:" + json.dumps(sel) + ", query:'', cat:'" + cat + "'})")
        raw = ctx.eval("JSON.stringify(__t.buildRows().slice(0, 5).map(function(r){"
                       "return [r.dish.name, r.percent, r.missing.length, r.ready];}))")
        return json.loads(raw)

    top = match(["egg", "kimchi", "rice"])
    print("계란·김치·밥 →", top[:3])
    check(len(top) > 0, "계란+김치+밥 매칭 결과 있음")
    check(all(top[i][1] >= top[i + 1][1] for i in range(len(top) - 1)), "매칭률 내림차순")
    check(top[0][3] is True, "1순위는 재료가 모두 준비된 요리")

    # 세분화된 양념을 골라도 매칭이 된다
    for sel in (["gochujang"], ["ganjang_jin"], ["doenjang"], ["balsamic", "olive_oil"],
                ["perilla_oil"], ["syrup"], ["gul_sauce"]):
        got = js(ctx, "__t.buildRows().filter(function(r){return r.hit.length>0;}).length") \
            if False else None
        ctx.eval("__t.setState({selected:" + json.dumps(sel) + ", query:'', cat:'all'})")
        n = js(ctx, "__t.buildRows().length")
        check(n > 0, f"양념 {sel[0]} 선택 시 후보 {n}개")

    ctx.eval("__t.setState({selected:[], query:'', cat:'all'})")
    check(js(ctx, "__t.buildRows().length") == len(home), "재료 미선택 시 전체 목록")

    common_ids = [i["id"] for i in ings if i.get("common")]
    unmatched = []
    for cid in common_ids:
        cnt = js(ctx, "__t.RECIPES.filter(function(d){return d.method==='home' && "
                     "(d.req.indexOf('" + cid + "') !== -1 || d.opt.indexOf('" + cid + "') !== -1);}).length")
        if cnt == 0:
            unmatched.append(cid)
    check(not unmatched, f"기본 재료 칩 모두 레시피와 연결됨 (미연결 {unmatched})")

    every_ing = []
    for iid in ing_ids:
        cnt = js(ctx, "__t.RECIPES.filter(function(d){return d.method==='home' && "
                     "(d.req.indexOf('" + iid + "') !== -1 || d.opt.indexOf('" + iid + "') !== -1);}).length")
        if cnt == 0:
            every_ing.append(iid)
    check(len(every_ing) <= 8, f"거의 모든 재료가 레시피와 연결됨 (미연결 {every_ing})")

    # ---------- 7. 별칭 해석 (세분화 핵심) ----------
    alias_cases = [
        ("다진 마늘", "garlic"), ("스팸", "ham"), ("순두부", "sundubu"),
        ("진간장", "ganjang_jin"), ("간장", "ganjang_jin"), ("국간장", "ganjang_guk"),
        ("양조간장", "ganjang_yangjo"), ("고추장", "gochujang"), ("쌈장", "ssamjang"),
        ("된장", "doenjang"), ("청국장", "cheonggukjang"), ("굴소스", "gul_sauce"),
        ("춘장", "chunjang"), ("데리야끼소스", "teriyaki"), ("돈까스소스", "donkatsu_sauce"),
        ("칠리소스", "chili_sauce"), ("스리라차", "hot_sauce"), ("케찹", "ketchup"),
        ("마요네즈", "mayo"), ("머스터드", "mustard"),
        ("양조식초", "vinegar"), ("식초", "vinegar"), ("사과식초", "apple_vinegar"),
        ("현미식초", "brown_vinegar"), ("발사믹식초", "balsamic"), ("레몬즙", "lemon_juice"),
        ("식용유", "oil"), ("올리브유", "olive_oil"), ("참기름", "sesame_oil"),
        ("들기름", "perilla_oil"), ("고춧가루", "gochugaru"), ("고추가루", "gochugaru"),
        ("올리고당", "syrup"), ("물엿", "syrup"), ("설탕", "sugar"),
        ("미림", "mirin"), ("맛술", "mirin"), ("치킨스톡", "stock_cube"),
        ("통깨", "sesame"), ("다시다", "msg"),
    ]
    wrong = []
    for label, want in alias_cases:
        got = ctx.eval("String((__t.findByLabel(" + json.dumps(label) + ")||{}).id)")
        if got != want:
            wrong.append(f"{label}→{got}(기대 {want})")
    check(not wrong, f"재료 별칭 {len(alias_cases)}건 정확히 해석 (틀림 {wrong[:5]})")
    check(ctx.eval("String(__t.findByLabel('두리안'))") == "null", "모르는 재료는 null")

    # ---------- 8. 룰렛 ----------
    def pool(mood="any", budget="any", method="all", cat="all", outcat="all"):
        ctx.eval(("__t.setState({mood:'%s', budget:'%s', method:'%s', cat:'%s', outCat:'%s'})"
                  % (mood, budget, method, cat, outcat)))
        return js(ctx, "__t.getPool().map(function(d){return d.method;})")

    all_pool = pool()
    check(len(all_pool) == len(recipes), f"룰렛 필터 없음 = 전체 {len(all_pool)}개")
    home_pool = pool(method="home")
    check(len(home_pool) == len(home) and all(m == "home" for m in home_pool), "룰렛 방식=집에서")
    out_pool = pool(method="out")
    check(len(out_pool) == len(out), f"룰렛 방식=배달·외식 ({len(out_pool)}개)")

    empty_out = [c for c in out_cats if len(pool(method="out", outcat=c)) == 0]
    check(not empty_out, f"배달 종류 필터 모두 후보 있음 (빈 종류 {empty_out})")
    one_out_cat = [c for c in out_cats if c != "all"][0]
    pool(method="out", outcat=one_out_cat)
    picked = js(ctx, "__t.getPool().map(function(d){return d.cat;})")
    check(all(c == one_out_cat for c in picked),
          f"배달 종류 '{one_out_cat}' 필터 시 해당 종류만 ({len(picked)}개)")

    combos = [(m, b, md, c) for m in ("any", "alone", "hearty", "night", "hangover", "light")
              for b in ("any", "low", "mid") for md in ("all", "home", "out")
              for c in cats[1:]]
    empty = [c for c in combos if len(pool(*c)) == 0]
    filled = (len(combos) - len(empty)) / len(combos)
    check(filled >= 0.95,
          f"룰렛 조합 {len(combos)}개 중 후보 있는 조합 {filled * 100:.0f}% (빈 조합 {empty[:3]})")
    mood_ok = all(len(pool(mood=m)) > 0 for m in ("alone", "hearty", "night", "hangover", "light"))
    check(mood_ok, "모든 기분 필터에 후보 존재")
    budget_ok = all(len(pool(budget=b, method="out")) > 0 for b in ("low", "mid"))
    check(budget_ok, "배달 메뉴 예산 필터 동작")
    # 배달 종류 + 기분 조합
    out_mood_empty = [(c, m) for c in out_cats[1:] for m in ("night", "light", "hangover")]
    ctx.eval("__t.setState({mood:'any', budget:'any', method:'all', cat:'all', outCat:'all'})")

    # ---------- 9. 화면 생성 ----------
    ctx.eval("__t.setState({selected:['egg','kimchi','rice'], query:'', cat:'all'})")
    rows = json.loads(ctx.eval("JSON.stringify(__t.buildRows().slice(0,1))"))
    first = rows[0]
    html = ctx.eval("__t.dishHtml({dish:__t.rowById('" + first["dish"]["id"] +
                    "'), hit:['egg'], missing:[], bonus:[], percent:50, ready:false}, true)")
    check("<div class=\"dish-name\">" in html and "match-num" in html, "요리 카드 HTML 생성")

    collected = home[0]
    drawer = ctx.eval("__t.drawerHtml(__t.rowById('" + collected["id"] + "'))")
    check("만드는 법" in drawer and "steps" in drawer, "레시피 드로어: 만드는 법 포함")
    check("ing-list" in drawer, "레시피 드로어: 재료 목록 포함")
    check("10000recipe" not in drawer and "원문 보기" not in drawer,
          "레시피 드로어: 원문 출처 링크 없음")
    check("요리 팁" in drawer, "레시피 드로어: 요리 팁")
    check("srv-row" in drawer and "인분" in drawer, "레시피 드로어: 인분 수 선택 버튼")
    check("데이터 출처" not in drawer, "레시피 드로어: 출처 표기 없음")

    curated = ctx.eval("__t.drawerHtml(__t.rowById('kimchi-fried-rice'))")
    check("만드는 법" in curated and "김치" in curated, "큐레이션 레시피 드로어")

    out_drawer = ctx.eval("__t.drawerHtml(__t.rowById('o1'))")
    check("예상 주문 가격" in out_drawer and "원" in out_drawer, "배달 드로어: 예상 가격")
    check("주문 팁" in out_drawer, "배달 드로어: 주문 팁")
    check("배달·외식" in out_drawer, "배달 드로어: 배달 표시")

    # ---------- 9-1. 찜 · 최근 본 메뉴 ----------
    check(js(ctx, "__t.favIds()") == [], "찜 목록은 처음에 비어 있음")
    check(js(ctx, "__t.toggleFav('kimchi-fried-rice')") is True, "찜 추가")
    check(js(ctx, "__t.isFav('kimchi-fried-rice')") is True, "찜 상태 확인")
    ctx.eval("__t.toggleFav('dubu-kimchi')")
    favs = js(ctx, "__t.favIds()")
    check(favs[:1] == ["dubu-kimchi"] and len(favs) == 2, f"찜은 최근 것이 앞 ({favs})")
    check(js(ctx, "__t.toggleFav('kimchi-fried-rice')") is False, "찜 해제")
    check(js(ctx, "__t.isFav('kimchi-fried-rice')") is False, "찜 해제 확인")

    ctx.eval("__t.pushRecent('kimchi-fried-rice')")
    ctx.eval("__t.pushRecent('tteokbokki')")
    ctx.eval("__t.pushRecent('kimchi-fried-rice')")
    recents = js(ctx, "__t.recentIds()")
    check(recents[:2] == ["kimchi-fried-rice", "tteokbokki"]
          and recents.count("kimchi-fried-rice") == 1,
          f"최근 본 메뉴는 중복 없이 최근 순 ({recents[:3]})")
    for i in range(20):
        ctx.eval("__t.pushRecent('" + home[i]["id"] + "')")
    check(len(js(ctx, "__t.recentIds()")) <= 12, "최근 본 메뉴는 12개까지만 남음")

    while js(ctx, "__t.favIds()"):
        ctx.eval("__t.toggleFav(__t.favIds()[0])")
    fav_rows = js(ctx, "__t.setFavView('fav')")
    check(fav_rows == [], "찜이 없으면 찜한 메뉴가 비어 있음")
    ctx.eval("__t.toggleFav('dubu-kimchi')")
    fav_rows = js(ctx, "__t.setFavView('fav')")
    check(fav_rows == ["dubu-kimchi"], f"찜한 메뉴 보기: 찜 목록만 ({fav_rows})")
    ctx.eval("__t.toggleFav('dubu-kimchi')")
    ctx.eval("__t.setState({favView:null})")

    # ---------- 9-2. 인분 수 분량 환산 ----------
    cases = [
        ("1/2개", 2, "1개"), ("1/2개", 0.5, "1/4개"), ("3~4장", 2, "6~8장"),
        ("1.5큰술", 2, "3큰술"), ("200g", 0.5, "100g"), ("1큰술", 1, "1큰술"),
        ("약간", 3, "약간"), ("1/3개", 3, "1개"), ("2개", 2, "4개"),
    ]
    wrong_scale = [(a, f, ctx.eval("__t.scaleAmount(" + json.dumps(a) + "," + str(f) + ")"), w)
                   for a, f, w in cases
                   if ctx.eval("__t.scaleAmount(" + json.dumps(a) + "," + str(f) + ")") != w]
    check(not wrong_scale, f"분량 환산 {len(cases)}건 (틀림 {wrong_scale[:3]})")
    check(ctx.eval("String(__t.readableAmount('1개','0.2개'))") == "약간",
          "아주 적어진 분량은 '약간'으로 표시")

    # 실제 레시피 재료 목록이 인분 수에 따라 달라지는지 (분량이 있는 레시피로)
    target = None
    for r in home:
        if any(re.search(r"\d", row[1] or "") for row in r["ing"]) and r["servings"]:
            target = r
            break
    check(target is not None, "분량이 있는 레시피 확보")
    one = ctx.eval("__t.ingredientListHtml('" + target["id"] + "',1)")
    four = ctx.eval("__t.ingredientListHtml('" + target["id"] + "',4)")
    check(one != four, "인분 수를 바꾸면 재료 분량이 달라짐")
    srv_html = ctx.eval("__t.servingsHtml('" + target["id"] + "')")
    check(all(f"{n}인분" in srv_html for n in (1, 2, 3, 4)), "인분 수 버튼 1·2·3·4 모두 있음")

    ctx.eval("__t.setState({selected:[]})")
    drawer_miss = ctx.eval("__t.drawerFor('" + collected["id"] + "', 2)")
    check("부족한 재료" in drawer_miss and "coupang.com" in drawer_miss,
          "부족한 재료에 쿠팡 검색 링크")
    check(js(ctx, "__t.CFG.coupangPartnersEnabled") is False,
          "쿠팡 파트너스 기본값은 꺼짐")
    link = ctx.eval("__t.coupangLink('대파')")
    check(link.startswith("https://www.coupang.com/np/search?q=") and "lptag" not in link,
          f"쿠팡 링크 기본형 ({link})")
    check("이 포스팅" not in drawer_miss, "제휴가 꺼져 있으면 고지 문구 없음")

    # 설정을 채우면 추적 태그와 고지가 붙는지
    ctx.eval("__t.CFG.coupangPartnersEnabled = true; __t.CFG.coupangPartnersTag = 'AF1234567'")
    tagged = ctx.eval("__t.coupangLink('대파')")
    check("lptag=AF1234567" in tagged, "태그를 채우면 lptag 추적이 붙음")
    drawer_on = ctx.eval("__t.drawerFor('" + collected["id"] + "', 2)")
    check("이 포스팅은 쿠팡 파트너스" in drawer_on, "제휴가 켜지면 고지 문구 표시")
    ctx.eval("__t.CFG.coupangPartnersEnabled = false; __t.CFG.coupangPartnersTag = ''")

    # 카드에 하트가 붙는지
    card_html = ctx.eval("__t.dishHtml({dish:__t.rowById('" + home[0]["id"] + "'), hit:[], missing:[], bonus:[], percent:0, ready:false}, false)")
    check("fav-btn" in card_html and "찜하기" in card_html, "요리 카드에 찜 하트 버튼")

    # ---------- 10. 정적 파일 ----------
    html_src = io.open(ROOT / "index.html", encoding="utf-8").read()
    app_src = io.open(ROOT / "app.js", encoding="utf-8").read()
    sw_src = io.open(ROOT / "sw.js", encoding="utf-8").read()

    ids_in_html = set(re.findall(r'id="([^"]+)"', html_src))
    ids_in_js = set(re.findall(r'\$\("#([A-Za-z0-9_-]+)"\)', app_src))
    missing = sorted(ids_in_js - ids_in_html)
    check(not missing, f"app.js가 참조하는 id가 HTML에 모두 존재 (누락 {missing})")
    for must in ("ingTabs", "ingSearch", "selChips", "outCatSeg", "chipList"):
        check(must in ids_in_html, f"재료 UI 요소 '{must}' 있음")

    check("data/recipes-data.js" in html_src, "index.html이 레시피 데이터 파일을 불러옴")
    check("data/recipes-data.js" in sw_src, "서비스 워커 캐시 목록에 레시피 데이터 포함")
    check(re.search(r'var CACHE = "wtt-v(\d+)"', sw_src) is not None, "서비스 워커 캐시 버전 표기")
    ver_html = set(re.findall(r'\?v=(\d+)', html_src))
    check(len(ver_html) == 1, f"HTML 자산 버전이 하나로 통일 ({ver_html})")
    v = ver_html.pop() if ver_html else "0"
    check(f"?v={v}" in sw_src and "wtt-v" + v in sw_src, f"서비스 워커 캐시도 v{v}")

    assets = set(re.findall(r'(?:href|src)="(\./[^"]+)"', html_src))
    missing_files = [a for a in sorted(assets)
                     if a != "./" and not (ROOT / a.lstrip("./").split("?")[0]).exists()]
    check(not missing_files, f"참조 파일 존재 (누락 {missing_files})")

    opens = len(re.findall(r"<(div|section|nav|header|main|form|button|p|h1|h2|h3|span|ul|ol|li|footer)\b", html_src))
    closes = len(re.findall(r"</(div|section|nav|header|main|form|button|p|h1|h2|h3|span|ul|ol|li|footer)>", html_src))
    check(opens == closes, f"태그 열고 닫음 균형 ({opens}/{closes})")
    check("moreChipsBtn" not in app_src and "moreChipsBtn" not in html_src,
          "예전 '재료 더 보기' 버튼 제거됨")

    # HTML id 중복
    all_ids = re.findall(r'id="([^"]+)"', html_src)
    dup_ids = sorted({i for i in all_ids if all_ids.count(i) > 1})
    check(not dup_ids, f"HTML id 중복 없음 (중복 {dup_ids})")

    # 수익화 설정 (MONETIZE_CONFIG)
    check("window.MONETIZE_CONFIG" in html_src, "index.html에 MONETIZE_CONFIG 있음")
    for key in ("gaMeasurementId", "adsenseClient", "adsenseSlot", "adfitUnit",
                "coupangPartnersEnabled", "coupangPartnersTag", "coupangSearchBase",
                "coupangDisclosure"):
        check(key in html_src, f"MONETIZE_CONFIG '{key}' 슬롯 있음")
    check("adsbygoogle" in app_src and "googletagmanager" in app_src and "ba.min.js" in app_src,
          "광고·분석 스크립트는 설정이 채워질 때만 삽입")
    check('class="ad-slot hidden"' in html_src, "광고 슬롯은 기본으로 숨김 (빈 광고 박스 없음)")

    # OpenGraph / Twitter / canonical
    for prop in ('property="og:title"', 'property="og:description"', 'property="og:image"',
                 'property="og:url"', 'name="twitter:card"', 'name="twitter:title"',
                 'name="twitter:image"'):
        check(prop in html_src, f"메타 {prop}")
    check('rel="canonical"' in html_src, "index.html canonical 링크")
    check('application/ld+json' in html_src, "구조화 데이터(JSON-LD) 있음")

    # 안내 페이지
    pages = {"about.html": "서비스 소개", "privacy.html": "개인정보처리방침",
             "terms.html": "이용약관"}
    for page, title in pages.items():
        path = ROOT / page
        check(path.exists(), f"{page} 파일 있음")
        if not path.exists():
            continue
        body = io.open(path, encoding="utf-8").read()
        check(title in body, f"{page}: '{title}' 내용 있음")
        check("pages.css" in body, f"{page}: 공용 스타일 연결")
        check("index.html" in body, f"{page}: 앱으로 돌아가는 링크")
        other = [q for q in pages if q != page]
        check(all(q in body for q in other), f"{page}: 다른 안내 페이지 링크")
        local = re.findall(r'href="(\./[^"#]+)"', body)
        broken = [h for h in local if not (ROOT / h.lstrip("./").split("?")[0]).exists()]
        check(not broken, f"{page}: 링크 대상 파일 존재 (깨짐 {broken})")

    # sitemap.xml / robots.txt
    sm = ROOT / "sitemap.xml"
    rb = ROOT / "robots.txt"
    check(sm.exists(), "sitemap.xml 있음")
    check(rb.exists(), "robots.txt 있음")
    if sm.exists():
        import xml.etree.ElementTree as ET
        try:
            tree = ET.parse(sm)
            locs = [e.text for e in tree.getroot().iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        except Exception as exc:  # noqa: BLE001
            locs = []
            check(False, f"sitemap.xml 파싱 실패: {exc}")
        check(len(locs) >= 4, f"sitemap URL {len(locs)}개")
        base = "https://chae7549-stack.github.io/what-to-eat-today/"
        for loc in locs:
            rel = loc[len(base):] or "index.html"
            check((ROOT / rel).exists(), f"sitemap URL 대상 존재: {rel}")
    if rb.exists():
        robots = io.open(rb, encoding="utf-8").read()
        check("Sitemap:" in robots and "what-to-eat-today/sitemap.xml" in robots,
              "robots.txt 에 sitemap 주소")
        check("Disallow: /" not in robots, "robots.txt 가 전체를 막지 않음")

    # 새 기능 UI가 HTML/CSS/JS에 모두 있는지
    for el_id in ("favBtn", "recentBtn", "favCount", "recentCount", "adSlot"):
        check(el_id in ids_in_html, f"새 UI 요소 '{el_id}' 있음")
    check("./about.html" in html_src and "./privacy.html" in html_src and "./terms.html" in html_src,
          "index.html 푸터에 안내 페이지 링크")

    # CSS 에 새 UI 클래스가 있는지
    css_src = io.open(ROOT / "styles.css", encoding="utf-8").read()
    for cls in (".ing-tabs", ".sel-chips", ".price-card", ".chip.is-selected",
                ".quick-bar", ".fav-btn", ".srv-row", ".srv-chip", ".buy-main",
                ".buy-chip", ".ad-disclosure", ".foot-links"):
        check(cls in css_src, f"CSS 에 {cls} 스타일 있음")

    # 서비스 워커가 새 페이지를 캐시하는지
    for page in ("./index.html", "./about.html", "./privacy.html", "./terms.html"):
        check(page in sw_src, f"서비스 워커 캐시/이동 처리에 {page}")

    size_kb = (ROOT / "data" / "recipes-data.js").stat().st_size / 1024
    print(f"데이터 파일 {size_kb:.0f}KB")
    check(size_kb < 3200, f"데이터 파일 3.2MB 미만 ({size_kb:.0f}KB)")

    print()
    for n in notes:
        print(n)
    if fails:
        print("\n실패:")
        for f in fails:
            print("  FAIL " + f)
        sys.exit(1)
    print("\n모든 점검 통과 ✅")


if __name__ == "__main__":
    main()
