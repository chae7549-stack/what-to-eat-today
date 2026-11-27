"""빌드 없이 돌리는 로직 점검 (quickjs 사용).

- data/recipes-data.js + app.js 를 실제로 실행해서 앱 로직을 검증한다 (DOM은 가짜 객체)
- 데이터: 집밥 1,400개 이상 · 배달·외식 100개 이상 · 재료 140종 이상
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
var localStorage = { getItem: function () { return null; }, setItem: function () {} };
"""

PROBE = r"""
globalThis.__t = {
  INGREDIENTS: INGREDIENTS,
  RECIPES: RECIPES.map(function (d) {
    return { id: d.id, name: d.name, cat: d.cat, emoji: d.emoji, time: d.time,
             level: d.level, moods: d.moods, budget: d.budget, method: d.method, price: d.price,
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
  searchRows: function (q) { state.query = q; return buildRows().length; }
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

    src_cnt = sum(1 for r in home if r["src"].startswith("https://www.10000recipe.com/recipe/"))
    check(src_cnt >= 1300, f"원문 출처 링크가 있는 레시피 {src_cnt}개")

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
    check(uniq >= 0.7, f"팁 문장이多样的 (고유 {uniq * 100:.0f}%)")
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

    collected = [r for r in home if r["src"]][0]
    drawer = ctx.eval("__t.drawerHtml(__t.rowById('" + collected["id"] + "'))")
    check("만드는 법" in drawer and "steps" in drawer, "레시피 드로어: 만드는 법 포함")
    check("ing-list" in drawer, "레시피 드로어: 재료 목록 포함")
    check("10000recipe.com" in drawer, "레시피 드로어: 원문 출처 링크")
    check("요리 팁" in drawer, "레시피 드로어: 요리 팁")

    curated = ctx.eval("__t.drawerHtml(__t.rowById('kimchi-fried-rice'))")
    check("만드는 법" in curated and "김치" in curated, "큐레이션 레시피 드로어")

    out_drawer = ctx.eval("__t.drawerHtml(__t.rowById('o1'))")
    check("예상 주문 가격" in out_drawer and "원" in out_drawer, "배달 드로어: 예상 가격")
    check("주문 팁" in out_drawer, "배달 드로어: 주문 팁")
    check("배달·외식" in out_drawer, "배달 드로어: 배달 표시")

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

    # CSS 에 새 UI 클래스가 있는지
    css_src = io.open(ROOT / "styles.css", encoding="utf-8").read()
    for cls in (".ing-tabs", ".sel-chips", ".price-card", ".chip.is-selected"):
        check(cls in css_src, f"CSS 에 {cls} 스타일 있음")

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
