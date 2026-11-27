"""앱 데이터(app.js + data/recipes-data.js)를 그대로 실행해 레시피 목록을 꺼낸다.

정적 SEO 페이지(tools/build_seo_pages.py)와 점검 도구가 앱과 **같은 데이터**를
쓰도록, app.js 를 quickjs 로 실행해 내부 상태를 JSON 으로 받아 온다.
(DOM 은 check_logic.py 의 가짜 객체를 그대로 빌려 쓴다)
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import check_logic as C  # noqa: E402  (DOM 스텁·PROBE·quickjs 로더를 함께 쓴다)


def recipes():
    """앱이 들고 있는 전체 메뉴(집밥 1,492 + 배달·외식 150).

    각 항목: id, name, cat, emoji, time, level, moods, budget, method, servings,
             req, opt, ing([[이름, 분량, 재료 id], ...]), steps, tip, comment, curated
    """
    ctx = C.load_context()
    return C.js(ctx, "__t.RECIPES")


if __name__ == "__main__":
    rows = recipes()
    home = [r for r in rows if r["method"] == "home"]
    print(f"전체 {len(rows)} · 집밥 {len(home)} · 배달·외식 {len(rows) - len(home)}")
