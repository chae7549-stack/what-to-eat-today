/* 냉장고 파먹기 — 오프라인 지원 서비스 워커
   앱 껍데기(shell)를 캐시해 두고, 페이지 이동은 네트워크 우선으로 처리합니다. */

var CACHE = "wtt-v12";
var PAGES = ["./", "./index.html", "./about.html", "./privacy.html", "./terms.html"];
var ASSETS = [
  "./styles.css?v=12",
  "./pages.css?v=12",
  "./data/recipes-data.js?v=12",
  "./app.js?v=12",
  "./manifest.webmanifest",
  "./icons/icon.svg",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/apple-touch-icon.png",
];

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

self.addEventListener("fetch", function (event) {
  var request = event.request;
  if (request.method !== "GET") return;

  var url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // 페이지 이동: 네트워크 우선 → 오프라인이면 같은 경로의 캐시 → index.html
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then(function (response) {
          var copy = response.clone();
          caches.open(CACHE).then(function (cache) { cache.put(request, copy); });
          return response;
        })
        .catch(function () {
          var path = "." + url.pathname.replace(/^\/what-to-eat-today/, "");
          return caches.match(path).then(function (cached) {
            return cached || caches.match("./index.html") || caches.match("./");
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
