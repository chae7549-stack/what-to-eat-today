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
        page.wait_for_timeout(500)
        page.screenshot(path=str(SHOTS / "01-start.png"), full_page=False)
        page.screenshot(path=str(SHOTS / "01b-start-full.png"), full_page=True)

        # 재료 선택: 계란 · 김치 · 밥
        for label in ["계란", "김치", "밥"]:
            page.get_by_role("button", name=label, exact=True).first.click()
            page.wait_for_timeout(120)
        page.wait_for_timeout(500)
        page.screenshot(path=str(SHOTS / "02-matched.png"))

        top = page.locator(".dish").first
        print("TOP DISH:", top.locator(".dish-name").inner_text().replace("\n", " "))
        print("TOP PERCENT:", top.locator(".match-num").inner_text())
        print("DISH COUNT:", page.locator(".dish").count())

        # 레시피 드로어
        top.click()
        page.wait_for_timeout(500)
        page.screenshot(path=str(SHOTS / "03-drawer.png"))
        print("DRAWER TITLE:", page.locator("#drawerTitle").inner_text())
        print("STEP COUNT:", page.locator(".steps li").count())
        page.locator('.drawer-foot [data-act="close"]').click()
        page.wait_for_timeout(300)

        # 직접 입력 재료
        page.fill("#customInput", "베이컨")
        page.click('#customForm button[type="submit"]')
        page.wait_for_timeout(400)
        print("SELECTED CHIP COUNT:", page.locator('.chip[aria-pressed="true"]').count())

        # 룰렛 탭
        page.get_by_role("tab", name="오늘 뭐 먹지").click()
        page.wait_for_timeout(400)
        page.screenshot(path=str(SHOTS / "04-roulette.png"))
        print("POOL LABEL:", page.locator("#poolLabel").inner_text())

        # 필터: 야식 + 배달·외식
        page.locator("#moodSeg button", has_text="야식").click()
        page.locator("#methodSeg button", has_text="배달·외식").click()
        page.wait_for_timeout(200)
        print("POOL AFTER FILTER:", page.locator("#poolLabel").inner_text())

        page.locator("#spinBtn").click()
        page.wait_for_timeout(400)
        page.screenshot(path=str(SHOTS / "05-spinning.png"))
        page.wait_for_selector("#rouletteResult:not(.hidden)", timeout=15000)
        page.wait_for_timeout(900)
        page.screenshot(path=str(SHOTS / "06-result.png"), full_page=True)
        print("RESULT:", page.locator(".result-name").inner_text())
        print("RESULT TAGS:", page.locator(".result-tags").inner_text().replace("\n", " | "))

        # 결과 카드가 화면 폭을 넘지 않는지 확인
        box = page.locator(".result").bounding_box()
        print("RESULT BOX:", box)
        print("SCROLL WIDTH:", page.evaluate("document.documentElement.scrollWidth"),
              "VIEWPORT:", page.evaluate("window.innerWidth"))

        # 데스크톱 폭 확인
        page.set_viewport_size({"width": 1280, "height": 900})
        page.wait_for_timeout(400)
        page.screenshot(path=str(SHOTS / "07-desktop.png"), full_page=False)

        # 오프라인(서비스 워커) 확인
        page.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="networkidle")
        page.wait_for_timeout(1200)
        sw = page.evaluate("navigator.serviceWorker.getRegistrations().then(r => r.length)")
        print("SW REGISTRATIONS:", sw)
        ctx.set_offline(True)
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(800)
        print("OFFLINE TITLE:", page.title())
        print("OFFLINE CHIP COUNT:", page.locator(".chip").count())
        ctx.set_offline(False)

        browser.close()

    httpd.shutdown()
    print("CONSOLE ERRORS:", errors)
    print("FAILED REQUESTS:", failed)


if __name__ == "__main__":
    main()
