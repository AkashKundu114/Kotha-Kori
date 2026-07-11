# Files to delete — run from repo root

## A. Confirmed dead — safe to remove now

```bash
git rm -r services/stt/
git rm infrastructure/terraform/__init__.py infrastructure/docker/__init__.py
git rm -r infrastructure/k8s/
git rm shared/redis/__init__.py
git rm services/gateway/middleware/__init__.py
git rm services/voice_gateway/providers/openai_stt_provider.py
git commit -m "cleanup: remove dead stt service, unused infra/package stubs, OpenAI STT provider"
```

| Path | Why |
|---|---|
| `services/stt/` (whole dir) | Pre-cascade standalone Whisper service. Superseded by `voice_gateway/provider_cascade.py`. Not in `docker-compose.yml`. |
| `infrastructure/terraform/__init__.py`, `infrastructure/docker/__init__.py` | Meaningless `__init__.py` in non-Python directories — scaffold leftovers. |
| `infrastructure/k8s/` | Contradicts your own documented single-VM Docker Compose pilot strategy (`scope.md` §4, `pilot-plan.md` non-goals). |
| `shared/redis/__init__.py` | Nothing imports `shared.redis` — `gateway/main.py` uses `redis.asyncio` directly. |
| `services/gateway/middleware/__init__.py` | No middleware files exist under it. |
| `services/voice_gateway/providers/openai_stt_provider.py` | Replaced by `saaras_provider.py` — this update removes OpenAI usage entirely, so this file is now dead code, not just unused. |

## B. Now also dead, as a direct result of this update

```bash
git rm services/voice_gateway/providers/openai_stt_provider.py   # (listed above, included for completeness)
```

Nothing else references OpenAI directly anymore. `model_router.py`'s
`_call_openai*` functions have been removed in the rewritten file, not just
unused — check your diff against the version in this package to confirm no
other file still imports the old `openai` symbols before deleting the
package pin from `requirements.txt`.

## C. Judgment calls — decide before deleting, don't blind-delete

| Path | Status |
|---|---|
| `migrations/0003_v3_features.sql` | Fully redundant with `0001_init.sql`, but **confirm no live deployed DB depends on it as its only migration path** before removing. |
| `services/rag_service/`, `nodes/scheme_rag_node.py`, `tests/unit/test_grounding_verifier.py`, `migrations/0002_hybrid_search.sql`, `whatsapp_flows/scheme_eligibility_flow.json`, `scripts/seed_schemes.py`, `scripts/audit_rag.py`, `data/schemes/raw/` | Deliberately kept per `scope.md` (portfolio artifact, Feature 2 not in V3 routing). **Known bug**: `0002_hybrid_search.sql` alters `scheme_chunks`, which is never `CREATE TABLE`'d in current migrations — this code is currently undeployable, not just unrouted. Fix the missing DDL or document the gap explicitly if keeping this. |
| `ml/` (entire directory) | Post-pilot fine-tuning roadmap, not wired into the current Sarvam-only production path. Recommend moving to `docs/archive/` rather than deleting — real reusable work for a future self-hosted migration. |

## Do NOT delete

- `services/vision_service/poster_composer.py`, `rembg_processor.py` — these are the free fallback tier for poster generation and vision preprocessing; Flux Pro is an *optional upgrade* over these, never a replacement.
- `services/voice_gateway/providers/whisper_local_provider.py` — the free STT fallback, unchanged by this update.
- `docs/archive/` — already well-organized per `docs/README.md`'s stated purpose.
- `demo_scripts/` — small, purposeful, referenced by its own README.
