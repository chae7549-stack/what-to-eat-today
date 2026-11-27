"""검색 유입용 정적 레시피 페이지(recipes/*.html)·sitemap·robots 점검.

확인하는 것
 - 레시피 1개 = 페이지 1개 (앱 데이터와 정확히 같은 수, 빠지거나 남는 페이지 없음)
 - 모든 페이지에 schema.org/Recipe JSON-LD (이름·분류·조리 시간·재료·조리 순서) 와
   BreadcrumbList 가 유효하게 들어 있음
 - canonical·og:주소가 기준 주소(SITE_ORIGIN)와 맞고, 관련 레시피 링크가 실제 파일로 이어짐
 - sitemap.xml 이 XML 로 파싱되고, 홈·허브·모든 레시피를 정확히 한 번씩 담음
 - recipes/index.html 허브가 모든 레시피로 링크하고, robots.txt 가 sitemap 을 가리킴

사용법: python3 tools/build_seo_pages.py && python3 tools/check_seo.py
"""
import io
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import appsnapshot  # noqa: E402

fails, notes = [], []
LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
LINK_RE = re.compile(r'href="([^"]+)"')


def check(cond, msg):
    if cond:
        notes.append("  OK   " + msg)
    else:
        fails.append(msg)


def site_origin():
    src = io.open(ROOT / "index.html", encoding="utf-8").read()
    m = re.search(r"<!--\s*SITE_ORIGIN:\s*(\S+?)\s*-->", src)
    if not m:
        raise SystemExit("index.html 에 SITE_ORIGIN 표시가 없습니다")
    return m.group(1).rstrip("/")


def main():
    origin = site_origin()
    rows = appsnapshot.recipes()
    home = [d for d in rows if d["method"] == "home"]
    by_id = {d["id"]: d for d in home}

    out = ROOT
    rec_dir = out / "recipes"
    files = sorted(p.name for p in rec_dir.glob("*.html") if p.name != "index.html")
    pages = {f[:-5] for f in files}

    print(f"기준 주소 {origin}")
    print(f"레시피 {len(home):,}개 · 생성된 페이지 {len(files):,}개")

    # ---------- 1. 개수·대응 ----------
    missing = sorted(set(by_id) - pages)
    extra = sorted(pages - set(by_id))
    check(not missing, f"모든 레시피에 페이지가 있음 (빠짐 {len(missing)}개 {missing[:3]})")
    check(not extra, f"앱 데이터에 없는 페이지가 남아 있지 않음 (남음 {len(extra)}개 {extra[:3]})")
    check((rec_dir / "index.html").exists(), "recipes/index.html 허브 페이지 있음")
    check((ROOT / "recipe-page.css").exists(), "recipe-page.css 있음")

    # ---------- 2. 페이지별 검사 ----------
    bad = {
        "ld": [], "ld_fields": [], "h1": [], "title": [], "desc": [], "canonical": [],
        "cta": [], "links": [], "steps": [], "ing": [], "size": [], "hub": [], "dup_name": [],
    }
    titles, descs = {}, {}
    rel_counts = []

    for rid in files:
        pid = rid[:-5]
        path = rec_dir / rid
        src = io.open(path, encoding="utf-8").read()
        dish = by_id.get(pid)

        if len(src.encode("utf-8")) > 60_000:
            bad["size"].append(pid)

        blocks = LD_RE.findall(src)
        kinds, recipe, crumb = [], None, None
        for raw in blocks:
            try:
                data = json.loads(raw)
            except Exception:  # noqa: BLE001
                bad["ld"].append(pid)
                continue
            kinds.append(data.get("@type"))
            if data.get("@type") == "Recipe":
                recipe = data
            elif data.get("@type") == "BreadcrumbList":
                crumb = data
        if "Recipe" not in kinds:
            bad["ld"].append(pid)
        if recipe:
            ok = (
                recipe.get("name")
                and recipe.get("recipeCategory")
                and re.match(r"^PT(\d+H)?(\d+M)?$", recipe.get("totalTime") or "")
                and isinstance(recipe.get("recipeIngredient"), list)
                and len(recipe["recipeIngredient"]) >= 2
                and all(str(x).strip() for x in recipe["recipeIngredient"])
                and isinstance(recipe.get("recipeInstructions"), list)
                and len(recipe["recipeInstructions"]) >= 2
                and all((x.get("text") or "").strip() for x in recipe["recipeInstructions"])
                and recipe.get("recipeYield")
            )
            if not ok:
                bad["ld_fields"].append(pid)
            if recipe.get("url") != f"{origin}/recipes/{rid}":
                bad["canonical"].append(pid)
        if not crumb or len(crumb.get("itemListElement") or []) != 3:
            bad["ld"].append(pid)

        h1 = re.search(r"<h1>([^<]*)</h1>", src)
        if not h1 or not dish or h1.group(1).strip() != dish["name"]:
            bad["h1"].append(pid)

        title = re.search(r"<title>([^<]*)</title>", src)
        title = title.group(1) if title else ""
        if dish and dish["name"] not in title:
            bad["title"].append(pid)
        if title in titles:
            bad["dup_name"].append(pid)
        titles[title] = pid

        desc = re.search(r'<meta name="description" content="([^"]*)"', src)
        desc = desc.group(1) if desc else ""
        if not (50 <= len(desc) <= 200):
            bad["desc"].append(pid)
        descs[desc] = descs.get(desc, 0) + 1

        canon = re.search(r'<link rel="canonical" href="([^"]+)"', src)
        if not canon or canon.group(1) != f"{origin}/recipes/{rid}":
            bad["canonical"].append(pid)

        cta = re.search(r'class="rp-cta" href="([^"]+)"', src)
        if not cta or cta.group(1) != f"../?dish={pid}":
            bad["cta"].append(pid)

        # 내부 링크: 관련 레시피(같은 폴더) + 사이트 페이지
        rel = [h for h in LINK_RE.findall(src) if h.startswith("./")]
        rel_counts.append(len(rel))
        for href in rel:
            if href.startswith("./") and not (rec_dir / href[2:].split("#")[0]).exists():
                bad["links"].append(f"{pid}->{href}")
                break
        for href in [h for h in LINK_RE.findall(src) if h.startswith("../")]:
            target = href.split("?")[0].split("#")[0]
            if target in ("../", "../recipes/index.html", "../about.html",
                          "../privacy.html", "../terms.html"):
                continue
            if not (ROOT / target.replace("../", "")).exists():
                bad["links"].append(f"{pid}->{href}")
                break
        if not (6 <= len(rel) <= 14):
            bad["hub"].append(f"{pid}:{len(rel)}")

        if dish:
            ol = re.search(r'<ol class="rp-steps">(.*?)</ol>', src, re.S)
            n_steps = len(re.findall(r"<li>", ol.group(1))) if ol else 0
            if n_steps != len(dish["steps"]) or n_steps < 2:
                bad["steps"].append(pid)
            tb = re.search(r"<tbody>(.*?)</tbody>", src, re.S)
            n_ing = len(re.findall(r"<tr>", tb.group(1))) if tb else 0
            if n_ing != len([r for r in dish["ing"] if r[0]]) or n_ing < 2:
                bad["ing"].append(pid)

    check(not bad["ld"], f"모든 페이지에 유효한 JSON-LD(Recipe+Breadcrumb) ({len(bad['ld'])}건)")
    check(not bad["ld_fields"], f"schema.org/Recipe 필수 항목 충족 ({len(bad['ld_fields'])}건 {bad['ld_fields'][:3]})")
    check(not bad["h1"], f"<h1>이 요리 이름과 같음 ({len(bad['h1'])}건)")
    check(not bad["title"], f"<title>에 요리 이름 포함 ({len(bad['title'])}건)")
    check(not bad["dup_name"], f"<title> 중복 없음 ({len(bad['dup_name'])}건)")
    dup_desc = sum(1 for v in descs.values() if v > 1)
    check(dup_desc <= len(files) * 0.05, f"설명 문구가 겹치지 않음 (중복 {dup_desc}개)")
    check(not bad["desc"], f"메타 설명 50~200자 ({len(bad['desc'])}건)")
    check(not bad["canonical"], f"canonical·url 이 기준 주소와 일치 ({len(bad['canonical'])}건)")
    check(not bad["cta"], f"CTA 가 ../?dish=딥링크 ({len(bad['cta'])}건)")
    check(not bad["links"], f"모든 내부 링크가 실제 파일로 이어짐 ({len(bad['links'])}건 {bad['links'][:3]})")
    check(not bad["steps"], f"조리 단계 수가 데이터와 같음 ({len(bad['steps'])}건)")
    check(not bad["ing"], f"재료 표가 데이터와 같음 ({len(bad['ing'])}건)")
    check(not bad["size"], f"페이지가 60KB 미만 ({len(bad['size'])}건)")
    check(not bad["hub"], f"관련 레시피 링크 6~14개 ({len(bad['hub'])}건 {bad['hub'][:3]})")
    if rel_counts:
        print(f"페이지당 내부 레시피 링크 {min(rel_counts)}~{max(rel_counts)}개")

    # ---------- 3. 허브 페이지 ----------
    hub = io.open(rec_dir / "index.html", encoding="utf-8").read()
    hub_links = [h for h in LINK_RE.findall(hub) if h.startswith("./")]
    hub_targets = {h[2:].split("#")[0] for h in hub_links}
    check(hub_targets == {f"{pid}.html" for pid in pages},
          f"허브가 모든 레시피로 링크 (링크 {len(hub_targets):,}개, "
          f"빠짐 {len({f'{pid}.html' for pid in pages} - hub_targets)})")
    anchors = set(re.findall(r'id="(cat-[a-z]+)"', hub))
    check(len(anchors) >= 8, f"허브 카테고리 앵커 {len(anchors)}개")
    check(all(f"#cat-" in h or not h.endswith("/index.html") for h in hub_links), "허브 링크 형식")
    check(f"{len(home):,}개" in hub or f"{len(home)}개" in hub, "허브에 전체 개수 표시")

    # ---------- 4. sitemap.xml · robots.txt ----------
    sm = ROOT / "sitemap.xml"
    try:
        tree = ET.parse(sm)
        locs = [e.text for e in tree.getroot().iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    except Exception as exc:  # noqa: BLE001
        locs = []
        check(False, f"sitemap.xml 파싱 실패: {exc}")
    check(len(locs) == len(set(locs)), f"sitemap URL 중복 없음 ({len(locs)}개)")
    want = {origin + "/", f"{origin}/recipes/index.html",
            f"{origin}/about.html", f"{origin}/privacy.html", f"{origin}/terms.html"}
    want |= {f"{origin}/recipes/{pid}.html" for pid in pages}
    check(set(locs) == want,
          f"sitemap 이 홈·허브·모든 레시피를 정확히 담음 (빠짐 {len(want - set(locs))}, 남음 {len(set(locs) - want)})")
    check(all(l.startswith(origin + "/") for l in locs), "sitemap 주소가 모두 기준 주소")
    check(all((ROOT / l[len(origin) + 1:]).exists() for l in locs if not l.endswith("/")),
          "sitemap 의 모든 주소에 파일이 있음")

    robots = io.open(ROOT / "robots.txt", encoding="utf-8").read()
    check("Disallow: /" not in robots, "robots.txt 가 전체를 막지 않음")
    check(f"Sitemap: {origin}/sitemap.xml" in robots, "robots.txt 가 sitemap 을 가리킴")

    # ---------- 5. 앱 첫 화면과의 연결 ----------
    index = io.open(ROOT / "index.html", encoding="utf-8").read()
    canon = re.search(r'<link rel="canonical" href="([^"]+)"', index)
    check(bool(canon) and canon.group(1) == origin + "/", f"index.html canonical = {origin}/")
    check('href="./recipes/index.html"' in index, "index.html 에서 허브로 이동 가능")
    check("google-site-verification" in index and "naver-site-verification" in index,
          "검색엔진 소유 확인 메타 자리 있음")
    check("chae7549-stack.github.io" not in index.replace(origin, ""),
          "index.html 에 옛 주소가 남아 있지 않음")

    total_mb = sum((rec_dir / f).stat().st_size for f in files) / (1024 * 1024)
    print(f"레시피 페이지 합계 {total_mb:.1f}MB")

    print()
    for n in notes:
        print(n)
    if fails:
        print("\n실패:")
        for f in fails:
            print("  FAIL " + f)
        sys.exit(1)
    print("\n모든 SEO 점검 통과 ✅")


if __name__ == "__main__":
    main()
