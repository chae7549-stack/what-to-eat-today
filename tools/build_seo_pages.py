"""집밥 레시피 1,492개를 검색 유입용 정적 페이지(recipes/*.html)로 만든다.

만들어지는 것
  recipes/{id}.html      레시피 1개 = 페이지 1개 (제목·재료 표·조리 순서·팁·관련 레시피·schema.org/Recipe)
  recipes/index.html     카테고리별 전체 목록 (허브 페이지, 내부 링크용)
  sitemap.xml            홈·안내 페이지·허브·레시피 전체
  robots.txt             sitemap 주소
  index.html 등          SITE_ORIGIN(기준 주소)이 바뀌면 canonical·og:url 도 함께 갱신

사용법
  python3 tools/build_seo_pages.py                      # 지금 기준 주소로 전체 생성
  python3 tools/build_seo_pages.py --origin https://새주소.pages.dev
  python3 tools/build_seo_pages.py --limit 20           # 미리 보기(20개만)
  python3 tools/build_seo_pages.py --dry-run            # 파일을 쓰지 않고 개수만 확인

기준 주소(SITE_ORIGIN)는 아래 DEFAULT_ORIGIN 한 곳에서만 정한다.
Cloudflare Pages 등으로 옮기면 --origin 한 번으로 사이트 전체 주소가 바뀐다.
"""
import argparse
import html
import json
import pathlib
import re
import sys
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import appsnapshot  # noqa: E402

# ---------------------------------------------------------------- 기준 주소
DEFAULT_ORIGIN = "https://chae7549-stack.github.io/what-to-eat-today"
ORIGIN_MARK = re.compile(r"<!--\s*SITE_ORIGIN:\s*(\S+?)\s*-->")

SITE_NAME = "냉장고 파먹기 · 오늘 뭐 먹지"
SITE_SHORT = "냉장고 파먹기"
CAT_ORDER = ["밥·죽", "국·찌개", "면·파스타", "볶음·구이", "반찬", "전·부침", "분식·야식", "양식·기타"]
CAT_SLUG = {
    "밥·죽": "rice", "국·찌개": "soup", "면·파스타": "noodle", "볶음·구이": "stirfry",
    "반찬": "side", "전·부침": "jeon", "분식·야식": "snack", "양식·기타": "western",
}
LEVEL_TEXT = {1: "쉬움", 2: "보통", 3: "어려움"}


def esc(text):
    return html.escape(str(text or ""), quote=True)


def norm_origin(origin):
    origin = (origin or "").strip().rstrip("/")
    if not re.match(r"^https?://[^\s/]+(/[^\s]*)?$", origin):
        raise SystemExit("--origin 은 https:// 로 시작하는 주소여야 합니다: " + origin)
    return origin


def duration(minutes):
    try:
        m = int(minutes)
    except (TypeError, ValueError):
        m = 0
    m = max(m, 1)
    h, mm = divmod(m, 60)
    out = "PT"
    if h:
        out += f"{h}H"
    if mm or not h:
        out += f"{mm}M"
    return out


def clip(text, limit):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(text) <= limit:
        return text
    cut = text[: limit - 1]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,·.") + "…"


def ing_text(rows):
    out = []
    for row in rows:
        name = (row[0] or "").strip()
        amt = (row[1] or "").strip()
        if not name:
            continue
        out.append((name + " " + amt).strip())
    return out


def build_related(dish, pool, by_cat):
    mine = set(dish["req"]) | set(dish["opt"])
    chosen, seen = [], {dish["id"]}

    def add(d):
        if not d or d["id"] in seen:
            return False
        seen.add(d["id"])
        chosen.append(d)
        return True

    same = [d for d in by_cat.get(dish["cat"], []) if d["id"] != dish["id"]]
    same.sort(key=lambda d: (
        -len(mine & (set(d["req"]) | set(d["opt"]))),
        abs((d["time"] or 0) - (dish["time"] or 0)),
        d["name"],
    ))
    for d in same:                       # 1) 같은 종류 + 재료가 겹치는 요리 3개
        if len(chosen) >= 3:
            break
        if mine & (set(d["req"]) | set(d["opt"])):
            add(d)
    for d in same:                       # 2) 같은 종류로 채우기
        if len(chosen) >= 5:
            break
        add(d)
    if len(chosen) < 6:                  # 3) 종류가 달라도 재료가 겹치는 요리
        others = [d for d in pool if d["cat"] != dish["cat"] and d["id"] != dish["id"]]
        others.sort(key=lambda d: (
            -len(mine & (set(d["req"]) | set(d["opt"]))),
            abs((d["time"] or 0) - (dish["time"] or 0)),
            d["name"],
        ))
        for d in others:
            if len(chosen) >= 6:
                break
            if mine & (set(d["req"]) | set(d["opt"])):
                add(d)
    return chosen


def recipe_jsonld(dish, origin, base_url):
    total = duration(dish["time"])
    instructions = [
        {"@type": "HowToStep", "position": i + 1, "text": step}
        for i, step in enumerate(dish["steps"])
    ]
    data = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": dish["name"],
        "headline": f'{dish["name"]} 레시피',
        "description": clip(
            f'{dish["name"]} 만드는 법. {dish["time"]}분이면 완성되는 {dish["cat"]} 요리로, '
            f'{dish["servings"]} 기준 재료 {len(dish["ing"])}가지와 조리 순서, 요리 팁을 정리했습니다.', 200),
        "url": base_url,
        "mainEntityOfPage": {"@type": "WebPage", "@id": base_url},
        "inLanguage": "ko",
        "recipeCategory": dish["cat"],
        "recipeCuisine": "한식",
        "keywords": ", ".join(filter(None, [dish["name"], dish["cat"], "집밥", "자취 요리", "냉장고 파먹기"])),
        "totalTime": total,
        "recipeYield": dish["servings"] or "2인분",
        "recipeIngredient": ing_text(dish["ing"]),
        "recipeInstructions": instructions,
        "isAccessibleForFree": True,
        "author": {"@type": "Organization", "name": SITE_NAME, "url": origin + "/"},
        "publisher": {
            "@type": "Organization",
            "name": SITE_SHORT,
            "logo": {"@type": "ImageObject", "url": origin + "/icons/icon-512.png"},
        },
    }
    if dish.get("tip"):
        data["description"] = clip(data["description"] + " " + dish["tip"], 300)
    return data


def breadcrumb_jsonld(dish, origin, base_url):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": SITE_SHORT, "item": origin + "/"},
            {"@type": "ListItem", "position": 2, "name": dish["cat"],
             "item": f'{origin}/recipes/index.html#cat-{CAT_SLUG.get(dish["cat"], "etc")}'},
            {"@type": "ListItem", "position": 3, "name": dish["name"], "item": base_url},
        ],
    }


def jsonld_block(data):
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return text.replace("</", "<\\/")


def related_html(items):
    out = []
    for d in items:
        out.append(
            f'<li><a href="./{esc(d["id"])}.html"><span class="e">{d["emoji"]}</span>'
            f'<span>{esc(d["name"])}<span class="m">{esc(d["cat"])} · {esc(d["time"])}분</span></span></a></li>'
        )
    return "".join(out)


def page_html(dish, origin, related, mates, hub_link):
    base_url = f'{origin}/recipes/{dish["id"]}.html'
    title = f'{dish["name"]} 레시피 · {dish["cat"]} | {SITE_SHORT}'
    desc = clip(
        f'{dish["name"]} 만드는 법. {dish["time"]}분 완성 {dish["cat"]} 요리. '
        f'{dish["servings"]} 기준 재료 {len(dish["ing"])}가지, 단계별 조리 순서와 요리 팁.', 155)
    first = dish["ing"][0][0] if dish["ing"] else ""
    lead = (
        f'{dish["name"]} 만드는 법입니다. {dish["time"]}분이면 완성되는 {dish["cat"]} 요리로, '
        f'{dish["servings"] or "2인분"} 기준 재료 {len(dish["ing"])}가지와 조리 순서를 정리했습니다. '
        f'냉장고에 {first} 등이 있다면 지금 바로 시작해 보세요.'
    )
    rows = "".join(
        f'<tr><td>{esc(row[0])}</td><td>{esc(row[1] or "-")}</td></tr>'
        for row in dish["ing"] if row[0]
    )
    steps = "".join(f"<li>{esc(s)}</li>" for s in dish["steps"])
    tip = (
        f'<section class="rp-tip"><h2>💡 요리 팁</h2><p>{esc(dish["tip"])}</p></section>'
        if dish.get("tip") else ""
    )
    mates_block = (
        '<section><h2>같은 재료로 만드는 요리</h2>'
        f'<ul class="rp-rel">{related_html(mates)}</ul></section>'
        if mates else ""
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="keywords" content="{esc(dish['name'])}, {esc(dish['cat'])}, 집밥 레시피, 자취 요리, 냉장고 파먹기">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="color-scheme" content="light">
<meta name="theme-color" content="#ff6b3d">
<meta name="format-detection" content="telephone=no">
<link rel="canonical" href="{esc(base_url)}">
<link rel="icon" type="image/svg+xml" href="../icons/icon.svg">
<link rel="apple-touch-icon" href="../icons/apple-touch-icon.png">
<meta property="og:type" content="article">
<meta property="og:site_name" content="{esc(SITE_NAME)}">
<meta property="og:locale" content="ko_KR">
<meta property="og:title" content="{esc(dish['name'])} 레시피 · {esc(dish['cat'])}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(base_url)}">
<meta property="og:image" content="{esc(origin)}/icons/icon-512.png">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{esc(dish['name'])} 레시피">
<meta name="twitter:description" content="{esc(desc)}">
<link rel="stylesheet" href="../recipe-page.css?v=1">
<script type="application/ld+json">{jsonld_block(recipe_jsonld(dish, origin, base_url))}</script>
<script type="application/ld+json">{jsonld_block(breadcrumb_jsonld(dish, origin, base_url))}</script>
</head>
<body>
<header class="rp-top">
  <a class="rp-brand" href="../">🍳 {esc(SITE_SHORT)}</a>
  <a class="rp-app" href="../?dish={esc(dish['id'])}">앱에서 열기</a>
</header>
<main class="rp-main">
  <nav class="rp-crumb" aria-label="현재 위치">
    <a href="../">홈</a><span>›</span><a href="{esc(hub_link)}">{esc(dish['cat'])}</a><span>›</span><b>{esc(dish['name'])}</b>
  </nav>
  <article>
    <p class="rp-cat">{esc(dish['cat'])}</p>
    <h1>{esc(dish['name'])}</h1>
    <ul class="rp-meta">
      <li>⏱ {esc(dish['time'])}분</li>
      <li>🔥 난이도 {esc(LEVEL_TEXT.get(dish['level'], '쉬움'))}</li>
      <li>🍽 {esc(dish['servings'] or '2인분')}</li>
      <li>🥕 재료 {len(dish['ing'])}가지</li>
    </ul>
    <p class="rp-lead">{esc(lead)}</p>
    <a class="rp-cta" href="../?dish={esc(dish['id'])}">🧊 냉장고 파먹기 앱에서 인분 조절 · 장보기 담기 →</a>

    <section>
      <h2>재료 <small>{esc(dish['servings'] or '2인분')} 기준</small></h2>
      <table class="rp-ing">
        <caption>분량은 기본 인분 기준입니다. 앱에서는 인분 수에 맞춰 자동으로 환산해 줍니다.</caption>
        <thead><tr><th scope="col">재료</th><th scope="col">분량</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </section>

    <section>
      <h2>만드는 법 <small>{len(dish['steps'])}단계</small></h2>
      <ol class="rp-steps">{steps}</ol>
    </section>

    {tip}

    <section>
      <h2>이런 요리도 있어요</h2>
      <ul class="rp-rel">{related_html(related)}</ul>
    </section>

    {mates_block}

    <section class="rp-about">
      <h2>🍳 {esc(SITE_SHORT)}에서 더 해보기</h2>
      <p>냉장고에 있는 재료를 고르면 <b>지금 바로 만들 수 있는 요리</b>만 골라 매칭률 순으로 보여 줘요.
      인분 수를 바꾸면 재료 분량과 조리 문장의 분량이 함께 환산되고, 부족한 재료는 <b>장보기 목록</b>에 담아 마트에서 하나씩 지울 수 있어요.</p>
      <p><a href="../?dish={esc(dish['id'])}">이 레시피를 앱에서 열기</a> · <a href="../recipes/index.html">레시피 전체 목록</a></p>
    </section>
  </article>
</main>
<footer class="rp-foot">
  <p><a href="../">냉장고 파먹기 앱</a> · <a href="../recipes/index.html">레시피 전체 목록</a> · <a href="../about.html">서비스 소개</a> · <a href="../privacy.html">개인정보처리방침</a></p>
  <p>재료와 분량, 조리 순서는 직접 정리한 표준 안내입니다. 배달·외식 가격은 2026년 서울 기준 예상 범위예요.</p>
</footer>
</body>
</html>
"""


def hub_html(home, origin, generated_at):
    groups = []
    for cat in CAT_ORDER + sorted({d["cat"] for d in home} - set(CAT_ORDER)):
        items = [d for d in home if d["cat"] == cat]
        if not items:
            continue
        items.sort(key=lambda d: d["name"])
        slug = CAT_SLUG.get(cat, "etc")
        lis = "".join(
            f'<li><a href="./{esc(d["id"])}.html">{esc(d["name"])}'
            f'<small>{esc(d["time"])}분 · {esc(d["servings"] or "2인분")}</small></a></li>'
            for d in items
        )
        groups.append((cat, slug, len(items), lis))

    jump = "".join(
        f'<a href="#cat-{slug}">{esc(cat)} {n}</a>' for cat, slug, n, _ in groups
    )
    sections = "".join(
        f'<section class="hub-cat" id="cat-{slug}"><h2>{esc(cat)} <small>{n}개</small></h2>'
        f'<ul class="hub-list">{lis}</ul></section>'
        for cat, slug, n, lis in groups
    )
    title = f"집밥 레시피 전체 {len(home):,}개 목록 · 카테고리별 모음 | {SITE_SHORT}"
    desc = clip(
        f"냉장고 재료로 만드는 집밥 레시피 {len(home):,}개를 카테고리별로 모았습니다. "
        "밥·죽, 국·찌개, 반찬, 면·파스타, 볶음·구이, 전·부침, 분식·야식, 양식까지 재료와 조리 순서를 한눈에.", 155)
    url = f"{origin}/recipes/index.html"
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="color-scheme" content="light">
<meta name="theme-color" content="#ff6b3d">
<link rel="canonical" href="{esc(url)}">
<link rel="icon" type="image/svg+xml" href="../icons/icon.svg">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(SITE_NAME)}">
<meta property="og:title" content="집밥 레시피 전체 {len(home):,}개 목록">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(url)}">
<meta property="og:image" content="{esc(origin)}/icons/icon-512.png">
<link rel="stylesheet" href="../recipe-page.css?v=1">
<script type="application/ld+json">{jsonld_block({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": f"집밥 레시피 전체 {len(home):,}개 목록",
        "description": desc,
        "url": url,
        "inLanguage": "ko",
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": origin + "/"},
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(home),
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "url": f'{origin}/recipes/{d["id"]}.html', "name": d["name"]}
                for i, d in enumerate(sorted(home, key=lambda x: x["name"]))
            ],
        },
    })}</script>
</head>
<body>
<header class="rp-top">
  <a class="rp-brand" href="../">🍳 {esc(SITE_SHORT)}</a>
  <a class="rp-app" href="../">앱 열기</a>
</header>
<main class="rp-main">
  <nav class="rp-crumb" aria-label="현재 위치"><a href="../">홈</a><span>›</span><b>레시피 전체 목록</b></nav>
  <h1>집밥 레시피 {len(home):,}개</h1>
  <p class="hub-intro">냉장고에 있는 재료로 만들 수 있는 집밥 레시피를 종류별로 모았습니다.
  각 레시피에는 기본 인분의 재료 분량과 단계별 조리 순서, 요리 팁이 정리되어 있어요.
  앱에서는 지금 있는 재료만 골라 <b>바로 만들 수 있는 요리</b>를 찾고, 인분 수에 맞춰 분량을 환산하고, 부족한 재료를 장보기 목록에 담을 수 있습니다.</p>
  <a class="rp-cta" href="../">🧊 냉장고 파먹기 앱 열기 — 있는 재료로 만들 수 있는 요리 찾기 →</a>
  <div class="hub-jump">{jump}</div>
  {sections}
  <p class="rp-crumb">최종 정리 {esc(generated_at)}</p>
</main>
<footer class="rp-foot">
  <p><a href="../">냉장고 파먹기 앱</a> · <a href="../about.html">서비스 소개</a> · <a href="../privacy.html">개인정보처리방침</a> · <a href="../terms.html">이용약관</a></p>
  <p>재료와 분량, 조리 순서는 직접 정리한 표준 안내입니다.</p>
</footer>
</body>
</html>
"""


def sitemap_xml(home, origin, generated_at, extra_pages):
    urls = []
    urls.append((origin + "/", generated_at, "daily", "1.0"))
    urls.append((origin + "/recipes/index.html", generated_at, "weekly", "0.8"))
    for page in extra_pages:
        urls.append((f"{origin}/{page}", generated_at, "monthly", "0.4"))
    for d in sorted(home, key=lambda x: (x["cat"], x["name"])):
        urls.append((f'{origin}/recipes/{d["id"]}.html', generated_at, "monthly", "0.6"))
    body = "".join(
        "  <url>\n"
        f"    <loc>{esc(u)}</loc>\n"
        f"    <lastmod>{esc(lm)}</lastmod>\n"
        f"    <changefreq>{esc(cf)}</changefreq>\n"
        f"    <priority>{esc(pr)}</priority>\n"
        "  </url>\n"
        for u, lm, cf, pr in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + body
        + "</urlset>\n"
    ), len(urls)


def sync_origin(origin, dry_run):
    """index.html 의 SITE_ORIGIN 표시를 읽어, 주소가 바뀌었으면 정적 페이지들의 절대 주소를 함께 바꾼다."""
    index = ROOT / "index.html"
    src = index.read_text(encoding="utf-8")
    mark = ORIGIN_MARK.search(src)
    old = mark.group(1).rstrip("/") if mark else origin
    changed = []
    if old != origin:
        for name in ("index.html", "about.html", "privacy.html", "terms.html"):
            path = ROOT / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            if old in text:
                changed.append(name)
                if not dry_run:
                    path.write_text(text.replace(old, origin), encoding="utf-8")
    if not dry_run:
        text = index.read_text(encoding="utf-8")
        if ORIGIN_MARK.search(text):
            text = ORIGIN_MARK.sub(f"<!-- SITE_ORIGIN: {origin} -->", text, count=1)
        else:
            text = text.replace("<head>", f"<head>\n    <!-- SITE_ORIGIN: {origin} -->", 1)
        index.write_text(text, encoding="utf-8")
    return old, changed


def main():
    ap = argparse.ArgumentParser(description="집밥 레시피 SEO 페이지 생성기")
    ap.add_argument("--origin", default=DEFAULT_ORIGIN, help="사이트 기준 주소 (예: https://oneulkit.pages.dev)")
    ap.add_argument("--limit", type=int, default=0, help="앞에서 N개만 생성 (미리 보기)")
    ap.add_argument("--dry-run", action="store_true", help="파일을 쓰지 않고 개수만 확인")
    args = ap.parse_args()

    origin = norm_origin(args.origin)
    rows = appsnapshot.recipes()
    home = [d for d in rows if d["method"] == "home"]
    for d in home:
        d["time"] = int(d["time"] or 15)
        d["level"] = int(d["level"] or 1)
        d["servings"] = d.get("servings") or "2인분"
        d["ing"] = d.get("ing") or []
        d["steps"] = d.get("steps") or []
    home.sort(key=lambda d: (CAT_ORDER.index(d["cat"]) if d["cat"] in CAT_ORDER else 99, d["name"]))
    if args.limit:
        home = home[: args.limit]

    by_cat, by_ing = {}, {}
    for d in home:
        by_cat.setdefault(d["cat"], []).append(d)
        for rid in d["req"][:3]:
            by_ing.setdefault(rid, []).append(d)

    generated_at = date.today().isoformat()
    out_dir = ROOT / "recipes"
    if not args.dry_run:
        out_dir.mkdir(exist_ok=True)

    written = 0
    for d in home:
        related = build_related(d, home, by_cat)
        mate_ids = {d["id"]} | {r["id"] for r in related}
        mates = []
        for rid in d["req"][:3]:
            for m in by_ing.get(rid, []):
                if m["id"] in mate_ids or len(mates) >= 4:
                    continue
                mate_ids.add(m["id"])
                mates.append(m)
            if len(mates) >= 4:
                break
        slug = CAT_SLUG.get(d["cat"], "etc")
        hub_link = f"../recipes/index.html#cat-{slug}"
        target = out_dir / f'{d["id"]}.html'
        if not args.dry_run:
            target.write_text(page_html(d, origin, related, mates, hub_link), encoding="utf-8")
        written += 1

    if not args.dry_run:
        (out_dir / "index.html").write_text(hub_html(home, origin, generated_at), encoding="utf-8")
        xml, n_urls = sitemap_xml(home, origin, generated_at, ["about.html", "privacy.html", "terms.html"])
        (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8")
        (ROOT / "robots.txt").write_text(
            "User-agent: *\nAllow: /\n\n"
            f"Sitemap: {origin}/sitemap.xml\n",
            encoding="utf-8",
        )
    else:
        n_urls = len(home) + 5

    old, changed = sync_origin(origin, args.dry_run)
    print(f"{'[미리 보기] ' if args.dry_run else ''}레시피 페이지 {written:,}개 · sitemap URL {n_urls:,}개")
    print(f"기준 주소: {origin}" + (f"  (이전 {old} → 바뀜: {', '.join(changed) or '없음'})" if old != origin else ""))
    if args.dry_run:
        print("파일을 쓰지 않았습니다 (--dry-run)")


if __name__ == "__main__":
    main()
