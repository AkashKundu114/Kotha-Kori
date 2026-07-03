# Field Research Toolkit — SHG / Micro-Entrepreneur Pilot Testing

**Read this note first:** everything in this document is preparation material —
scripts, forms, and protocols — for *you* (or your NGO partner) to run in person.
I can't recruit participants, obtain consent, or conduct interviews myself; those
require a real human physically present with real people. What follows is designed
to make that fieldwork as fast, respectful, and methodologically sound as possible
once you're on the ground.

---

## 1. Outreach plan — who to approach and how

### 1.1 Target participant mix (aim for 15–30 people total)
- **10–20 SHG member women** (the primary persona — Sunita) — via an existing NGO's
  SHG WhatsApp groups. Don't cold-approach individuals; go through a group leader
  or NGO coordinator who already has trust in the community.
- **3–5 SHG group leaders/Pradhans** (the Rina persona) — they'll have sharper
  feedback on the Meeting Minutes / group governance angle even though it's out of
  this pilot's scope; useful for the "what would you want next" interview question.
- **2–5 independent micro-entrepreneurs** (not SHG-affiliated — e.g. a woman running
  a small shop, a home-based tailor) — useful contrast group to see if the product's
  value holds outside the SHG structure specifically, or if the k-anonymized market
  data feature needs SHG-scale density to be useful at all.

### 1.2 Outreach sequence
1. **NGO partner call** (do this before any individual outreach) — explain the
   product in plain terms, ask them to identify one SHG group whose members already
   use WhatsApp regularly. Don't lead with technical detail; lead with "does this
   save someone time or get them something they're currently missing out on."
2. **Group WhatsApp message** (sent by the NGO coordinator, not by you as an
   outsider — trust transfers through the existing relationship):
   > আমরা একটি নতুন WhatsApp সেবা পরীক্ষা করছি যা ভয়েস দিয়ে হিসাব রাখতে এবং পণ্যের
   > ছবি সুন্দর করতে সাহায্য করে। আগ্রহী হলে যোগাযোগ করুন — সম্পূর্ণ বিনামূল্যে,
   > এবং আপনার তথ্য সম্পূর্ণ গোপন থাকবে।
   *(Translation for your reference: "We're testing a new free WhatsApp service that
   helps record accounts by voice and make product photos look nicer. Contact us if
   interested — completely free, and your information stays fully private.")*
3. **Individual onboarding calls/visits** for anyone who responds — this is where
   consent (§2) happens before any product use or data collection.

### 1.3 A realistic timeline
Recruiting 15–30 real participants through a real NGO relationship typically takes
longer than engineering estimates assume. Budget **at least a full week**, running
in parallel with Week 2 of the engineering sprint, not after it. Don't compress this
into "one afternoon" in your plan — that's the single most common way field-work
timelines blow past a paper's submission deadline.

---

## 2. Consent — do this before anyone touches the product

Two **separate** consent steps. Don't bundle them — using someone's voice/video for
a conference talk is a materially different thing than letting them try an app, and
DPDP Act 2023 practice (and basic research ethics) treats them separately.

### 2.1 Product consent (required before any data collection, even a single test message)
Read aloud or shown as WhatsApp text, in Bengali, **before** onboarding:

> কোথা-খাতা ব্যবহারের আগে একটা কথা জানানো দরকার:
> - এটি একটি পরীক্ষামূলক (পাইলট) সেবা, এখনও পুরোপুরি প্রস্তুত নয়
> - আপনার ভয়েস মেসেজ প্রসেস করার পরপরই মুছে ফেলা হয়, সংরক্ষণ করা হয় না
> - আপনার হিসাবের তথ্য শুধু আপনি দেখতে পাবেন, অন্য কারো সাথে শেয়ার করা হবে না
> - বাজারের তথ্য একত্রিত করার সময় আপনার ব্যক্তিগত তথ্য কখনো আলাদাভাবে দেখানো হয় না
> - আপনি যেকোনো সময় ব্যবহার বন্ধ করতে পারেন, কোনো কারণ ছাড়াই
> - এই সেবা কোনো ব্যাংক বা সরকারি প্রতিষ্ঠান থেকে নয়, এটি একটি গবেষণা প্রকল্প
>
> রাজি থাকলে 'হ্যাঁ' বলুন বা লিখুন।

Log: `consent_given = TRUE`, `consent_given_at = <timestamp>`, and — for the research
record specifically (separate from the product DB) — who obtained consent and how
(in person / phone / WhatsApp text).

### 2.2 Interview & video consent (separate, only for the 3–5 people doing in-depth interviews)
This needs to name **exactly** how the material will be used — research paper, slide
deck, conference talk — not a vague "for research purposes." Written or recorded
(audio is enough — get explicit spoken consent recorded at the start of the interview
itself as a second layer of evidence):

> আমি বুঝতে পেরেছি যে এই সাক্ষাৎকারটি রেকর্ড করা হচ্ছে এবং গবেষণাপত্র বা সম্মেলনে
> উপস্থাপনার জন্য ব্যবহার করা হতে পারে। আমার নাম বা মুখ দেখানো হবে কিনা তা আমি
> নিচে বেছে নিতে পারি:
> ☐ আমার নাম ব্যবহার করা যেতে পারে
> ☐ শুধু ছদ্মনাম ব্যবহার করা হোক (আমার আসল নাম গোপন রাখা হবে)
> ☐ ভিডিওতে আমার মুখ দেখানো যেতে পারে
> ☐ শুধু কণ্ঠস্বর ব্যবহার করা হোক, মুখ না দেখিয়ে

Default to the most protective option (pseudonym, voice-only) unless someone
actively opts into more visibility. Never assume permission you weren't explicitly given.

---

## 3. Structured interview guide (~15 minutes per participant)

Ask in this order. Don't lead with feature names — you want to know what they
actually did, not what they think they're supposed to say.

1. **"গত সপ্তাহে আপনি কী কাজে এটা ব্যবহার করেছেন?"**
   (What did you use it for in the last week?) — open-ended, unprompted.
2. **"শেষবার যখন ব্যবহার করেছিলেন, ঠিক কী হয়েছিল? প্রথম থেকে বলুন।"**
   (Walk me through the last time you used it, step by step.) — get the concrete
   sequence, including anything that confused or frustrated them.
3. **"আপনি কি এটা দিয়ে তৈরি কিছু কাউকে দেখিয়েছেন — ব্যাংক, পঞ্চায়েত, পরিবার, কাস্টমার?
   কী হয়েছিল?"**
   (Did you show anyone — bank, panchayat, family, customer — something it produced?
   What happened?) — this is your outcome-grounded evidence, the strongest thing
   you can put in a paper. Push gently for specifics: which bank, what they said,
   did the PDF actually get accepted.
4. **"এটা কী করলে আরো ভালো হতো, যা এখন করে না?"**
   (What would you want it to do that it doesn't?) — feature-gap signal, also good
   for the paper's "future work" section.
5. **(For Catalog Creator users specifically) "ছবিটা কি সত্যিই কারো কাছে পাঠিয়েছেন?
   কেউ কিনেছে?"**
   (Did you actually send the photo to someone? Did anyone buy?) — the specific
   outcome metric for Feature 3.
6. **(For Market Predictor users) "বাজারের পরামর্শ অনুযায়ী কি কিছু পরিবর্তন করেছেন?"**
   (Did you change anything based on the market advice?) — behavioral-change
   evidence, not just "did you read it."

Record audio (with consent from §2.2) or take detailed notes in real time — don't
rely on memory afterward. Transcribe within 24 hours while context is fresh.

---

## 4. Recording protocol (for the 3–5 in-depth video interviews)

- Get the §2.2 consent **on camera, spoken, before** the substantive interview starts
  — this is your strongest evidence trail, stronger than a signed paper form alone
  for a rural, sometimes low-literacy context where reading a form isn't the most
  reliable consent mechanism.
- Bring: recording device (phone is fine), a translator if you're not fluent in the
  local dialect, spare batteries/power bank, printed consent forms as backup.
- Budget a **full field day** for 3–5 video interviews — don't compress this into
  the same visit as bulk onboarding. Rushed interviews produce weak footage and
  weaker quotes.
- Ask permission again at the end: "is there anything you said that you'd want me
  to not include?" — a second consent checkpoint after they've actually seen what
  the conversation covered, not just before.

---

## 5. What to do with the results

- Feed the correction-rate and STT-confidence data back into `docs/research.md`'s
  metrics table — this is the quantitative backbone.
- Feed the interview transcripts into `paper-draft.md`'s Results section
  (§5) — this is the qualitative backbone. Use direct quotes sparingly and only with
  explicit consent per participant's choice in §2.2.
- If 3+ participants independently mention the same friction point, that's worth its
  own subsection in the paper — recurring, unprompted feedback is stronger evidence
  than a single anecdote, however compelling.
- Don't wait until all 15–30 participants are done to start writing — draft the
  paper's methodology and system-description sections now (they don't depend on
  field data), and slot in results as they arrive.
