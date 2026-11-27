"""로컬에서 앱을 실제 Chromium(iPhone 크기)으로 띄워 동작·디자인을 확인하는 테스트 스크립트.

확인하는 것
 - 첫 화면: 오늘의 추천 3개, 재료 칩, 요리 목록
 - 장보기: 드로어의 '+ 담기' → 상단 🛒 장보기 N → 목록 체크 → 새로고침 후에도 유지(localStorage)
 - 딥링크: index.html?dish=... 로 열면 그 레시피 드로어가 바로 열림 · 공유 주소 확인
 - 룰렛 탭 · ?tab=roulette
 - 검색용 레시피 페이지(recipes/*.html): 제목·재료·조리 순서, 콘솔 오류 없음
 - 가로 스크롤 없음(320~390px), 데스크톱 폭
 - 서비스 워커 오프라인 동작

사용법: python3 tools/check_app.py
결과: 스크린샷은 shots/ 에 저장되고, 콘솔 오류·네트워크 실패가 있으면 출력됩니다.
"""
import functools
import http.server
import pathlib
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
SHOTS = ROOT / "shots"
PORT = 8787
problems = []


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    httpd.log_message = lambda *a, **k: None
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        problems.append(msg)


def main():
    SHOTS.mkdir(exist_ok=True)
    httpd = serve()
    errors, failed = [], []
    base = f"http://127.0.0.1:{PORT}"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
            locale="ko-KR",
        )
        page = ctx.new_page()
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page.on("response", lambda r: failed.append((r.status, r.url)) if r.status >= 400 else None)

        # ---------- 1. 첫 화면 · 오늘의 추천 ----------
        page.goto(f"{base}/index.html", wait_until="networkidle")
        page.wait_for_timeout(700)
        page.screenshot(path=str(SHOTS / "01-start.png"), full_page=False)
        print("HERO STAT:", page.locator("#heroStat").inner_text())
        check(page.locator("#dailyPick .daily-card").count() == 3, "첫 화면 오늘의 추천 3개")
        check(page.locator("#dailyPick .daily-head b").inner_text().startswith("오늘 이런 메뉴"),
              "오늘의 추천 제목")
        check(page.locator(".dish").count() >= 20, f"요리 목록 {page.locator('.dish').count()}개")
        check(page.locator("#shopCount").inner_text() == "0", "장보기 개수 0에서 시작")

        # 다른 메뉴
        first_pick = page.locator("#dailyPick .daily-card").first.inner_text()
        page.locator(".daily-shuffle").click()
        page.wait_for_timeout(300)
        check(page.locator("#dailyPick .daily-card").count() == 3, "다른 메뉴를 눌러도 3개")

        # 오늘의 추천 카드 → 드로어
        page.locator("#dailyPick .daily-card").first.click()
        page.wait_for_timeout(500)
        check(page.locator("#drawerTitle").inner_text() != "", "오늘의 추천 카드를 누르면 레시피가 열림")
        page.locator('.drawer-foot [data-act="close"]').click()
        page.wait_for_timeout(300)

        # ---------- 2. 재료 선택 → 부족한 재료 → 장보기 ----------
        for label in ["계란", "김치", "밥"]:
            page.get_by_role("button", name=label, exact=True).first.click()
            page.wait_for_timeout(150)
        page.wait_for_timeout(500)
        check(page.locator("#dailyPick").is_hidden() or not page.locator("#dailyPick .daily-card").count(),
              "재료를 고르면 오늘의 추천은 숨음")
        page.screenshot(path=str(SHOTS / "02-matched.png"))

        top = page.locator(".dish").first
        top.click()
        page.wait_for_timeout(600)
        title = page.locator("#drawerTitle").inner_text()
        print("DRAWER:", title)
        check(page.locator(".miss-add").count() >= 1, "부족한 재료마다 '+ 담기' 버튼")
        check(page.locator("[data-shop-addall]").count() == 1, "'부족한 재료 N개 장보기에 담기' 버튼")
        page.screenshot(path=str(SHOTS / "03-drawer.png"))

        page.locator("[data-shop-addall]").click()
        page.wait_for_timeout(400)
        badge = page.locator("#shopCount").inner_text()
        check(badge != "0", f"장보기 버튼에 담은 개수 표시 ({badge})")
        check("목록 열기" in page.locator("[data-shop-addall]").inner_text(),
              "담은 뒤 버튼이 '목록 열기'로 바뀜")
        page.locator("[data-shop-addall]").click()
        page.wait_for_timeout(500)
        rows = page.locator(".shop-item").count()
        check(rows >= 1 and str(rows) == badge, f"장보기 목록에 {rows}개 표시")
        page.screenshot(path=str(SHOTS / "04-shop.png"))

        page.locator(".shop-check").first.click()
        page.wait_for_timeout(250)
        check(page.locator(".shop-item.is-done").count() == 1, "마트에서 산 항목 체크")

        page.fill("#shopInput", "우유")
        page.locator("#shopForm button").click()
        page.wait_for_timeout(250)
        check(page.locator(".shop-item").count() == rows + 1, "장보기에 직접 추가")
        page.locator(".drawer-close").last.click()
        page.wait_for_timeout(300)

        # 새로고침 후에도 남아 있는지 (localStorage)
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(800)
        check(page.locator("#shopCount").inner_text() == str(rows), "새로고침해도 장보기 개수 유지")
        page.locator("#shopBtn").click()
        page.wait_for_timeout(400)
        check(page.locator(".shop-item").count() == rows + 1, "새로고침해도 장보기 목록 유지")
        check(page.locator(".shop-item.is-done").count() == 1, "산 것 체크도 유지")
        page.locator(".shop-item .shop-buy").first.get_attribute("href")
        check("coupang.com" in (page.locator(".shop-buy").first.get_attribute("href") or ""),
              "장보기 항목 쿠팡 링크")
        # 완료 지우기
        page.locator("[data-act='shop-clear-done']").click()
        page.wait_for_timeout(300)
        check(page.locator(".shop-item.is-done").count() == 0, "완료한 항목 지우기")
        page.locator("[data-act='shop-close']").last.click()
        page.wait_for_timeout(300)

        # ---------- 3. 딥링크 ----------
        page.goto(f"{base}/index.html?dish=kimchi-fried-rice", wait_until="networkidle")
        page.wait_for_timeout(900)
        check(not page.locator("#drawer").is_hidden(), "?dish= 로 열면 드로어가 바로 열림")
        check(page.locator("#drawerTitle").inner_text() == "김치볶음밥",
              f"?dish=kimchi-fried-rice → {page.locator('#drawerTitle').inner_text()}")
        page.screenshot(path=str(SHOTS / "05-deeplink.png"))
        page.locator('.drawer-foot [data-act="close"]').click()
        page.wait_for_timeout(400)
        check("dish=" not in page.url, "드로어를 닫으면 주소에서 dish= 제거")

        page.goto(f"{base}/index.html?tab=roulette", wait_until="networkidle")
        page.wait_for_timeout(700)
        check(page.locator("#view-roulette").is_visible(), "?tab=roulette 로 룰렛 화면 열림")
        check("tab=roulette" in page.url, "주소에 tab=roulette 유지")

        # 배달 메뉴 딥링크
        page.goto(f"{base}/index.html?dish=o1", wait_until="networkidle")
        page.wait_for_timeout(800)
        check("치킨" in page.locator("#drawerTitle").inner_text(), "배달 메뉴도 ?dish= 로 열림")

        # 존재하지 않는 id
        page.goto(f"{base}/index.html?dish=없는메뉴", wait_until="networkidle")
        page.wait_for_timeout(700)
        check(page.locator("#drawer").is_hidden(), "없는 id 는 드로어를 열지 않음")
        check("없는메뉴" not in page.url, "없는 id 는 주소에서 정리")

        # ---------- 4. 룰렛 ----------
        page.goto(f"{base}/index.html", wait_until="networkidle")
        page.wait_for_timeout(500)
        page.get_by_role("tab", name="오늘 뭐 먹지").click()
        page.wait_for_timeout(400)
        page.locator("#moodSeg button", has_text="야식").click()
        page.locator("#methodSeg button", has_text="집에서").click()
        page.wait_for_timeout(300)
        page.locator("#spinBtn").click()
        page.wait_for_selector("#rouletteResult:not(.hidden)", timeout=20000)
        page.wait_for_timeout(700)
        check(page.locator(".result-name").inner_text() != "", "룰렛 결과 표시")
        page.screenshot(path=str(SHOTS / "06-roulette.png"))

        # ---------- 5. 검색용 레시피 페이지 ----------
        page.goto(f"{base}/recipes/kimchi-fried-rice.html", wait_until="networkidle")
        page.wait_for_timeout(400)
        check("김치볶음밥" in page.locator("h1").inner_text(), "레시피 페이지 h1")
        check(page.locator(".rp-ing tbody tr").count() >= 5, "레시피 페이지 재료 표")
        check(page.locator(".rp-steps li").count() >= 3, "레시피 페이지 조리 단계")
        check(page.locator(".rp-rel a").count() >= 6, "레시피 페이지 관련 레시피 링크")
        css = page.evaluate("getComputedStyle(document.body).backgroundColor")
        check(css == "rgb(255, 251, 246)", f"레시피 페이지 스타일 적용 ({css})")
        page.screenshot(path=str(SHOTS / "07-recipe-page.png"), full_page=False)
        page.locator(".rp-cta").click()
        page.wait_for_timeout(900)
        check(not page.locator("#drawer").is_hidden(), "레시피 페이지 CTA → 앱에서 드로어 열림")

        page.goto(f"{base}/recipes/index.html", wait_until="networkidle")
        page.wait_for_timeout(400)
        check(page.locator(".hub-list a").count() == 1492, f"허브 목록 링크 {page.locator('.hub-list a').count()}개")
        page.screenshot(path=str(SHOTS / "08-hub.png"))

        # ---------- 6. 폭·오프라인 ----------
        for width in (320, 390):
            page.goto(f"{base}/index.html", wait_until="networkidle")
            page.set_viewport_size({"width": width, "height": 844})
            page.wait_for_timeout(500)
            sw = page.evaluate("document.documentElement.scrollWidth")
            check(sw <= width + 1, f"{width}px 폭에서 가로 스크롤 없음 ({sw})")
        page.screenshot(path=str(SHOTS / "09-small.png"))

        page.set_viewport_size({"width": 1280, "height": 900})
        page.wait_for_timeout(400)
        page.screenshot(path=str(SHOTS / "10-desktop.png"))

        page.goto(f"{base}/index.html", wait_until="networkidle")
        page.wait_for_timeout(1500)
        print("SW REGISTRATIONS:", page.evaluate("navigator.serviceWorker.getRegistrations().then(r => r.length)"))
        ctx.set_offline(True)
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(900)
        check(page.locator(".chip").count() > 10, "오프라인에서도 앱이 열림")
        ctx.set_offline(False)

        browser.close()

    httpd.shutdown()
    check(not errors, f"콘솔 오류 없음 ({errors[:3]})")
    check(not failed, f"실패한 요청 없음 ({failed[:3]})")
    print()
    if problems:
        print("실패:")
        for msg in problems:
            print("  FAIL " + msg)
        sys.exit(1)
    print("모든 화면 점검 통과 ✅")


if __name__ == "__main__":
    main()
