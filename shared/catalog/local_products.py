from __future__ import annotations

CATEGORY_PRICE_RANGES: dict[str, tuple[float, float]] = {
    "textile": (500, 1500),
    "food": (50, 400),
    "handicraft": (150, 800),
    "agriculture": (30, 300),
    "other": (100, 600),
}

LOCAL_PRODUCTS: list[dict] = [
    {
        "slug": "papad",
        "name_bengali": "পাপড়",
        "category": "food",
        "price_min": 80,
        "price_max": 250,
        "keywords": ["পাপড়"],
    },
    {
        "slug": "pickle",
        "name_bengali": "আচার",
        "category": "food",
        "price_min": 100,
        "price_max": 400,
        "keywords": ["আচার"],
    },
    {
        "slug": "kantha embroidery / kantha saree",
        "name_bengali": "কাঁথা / কাঁথা স্টিচ শাড়ি",
        "category": "textile",
        "price_min": 500,
        "price_max": 2000,
        "keywords": ["কাঁথা"],
    },
    {
        "slug": "poultry / eggs",
        "name_bengali": "হাঁস-মুরগি ও ডিম",
        "category": "agriculture",
        "price_min": 150,
        "price_max": 600,
        "keywords": ["মুরগি", "হাঁস", "ডিম"],
    },
    {
        "slug": "vegetables",
        "name_bengali": "তাজা সবজি",
        "category": "agriculture",
        "price_min": 20,
        "price_max": 100,
        "keywords": ["সবজি", "শাকসবজি"],
    },
    {
        "slug": "jute handicraft",
        "name_bengali": "পাটের সামগ্রী",
        "category": "handicraft",
        "price_min": 100,
        "price_max": 500,
        "keywords": ["পাট", "পাটের ব্যাগ"],
    },
    {
        "slug": "terracotta craft",
        "name_bengali": "টেরাকোটা শিল্প",
        "category": "handicraft",
        "price_min": 150,
        "price_max": 800,
        "keywords": ["টেরাকোটা"],
    },
    {
        "slug": "mushroom",
        "name_bengali": "মাশরুম",
        "category": "food",
        "price_min": 150,
        "price_max": 400,
        "keywords": ["মাশরুম"],
    },
    {
        "slug": "honey",
        "name_bengali": "মধু",
        "category": "food",
        "price_min": 200,
        "price_max": 600,
        "keywords": ["মধু"],
    },
    {
        "slug": "mustard oil",
        "name_bengali": "সরিষার তেল",
        "category": "food",
        "price_min": 150,
        "price_max": 350,
        "keywords": ["সরিষার তেল", "সর্ষের তেল"],
    },
    {
        "slug": "muri / puffed rice",
        "name_bengali": "মুড়ি",
        "category": "food",
        "price_min": 40,
        "price_max": 100,
        "keywords": ["মুড়ি"],
    },
    {
        "slug": "batik / natural dye textile",
        "name_bengali": "বাটিক ও প্রাকৃতিক রঙের কাপড়",
        "category": "textile",
        "price_min": 300,
        "price_max": 1200,
        "keywords": ["বাটিক"],
    },
    {
        "slug": "tailoring",
        "name_bengali": "দর্জির কাজ / সেলাই",
        "category": "textile",
        "price_min": 150,
        "price_max": 800,
        "keywords": ["সেলাই", "দর্জি"],
    },
    {
        "slug": "candle and soap making",
        "name_bengali": "মোমবাতি ও সাবান",
        "category": "handicraft",
        "price_min": 50,
        "price_max": 250,
        "keywords": ["মোমবাতি", "সাবান"],
    },
]

_SLUG_INDEX: dict[str, dict] = {p["slug"].lower(): p for p in LOCAL_PRODUCTS}


def find_local_product_by_slug(text_en: str) -> dict | None:
    if not text_en:
        return None
    normalized = text_en.lower().strip()
    for slug, product in _SLUG_INDEX.items():
        if slug in normalized or normalized in slug:
            return product
    for slug, product in _SLUG_INDEX.items():
        for word in slug.replace("/", " ").split():
            if len(word) >= 4 and word in normalized:
                return product
    return None


def find_local_product_by_bengali_text(text_bn: str) -> dict | None:
    if not text_bn:
        return None
    for product in LOCAL_PRODUCTS:
        if any(kw in text_bn for kw in product["keywords"]):
            return product
    return None


def category_keywords() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for product in LOCAL_PRODUCTS:
        out.setdefault(product["category"], []).extend(product["keywords"])
    return out
