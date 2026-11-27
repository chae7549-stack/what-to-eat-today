# 검색에 노출시키기 — 배포 · Search Console · 네이버 (5분)

이 앱은 **로그인 없이 도는 정적 사이트**예요. 그래서 배포는 파일을 올리는 일이 전부이고,
검색 노출은 ① 주소를 하나로 정하고 ② 검색엔진에 그 주소를 알려 주는 일이 전부입니다.

- 지금 서비스 중: **<https://chae7549-stack.github.io/what-to-eat-today/>** (GitHub Pages, `main` 브랜치)
- 옮길 수 있는 곳: **Cloudflare Pages** (`https://<프로젝트이름>.pages.dev`)

> ⚠️ `what-to-eat-today.pages.dev` 는 **이미 다른 사람 앱이 쓰고 있는 주소**예요(2026-11-28 확인).
> Cloudflare Pages 프로젝트 이름은 겹치지 않게 정해야 합니다. 예: `oneulkit`, `mwomeokji`, `what-to-eat-today-kr`

---

## 1. Cloudflare Pages 로 옮기기 (무료, 트래픽 무제한)

1. <https://dash.cloudflare.com/sign-up> 에서 무료 가입 (이메일 인증만 하면 됩니다)
2. 왼쪽 **Workers & Pages** → **Create** → **Pages** → **Connect to Git**
3. GitHub 계정 연결 → 저장소 **`chae7549-stack/what-to-eat-today`** 선택 → **Begin setup**
4. 설정은 아래처럼 그대로 두면 됩니다 (빌드 과정이 없는 순수 정적 사이트예요)

   | 항목 | 값 |
   | --- | --- |
   | Project name | 원하는 주소 이름 (예: `oneulkit`) |
   | Production branch | `main` |
   | Framework preset | `None` |
   | Build command | (비움) |
   | Build output directory | `/` |

5. **Save and Deploy** → 1~2분 뒤 `https://<프로젝트이름>.pages.dev` 로 열립니다.
6. 이제 저장소에 push 할 때마다 자동으로 다시 배포됩니다.

### 주소를 새 주소로 바꾸기 (한 줄)

```bash
python3 tools/build_seo_pages.py --origin https://oneulkit.pages.dev
git add -A && git commit -m "기준 주소를 Cloudflare Pages로 변경" && git push
```

이 명령 하나로 **canonical · og:url · 1,492개 레시피 페이지 · sitemap.xml · robots.txt** 가
모두 새 주소로 바뀝니다. (기준 주소는 `index.html` 의 `<!-- SITE_ORIGIN: ... -->` 줄에 적혀 있어요)

> 기준 주소는 **하나만** 쓰세요. 두 주소를 동시에 열어 두면 검색엔진이 어느 쪽을 원본으로 볼지
> 헷갈립니다(canonical 이 가리키는 주소가 원본이 됩니다).

---

## 2. Google Search Console 등록 (3분)

1. <https://search.google.com/search-console> → **속성 추가**
2. **URL 접두어** 를 고르고 사이트 주소를 그대로 붙여넣기
   - 예: `https://oneulkit.pages.dev/` (끝에 `/` 포함)
   - GitHub Pages 를 계속 쓴다면 `https://chae7549-stack.github.io/what-to-eat-today/`
3. **HTML 태그** 방식을 선택하면 이런 태그가 나옵니다

   ```html
   <meta name="google-site-verification" content="여기에_긴_문자열" />
   ```

4. `index.html` 위쪽 `<head>` 에서 아래 두 줄의 주석을 풀고 `content` 값만 붙여넣기

   ```html
   <!-- <meta name="google-site-verification" content="" /> -->
   <!-- <meta name="naver-site-verification" content="" /> -->
   ```

   ```html
   <meta name="google-site-verification" content="여기에_긴_문자열" />
   ```

5. 저장 → `git push` → 1~2분 뒤 Search Console 에서 **확인** 클릭
6. 왼쪽 **Sitemaps** → `sitemap.xml` 입력 → **제출**
   (전체 주소: `https://oneulkit.pages.dev/sitemap.xml`)

색인이 되기까지 보통 **3일~2주** 걸립니다. 처음에는 상위 페이지 몇 개만 잡히고,
시간이 지나면 레시피 페이지가 하나씩 늘어납니다.

---

## 3. 네이버 서치어드바이저 등록 (2분)

1. <https://searchadvisor.naver.com> → **웹마스터 도구** → **사이트 등록**
2. 사이트 주소 입력 (예: `https://oneulkit.pages.dev/`) → 소유 확인
3. **HTML 태그** 방식을 고르면 나오는 태그의 `content` 값을
   `index.html` 의 `naver-site-verification` 줄에 붙여넣고 주석 해제 → `git push` → **확인**
4. **요청 → 사이트맵 제출** 에 `sitemap.xml` 입력
5. (선택) **요청 → 웹페이지 수집** 에서 대표 레시피 페이지 5~10개를 직접 요청하면 빨리 잡힙니다

> 네이버는 첫 등록 후 **수집이 시작되기까지 며칠** 걸리고, `robots.txt` 와 `sitemap.xml` 을
> 자동으로 읽어 갑니다. 이 저장소의 두 파일은 `tools/build_seo_pages.py` 가 만들어 주니
> 손으로 고칠 필요가 없어요.

---

## 4. 무엇이 자동으로 되어 있나

| 항목 | 상태 |
| --- | --- |
| 개별 레시피 페이지 | `recipes/{id}.html` **1,492개** (제목·재료 표·조리 순서·팁·관련 레시피 링크) |
| 구조화 데이터 | 모든 레시피 페이지에 `schema.org/Recipe` + `BreadcrumbList` (JSON-LD) |
| 전체 목록(허브) | `recipes/index.html` — 카테고리별 1,492개 링크 |
| sitemap.xml | 홈 + 허브 + 안내 페이지 + 레시피 1,492개 = **1,497개 주소** |
| robots.txt | `Sitemap: <기준 주소>/sitemap.xml` |
| canonical · og:url | 모두 기준 주소(SITE_ORIGIN) 기준 |
| 서비스 워커 | 앱 껍데기만 미리 캐시, 레시피 페이지는 **네트워크 우선**(`wtt-v17`) |
| 앱에서 레시피 열기 | `?dish={id}` — 카톡·문자로 공유하면 그 레시피가 바로 열림 |

### 다시 만들기 / 점검하기

```bash
python3 tools/build_seo_pages.py        # 페이지·sitemap·robots 다시 생성
python3 tools/check_logic.py            # 앱 로직(장보기·딥링크·오늘의 추천 등) 점검
python3 tools/check_seo.py              # 1,492개 페이지·sitemap·링크 점검
```

---

## 5. 자주 막히는 곳

- **"소유 확인 실패"** — 주소 끝 `/` 유무가 다르면 실패합니다. Search Console 에 넣은 주소와
  실제로 열리는 주소를 똑같이 맞춰 주세요. 배포가 끝나기 전에 확인을 누르면 태그가 아직 없습니다.
- **"가져올 수 없음(404)"** — `main` 브랜치에 push 했는지, Cloudflare Pages 의 Production branch 가
  `main` 인지 확인하세요.
- **레시피 페이지가 안 보임** — sitemap 제출 후에도 바로 안 나오는 게 정상입니다.
  Search Console 의 **URL 검사**에 레시피 주소 하나를 넣어 직접 색인을 요청해 보세요.
- **광고(애드센스) 심사** — 개인정보처리방침·소개·이용약관 페이지가 이미 있고, 레시피 페이지마다
  실제 내용(재료·조리법)이 있어요. 다만 애드센스는 **사이트 단위** 심사이므로, 색인이 어느 정도
  된 뒤에 신청하는 편이 통과가 쉽습니다.
