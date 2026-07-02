# Kotha-Kori (কথা-কড়ি)
## Application Flow Document
**Version:** 1.0 | **Coverage:** All 8 Features | **Date:** June 2026

---

## 1. Overview: The Three-Layer Flow Model

Every interaction in Kotha-Khata passes through three layers:

```
LAYER 1: USER LAYER
  (WhatsApp message: voice / text / image)
         ↓
LAYER 2: INTENT LAYER  
  (What does the user want? Route to correct flow.)
         ↓
LAYER 3: FEATURE LAYER
  (Execute the specific feature FSM, return result)
```

This document covers all flows at all three layers.

---

## 2. Master Intent Router

Every incoming message hits this router first:

```
INCOMING MESSAGE
├── Is this a NEW USER? (not in DB)
│   └── → ONBOARDING FLOW
│
├── Is there an ACTIVE SESSION STATE? (Redis TTL not expired)
│   └── → Resume active flow at current state (pass to feature FSM)
│
├── Message type = IMAGE?
│   ├── User sent image WITH "chasha" / "khet" / plant/crop keyword?
│   │   └── → AGRI-DIAGNOSTIC FLOW
│   └── Otherwise (product image default)
│       └── → CATALOG CREATOR FLOW
│
├── Message is VOICE NOTE?
│   ├── Keywords: "bikri" / "kharach" / "hisab" / "labh" / "khati" / "taka"?
│   │   └── → VOICE-LEDGER FLOW
│   ├── Keywords: "prakalpa" / "yojana" / "scheme" / scheme names?
│   │   └── → SCHEME RAG FLOW
│   ├── Keywords: "sobha" / "mishon" / "meeting" / "boisak"?
│   │   └── → MEETING MINUTES FLOW
│   ├── Keywords: "shikhte chai" / "training" / "course"?
│   │   └── → TRAINING FLOW
│   └── Unclear → CLARIFICATION FLOW
│
├── Message is TEXT?
│   ├── "রিপোর্ট" / "report" / "maaser hisab"?
│   │   └── → LEDGER REPORT FLOW
│   ├── "MENU" / "HELP" / "কি করতে পারি"?
│   │   └── → HELP MENU
│   ├── Scheme keywords?
│   │   └── → SCHEME RAG FLOW
│   └── Other → NLU INTENT CLASSIFICATION (Claude)
│
└── Anything else → FRIENDLY REDIRECT
    "আমি হিসাব রাখতে, প্রকল্প জানাতে, আর পণ্যের
     বিজ্ঞাপন বানাতে পারি। কি দরকার আপনার?"
```

---

## 3. Onboarding Flow

```
TRIGGER: New phone number sends ANY message

STATE: ONBOARDING_WELCOME
────────────────────────────────────────
BOT: "🙏 কোথা-খাতায় আপনাকে স্বাগতম!
      
      আমি আপনার:
      🎙️ ব্যবসার হিসাব রাখব
      📋 সরকারি প্রকল্প খুঁজে দেব
      📸 পণ্যের ছবি সুন্দর করব
      🌾 চাষ ও পশুপালনে পরামর্শ দেব
      
      শুরু করতে আপনার নাম বলুন বা লিখুন।"

USER INPUT: Any name (text or voice)
  → If voice: STT → extract name
  → If text: direct

STATE: ONBOARDING_NAME_RECEIVED
────────────────────────────────────────
  → Save name to context
  
BOT: "{name} দি/দা, আপনার স্বনির্ভর গোষ্ঠীর নাম কী?"

USER INPUT: SHG group name
  → Store in context

STATE: ONBOARDING_SHG_RECEIVED
────────────────────────────────────────
BOT: "আপনি কোন জেলায়? 
      ১. মুর্শিদাবাদ
      ২. দক্ষিণ ২৪ পরগনা
      ৩. বীরভূম
      ৪. পুরুলিয়া
      ৫. কোচবিহার
      ৬. অন্য জেলা (নাম লিখুন)"

USER INPUT: District selection (number or text)

STATE: ONBOARDING_CONSENT
────────────────────────────────────────
BOT: "কোথা-খাতা ব্যবহারের আগে একটা কথা:
      
      ✅ আপনার কণ্ঠস্বর ব্যবহার করা হবে না
      ✅ আপনার হিসাব শুধু আপনি দেখতে পাবেন
      ✅ কোনো ব্যক্তিগত তথ্য বিক্রি হবে না
      
      রাজি থাকলে 'হ্যাঁ' বলুন।"

USER INPUT: "হ্যাঁ" / "ha" / "yes"
  → Set consent_given = TRUE
  → Write user to DB
  → Create SHG record if new

STATE: ONBOARDING_COMPLETE
────────────────────────────────────────
BOT: "✨ {name} দি, আপনার কোথা-খাতা তৈরি!
      
      এখনই চেষ্টা করুন:
      আজকের বিক্রি বা খরচ ভয়েসে বলুন। 🎙️"

→ Transition to IDLE
→ Set Redis session: {state: "IDLE"}
```

---

## 4. Voice-Ledger Flow (Feature 1)

```
TRIGGER: Voice note with financial keywords OR text with amount + item

┌─────────────────────────────────────────────────────────────┐
│                   VOICE-LEDGER FLOW                         │
└─────────────────────────────────────────────────────────────┘

STATE: LEDGER_AUDIO_RECEIVED
────────────────────────────────────────────────────────────
  Action:
  1. ACK immediately → BOT: "🔄 হিসাব করছি..."
  2. Queue Celery task: process_voice_ledger(audio_id)
  3. Download audio from Meta
  4. Convert OGG → WAV 16kHz
  5. Bhashini STT → transcript
  6. NER extraction → entities{}

  ┌─── IF entities.overall_confidence ≥ 0.80 ───┐
  │                                               │
  │    → STATE: LEDGER_CONFIRM                    │
  │                                               │
  │    BOT: "আমি বুঝলাম:                          │
  │                                               │
  │         ✅ আয়: পাপড় ১৫ প্যাকেট → ₹৩০০       │
  │         📤 খরচ: ডাল ও মশলা → ₹১০০            │
  │                                               │
  │         📊 আজকের লাভ: ₹২০০                    │
  │                                               │
  │         ঠিক আছে? (হ্যাঁ / না)"               │
  └───────────────────────────────────────────────┘

  ┌─── IF entities.overall_confidence < 0.80 ───┐
  │                                              │
  │    → STATE: LEDGER_CLARIFY                   │
  │                                              │
  │    BOT: "একটু পরিষ্কার হলো না। আবার বলুন?    │
  │          যেমন: '৩০০ টাকা পাপড় বিক্রি করেছি,   │
  │          ১০০ টাকা মশলা কিনেছি'"              │
  └──────────────────────────────────────────────┘

STATE: LEDGER_CONFIRM (waiting for YES/NO)
────────────────────────────────────────────────────────────
  USER: "হ্যাঁ" / "ha" / "thik" / "ok" / 👍
  
    → STATE: LEDGER_SAVE
    → Write to ledger_entries (DB)
    → BOT: "✅ হিসাব রাখা হয়েছে!
            
            এই মাসে এখন পর্যন্ত:
            📈 মোট আয়: ₹{monthly_income}
            📉 মোট খরচ: ₹{monthly_expense}
            💰 নেট লাভ: ₹{net_profit}
            
            মাসের শেষে রিপোর্ট পেতে 'রিপোর্ট' লিখুন।"
    → IDLE

  USER: "না" / "bhul" / "ঠিক নয়" / 
        OR sends a correction voice note
  
    → STATE: LEDGER_CORRECT
    → Extract correction from user message
    → Apply correction to pending_entry
    → Loop back to LEDGER_CONFIRM with updated entities

  TIMEOUT (90 seconds, no response):
    → BOT: "হিসাব বাদ দেওয়া হলো। পরে আবার বলুন।"
    → IDLE
    → Discard pending_entry

STATE: LEDGER_REPORT_REQUEST
────────────────────────────────────────────────────────────
  TRIGGER: "রিপোর্ট" / "মাসের হিসাব" / "report"

  BOT: "কোন মাসের রিপোর্ট?
        ১. এই মাস ({current_month})
        ২. গত মাস ({last_month})
        ৩. নিজে বলুন (যেমন: 'মার্চ ২০২৬')"

  USER: Selection

  → Generate PDF (WeasyPrint)
  → Upload to S3
  → Send PDF via WhatsApp document message
  
  BOT: (with PDF attachment)
       "📄 {member_name} দির {month} মাসের হিসাব:
        
        আয়: ₹{income} | খরচ: ₹{expense} | লাভ: ₹{profit}
        
        এই PDF ব্যাংক বা পঞ্চায়েতে দেখাতে পারবেন।"
  → IDLE
```

---

## 5. Scheme RAG Flow (Feature 2)

```
TRIGGER: "প্রকল্প" / "যোজনা" / "লক্ষ্মীর ভান্ডার" / "আনন্দধারা" etc.
         OR: "আমি কি X-র সুবিধা পাবো?"

┌─────────────────────────────────────────────────────────────┐
│                    SCHEME RAG FLOW                          │
└─────────────────────────────────────────────────────────────┘

STATE: SCHEME_IDENTIFY
────────────────────────────────────────────────────────────
  If scheme name detected in query:
    → Directly go to SCHEME_COLLECT_ELIGIBILITY
  
  If no scheme specified:
    BOT: "কোন প্রকল্প সম্পর্কে জানতে চান?
          
          ১. লক্ষ্মীর ভান্ডার
          ২. আনন্দধারা
          ৩. SVSKP (স্বামী বিবেকানন্দ স্বনির্ভর কর্মসংস্থান প্রকল্প)
          ৪. কৃষক বন্ধু
          ৫. WBSSP (ঋণের সুদ সহায়তা)
          ৬. JAAGO
          ৭. কন্যাশ্রী
          ৮. রূপশ্রী
          
          নম্বর বলুন বা প্রকল্পের নাম বলুন।"

STATE: SCHEME_COLLECT_ELIGIBILITY
────────────────────────────────────────────────────────────
  Dynamic Q&A based on scheme requirements.
  Example for Lakshmir Bhandar:

  Q1: BOT: "আপনার বয়স কত?" → USER: "৩৪"
  Q2: BOT: "আপনার কাছে স্বাস্থ্য সাথী কার্ড আছে?" → USER: "হ্যাঁ"
  Q3: BOT: "আপনি কি সরকারি চাকরিজীবী বা আয়কর দাতা?" → USER: "না"
  Q4: BOT: "আপনার পরিবারে কি কোনো সদস্য ইতিমধ্যে এই সুবিধা পাচ্ছেন?" → USER: "না"
  
  → All answers stored in session context
  → Calculate eligibility via rule engine

STATE: SCHEME_CALCULATE_ELIGIBILITY
────────────────────────────────────────────────────────────
  Eligibility Rule Engine (deterministic, not LLM):
  
  [LAKSHMIR_BHANDAR_RULES]
  - Age: 25-60 ✓
  - Not a government employee ✓
  - Not an income tax payer ✓
  - Not already receiving ✓
  → ELIGIBLE
  
  RAG query: "Lakshmir Bhandar documents required for application"
  → Retrieve from scheme_chunks
  → Generate checklist

  ┌─── ELIGIBLE ───────────────────────────────────────────┐
  │                                                        │
  │    BOT: "✅ সুখবর! আপনি লক্ষ্মীর ভান্ডার পাওয়ার     │
  │          যোগ্য।                                        │
  │                                                        │
  │          আবেদনের জন্য এই কাগজপত্র নিয়ে যান:          │
  │                                                        │
  │          📄 ১. আধার কার্ড                              │
  │          📄 ২. ভোটার কার্ড                             │
  │          📄 ৩. ব্যাংকের পাসবুক (প্রথম পাতা)           │
  │          📄 ৪. রেশন কার্ড                              │
  │          📄 ৫. স্বাস্থ্য সাথী কার্ড (যদি থাকে)        │
  │                                                        │
  │          📍 কোথায় যাবেন: আপনার গ্রাম পঞ্চায়েত অফিস   │
  │                                                        │
  │          ⚠️ তথ্যসূত্র: wb.gov.in (এপ্রিল ২০২৬)        │
  │                                                        │
  │          ১৪ দিন পরে মনে করিয়ে দেব।"                  │
  │                                                        │
  │    → Set reminder in notification_queue                │
  │    → IDLE                                              │
  └────────────────────────────────────────────────────────┘

  ┌─── INELIGIBLE ─────────────────────────────────────────┐
  │                                                        │
  │    BOT: "দুঃখিত, এই মুহূর্তে আপনি লক্ষ্মীর ভান্ডারের │
  │          জন্য যোগ্য নন কারণ: [specific reason]        │
  │                                                        │
  │          তবে আপনি এই প্রকল্পগুলো দেখতে পারেন:         │
  │          → SVSKP (নতুন ব্যবসা শুরুতে ৩০% ভর্তুকি)    │
  │          → WBSSP (ব্যাংক ঋণে ২% সুদ সহায়তা)          │
  │                                                        │
  │          এগুলো সম্পর্কে জানতে চান?"                   │
  └────────────────────────────────────────────────────────┘

  ┌─── RAG CANNOT GROUND ANSWER ───────────────────────────┐
  │                                                        │
  │    BOT: "এই বিষয়ে আমার কাছে নিশ্চিত তথ্য নেই।       │
  │          পঞ্চায়েত অফিসে বা আনন্দধারা ব্লক অফিসে      │
  │          জিজ্ঞেস করুন। ফোন: [block office number]"    │
  └────────────────────────────────────────────────────────┘
```

---

## 6. Catalog Creator Flow (Feature 3)

```
TRIGGER: User sends a product image (no crop/plant keywords in caption)

STATE: CATALOG_IMAGE_RECEIVED
────────────────────────────────────────────────────────────
  BOT: "📸 ছবি পেলাম! সুন্দর বিজ্ঞাপন বানাচ্ছি... ⏳"
  
  BACKGROUND PROCESSING:
  1. Download image from Meta
  2. Quality check (blur, resolution)
     → If too blurry: BOT: "ছবিটা একটু ঝাপসা। আরো কাছ থেকে তুলুন।"
  3. rembg background removal
  4. Apply clean gradient background
  5. GPT-4o Vision analysis → product details
  6. Claude: generate Bengali caption + price suggestion
  7. Pillow: overlay product name + SHG watermark on image
  8. Upload processed image to S3

STATE: CATALOG_DELIVER
────────────────────────────────────────────────────────────
  BOT sends:
  [PROCESSED IMAGE with clean background + watermark]
  
  Caption text:
  "✨ এই বার্তাটি আপনার কাস্টমার গ্রুপে পাঠাতে পারেন:
   
   ━━━━━━━━━━━━━━━━━━
   🧵 হাতের কাজের কাঁথা শাড়ি
   
   🎨 খাঁটি হাতের সূক্ষ্ম কাজ
   📐 সাইজ: ৫.৫ × ৫.৫ মিটার
   💰 দাম: ₹৮০০–₹১,২০০
   
   অর্ডার করতে এই নম্বরে WhatsApp করুন 📱
   
   — {SHG নাম}
   ━━━━━━━━━━━━━━━━━━"
  
  Follow-up:
  BOT: "ইংরেজিতেও চান? (শহুরে বা বাইরের কাস্টমারের জন্য)"
  
  USER: "হ্যাঁ"
  → BOT sends English caption variant
  → IDLE
  
  USER: "না"
  → IDLE
```

---

## 7. Agri-Diagnostic Flow (Feature 4)

```
TRIGGER A: Image with crop/plant/animal context keyword
TRIGGER B: Voice note describing plant symptoms
TRIGGER C: Text: "গাছে রোগ হয়েছে" / "মুরগি অসুস্থ"

STATE: AGRI_INPUT_RECEIVED
────────────────────────────────────────────────────────────

PATH A: IMAGE-BASED
  BOT: "🔍 দেখছি..."
  
  1. Resize image to 512x512
  2. Run EfficientNet-B4 inference
     → Top-3 predictions with confidence
  
  IF max_confidence ≥ 0.60:
    → Proceed to AGRI_DIAGNOSE
  IF max_confidence < 0.60:
    → Escalate to GPT-4o Vision for secondary analysis
    → If GPT-4o also uncertain: AGRI_ESCALATE

PATH B: VOICE-BASED
  1. STT → transcript
  2. Extract symptom keywords
  3. Map to disease knowledge base
  4. Retrieve top-3 matches → AGRI_DIAGNOSE

STATE: AGRI_DIAGNOSE
────────────────────────────────────────────────────────────
  BOT: "🌾 রোগ চেনা গেছে:
        
        🔴 নাম: ধানের পাতা পোড়া রোগ (Leaf Scorch)
        📊 আক্রান্ত: আনুমানিক ৩০%
        
        💊 চিকিৎসা:
        
        ১. ঘরোয়া উপায় (বিনা খরচে):
           → নিমপাতার রস স্প্রে করুন সন্ধ্যায়
           → আক্রান্ত পাতা তুলে পুড়িয়ে দিন
        
        ২. কৃষি দোকানে পাবেন:
           → কার্বেন্ডাজিম (১ গ্রাম / ১ লিটার জলে)
           → স্প্রে করুন ৭ দিন পর পর
        
        ৩. KVK-তে যোগাযোগ করুন যদি:
           → ৫০% এর বেশি জমি আক্রান্ত হয়
        
        ⚠️ সতর্কতা: এই পরামর্শ সাধারণ জ্ঞানের ভিত্তিতে।
        গুরুতর রোগে বিশেষজ্ঞের পরামর্শ নিন।
        📞 জেলা KVK: {kvk_phone_number}"
  → IDLE

STATE: AGRI_ESCALATE (Low confidence)
────────────────────────────────────────────────────────────
  BOT: "ছবি থেকে নিশ্চিত হতে পারলাম না।
        
        দয়া করে:
        ✅ আক্রান্ত অংশের কাছ থেকে ছবি তুলুন
        বা
        ✅ লক্ষণগুলো ভয়েসে বর্ণনা করুন
        (যেমন: পাতার রং কেমন, দাগ আছে কিনা)
        
        📞 এখনই সাহায্য দরকার হলে:
        কৃষি বিজ্ঞান কেন্দ্র (KVK): {kvk_phone}"
  → Wait for re-attempt or IDLE after 5 min
```

---

## 8. Meeting Minutes Flow (Feature 7)

```
TRIGGER: Voice note/text with "সভা" / "মিটিং" / "বৈঠক" / "হাজিরা"
         (Usually from SHG leader)

STATE: MEETING_PROMPT
────────────────────────────────────────────────────────────
  BOT: "📋 সভার সারসংক্ষেপ বলুন ভয়েসে।
        যেমন:
        'আজ ৮ জন হাজির ছিলেন। প্রত্যেকে ৫০ টাকা জমা দিয়েছেন।
         সিতাকে স্কুলের ফি-এর জন্য ৫০০ টাকা ঋণ দেওয়া হলো।'"

STATE: MEETING_AUDIO_RECEIVED
────────────────────────────────────────────────────────────
  1. STT → transcript
  2. NLP extraction:
     → attendees_count: 8
     → per_member_savings: ₹50
     → total_savings: ₹400
     → loans: [{member: "Sita", amount: 500, purpose: "school fees"}]
     → resolutions: []
  
  3. Generate formatted minutes text
  4. Generate PDF (West Bengal SHG format)

STATE: MEETING_CONFIRM
────────────────────────────────────────────────────────────
  BOT sends text + PDF:
  
  Text preview:
  "📋 সভার কার্যবিবরণী:
   
   তারিখ: ২৪ জুন ২০২৬
   গোষ্ঠীর নাম: মা দুর্গা গোষ্ঠী
   উপস্থিত: ৮ জন
   
   💰 আয়:
   • প্রত্যেক সদস্যের সঞ্চয়: ₹৫০ × ৮ = ₹৪০০
   
   💸 ঋণ প্রদান:
   • সিতা দেবী — ₹৫০০ (স্কুল ফি)
   
   সিদ্ধান্ত: কোনো বিশেষ সিদ্ধান্ত নেই
   
   [PDF সংযুক্ত — ব্লক অফিসে জমা দিতে পারবেন]
   
   ঠিক আছে?"

  USER: "হ্যাঁ"
  → Save meeting_record to DB
  → Update group savings balance
  → Update loan register
  → BOT: "✅ সভার নথি রাখা হয়েছে। এই PDF ব্লক অফিসে দিতে পারবেন।"
  → IDLE

  USER: Correction
  → Re-extract with correction context → loop to MEETING_CONFIRM
```

---

## 9. Subsidy Matchmaker Flow (Feature 5) — Proactive

```
TRIGGER: Background job (daily cron, not user-initiated)

CRON JOB: check_scheme_eligibility_all_users()
────────────────────────────────────────────────────────────
  For each active user:
  
  1. Fetch user profile + ledger summary + SHG data
  2. Run eligibility rules against all scheme thresholds:
  
     JAAGO_ELIGIBLE = (
       shg.grade_level >= 2 AND
       shg.months_active >= 6 AND
       NOT previously_alerted_for_JAAGO
     )
     
     SVSKP_ELIGIBLE = (
       user.age between 18 and 45 AND
       NOT is_government_employee AND
       user has NO existing business_loan
     )
     
     WBSSP_ELIGIBLE = (
       shg.bank_linkage_status IN ['PHASE1', 'PHASE2', 'PHASE3'] AND
       NOT already_has_wbssp_benefit
     )
  
  3. If any eligibility = TRUE and NOT already_alerted:
     → Queue WhatsApp template notification

NOTIFICATION (WhatsApp Template Message — pre-approved):
────────────────────────────────────────────────────────────
  BOT → Sunita's number:
  "🌟 সুনীতা দি, সুখবর!
   
   আপনার গোষ্ঠী JAAGO প্রকল্পের জন্য যোগ্য হয়েছে।
   প্রতি বছর ₹৫,০০০ সহায়তা পেতে পারেন।
   
   'JAAGO' লিখুন বিস্তারিত জানতে।"

USER RESPONSE: "JAAGO"
  → Trigger SCHEME RAG FLOW for JAAGO
  → Full checklist + Panchayat office info
  → Set 14-day reminder

14 DAYS LATER (if no confirmation of application):
  BOT: "সুনীতা দি, JAAGO-র আবেদন করা হয়েছে?
        না হলে, এখনো সময় আছে। 'হ্যাঁ/না' জানান।"

USER: "না"
  → BOT: "ঠিক আছে। সাহায্য লাগলে 'JAAGO' লিখুন।"
  → Set 30-day final reminder

30 DAYS LATER:
  BOT: "JAAGO প্রকল্পের শেষ মনে করিয়ে দিচ্ছি।
        আর জানাব না যদি না চান।"
  → Mark as EXPIRED in DB
```

---

## 10. Training Flow (Feature 6)

```
TRIGGER: "শিখতে চাই" / "training" / "কোর্স" / "মাশরুম চাষ শেখাও"

STATE: TRAINING_SELECT_TRACK
────────────────────────────────────────────────────────────
  BOT: "কোন বিষয়ে শিখতে চান?
        
        ১. 🍄 মাশরুম চাষ
        ২. 🥒 আচার ও মুড়ি-মুড়কি তৈরি
        ৩. 🧵 কাঁথা সেলাই ও বিক্রি
        ৪. 🐓 হাঁস-মুরগি পালন
        ৫. 🥬 জৈব সবজি চাষ"

  USER: "১" or "মাশরুম"
  
  → Load track: MUSHROOM_CULTIVATION
  → Check: user already enrolled? Resume or start fresh

STATE: TRAINING_LESSON_DELIVER
────────────────────────────────────────────────────────────
  Day 1:
  BOT: "🍄 মাশরুম চাষ — পাঠ ১: পরিচয়
        
        [AUDIO MESSAGE — 3 minutes]
        
        আজকের পাঠ শুনুন। শেষে একটা প্রশ্ন করব।"
  
  (Audio plays)
  
  BOT: "প্রশ্ন: মাশরুম চাষে সবচেয়ে দরকারি কী —
        ক) রোদ  খ) আর্দ্রতা  গ) মাটি
        
        উত্তর বলুন বা লিখুন।"
  
  USER: "আর্দ্রতা" (voice or text)
  
  → NLP: grade answer → CORRECT
  → BOT: "✅ একদম ঠিক! কাল পাঠ ২ পাঠাব।"
  → Update training_progress: lesson_1 = COMPLETE
  → Schedule: tomorrow same time → Lesson 2

  USER: "সূর্যের আলো" → INCORRECT
  → BOT: "আসলে মাশরুমের জন্য আর্দ্রতা সবচেয়ে দরকারি।
          রোদ বা মাটির প্রয়োজন নেই। আগামীকাল পাঠ ২।"
  → Mark lesson as ATTEMPTED (not CORRECT) but continue

STATE: TRAINING_COMPLETE
────────────────────────────────────────────────────────────
  On final lesson completion:
  → Generate Certificate PDF (Bengali)
  → Send PDF
  
  BOT: "🎓 অভিনন্দন সুনীতা দি!
        
        আপনি মাশরুম চাষের কোর্স সম্পন্ন করেছেন।
        
        [CERTIFICATE PDF]
        
        এখন কি শুরু করতে চান?
        বীজমশলার জন্য কোথায় যাবেন জানাতে পারি।"
```

---

## 11. Help Menu Flow

```
TRIGGER: "সাহায্য" / "HELP" / "menu" / "কি করো"

BOT: "কোথা-খাতা যা করতে পারে:
      
      🎙️ হিসাব রাখুন
         ভয়েসে বলুন: 'আজ ৫০০ টাকা পাপড় বিক্রি'
      
      📋 সরকারি প্রকল্প
         বলুন: 'লক্ষ্মীর ভান্ডার পাবো কিনা'
      
      📸 পণ্যের বিজ্ঞাপন
         পণ্যের ছবি পাঠান
      
      🌾 চাষের সমস্যা
         গাছের ছবি পাঠান বা লক্ষণ বলুন
      
      📊 মাসের রিপোর্ট
         লিখুন: 'রিপোর্ট'
      
      📋 সভার নথি
         সভার সারসংক্ষেপ ভয়েসে বলুন
      
      🎓 ব্যবসার প্রশিক্ষণ
         লিখুন: 'শিখতে চাই'"
→ IDLE
```

---

## 12. Error & Edge Case Flows

### 12.1 Network / STT Failure
```
STT fails or times out:
BOT: "দুঃখিত, কণ্ঠস্বর বুঝতে পারলাম না।
      একটু পরে আবার বলুন, বা টাইপ করে লিখুন।"
→ IDLE (session preserved for 5 minutes for retry)
```

### 12.2 Off-Topic Query
```
User asks about politics, cricket scores, entertainment, etc.:
BOT: "এই বিষয়ে আমি সাহায্য করতে পারব না।
      
      আমি শুধু ব্যবসার হিসাব, সরকারি প্রকল্প,
      পণ্যের বিজ্ঞাপন, আর চাষের বিষয়ে জানি।
      
      কি দরকার আপনার?"
```

### 12.3 Sensitive / Personal Request
```
User shares personal distress or asks for help outside scope:
BOT: "আপনার কথা শুনলাম। এই বিষয়ে আমি সাহায্য করতে পারব না।
      আপনার এলাকার আনন্দধারা দিদির সাথে কথা বলুন।
      
      তারপর আমাকে ব্যবসার কথা বলুন — সেখানে সাহায্য করতে পারব।"
```

### 12.4 Spam / Abusive Input
```
→ Rate limit: max 30 messages per hour per user
→ Warning on 25th message: "আপনি অনেক বার মেসেজ পাঠিয়েছেন।
   ১ ঘন্টা পর আবার চেষ্টা করুন।"
→ Soft block at limit (not permanent)
```

---

## 13. System Sequence Diagram — Voice Ledger (Complete)

```
User          WhatsApp      Gateway       Redis       Celery       Bhashini    Claude      PostgreSQL   S3
 │                │             │            │            │             │           │             │        │
 │─voice note────►│             │            │            │             │           │             │        │
 │                │──webhook───►│            │            │             │           │             │        │
 │                │◄─200 OK─────│            │            │             │           │             │        │
 │                │             │─get session►            │             │           │             │        │
 │                │             │◄─session───│            │             │           │             │        │
 │                │             │──queue task────────────►│             │           │             │        │
 │                │             │            │            │─download audio──────────────────────────────── │
 │                │             │            │            │◄─audio bytes──────────────────────────────────  │
 │                │             │            │            │─STT request─►│           │             │        │
 │                │             │            │            │◄─transcript──│           │             │        │
 │                │             │            │            │─NER extract────────────►│             │        │
 │                │             │            │◄─set CONFIRM│◄─entities──│           │             │        │
 │                │◄─confirm msg│◄─send msg──│            │             │           │             │        │
 │◄─confirmation──│             │            │            │             │           │             │        │
 │                │             │            │            │             │           │             │        │
 │─"হ্যাঁ"────────►│             │            │            │             │           │             │        │
 │                │──webhook───►│            │            │             │           │             │        │
 │                │             │─get session►            │             │           │             │        │
 │                │             │◄─CONFIRM───│            │             │           │             │        │
 │                │             │──save entry─────────────────────────────────────────────────────►        │
 │                │             │◄─entry_id──────────────────────────────────────────────────────│        │
 │                │             │─update session─────────►            │             │             │        │
 │                │◄─"✅ রাখা হয়েছে"          │            │             │           │             │        │
 │◄─success msg───│             │            │            │             │           │             │        │
```

---

## 14. State Transition Summary

```
All Feature States:

IDLE
├── onboarding trigger ──────────────────► ONBOARD_WELCOME → ... → IDLE
├── financial keywords (voice) ──────────► LEDGER_AUDIO_RECEIVED → CONFIRM → SAVE → IDLE
├── "রিপোর্ট" ───────────────────────────► LEDGER_REPORT → PDF_SEND → IDLE  
├── scheme keywords ────────────────────► SCHEME_IDENTIFY → ELIGIBILITY → CHECKLIST → IDLE
├── product image ────────────────────► CATALOG_IMAGE → PROCESS → DELIVER → IDLE
├── crop image / symptom voice ──────────► AGRI_INPUT → DIAGNOSE → DELIVER → IDLE
├── meeting keywords ────────────────────► MEETING_PROMPT → AUDIO → MINUTES → IDLE
├── training keywords ───────────────────► TRAINING_SELECT → LESSON → QUIZ → (next day) → IDLE
├── "HELP" / "সাহায্য" ──────────────────► HELP_MENU → IDLE
└── unknown ─────────────────────────────► NLU_CLASSIFY → route or CLARIFY → IDLE

PROACTIVE (cron-triggered):
background_job → SCHEME_ALERT → user responds → SCHEME_RAG_FLOW
training_schedule → LESSON_DELIVER → QUIZ → IDLE
reminder_queue → SCHEME_REMINDER → IDLE
```
