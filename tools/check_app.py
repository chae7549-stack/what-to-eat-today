"""로컬에서 앱을 실제 Chromium(iPhone 크기)으로 띄워 동작·디자인을 확인하는 테스트 스크립트.

사용법: python3 tools/check_app.py
결과: 스크린샷은 shots/ 에 저장되고, 콘솔 오류·네트워크 실패가 있으면 출력됩니다.
"""
import functools
import http.server
import pathlib
import socketserver
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
SHOTS = ROOT / "shots"
PORT = 8787


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    httpd.log_message = lambda *a, **k: None
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


def main():
    SHOTS.mkdir(exist_ok=True)
    httpd = serve()
    errors, failed = [], []

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

        page.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="networkidle")
        page.wait_for_timeout(600)
        page.screenshot(path=str(SHOTS / "01-start.png"))
        print("HERO STAT:", page.locator("#heroStat").inner_text())
        print("CHIPS:", page.locator(".chip").count())
        print("HEAD:", page.locator("#resultHead").inner_text().replace("\n", " | "))
        print("LISTED:", page.locator(".dish").count())

        # 카테고리 필터
        page.locator(".pill", has_text="국·찌개").first.click()
        page.wait_for_timeout(400)
        print("CAT HEAD:", page.locator("#resultHead").inner_text().replace("\n", " | "))
        print("CAT LISTED:", page.locator(".dish").count())
        page.screenshot(path=str(SHOTS / "02-category.png"))
        page.locator(".pill", has_text="전체").first.click()
        page.wait_for_timeout(300)

        # 검색
        page.fill("#dishSearch", "김치")
        page.wait_for_timeout(500)
        print("SEARCH HEAD:", page.locator("#resultHead").inner_text().replace("\n", " | "))
        page.screenshot(path=str(SHOTS / "03-search.png"))
        page.click("#searchClear")
        page.wait_for_timeout(400)

        # 더 보기
        before = page.locator(".dish").count()
        page.locator(".more-btn").first.click()
        page.wait_for_timeout(400)
        print("MORE:", before, "→", page.locator(".dish").count())

        # 재료 전체 보기
        page.click("#moreChipsBtn")
        page.wait_for_timeout(300)
        print("CHIPS EXPANDED:", page.locator(".chip").count(),
              "GROUPS:", page.locator(".chip-group").count())
        page.screenshot(path=str(SHOTS / "04-chips-all.png"))
        page.click("#moreChipsBtn")
        page.wait_for_timeout(200)

        # 재료 선택: 계란 · 김치 · 밥
        for label in ["계란", "김치", "밥"]:
            page.get_by_role("button", name=label, exact=True).first.click()
            page.wait_for_timeout(150)
        page.wait_for_timeout(500)
        page.screenshot(path=str(SHOTS / "05-matched.png"))
        print("MATCH HEAD:", page.locator("#resultHead").inner_text().replace("\n", " | "))
        print("MATCHED:", page.locator(".dish").count())

        top = page.locator(".dish").first
        print("TOP DISH:", top.locator(".dish-name").inner_text().replace("\n", " "))
        print("TOP PERCENT:", top.locator(".match-num").inner_text())

        # 레시피 드로어
        top.click()
        page.wait_for_timeout(600)
        page.screenshot(path=str(SHOTS / "06-drawer.png"))
        print("DRAWER TITLE:", page.locator("#drawerTitle").inner_text())
        print("INGREDIENTS:", page.locator(".ing-list li").count())
        print("STEPS:", page.locator(".steps li").count())
        box = page.locator("#drawerPanel").bounding_box()
        print("DRAWER BOX:", box)
        page.locator('.drawer-foot [data-act="close"]').click()
        page.wait_for_timeout(300)

        # 직접 입력 재료
        page.fill("#customInput", "베이컨")
        page.click('#customForm button[type="submit"]')
        page.wait_for_timeout(400)
        print("SELECTED CHIP COUNT:", page.locator('.chip[aria-pressed="true"]').count())

        # 룰렛 탭
        page.get_by_role("tab", name="오늘 뭐 먹지").click()
        page.wait_for_timeout(500)
        page.screenshot(path=str(SHOTS / "07-roulette.png"))
        print("POOL LABEL:", page.locator("#poolLabel").inner_text())

        # 필터: 야식 + 집에서 + 국·찌개
        page.locator("#moodSeg button", has_text="야식").click()
        page.locator("#methodSeg button", has_text="집에서").click()
        page.locator("#catSeg button", has_text="국·찌개").click()
        page.wait_for_timeout(300)
        print("POOL AFTER FILTER:", page.locator("#poolLabel").inner_text())

        page.locator("#spinBtn").click()
        page.wait_for_timeout(500)
        page.screenshot(path=str(SHOTS / "08-spinning.png"))
        page.wait_for_selector("#rouletteResult:not(.hidden)", timeout=20000)
        page.wait_for_timeout(900)
        page.screenshot(path=str(SHOTS / "09-result.png"), full_page=True)
        print("RESULT:", page.locator(".result-name").inner_text())
        print("RESULT TAGS:", page.locator(".result-tags").inner_text().replace("\n", " | "))

        print("SCROLL WIDTH:", page.evaluate("document.documentElement.scrollWidth"),
              "VIEWPORT:", page.evaluate("window.innerWidth"))

        # 데스크톱 폭 확인
        page.set_viewport_size({"width": 1280, "height": 900})
        page.wait_for_timeout(400)
        page.screenshot(path=str(SHOTS / "10-desktop.png"))

        # 오프라인(서비스 워커) 확인
        page.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="networkidle")
        page.wait_for_timeout(1500)
        print("SW REGISTRATIONS:",
              page.evaluate("navigator.serviceWorker.getRegistrations().then(r => r.length)"))
        ctx.set_offline(True)
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(900)
        print("OFFLINE TITLE:", page.title())
        print("OFFLINE CHIPS:", page.locator(".chip").count())
        print("OFFLINE DISHES:", page.locator(".dish").count())
        ctx.set_offline(False)

        browser.close()

    httpd.shutdown()
    print("CONSOLE ERRORS:", errors)
    print("FAILED REQUESTS:", failed)


if __name__ == "__main__":
    main()
