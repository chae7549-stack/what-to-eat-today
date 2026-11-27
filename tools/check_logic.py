"""빌드 없이 돌리는 로직 점검 (quickjs 사용).

- data/recipes-data.js + app.js 를 실제로 실행해서 앱 로직을 검증한다
  (DOM은 가짜 객체로 대체)
- 레시피 데이터 정합성: 1,000개 이상, 빈 재료/조리순서 0건, id·제목 중복 0건
- 재료 분류(taxonomy) 유효성, 검색, 냉장고 매칭, 룰렛 필터, 드로어 HTML

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
      id: id, innerHTML: "", textContent: "", hidden: false, disabled: false,
      style: { setProperty: function () {} }, dataset: {},
      classList: { add: function () {}, remove: function () {}, toggle: function () {} },
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
        { dataset: { view: "fridge" }, setAttribute: function () {}, addEventListener: function () {} },
        { dataset: { view: "roulette" }, setAttribute: function () {}, addEventListener: function () {} }
      ];
    }
    return [];
  },
  createElement: function () {
    return {
      style: { setProperty: function () {} }, classList: { add: function () {}, remove: function () {}, toggle: function () {} },
      dataset: {}, children: [], innerHTML: "", textContent: "",
      appendChild: function (n) { this.children.push(n); return n; },
      removeChild: function () {},
      addEventListener: function () {}, setAttribute: function () {},
      querySelector: function () { return null; }, querySelectorAll: function () { return []; },
    };
  },
  createDocumentFragment: function () {
    return {
      children: [],
      appendChild: function (n) { this.children.push(n); return n; },
    };
  },
  body: { style: {}, appendChild: function () {}, removeChild: function () {} }
};
var window = { addEventListener: function () {}, scrollTo: function () {}, RECIPE_DB: null };
var navigator = {};
var location = { protocol: "http:", href: "https://example.com/" };
var localStorage = { getItem: function () { return null; }, setItem: function () {} };
"""

PROBE = r"""
globalThis.__t = {
  INGREDIENTS: INGREDIENTS,
  RECIPES: RECIPES.map(function (d) {
    return { id: d.id, name: d.name, cat: d.cat, emoji: d.emoji, time: d.time,
             level: d.level, moods: d.moods, budget: d.budget, method: d.method, price: d.price,
             req: d.req, opt: d.opt, ing: d.ing, steps: d.steps, src: d.src, curated: !!d.curated };
  }),
  HOME_COUNT: HOME_RECIPES.length,
  ALL_COUNT: ALLDISH.length,
  CATEGORIES: CATEGORIES,
  state: state,
  matchRows: matchRows,
  buildRows: buildRows,
  getPool: getPool,
  findByLabel: findByLabel,
  formatTime: formatTime,
  openDrawer: openDrawer,
  drawerHtml: function (d) { openDrawer(d); return __el("drawerPanel").innerHTML; },
  dishHtml: function (row, showMatch) {
    var node = dishNode(row, 0, showMatch);
    return node.innerHTML;
  },
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
    ctx.eval(data)  # window.RECIPE_DB 정의
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
    home = [r for r in recipes if r["method"] == "home"]
    out = [r for r in recipes if r["method"] == "out"]

    print(f"재료 분류 {len(ings)}종 · 레시피 {len(recipes)}개 (집밥 {len(home)} / 배달·외식 {len(out)})")

    # ---------- 1. 규모 ----------
    check(len(ings) >= 100, f"재료 분류 100종 이상 ({len(ings)}종)")
    check(len(home) >= 1000, f"집밥 레시피 1,000개 이상 ({len(home)}개)")
    check(len(recipes) >= 1000, f"전체 레시피 1,000개 이상 ({len(recipes)}개)")

    ing_ids = [i["id"] for i in ings]
    check(len(ing_ids) == len(set(ing_ids)), "재료 id 중복 없음")

    ids = [r["id"] for r in recipes]
    check(len(ids) == len(set(ids)), "레시피 id 중복 없음")

    def norm(t):
        return re.sub(r"[^0-9a-z가-힣]", "", (t or "").lower())

    titles = [norm(r["name"]) for r in recipes]
    dup_titles = sorted({t for t in titles if titles.count(t) > 1})
    check(not dup_titles, f"레시피 제목 중복 없음 (중복 {dup_titles[:5]})")

    # ---------- 2. 데이터 정합성 ----------
    empty_ing, empty_steps, short_steps, bad_req, bad_cat = [], [], [], [], []
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
        else:
            if not r.get("price"):
                bad_cat.append(r["id"] + ":price")

    check(not empty_ing, f"모든 레시피에 재료 있음 (빈 재료 {len(empty_ing)}건)")
    check(not empty_steps, f"모든 레시피에 조리 순서 있음 (빈 순서 {len(empty_steps)}건)")
    check(not short_steps, f"조리 순서가 2단계·40자 이상 (부실 {len(short_steps)}건)")
    check(not bad_req, f"필수 재료 2개 이상·모두 유효 id (문제 {bad_req[:5]})")
    check(not bad_cat, f"카테고리·시간·난이도 유효 (문제 {bad_cat[:5]})")

    # 카테고리 분포
    dist = {}
    for r in home:
        dist[r["cat"]] = dist.get(r["cat"], 0) + 1
    print("카테고리 분포:", dist)
    check(all(dist.get(c, 0) >= 50 for c in cats if c != "all" and c != "배달·외식"),
          "모든 카테고리에 50개 이상")
    check(len(dist) >= 6, "카테고리 6종 이상")

    # 출처
    src_cnt = sum(1 for r in home if r["src"].startswith("https://www.10000recipe.com/recipe/"))
    check(src_cnt >= 1000, f"원문 출처 링크가 있는 레시피 {src_cnt}개")

    # ---------- 3. 검색 ----------
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

    # ---------- 4. 냉장고 매칭 ----------
    def match(sel, cat="all"):
        ctx.eval("__t.setState({selected:" + json.dumps(sel) + ", query:'', cat:'" + cat + "'})")
        rows = js(ctx, "[[r.dish.name, r.percent, r.missing.length, r.ready] for r in []]") if False else None
        raw = ctx.eval("JSON.stringify(__t.buildRows().slice(0, 5).map(function(r){"
                       "return [r.dish.name, r.percent, r.missing.length, r.ready];}))")
        import json as _j
        return _j.loads(raw)

    top = match(["egg", "kimchi", "rice"])
    print("계란·김치·밥 →", top[:3])
    check(len(top) > 0, "계란+김치+밥 매칭 결과 있음")
    check(all(top[i][1] >= top[i + 1][1] for i in range(len(top) - 1)), "매칭률 내림차순")
    check(top[0][3] is True, "1순위는 재료가 모두 준비된 요리")

    many = match(["onion", "egg", "kimchi", "tofu", "pa", "rice", "pork", "potato", "carrot", "bean"])
    check(len(many) > 0, "재료 10개 선택 시 매칭 동작")

    ctx.eval("__t.setState({selected:[], query:'', cat:'all'})")
    check(js(ctx, "__t.buildRows().length") == len(home), "재료 미선택 시 전체 목록")

    # 모든 주요 재료가 최소 1개 레시피에 매칭되는지
    common_ids = [i["id"] for i in ings if i.get("common")]
    unmatched = []
    for cid in common_ids:
        cnt = js(ctx, "__t.RECIPES.filter(function(d){return d.method==='home' && "
                     "(d.req.indexOf('" + cid + "') !== -1 || d.opt.indexOf('" + cid + "') !== -1);}).length")
        if cnt == 0:
            unmatched.append(cid)
    check(not unmatched, f"기본 재료 칩 모두 레시피와 연결됨 (미연결 {unmatched})")

    # ---------- 5. 별칭 해석 ----------
    check(ctx.eval("__t.findByLabel('다진 마늘').id") == "garlic", "직접 입력 별칭: 다진 마늘 → 마늘")
    check(ctx.eval("__t.findByLabel('스팸').id") == "ham", "직접 입력 별칭: 스팸 → 햄")
    check(ctx.eval("__t.findByLabel('순두부').id") == "sundubu", "직접 입력 별칭: 순두부")
    check(ctx.eval("String(__t.findByLabel('두리안'))") == "null", "모르는 재료는 null")

    # ---------- 6. 룰렛 ----------
    def pool(mood="any", budget="any", method="all", cat="all"):
        ctx.eval("__t.setState({mood:'%s', budget:'%s', method:'%s', cat:'%s'})" % (mood, budget, method, cat))
        return js(ctx, "__t.getPool().map(function(d){return d.method;})")

    all_pool = pool()
    check(len(all_pool) == len(recipes), f"룰렛 필터 없음 = 전체 {len(all_pool)}개")
    home_pool = pool(method="home")
    check(len(home_pool) == len(home) and all(m == "home" for m in home_pool), "룰렛 방식=집에서")
    out_pool = pool(method="out")
    check(len(out_pool) == len(out), "룰렛 방식=배달·외식")
    combos = [(m, b, md, c) for m in ("any", "alone", "hearty", "night", "hangover", "light")
              for b in ("any", "low", "mid") for md in ("all", "home", "out")
              for c in ("all", "밥·죽", "국·찌개", "면·파스타", "볶음·구이", "반찬", "전·부침", "분식·야식", "양식·기타")]
    empty = [c for c in combos if len(pool(*c)) == 0]
    filled = (len(combos) - len(empty)) / len(combos)
    check(filled >= 0.95,
          f"룰렛 필터 조합 {len(combos)}개 중 후보 있는 조합 {filled * 100:.0f}% (빈 조합 {empty[:3]})")
    cat_ok = all(len(pool(mood="any", cat=c)) > 0 for c in
                 ("밥·죽", "국·찌개", "면·파스타", "볶음·구이", "반찬", "전·부침", "분식·야식", "양식·기타"))
    check(cat_ok, "모든 카테고리에 룰렛 후보 존재")
    mood_ok = all(len(pool(mood=m)) > 0 for m in ("alone", "hearty", "night", "hangover", "light"))
    check(mood_ok, "모든 기분 필터에 룰렛 후보 존재")
    check(len(pool(cat="국·찌개")) > 50, "룰렛 카테고리 필터 동작")
    ctx.eval("__t.setState({mood:'any', budget:'any', method:'all', cat:'all'})")

    # ---------- 7. 화면 생성 ----------
    ctx.eval("__t.setState({selected:['egg','kimchi','rice'], query:'', cat:'all'})")
    rows = ctx.eval("JSON.stringify(__t.buildRows().slice(0,1))")
    first = json.loads(rows)[0]
    html = ctx.eval("__t.dishHtml({dish:__t.rowById('" + first["dish"]["id"] + "'), hit:['egg'], missing:[], bonus:[], percent:50, ready:false}, true)")
    check("<div class=\"dish-name\">" in html and "match-num" in html, "요리 카드 HTML 생성")

    collected = [r for r in recipes if r["src"]][0]
    drawer = ctx.eval("__t.drawerHtml(__t.rowById('" + collected["id"] + "'))")
    check("만드는 법" in drawer and "steps" in drawer, "레시피 드로어: 만드는 법 포함")
    check("ing-list" in drawer, "레시피 드로어: 재료 목록 포함")
    check("10000recipe.com" in drawer, "레시피 드로어: 원문 출처 링크")

    curated = ctx.eval("__t.drawerHtml(__t.rowById('kimchi-fried-rice'))")
    check("만드는 법" in curated and "김치" in curated, "큐레이션 레시피 드로어")

    # ---------- 8. 정적 파일 ----------
    html_src = io.open(ROOT / "index.html", encoding="utf-8").read()
    app_src = io.open(ROOT / "app.js", encoding="utf-8").read()
    sw_src = io.open(ROOT / "sw.js", encoding="utf-8").read()

    ids_in_html = set(re.findall(r'id="([^"]+)"', html_src))
    ids_in_js = set(re.findall(r'\$\("#([A-Za-z0-9_-]+)"\)', app_src))
    missing = sorted(ids_in_js - ids_in_html)
    check(not missing, f"app.js가 참조하는 id가 HTML에 모두 존재 (누락 {missing})")

    check("./data/recipes-data.js" in html_src, "index.html이 레시피 데이터 파일을 불러옴")
    check("./data/recipes-data.js" in sw_src, "서비스 워커 캐시 목록에 레시피 데이터 포함")
    check("wtt-v2" in sw_src, "서비스 워커 캐시 버전 갱신")

    assets = set(re.findall(r'(?:href|src)="(\./[^"]+)"', html_src))
    missing_files = [a for a in sorted(assets) if a != "./" and not (ROOT / a.lstrip("./")).exists()]
    check(not missing_files, f"참조 파일 존재 (누락 {missing_files})")

    opens = len(re.findall(r"<(div|section|nav|header|main|form|button|p|h1|h2|h3|span|ul|ol|li|footer)\b", html_src))
    closes = len(re.findall(r"</(div|section|nav|header|main|form|button|p|h1|h2|h3|span|ul|ol|li|footer)>", html_src))
    check(opens == closes, f"태그 열고 닫음 균형 ({opens}/{closes})")

    # 데이터 파일 크기
    size_kb = (ROOT / "data" / "recipes-data.js").stat().st_size / 1024
    print(f"데이터 파일 {size_kb:.0f}KB")
    check(size_kb < 3000, f"데이터 파일 3MB 미만 ({size_kb:.0f}KB)")

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
