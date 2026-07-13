import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared.catalog.local_products import (
    LOCAL_PRODUCTS,
    CATEGORY_PRICE_RANGES,
    find_local_product_by_slug,
    find_local_product_by_bengali_text,
    category_keywords,
)

_VALID_CATEGORIES = {"textile", "food", "handicraft", "agriculture", "other"}


def test_every_product_has_a_valid_category():
    for product in LOCAL_PRODUCTS:
        assert product["category"] in _VALID_CATEGORIES, product["slug"]


def test_every_product_has_a_sane_price_range():
    for product in LOCAL_PRODUCTS:
        assert product["price_min"] > 0, product["slug"]
        assert product["price_max"] >= product["price_min"], product["slug"]


def test_every_product_has_at_least_one_bengali_keyword():
    for product in LOCAL_PRODUCTS:
        assert len(product["keywords"]) >= 1, product["slug"]
        assert all(kw.strip() for kw in product["keywords"]), product["slug"]


def test_no_duplicate_slugs():
    slugs = [p["slug"] for p in LOCAL_PRODUCTS]
    assert len(slugs) == len(set(slugs))


def test_category_price_ranges_cover_every_category_used_by_products():
    categories_in_use = {p["category"] for p in LOCAL_PRODUCTS}
    assert categories_in_use.issubset(CATEGORY_PRICE_RANGES.keys())


def test_find_local_product_by_slug_matches_known_product():
    match = find_local_product_by_slug("kantha saree")
    assert match is not None
    assert match["slug"].startswith("kantha")


def test_find_local_product_by_slug_matches_partial_word():
    match = find_local_product_by_slug("a nice kantha piece")
    assert match is not None


def test_find_local_product_by_slug_returns_none_for_unrelated_text():
    assert find_local_product_by_slug("smartphone charger cable") is None


def test_find_local_product_by_slug_returns_none_for_empty_string():
    assert find_local_product_by_slug("") is None
    assert find_local_product_by_slug(None) is None


def test_find_local_product_by_bengali_text_matches():
    match = find_local_product_by_bengali_text("আজ ১৫ প্যাকেট পাপড় বিক্রি করেছি")
    assert match is not None
    assert match["slug"] == "papad"


def test_find_local_product_by_bengali_text_returns_none_when_no_match():
    assert find_local_product_by_bengali_text("আজ অফিসে গিয়েছিলাম") is None


def test_category_keywords_groups_by_category():
    grouped = category_keywords()
    assert "food" in grouped
    assert "পাপড়" in grouped["food"]
    assert "textile" in grouped
    assert "কাঁথা" in grouped["textile"]
