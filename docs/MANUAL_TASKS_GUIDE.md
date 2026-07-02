# Manual Tasks Guide — Nothing Here Can Be Delegated to an AI Tool

Everything in this list requires a human with account access, a phone number,
a bank/payment method, or judgment that isn't yours to automate away. UI
steps for third-party platforms (Meta, AWS, etc.) change over time — treat
the *sequence and purpose* below as reliable, but click through the actual
current screens yourself rather than trusting exact button names to still
match.

---

## Tier 0 — Before you can run anything locally

### 1. Anthropic API key
1. Go to `console.anthropic.com`, create an account (or use your existing one).
2. Add a payment method under Billing — the free/trial credit will not
   survive real pilot traffic once Feature 1's confirmation loop and Feature
   8's phrasing calls are both live.
3. Create an API key under **API Keys**. Put it in `.env` as
   `ANTHROPIC_API_KEY`. **Never commit this file** — double check
   `.gitignore` actually excludes `.env` before your first `git add .`.
4. Set a spend alert/budget cap in the console if the option exists at the
   time you look — this is your single biggest cost-exhaustion exposure
   (see `SECURITY_AUDIT_V3.md` H2 — the code-side rate limiter helps, but a
   platform-side hard cap is a second independent safety net).

### 2. A GPU box for Ollama + Whisper fallback (Sarvam/Bhashini are cloud APIs, no GPU needed for those two)
1. Pick a provider — RunPod, Lambda Labs, or Vast.ai are all reasonable for
   a pilot; pricing and instance availability shift often enough that I
   won't tell you which is cheapest right now — compare current per-hour
   rates yourself at signup time.
2. Create an account, add payment, spin up an RTX 4090-class (24GB VRAM)
   instance. You need this only for the local-first tiers (`ollama`,
   `whisper-local` fallback in the voice cascade) — Sarvam/Bhashini/Claude
   calls don't touch this box at all.
3. Note the instance's public IP/SSH endpoint — you'll point
   `OLLAMA_BASE_URL` at it (or run it in the same docker-compose stack on
   that box, which is simpler for a pilot — see `docker-compose.yml`).
4. `ssh` in, install `nvidia-smi`-visible drivers if not preinstalled,
   confirm `docker compose up ollama` can see the GPU (`nvidia-smi` inside
   the container should list it).

### 3. Postgres with pgvector (and TimescaleDB if you want the real hypertable — see `migrations/0003_v3_features.sql`)
- Easiest: run it inside `docker-compose.yml` on the same GPU box (already
  configured as `pgvector/pgvector:pg16`) — fine for pilot scale.
- If you want managed Postgres instead (less ops burden, costs more):
  Supabase supports pgvector out of the box; check current TimescaleDB
  extension availability on whichever managed provider you pick before
  assuming Feature 8's hypertable will work unmodified — the migration
  already has a fallback path if it's not available.

---

## Tier 1 — Before the bot can send/receive a single WhatsApp message

### 4. Meta Developer account + WhatsApp Business App
1. Go to `developers.facebook.com`, log in with a Facebook account (create
   one dedicated to the business if you don't want to use a personal
   account — recommended, since you'll be granting it business permissions).
2. Create a new App, type "Business."
3. Add the **WhatsApp** product to the app.
4. Meta will provision a **test phone number** automatically — use this for
   all of Week 1's development and the Day-3 trace exercise in
   `INTERNSHIP_GUIDE.md`. It only works for numbers you manually
   allow-list (up to 5) until you go through business verification.
5. Under WhatsApp > API Setup, note: the **temporary access token** (expires
   in 24h — fine for local dev, useless for production), the
   **Phone Number ID**, and the **WhatsApp Business Account ID**.

### 5. Business verification (required before a real, non-test phone number and before scaling past 5 allow-listed test numbers)
1. Under Meta Business Settings, submit business verification: legal
   business name, address, and a document (business PAN/GST/registration
   certificate — if this project doesn't have a formal registered entity
   yet, look into whether your NGO partner can sponsor the WABA, or whether
   you need to register one — this is a genuine judgment call to make with
   your mentor, not something to guess at).
2. This review has historically taken 1-4 weeks and its exact requirements
   change — start it in parallel with Week 1 coding, don't block on it, but
   don't assume a 2-week timeline for verification itself.
3. Once verified, add a **permanent (System User) access token** instead of
   the 24h temporary one — Meta Business Settings > System Users > generate
   token with `whatsapp_business_messaging` + `whatsapp_business_management`
   permissions. Put this in `.env` as `WA_ACCESS_TOKEN`.

### 6. Webhook configuration
1. You need a **public HTTPS URL** pointing at `services/gateway`'s
   `/webhook/whatsapp` endpoint. For local dev: `ngrok http 8000` gives you
   a temporary HTTPS tunnel. For the actual pilot: deploy the gateway on
   your GPU box or a small separate VM behind a real domain + TLS
   certificate (Caddy or nginx + Let's Encrypt both auto-provision certs
   with minimal config).
2. In Meta's App Dashboard > WhatsApp > Configuration, set the Webhook URL
   to `https://<your-domain>/webhook/whatsapp` and the Verify Token to
   whatever you set as `WA_WEBHOOK_VERIFY_TOKEN` in `.env` — these must
   match exactly, that's what `verify_webhook()` in `gateway/main.py` checks.
3. Subscribe the webhook to the `messages` field.
4. **Security step from `SECURITY_AUDIT_V3.md` H12**: once you're off the
   test tunnel, restrict inbound traffic on port 443/8000 at your cloud
   provider's firewall/security-group level to Meta's published webhook IP
   ranges — search "WhatsApp Cloud API webhook IP ranges" for the current
   list, Meta updates this occasionally.

---

## Tier 2 — Feature-specific manual setup

### 7. Sarvam AI (primary STT tier)
1. Sign up at `sarvam.ai`, get an API key from their developer dashboard.
2. Note their current free-tier limits and pricing before assuming it's
   free at pilot volume — set `SARVAM_MONTHLY_BUDGET_INR` in `.env` to
   whatever cap makes sense once you've checked current pricing.

### 8. Bhashini (free fallback STT tier)
1. Register at `bhashini.gov.in` / the ULCA developer portal
   (`dhruva-api.bhashini.gov.in` is the API host referenced in the code).
2. This is a government registration process — historically slower than a
   typical SaaS signup (days, not minutes). Start this in Week 1 even
   though it's your fallback tier, not your primary one, so it's ready
   before you need it.

### 9. data.gov.in API key (Feature 8's Agmarknet price signal — optional)
1. Register at `data.gov.in`, request an API key.
2. This is explicitly optional — `agmarknet_client.py` returns `[]`
   gracefully if `DATA_GOV_IN_API_KEY` is unset, and the market predictor
   still works off ledger-derived signals alone. Don't block Feature 8's
   launch on this.
3. **You must verify the exact resource ID and response schema yourself**
   against the live API before trusting the client's parsing — flagged
   explicitly in `agmarknet_client.py`'s docstring, this is not something I
   could confirm without live access to that API.

### 10. AWS account + S3 bucket (or equivalent object storage)
1. Create an AWS account, an IAM user (not root credentials) scoped to
   only `s3:PutObject`/`s3:GetObject` on your specific bucket — least
   privilege, per `SECURITY_AUDIT_V3.md`'s general posture.
2. Create the S3 bucket (`s3_bucket` in settings), enable default
   encryption (SSE-S3/AES256 — the code already sets this per-object, but
   bucket-level default is a good second layer).
3. Put the IAM access key/secret in `.env`
   (`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` — standard boto3 env vars,
   not currently in `shared/config/settings.py` since boto3 reads them
   directly from the environment; just make sure they're in `.env` and
   loaded).

---

## Tier 3 — Before you enroll a single real pilot user

### 11. NGO partnership
This is a relationship, not an account — reach out to your existing
network/mentor's contacts for an SHG-facing NGO in your target district.
No AI tool does this step for you; budget real calendar time for it, and
don't assume it closes inside the 2-week engineering sprint.

### 12. Consent materials, reviewed by a human who knows DPDP Act 2023
Draft Bengali consent copy (product consent + separate video-interview
consent per `USER_MODEL_AND_RESEARCH.md`) and have it reviewed — ideally by
someone with actual legal familiarity with DPDP, not just an AI-drafted
approximation. This matters more than most engineering tasks here: it's the
thing standing between the project and a real compliance problem.

### 13. A dedicated pilot WhatsApp number + physical SIM
Once past business verification, you'll add a real (not test) phone number
to the WABA. That number needs a working SIM during the initial Meta OTP
verification step — plan for someone to have that phone physically in hand.

### 14. Field visit logistics
Travel, a translator if you're not fluent in the relevant dialect yourself,
a recording device + release forms for the video interviews, and time —
none of this is code. Block calendar time for this explicitly in your
2-week plan rather than treating it as something that happens automatically
alongside the engineering work.

---

## Tier 4 — Ongoing manual ops during the pilot (not one-time)

- **Daily**: check the Langfuse dashboard for grounding-verifier /
  hallucination-rate spikes (if you re-enable Feature 2) and general error
  rate — this is manual per `SECURITY_AUDIT_V3.md` H10's judgment call for
  pilot scale.
- **Weekly**: run `scripts/eval_stt.py` against your labeled sample set once
  you have one; review a sample of Feature 3 captions and Feature 8 reports
  for quality drift.
- **Ad hoc**: rotate any API key you suspect may have leaked (e.g., if a
  `.env` file was ever accidentally committed — check `git log` for it
  explicitly, don't assume).

---

## What I'd genuinely prioritize first if I were you this week

1. Anthropic key + GPU box (Tier 0) — unblocks all local development today.
2. Meta Developer account + test number (Tier 1, steps 4 and 6 via ngrok) —
   unblocks the Day-3 trace exercise and real end-to-end testing.
3. Business verification (Tier 1, step 5) and Bhashini registration (Tier 2,
   step 8) — **start these in parallel immediately**, both have unpredictable
   external review timelines and are the two most likely things to quietly
   blow your 2-week deadline if started late.
4. NGO conversation (Tier 3, step 11) — also start this week; it's a
   relationship with its own timeline you don't control.

Everything else in Tiers 2-4 can genuinely wait until the code needs it.
