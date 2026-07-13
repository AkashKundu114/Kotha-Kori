from __future__ import annotations

"""Single source of truth for common West Bengal SHG micro-business
products — drawn directly from the personas and trade list already
documented in docs/product.md (§3.1 Sunita's businesses) and
docs/archive/engineering/llm-guide.md's training-track list, so this isn't
a generic/invented catalog but matches what this product's actual target
users make and sell.

Used by:
  - services/vision_service/vision_router.py — a specific product match
    gives a tighter price-range default than the broad 5-bucket category
    fallback that used to be the only option.
  - services/orchestrator/nodes/catalog_node.py — category_keywords()
    replaces the previously hand-maintained, sparse _CATEGORY_KEYWORDS
    dict with one generated from this list.

`category` values are constrained to the same set already used elsewhere
in the codebase (textile/food/handicraft/agriculture/other) so nothing
downstream (market_service aggregation category matching, etc.) needs to
change to understand a new value.
"""

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

# Fast lookup: normalized english slug/alias -> product dict. Built once at
# import time rather than scanning the list on every lookup.
_SLUG_INDEX: dict[str, dict] = {p["slug"].lower(): p for p in LOCAL_PRODUCTS}


def find_local_product_by_slug(text_en: str) -> dict | None:
    """Matches a vision model's English product_type output (e.g. Sarvam
    Vision / local Ollama vision returning 'kantha saree') against the
    local catalog for a tighter price-range default than the broad
    category fallback. Conservative substring match — returns None (never
    a fabricated guess) if nothing matches, same fail-safe pattern as every
    other lookup helper in this codebase (see grounding_verifier.py's
    _nearby_scheme, market_service's aggregator)."""
    if not text_en:
        return None
    normalized = text_en.lower().strip()
    for slug, product in _SLUG_INDEX.items():
        if slug in normalized or normalized in slug:
            return product
    # Loosen slightly: check individual slug words against the input, so
    # "kantha" alone (not the full "kantha embroidery / kantha saree")
    # still matches.
    for slug, product in _SLUG_INDEX.items():
        for word in slug.replace("/", " ").split():
            if len(word) >= 4 and word in normalized:
                return product
    return None


def find_local_product_by_bengali_text(text_bn: str) -> dict | None:
    """Matches free Bengali text (ledger categories, captions, voice
    transcripts) against the local catalog's Bengali keywords."""
    if not text_bn:
        return None
    for product in LOCAL_PRODUCTS:
        if any(kw in text_bn for kw in product["keywords"]):
            return product
    return None


def category_keywords() -> dict[str, list[str]]:
    """Builds the category -> Bengali-keyword-list mapping
    catalog_node.py's market-trend note matching uses, generated from this
    single source of truth instead of a separately hand-maintained dict
    that can drift out of sync with the actual product list."""
    out: dict[str, list[str]] = {}
    for product in LOCAL_PRODUCTS:
        out.setdefault(product["category"], []).extend(product["keywords"])
    return out
