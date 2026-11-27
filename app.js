/* ==========================================================================
   냉장고 파먹기 — 오늘 뭐 먹지
   - 모드 1: 냉장고 재료 매칭 (계란·김치·두부 … 보유 재료로 만들 수 있는 요리 추천)
   - 모드 2: 기분·예산·방식 룰렛 (오늘 뭐 먹지?)
   - 공유: Web Share API → 클립보드 순으로 폴백
   ========================================================================== */

(function () {
  "use strict";

  /* ------------------------------------------------------------------
     1. 재료 데이터 (냉장고 칩)
     ------------------------------------------------------------------ */
  var INGREDIENTS = [
    { id: "egg", label: "계란", emoji: "🥚", common: true },
    { id: "kimchi", label: "김치", emoji: "🌶️", common: true },
    { id: "tofu", label: "두부", emoji: "🧊", common: true },
    { id: "pa", label: "대파", emoji: "🌿", common: true },
    { id: "onion", label: "양파", emoji: "🧅", common: true },
    { id: "garlic", label: "마늘", emoji: "🧄", common: true },
    { id: "ham", label: "스팸·햄", emoji: "🥓", common: true },
    { id: "tuna", label: "참치캔", emoji: "🐟", common: true },
    { id: "rice", label: "밥", emoji: "🍚", common: true },
    { id: "ramen", label: "라면·면", emoji: "🍜", common: true },
    { id: "pasta", label: "파스타면", emoji: "🍝", common: true },
    { id: "cheese", label: "치즈", emoji: "🧀", common: true },
    { id: "potato", label: "감자", emoji: "🥔", common: true },
    { id: "pork", label: "돼지고기·베이컨", emoji: "🥩", common: true },
    { id: "chicken", label: "닭가슴살", emoji: "🍗", common: true },
    { id: "bean", label: "콩나물", emoji: "🌱", common: true },
    { id: "fishcake", label: "어묵", emoji: "🍢", common: true },
    { id: "mushroom", label: "버섯", emoji: "🍄", common: true },
    { id: "sauce", label: "장류·양념", emoji: "🥫", common: true },
    { id: "milk", label: "우유", emoji: "🥛", common: false },
    { id: "butter", label: "버터", emoji: "🧈", common: false },
    { id: "bread", label: "식빵", emoji: "🍞", common: false },
    { id: "cabbage", label: "양배추", emoji: "🥬", common: false },
    { id: "cucumber", label: "오이", emoji: "🥒", common: false },
    { id: "carrot", label: "당근", emoji: "🥕", common: false },
    { id: "tteok", label: "떡", emoji: "🍡", common: false },
    { id: "tomato", label: "토마토", emoji: "🍅", common: false },
    { id: "flour", label: "부침가루", emoji: "🌾", common: false },
    { id: "curry", label: "카레가루", emoji: "🍛", common: false },
  ];

  // 직접 입력한 재료를 기존 재료로 연결하는 별칭
  var ALIASES = {
    계란: "egg", 달걀: "egg", 에그: "egg", 계란후라이: "egg",
    김치: "kimchi", 김치속: "kimchi", 포기김치: "kimchi",
    두부: "tofu", 순두부: "tofu", 찌개두부: "tofu", 부침두부: "tofu",
    대파: "pa", 파: "pa", 쪽파: "pa", 실파: "pa", 다진파: "pa",
    양파: "onion", 적양파: "onion",
    마늘: "garlic", 다진마늘: "garlic", 통마늘: "garlic", 마늘쫑: "garlic",
    스팸: "ham", 햄: "ham", 소시지: "ham", 비엔나: "ham", 베이컨: "ham",
    참치: "tuna", 참치캔: "tuna", 동원참치: "tuna", 동원: "tuna",
    밥: "rice", 쌀밥: "rice", 찬밥: "rice", 공기밥: "rice", 즉석밥: "rice",
    라면: "ramen", 라멘: "ramen", 면: "ramen", 소면: "ramen", 국수: "ramen",
    파스타: "pasta", 파스타면: "pasta", 스파게티: "pasta", 스파게티면: "pasta", 링귀니: "pasta",
    치즈: "cheese", 슬라이스치즈: "cheese", 모짜렐라: "cheese", 스트링: "cheese",
    감자: "potato", 알감자: "potato",
    돼지고기: "pork", 삼겹살: "pork", 목살: "pork", 앞다리살: "pork", 다진고기: "pork",
    닭가슴살: "chicken", 닭고기: "chicken", 닭다리: "chicken",
    콩나물: "bean", 숙주: "bean",
    어묵: "fishcake", 오뎅: "fishcake", 사각어묵: "fishcake",
    버섯: "mushroom", 표고: "mushroom", 느타리: "mushroom", 양송이: "mushroom", 새송이: "mushroom",
    고추장: "sauce", 간장: "sauce", 된장: "sauce", 쌈장: "sauce", 양념: "sauce", 굴소스: "sauce",
    우유: "milk", 버터: "butter", 식빵: "bread", 빵: "bread", 토스트: "bread",
    양배추: "cabbage", 오이: "cucumber", 당근: "carrot",
    떡: "tteok", 떡볶이떡: "tteok", 가래떡: "tteok",
    토마토: "tomato", 방울토마토: "tomato",
    부침가루: "flour", 밀가루: "flour", 튀김가루: "flour",
    카레: "curry", 카레가루: "curry",
  };

  /* ------------------------------------------------------------------
     2. 요리 데이터베이스
        method: home(집에서) / out(배달·외식)
        moods : alone(혼밥) hearty(든든한 한끼) night(야식) hangover(해장) light(가벼운 식단)
        budget: low(1만원 이하) mid(1~2만원) high(2만원 이상)
     ------------------------------------------------------------------ */
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
      req: ["egg", "rice", "sauce"], opt: ["butter", "pa"],
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
      req: ["tofu", "potato", "onion", "sauce"], opt: ["mushroom", "pa"],
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
      req: ["tteok", "sauce"], opt: ["egg", "fishcake", "pa", "cheese"],
      moods: ["night", "hearty"], budget: "low", method: "home",
      steps: [
        "떡을 물에 5분 담가 말랑하게 해 주세요.",
        "물 2컵에 고추장 2큰술, 설탕 1큰술을 풀어요.",
        "떡과 어묵, 대파를 넣고 8분 졸여 주세요.",
        "불을 줄이고 치즈나 삶은 계란을 올려요.",
      ],
      tip: "떡을 미리 불리면 쫄깃함이 살아요.",
      comment: "야식의 왕, 실패 없는 떡볶이 🌶️",
    },
    {
      id: "rabokki", name: "라볶이", emoji: "🍜", time: 18, level: 1,
      req: ["tteok", "ramen", "sauce"], opt: ["fishcake", "egg", "cheese"],
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
      req: ["pork", "onion", "sauce"], opt: ["garlic", "pa", "cabbage"],
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
      tip: "약불에서 천천히 익혀야 부드러워요.",
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
      tip: "참치 기름을 빼면 국물이 깔끔해요.",
      comment: "고기 없이도 깊은 맛, 참치의 힘 🐟",
    },
    {
      id: "dubu-jorim", name: "두부조림", emoji: "🍲", time: 15, level: 1,
      req: ["tofu", "sauce"], opt: ["pa", "onion"],
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
      req: ["potato", "sauce"], opt: ["onion", "carrot"],
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
      tip: "밥은 찬밥이 고슬고슬해서 좋아요.",
      comment: "단백질 가득, 다이어터 볶음밥 🍗",
    },
    {
      id: "oi-muchim", name: "오이무침", emoji: "🥒", time: 8, level: 1,
      req: ["cucumber", "garlic", "sauce"], opt: ["onion"],
      moods: ["light", "hangover"], budget: "low", method: "home",
      steps: [
        "오이를 반달 모양으로 썰어 소금에 5분 절여요.",
        "물기를 살짝 짜 주세요.",
        "고춧가루, 다진 마늘, 식초, 설탕으로 무쳐요.",
        "통깨를 뿌려 완성!",
      ],
      tip: "절인 오이는 아삭함이 살아 있어요.",
      comment: "입맛 없을 때 딱, 새콤달콤 🥒",
    },
    {
      id: "pork-cabbage", name: "돼지고기 양배추볶음", emoji: "🥬", time: 15, level: 2,
      req: ["pork", "cabbage", "sauce"], opt: ["pa"],
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
      req: ["rice", "egg", "sauce"], opt: ["bean", "cucumber", "carrot", "mushroom"],
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
      req: ["fishcake", "sauce"], opt: ["onion", "pa"],
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
      req: ["tofu", "butter"], opt: ["sauce", "pa"],
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
      req: ["tuna", "potato", "sauce"], opt: ["onion"],
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
      req: ["tteok", "egg", "sauce"], opt: ["pa", "mushroom"],
      moods: ["hangover", "hearty"], budget: "low", method: "home",
      steps: [
        "떡을 물에 10분 담가 불려요.",
        "물 4컵에 국간장으로 간을 해 끓여요.",
        "떡을 넣고 떠오를 때까지 5분 끓여요.",
        "계란 지단과 대파를 올려 완성!",
      ],
      tip: "떡이 떠오르면 다 익은 거예요.",
      comment: "명절 아니어도 좋은 떡국 🍡",
    },

    /* -------------------- 배달·외식 메뉴 -------------------- */
    {
      id: "out-chicken", name: "치킨", emoji: "🍗", price: "18,000원~", level: 1,
      req: [], opt: [], moods: ["hearty", "night"], budget: "mid", method: "out",
      tip: "반반으로 주문하면 배달비가 아깝지 않아요.",
      comment: "콜라는 필수! 오늘은 치킨 🍗",
    },
    {
      id: "out-pizza", name: "피자", emoji: "🍕", price: "15,000원~", level: 1,
      req: [], opt: [], moods: ["hearty", "night"], budget: "mid", method: "out",
      tip: "포장 주문이 보통 20~30% 저렴해요.",
      comment: "한 판이면 온 가족 든든 🍕",
    },
    {
      id: "out-jjajang", name: "짜장면", emoji: "🍜", price: "7,000원~", level: 1,
      req: [], opt: [], moods: ["alone", "hearty"], budget: "low", method: "out",
      tip: "군만두 하나 추가하면 완벽한 세트예요.",
      comment: "후루룩 넘어가는 든든한 한 그릇 🍜",
    },
    {
      id: "out-jjambbong", name: "짬뽕", emoji: "🍜", price: "8,000원~", level: 1,
      req: [], opt: [], moods: ["hangover", "hearty"], budget: "low", method: "out",
      tip: "해장엔 짬뽕 국물이 최고예요.",
      comment: "얼큰한 국물이 속을 풀어줘요 🌶️",
    },
    {
      id: "out-samgyeopsal", name: "삼겹살", emoji: "🥓", price: "12,000원/인~", level: 1,
      req: [], opt: [], moods: ["hearty"], budget: "high", method: "out",
      tip: "고기집은 보통 1인분 200g 기준이에요.",
      comment: "오늘은 고기다! 🥓",
    },
    {
      id: "out-maratang", name: "마라탕", emoji: "🍲", price: "12,000원~", level: 1,
      req: [], opt: [], moods: ["hearty", "night"], budget: "mid", method: "out",
      tip: "재료를 많이 담으면 금액이 확 올라가요.",
      comment: "중독성 있는 얼얼함 🍲",
    },
    {
      id: "out-gimbap", name: "김밥", emoji: "🍙", price: "3,500원~", level: 1,
      req: [], opt: [], moods: ["alone", "light"], budget: "low", method: "out",
      tip: "라면 하나 곁들이면 든든해요.",
      comment: "가볍게 한 끼, 부담 없는 김밥 🍙",
    },
    {
      id: "out-pho", name: "쌀국수", emoji: "🍜", price: "9,000원~", level: 1,
      req: [], opt: [], moods: ["hangover", "light"], budget: "low", method: "out",
      tip: "고수는 빼달라고 미리 말해요.",
      comment: "깔끔한 국물로 속을 달래요 🍜",
    },
    {
      id: "out-burger", name: "햄버거", emoji: "🍔", price: "8,000원~", level: 1,
      req: [], opt: [], moods: ["alone", "night"], budget: "low", method: "out",
      tip: "세트로 시키면 감튀까지 든든해요.",
      comment: "한입 베어물면 행복 🍔",
    },
    {
      id: "out-sushi", name: "초밥", emoji: "🍣", price: "15,000원~", level: 1,
      req: [], opt: [], moods: ["hearty"], budget: "high", method: "out",
      tip: "런치 세트가 저녁보다 저렴해요.",
      comment: "오늘은 나에게 선물 🍣",
    },
    {
      id: "out-naengmyeon", name: "냉면", emoji: "🍜", price: "10,000원~", level: 1,
      req: [], opt: [], moods: ["hangover", "light"], budget: "mid", method: "out",
      tip: "식초와 겨자를 넣으면 더 시원해요.",
      comment: "시원한 한 그릇으로 리셋 🧊",
    },
    {
      id: "out-donkatsu", name: "돈까스", emoji: "🍛", price: "10,000원~", level: 1,
      req: [], opt: [], moods: ["hearty"], budget: "low", method: "out",
      tip: "소스는 뿌리지 말고 찍어 먹는 게 바삭해요.",
      comment: "바삭함이 생명, 돈까스 🍛",
    },
    {
      id: "out-gukbap", name: "국밥", emoji: "🍲", price: "9,000원~", level: 1,
      req: [], opt: [], moods: ["hangover", "hearty"], budget: "low", method: "out",
      tip: "수육 한 접시 추가하면 든든해요.",
      comment: "든든하고 따뜻한 국밥 한 그릇 🍲",
    },
    {
      id: "out-jokbal", name: "족발", emoji: "🍖", price: "30,000원~", level: 1,
      req: [], opt: [], moods: ["night", "hearty"], budget: "high", method: "out",
      tip: "막국수는 세트로 시키면 저렴해요.",
      comment: "야식의 끝판왕, 족발 🍖",
    },
    {
      id: "out-salad", name: "샐러드", emoji: "🥗", price: "9,000원~", level: 1,
      req: [], opt: [], moods: ["light"], budget: "low", method: "out",
      tip: "닭가슴살 토핑을 더하면 든든해요.",
      comment: "가볍게 먹고 싶은 날 🥗",
    },
  ];

  /* ------------------------------------------------------------------
     3. 상태
     ------------------------------------------------------------------ */
  var STORE_KEY = "wtt:v1";
  var state = {
    selected: [],        // 재료 id 배열 (직접 입력은 "c:라벨")
    expandedChips: false,
    showAllDishes: false,
    tab: "fridge",
    mood: "any",
    budget: "any",
    method: "all",
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
    for (var i = 0; i < INGREDIENTS.length; i++) {
      if (INGREDIENTS[i].id === id) return INGREDIENTS[i];
    }
    return { id: id, label: id.replace(/^c:/, ""), emoji: "🍴", custom: true };
  }

  function ingLabel(id) {
    return ing(id).label;
  }

  function sleep(ms) {
    return new Promise(function (resolve) { setTimeout(resolve, ms); });
  }

  function normalize(text) {
    return String(text || "")
      .replace(/\s+/g, "")
      .replace(/[()[\]{}]/g, "")
      .trim()
      .toLowerCase();
  }

  function findByLabel(text) {
    var key = normalize(text);
    if (!key) return null;
    for (var i = 0; i < INGREDIENTS.length; i++) {
      var item = INGREDIENTS[i];
      if (normalize(item.label) === key || item.id === key) return item;
    }
    if (ALIASES[key]) return ing(ALIASES[key]);
    // 부분 일치 (예: "다진 마늘" → 마늘)
    for (var k in ALIASES) {
      if (key.indexOf(k) !== -1) return ing(ALIASES[k]);
    }
    return null;
  }

  function save() {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify({
        selected: state.selected,
        tab: state.tab,
        mood: state.mood,
        budget: state.budget,
        method: state.method,
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
    } catch (e) { /* 무시 */ }
  }

  /* ------------------------------------------------------------------
     5. 냉장고 매칭
     ------------------------------------------------------------------ */
  function matchDishes() {
    var have = {};
    state.selected.forEach(function (id) { have[id] = true; });

    var rows = DISHES.filter(function (d) { return d.method === "home"; }).map(function (d) {
      var hit = d.req.filter(function (id) { return !!have[id]; });
      var missing = d.req.filter(function (id) { return !have[id]; });
      var bonus = d.opt.filter(function (id) { return !!have[id]; });
      var percent = d.req.length ? Math.round((hit.length / d.req.length) * 100) : 100;
      return {
        dish: d,
        hit: hit,
        missing: missing,
        bonus: bonus,
        percent: percent,
        ready: missing.length === 0,
      };
    });

    var matched = rows.filter(function (r) { return r.hit.length > 0 || r.ready; });
    matched.sort(function (a, b) {
      if (b.percent !== a.percent) return b.percent - a.percent;
      if (a.missing.length !== b.missing.length) return a.missing.length - b.missing.length;
      if (b.bonus.length !== a.bonus.length) return b.bonus.length - a.bonus.length;
      return a.dish.time - b.dish.time;
    });
    return { all: matched, total: rows.length };
  }

  /* ------------------------------------------------------------------
     6. 렌더 — 재료 칩
     ------------------------------------------------------------------ */
  function renderChips() {
    var wrap = el.chipList;
    wrap.innerHTML = "";

    var list = INGREDIENTS.filter(function (item) {
      return state.expandedChips || item.common;
    });

    list.forEach(function (item) {
      wrap.appendChild(chipNode(item.id, item.label, item.emoji, false));
    });

    // 직접 추가한 재료
    state.selected.forEach(function (id) {
      if (id.indexOf("c:") !== 0) return;
      wrap.appendChild(chipNode(id, id.slice(2), "🍴", true));
    });

    var hidden = INGREDIENTS.length - list.length;
    el.moreChipsBtn.textContent = state.expandedChips
      ? "접기 ▲"
      : "재료 더 보기 (+" + hidden + ") ▼";
    el.moreChipsBtn.classList.toggle("hidden", hidden <= 0 && !state.expandedChips);
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
     7. 렌더 — 요리 목록
     ------------------------------------------------------------------ */
  function renderResults() {
    var list = el.dishList;
    list.innerHTML = "";

    var res = matchDishes();
    var hasIngredients = state.selected.length > 0;

    el.resultHead.innerHTML =
      "<h2>" +
      (hasIngredients ? "지금 만들 수 있는 요리" : "오늘의 인기 레시피") +
      "</h2><span>" +
      (hasIngredients ? res.all.length + "개 찾음" : "") +
      "</span>";

    if (!hasIngredients) {
      appendPopular(list);
      renderStartCard(list);
      return;
    }

    if (!res.all.length) {
      renderEmpty(false);
      appendPopular(list);
      return;
    }

    var rows = res.all;
    var limit = state.showAllDishes ? rows.length : Math.min(8, rows.length);

    for (var i = 0; i < limit; i++) {
      list.appendChild(dishNode(rows[i], i, true));
    }

    if (rows.length > limit) {
      var more = document.createElement("button");
      more.type = "button";
      more.className = "ghost-btn";
      more.style.alignSelf = "center";
      more.style.marginTop = "4px";
      more.textContent = "요리 " + (rows.length - limit) + "개 더 보기";
      more.addEventListener("click", function () {
        state.showAllDishes = true;
        renderResults();
      });
      list.appendChild(more);
    }
  }

  var POPULAR_IDS = [
    "kimchi-fried-rice", "tuna-mayo", "ganjang-gyeran-bap",
    "tteokbokki", "gyeranmari", "kimchi-ramyeon",
  ];

  function appendPopular(list) {
    POPULAR_IDS.forEach(function (id, i) {
      var d = DISHES.filter(function (x) { return x.id === id; })[0];
      if (!d) return;
      list.appendChild(dishNode({
        dish: d,
        hit: [],
        missing: [],
        bonus: [],
        percent: 0,
        ready: false,
      }, i, false));
    });
  }

  function renderStartCard(list) {
    var box = document.createElement("div");
    box.className = "empty compact";
    box.innerHTML =
      '<h3>가진 재료만 골라도 돼요</h3>' +
      "<p>위에서 재료를 누르면<br>지금 바로 만들 수 있는 요리를 찾아드려요.</p>" +
      '<button type="button" class="quick-start" id="quickStart">자주 있는 재료로 시작하기</button>';
    list.appendChild(box);
    bindQuickStart(box);
  }

  function bindQuickStart(box) {
    var quick = $("#quickStart", box);
    if (!quick) return;
    quick.addEventListener("click", function () {
      state.selected = ["egg", "kimchi", "rice", "pa"];
      state.showAllDishes = false;
      renderChips();
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
      "<h3>이 재료로는 아직 레시피가 없어요</h3>" +
      "<p>재료를 한두 개 더 골라보세요.<br>아래는 오늘 인기 레시피예요.</p>";
    el.dishList.appendChild(box);
  }

  function dishNode(row, index, showMatch) {
    var d = row.dish;
    var card = document.createElement("button");
    card.type = "button";
    card.className = "dish" + (row.ready ? " is-ready" : "");
    card.style.animationDelay = Math.min(index * 0.035, 0.25) + "s";
    card.setAttribute("aria-label", d.name + " 레시피 보기");

    var levelText = d.level >= 2 ? "보통" : "쉬움";

    var html = "";
    html += '<div class="dish-top">';
    html += '<div class="dish-thumb">' + d.emoji + "</div>";
    html += '<div class="dish-main">';
    html += '<div class="dish-name">' + escapeHtml(d.name);
    if (row.ready) html += '<span class="ready-tag">바로 가능</span>';
    html += "</div>";
    html += '<div class="dish-meta"><span>⏱ ' + d.time + "분</span><i>·</i><span>난이도 " + levelText + "</span>";
    if (row.bonus.length) html += "<i>·</i><span>보너스 재료 " + row.bonus.length + "개</span>";
    html += "</div></div>";

    if (showMatch) {
      html += '<div class="match' + (row.ready ? " is-ready" : "") + '">';
      html += '<div class="match-num">' + row.percent + "<small>%</small></div>";
      html += '<div class="match-bar"><i style="width:' + row.percent + '%"></i></div>';
      html += "</div>";
    }
    html += "</div>";

    if (showMatch && d.req.length) {
      html += '<div class="ing-row">';
      d.req.forEach(function (id) {
        var has = row.hit.indexOf(id) !== -1;
        html += '<span class="ing' + (has ? "" : " miss") + '">' + ingLabel(id) + "</span>";
      });
      d.opt.forEach(function (id) {
        var has = state.selected.indexOf(id) !== -1;
        html += '<span class="ing opt' + (has ? " has" : "") + '">' + ingLabel(id) + "</span>";
      });
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
     8. 룰렛 모드
     ------------------------------------------------------------------ */
  function renderFilters() {
    el.moodSeg.innerHTML = "";
    el.budgetSeg.innerHTML = "";
    el.methodSeg.innerHTML = "";

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
        renderFilters();
        renderPoolHint();
        save();
      }));
    });
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
    return DISHES.filter(function (d) {
      if (state.method !== "all" && d.method !== state.method) return false;
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
      return;
    }
    el.poolLabel.textContent = pool.length + "개 메뉴 중에서 뽑아요";
    el.spinBtn.disabled = state.spinning;
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
      ? dish.time + "분 · 난이도 " + (dish.level >= 2 ? "보통" : "쉬움")
      : dish.price + " · 배달·외식";
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
    if (navigator.vibrate) { try { navigator.vibrate(24); } catch (e) {} }
  }

  function renderResult(dish) {
    el.result.classList.remove("hidden");
    el.result.innerHTML = "";

    var wrap = document.createElement("div");
    var meta = dish.method === "home"
      ? ["⏱ " + dish.time + "분", "난이도 " + (dish.level >= 2 ? "보통" : "쉬움"), "🏠 집에서"]
      : [dish.price, "🛵 배달·외식", moodLabel(dish.moods[0])];

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
     9. 공유
     ------------------------------------------------------------------ */
  function shareText(dish) {
    var lines = [];
    lines.push("오늘 메뉴는 " + dish.name + " 당첨! " + dish.emoji);
    if (dish.comment) lines.push(dish.comment);
    if (dish.method === "home") {
      lines.push("⏱ " + dish.time + "분 · 난이도 " + (dish.level >= 2 ? "보통" : "쉬움"));
    } else {
      lines.push(dish.price + " · 배달·외식");
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
     10. 레시피 드로어
     ------------------------------------------------------------------ */
  function openDrawer(dish) {
    state.drawerDish = dish;
    var has = function (id) { return state.selected.indexOf(id) !== -1; };

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
      html += '<div class="drawer-section"><h3>재료</h3><div class="check-row">';
      dish.req.forEach(function (id) {
        var ok = has(id);
        html += '<span class="check' + (ok ? "" : " no") + '">' + (ok ? "✓ " : "+ ") + ingLabel(id) + "</span>";
      });
      dish.opt.forEach(function (id) {
        var ok = has(id);
        html += '<span class="check' + (ok ? "" : " no") + '" style="opacity:' + (ok ? 1 : 0.62) + '">' + (ok ? "✓ " : "· ") + ingLabel(id) + " (선택)</span>";
      });
      html += "</div></div>";

      html += '<div class="drawer-section"><h3>만드는 법</h3><ol class="steps">';
      dish.steps.forEach(function (s, i) {
        html += "<li><b>" + (i + 1) + "</b><span>" + escapeHtml(s) + "</span></li>";
      });
      html += "</ol></div>";
    } else {
      html += '<div class="drawer-section"><h3>메뉴 정보</h3><div class="check-row">';
      html += '<span class="check">' + escapeHtml(dish.price) + "</span>";
      html += '<span class="check">🛵 배달·외식</span>';
      dish.moods.forEach(function (m) {
        html += '<span class="check" style="background:#fdf2e7;color:#b5652f">' + moodLabel(m) + "</span>";
      });
      html += "</div></div>";
    }

    if (dish.tip) {
      html += '<div class="tip-box"><b>💡 팁</b> ' + escapeHtml(dish.tip) + "</div>";
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
      return "⏱ " + dish.time + "분 · 난이도 " + (dish.level >= 2 ? "보통" : "쉬움");
    }
    return dish.price + " · 배달·외식";
  }

  function closeDrawer() {
    el.drawer.hidden = true;
    document.body.style.overflow = "";
    state.drawerDish = null;
  }

  /* ------------------------------------------------------------------
     11. 탭 전환 / 토스트
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
     12. 초기화
     ------------------------------------------------------------------ */
  function init() {
    el.chipList = $("#chipList");
    el.moreChipsBtn = $("#moreChipsBtn");
    el.customForm = $("#customForm");
    el.customInput = $("#customInput");
    el.selSummary = $("#selSummary");
    el.resultHead = $("#resultHead");
    el.dishList = $("#dishList");
    el.viewFridge = $("#view-fridge");
    el.viewRoulette = $("#view-roulette");
    el.moodSeg = $("#moodSeg");
    el.budgetSeg = $("#budgetSeg");
    el.methodSeg = $("#methodSeg");
    el.poolLabel = $("#poolLabel");
    el.reel = $("#reel");
    el.reelEmoji = $("#reelEmoji");
    el.reelName = $("#reelName");
    el.reelSub = $("#reelSub");
    el.spinBtn = $("#spinBtn");
    el.result = $("#rouletteResult");
    el.drawer = $("#drawer");
    el.drawerPanel = $("#drawerPanel");
    el.toast = $("#toast");
    el.tabs = Array.prototype.slice.call(document.querySelectorAll(".tab"));

    load();

    el.moreChipsBtn.addEventListener("click", function () {
      state.expandedChips = !state.expandedChips;
      renderChips();
    });

    el.customForm.addEventListener("submit", function (event) {
      event.preventDefault();
      var raw = el.customInput.value.trim();
      if (!raw) return;

      var found = findByLabel(raw);
      if (found) {
        if (state.selected.indexOf(found.id) === -1) {
          state.selected.push(found.id);
          toast("'" + found.label + "' 재료를 골랐어요");
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
      state.showAllDishes = false;
      renderChips();
      renderSummary();
      renderResults();
      save();
    });

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

    // 초기 렌더
    renderChips();
    renderSummary();
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
