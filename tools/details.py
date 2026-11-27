"""후보 id의 레시피 상세 페이지를 받아 구조화된 레코드로 저장한다.

- JSON-LD(Recipe)에서 재료·조리순서를, 페이지 상단 정보에서 인분·시간·난이도를 뽑는다.
- raw.jsonl 에 id 단위로 덧붙여 저장하므로 중간에 끊겨도 이어서 받을 수 있다.

사용법:
  python3 tools/details.py --budget 250 --workers 5
"""
import argparse
import json
import pathlib
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from collect_net import fetch  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
HERE = ROOT / "scratch"
RAW = HERE / "raw.jsonl"

LD_RE = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S)
INFO_RE = re.compile(r'<div class="view3_top_info">(.*?)</div>', re.S)
TIT_RE = re.compile(r'<div class="view3_top_tit"[^>]*>(.*?)</div>', re.S)
SUM_RE = re.compile(r'<div class="view3_top_summary"[^>]*>(.*?)</div>', re.S)
TAG_RE = re.compile(r"<[^>]+>")


def clean_text(s):
    s = TAG_RE.sub(" ", s or "")
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    s = s.replace("&quot;", '"').replace("&#39;", "'")
    s = re.sub(r"[\u200b\ufeff]", "", s)
    s = re.sub(r"[ \t\r\n]+", " ", s)
    return s.strip()


def parse(rid, html):
    rec = {"id": rid, "url": f"https://www.10000recipe.com/recipe/{rid}"}
    ld = None
    for raw in LD_RE.findall(html):
        try:
            obj = json.loads(raw)
        except Exception:  # noqa: BLE001
            continue
        cand = obj if isinstance(obj, dict) else (obj[0] if isinstance(obj, list) and obj else None)
        if isinstance(cand, dict) and "Recipe" in str(cand.get("@type", "")):
            ld = cand
            break
    if ld:
        rec["name"] = clean_text(ld.get("name", ""))
        rec["description"] = clean_text(ld.get("description", ""))[:300]
        ings = ld.get("recipeIngredient") or []
        if isinstance(ings, str):
            ings = [ings]
        rec["ingredients"] = [clean_text(x) for x in ings if clean_text(x)]
        steps = []
        for ins in ld.get("recipeInstructions") or []:
            if isinstance(ins, dict):
                t = clean_text(ins.get("text", ""))
            else:
                t = clean_text(str(ins))
            if t:
                steps.append(t)
        rec["steps"] = steps
        rec["total_time"] = clean_text(ld.get("totalTime", ""))
        rec["yield"] = clean_text(ld.get("recipeYield", ""))
        au = ld.get("author")
        rec["author"] = clean_text(au.get("name", "") if isinstance(au, dict) else str(au or ""))
        ar = ld.get("aggregateRating") or {}
        try:
            rec["rating"] = float(ar.get("ratingValue") or 0)
            rec["reviews"] = int(float(ar.get("reviewCount") or 0))
        except Exception:  # noqa: BLE001
            rec["rating"], rec["reviews"] = 0.0, 0
        rec["published"] = clean_text(ld.get("datePublished", ""))[:10]
    else:
        rec["name"] = clean_text(TIT_RE.search(html).group(1)) if TIT_RE.search(html) else ""
        rec["ingredients"], rec["steps"] = [], []

    m = INFO_RE.search(html)
    rec["servings"] = ""
    rec["time_text"] = ""
    rec["level"] = ""
    if m:
        spans = [clean_text(x) for x in re.findall(r"<span>(.*?)</span>", m.group(1), re.S)]
        for s in spans:
            if "인분" in s:
                rec["servings"] = s
            elif "분" in s or "시간" in s:
                rec["time_text"] = s
            elif s in ("아무나", "초급", "중급", "고급", "초보"):
                rec["level"] = s
    if not rec["level"]:
        m2 = re.search(r"icon_level\.png\">([^<]{1,6})</span>", html)
        if m2:
            rec["level"] = clean_text(m2.group(1))
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=250)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--target", type=int, default=100000)
    a = ap.parse_args()

    cands = json.loads((HERE / "candidates.json").read_text(encoding="utf-8"))
    done = set()
    if RAW.exists():
        for line in RAW.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                done.add(json.loads(line)["id"])
            except Exception:  # noqa: BLE001
                pass
    todo = [c for c in cands if c["id"] not in done]
    print(f"이미 {len(done)}개 · 남은 후보 {len(todo)}개", flush=True)

    lock = threading.Lock()
    started = time.time()
    count = [0]
    stop = threading.Event()

    def work(item):
        if stop.is_set():
            return
        try:
            status, html = fetch(item["url"] if "url" in item else
                                 f"https://www.10000recipe.com/recipe/{item['id']}")
        except Exception as e:  # noqa: BLE001
            print("ERR", item["id"], e, flush=True)
            return
        if status != 200 or not html:
            return
        rec = parse(item["id"], html)
        rec["cat"] = item["cat"]
        rec["kw"] = item["kw"]
        rec["page"] = item["page"]
        rec["rank"] = item["rank"]
        with lock:
            with RAW.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count[0] += 1
            if count[0] % 50 == 0:
                print(f"  {count[0]}건 · {time.time() - started:.0f}s", flush=True)
            if count[0] >= a.target:
                stop.set()

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futures = []
        for item in todo:
            if time.time() - started > a.budget:
                break
            futures.append(ex.submit(work, item))
        for f in futures:
            try:
                f.result()
            except Exception as e:  # noqa: BLE001
                print("ERR", e)

    total = sum(1 for _ in RAW.read_text(encoding="utf-8").splitlines()) if RAW.exists() else 0
    print(f"이번 실행 {count[0]}건 · 전체 raw {total}건 · {time.time() - started:.0f}s", flush=True)


if __name__ == "__main__":
    main()
