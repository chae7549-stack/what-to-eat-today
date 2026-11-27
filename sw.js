/* 냉장고 파먹기 — 오프라인 지원 서비스 워커
   앱 껍데기(shell)만 미리 캐시하고, 페이지 이동은 네트워크 우선으로 처리합니다.
   검색 유입용 개별 레시피 페이지(recipes/*.html, 1,400여 개)는 미리 캐시하지 않고
   사용자가 실제로 연 페이지만 그때그때 캐시합니다 (설치·업데이트를 가볍게). */

var CACHE = "wtt-v17";
var PAGES = ["./", "./index.html", "./about.html", "./privacy.html", "./terms.html"];
var ASSETS = [
  "./styles.css?v=17",
  "./pages.css?v=17",
  "./data/recipes-data.js?v=17",
  "./app.js?v=17",
  "./manifest.webmanifest",
  "./icons/icon.svg",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/apple-touch-icon.png",
];

var OFFLINE_HTML =
  '<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">' +
  '<meta name="viewport" content="width=device-width, initial-scale=1">' +
  "<title>오프라인 · 냉장고 파먹기</title>" +
  '<style>body{font-family:-apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;' +
  "margin:0;padding:48px 24px;text-align:center;color:#2a1d14;background:#fffbf6;line-height:1.7}" +
  "h1{font-size:20px}b{color:#e8501f}</style></head><body>" +
  "<h1>지금은 오프라인이에요</h1>" +
  "<p>인터넷이 연결되면 다시 열어 주세요.<br>앱 첫 화면은 오프라인에서도 열려요.</p>" +
  '<p><a href="./">냉장고 파먹기 열기</a></p></body></html>';

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches
      .open(CACHE)
      .then(function (cache) {
        return cache.addAll(PAGES.concat(ASSETS)).catch(function () {
          /* 일부 자산이 없어도 설치 자체는 진행 */
        });
      })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches
      .keys()
      .then(function (keys) {
        return Promise.all(
          keys.map(function (key) {
            if (key !== CACHE) return caches.delete(key);
          })
        );
      })
      .then(function () { return self.clients.claim(); })
  );
});

// 배포 경로가 달라도(깃허브 Pages 하위 경로 · pages.dev 루트) 앱 루트를 찾아낸다
function appRoot() {
  var path = self.location.pathname;
  var at = path.lastIndexOf("/");
  return at === -1 ? "/" : path.slice(0, at + 1);
}

self.addEventListener("fetch", function (event) {
  var request = event.request;
  if (request.method !== "GET") return;

  var url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  var root = appRoot();
  var rel = url.pathname.indexOf(root) === 0
    ? url.pathname.slice(root.length)
    : url.pathname.replace(/^\//, "");

  // 페이지 이동: 네트워크 우선 → 오프라인이면 같은 경로의 캐시
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then(function (response) {
          if (response && response.status === 200) {
            var copy = response.clone();
            caches.open(CACHE).then(function (cache) { cache.put(request, copy); });
          }
          return response;
        })
        .catch(function () {
          return caches.match(request).then(function (cached) {
            if (cached) return cached;
            // 레시피 페이지는 열어 본 적이 있을 때만 캐시에 있다
            return caches.match("./" + rel).then(function (byPath) {
              if (byPath) return byPath;
              if (/^recipes\//.test(rel)) {
                return new Response(OFFLINE_HTML, {
                  headers: { "Content-Type": "text/html; charset=utf-8" },
                });
              }
              return caches.match("./index.html") || caches.match("./");
            });
          });
        })
    );
    return;
  }

  // 정적 자산: 캐시를 먼저 보여주고, 뒤에서 새 파일을 받아 갱신한다.
  // (앱을 업데이트했을 때 사용자가 옛 app.js에 갇히지 않도록)
  event.respondWith(
    caches.match(request).then(function (cached) {
      var network = fetch(request)
        .then(function (response) {
          if (response && response.status === 200) {
            var copy = response.clone();
            caches.open(CACHE).then(function (cache) { cache.put(request, copy); });
          }
          return response;
        })
        .catch(function () { return cached; });
      return cached || network;
    })
  );
});
