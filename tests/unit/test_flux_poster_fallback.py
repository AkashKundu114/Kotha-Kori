import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest

from services.vision_service import poster_composer


class _FakeSettingsNoFlux:
    bengali_font_path = "/definitely/does/not/exist.ttf"
    flux_api_key = ""


class _FakeSettingsWithFluxKeyButBadUrl:
    bengali_font_path = "/definitely/does/not/exist.ttf"
    flux_api_key = "test-key"
    flux_base_url = "http://127.0.0.1:1"


@pytest.mark.asyncio
async def test_generate_poster_falls_back_to_pillow_tier_without_flux_key(monkeypatch):
    monkeypatch.setattr(poster_composer, "get_settings", lambda: _FakeSettingsNoFlux())
    image_bytes, tier = await poster_composer.generate_poster(
        b"not-a-real-image", product_name="test", ad_caption="test", price_min=1, price_max=2
    )
    assert tier == "pillow"
    assert image_bytes is None


@pytest.mark.asyncio
async def test_generate_poster_falls_back_to_pillow_tier_on_flux_failure(monkeypatch):
    monkeypatch.setattr(poster_composer, "get_settings", lambda: _FakeSettingsWithFluxKeyButBadUrl())

    async def _fake_flux_get_settings():
        return _FakeSettingsWithFluxKeyButBadUrl()




    import services.vision_service.flux_poster_client as flux_client
    monkeypatch.setattr(flux_client, "get_settings", lambda: _FakeSettingsWithFluxKeyButBadUrl())

    image_bytes, tier = await poster_composer.generate_poster(
        b"not-a-real-image", product_name="test", ad_caption="test", price_min=1, price_max=2
    )
    assert tier == "pillow"
    assert image_bytes is None
