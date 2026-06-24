# Kotha-Kori (কথা-কড়ি)
## Product Requirements Document (PRD)
**Version:** 1.0 | **Status:** Approved for Development | **Date:** June 2026

---

## 1. Executive Summary

**Kotha-Khata** (Voice-Ledger) is a voice-first, multimodal AI assistant delivered exclusively through WhatsApp for Self-Help Group (SHG) women in rural and semi-urban West Bengal. It turns casual spoken Bengali into structured financial records, government scheme eligibility assessments, product marketing assets, agricultural diagnostics, and group governance documents — without requiring literacy, a smartphone app download, or any prior digital experience.

The product is not a general-purpose AI wrapper. It is a domain-locked, mission-specific operational platform that makes the invisible formal — turning unstructured local-language activity into auditable, bank-grade financial and governance data.

**Primary Impact Metric:** Number of SHG women who successfully access a new government scheme or micro-finance product as a direct result of Kotha-Khata, within 12 months of onboarding.

---

## 2. Problem Statement

### 2.1 The Structural Gaps

| Gap | Current State | Cost |
|-----|--------------|------|
| **Bookkeeping** | Manual ledger or none | Ineligible for bank linkage loans; no profit visibility |
| **Scheme Access** | Word-of-mouth; Panchayat office visits | 40–60% of eligible women never apply |
| **Marketing** | No materials; word-of-mouth sales only | Products underpriced; market limited to neighborhood |
| **Agricultural Risk** | Nearest agronomist is 15–30 km away | Crop/livestock loss wipes out investment overnight |
| **Meeting Records** | Handwritten minutes (or none) | SHG loses "graded" status; bank linkage severed |
| **Training Access** | Physical centers; family duties prevent attendance | Livelihood skills remain stagnant |
| **Market Intelligence** | None | Overproduction of low-margin goods; lost capital |

### 2.2 Why Existing Tools Fail This Demographic

- **General AI chatbots** require literacy, English or formal Hindi, and sustained attention to text
- **Government portals** require Aadhaar-linked logins, desktop access, and bureaucratic form knowledge
- **Stand-alone apps** suffer 80%+ drop-off because they require download, account creation, and repeated habit formation
- **WhatsApp** already has near-universal adoption in this demographic — no new behavior is required

### 2.3 The Insight

> The barrier is not capability. It is translation — between what women already do and know (spoken Bengali, everyday business) and what the formal system accepts (structured text, documented records). Kotha-Khata is that translator.

---

## 3. Target Users

### 3.1 Primary Persona — Sunita (The Core User)

| Attribute | Detail |
|-----------|--------|
| Age | 28–55 |
| Location | Rural/semi-urban West Bengal (districts: Murshidabad, Purulia, South 24 Parganas, Birbhum, Cooch Behar) |
| Language | Bengali (often dialectal — Rarhi, Barendri, Haor variants) |
| Literacy | Limited or functional (can recognize digits, sign name) |
| Phone | Android smartphone with WhatsApp; typically 2G/3G connectivity |
| Business | 1–3 micro-businesses: pickle/papad production, Kantha embroidery, poultry, vegetable cultivation, jute weaving |
| SHG Role | Member (group of 10–20 women) |
| Pain Points | Cannot prove income for loans; does not know which schemes she qualifies for; produces goods with no marketing |
| Motivations | School fees for children; home repair; starting a second business line |

### 3.2 Secondary Persona — Rina (The Group Leader / Pradhan)

| Attribute | Detail |
|-----------|--------|
| Age | 35–55 |
| Role | SHG president or secretary |
| Additional Responsibility | Runs weekly meetings; submits grading documents to block office |
| Pain Point | Handwriting minutes takes 45+ minutes per meeting; errors lead to re-grading delays |
| Tech Comfort | Slightly higher; uses WhatsApp groups to communicate with block-level NGO coordinators |

### 3.3 Tertiary Persona — Block-Level NGO Coordinator

| Attribute | Detail |
|-----------|--------|
| Role | Anandadhara / DRDC field coordinator overseeing 50–200 SHGs |
| Usage | Aggregate reports; compliance dashboard; scheme uptake tracking |
| Pain Point | No single source of truth for SHG activity across their block |

---

## 4. Product Vision & Goals

### 4.1 Vision Statement
A future where every SHG woman in West Bengal, regardless of literacy or location, has access to the same financial intelligence, government entitlements, and market opportunities as a formal business owner.

### 4.2 Strategic Goals (12-Month Horizon)

| # | Goal | Target |
|---|------|--------|
| G1 | Active monthly users | 50,000 SHG members |
| G2 | Government schemes accessed via bot | 15,000 successful applications |
| G3 | Micro-finance loan applications supported | 8,000 loans (using bot-generated PDF ledgers) |
| G4 | SHG groups using Meeting Minutes feature | 5,000 groups |
| G5 | Average session duration | < 3 minutes (voice-first, fast) |
| G6 | Bengali STT accuracy on rural dialects | ≥ 92% word error rate |

---

## 5. Feature Specifications

### Feature 1: Voice-Ledger (Automated Accounting)
**Priority:** P0 — MVP Core

**User Story:** As Sunita, I want to record my daily sales and expenses by speaking in Bengali into WhatsApp, so that I have a monthly financial report without needing to write or use a calculator.

**Functional Requirements:**
- FR1.1: Accept Bengali voice notes (OGG/OPUS format via WhatsApp) up to 3 minutes in length
- FR1.2: Transcribe audio using Bhashini STT API with dialect fallback to fine-tuned Whisper
- FR1.3: Extract financial entities: Revenue items, Amounts (₹), Expense categories, Date (inferred if not stated)
- FR1.4: Store extracted data in user ledger (PostgreSQL, per-user schema)
- FR1.5: Support correction commands: "Bhul hoyeche, papad bikri chhilo 400 taka, 300 noy" (That was wrong, papad sale was ₹400, not ₹300)
- FR1.6: On request ("Amar maasher hisab dao"), generate a PDF Profit/Loss statement
- FR1.7: PDF must include: SHG name, member name, date range, itemized revenue, itemized expenses, net profit, a statement in Bengali suitable for bank submission
- FR1.8: Send PDF back as WhatsApp document message

**Acceptance Criteria:**
- Voice note to confirmed ledger entry: < 8 seconds end-to-end
- Entity extraction accuracy: ≥ 88% on test set of 500 rural Bengali audio samples
- PDF generation: < 5 seconds
- Corrections processed correctly: ≥ 95% of the time

**Edge Cases:**
- Multiple transactions in one voice note → extract all, confirm with numbered list
- Ambiguous currency ("ek shatak" = ₹100?) → confirm before storing
- Network dropout mid-recording → prompt retry with last partial save

---

### Feature 2: Hallucination-Free Government Scheme RAG
**Priority:** P0 — MVP Core

**User Story:** As Sunita, I want to ask whether I qualify for Lakshmir Bhandar or SVSKP and get a step-by-step checklist of exactly which documents to bring to the Panchayat office.

**Functional Requirements:**
- FR2.1: Ingest and index official West Bengal government scheme documents (PDF/HTML) from wb.gov.in, wbfin.nic.in, and anandadhara.wb.gov.in
- FR2.2: Schemes indexed at launch: Lakshmir Bhandar, Anandadhara, Kanyashree, SVSKP, Krishak Bandhu, WBSSP, JAAGO, Rupashree, Sabooj Sathi
- FR2.3: RAG system must cite source documents and refuse to answer if grounding evidence is absent (strict hallucination prevention)
- FR2.4: Eligibility determination via sequential voice/text Q&A dialogue (max 5 questions per scheme)
- FR2.5: Output: Bengali-language eligibility verdict + itemized document checklist + nearest Panchayat office address (via PIN code lookup)
- FR2.6: Scheme database refreshed weekly via automated scraper + human review flag
- FR2.7: Fallback: If scheme information cannot be confirmed, bot states "Ei byshe aami nishchit noi, Panchayat-e jiggesh korun" (I'm not certain about this, please ask the Panchayat) and provides phone number

**Acceptance Criteria:**
- Zero hallucinated scheme amounts or eligibility criteria (verified by manual audit of 200 Q&A pairs)
- Eligibility dialogue completes in ≤ 5 voice exchanges
- Scheme document freshness: ≤ 7 days from official source update

---

### Feature 3: Instant WhatsApp Catalog Creator
**Priority:** P1 — MVP+

**User Story:** As Sunita, I want to photograph my Kantha saree, send it to the bot, and get back a professional Bengali promotional message with a clean background that I can forward to my customer WhatsApp groups.

**Functional Requirements:**
- FR3.1: Accept image via WhatsApp (JPEG/PNG, max 5MB)
- FR3.2: Use vision model to: identify product type, remove/replace background (clean white or gradient), generate Bengali product description (2–4 lines), suggest a price range based on product category (from internal pricing database)
- FR3.3: Output format: processed image (PNG, < 1MB) + Bengali caption text in the same WhatsApp message
- FR3.4: Caption includes: product name, key features (material, size if visible), price suggestion, SHG name watermark, simple Bengali CTA ("Janate chai?" = "Want to know more?")
- FR3.5: User can request English caption variant for urban/export markets
- FR3.6: Option to create a multi-product catalog page (up to 4 images combined into one)

**Acceptance Criteria:**
- Image processing and caption: < 15 seconds
- Background removal accuracy: ≥ 90% clean separation on product photos
- Caption quality: judged ≥ 4/5 by 20 SHG women in user testing

---

### Feature 4: Agri-Doc & Livestock Diagnostic
**Priority:** P1 — MVP+

**User Story:** As a woman who grows vegetables and raises poultry, I want to describe or photograph a sick plant or chicken and get immediate, affordable, locally-available treatment advice in Bengali.

**Functional Requirements:**
- FR4.1: Accept image (diseased plant leaf, affected animal visible symptom) or voice description of symptoms
- FR4.2: Vision model identifies: crop type, disease/pest type, severity (mild/moderate/severe), affected area percentage
- FR4.3: For voice: extract symptom keywords, map to diagnostic knowledge base
- FR4.4: Output: disease name (in Bengali common name), probable cause, 2–3 treatment options prioritized by: (1) home remedy/organic, (2) locally available agri-shop product (avoid brand names; use generic chemical names), (3) when to consult a KVK (Krishi Vigyan Kendra) officer
- FR4.5: Include: "Do NOT apply X without consulting" warnings for potentially harmful pesticides
- FR4.6: Knowledge base covers: West Bengal's 20 most common crops (paddy, potato, tomato, mustard, jute, onion, chili, brinjal) and poultry diseases (Ranikhet, Marek's, coccidiosis, fowl pox)
- FR4.7: Strict liability disclaimer in Bengali at end of every diagnostic response

**Acceptance Criteria:**
- Correct disease identification on top-20 crop diseases: ≥ 85% accuracy on test image set
- Response includes actionable organic/home remedy in 100% of cases
- Disclaimer present: 100% of responses

---

### Feature 5: Automated Subsidy & Loan Matchmaker
**Priority:** P1 — MVP+

**User Story:** As a group leader, I want the bot to tell me when our group becomes eligible for a new fund or scheme, without me having to track it myself.

**Functional Requirements:**
- FR5.1: Bot proactively monitors user ledger data and SHG metadata (group size, meeting regularity, savings record) against scheme eligibility thresholds
- FR5.2: Push WhatsApp notification when eligibility is detected: "Aapnader dal JAAGO prakalpar jonyo eligible hoyeche. Reply 'HAAN' to get the checklist."
- FR5.3: Track schemes: JAAGO revolving fund, WBSSP (≤2% interest), SVSKP (30% subsidy), PMMY (Mudra Loan), NULM, Anandadhara bank linkage tiers
- FR5.4: Generate a pre-filled loan application summary document (PDF) using ledger data: income proof, expense summary, net savings, SHG grade level
- FR5.5: Reminder cadence: notify once, reminder after 14 days if no action, final reminder at 30 days, then mark as "expired opportunity"

**Acceptance Criteria:**
- Zero false positive eligibility notifications (no notifying ineligible groups)
- Application summary PDF accepted as supporting document by at least 3 partner banks (validated during pilot)

---

### Feature 6: Micro-Skill Audio Training
**Priority:** P2 — Post-MVP

**User Story:** As Sunita, I want to learn how to start a mushroom cultivation business through short audio lessons on WhatsApp, at my own pace, while doing household work.

**Functional Requirements:**
- FR6.1: Training library: 10 vocational tracks at launch (mushroom cultivation, terracotta craft, Kantha embroidery, food processing/pickle, poultry rearing, organic vegetable, jute handicraft, tailoring basics, natural dye batik, candle/soap making)
- FR6.2: Each track: 5–10 audio lessons (2–4 minutes each), delivered over consecutive days
- FR6.3: Each lesson ends with a single-question Bengali voice quiz; user speaks answer; NLP grades it
- FR6.4: Progress tracked per user; resume from last lesson
- FR6.5: On track completion: generate a Bengali "Certificate of Completion" PDF with SHG name, member name, date
- FR6.6: Integration with West Bengal SHG & SE department's approved trade list for curriculum alignment

**Acceptance Criteria:**
- Course completion rate (all lessons in a track): ≥ 40% (industry benchmark for async training: 15%; this target reflects community accountability)
- Quiz answer grading accuracy: ≥ 85%

---

### Feature 7: Voice-Driven Meeting Minutes & Group Governance
**Priority:** P1 — MVP+

**User Story:** As Rina, the group leader, I want to record a 2-minute summary of our weekly meeting and have the bot generate properly formatted meeting minutes that I can send to the block coordinator.

**Functional Requirements:**
- FR7.1: Accept group meeting summary as single voice note (max 5 minutes)
- FR7.2: Extract entities: date, attendees (names + count), savings collected (₹ per member), loans given (to whom, amount, purpose), resolutions passed
- FR7.3: Format output as standard SHG meeting minutes template (per West Bengal SHG grading guidelines)
- FR7.4: Send formatted minutes as: WhatsApp text (for WhatsApp group sharing) + PDF (for official submission)
- FR7.5: Maintain cumulative: attendance register, savings register, loan register — all queryable
- FR7.6: Auto-calculate: total group savings, total loans outstanding, repayment status
- FR7.7: Monthly report: full group financial summary, attendance percentage per member — for block officer submission

**Acceptance Criteria:**
- Entity extraction from meeting audio: ≥ 90% accuracy on structured test set
- Meeting minutes format matches West Bengal SHG grading format: validated by 3 block-level officers

---

### Feature 8: Localized Market Price & Demand Predictor
**Priority:** P2 — Post-MVP

**User Story:** As Sunita, I want to know what product I should focus on making next month so I don't waste materials on something the market is already saturated with.

**Functional Requirements:**
- FR8.1: Aggregate anonymous sales data from Voice-Ledger (product category, volume, price realized) by block/district
- FR8.2: Integrate external data: mandi price APIs (Agmarknet), seasonal calendar, West Bengal festival calendar (Durga Puja, Eid, Christmas, Poush Mela) as demand signals
- FR8.3: Weekly demand report per user: "Products with rising demand in your block," "Products with high supply (consider pausing)," "Upcoming seasonal opportunity"
- FR8.4: All data anonymized and aggregated; no individual user data shared with other users
- FR8.5: User can ask: "Ei mase ki banabo?" (What should I make this month?) → personalized recommendation based on their skill set (from training tracks) and local market signal

**Acceptance Criteria:**
- Demand prediction directional accuracy: ≥ 70% (product demand goes up when predicted, vs. goes down or flat)
- Zero individual user data exposed to other users (verified by privacy audit)

---

## 6. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Availability** | 99.5% uptime (allowing ~3.6 hours downtime/month); degraded-mode fallback for STT outages |
| **Latency** | Voice-to-response: < 10 seconds for simple transactions; < 20 seconds for RAG/image queries |
| **Scalability** | Handle 50,000 concurrent active sessions; 500,000 messages/day at peak |
| **Data Privacy** | No audio stored beyond processing (< 60 seconds retention); ledger data encrypted at rest (AES-256); DPDP Act 2023 compliant |
| **Language** | Primary: Bengali (Devanagari romanized + Bengali script output); Secondary: Hindi; Tertiary: English |
| **Accessibility** | Voice-first; no reading required for core flows; all responses available as voice (TTS) on request |
| **Connectivity** | Functional on 2G (text flows); graceful degradation for image/voice features on low bandwidth |
| **Dialect Support** | Standard Bengali + Rarhi, Barendri, Haor, Sylheti-influenced dialects |
| **Security** | End-to-end WhatsApp encryption preserved; no PII in logs; VAPT audit before launch |
| **Compliance** | WhatsApp Business Policy; RBI guidelines on financial advice disclaimers; NOT a registered financial advisor — disclaimers mandatory |

---

## 7. Out of Scope (v1.0)

- Payment processing or money transfer
- Medical diagnosis (only agricultural/livestock)
- Legal advice
- Content outside the SHG/micro-business domain (politics, entertainment, etc.)
- Native mobile app
- Web dashboard for end users (block coordinator dashboard is in scope, but not SHG member web UI)

---

## 8. Success Metrics & KPIs

### 8.1 Acquisition
- Weekly new user registrations via onboarding keyword ("SHURU" or "শুরু")
- Referral rate (new users who joined because an existing user shared the bot number)

### 8.2 Engagement
- DAU/MAU ratio (target: > 0.4 — high for a utility bot)
- Messages per session
- Voice note usage % (target: > 70% of transactions via voice, not text)

### 8.3 Impact (Primary)
- # of PDF ledger reports generated and used for bank applications
- # of government scheme checklists sent
- # of confirmed scheme applications (tracked via follow-up survey at 30 days)
- # of meeting minutes generated, correlating with SHG grading improvements

### 8.4 Quality
- Bengali STT word error rate (WER) — weekly automated eval
- RAG hallucination rate — weekly human audit of 50 random scheme Q&As
- User-reported correction rate (as proxy for entity extraction errors)

---

## 9. Regulatory & Ethical Considerations

| Area | Stance |
|------|--------|
| Financial Advice | Bot is a ledger and information tool. All scheme/loan information is factual, not advice. Disclaimer: "Ei tathya jankari debar jonyo. Loan nebar age bank ba NGO-r sahajje neben." |
| Agricultural Advice | Liability disclaimer on every diagnostic. Recommends KVK consultation for severe cases. |
| Data Consent | Onboarding requires voice/text consent acknowledgement in Bengali |
| Vulnerable Users | Bot does not ask for Aadhaar numbers, bank account numbers, or OTPs at any point — ever |
| Guardrails | Domain-locked: bot politely redirects off-topic queries back to its function |
| Abuse Prevention | Rate limiting; no bulk message capability for end users; WhatsApp WABA policy compliance |
