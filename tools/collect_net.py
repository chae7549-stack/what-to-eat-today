"""수집용 네트워크 헬퍼 (만개의레시피 https)."""
import gzip
import io
import json
import os
import random
import re
import ssl
import threading
import time
import urllib.error
import urllib.request

UA_POOL = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-S918N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
]

_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE

_lock = threading.Lock()
_last = [0.0]
MIN_GAP = 0.30  # 초당 약 3건


def _throttle():
    with _lock:
        now = time.time()
        wait = _last[0] + MIN_GAP - now
        if wait > 0:
            time.sleep(wait)
            now = time.time()
        _last[0] = now


def fetch(url, tries=4, timeout=30):
    last_err = None
    for attempt in range(tries):
        _throttle()
        req = urllib.request.Request(url, headers={
            "User-Agent": random.choice(UA_POOL),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "ko-KR,ko;q=0.9",
            "Accept-Encoding": "gzip",
            "Referer": "https://www.10000recipe.com/",
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_ctx) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return r.status, raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
            if e.code in (403, 429):
                time.sleep(3 + attempt * 4)
            elif e.code == 404:
                return 404, ""
            else:
                time.sleep(1 + attempt)
        except Exception as e:  # noqa: BLE001
            last_err = repr(e)
            time.sleep(1 + attempt * 2)
    raise RuntimeError(f"fetch failed {url}: {last_err}")
