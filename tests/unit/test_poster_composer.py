import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from services.vision_service.poster_composer import _truncate, compose_poster
from services.vision_service import poster_composer


def test_truncate_short_text_unchanged():
    assert _truncate("hello", 10) == "hello"


def test_truncate_long_text_gets_ellipsis():
    result = _truncate("a" * 50, 10)
    assert len(result) == 10
    assert result.endswith("…")


def test_truncate_strips_newlines():
    assert "\n" not in _truncate("line one\nline two", 50)


class _FakeSettings:
    bengali_font_path = "/definitely/does/not/exist.ttf"


def test_compose_poster_returns_none_without_font(monkeypatch):
    """Missing font asset must degrade gracefully (None), never raise —
    catalog_node falls back to plain photo delivery in that case."""
    monkeypatch.setattr(poster_composer, "get_settings", lambda: _FakeSettings())
    result = compose_poster(
        b"not-a-real-image", product_name="test", ad_caption="test", price_min=1, price_max=2
    )
    assert result is None
