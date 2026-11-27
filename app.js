/* ==========================================================================
   냉장고 파먹기 — 오늘 뭐 먹지
   - 모드 1: 냉장고 재료 매칭 (보유 재료로 만들 수 있는 요리 추천)
   - 모드 2: 기분·예산·방식·카테고리 룰렛 (오늘 뭐 먹지?)
   - 레시피: 직접 만든 큐레이션 57개 + 만개의레시피(10000recipe.com)에서
             수집한 집밥 레시피 1,400여 개 + 배달·외식 메뉴 150개 (data/recipes-data.js)
   - 공유: Web Share API → 클립보드 순으로 폴백
   ========================================================================== */

(function () {
  "use strict";

  var DB = (typeof window !== "undefined" && window.RECIPE_DB) || null;

  /* ------------------------------------------------------------------
     1. 재료 분류
        data/recipes-data.js 의 taxonomy(112종)를 그대로 쓴다.
        데이터 파일이 없을 때를 대비해 최소 목록을 둔다.
     ------------------------------------------------------------------ */
  var FALLBACK_TAXONOMY = [
    { id: "egg", label: "계란", emoji: "🥚", group: "계란·두부·콩", common: true, aliases: ["계란", "달걀"] },
    { id: "kimchi", label: "김치", emoji: "🌶️", group: "채소·버섯", common: true, aliases: ["김치", "포기김치", "신김치"] },
    { id: "tofu", label: "두부", emoji: "🧊", group: "계란·두부·콩", common: true, aliases: ["두부"] },
    { id: "pa", label: "대파", emoji: "🌿", group: "채소·버섯", common: true, aliases: ["대파", "파", "쪽파"] },
    { id: "onion", label: "양파", emoji: "🧅", group: "채소·버섯", common: true, aliases: ["양파"] },
    { id: "garlic", label: "마늘", emoji: "🧄", group: "채소·버섯", common: true, aliases: ["마늘", "다진마늘"] },
    { id: "ham", label: "햄·소시지", emoji: "🥓", group: "고기·해산물", common: true, aliases: ["스팸", "햄", "소시지", "베이컨"] },
    { id: "tuna", label: "참치캔", emoji: "🐟", group: "고기·해산물", common: true, aliases: ["참치", "참치캔"] },
    { id: "rice", label: "밥", emoji: "🍚", group: "곡류·면·떡", common: true, aliases: ["밥", "쌀밥", "찬밥"] },
    { id: "ramen", label: "라면·면", emoji: "🍜", group: "곡류·면·떡", common: true, aliases: ["라면", "라면사리"] },
    { id: "pasta", label: "파스타면", emoji: "🍝", group: "곡류·면·떡", common: true, aliases: ["파스타", "스파게티"] },
    { id: "cheese", label: "치즈", emoji: "🧀", group: "빵·유제품", common: true, aliases: ["치즈", "모짜렐라"] },
    { id: "potato", label: "감자", emoji: "🥔", group: "채소·버섯", common: true, aliases: ["감자"] },
    { id: "pork", label: "돼지고기", emoji: "🥩", group: "고기·해산물", common: true, aliases: ["돼지고기", "삼겹살"] },
    { id: "chicken", label: "닭고기", emoji: "🍗", group: "고기·해산물", common: true, aliases: ["닭고기", "닭가슴살"] },
    { id: "bean", label: "콩나물", emoji: "🌱", group: "채소·버섯", common: true, aliases: ["콩나물"] },
    { id: "fishcake", label: "어묵", emoji: "🍢", group: "고기·해산물", common: true, aliases: ["어묵", "오뎅"] },
    { id: "mushroom", label: "버섯", emoji: "🍄", group: "채소·버섯", common: true, aliases: ["버섯", "표고버섯", "느타리"] },
    { id: "ganjang_jin", label: "진간장", emoji: "🍶", group: "장류·소스", common: true, pantry: true, aliases: ["진간장", "간장", "맛간장"] },
    { id: "gochujang", label: "고추장", emoji: "🌶️", group: "장류·소스", common: true, pantry: true, aliases: ["고추장", "초고추장"] },
    { id: "doenjang", label: "된장", emoji: "🫘", group: "장류·소스", common: true, pantry: true, aliases: ["된장"] },
    { id: "gochugaru", label: "고춧가루", emoji: "🌶️", group: "양념·향신", common: true, pantry: true, aliases: ["고춧가루", "고추가루"] },
    { id: "vinegar", label: "양조식초", emoji: "🍶", group: "식초·오일", pantry: true, aliases: ["양조식초", "식초"] },
    { id: "milk", label: "우유", emoji: "🥛", group: "빵·유제품", aliases: ["우유"] },
    { id: "butter", label: "버터", emoji: "🧈", group: "빵·유제품", aliases: ["버터"] },
    { id: "bread", label: "식빵", emoji: "🍞", group: "빵·유제품", aliases: ["식빵", "빵"] },
    { id: "cabbage", label: "양배추", emoji: "🥬", group: "채소·버섯", aliases: ["양배추"] },
    { id: "cucumber", label: "오이", emoji: "🥒", group: "채소·버섯", aliases: ["오이"] },
    { id: "carrot", label: "당근", emoji: "🥕", group: "채소·버섯", aliases: ["당근"] },
    { id: "tteok", label: "떡", emoji: "🍡", group: "곡류·면·떡", aliases: ["떡", "떡볶이떡"] },
    { id: "tomato", label: "토마토", emoji: "🍅", group: "채소·버섯", aliases: ["토마토"] },
    { id: "flour", label: "부침가루·밀가루", emoji: "🌾", group: "곡류·면·떡", aliases: ["부침가루", "밀가루", "튀김가루"] },
    { id: "curry", label: "카레가루", emoji: "🍛", group: "곡류·면·떡", aliases: ["카레", "카레가루"] },
  ];

  var INGREDIENTS = [];   // 칩으로 쓰는 재료
  var BY_ID = {};         // id → 재료
  var ALIAS = [];         // [{key, id}] 긴 이름부터 정렬

  function normalize(text) {
    return String(text || "").replace(/\s+/g, "").replace(/[()[\]{}]/g, "").trim().toLowerCase();
  }

  (function buildTaxonomy() {
    var src = (DB && DB.taxonomy && DB.taxonomy.length) ? DB.taxonomy : FALLBACK_TAXONOMY;
    src.forEach(function (t) {
      var item = {
        id: t.id, label: t.label, emoji: t.emoji || "🍴",
        group: t.group || "기타",
        common: !!t.common, pantry: !!t.pantry, always: !!t.always,
        aliases: t.aliases || [],
      };
      INGREDIENTS.push(item);
      BY_ID[item.id] = item;
      var keys = [item.label].concat(item.aliases);
      keys.forEach(function (k) {
        var key = normalize(k);
        if (key) ALIAS.push({ key: key, id: item.id });
      });
    });
    ALIAS.sort(function (a, b) { return b.key.length - a.key.length; });
  })();

  // 기본으로 보여줄 재료 칩 순서 (자주 쓰는 순)
  var COMMON_ORDER = [
    "egg", "kimchi", "tofu", "rice", "pa", "onion", "garlic", "potato", "pork", "chicken",
    "ham", "tuna", "fishcake", "bean", "mushroom", "cheese", "milk", "butter", "bread",
    "ramen", "pasta", "tteok", "dumpling", "flour", "curry",
    "ganjang_jin", "gochujang", "doenjang", "gochugaru", "salt", "sugar", "pepper",
    "oil", "sesame_oil", "sesame", "mirin", "vinegar", "mayo", "ketchup",
  ];

  var GROUP_EMOJI = {
    "채소·버섯": "🥬", "고기·해산물": "🥩", "계란·두부·콩": "🥚", "곡류·면·떡": "🍚",
    "빵·유제품": "🧀", "장류·소스": "🥫", "식초·오일": "🫗", "양념·향신": "🧂",
    "과일·기타": "🍎",
  };

  var GROUPS = [];
  INGREDIENTS.forEach(function (it) {
    if (GROUPS.indexOf(it.group) === -1) GROUPS.push(it.group);
  });

  // 재료 탭: 자주 쓰는 + 그룹별
  var ING_TABS = [{ id: "common", label: "자주 쓰는", emoji: "⭐" }];
  GROUPS.forEach(function (g) { ING_TABS.push({ id: g, label: g, emoji: GROUP_EMOJI[g] || "🍴" }); });

  /* ------------------------------------------------------------------
     2. 요리 데이터
        - DISHES: 직접 만든 큐레이션 요리
        - RECIPES: 큐레이션(집밥) + 수집 레시피
        - ALLDISH: 룰렛용 (배달·외식 포함)
     ------------------------------------------------------------------ */
  var CURATED_CAT = {
    "kimchi-fried-rice": "밥·죽", "gyeranmari": "반찬", "tuna-mayo": "밥·죽",
    "dubu-kimchi": "반찬", "ganjang-gyeran-bap": "밥·죽", "spam-mayo": "밥·죽",
    "kimchi-jjigae": "국·찌개", "doenjang-jjigae": "국·찌개", "budae-jjigae": "국·찌개",
    "aglio": "면·파스타", "tomato-pasta": "면·파스타", "cream-pasta": "면·파스타",
    "tteokbokki": "분식·야식", "rabokki": "분식·야식", "jeyuk": "볶음·구이",
    "gamjajeon": "전·부침", "eomuktang": "국·찌개", "kongnamul-gukbap": "국·찌개",
    "curry": "밥·죽", "omurice": "밥·죽", "street-toast": "양식·기타",
    "kimchijeon": "전·부침", "gyeranjjim": "반찬", "kimchi-ramyeon": "분식·야식",
    "cheese-ramyeon": "분식·야식", "tuna-kimchi-stew": "국·찌개", "dubu-jorim": "반찬",
    "kongnamul-muchim": "반찬", "gamja-jorim": "반찬", "beoseot-bokkeum": "볶음·구이",
    "chicken-salad": "양식·기타", "chicken-fried-rice": "밥·죽", "oi-muchim": "반찬",
    "pork-cabbage": "볶음·구이", "french-toast": "양식·기타", "ham-cheese-sandwich": "양식·기타",
    "bibimbap": "밥·죽", "eomuk-bokkeum": "볶음·구이", "potato-soup": "양식·기타",
    "dubu-butter": "볶음·구이", "tuna-potato-jorim": "반찬", "tteokguk": "국·찌개",
    "balsamic-salad": "양식·기타", "coconut-noodle": "면·파스타", "barley-bibimbap": "밥·죽",
    "oat-banana-porridge": "양식·기타", "duck-bokkeum": "볶음·구이", "gopchang-bokkeum": "볶음·구이",
    "edamame-muchim": "반찬", "mango-smoothie": "양식·기타", "hwanggi-baeksuk": "국·찌개",
    "oi-chomuchim": "반찬",
  };

  var CATEGORIES = [
    { id: "all", label: "전체" },
    { id: "밥·죽", label: "밥·죽" },
    { id: "국·찌개", label: "국·찌개" },
    { id: "면·파스타", label: "면·파스타" },
    { id: "볶음·구이", label: "볶음·구이" },
    { id: "반찬", label: "반찬" },
    { id: "전·부침", label: "전·부침" },
    { id: "분식·야식", label: "분식·야식" },
    { id: "양식·기타", label: "양식·기타" },
  ];

  // 배달·외식 메뉴 종류 (배민 카테고리) — DB.out 의 cat 값에서 만든다
  var OUT_CATS = [{ id: "all", label: "전체" }];
  var OUT_EMOJI = {
    "치킨": "🍗", "피자": "🍕", "중식": "🥟", "한식·찌개": "🍲", "덮밥·비빔밥": "🍚",
    "족발·보쌈": "🐷", "일식·돈까스": "🍣", "면·국수": "🍜", "분식·떡볶이": "🌶️",
    "야식·안주": "🍢", "패스트푸드": "🍔", "아시안": "🍜", "샐러드·건강식": "🥗",
    "카페·디저트": "☕",
  };

  var DISHES = [
    {
      id: "kimchi-fried-rice", name: "김치볶음밥", emoji: "🍳", time: 10, level: 1,
      req: ["kimchi", "rice", "egg"], opt: ["pa", "ham", "cheese"],
      moods: ["alone", "hearty"], budget: "low", method: "home",
      steps: [
        "김치를 한입 크기로 썰고, 대파나 햄이 있으면 같이 다져 주세요.",
        "팬에 기름을 두르고 김치를 2분간 볶아 신맛을 날려요.",
        "밥을 넣고 김치국물 2큰술과 함께 고슬고슬하게 볶아 주세요.",
        "한쪽에 계란을 풀어 익힌 뒤 비비고, 치즈가 있으면 올려 녹여요.",
      ],
      tip: "너무 익은 김치는 설탕 반 티스푼으로 신맛을 잡아 주세요.",
      comment: "김치 하나로 완성되는 국민 한 그릇이에요 🔥",
    },
    {
      id: "gyeranmari", name: "계란말이", emoji: "🥚", time: 10, level: 1,
      req: ["egg", "pa"], opt: ["cheese", "carrot", "ham"],
      moods: ["alone", "light"], budget: "low", method: "home",
      steps: [
        "계란 3개를 풀고 소금 한 꼮집과 잘게 썬 대파를 섞어요.",
        "약불로 줄인 팬에 계란물을 얇게 부어 주세요.",
        "가장자리가 익으면 사각으로 접어 주세요.",
        "계란물을 한 번 더 부어 접고, 김발로 모양을 잡으면 완성!",
      ],
      tip: "불이 세면 부풀어 갈라져요. 약불이 포인트!",
      comment: "10분이면 도시락 반찬 완성 🥚",
    },
    {
      id: "tuna-mayo", name: "참치마요덮밥", emoji: "🍚", time: 8, level: 1,
      req: ["tuna", "rice"], opt: ["egg", "pa", "cheese"],
      moods: ["alone", "hearty"], budget: "low", method: "home",
      steps: [
        "참치캔 기름을 빼고 마요네즈 2큰술과 섞어 주세요.",
        "따뜻한 밥에 참치마요를 올려 주세요.",
        "계란이 있으면 반숙 프라이로 올리고 대파를 솔솔 뿌려요.",
        "간장 반 스푼을 둘러 비벼 드세요.",
      ],
      tip: "참치 기름을 완전히 빼야 느끼하지 않아요.",
      comment: "젓가락이 멈추지 않는 그 맛 🥄",
    },
    {
      id: "dubu-kimchi", name: "두부김치", emoji: "🍲", time: 15, level: 1,
      req: ["tofu", "kimchi"], opt: ["pork", "pa"],
      moods: ["hearty", "night"], budget: "low", method: "home",
      steps: [
        "두부를 1.5cm 두께로 썰어 끓는 물에 1분 데쳐요.",
        "팬에 김치를 볶다가 돼지고기가 있으면 함께 볶아 주세요.",
        "접시에 두부를 깔고 김치볶음을 올려요.",
        "대파와 참기름을 살짝 올리면 완성!",
      ],
      tip: "두부는 데치면 물이 빠져 더 담백해져요.",
      comment: "안주로도 밥반찬으로도 딱 🍲",
    },
    {
      id: "ganjang-gyeran-bap", name: "간장계란밥", emoji: "🍚", time: 5, level: 1,
      req: ["egg", "rice", "ganjang_jin"], opt: ["butter", "pa"],
      moods: ["alone", "night"], budget: "low", method: "home",
      steps: [
        "따뜻한 밥에 계란 프라이를 올려 주세요.",
        "간장 1큰술과 참기름 반 큰술을 둘러요.",
        "노른자를 터뜨려 골고루 비벼 드세요.",
        "버터 반 쪽을 더하면 고소함이 확 살아요.",
      ],
      tip: "간장은 밥 위에 둘러야 짜지 않아요.",
      comment: "5분 요리의 정석 ⏱️",
    },
    {
      id: "spam-mayo", name: "스팸마요덮밥", emoji: "🍱", time: 8, level: 1,
      req: ["ham", "rice"], opt: ["egg", "pa"],
      moods: ["alone", "hearty"], budget: "low", method: "home",
      steps: [
        "스팸을 도톰하게 썰어 노릇하게 구워요.",
        "밥 위에 스팸을 올리고 마요네즈를 둘러 주세요.",
        "계란 프라이를 올리고 대파를 뿌려요.",
        "간장 반 스푼으로 간을 맞춰 비벼 드세요.",
      ],
      tip: "스팸은 키친타월에 눌러 기름을 빼면 담백해요.",
      comment: "한 그릇 순삭, 든든한 한 끼 🍱",
    },
    {
      id: "kimchi-jjigae", name: "김치찌개", emoji: "🍲", time: 25, level: 2,
      req: ["kimchi", "pork", "tofu"], opt: ["pa", "onion", "mushroom"],
      moods: ["hearty", "hangover"], budget: "mid", method: "home",
      steps: [
        "돼지고기를 한입 크기로 썰어 팬에 볶아 주세요.",
        "김치를 넣고 3분 더 볶아 감칠맛을 내요.",
        "물 3컵을 붓고 10분간 끓여 주세요.",
        "두부와 대파를 넣고 5분 더 끓이면 완성!",
      ],
      tip: "김치국물을 함께 넣어야 깊은 맛이 나요.",
      comment: "국물까지 남기지 않는 그 맛 🍲",
    },
    {
      id: "doenjang-jjigae", name: "된장찌개", emoji: "🍲", time: 25, level: 2,
      req: ["tofu", "potato", "onion", "doenjang"], opt: ["mushroom", "pa"],
      moods: ["hearty"], budget: "mid", method: "home",
      steps: [
        "감자와 양파, 두부를 한입 크기로 썰어 주세요.",
        "물 3컵에 된장 1큰술을 풀어 끓여요.",
        "감자부터 넣고 8분 끓인 뒤 두부와 양파를 넣어요.",
        "대파를 넣고 3분 더 끓이면 완성!",
      ],
      tip: "된장은 체에 걸러 풀면 덩어리 없이 부드러워요.",
      comment: "밥 한 공기 부르는 집밥의 기본 🍚",
    },
    {
      id: "budae-jjigae", name: "부대찌개", emoji: "🍲", time: 25, level: 2,
      req: ["ham", "kimchi", "ramen", "tofu"], opt: ["onion", "pa", "cheese"],
      moods: ["hearty", "night"], budget: "mid", method: "home",
      steps: [
        "스팸과 두부, 김치를 먹기 좋게 썰어 냄비에 담아요.",
        "고춧가루 1큰술, 간장 1큰술, 물 4컵을 붓고 끓여요.",
        "김치가 익으면 라면 사리를 넣어 주세요.",
        "라면이 익으면 치즈를 올려 불을 꺼요.",
      ],
      tip: "라면은 마지막에 넣어야 불지 않아요!",
      comment: "냉장고 재료로 만드는 얼큰한 한 그릇 🌶️",
    },
    {
      id: "aglio", name: "알리오올리오", emoji: "🍝", time: 15, level: 2,
      req: ["pasta", "garlic"], opt: ["cheese", "mushroom"],
      moods: ["alone", "light"], budget: "mid", method: "home",
      steps: [
        "파스타면을 소금물에 8분 삶아 주세요.",
        "올리브유에 편마늘을 약불로 노릇하게 볶아요.",
        "삶은 면과 면수 반 컵을 넣고 1분 볶아요.",
        "소금·후추로 간하고 치즈를 뿌려 완성!",
      ],
      tip: "면수는 소스가 면에 붙게 해 주는 열쇠예요.",
      comment: "마늘 하나만 있으면 가능 🧄",
    },
    {
      id: "tomato-pasta", name: "토마토파스타", emoji: "🍝", time: 20, level: 2,
      req: ["pasta", "tomato", "onion"], opt: ["garlic", "cheese", "mushroom"],
      moods: ["light", "hearty"], budget: "mid", method: "home",
      steps: [
        "양파와 마늘을 다져 올리브유에 볶아 주세요.",
        "토마토를 썰어 넣고 8분간 조려요.",
        "삶은 면과 면수를 넣고 2분 볶아요.",
        "소금·후추 간하고 치즈를 뿌려요.",
      ],
      tip: "토마토 캔이 있으면 더 진한 맛이 나요.",
      comment: "집에서 만드는 이탈리안 기본 🍅",
    },
    {
      id: "cream-pasta", name: "크림파스타", emoji: "🍝", time: 20, level: 2,
      req: ["pasta", "milk", "cheese"], opt: ["ham", "mushroom", "garlic"],
      moods: ["hearty"], budget: "mid", method: "home",
      steps: [
        "우유 1컵과 치즈 2장을 약불에 녹여 소스를 만들어요.",
        "삶은 면을 넣고 2분간 버무려 주세요.",
        "햄이나 버섯이 있으면 미리 볶아 함께 넣어요.",
        "후추를 듬뿍 갈아 완성!",
      ],
      tip: "생크림이 없어도 우유만으로 충분히 고소해요.",
      comment: "냉장고 우유로 만드는 크림파스타 🥛",
    },
    {
      id: "tteokbokki", name: "떡볶이", emoji: "🍡", time: 15, level: 1,
      req: ["tteok", "gochujang"], opt: ["egg", "fishcake", "pa", "cheese"],
      moods: ["night", "hearty"], budget: "low", method: "home",
      steps: [
        "떡을 물에 5분 담가 말랑하게 해 주세요.",
        "물 2컵에 고추장 2큰술, 설탕 1큰술을 풀어요.",
        "떡과 어묵, 대파를 넣고 8분 졸여 주세요.",
        "불을 줄이고 치즈나 삶은 계란을 올려요.",
      ],
      tip: "떡을 미지근한 물에 5분 불리면 쫄깃함이 살아요. 고추장은 멸치 육수에 풀어야 짜지 않아요.",
      comment: "야식의 왕, 실패 없는 떡볶이 🌶️",
    },
    {
      id: "rabokki", name: "라볶이", emoji: "🍜", time: 18, level: 1,
      req: ["tteok", "ramen", "gochujang"], opt: ["fishcake", "egg", "cheese"],
      moods: ["night", "hearty"], budget: "low", method: "home",
      steps: [
        "물 2컵에 고추장 2큰술, 설탕 1큰술을 풀어 끓여요.",
        "떡과 어묵을 넣고 5분 끓여 주세요.",
        "라면 사리를 넣고 3분 더 끓여요.",
        "계란이나 치즈를 올려 마무리!",
      ],
      tip: "국물이 많으면 라면이 불어요. 물 양을 지켜 주세요.",
      comment: "떡볶이에 라면은 반칙이죠 🍜",
    },
    {
      id: "jeyuk", name: "제육볶음", emoji: "🥘", time: 20, level: 2,
      req: ["pork", "onion", "gochujang"], opt: ["garlic", "pa", "cabbage"],
      moods: ["hearty"], budget: "mid", method: "home",
      steps: [
        "돼지고기에 고추장 2큰술, 간장 1큰술, 설탕 1큰술로 밑간해요.",
        "양파와 마늘을 먼저 볶아 주세요.",
        "고기를 넣고 센 불에서 5분 볶아요.",
        "대파와 양배추를 넣고 2분 더 볶으면 완성!",
      ],
      tip: "고기를 10분 재워 두면 훨씬 맛있어요.",
      comment: "밥 위에 올리면 그 자체로 한 끼 🍚",
    },
    {
      id: "gamjajeon", name: "감자전", emoji: "🥔", time: 15, level: 1,
      req: ["potato"], opt: ["onion", "pa"],
      moods: ["light", "alone"], budget: "low", method: "home",
      steps: [
        "감자 2개를 강판에 갈아 주세요.",
        "물기를 살짝 따라내고 소금으로 간해요.",
        "팬에 기름을 넉넉히 두르고 얇게 펴 구워요.",
        "양쪽이 노릇해지면 접시에 담아 완성!",
      ],
      tip: "감자를 갈 때 양파를 조금 넣으면 색이 예뻐요.",
      comment: "감자 세 개로 만드는 고소한 간식 🥔",
    },
    {
      id: "eomuktang", name: "어묵탕", emoji: "🍢", time: 15, level: 1,
      req: ["fishcake", "pa"], opt: ["onion", "mushroom"],
      moods: ["hangover", "light"], budget: "low", method: "home",
      steps: [
        "어묵을 꼬치나 한입 크기로 준비해요.",
        "물 3컵에 다시마나 간장을 넣고 끓여요.",
        "어묵과 양파를 넣고 5분 끓여 주세요.",
        "대파와 후추를 뿌려 마무리!",
      ],
      tip: "어묵은 끓는 물에 한 번 데치면 잡내가 사라져요.",
      comment: "해장으로 딱, 뜨끈한 어묵탕 🍢",
    },
    {
      id: "kongnamul-gukbap", name: "콩나물국밥", emoji: "🍲", time: 15, level: 1,
      req: ["bean", "rice"], opt: ["egg", "pa", "garlic"],
      moods: ["hangover", "light"], budget: "low", method: "home",
      steps: [
        "콩나물을 씻어 물 4컵과 함께 끓여요.",
        "다진 마늘과 국간장으로 간을 해 주세요.",
        "밥을 넣고 2분 더 끓여요.",
        "계란을 풀어 넣고 대파를 뿌리면 완성!",
      ],
      tip: "콩나물은 뚜껑을 열고 끓여야 비린내가 없어요.",
      comment: "숙취엔 이거죠, 뜨끈한 국밥 🌱",
    },
    {
      id: "curry", name: "카레", emoji: "🍛", time: 25, level: 1,
      req: ["potato", "onion", "carrot", "curry"], opt: ["pork", "chicken", "rice"],
      moods: ["hearty"], budget: "low", method: "home",
      steps: [
        "감자, 당근, 양파를 깍둑썰기해 주세요.",
        "고기가 있으면 먼저 볶아 주세요.",
        "물 3컵을 붓고 채소가 익을 때까지 12분 끓여요.",
        "불을 끄고 카레가루를 풀어 5분 더 끓여요.",
      ],
      tip: "카레는 하루 지나면 더 맛있어요. 다음날도 OK!",
      comment: "한 번 끓이면 이틀 든든 🍛",
    },
    {
      id: "omurice", name: "오므라이스", emoji: "🍳", time: 20, level: 2,
      req: ["egg", "rice", "onion"], opt: ["ham", "cheese", "milk"],
      moods: ["alone", "hearty"], budget: "low", method: "home",
      steps: [
        "양파와 햄을 볶다가 밥과 케첩 2큰술을 넣어 볶아요.",
        "밥을 그릇에 담아 모양을 잡아 주세요.",
        "계란 2개를 풀어 약불에서 넓게 부쳐요.",
        "밥 위에 계란을 덮고 케첩을 뿌리면 완성!",
      ],
      tip: "계란에 우유 1큰술을 넣으면 더 부드러워요.",
      comment: "케첩 그림까지 그리고 싶은 비주얼 🍳",
    },
    {
      id: "street-toast", name: "길거리토스트", emoji: "🍞", time: 10, level: 1,
      req: ["bread", "egg", "ham"], opt: ["cheese", "cabbage"],
      moods: ["alone", "light"], budget: "low", method: "home",
      steps: [
        "식빵을 팬에 살짝 구워 주세요.",
        "계란과 햄을 각각 구워요.",
        "빵 위에 계란, 햄, 치즈를 차례로 올려요.",
        "케첩과 설탕을 살짝 뿌려 덮으면 완성!",
      ],
      tip: "양배추를 채 썰어 넣으면 아삭함이 살아요.",
      comment: "아침 10분, 길거리 감성 🍞",
    },
    {
      id: "kimchijeon", name: "김치전", emoji: "🌶️", time: 15, level: 1,
      req: ["kimchi", "flour"], opt: ["pa"],
      moods: ["night", "hearty"], budget: "low", method: "home",
      steps: [
        "김치를 잘게 썰고 부침가루 1컵과 김치국물을 섞어요.",
        "반죽이 되직해지면 물로 농도를 맞춰요.",
        "팬에 기름을 두르고 반죽을 얇게 펴 구워요.",
        "양면이 노릇해지면 접시에 담아 완성!",
      ],
      tip: "김치국물을 넣어야 색과 맛이 살아요.",
      comment: "비 오는 날 생각나는 그 맛 🌶️",
    },
    {
      id: "gyeranjjim", name: "계란찜", emoji: "🥚", time: 12, level: 1,
      req: ["egg", "pa"], opt: ["carrot"],
      moods: ["hangover", "light"], budget: "low", method: "home",
      steps: [
        "계란 3개에 물 반 컵, 소금을 넣고 풀어요.",
        "체에 한 번 걸러 냄비에 담아요.",
        "약불에서 저어가며 6분 익혀요.",
        "대파를 뿌리고 뚜껑을 덮어 1분 뜸 들여요.",
      ],
      tip: "약불에서 천천히 익혀야 부드러워요. 뚜껑을 덮고 익히면 구멍이 적게 나요.",
      comment: "숟가락으로 떠먹는 폭신한 계란찜 🥚",
    },
    {
      id: "kimchi-ramyeon", name: "김치라면", emoji: "🍜", time: 8, level: 1,
      req: ["ramen", "kimchi"], opt: ["egg", "pa"],
      moods: ["night", "alone"], budget: "low", method: "home",
      steps: [
        "물 550ml를 끓이고 김치를 먼저 넣어요.",
        "스프와 건더기를 넣고 2분 끓여요.",
        "면을 넣고 3분 더 끓여 주세요.",
        "계란을 풀어 넣고 대파를 올려 완성!",
      ],
      tip: "김치를 먼저 끓이면 국물이 깊어져요.",
      comment: "야식의 정답, 김치라면 🍜",
    },
    {
      id: "cheese-ramyeon", name: "치즈라면", emoji: "🍜", time: 8, level: 1,
      req: ["ramen", "cheese"], opt: ["egg"],
      moods: ["night", "alone"], budget: "low", method: "home",
      steps: [
        "물 550ml에 스프를 넣고 끓여요.",
        "면을 넣고 3분 끓여 주세요.",
        "불을 끄고 치즈를 올려 녹여요.",
        "후추를 살짝 뿌리면 완성!",
      ],
      tip: "치즈는 불을 끈 뒤 올려야 부드럽게 녹아요.",
      comment: "매운맛을 잡아주는 치즈의 힘 🧀",
    },
    {
      id: "tuna-kimchi-stew", name: "참치김치찌개", emoji: "🍲", time: 20, level: 1,
      req: ["tuna", "kimchi"], opt: ["tofu", "pa"],
      moods: ["hearty", "hangover"], budget: "low", method: "home",
      steps: [
        "김치를 냄비에 넣고 3분 볶아요.",
        "물 3컵을 붓고 8분 끓여요.",
        "참치캔과 두부를 넣고 5분 더 끓여요.",
        "대파와 후추를 뿌려 마무리!",
      ],
      tip: "참치 기름을 빼면 국물이 깔끔해요. 참치는 마지막에 넣어야 부서지지 않아요.",
      comment: "고기 없이도 깊은 맛, 참치의 힘 🐟",
    },
    {
      id: "dubu-jorim", name: "두부조림", emoji: "🍲", time: 15, level: 1,
      req: ["tofu", "ganjang_jin"], opt: ["pa", "onion"],
      moods: ["light", "alone"], budget: "low", method: "home",
      steps: [
        "두부를 도톰하게 썰어 물기를 빼요.",
        "팬에 두부를 노릇하게 지져 주세요.",
        "간장 2큰술, 물 3큰술, 설탕 반 큰술을 섞어 부어요.",
        "대파를 올리고 국물이 졸면 완성!",
      ],
      tip: "두부는 키친타월로 물기를 빼야 부서지지 않아요.",
      comment: "밥 도둑 반찬, 두부조림 🍲",
    },
    {
      id: "kongnamul-muchim", name: "콩나물무침", emoji: "🌱", time: 10, level: 1,
      req: ["bean", "garlic"], opt: ["pa"],
      moods: ["light"], budget: "low", method: "home",
      steps: [
        "콩나물을 끓는 물에 3분 삶아요.",
        "찬물에 헹궈 물기를 꼭 짜 주세요.",
        "다진 마늘, 소금, 참기름으로 무쳐요.",
        "대파를 솔솔 뿌려 완성!",
      ],
      tip: "삶은 뒤 찬물에 헹구면 아삭함이 살아요.",
      comment: "5분 반찬, 콩나물무침 🌱",
    },
    {
      id: "gamja-jorim", name: "감자조림", emoji: "🥔", time: 20, level: 1,
      req: ["potato", "ganjang_jin"], opt: ["onion", "carrot"],
      moods: ["light", "alone"], budget: "low", method: "home",
      steps: [
        "감자를 한입 크기로 썰어 물기를 빼요.",
        "팬에 기름을 두르고 감자를 노릇하게 볶아요.",
        "간장 3큰술, 물 반 컵, 설탕 1큰술을 넣고 끓여요.",
        "국물이 졸면 참기름과 통깨로 마무리!",
      ],
      tip: "감자를 먼저 볶으면 으깨지지 않아요.",
      comment: "달짝지근한 밥도둑 반찬 🥔",
    },
    {
      id: "beoseot-bokkeum", name: "버섯볶음", emoji: "🍄", time: 12, level: 1,
      req: ["mushroom", "garlic"], opt: ["butter", "onion"],
      moods: ["light", "alone"], budget: "low", method: "home",
      steps: [
        "버섯을 먹기 좋게 찢어 주세요.",
        "팬에 버터나 기름을 두르고 마늘을 볶아요.",
        "버섯을 넣고 센 불에 4분 볶아요.",
        "소금·후추로 간하고 완성!",
      ],
      tip: "버섯은 물에 씻지 말고 키친타월로 닦아 주세요.",
      comment: "향이 좋아 고기 안 부럽습니다 🍄",
    },
    {
      id: "chicken-salad", name: "닭가슴살샐러드", emoji: "🥗", time: 15, level: 1,
      req: ["chicken", "cabbage"], opt: ["tomato", "cucumber", "onion"],
      moods: ["light"], budget: "mid", method: "home",
      steps: [
        "닭가슴살을 소금·후추로 밑간해 팬에 구워요.",
        "양배추를 채 썰어 찬물에 5분 담가요.",
        "닭가슴살을 먹기 좋게 찢어 올려요.",
        "올리브유와 레몬즙, 소금으로 드레싱해요.",
      ],
      tip: "닭가슴살은 약불에서 천천히 익혀야 촉촉해요.",
      comment: "가볍지만 든든한 한 끼 🥗",
    },
    {
      id: "chicken-fried-rice", name: "닭가슴살볶음밥", emoji: "🍚", time: 15, level: 2,
      req: ["chicken", "rice", "egg"], opt: ["onion", "pa", "carrot"],
      moods: ["alone", "light"], budget: "mid", method: "home",
      steps: [
        "닭가슴살을 잘게 썰어 소금·후추로 밑간해요.",
        "팬에 닭가슴살과 채소를 볶아 주세요.",
        "밥을 넣고 간장 1큰술로 간하며 볶아요.",
        "계란을 풀어 넣고 한 번 더 볶으면 완성!",
      ],
      tip: "밥은 찬밥이 고슬고슬해서 좋아요. 닭가슴살은 우유에 20분 재우면 퍽퍽하지 않아요.",
      comment: "단백질 가득, 다이어터 볶음밥 🍗",
    },
    {
      id: "oi-muchim", name: "오이무침", emoji: "🥒", time: 8, level: 1,
      req: ["cucumber", "garlic", "gochugaru"], opt: ["onion"],
      moods: ["light", "hangover"], budget: "low", method: "home",
      steps: [
        "오이를 반달 모양으로 썰어 소금에 5분 절여요.",
        "물기를 살짝 짜 주세요.",
        "고춧가루, 다진 마늘, 식초, 설탕으로 무쳐요.",
        "통깨를 뿌려 완성!",
      ],
      tip: "절인 오이는 아삭함이 살아 있어요. 소금에 5분 절인 뒤 물기를 빼야 양념이 묽지 않아요.",
      comment: "입맛 없을 때 딱, 새콤달콤 🥒",
    },
    {
      id: "pork-cabbage", name: "돼지고기 양배추볶음", emoji: "🥬", time: 15, level: 2,
      req: ["pork", "cabbage", "gochujang"], opt: ["pa"],
      moods: ["hearty"], budget: "mid", method: "home",
      steps: [
        "양배추를 한입 크기로 썰어 주세요.",
        "돼지고기를 먼저 볶아 겉면을 익혀요.",
        "양배추와 간장·굴소스를 넣고 4분 볶아요.",
        "후추를 뿌려 완성!",
      ],
      tip: "센 불에 빠르게 볶아야 양배추가 아삭해요.",
      comment: "밥에 올리면 순식간에 사라져요 🥬",
    },
    {
      id: "french-toast", name: "프렌치토스트", emoji: "🍞", time: 12, level: 1,
      req: ["bread", "egg", "milk"], opt: ["butter", "cheese"],
      moods: ["alone", "light"], budget: "low", method: "home",
      steps: [
        "계란 1개와 우유 반 컵, 설탕 1큰술을 섞어요.",
        "식빵을 반으로 잘라 계란물에 적셔요.",
        "버터 두른 팬에 약불로 노릇하게 구워요.",
        "꿀이나 설탕을 뿌려 완성!",
      ],
      tip: "빵을 살짝 마르게 두면 계란물이 잘 배요.",
      comment: "카페 부럽지 않은 아침 🍞",
    },
    {
      id: "ham-cheese-sandwich", name: "햄치즈샌드위치", emoji: "🥪", time: 8, level: 1,
      req: ["bread", "ham", "cheese"], opt: ["cabbage", "tomato"],
      moods: ["alone", "light"], budget: "low", method: "home",
      steps: [
        "식빵을 살짝 구워 주세요.",
        "햄을 팬에 노릇하게 구워요.",
        "빵-치즈-햄-치즈-빵 순서로 쌓아요.",
        "전자레인지에 20초 돌려 치즈를 녹여요.",
      ],
      tip: "양배추 채를 넣으면 아삭한 식감이 더해져요.",
      comment: "5분 완성, 든든한 간식 🥪",
    },
    {
      id: "bibimbap", name: "비빔밥", emoji: "🍚", time: 15, level: 1,
      req: ["rice", "egg", "gochujang"], opt: ["bean", "cucumber", "carrot", "mushroom"],
      moods: ["hearty", "hangover"], budget: "low", method: "home",
      steps: [
        "냉장고 채소를 채 썰어 살짝 볶아 주세요.",
        "밥 위에 채소를 색 맞춰 돌려 담아요.",
        "고추장 1큰술, 참기름 반 큰술, 설탕 반 티스푼으로 양념장을 만들어요.",
        "계란 프라이를 올리고 비벼 드세요.",
      ],
      tip: "양념장에 식초 반 스푼을 넣으면 더 산뜻해요.",
      comment: "냉장고 채소 총출동, 비빔밥 🥢",
    },
    {
      id: "eomuk-bokkeum", name: "어묵볶음", emoji: "🍢", time: 12, level: 1,
      req: ["fishcake", "ganjang_jin"], opt: ["onion", "pa"],
      moods: ["night", "alone"], budget: "low", method: "home",
      steps: [
        "어묵을 먹기 좋게 썰어 끓는 물에 데쳐요.",
        "팬에 기름을 두르고 어묵을 볶아 주세요.",
        "간장 1큰술, 물엿 1큰술, 고춧가루 반 티스푼을 넣어요.",
        "대파와 통깨를 뿌려 완성!",
      ],
      tip: "물엿 대신 설탕 반 스푼도 괜찮아요.",
      comment: "도시락 단골 반찬 🍢",
    },
    {
      id: "potato-soup", name: "감자수프", emoji: "🥔", time: 20, level: 1,
      req: ["potato", "milk", "butter"], opt: ["onion", "bread"],
      moods: ["light"], budget: "low", method: "home",
      steps: [
        "감자와 양파를 썰어 버터에 볶아요.",
        "물 2컵을 붓고 감자가 익을 때까지 10분 끓여요.",
        "믹서나 감자으깨기로 곱게 갈아 주세요.",
        "우유를 넣고 약불에서 데우면 완성!",
      ],
      tip: "우유는 마지막에 넣어야 분리되지 않아요.",
      comment: "빵 찍어 먹으면 그게 저녁 🥖",
    },
    {
      id: "dubu-butter", name: "두부버터구이", emoji: "🧈", time: 15, level: 1,
      req: ["tofu", "butter"], opt: ["ganjang_jin", "pa"],
      moods: ["light", "alone"], budget: "low", method: "home",
      steps: [
        "두부 물기를 빼고 도톰하게 썰어요.",
        "팬에 버터를 녹이고 두부를 노릇하게 구워요.",
        "간장 반 스푼을 살짝 발라 주세요.",
        "대파를 뿌려 완성!",
      ],
      tip: "버터에 간장만 더해도 근사한 안주가 돼요.",
      comment: "고소함 폭발, 두부버터구이 🧈",
    },
    {
      id: "tuna-potato-jorim", name: "참치감자조림", emoji: "🍚", time: 20, level: 2,
      req: ["tuna", "potato", "ganjang_jin"], opt: ["onion"],
      moods: ["alone"], budget: "low", method: "home",
      steps: [
        "감자를 썰어 기름에 살짝 볶아요.",
        "간장 2큰술, 설탕 1큰술, 물 반 컵을 넣고 끓여요.",
        "감자가 익으면 참치를 넣어요.",
        "국물이 졸면 대파를 뿌려 마무리!",
      ],
      tip: "참치는 마지막에 넣어야 부서지지 않아요.",
      comment: "반찬 하나로 밥 한 공기 뚝딱 🍚",
    },
    {
      id: "tteokguk", name: "떡국", emoji: "🍡", time: 20, level: 1,
      req: ["tteok", "egg", "ganjang_guk"], opt: ["pa", "mushroom"],
      moods: ["hangover", "hearty"], budget: "low", method: "home",
      steps: [
        "떡을 물에 10분 담가 불려요.",
        "물 4컵에 국간장으로 간을 해 끓여요.",
        "떡을 넣고 떠오를 때까지 5분 끓여요.",
        "계란 지단과 대파를 올려 완성!",
      ],
      tip: "떡이 떠오르면 다 익은 거예요. 떡은 찬물에 10분 불려야 국물이 텁텁하지 않아요.",
      comment: "명절 아니어도 좋은 떡국 🍡",
    },

    /* -------------------- 세분화 재료 큐레이션 -------------------- */
    {
      id: "balsamic-salad", name: "발사믹 샐러드", emoji: "🥗", time: 10, level: 1,
      req: ["sangchu", "tomato", "balsamic"], opt: ["olive_oil", "cheese", "onion", "nut"],
      moods: ["light"], budget: "low", method: "home",
      steps: [
        "상추와 토마토를 먹기 좋게 씻어 물기를 완전히 빼 주세요.",
        "올리브유 2큰술, 발사믹식초 1큰술, 소금·후추를 섞어 드레싱을 만들어요.",
        "채소를 그릇에 담고 드레싱을 먹기 직전에 둘러 주세요.",
        "치즈나 견과류가 있으면 부숴서 올리면 고소함이 더해져요.",
      ],
      tip: "발사믹식초는 올리브유와 1:2로 섞어야 산미가 부드러워져요. 채소 물기를 빼야 드레싱이 묽지 않아요.",
      comment: "10분이면 완성되는 산뜻한 한 접시 🥗",
    },
    {
      id: "coconut-noodle", name: "집에서 만드는 쌀국수", emoji: "🍜", time: 25, level: 2,
      req: ["rice_noodle", "chicken", "pa", "onion"], opt: ["lemon_juice", "gochu", "fish_sauce", "cilantro"],
      moods: ["hangover", "light"], budget: "mid", method: "home",
      steps: [
        "닭고기와 양파, 대파를 넣고 20분 끓여 육수를 만들어요.",
        "쌀국수면은 미지근한 물에 10분 불려 주세요.",
        "육수를 체에 거르고 소금과 액젓으로 간을 맞춰요.",
        "면을 끓는 물에 30초 데쳐 그릇에 담고 육수를 부어요.",
        "레몬즙과 고수를 곁들이면 베트남식 완성!",
      ],
      tip: "쌀국수면은 불린 뒤 데쳐야 부드러워요. 육수는 양파를 구워 넣어야 향이 깊어져요.",
      comment: "집에서 즐기는 베트남 한 그릇 🍜",
    },
    {
      id: "barley-bibimbap", name: "보리비빔밥", emoji: "🍚", time: 25, level: 1,
      req: ["barley", "rice", "buchu", "gochujang"], opt: ["egg", "carrot", "sesame_oil"],
      moods: ["light", "hearty"], budget: "low", method: "home",
      steps: [
        "보리는 30분 불려 밥과 함께 고슬고슬하게 지어요.",
        "부추와 당근은 잘게 썰어 참기름에 살짝 볶아요.",
        "밥을 그릇에 담고 채소를 돌려 담아 주세요.",
        "고추장과 참기름을 넣고 계란후라이를 올려 비벼 드세요.",
      ],
      tip: "보리는 불리는 시간이 짧으면 딱딱해요. 30분 이상 불려야 부드럽게 씹혀요.",
      comment: "씹는 맛이 살아 있는 보리밥 한 그릇 🍚",
    },
    {
      id: "oat-banana-porridge", name: "오트밀 바나나죽", emoji: "🥣", time: 8, level: 1,
      req: ["oat", "milk", "banana"], opt: ["honey", "nut", "blueberry"],
      moods: ["light"], budget: "low", method: "home",
      steps: [
        "우유 1컵을 냄비에 붓고 약불로 데워요.",
        "오트밀 3큰술을 넣고 3분간 천천히 저어요.",
        "바나나를 으깨 넣고 1분 더 끓이면 완성!",
        "꿀이나 견과류를 올려 마무리해요.",
      ],
      tip: "우유가 끓어 넘치지 않게 약불에서 저어 주세요. 오트밀은 1분만 더 두면 걸쭉해져요.",
      comment: "8분이면 든든한 아침 🥣",
    },
    {
      id: "duck-bokkeum", name: "오리 주물럭", emoji: "🦆", time: 20, level: 2,
      req: ["duck", "onion", "pa", "gochujang"], opt: ["garlic", "sugar", "sesame_oil"],
      moods: ["hearty", "night"], budget: "mid", method: "home",
      steps: [
        "오리고기는 한입 크기로 썰어 물기를 닦아요.",
        "고추장 2큰술, 간장 1큰술, 설탕 1큰술, 다진 마늘을 섞어요.",
        "고기에 양념을 버무려 15분 재워 주세요.",
        "센 불에 팬을 달군 뒤 고기를 볶아요.",
        "양파와 대파를 넣고 2분 더 볶아 완성!",
      ],
      tip: "오리는 기름이 많아 양파를 먼저 볶아 기름을 입히면 느끼하지 않아요.",
      comment: "밥도 술도 부르는 오리 주물럭 🦆",
    },
    {
      id: "gopchang-bokkeum", name: "곱창 볶음", emoji: "🍢", time: 25, level: 3,
      req: ["gopchang", "onion", "pa", "gochugaru"], opt: ["garlic", "sugar", "sesame_oil"],
      moods: ["night", "hearty"], budget: "mid", method: "home",
      steps: [
        "곱창은 밀가루로 주물러 씻고 물기를 빼 주세요.",
        "고춧가루 2큰술, 간장 1큰술, 설탕 반 큰술로 양념을 만들어요.",
        "센 불에 곱창을 볶아 기름을 내요.",
        "양파와 대파, 다진 마늘을 넣고 함께 볶아요.",
        "양념을 넣고 2분 더 볶은 뒤 참기름을 두르면 완성!",
      ],
      tip: "곱창은 밀가루로 주물러야 잡내가 빠져요. 센 불에 짧게 볶아야 질기지 않아요.",
      comment: "야식엔 역시 곱창 볶음 🍢",
    },
    {
      id: "edamame-muchim", name: "마늘 에다마메", emoji: "🫛", time: 10, level: 1,
      req: ["edamame", "garlic"], opt: ["salt", "sesame_oil", "gochu"],
      moods: ["light", "night"], budget: "low", method: "home",
      steps: [
        "에다마메는 끓는 물에 소금을 넣고 3분 삶아요.",
        "물을 버리고 찬물에 헹구지 않고 그대로 두세요.",
        "다진 마늘과 소금, 참기름을 넣고 버무려요.",
        "청양고추를 송송 썰어 올리면 칼칼함이 더해져요.",
      ],
      tip: "삶은 뒤 바로 물을 빼야 콩알이 촉촉해요. 참기름은 불을 끈 뒤에 넣어야 향이 살아요.",
      comment: "한 알씩 집어 먹는 재미 🫛",
    },
    {
      id: "mango-smoothie", name: "망고 스무디", emoji: "🥭", time: 5, level: 1,
      req: ["mango", "yogurt", "milk"], opt: ["honey", "banana"],
      moods: ["light"], budget: "low", method: "home",
      steps: [
        "망고는 껍질을 벗겨 한입 크기로 썰어 얼려 두세요.",
        "믹서에 얼린 망고와 요거트, 우유를 넣어요.",
        "30초 갈고 꿀이나 바나나를 더해 한 번 더 갈아요.",
        "차가운 컵에 담아 바로 드세요.",
      ],
      tip: "과일을 얼려 쓰면 얼음을 넣지 않아도 되고 맛이 진해요. 우유를 조금씩 넣어 농도를 맞추세요.",
      comment: "카페 부럽지 않은 한 잔 🥭",
    },
    {
      id: "hwanggi-baeksuk", name: "황기 닭백숙", emoji: "🍲", time: 70, level: 2,
      req: ["chicken", "hwanggi", "garlic", "rice"], opt: ["insam", "daechu", "pa", "salt"],
      moods: ["hearty"], budget: "mid", method: "home",
      steps: [
        "닭은 찬물에 30분 담가 핏물을 빼요.",
        "황기와 대추, 통마늘을 냄비에 넣고 물 2L를 부어요.",
        "닭을 넣고 끓어오르면 중불로 줄여 50분 끓여요.",
        "찹쌀이나 밥을 넣고 10분 더 끓이면 걸쭉해져요.",
        "소금으로 간을 맞추고 대파를 올려 마무리해요.",
      ],
      tip: "황기는 오래 끓일수록 구수한 향이 우러나요. 닭은 젓가락이 쑥 들어가면 다 익은 거예요.",
      comment: "기운 나는 날의 보양식 🍲",
    },
    {
      id: "oi-chomuchim", name: "오이 초무침", emoji: "🥒", time: 10, level: 1,
      req: ["cucumber", "brown_vinegar", "sugar"], opt: ["gochugaru", "garlic", "sesame"],
      moods: ["light", "hangover"], budget: "low", method: "home",
      steps: [
        "오이는 어슷하게 썰어 소금에 5분 절여요.",
        "물기를 꼭 짜고 그릇에 담아요.",
        "현미식초 2큰술, 설탕 1큰술, 소금 한 꼬집을 섞어 부어요.",
        "고춧가루와 다진 마늘을 넣고 조물조물 버무려요.",
        "통깨를 뿌려 마무리하면 완성!",
      ],
      tip: "현미식초는 양조식초보다 향이 부드러워 초무침에 잘 어울려요. 절인 오이 물기를 빼야 묽지 않아요.",
      comment: "입맛 돋우는 새콤한 반찬 🥒",
    },

  ];

  var RECIPES = [];

  (function buildRecipes() {
    DISHES.forEach(function (d) {
      var ing = [];
      (d.req || []).forEach(function (id) { ing.push([ingLabel(id), "", id]); });
      (d.opt || []).forEach(function (id) { ing.push([ingLabel(id), "", id]); });
      RECIPES.push({
        id: d.id, name: d.name, emoji: d.emoji || "🍽️",
        cat: CURATED_CAT[d.id] || "양식·기타",
        time: d.time || 15, level: d.level || 1, servings: "",
        moods: d.moods || ["hearty"], budget: d.budget || "low",
        method: d.method || "home",
        req: d.req || [], opt: d.opt || [],
        steps: d.steps || [], ing: ing,
        tip: d.tip || "", comment: d.comment || "", price: d.price || "",
        src: "", author: "", reviews: 0, rating: 0, curated: true,
      });
    });

    // 배달·외식 메뉴 (data/recipes-data.js 의 out 배열 = 배민 카테고리)
    var outs = (DB && DB.out) || [];
    outs.forEach(function (m) {
      RECIPES.push({
        id: m.id, name: m.name, emoji: m.emoji || "🛵",
        cat: m.cat || "배달·외식",
        time: 0, level: 1, servings: "",
        moods: m.moods || ["hearty"], budget: m.budget || "mid",
        method: "out",
        req: [], opt: [], steps: [], ing: [],
        tip: m.tip || "", comment: m.note || "", price: m.price || "",
        bracket: m.bracket || "", priceMin: m.priceMin || 0, priceMax: m.priceMax || 0,
        src: "", author: "", reviews: 0, rating: 0, curated: false,
      });
    });

    var collected = (DB && DB.recipes) || [];
    collected.forEach(function (r) {
      var ing = (r.ing || []).map(function (row) {
        return [row[0] || "", row[1] || "", row[2] || ""];
      });
      RECIPES.push({
        id: r.id, name: r.name, emoji: r.emoji || "🍽️",
        cat: r.cat || "양식·기타",
        time: r.time || 30, level: r.level || 1, servings: r.servings || "",
        moods: r.moods || ["hearty"], budget: r.budget || "low",
        method: "home",
        req: r.req || [], opt: r.opt || [],
        steps: r.steps || [], ing: ing,
        tip: r.tip || "", comment: "", price: "",
        src: r.src || "", author: r.author || "",
        reviews: r.reviews || 0, rating: r.rating || 0, curated: false,
      });
    });
  })();

  // 검색용 문자열을 미리 만들어 둔다 (1,000개 이상도 즉시 검색)
  var HOME_RECIPES = [];
  (function buildIndex() {
    RECIPES.forEach(function (d, i) {
      d._i = i;
      var parts = [d.name, d.cat];
      d.ing.forEach(function (row) { parts.push(row[0]); });
      d._s = normalize(parts.join(" "));
      if (d.method === "home") HOME_RECIPES.push(d);
    });
  })();

  var ALLDISH = RECIPES; // 배달·외식까지 포함한 전체 (룰렛용)

  // 배달·외식 종류 탭 (데이터에 있는 순서 그대로)
  (function buildOutCats() {
    ALLDISH.forEach(function (d) {
      if (d.method !== "out") return;
      for (var i = 0; i < OUT_CATS.length; i++) if (OUT_CATS[i].id === d.cat) return;
      OUT_CATS.push({ id: d.cat, label: d.cat });
    });
  })();

  /* ------------------------------------------------------------------
     3. 상태
     ------------------------------------------------------------------ */
  var STORE_KEY = "wtt:v2";
  var state = {
    selected: [],        // 재료 id 배열 (직접 입력은 "c:라벨")
    ingGroup: "common",  // 재료 탭
    ingQuery: "",        // 재료 빠른 검색
    tab: "fridge",
    mood: "any",
    budget: "any",
    method: "all",
    cat: "all",
    outCat: "all",
    query: "",
    visible: 24,
    rows: [],
    spinning: false,
    lastPick: null,
    drawerDish: null,
  };

  var MOODS = [
    { id: "any", label: "아무거나" },
    { id: "alone", label: "혼밥" },
    { id: "hearty", label: "든든한 한끼" },
    { id: "night", label: "야식" },
    { id: "hangover", label: "해장" },
    { id: "light", label: "가벼운 식단" },
  ];
  var BUDGETS = [
    { id: "any", label: "상관없음" },
    { id: "low", label: "1만원 이하" },
    { id: "mid", label: "1~2만원" },
  ];
  var METHODS = [
    { id: "all", label: "전체" },
    { id: "home", label: "집에서 만들기" },
    { id: "out", label: "배달·외식" },
  ];

  var el = {}; // DOM 캐시

  /* ------------------------------------------------------------------
     4. 유틸
     ------------------------------------------------------------------ */
  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function ing(id) {
    return BY_ID[id] || { id: id, label: String(id).replace(/^c:/, ""), emoji: "🍴", custom: true };
  }

  function ingLabel(id) {
    return BY_ID[id] ? BY_ID[id].label : String(id).replace(/^c:/, "");
  }

  function sleep(ms) {
    return new Promise(function (resolve) { setTimeout(resolve, ms); });
  }

  function findByLabel(text) {
    var key = normalize(text);
    if (!key) return null;
    if (BY_ID[key]) return BY_ID[key];
    for (var i = 0; i < ALIAS.length; i++) {
      if (ALIAS[i].key === key) return ing(ALIAS[i].id);
    }
    for (var j = 0; j < ALIAS.length; j++) {
      if (ALIAS[j].key.length >= 2 && key.indexOf(ALIAS[j].key) !== -1) return ing(ALIAS[j].id);
    }
    return null;
  }

  function formatTime(min) {
    min = Number(min) || 0;
    if (min >= 60) {
      var h = Math.floor(min / 60);
      var m = min % 60;
      return m ? h + "시간 " + m + "분" : h + "시간";
    }
    return min + "분";
  }

  function shortName(name, max) {
    var n = String(name || "");
    var limit = max || 30;
    return n.length > limit ? n.slice(0, limit - 1).trim() + "…" : n;
  }

  function levelText(level) {
    if (level >= 3) return "어려움";
    if (level === 2) return "보통";
    return "쉬움";
  }

  function save() {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify({
        selected: state.selected,
        tab: state.tab,
        mood: state.mood,
        budget: state.budget,
        method: state.method,
        cat: state.cat,
        outCat: state.outCat,
      }));
    } catch (e) { /* 저장 실패는 무시 (사생활 모드 등) */ }
  }

  function load() {
    try {
      var raw = localStorage.getItem(STORE_KEY);
      if (!raw) return;
      var data = JSON.parse(raw);
      if (data && Array.isArray(data.selected)) {
        state.selected = data.selected.filter(function (v) { return typeof v === "string"; });
      }
      if (data && (data.tab === "fridge" || data.tab === "roulette")) state.tab = data.tab;
      if (data && data.mood) state.mood = data.mood;
      if (data && data.budget) state.budget = data.budget;
      if (data && data.method) state.method = data.method;
      if (data && data.outCat) state.outCat = data.outCat;
      if (data && data.cat) {
        var okCat = CATEGORIES.some(function (c) { return c.id === data.cat; });
        if (okCat) state.cat = data.cat;
      }
    } catch (e) { /* 무시 */ }
  }

  /* ------------------------------------------------------------------
     5. 냉장고 매칭
     ------------------------------------------------------------------ */
  function matchRows(pool) {
    var have = {};
    state.selected.forEach(function (id) { have[id] = true; });

    var rows = [];
    for (var i = 0; i < pool.length; i++) {
      var d = pool[i];
      var hit = [], missing = [], bonus = [];
      for (var j = 0; j < d.req.length; j++) {
        if (have[d.req[j]]) hit.push(d.req[j]);
        else missing.push(d.req[j]);
      }
      for (var k = 0; k < d.opt.length; k++) {
        if (have[d.opt[k]]) bonus.push(d.opt[k]);
      }
      rows.push({
        dish: d,
        hit: hit,
        missing: missing,
        bonus: bonus,
        percent: d.req.length ? Math.round((hit.length / d.req.length) * 100) : 0,
        ready: d.req.length > 0 && missing.length === 0,
      });
    }
    return rows;
  }

  function buildRows() {
    var q = normalize(state.query);
    var pool = HOME_RECIPES;

    if (state.cat !== "all") {
      pool = pool.filter(function (d) { return d.cat === state.cat; });
    }
    if (q) {
      pool = pool.filter(function (d) { return d._s.indexOf(q) !== -1; });
    }

    if (state.selected.length) {
      // 필수 재료가 걸린 요리 + 고른 양념(선택 재료)이 쓰이는 요리까지 보여 준다
      var rows = matchRows(pool).filter(function (r) {
        return r.hit.length > 0 || r.bonus.length > 0;
      });
      rows.sort(function (a, b) {
        if (a.ready !== b.ready) return a.ready ? -1 : 1;
        if (b.percent !== a.percent) return b.percent - a.percent;
        if (a.missing.length !== b.missing.length) return a.missing.length - b.missing.length;
        if (b.bonus.length !== a.bonus.length) return b.bonus.length - a.bonus.length;
        return (a.dish.time || 99) - (b.dish.time || 99);
      });
      return rows;
    }

    if (!POP_RANK) {
      POP_RANK = {};
      POPULAR_IDS.forEach(function (id, i) { POP_RANK[id] = i; });
    }
    return pool.map(function (d) {
      return { dish: d, hit: [], missing: [], bonus: [], percent: 0, ready: false };
    }).sort(function (a, b) {
      var da = a.dish, db = b.dish;
      if (da.curated !== db.curated) return da.curated ? -1 : 1;
      if (da.curated) {
        var ra = POP_RANK[da.id] == null ? 99 : POP_RANK[da.id];
        var rb = POP_RANK[db.id] == null ? 99 : POP_RANK[db.id];
        if (ra !== rb) return ra - rb;
        return da._i - db._i;
      }
      if (db.reviews !== da.reviews) return db.reviews - da.reviews;
      return da.name < db.name ? -1 : 1;
    });
  }

  /* ------------------------------------------------------------------
     6. 렌더 — 재료 칩
     ------------------------------------------------------------------ */
  function ingMatches(item, q) {
    if (normalize(item.label).indexOf(q) !== -1) return true;
    for (var i = 0; i < item.aliases.length; i++) {
      if (normalize(item.aliases[i]).indexOf(q) !== -1) return true;
    }
    return false;
  }

  function renderIngTabs() {
    var wrap = el.ingTabs;
    if (!wrap) return;
    wrap.innerHTML = "";
    var frag = document.createDocumentFragment();
    ING_TABS.forEach(function (t) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "pill ing-tab";
      btn.dataset.group = t.id;
      btn.setAttribute("aria-pressed", !state.ingQuery && state.ingGroup === t.id ? "true" : "false");
      btn.innerHTML = '<span class="pill-emoji">' + t.emoji + "</span>" + escapeHtml(t.label);
      btn.addEventListener("click", function () {
        state.ingGroup = t.id;
        state.ingQuery = "";
        if (el.ingSearch) el.ingSearch.value = "";
        if (el.ingSearchClear) el.ingSearchClear.classList.add("hidden");
        renderIngTabs();
        renderChips();
      });
      frag.appendChild(btn);
    });
    wrap.appendChild(frag);
  }

  function renderChips() {
    var wrap = el.chipList;
    wrap.innerHTML = "";
    var frag = document.createDocumentFragment();
    var q = normalize(state.ingQuery);
    var list = [];

    if (q) {
      list = INGREDIENTS.filter(function (it) { return ingMatches(it, q); });
    } else if (state.ingGroup === "common" || !state.ingGroup) {
      var picked = {};
      COMMON_ORDER.forEach(function (id) {
        var it = BY_ID[id];
        if (!it || picked[it.id]) return;
        picked[it.id] = 1;
        list.push(it);
      });
      INGREDIENTS.forEach(function (it) {
        if (!it.common || picked[it.id]) return;
        picked[it.id] = 1;
        list.push(it);
      });
    } else {
      list = INGREDIENTS.filter(function (it) { return it.group === state.ingGroup; });
    }

    if (q) {
      var note = document.createElement("p");
      note.className = "ing-hint";
      note.textContent = list.length
        ? "'" + state.ingQuery + "' 검색 결과 " + list.length + "개"
        : "'" + state.ingQuery + "'에 맞는 재료가 없어요. 아래에 직접 입력해 추가할 수 있어요.";
      frag.appendChild(note);
    }

    var lastGroup = null;
    list.forEach(function (item) {
      if (q && item.group !== lastGroup) {
        lastGroup = item.group;
        var head = document.createElement("span");
        head.className = "chip-group";
        head.textContent = (GROUP_EMOJI[item.group] || "🍴") + " " + item.group;
        frag.appendChild(head);
      }
      frag.appendChild(chipNode(item.id, item.label, item.emoji, false));
    });

    // 직접 추가한 재료
    state.selected.forEach(function (id) {
      if (id.indexOf("c:") !== 0) return;
      frag.appendChild(chipNode(id, id.slice(2), "🍴", true));
    });

    wrap.appendChild(frag);
  }

  // 선택한 재료만 따로 보여 주는 줄
  function renderSelectedChips() {
    if (!el.selChips) return;
    el.selChips.innerHTML = "";
    if (!state.selected.length) {
      el.selChips.classList.add("hidden");
      return;
    }
    el.selChips.classList.remove("hidden");

    var label = document.createElement("span");
    label.className = "sel-label";
    label.textContent = "내가 고른 재료";
    el.selChips.appendChild(label);

    state.selected.forEach(function (id) {
      var it = ing(id);
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "chip is-selected";
      btn.innerHTML = '<span class="chip-emoji">' + (it.emoji || "🍴") + "</span>" +
        escapeHtml(it.label) + '<span class="chip-x" aria-hidden="true">✕</span>';
      btn.setAttribute("aria-label", it.label + " 선택 해제");
      btn.addEventListener("click", function () { toggleIngredient(id); });
      el.selChips.appendChild(btn);
    });
  }

  function chipNode(id, label, emoji, custom) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip" + (custom ? " is-custom" : "");
    btn.setAttribute("aria-pressed", state.selected.indexOf(id) !== -1 ? "true" : "false");
    btn.dataset.id = id;

    var e = document.createElement("span");
    e.className = "chip-emoji";
    e.textContent = emoji;
    var t = document.createElement("span");
    t.textContent = label;
    btn.appendChild(e);
    btn.appendChild(t);

    btn.addEventListener("click", function () { toggleIngredient(id); });
    return btn;
  }

  function toggleIngredient(id) {
    var i = state.selected.indexOf(id);
    if (i === -1) state.selected.push(id);
    else state.selected.splice(i, 1);

    if (navigator.vibrate) { try { navigator.vibrate(8); } catch (e) {} }

    renderChips();
    renderSelectedChips();
    renderSummary();
    renderResults();
    save();
  }

  function renderSummary() {
    var count = state.selected.length;
    if (!count) {
      el.selSummary.innerHTML = "<span>재료를 고르면 <strong>바로 만들 수 있는 요리</strong>를 찾아드려요</span>";
      return;
    }
    var names = state.selected.map(function (id) { return ingLabel(id); });
    var shown = names.slice(0, 4).join(", ");
    if (names.length > 4) shown += " 외 " + (names.length - 4) + "개";
    el.selSummary.innerHTML =
      "<span><strong>" + count + "개</strong> 선택 · " + escapeHtml(shown) + "</span>" +
      '<button type="button" class="link-btn" id="summaryClear">모두 지우기</button>';

    var clear = $("#summaryClear", el.selSummary);
    if (clear) clear.addEventListener("click", clearIngredients);
  }

  function clearIngredients() {
    if (!state.selected.length) return;
    state.selected = [];
    renderChips();
    renderSelectedChips();
    renderSummary();
    renderResults();
    save();
    toast("재료를 모두 지웠어요");
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /* ------------------------------------------------------------------
     7. 렌더 — 카테고리 알약 · 검색
     ------------------------------------------------------------------ */
  function renderCatPills() {
    var wrap = el.catPills;
    if (!wrap) return;
    wrap.innerHTML = "";
    var frag = document.createDocumentFragment();
    CATEGORIES.forEach(function (c) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "pill";
      btn.textContent = c.label;
      btn.dataset.cat = c.id;
      btn.setAttribute("aria-pressed", state.cat === c.id ? "true" : "false");
      btn.addEventListener("click", function () {
        state.cat = c.id;
        state.visible = 24;
        renderCatPills();
        renderResults();
        save();
      });
      frag.appendChild(btn);
    });
    wrap.appendChild(frag);
  }

  /* ------------------------------------------------------------------
     8. 렌더 — 요리 목록
     ------------------------------------------------------------------ */
  function renderResults() {
    state.rows = buildRows();
    state.visible = 24;
    renderHead();
    paintList();
  }

  function renderHead() {
    var n = state.rows.length;
    var title, sub = "";
    if (state.selected.length) {
      title = "내 재료로 만드는 요리";
      sub = n + "개 찾음";
    } else if (state.query) {
      title = "'" + state.query + "' 검색 결과";
      sub = n + "개";
    } else if (state.cat !== "all") {
      title = state.cat;
      sub = n + "개";
    } else {
      title = "전체 집밥 레시피";
      sub = n.toLocaleString("ko-KR") + "개";
    }
    el.resultHead.innerHTML =
      "<h2>" + escapeHtml(title) + "</h2><span>" + escapeHtml(sub) + "</span>";
  }

  function paintList() {
    var list = el.dishList;
    list.innerHTML = "";

    if (!state.rows.length) {
      renderEmpty();
      return;
    }

    // 처음 방문(필터 없음)일 때만 빠른 시작 카드
    if (!state.selected.length && !state.query && state.cat === "all") {
      renderStartCard(list);
    }

    var frag = document.createDocumentFragment();
    var end = Math.min(state.visible, state.rows.length);
    for (var i = 0; i < end; i++) {
      frag.appendChild(dishNode(state.rows[i], i, state.selected.length > 0));
    }
    list.appendChild(frag);

    if (state.rows.length > end) {
      var more = document.createElement("button");
      more.type = "button";
      more.className = "ghost-btn more-btn";
      more.textContent = "레시피 " + (state.rows.length - end).toLocaleString("ko-KR") + "개 더 보기";
      more.addEventListener("click", function () {
        var start = state.visible;
        state.visible = Math.min(state.visible + 24, state.rows.length);
        more.parentNode.removeChild(more);
        var f = document.createDocumentFragment();
        for (var j = start; j < state.visible; j++) {
          f.appendChild(dishNode(state.rows[j], j, state.selected.length > 0));
        }
        list.appendChild(f);
        if (state.rows.length > state.visible) {
          list.appendChild(more);
          more.textContent = "레시피 " + (state.rows.length - state.visible).toLocaleString("ko-KR") + "개 더 보기";
        }
      });
      list.appendChild(more);
    }
  }

  var POP_RANK = null;

  var POPULAR_IDS = [
    "kimchi-fried-rice", "tuna-mayo", "ganjang-gyeran-bap",
    "tteokbokki", "gyeranmari", "kimchi-ramyeon",
  ];

  function appendPopular(list) {
    var frag = document.createDocumentFragment();
    POPULAR_IDS.forEach(function (id, i) {
      var d = null;
      for (var k = 0; k < RECIPES.length; k++) {
        if (RECIPES[k].id === id) { d = RECIPES[k]; break; }
      }
      if (!d) return;
      frag.appendChild(dishNode({
        dish: d, hit: [], missing: [], bonus: [], percent: 0, ready: false,
      }, i, false));
    });
    list.appendChild(frag);
  }

  function renderStartCard(list) {
    var box = document.createElement("div");
    box.className = "empty compact";
    box.innerHTML =
      '<h3>가진 재료만 골라도 돼요</h3>' +
      "<p>위에서 재료를 누르면 지금 바로 만들 수 있는 요리를 찾아드려요.<br>" +
      "재료 없이도 검색이나 카테고리로 1,400개가 넘는 레시피를 둘러볼 수 있어요.</p>" +
      '<button type="button" class="quick-start" id="quickStart">자주 있는 재료로 시작하기</button>';
    list.appendChild(box);
    bindQuickStart(box);
  }

  function bindQuickStart(box) {
    var quick = $("#quickStart", box);
    if (!quick) return;
    quick.addEventListener("click", function () {
      state.selected = ["egg", "kimchi", "rice", "pa"];
      renderChips();
      renderSelectedChips();
      renderSummary();
      renderResults();
      save();
      toast("자주 있는 재료 4개를 골랐어요");
    });
  }

  function renderEmpty() {
    var box = document.createElement("div");
    box.className = "empty compact";
    box.innerHTML =
      '<span class="e-emoji">🧑‍🍳</span>' +
      "<h3>조건에 맞는 레시피가 없어요</h3>" +
      "<p>재료를 한두 개 더 고르거나, 검색어·카테고리를 바꿔보세요.<br>아래는 오늘 인기 레시피예요.</p>";
    el.dishList.appendChild(box);
    appendPopular(el.dishList);
  }

  function dishNode(row, index, showMatch) {
    var d = row.dish;
    var card = document.createElement("button");
    card.type = "button";
    card.className = "dish" + (row.ready ? " is-ready" : "");
    if (index < 12) card.style.animationDelay = Math.min(index * 0.035, 0.25) + "s";
    card.setAttribute("aria-label", d.name + " 레시피 보기");

    var html = "";
    html += '<div class="dish-top">';
    html += '<div class="dish-thumb">' + d.emoji + "</div>";
    html += '<div class="dish-main">';
    html += '<div class="dish-name">' + escapeHtml(shortName(d.name));
    if (row.ready) html += '<span class="ready-tag">바로 가능</span>';
    html += "</div>";
    html += '<div class="dish-meta"><span class="cat-tag">' + escapeHtml(d.cat) + "</span>";
    html += "<span>⏱ " + formatTime(d.time) + "</span><i>·</i><span>" + levelText(d.level) + "</span>";
    if (d.reviews >= 30) html += "<i>·</i><span>후기 " + d.reviews + "</span>";
    html += "</div></div>";

    if (showMatch) {
      html += '<div class="match' + (row.ready ? " is-ready" : "") + '">';
      html += '<div class="match-num">' + row.percent + "<small>%</small></div>";
      html += '<div class="match-bar"><i style="width:' + row.percent + '%"></i></div>';
      html += "</div>";
    }
    html += "</div>";

    if (d.req.length) {
      html += '<div class="ing-row">';
      var shown = showMatch ? d.req : d.req.slice(0, 5);
      shown.forEach(function (id) {
        if (!showMatch) {
          html += '<span class="ing plain">' + escapeHtml(ingLabel(id)) + "</span>";
          return;
        }
        var has = row.hit.indexOf(id) !== -1;
        html += '<span class="ing' + (has ? "" : " miss") + '">' + escapeHtml(ingLabel(id)) + "</span>";
      });
      if (!showMatch && d.req.length > 5) {
        html += '<span class="ing more">+' + (d.req.length - 5) + "</span>";
      }
      if (showMatch && d.opt.length) {
        d.opt.slice(0, 3).forEach(function (id) {
          var has = state.selected.indexOf(id) !== -1;
          html += '<span class="ing opt' + (has ? " has" : "") + '">' + escapeHtml(ingLabel(id)) + "</span>";
        });
        if (d.opt.length > 3) {
          html += '<span class="ing more">+' + (d.opt.length - 3) + "</span>";
        }
      }
      html += "</div>";
    }

    if (showMatch) {
      if (row.ready) {
        html += '<div class="miss-line" style="color:#12805a"><span class="dot" style="background:#17a673"></span>재료가 모두 준비됐어요! 지금 바로 요리하세요</div>';
      } else if (row.missing.length) {
        html += '<div class="miss-line"><span class="dot"></span>' +
          row.missing.map(ingLabel).join(", ") + "만 더 있으면 돼요</div>";
      }
    }

    card.innerHTML = html;
    card.addEventListener("click", function () { openDrawer(d); });
    return card;
  }

  /* ------------------------------------------------------------------
     9. 룰렛 모드
     ------------------------------------------------------------------ */
  function renderFilters() {
    el.moodSeg.innerHTML = "";
    el.budgetSeg.innerHTML = "";
    el.methodSeg.innerHTML = "";
    if (el.catSeg) el.catSeg.innerHTML = "";
    if (el.outCatSeg) el.outCatSeg.innerHTML = "";

    MOODS.forEach(function (m) {
      el.moodSeg.appendChild(segButton(m.label, state.mood === m.id, function () {
        state.mood = m.id;
        renderFilters();
        renderPoolHint();
        save();
      }));
    });
    BUDGETS.forEach(function (b) {
      el.budgetSeg.appendChild(segButton(b.label, state.budget === b.id, function () {
        state.budget = b.id;
        renderFilters();
        renderPoolHint();
        save();
      }));
    });
    METHODS.forEach(function (m) {
      el.methodSeg.appendChild(segButton(m.label, state.method === m.id, function () {
        state.method = m.id;
        if (m.id === "home") state.outCat = "all";
        if (m.id === "out") state.cat = "all";
        renderFilters();
        renderPoolHint();
        save();
      }));
    });
    if (el.catSeg) {
      CATEGORIES.forEach(function (c) {
        el.catSeg.appendChild(segButton(c.label, state.cat === c.id, function () {
          state.cat = c.id;
          if (c.id !== "all") state.outCat = "all";
          renderFilters();
          renderPoolHint();
          save();
        }));
      });
    }
    if (el.outCatSeg) {
      OUT_CATS.forEach(function (c) {
        var label = c.id === "all" ? "전체" : (OUT_EMOJI[c.id] || "🛵") + " " + c.label;
        el.outCatSeg.appendChild(segButton(label, state.outCat === c.id, function () {
          state.outCat = c.id;
          if (c.id !== "all") state.cat = "all";
          renderFilters();
          renderPoolHint();
          save();
        }));
      });
    }
    if (el.catRow) el.catRow.classList.toggle("hidden", state.method === "out");
    if (el.outCatRow) el.outCatRow.classList.toggle("hidden", state.method === "home");
  }

  function segButton(label, active, onClick) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = label;
    btn.setAttribute("aria-pressed", active ? "true" : "false");
    btn.addEventListener("click", onClick);
    return btn;
  }

  function getPool() {
    var homeCat = state.method === "out" ? "all" : state.cat;
    var outCat = state.method === "home" ? "all" : state.outCat;

    return ALLDISH.filter(function (d) {
      if (state.method !== "all" && d.method !== state.method) return false;
      if (d.method === "out") {
        if (outCat !== "all" && d.cat !== outCat) return false;
        // 집밥 종류를 골랐으면 배달은 후보에서 뺀다
        if (homeCat !== "all") return false;
      } else {
        if (homeCat !== "all" && d.cat !== homeCat) return false;
        // 배달 종류를 골랐으면 집밥은 후보에서 뺀다
        if (outCat !== "all") return false;
      }
      if (state.mood !== "any" && d.moods.indexOf(state.mood) === -1) return false;
      if (state.budget === "low" && d.budget !== "low") return false;
      if (state.budget === "mid" && d.budget === "high") return false;
      return true;
    });
  }

  function renderPoolHint() {
    var pool = getPool();
    if (!pool.length) {
      el.poolLabel.textContent = "조건에 맞는 메뉴가 없어요 · 필터를 풀어보세요";
      el.spinBtn.disabled = true;
    } else {
      el.poolLabel.textContent = pool.length.toLocaleString("ko-KR") + "개 메뉴 중에서 뽑아요";
      el.spinBtn.disabled = state.spinning;
    }
    renderPoolPreview(pool);
  }

  function renderPoolPreview(pool) {
    if (!el.poolPreview) return;
    el.poolPreview.innerHTML = "";

    var head = document.createElement("div");
    head.className = "preview-head";
    head.innerHTML = "<span>이 중에서 뽑아요</span><b>" + pool.length.toLocaleString("ko-KR") + "개</b>";
    el.poolPreview.appendChild(head);

    if (!pool.length) return;

    var wrap = document.createElement("div");
    wrap.className = "chips";
    // 중복 없이 14개 미리보기
    var picks = [], idx = [];
    while (idx.length < Math.min(14, pool.length)) {
      var k = Math.floor(Math.random() * pool.length);
      if (idx.indexOf(k) === -1) idx.push(k);
    }
    idx.forEach(function (k) { picks.push(pool[k]); });
    picks.forEach(function (d) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "chip mini";
      b.innerHTML = '<span class="chip-emoji">' + d.emoji + "</span><span>" +
        escapeHtml(shortName(d.name, 20)) + "</span>";
      b.addEventListener("click", function () { openDrawer(d); });
      wrap.appendChild(b);
    });
    el.poolPreview.appendChild(wrap);
  }

  function setReel(dish) {
    if (!dish) {
      el.reelEmoji.textContent = "🍳";
      el.reelName.textContent = "오늘 뭐 먹지?";
      el.reelSub.textContent = "필터를 고르고 돌려보세요";
      return;
    }
    el.reelEmoji.textContent = dish.emoji;
    el.reelName.textContent = dish.name;
    el.reelSub.textContent = dish.method === "home"
      ? dish.cat + " · " + formatTime(dish.time) + " · " + levelText(dish.level)
      : (OUT_EMOJI[dish.cat] || "🛵") + " " + dish.cat + " · " + dish.price;
  }

  async function spin() {
    if (state.spinning) return;
    var pool = getPool();
    if (!pool.length) {
      toast("조건에 맞는 메뉴가 없어요. 필터를 풀어주세요");
      return;
    }

    state.spinning = true;
    state.lastPick = null;
    el.roulette.classList.remove("hidden");
    el.spinBtn.disabled = true;
    el.spinBtn.innerHTML = "<span>돌리는 중…</span>";
    el.reel.classList.add("is-spinning");
    el.reel.classList.remove("is-landed");
    el.result.classList.add("hidden");
    if (navigator.vibrate) { try { navigator.vibrate([12, 40, 12]); } catch (e) {} }

    var target = pool[Math.floor(Math.random() * pool.length)];
    var steps = 14 + Math.floor(Math.random() * 6);
    var delay = 52;

    for (var i = 0; i < steps; i++) {
      var shown = i === steps - 1
        ? target
        : pool[Math.floor(Math.random() * pool.length)];
      setReel(shown);
      await sleep(delay);
      delay = Math.min(delay * 1.16, 260);
    }

    setReel(target);
    el.reel.classList.remove("is-spinning");
    el.reel.classList.add("is-landed");
    state.spinning = false;
    state.lastPick = target;
    el.spinBtn.disabled = false;
    el.spinBtn.innerHTML = "<span>한 번 더 돌리기</span>";
    renderResult(target);
    el.roulette.classList.add("hidden");
    if (navigator.vibrate) { try { navigator.vibrate(24); } catch (e) {} }
  }

  function renderResult(dish) {
    el.result.classList.remove("hidden");
    el.result.innerHTML = "";

    var wrap = document.createElement("div");
    var meta = dish.method === "home"
      ? [dish.cat, "⏱ " + formatTime(dish.time), levelText(dish.level), "🏠 집에서"]
      : [dish.price, (OUT_EMOJI[dish.cat] || "🛵") + " " + dish.cat, moodLabel(dish.moods[0])];

    var html = "";
    html += '<div class="result-emoji">' + dish.emoji + "</div>";
    html += '<div class="result-label">오늘의 메뉴</div>';
    html += '<div class="result-name">' + escapeHtml(dish.name) + "</div>";
    html += '<p class="result-comment">' + escapeHtml(dish.comment || "오늘은 이걸로 정해요!") + "</p>";
    html += '<div class="result-tags">';
    meta.forEach(function (t) { html += '<span class="tag">' + escapeHtml(t) + "</span>"; });
    html += "</div>";
    html += '<div class="result-actions">';
    html += '<button type="button" class="btn-soft" data-act="again">🔄 다시</button>';
    html += '<button type="button" class="btn-primary" data-act="share">📤 공유하기</button>';
    html += '<button type="button" class="btn-outline" data-act="recipe">📖 ' + (dish.method === "home" ? "레시피" : "주문 팁") + "</button>";
    html += "</div>";
    wrap.innerHTML = html;
    el.result.appendChild(wrap);

    var confetti = document.createElement("div");
    confetti.className = "confetti";
    var bits = ["🎉", "✨", "🍽️", "😋", "🔥", "⭐"];
    for (var i = 0; i < 12; i++) {
      var s = document.createElement("i");
      s.textContent = bits[i % bits.length];
      s.style.left = 12 + Math.random() * 76 + "%";
      s.style.setProperty("--dx", (Math.random() * 160 - 80).toFixed(0) + "px");
      s.style.setProperty("--dy", (-60 - Math.random() * 90).toFixed(0) + "px");
      s.style.setProperty("--rot", (Math.random() * 300 - 150).toFixed(0) + "deg");
      s.style.animationDelay = (i * 0.035).toFixed(2) + "s";
      confetti.appendChild(s);
    }
    el.result.appendChild(confetti);
    setTimeout(function () {
      if (confetti.parentNode) confetti.parentNode.removeChild(confetti);
    }, 1500);

    var again = $('[data-act="again"]', wrap);
    var share = $('[data-act="share"]', wrap);
    var recipe = $('[data-act="recipe"]', wrap);
    if (again) again.addEventListener("click", spin);
    if (share) share.addEventListener("click", function () { sharePick(dish); });
    if (recipe) recipe.addEventListener("click", function () { openDrawer(dish); });

    el.result.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function moodLabel(id) {
    for (var i = 0; i < MOODS.length; i++) {
      if (MOODS[i].id === id) return MOODS[i].label;
    }
    return "";
  }

  /* ------------------------------------------------------------------
     10. 공유
     ------------------------------------------------------------------ */
  function shareText(dish) {
    var lines = [];
    lines.push("오늘 메뉴는 " + dish.name + " 당첨! " + dish.emoji);
    if (dish.comment) lines.push(dish.comment);
    if (dish.method === "home") {
      lines.push("⏱ " + formatTime(dish.time) + " · " + levelText(dish.level) + " · " + dish.cat);
    } else {
      lines.push(dish.price + " · " + dish.cat + " (배달·외식)");
      if (dish.tip) lines.push("💡 " + dish.tip);
    }
    if (/^https?:/.test(location.protocol)) lines.push(location.href);
    return lines.join("\n");
  }

  function sharePick(dish) {
    var text = shareText(dish);
    if (navigator.share) {
      navigator.share({ title: "오늘 뭐 먹지? — " + dish.name, text: text })
        .catch(function () { /* 사용자가 취소한 경우 */ });
      return;
    }
    copyText(text).then(function (ok) {
      toast(ok ? "결과를 복사했어요! 붙여넣기 해보세요" : "복사가 안 됐어요. 길게 눌러 복사해 주세요");
    });
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text)
        .then(function () { return true; })
        .catch(function () { return legacyCopy(text); });
    }
    return Promise.resolve(legacyCopy(text));
  }

  function legacyCopy(text) {
    try {
      var area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.top = "-1000px";
      document.body.appendChild(area);
      area.select();
      area.setSelectionRange(0, area.value.length);
      var ok = document.execCommand("copy");
      document.body.removeChild(area);
      return ok;
    } catch (e) {
      return false;
    }
  }

  /* ------------------------------------------------------------------
     11. 레시피 드로어
     ------------------------------------------------------------------ */
  function openDrawer(dish) {
    state.drawerDish = dish;
    var has = function (id) { return !!id && state.selected.indexOf(id) !== -1; };

    var html = "";
    html += '<div class="drawer-grip"></div>';
    html += '<div class="drawer-head">';
    html += '<div class="drawer-emoji">' + dish.emoji + "</div>";
    html += "<div>";
    html += '<div class="drawer-title" id="drawerTitle">' + escapeHtml(dish.name) + "</div>";
    html += '<div class="drawer-sub">' + escapeHtml(drawerSub(dish)) + "</div>";
    html += "</div>";
    html += '<button type="button" class="drawer-close" aria-label="닫기" data-act="close">✕</button>';
    html += "</div>";
    html += '<div class="drawer-body">';

    if (dish.method === "home") {
      html += '<div class="drawer-section"><h3>재료' +
        (dish.servings ? ' <small>' + escapeHtml(dish.servings) + " 기준</small>" : "") +
        "</h3>";
      if (state.selected.length) {
        var mine = 0;
        dish.req.forEach(function (id) { if (has(id)) mine++; });
        html += '<p class="drawer-match">내 재료로 <b>' + mine + " / " + dish.req.length +
          "</b> 준비됨</p>";
      }
      html += '<ul class="ing-list">';
      dish.ing.forEach(function (row) {
        var name = row[0], amt = row[1] || "", id = row[2] || "";
        var ok = has(id);
        var essential = id && dish.req.indexOf(id) !== -1;
        html += '<li class="' + (ok ? "is-on" : "") + '">' +
          '<span class="ing-tick">' + (ok ? "✓" : "·") + "</span>" +
          '<span class="ing-name">' + escapeHtml(name) + "</span>" +
          '<span class="ing-amt">' + escapeHtml(amt) + (essential ? "" : "") + "</span></li>";
      });
      html += "</ul></div>";

      if (dish.steps.length) {
        html += '<div class="drawer-section"><h3>만드는 법</h3><ol class="steps">';
        dish.steps.forEach(function (s, i) {
          html += "<li><b>" + (i + 1) + "</b><span>" + escapeHtml(s) + "</span></li>";
        });
        html += "</ol></div>";
      }
    } else {
      html += '<div class="drawer-section"><h3>배달·외식 메뉴</h3>';
      html += '<div class="price-card">';
      html += '<div class="price-card-label">예상 주문 가격</div>';
      html += '<div class="price-card-value">' + escapeHtml(dish.price) + "</div>";
      html += '<div class="price-card-sub">2026년 서울 기준 · 배달비 별도</div>';
      html += "</div>";
      html += '<div class="check-row">';
      html += '<span class="check is-cat">' + (OUT_EMOJI[dish.cat] || "🛵") + " " + escapeHtml(dish.cat) + "</span>";
      var bLabel = { under10k: "1만원 이하", "10to20k": "1만~2만원", over20k: "2만원 이상" }[dish.bracket] || "";
      if (bLabel) html += '<span class="check is-budget">' + escapeHtml(bLabel) + "</span>";
      dish.moods.forEach(function (m) {
        html += '<span class="check is-mood">' + moodLabel(m) + "</span>";
      });
      html += "</div></div>";
    }

    if (dish.tip) {
      var tipTitle = dish.method === "out" ? "💡 주문 팁" : "💡 요리 팁";
      html += '<div class="tip-box"><b>' + tipTitle + "</b> " + escapeHtml(dish.tip) + "</div>";
    }

    if (dish.src) {
      html += '<div class="source-box">' +
        '<a href="' + escapeHtml(dish.src) + '" target="_blank" rel="noopener noreferrer">' +
        "만개의레시피 원문 보기 ↗</a>" +
        (dish.author ? '<span class="src-author">' + escapeHtml(dish.author) + "</span>" : "") +
        "</div>";
    }
    html += "</div>";

    html += '<div class="drawer-foot">';
    html += '<button type="button" class="btn-soft" data-act="share">📤 공유</button>';
    html += '<button type="button" class="btn-primary" data-act="close">닫기</button>';
    html += "</div>";

    el.drawerPanel.innerHTML = html;
    el.drawer.hidden = false;
    document.body.style.overflow = "hidden";

    Array.prototype.forEach.call(el.drawerPanel.querySelectorAll('[data-act="close"]'), function (b) {
      b.addEventListener("click", closeDrawer);
    });
    var shareBtn = el.drawerPanel.querySelector('[data-act="share"]');
    if (shareBtn) shareBtn.addEventListener("click", function () { sharePick(dish); });
    el.drawerPanel.querySelector(".drawer-body").scrollTop = 0;

    var closeBtn = el.drawerPanel.querySelector(".drawer-close");
    if (closeBtn) closeBtn.focus({ preventScroll: true });
  }

  function drawerSub(dish) {
    if (dish.method === "home") {
      return [dish.cat, "⏱ " + formatTime(dish.time), levelText(dish.level)]
        .filter(Boolean).join(" · ");
    }
    return dish.price + " · " + dish.cat + " · 배달·외식";
  }

  function closeDrawer() {
    el.drawer.hidden = true;
    document.body.style.overflow = "";
    state.drawerDish = null;
  }

  /* ------------------------------------------------------------------
     12. 탭 전환 / 토스트
     ------------------------------------------------------------------ */
  function setTab(tab) {
    state.tab = tab;
    el.tabs.forEach(function (btn) {
      var on = btn.dataset.view === tab;
      btn.setAttribute("aria-selected", on ? "true" : "false");
    });
    el.viewFridge.classList.toggle("hidden", tab !== "fridge");
    el.viewRoulette.classList.toggle("hidden", tab !== "roulette");
    window.scrollTo({ top: 0, behavior: "smooth" });
    save();
  }

  var toastTimer = null;
  function toast(message) {
    el.toast.textContent = message;
    el.toast.classList.add("is-on");
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      el.toast.classList.remove("is-on");
    }, 2200);
  }

  /* ------------------------------------------------------------------
     13. 초기화
     ------------------------------------------------------------------ */
  function init() {
    el.chipList = $("#chipList");
    el.ingTabs = $("#ingTabs");
    el.ingSearch = $("#ingSearch");
    el.ingSearchClear = $("#ingSearchClear");
    el.selChips = $("#selChips");
    el.customForm = $("#customForm");
    el.customInput = $("#customInput");
    el.selSummary = $("#selSummary");
    el.resultHead = $("#resultHead");
    el.dishList = $("#dishList");
    el.catPills = $("#catPills");
    el.searchInput = $("#dishSearch");
    el.searchClear = $("#searchClear");
    el.heroStat = $("#heroStat");
    el.viewFridge = $("#view-fridge");
    el.viewRoulette = $("#view-roulette");
    el.moodSeg = $("#moodSeg");
    el.budgetSeg = $("#budgetSeg");
    el.methodSeg = $("#methodSeg");
    el.catSeg = $("#catSeg");
    el.outCatSeg = $("#outCatSeg");
    el.catRow = $("#catRow");
    el.outCatRow = $("#outCatRow");
    el.poolLabel = $("#poolLabel");
    el.reel = $("#reel");
    el.reelEmoji = $("#reelEmoji");
    el.reelName = $("#reelName");
    el.reelSub = $("#reelSub");
    el.spinBtn = $("#spinBtn");
    el.poolPreview = $("#poolPreview");
    el.roulette = $(".roulette");
    el.result = $("#rouletteResult");
    el.drawer = $("#drawer");
    el.drawerPanel = $("#drawerPanel");
    el.toast = $("#toast");
    el.tabs = Array.prototype.slice.call(document.querySelectorAll(".tab"));

    load();

    if (el.ingSearch) {
      var ingTimer = null;
      el.ingSearch.addEventListener("input", function () {
        var value = el.ingSearch.value;
        if (ingTimer) clearTimeout(ingTimer);
        ingTimer = setTimeout(function () {
          state.ingQuery = value.trim();
          if (el.ingSearchClear) el.ingSearchClear.classList.toggle("hidden", !state.ingQuery);
          renderIngTabs();
          renderChips();
        }, 120);
      });
    }
    if (el.ingSearchClear) {
      el.ingSearchClear.addEventListener("click", function () {
        el.ingSearch.value = "";
        state.ingQuery = "";
        el.ingSearchClear.classList.add("hidden");
        renderIngTabs();
        renderChips();
        el.ingSearch.focus();
      });
    }

    el.customForm.addEventListener("submit", function (event) {
      event.preventDefault();
      var raw = el.customInput.value.trim();
      if (!raw) return;

      var found = findByLabel(raw);
      if (found) {
        if (state.selected.indexOf(found.id) === -1) {
          state.selected.push(found.id);
          toast("'" + raw + "' → " + found.label + " 재료로 추가했어요");
        } else {
          toast("이미 고른 재료예요");
        }
      } else {
        var id = "c:" + raw.slice(0, 10);
        if (state.selected.indexOf(id) === -1) {
          state.selected.push(id);
          toast("'" + raw + "' 추가! 직접 넣은 재료는 매칭에 쓰이지 않아요");
        }
      }

      el.customInput.value = "";
      renderChips();
      renderSelectedChips();
      renderSummary();
      renderResults();
      save();
    });

    var searchTimer = null;
    if (el.searchInput) {
      el.searchInput.addEventListener("input", function () {
        var value = el.searchInput.value;
        if (searchTimer) clearTimeout(searchTimer);
        searchTimer = setTimeout(function () {
          state.query = value.trim();
          if (el.searchClear) el.searchClear.classList.toggle("hidden", !state.query);
          renderResults();
        }, 140);
      });
    }
    if (el.searchClear) {
      el.searchClear.addEventListener("click", function () {
        el.searchInput.value = "";
        state.query = "";
        el.searchClear.classList.add("hidden");
        renderResults();
        el.searchInput.focus();
      });
    }

    el.tabs.forEach(function (btn) {
      btn.addEventListener("click", function () { setTab(btn.dataset.view); });
    });

    el.spinBtn.addEventListener("click", spin);

    el.drawer.addEventListener("click", function (event) {
      if (event.target === el.drawer || event.target.classList.contains("drawer-backdrop")) {
        closeDrawer();
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !el.drawer.hidden) closeDrawer();
    });

    if (el.heroStat) {
      el.heroStat.textContent = "집밥 " + HOME_RECIPES.length.toLocaleString("ko-KR") +
        " · 배달·외식 " + (ALLDISH.length - HOME_RECIPES.length) +
        " · 재료 " + INGREDIENTS.length + "종";
    }

    // 초기 렌더
    renderIngTabs();
    renderChips();
    renderSelectedChips();
    renderSummary();
    renderCatPills();
    renderFilters();
    renderPoolHint();
    setReel(null);
    renderResults();
    setTab(state.tab);

    el.result.classList.add("hidden");

    // 서비스 워커 (오프라인 지원, https/localhost에서만)
    if ("serviceWorker" in navigator && /^https?:$/.test(location.protocol)) {
      window.addEventListener("load", function () {
        navigator.serviceWorker.register("./sw.js").catch(function () { /* 무시 */ });
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
