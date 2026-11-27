"""빌드 없이 돌리는 로직 점검 (quickjs 사용).

- 요리 데이터 정합성 (재료 id 존재, 단계 수, id 중복)
- 냉장고 매칭 결과 순서/퍼센트
- 룰렛 필터 동작
- index.html 이 참조하는 id·파일 존재

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


def load_app_source():
    src = io.open(ROOT / "app.js", encoding="utf-8").read()
    probe = """
    globalThis.__t = {
      INGREDIENTS: INGREDIENTS,
      DISHES: DISHES,
      matchDishes: matchDishes,
      getPool: getPool,
      state: state,
      findByLabel: findByLabel,
      shareText: shareText,
      setTabState: function (o) { for (var k in o) state[k] = o[k]; },
      escapeHtml: escapeHtml
    };
    """
    assert src.rstrip().endswith("})();"), "app.js 구조가 예상과 다릅니다"
    idx = src.rstrip().rfind("})();")
    return src[:idx] + probe + "\n})();\n"


def stub_prelude():
    return """
    var __listeners = {};
    var document = {
      readyState: "loading",
      addEventListener: function (k, f) { __listeners[k] = f; },
      querySelector: function () { return null; },
      querySelectorAll: function () { return []; },
      createElement: function () { return { style: {}, classList: { add: function(){}, remove: function(){}, toggle: function(){} }, appendChild: function(){}, addEventListener: function(){}, setAttribute: function(){}, dataset: {} }; },
      body: { style: {}, appendChild: function(){}, removeChild: function(){} }
    };
    var window = { addEventListener: function(){}, scrollTo: function(){} };
    var navigator = {};
    var location = { protocol: "http:", href: "https://example.com/" };
    var localStorage = { getItem: function(){ return null; }, setItem: function(){} };
    """


def main():
    ctx = quickjs.Context()
    ctx.eval(stub_prelude())
    ctx.eval(load_app_source())

    ings = json.loads(ctx.eval("JSON.stringify(__t.INGREDIENTS)"))
    dishes = json.loads(ctx.eval("JSON.stringify(__t.DISHES)"))

    ing_ids = [i["id"] for i in ings]
    dish_ids = [d["id"] for d in dishes]
    home = [d for d in dishes if d["method"] == "home"]
    out = [d for d in dishes if d["method"] == "out"]

    print(f"재료 {len(ings)}개 · 요리 {len(dishes)}개 (집밥 {len(home)} / 배달·외식 {len(out)})")
    check(len(ings) >= 19, "재료 19종 이상")
    check(len(ings) == len(set(ing_ids)), "재료 id 중복 없음")
    check(len(dishes) >= 35, "요리 35종 이상")
    check(len(dishes) == len(set(dish_ids)), "요리 id 중복 없음")

    good_dish = True
    for d in dishes:
        for key in ("id", "name", "emoji", "moods", "budget", "method"):
            if key not in d:
                fails.append(f"{d.get('id')}: 필드 {key} 없음")
                good_dish = False
        for rid in d["req"] + d.get("opt", []):
            if rid not in ing_ids:
                fails.append(f"{d['id']}: 알 수 없는 재료 id '{rid}'")
                good_dish = False
        if d["method"] == "home":
            if not (3 <= len(d.get("steps", [])) <= 4):
                fails.append(f"{d['id']}: 단계 수 {len(d.get('steps', []))} (3~4 필요)")
                good_dish = False
            if not d["req"]:
                fails.append(f"{d['id']}: 집밥인데 필수 재료가 없음")
                good_dish = False
            if not isinstance(d.get("time"), int):
                fails.append(f"{d['id']}: 조리 시간 없음")
                good_dish = False
        else:
            if not d.get("price"):
                fails.append(f"{d['id']}: 배달 메뉴인데 가격 표기 없음")
                good_dish = False
        for mood in d["moods"]:
            if mood not in ("alone", "hearty", "night", "hangover", "light"):
                fails.append(f"{d['id']}: 알 수 없는 mood '{mood}'")
                good_dish = False
        if d["budget"] not in ("low", "mid", "high"):
            fails.append(f"{d['id']}: 알 수 없는 budget '{d['budget']}'")
            good_dish = False
    check(good_dish, "모든 요리 데이터 정합성")

    # ---- 매칭 로직 ----
    order = json.loads(ctx.eval(
        "(() => { __t.state.selected = ['egg','kimchi','rice'];"
        " var r = __t.matchDishes();"
        " return JSON.stringify(r.all.slice(0,3).map(x => [x.dish.name, x.percent, x.missing.length])); })()"
    ))
    print("계란·김치·밥 →", order)
    check(order[0][0] == "김치볶음밥" and order[0][1] == 100, "계란+김치+밥 = 김치볶음밥 100% 최상위")
    check(all(order[i][1] >= order[i + 1][1] for i in range(len(order) - 1)), "매칭률 내림차순 정렬")

    empty = json.loads(ctx.eval(
        "(() => { __t.state.selected = []; return JSON.stringify(__t.matchDishes().all.length); })()"
    ))
    check(empty == 0, "재료 미선택 시 매칭 결과 없음")

    unknown = ctx.eval("__t.findByLabel('다진 마늘').id")
    check(unknown == "garlic", "직접 입력 별칭 해석 (다진 마늘 → 마늘)")
    unknown2 = ctx.eval("__t.findByLabel('스팸').id")
    check(unknown2 == "ham", "직접 입력 별칭 해석 (스팸 → 스팸·햄)")
    unknown3 = ctx.eval("String(__t.findByLabel('두리안'))")
    check(unknown3 == "null", "알 수 없는 재료는 null")

    # ---- 룰렛 필터 ----
    def pool(mood="any", budget="any", method="all"):
        return json.loads(ctx.eval(
            f"(() => {{ __t.setTabState({{mood:'{mood}',budget:'{budget}',method:'{method}'}});"
            " return JSON.stringify(__t.getPool().map(d => d.method)); })()"
        ))

    all_pool = pool()
    check(len(all_pool) == len(dishes), f"필터 없음 = 전체 {len(all_pool)}개")
    home_pool = pool(method="home")
    check(all(m == "home" for m in home_pool) and len(home_pool) == len(home), "방식=집에서 만들기")
    out_pool = pool(method="out")
    check(all(m == "out" for m in out_pool) and len(out_pool) == len(out), "방식=배달·외식")
    night = pool(mood="night")
    check(len(night) > 0, f"야식 후보 {len(night)}개")
    combos = [(m, b, md) for m in ("any", "alone", "hearty", "night", "hangover", "light")
              for b in ("any", "low", "mid") for md in ("all", "home", "out")]
    empty_combos = [c for c in combos if len(pool(*c)) == 0]
    check(not empty_combos, f"모든 필터 조합에 후보 존재 (빈 조합 {empty_combos})")
    sizes = sorted((len(pool(*c)), c) for c in combos)
    print("가장 적은 후보 조합:", sizes[0])

    # ---- 공유 문구 ----
    text = ctx.eval("__t.shareText(__t.DISHES[0])")
    check("오늘 메뉴는 김치볶음밥 당첨!" in text, "공유 문구 형식")

    # ---- index.html 참조 확인 ----
    html = io.open(ROOT / "index.html", encoding="utf-8").read()
    app = io.open(ROOT / "app.js", encoding="utf-8").read()
    ids_in_html = set(re.findall(r'id="([^"]+)"', html))
    ids_in_js = set(re.findall(r'\$\("#([A-Za-z0-9_-]+)"\)', app))
    missing = sorted(ids_in_js - ids_in_html)
    check(not missing, f"app.js가 참조하는 id가 HTML에 모두 존재 (누락 {missing})")

    assets = set(re.findall(r'(?:href|src)="(\./[^"]+)"', html))
    assets |= set(re.findall(r'"\./(index\.html|[^"]+\.(?:css|js|png|svg|webmanifest))"', io.open(
        ROOT / "manifest.webmanifest", encoding="utf-8").read()))
    missing_files = [a for a in sorted(assets) if a != "./" and not (ROOT / a.lstrip("./")).exists()]
    check(not missing_files, f"참조 파일 존재 (누락 {missing_files})")

    # 태그 균형 간단 점검
    opens = len(re.findall(r"<(div|section|nav|header|main|form|button|p|h1|h2|h3|span|ul|ol|li)\b", html))
    closes = len(re.findall(r"</(div|section|nav|header|main|form|button|p|h1|h2|h3|span|ul|ol|li)>", html))
    check(opens == closes, f"태그 열고 닫음 균형 ({opens}/{closes})")

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
