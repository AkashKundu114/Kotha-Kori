# Demo run order

Copy `demo_scripts/` into the repo root, next to `services/`. Run everything
from the repo root.

## Setup

```bash
pip install pytest pytest-asyncio rembg onnxruntime Pillow --break-system-packages
```

## Steps

1. `pytest tests/unit/test_grounding_verifier.py -v`
2. `python demo_scripts/demo_01_grounding_verifier.py`
3. `python demo_scripts/demo_02_market_trend.py`
4. `python demo_scripts/demo_03_catalog_image.py path/to/photo.jpg`
5. `bash demo_scripts/demo_05_infra_healthcheck.sh` (needs Docker)
6. `python demo_scripts/demo_04_llm_wall.py` - fails without an OpenAI key;
   this is the ask.
