# Setup — Official WhatsApp Cloud API only

This assumes you already have (or are getting) a Meta Developer account.
Nothing here uses a third-party messaging provider.

## 1. Meta Developer account + WhatsApp app

1. Go to `developers.facebook.com`, create a Business-type app.
2. Add the **WhatsApp** product to it.
3. Meta auto-provisions a **test phone number** — good enough for tonight's
   testing (works for up to 5 manually allow-listed recipient numbers,
   no business verification needed yet).
4. Under WhatsApp → API Setup, copy:
   - **Phone Number ID** → `WA_PHONE_NUMBER_ID`
   - **Temporary access token** → `WA_ACCESS_TOKEN` (expires in 24h — fine for
     testing; once verified, generate a permanent System User token instead)
5. App Dashboard → Settings → Basic → **App Secret** → `WA_APP_SECRET`
   (this is *not* the same value as the verify token below — mixing these
   two up silently breaks or forges webhook verification).
6. Pick any random string yourself for `WA_WEBHOOK_VERIFY_TOKEN` — you'll
   enter this exact value into Meta's webhook config screen in step 3 below.

## 2. Sarvam AI — required, sole AI vendor

There is no OpenAI dependency anywhere in this codebase. Sarvam is required,
not optional:

1. `sarvam.ai` → sign up → API Keys → create one → `SARVAM_API_KEY`.
2. You get free ₹100 credit on signup; check the current pricing page before
   picking a paid plan tier.
3. Set a spend/budget cap in the Sarvam dashboard — the app-level rate
   limiting (30 msgs/hour/user) is one safety net, a platform-side hard cap
   is a second, independent one. With no other paid vendor in this system,
   this cap is your only spend ceiling.
4. That's it for the cloud tier — no model download needed. See
   `docs/COST.md` for exactly which agent uses `sarvam-30b` vs
   `sarvam-105b` vs `sarvam-vision` vs `saaras:v3`, and why.

**Strongly recommended — set up the free local fallback too.** With OpenAI
removed, self-hosted Ollama is the *only* thing that keeps every agent alive
if Sarvam is briefly down or rate-limited:
```bash
docker compose --profile local-models up -d ollama
docker compose exec ollama ollama pull qwen2.5:7b-instruct-q4_K_M
docker compose exec ollama ollama pull qwen2-vl:7b-q4_K_M
```
Then set `USE_LOCAL_MODELS=true` in `.env`.

**If you're also self-hosting a Q4-quantized `sarvam-translate` box** (your
own GPU, via vLLM) as an additional free fallback tier specifically for
translation:
```bash
vllm serve sarvamai/sarvam-translate --port 8000
```
then set `SARVAM_LOCAL_BASE_URL=http://<that-host>:8000/v1` in `.env`. This
is genuinely optional — the cloud tier plus generic Ollama fallback is
enough to run the bot.

## 3. Expose the webhook and configure it in Meta

Local testing: `ngrok http 8000`, copy the HTTPS URL it gives you.

In Meta App Dashboard → WhatsApp → Configuration:
- **Callback URL**: `https://<your-ngrok-or-real-domain>/webhook/whatsapp`
- **Verify token**: exactly what you put in `WA_WEBHOOK_VERIFY_TOKEN`
- Subscribe to the `messages` field.

## 4. Flux Pro (optional — poster generation upgrade)

Skip this entirely if you want — posters are generated locally via Pillow
(`services/vision_service/poster_composer.py`) at zero cost regardless.
Only set this up if you want higher-fidelity generated posters:

1. Get an API key from your Flux Pro provider → `FLUX_API_KEY`.
2. Set a spend cap — per-image pricing scales with catalog usage.

## 5. Bengali font for ad posters (optional, but worth doing)

Download `NotoSansBengali-Bold.ttf` from
`fonts.google.com/noto/specimen/Noto+Sans+Bengali` and place it at
`assets/fonts/NotoSansBengali-Bold.ttf`. Without it, Catalog Creator still
works — it just sends the photo and captions as separate messages instead of
a single composited poster.

## 6. Storage (S3-compatible)

Any S3-compatible bucket works (DigitalOcean Spaces is the default in
`.env.example`). Create a bucket, an access key scoped to just that bucket,
enable default encryption, and fill in `S3_BUCKET` / `AWS_ACCESS_KEY_ID` /
`AWS_SECRET_ACCESS_KEY` / `S3_ENDPOINT_URL`.

## 7. Run it

```bash
make setup
# fill in .env
make check-env     # tells you exactly what's still missing, if anything —
                    # including a hard warning if BOTH Sarvam and local
                    # Ollama are unconfigured, since that means every
                    # agent will fail immediately
make dev
```

Send a WhatsApp message from one of your allow-listed test numbers to the
test number Meta gave you — you should get a Bengali onboarding reply within
a few seconds.

## 8. Before real (non-test) users

- Submit **Business Verification** in Meta Business Settings (legal name +
  address + a business document). This step has historically taken 1–4 weeks
  and its exact requirements change — start it as early as possible, it does
  not block anything in steps 1–6 above.
- Swap the temporary access token for a permanent System User token.
- Set `DEBUG=false` (already the default) and put this behind a real TLS
  domain via the included `Caddyfile` instead of ngrok.
- Confirm `USE_LOCAL_MODELS=true` and Ollama is actually healthy — this is
  no longer a "nice to have," it's your only fallback if Sarvam has an
  outage during real pilot traffic.

## About WhatsApp Flows

Flows (native tap-to-select forms) require the same Meta Business
verification as above — there's no way to use Flows without it, regardless
of hosting. This build's onboarding uses a plain numbered-text sequence
instead, which works identically on a test number or a verified one.
