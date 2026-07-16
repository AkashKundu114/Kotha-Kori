# Kotha-Khata — Field Work Cost Brief
**Scope:** 2 field sessions, 1 SHG group each (10–15 members/group) | **Prepared for:** Mentor review | **Date:** July 2026

---

## 1. Purpose

Two in-person field visits to pilot Kotha-Khata with real SHG members (per `docs/fieldwork.md`), covering onboarding, live use of Voice-Ledger / Catalog Creator / Pricing, and short structured interviews. Total participants: ~20–30 women across both sessions, within the project's target recruitment range.

## 2. Cost Breakdown

| Item | Detail | Cost (₹) |
|---|---|---|
| **Domain registration** | `.in` domain, 1 year (e.g. `kotha-khata.in`) - needed for the Meta webhook to sit behind a real TLS domain instead of a temporary ngrok tunnel during field use | ₹799 |
| **API & field usage cost** | Sarvam AI (all 4 models) + Flux Pro + on-ground field materials for both sessions combined | ₹670 |
| **Object storage (S3-compatible)** | Ledger PDFs + catalog images, ~2 weeks of active usage around the two visits | ₹150 |
| **Contingency buffer** | Covers minor overage on any single item above | ₹200 |
| **Total** | | **₹1,819** |

Remaining headroom to the ₹2,000 cap: **₹181**.

## 3. What's Deliberately Excluded (₹0 cost, already covered)

- **WhatsApp Cloud API test number** - Meta provisions this free for up to 5 allow-listed numbers; sufficient for a 10–15 person pilot per group, no business verification needed.
- **GPU box / self-hosted Ollama fallback** - not required at this scale; Sarvam's cloud tier alone comfortably covers pilot volume.
- **NGO partnership, translator, researcher time** - relationship/labor cost, not a line item here.
- **Flux Pro at full scale** - only a small subset (~10 posters) is priced in; the free local Pillow poster tier remains the default for everything else, so this line can be dropped to ₹0 entirely if the budget needs more headroom.

## 4. Notes for Mentor

- The four Sarvam models (Saaras V3, Sarvam-30B, Sarvam-105B, Sarvam Vision) are each billed independently on Sarvam's dashboard, so actual per-model spend will be visible in real time; a spend cap can be set per-key so we don't overrun silently.
- Flux Pro is the one truly optional line - dropping it saves ₹80 with no functional loss (posters just render via the free Pillow tier instead).
- Domain cost is a **one-time annual** cost, not per-field-visit - it carries forward to any future pilot sessions at no extra charge.
- If a third field session is added later, only the API/field-materials line would scale up; domain and storage costs are already fixed for the year.
