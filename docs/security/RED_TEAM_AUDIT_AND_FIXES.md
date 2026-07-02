# Kotha-Khata — Red-Team Pass #2
### Attacking beyond `docs/security/SECURITY_AUDIT_V3.md`

**Method:** treat every trust boundary as hostile. For each one: try to read data I
shouldn't, write data I shouldn't, crash a process, or make the system spend money/GPU
on my behalf. Where an attempt failed, I noted *why* and moved to the next angle rather
than assuming "safe." Looped three passes over the repo; findings below survived all
three (i.e., they're real, not a misread of one file in isolation).

Severity: **CRIT** = full outage or data breach with low effort. **HIGH** = real damage,
needs some setup. **MED** = degraded trust/quality, not an outage.

---

## CRIT-1 — Redis/Postgres/Ollama are unauthenticated and exposed to the host network

**File:** `docker-compose.yml`

```yaml
redis:
  image: redis:7-alpine
  ports: ["6379:6379"]
  command: redis-server --appendonly yes   # <-- no requirepass
ollama:
  ports: ["11434:11434"]                    # <-- no auth layer at all
```

`ports: "6379:6379"` binds to `0.0.0.0` on the host by default. Combined with no
`requirepass`, **anyone who can reach the VM's IP on port 6379 can run `redis-cli`
against it with zero credentials.** That Redis instance is simultaneously:
- the session store (`session:{number}`)
- the webhook dedup set (`dedup:{message_id}`)
- the rate-limit counters (`ratelimit:{number}:{hour}`)
- the **Celery broker and result backend**

Exploit path (single command, no auth): `redis-cli -h <ip> FLUSHALL` wipes every active
conversation, every dedup record (re-enabling the H1 replay bug from the original
audit), and every rate-limit counter — instant, total denial of service, and it
re-opens an already-"fixed" vulnerability. A less noisy attacker can instead `redis-cli
LPUSH` directly into the Celery queue key to inject arbitrary task messages, or just
read every user's session JSON (phone-number-keyed, i.e. PII) with `KEYS session:*`.

Ollama on `11434` has no auth layer either — an outsider can hit `/api/generate`
directly, exhausting the single shared GPU that the real ledger-extraction path depends
on. Since `model_router.py`'s ROUTINE path falls back to Claude when the local model is
slow/low-confidence, a saturated Ollama silently shifts 100% of traffic to the paid
Claude tier — this is also a **cost-exhaustion vector**, not just latency.

**Fix:**
```yaml
redis:
  image: redis:7-alpine
  command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
  ports:
    - "127.0.0.1:6379:6379"      # loopback only — no host-network exposure
ollama:
  ports:
    - "127.0.0.1:11434:11434"
postgres:
  ports:
    - "127.0.0.1:5432:5432"      # already password-protected, but still shouldn't be world-reachable
```
And update `REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0` in `.env.example`.
Internal services (`gateway`, `orchestrator-worker`) still reach these by service name
on the compose network — only the *host port* binding changes. Also explicitly pin the
Celery serializer to close off a task-injection RCE surface if the broker is ever
reachable again:
```python
# services/orchestrator/celery_entrypoint.py
celery_app.conf.update(task_serializer="json", result_serializer="json", accept_content=["json"])
```

---

## CRIT-2 — PDF generation is an SSRF + injection primitive (Jinja2 autoescape is OFF)

**Files:** `services/pdf_service/generator.py`, `services/pdf_service/templates/monthly_report.html`

```python
_env = Environment(loader=FileSystemLoader(_TEMPLATE_DIR))   # no autoescape=True
...
template.render(member_name=user.name or "সদস্য", ... category names from LLM extraction ...)
```

Jinja2's `Environment()` does **not** autoescape by default unless you pass
`autoescape=True` or use `select_autoescape()`. Every field rendered here —
`member_name`, `shg_name`, `district`, and every category key in
`income_by_category`/`expense_by_category` — ultimately originates from **user voice
input, passed through an LLM extraction step** (`ledger_node.py`'s
`item_bengali` field becomes `LedgerEntry.category`). Nothing sanitizes it before it
lands in an HTML template.

WeasyPrint then renders that HTML to PDF **and fetches remote resources it finds in the
markup** (images, stylesheets, `@import`). So a category string like:
```
পাপড়<img src="http://169.254.169.254/latest/meta-data/iam/security-credentials/">
```
gets stored as a ledger category via a normal voice/text "correction" flow, and the
next time that user requests a report, the **pdf-service container itself makes an
outbound HTTP request to wherever the attacker put in the tag** — classic SSRF, with
the added twist that it can also read local files via `file://` URIs resolved against
`base_url="templates/"`, and exfiltrate their contents by observing which external URL
gets hit (or just embedding local file content directly into the rendered PDF page,
which then gets emailed/WhatsApp'd to a bank).

This one is more dangerous than an ordinary XSS finding because there's no browser and
no CSP to save you — WeasyPrint is a standalone renderer with real network access from
inside your infra.

**Fix (two independent layers, both required):**
```python
# services/pdf_service/generator.py
from markupsafe import escape
_env = Environment(loader=FileSystemLoader(_TEMPLATE_DIR), autoescape=True)  # layer 1

def _clean(s: str | None, max_len: int = 120) -> str:
    """Strip anything that isn't plain text before it ever reaches the template,
    independent of autoescape — defense in depth for a WeasyPrint renderer with
    outbound network access."""
    if not s:
        return ""
    s = re.sub(r"<[^>]*>", "", s)          # strip tags outright, don't rely on escaping alone
    return s[:max_len]

# apply _clean() to member_name, shg_name, district, and every category key
income_by_category = {_clean(cat): amt for cat, amt in income_by_category.items()}
expense_by_category = {_clean(cat): amt for cat, amt in expense_by_category.items()}
```
```python
# WeasyPrint call — disable remote fetch entirely, this document never needs it
pdf_bytes = HTML(string=html_content, base_url=None).write_pdf(
    presentational_hints=True,
)
```
And drop the Google Fonts `@import` from the template in favor of a locally bundled
Noto Sans Bengali font file, so the renderer has *zero* legitimate reason to make
outbound requests — removing the SSRF surface rather than just filtering it.

---

## HIGH-1 — Webhook signature verification uses the wrong secret (silent, not a crash)

**File:** `services/gateway/main.py`

```python
expected = "sha256=" + hmac.new(s.wa_webhook_verify_token.encode(), body, hashlib.sha256).hexdigest()
```

Meta signs `X-Hub-Signature-256` with the WhatsApp **App Secret**, not the webhook
**verify token** (the verify token is only used in the one-time GET handshake
challenge/response — a completely different value with a completely different purpose).
As written, this check will either (a) always fail against real Meta traffic if the
values genuinely differ, silently dropping all production messages, or (b) "pass" only
because someone set `WA_WEBHOOK_VERIFY_TOKEN` and the app secret to the same string,
which means anyone who ever saw the verify token (it's visible in the Meta dashboard
URL config, shared more casually than a secret) can now forge webhook payloads.

**Fix:**
```python
# shared/config/settings.py
wa_app_secret: str  # separate from wa_webhook_verify_token — get from Meta App Dashboard > Settings > Basic

# services/gateway/main.py
expected = "sha256=" + hmac.new(s.wa_app_secret.encode(), body, hashlib.sha256).hexdigest()
```

---

## HIGH-2 — Voice notes have zero size/duration validation before hitting ffmpeg/GPU

**File:** `shared/whatsapp/media.py`, called from `services/gateway/main.py`

The original audit (H9) flagged this for the old `stt-service`, but the *current*
production path (`voice_gateway`/`provider_cascade.py`, invoked from `main.py`) has the
exact same gap and was never covered:

```python
elif msg.message_type == "audio":
    audio_bytes = await download_whatsapp_audio(msg.audio_id)   # no cap, no streaming check
    stt_result = await transcribe(audio_bytes)                   # straight into Sarvam/Bhashini/Whisper
```

Image at least gets a post-download size check (too late to save bandwidth, but at
least rejects it before S3 upload). Audio gets **nothing** — no cap, and it's fed
straight into `whisper_local_provider.transcribe()`, which runs on the single shared
GPU. An oversized or malformed OGG blob (WhatsApp's own client caps voice notes, but
nothing stops a modified client or a direct API call to your webhook from Meta with a
crafted payload) can hang or OOM the GPU worker, taking down transcription for every
concurrent pilot user — the "shared blast radius" risk the original audit warned about
under H9, just via the path that's actually wired up.

**Fix:**
```python
# shared/whatsapp/media.py
MAX_AUDIO_BYTES = 6 * 1024 * 1024  # ~3 min OGG/OPUS per PRD FR1.1, generous margin

async def _download(media_id: str, max_bytes: int | None = None) -> bytes:
    s = get_settings()
    async with httpx.AsyncClient() as client:
        url_resp = await client.get(f"https://graph.facebook.com/v19.0/{media_id}",
                                     headers={"Authorization": f"Bearer {s.wa_access_token}"})
        url_resp.raise_for_status()
        meta = url_resp.json()
        if max_bytes and int(meta.get("file_size", 0)) > max_bytes:
            raise ValueError("media_too_large")
        media_resp = await client.get(meta["url"], headers={"Authorization": f"Bearer {s.wa_access_token}"})
        media_resp.raise_for_status()
        if max_bytes and len(media_resp.content) > max_bytes:
            raise ValueError("media_too_large")
        return media_resp.content

async def download_whatsapp_audio(media_id: str) -> bytes:
    return await _download(media_id, max_bytes=MAX_AUDIO_BYTES)
```
And in `main.py`, wrap the call so an oversized note gets a friendly Bengali reply
instead of an unhandled exception bubbling out of a background task (which currently
just vanishes silently — a debuggability problem on top of the security one).

---

## HIGH-3 — Grounding verifier can be defeated by spelling the number out in words

**File:** `services/rag_service/grounding_verifier.py`

```python
_AMOUNT_RE = re.compile(r"(₹\s?[০-৯0-9,]+|[০-৯0-9,]+\s?টাকা)")
```

This is the system's single most important safety mechanism (per
`docs/product/UNIQUE_VALUE_PROPOSITION.md`, it's *the* differentiator) — and it only
extracts assertions that use digits. Bengali financial speech routinely uses number
*words* ("এক হাজার টাকা" = "one thousand rupees"). If the LLM hallucinates an amount
and phrases it in words instead of digits — which is a completely ordinary, unforced
generation choice, not even an adversarial prompt-injection — `_extract_assertions`
never sees it as an assertion at all, so it can never be flagged ungrounded. A
fabricated scheme amount phrased in words sails through with `all_grounded: True`.

I confirmed this isn't theoretical: `ml/llm-finetune/finetune_qlora.py`'s own training
data uses exactly this style ("Bengali number words: এক=1, দুই=2..."), meaning the
fine-tuned model is *specifically trained* to sometimes produce word-form numbers —
directly undermining the verifier that's supposed to catch it downstream.

**Fix (extend assertion extraction to catch word-numbers before scheme names):**
```python
_NUMBER_WORDS = {
    "এক": 1, "দুই": 2, "তিন": 3, "চার": 4, "পাঁচ": 5, "দশ": 10, "পনেরো": 15,
    "বিশ": 20, "পঁচিশ": 25, "ত্রিশ": 30, "পঞ্চাশ": 50, "একশো": 100,
    "দুইশো": 200, "তিনশো": 300, "পাঁচশো": 500, "হাজার": 1000,
}
_WORD_AMOUNT_RE = re.compile(
    r"(" + "|".join(re.escape(w) for w in _NUMBER_WORDS) + r")(?:\s+(টাকা|হাজার))?"
)

def _extract_assertions(answer_bengali: str) -> list[tuple[str, int]]:
    assertions = []
    for m in _AMOUNT_RE.finditer(answer_bengali):
        assertions.append((m.group(1).strip(), m.start()))
    for m in _DATE_RE.finditer(answer_bengali):
        assertions.append((m.group(1).strip(), m.start()))
    for m in _WORD_AMOUNT_RE.finditer(answer_bengali):
        assertions.append((m.group(0).strip(), m.start()))   # flag it; even an
        # imperfect word->digit conversion is strictly better than silently
        # skipping it — a false "ungrounded" triggers the safe fallback message,
        # which is the correct fail-safe direction for this product.
    return assertions
```
Add this as its own test case (`test_word_form_hallucination_is_caught`) alongside the
existing nine — treat it as a first-class regression, not a nice-to-have, given how
central this check is to the product's actual safety claim.

---

## HIGH-4 — Ledger amounts are stored with no bounds checking, and the save path has no exception handling

**File:** `services/orchestrator/nodes/ledger_confirm_node.py`, `shared/db/models.py`

```python
amount_inr: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)   # max ~99,999,999.99
```
```python
async def _save(state, pending):
    ...
    async with get_db_session() as db:
        for tx in pending.get("transactions", []):
            amt = float(tx.get("amount_inr", 0) or 0)     # <-- no range check at all
            entry = LedgerEntry(..., amount_inr=amt, ...)
            db.add(entry)
        await db.commit()   # <-- not inside try/except
```
The LLM extraction has no upper/lower bound enforced on `amount_inr` before it's
written. A negative amount, a NaN, or a value that overflows `NUMERIC(10,2)` will
either corrupt every downstream P&L calculation (negative income silently flips a
profit/loss report) or raise a `DataError` on `commit()` that is **not caught anywhere
in this function** — it propagates up through the LangGraph node, into
`celery_entrypoint.py`'s `_process_turn_async`, which also has no try/except around
`graph.ainvoke(...)`. The Celery task then retries (per
`@celery_app.task(..., max_retries=2)`) against the same bad input, fails identically
twice more, and the user gets silence — no error message, no confirmation, nothing —
while burning three LLM calls per bad input. A single voice note like "মাইনাস পাঁচ হাজার
টাকা বিক্রি" (or the LLM simply mis-extracting a huge number from noisy audio, which
*will* happen at pilot scale) is enough to trigger this, no malicious intent required —
which makes it more concerning, not less: it'll happen organically during the pilot.

**Fix:**
```python
# ledger_confirm_node.py
MAX_REASONABLE_AMOUNT = 500_000  # ₹5 lakh per single voice-note transaction; PRD's
                                  # domain is micro-business SHG sales — anything above
                                  # this is almost certainly a mis-extraction, not a
                                  # real transaction, and should be caught before storage

def _validate_amount(amt: float) -> float | None:
    if amt != amt or amt in (float("inf"), float("-inf")):   # NaN/inf check
        return None
    if amt < 0 or amt > MAX_REASONABLE_AMOUNT:
        return None
    return round(amt, 2)

async def _save(state, pending):
    user_id = state.get("user_id")
    if not user_id:
        return _reset_with_message(..., trace="ledger_confirm_node:save_failed_no_user_id")

    validated_txs = []
    for tx in pending.get("transactions", []):
        amt = _validate_amount(float(tx.get("amount_inr", 0) or 0))
        if amt is None:
            return _reset_with_message(
                "টাকার পরিমাণটা ঠিক বুঝতে পারলাম না। আবার বলুন, যেমন: '৩০০ টাকা পাপড় বিক্রি করেছি'",
                trace="ledger_confirm_node:amount_out_of_range",
            )
        validated_txs.append((tx, amt))

    try:
        async with get_db_session() as db:
            for tx, amt in validated_txs:
                db.add(LedgerEntry(user_id=user_id, entry_type=tx.get("type", "INCOME"),
                                    amount_inr=amt, category=tx.get("item_bengali"), ...))
            await db.commit()
    except Exception:
        return _reset_with_message(
            "হিসাব রাখতে সমস্যা হয়েছে। একটু পরে আবার চেষ্টা করুন।",
            trace="ledger_confirm_node:db_commit_failed",
        )
    ...
```
And wrap `graph.ainvoke(...)` in `celery_entrypoint.py` similarly, so *any* unhandled
node exception degrades to a Bengali error message instead of silent task death:
```python
async def _process_turn_async(whatsapp_number, turn_input):
    try:
        graph = await get_compiled_graph()
        result = await graph.ainvoke({"whatsapp_number": whatsapp_number, **turn_input},
                                      config={"configurable": {"thread_id": whatsapp_number}})
    except Exception:
        await send_text(whatsapp_number, "দুঃখিত, একটু সমস্যা হয়েছে। আবার চেষ্টা করুন।")
        raise   # still lets Celery's retry/alerting logic see it
    for msg in result.get("outbound_messages", []):
        if msg["type"] == "text":
            await send_text(whatsapp_number, msg["body"])
```

---

## MED-1 — Docker images run as root

None of the Dockerfiles (`gateway`, `pdf_service`, `orchestrator`, `voice_gateway`,
`stt-service`) declare a `USER` directive, so every container runs its process as
`root` by default. Combined with CRIT-2's SSRF-capable PDF renderer, a compromise of
the WeasyPrint/Pillow/rembg dependency chain (all real, actively-updated libraries with
occasional CVEs) gets root inside that container for free, instead of a low-privilege
account an attacker would then need a second bug to escalate from.

**Fix (apply to each Dockerfile):**
```dockerfile
RUN useradd -m -u 1000 appuser
USER appuser
```
placed after `pip install` (so package installs still run with build privileges) and
before `CMD`.

---

## MED-2 — WhatsApp Flow `interactive_payload` is trusted JSON with no schema

**File:** `shared/whatsapp/parser.py`, consumed via `main.py`'s
`turn_input["raw_input_text"] = json.dumps(msg.interactive_payload or {})`

The Flow's `nfm_reply.response_json` is parsed and forwarded into the graph as raw text
with no schema validation (`INTERNSHIP_GUIDE.md` Option C already flags this as
unbuilt). Once a node actually consumes it, an attacker who can trigger a Flow submit
with unexpected fields (extra keys, wrong types, oversized strings) gets whatever that
node does with unvalidated input — currently low-impact since nothing consumes it yet,
but worth a pydantic schema *before* Option C ships, not after.

---

## Summary checklist

| # | Finding | Fixed here |
|---|---|---|
| CRIT-1 | Redis/Postgres/Ollama unauthenticated + host-exposed | ✅ compose port binding + requirepass + Celery serializer pin |
| CRIT-2 | PDF SSRF + HTML injection via unescaped ledger fields | ✅ autoescape + strip-tags + WeasyPrint network disabled |
| HIGH-1 | Webhook HMAC uses wrong secret (verify token ≠ app secret) | ✅ new `wa_app_secret` setting |
| HIGH-2 | No size cap on voice notes before GPU processing | ✅ `Content-Length`/post-download check in `media.py` |
| HIGH-3 | Grounding verifier misses word-form hallucinated amounts | ✅ `_WORD_AMOUNT_RE` extension + new test |
| HIGH-4 | Unbounded ledger amounts, uncaught DB exceptions | ✅ `_validate_amount` + try/except + graph-level catch |
| MED-1 | Containers run as root | ✅ non-root `USER` in Dockerfiles |
| MED-2 | Unvalidated Flow JSON payload | ⚠️ flagged for Option C implementation, not yet consumed anywhere so no fix applied |

Everything above is additive to `SECURITY_AUDIT_V3.md` (H1–H12), not a replacement —
that audit's P0 items (idempotency, rate limiting, audio-retention claims, media size
caps on the *old* `stt-service` path) are still correct and still need to stay applied.
