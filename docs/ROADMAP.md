# Kotha-Kori (কথা-কড়ি)
## Product Roadmap
**Version:** 1.0 | **Horizon:** 18 Months | **Date:** June 2026

---

## Roadmap Philosophy

Kotha-Khata is built in three concentric rings of value:

- **Ring 1 (MVP):** Prove the core loop — women record transactions by voice, get a PDF they can show a bank. This is the wedge.
- **Ring 2 (Growth):** Add surface area — schemes, catalog, agri-diagnostics, meeting minutes. This is the retention engine.
- **Ring 3 (Scale):** Build network effects — market intelligence becomes accurate only with volume; training completion rates rise with community features. This is the moat.

**Release Cadence:** 2-week sprints; major releases every 6 weeks.

---

## Phase 0 — Foundation (Weeks 1–6)
**Theme: Infrastructure & Core Bot Skeleton**

### Goals
- WhatsApp bot is live and responds to messages
- Bengali STT pipeline functional with Bhashini + Whisper fallback
- Basic onboarding flow complete
- Database schema deployed and migrated
- CI/CD pipeline operational

### Deliverables

| # | Deliverable | Owner | Exit Criteria |
|---|-------------|-------|---------------|
| 0.1 | WhatsApp Cloud API WABA verification and webhook setup | Backend | Webhook receives messages; ACKs within 200ms |
| 0.2 | FastAPI gateway service | Backend | Passes load test of 1,000 concurrent webhooks |
| 0.3 | Redis session management | Backend | Session state persists across turns; TTL cleanup working |
| 0.4 | Bhashini STT integration | ML | Transcribes Bengali voice note with ≥ 85% WER on 50-sample test set |
| 0.5 | Whisper fallback STT (self-hosted) | ML/DevOps | Handles 100% of Bhashini failure cases |
| 0.6 | PostgreSQL schema deployment (Supabase) | Backend | All tables created; migrations versioned with Alembic |
| 0.7 | Bengali onboarding flow | Product/Backend | New user completes onboarding in ≤ 4 messages |
| 0.8 | CI/CD pipeline (GitHub Actions → ECR → ArgoCD) | DevOps | Automated deploy on merge to main; < 10 min deploy time |
| 0.9 | Error handling & alerting baseline | DevOps | PagerDuty alerts for webhook errors; Sentry for exceptions |
| 0.10 | DPDP Act 2023 compliance audit | Legal/Backend | Consent flow approved; data retention policies documented |

### Milestone: M0 — "Bot is alive"
> A WhatsApp message to the bot number in Bengali receives a coherent Bengali response within 10 seconds. Internal demo complete.

---

## Phase 1 — MVP (Weeks 7–18)
**Theme: Voice-Ledger + Scheme RAG — The Core Value Loop**

### Goals
- A woman can record transactions by voice and receive a monthly PDF
- A woman can ask about government schemes and receive a checklist
- System deployed to 200 pilot users (2 districts: Murshidabad + South 24 Parganas)
- STT WER ≤ 92%, zero RAG hallucinations in production

### Sprint Breakdown

#### Sprint 1–2 (Weeks 7–10): Voice-Ledger Core
| # | Task | Exit Criteria |
|---|------|---------------|
| 1.1 | NER model for Bengali financial entities | F1 ≥ 0.85 on labeled test set of 200 utterances |
| 1.2 | Ledger FSM (entry, confirm, correct, save) | Full flow tested end-to-end with 5 test users |
| 1.3 | Ledger DB write + read operations | ACID compliance verified; no duplicate entries under load |
| 1.4 | Correction handling ("bhul hoyeche") | Correction processed correctly in ≥ 95% of test cases |
| 1.5 | Multi-transaction voice note parsing | All transactions extracted from a 2-min note with 3 items |

#### Sprint 3–4 (Weeks 11–14): PDF Report Generation
| # | Task | Exit Criteria |
|---|------|---------------|
| 1.6 | Bengali PDF template (WeasyPrint) | PDF renders Bengali Unicode correctly in 3 test environments |
| 1.7 | Monthly report generation pipeline | PDF generated in < 5 seconds for 30-day ledger |
| 1.8 | PDF delivery via WhatsApp document message | File received by test users on 2G and 4G |
| 1.9 | Date range selector ("ei maser hisab") | Custom period reports functional |
| 1.10 | Bank-submission statement in PDF | Reviewed and approved by 1 partner bank manager |

#### Sprint 5–6 (Weeks 15–18): Scheme RAG
| # | Task | Exit Criteria |
|---|------|---------------|
| 1.11 | Scheme document ingestion pipeline (9 schemes) | All 9 schemes indexed; source URLs verified |
| 1.12 | Hybrid RAG retrieval (BM25 + pgvector) | Retrieval accuracy ≥ 80% on 50-question eval set |
| 1.13 | Eligibility dialogue FSM | 5-question dialogue completes for each scheme |
| 1.14 | Bengali eligibility verdict + checklist output | Zero hallucinations in 100 manual audit queries |
| 1.15 | Scheme refresh pipeline (weekly scraper) | Detects and flags document changes automatically |
| 1.16 | Pilot deployment to 200 users | ≥ 60% of pilots complete at least 1 ledger entry; ≥ 20% ask a scheme question |

### Milestone: M1 — "Pilot Live"
> 200 real SHG women using the Voice-Ledger and Scheme RAG in production. First bank loan application submitted using a Kotha-Khata PDF. Press release ready.

---

## Phase 2 — Growth (Weeks 19–36)
**Theme: Full Feature Suite + 5,000 Users**

### Goals
- All 8 features live
- 5,000 active monthly users across 5 districts
- NGO coordinator dashboard live
- First integration with Anandadhara block-level reporting

### Feature Releases

#### Release 2.0 (Weeks 19–24): Catalog Creator + Agri-Diagnostic

**Catalog Creator:**
- Product image background removal (rembg)
- GPT-4o Vision integration for product identification
- Bengali caption generation
- Image overlay (product name, price, SHG watermark)
- WhatsApp send as sticker/image message

**Agri-Diagnostic:**
- EfficientNet-B4 model training on West Bengal crop disease dataset (initial: 10,000 images)
- Top-20 crop disease coverage
- Poultry disease knowledge base (voice description path)
- Organic remedy database (300+ remedies, locally sourced)
- KVK referral escalation logic
- Liability disclaimer enforcement

#### Release 2.1 (Weeks 25–30): Meeting Minutes + Subsidy Matchmaker

**Meeting Minutes:**
- Meeting summary voice note parsing
- West Bengal SHG format template
- Attendance register, savings register, loan register
- PDF + WhatsApp text output
- Monthly group report for block submission
- Group savings and loan balance tracking

**Subsidy Matchmaker:**
- Proactive eligibility monitoring (daily background job)
- WhatsApp template message alerts (pre-approved by Meta)
- JAAGO, WBSSP, SVSKP, PMMY scheme integration
- Pre-filled loan application summary PDF
- Reminder cadence (14-day, 30-day follow-up)

#### Release 2.2 (Weeks 31–36): Training Tracks + NGO Dashboard

**Micro-Skill Training:**
- 5 vocational tracks (mushroom, food processing, Kantha, poultry, organic vegetable)
- Bengali audio lesson content (produced with West Bengal SHG & SE Dept.)
- Day-by-day delivery via WhatsApp
- Voice quiz grading
- Certificate PDF on completion

**NGO Coordinator Dashboard (Web):**
- Google SSO login
- Block-level SHG overview (active users, scheme interactions, ledger entries, meeting compliance)
- Export: CSV reports for DRDC submission
- Scheme uptake funnel visualization

### Milestone: M2 — "Growth Proven"
> 5,000 monthly active users. 500 government scheme applications tracked. First block-level Anandadhara integration. Series A funding deck ready.

---

## Phase 3 — Scale (Weeks 37–54)
**Theme: Network Effects, Market Intelligence, State-Level Deployment**

### Goals
- 50,000 monthly active users across West Bengal
- Market demand predictor live (requires critical mass of ledger data)
- Remaining 5 training tracks live
- Integration with WBSSP bank portal for direct loan application submission
- Offline-capable mode (SMS fallback for areas without WhatsApp/data)
- State government partnership formalized (MoU with West Bengal SHG & SE Dept.)

### Feature Releases

#### Release 3.0 (Weeks 37–42): Market Demand Predictor
- Anonymous sales data aggregation by block (from ledger data)
- Agmarknet API integration (real-time mandi prices)
- Festival and seasonal calendar demand signals
- Weekly demand report per user
- "Ki banabo ei mase?" (What should I make this month?) personalized query

#### Release 3.1 (Weeks 43–48): SMS Fallback + Accessibility
- USSD/SMS gateway for users without WhatsApp (partner: BSNL/Airtel for rural India)
- IVR fallback: users can call a number and interact entirely by voice (for feature phones)
- Compatibility mode: text-only flows for all features (for literacy-limited users on 2G)

#### Release 3.2 (Weeks 49–54): Bank Integration + Scale Infrastructure
- Direct WBSSP bank portal integration (API-level, pending MoU)
- Automated ledger data submission (user-consented) to partner bank for loan assessment
- Multi-language expansion: Santali, Odia (for border district SHGs)
- State dashboard: district collector + DRDC-level reporting
- Infrastructure scale-up: 100,000 concurrent users

### Milestone: M3 — "State Scale"
> 50,000 monthly active users. MoU signed with West Bengal government. Coverage in all 23 districts. Featured at national SHG conclave.

---

## Risk Register & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Bhashini API outage / rural Bengali WER too high | High | High | Self-hosted Whisper fallback; 500h fine-tuning dataset procurement starts in Month 1 |
| Meta WhatsApp WABA rejection or policy change | Medium | Critical | Gupshup as backup provider; terms of service review quarterly |
| Low user adoption (tech fear / distrust) | High | High | On-ground NGO partner for training; onboarding via existing SHG WhatsApp groups |
| RAG hallucination on scheme data | Medium | High | Strict grounding prompt; weekly human audit; no answer > no wrong answer policy |
| Government scheme document scraping blocked | Medium | Medium | Manual document update process + government partnership for direct data access |
| Data privacy breach | Low | Critical | VAPT before launch; no audio storage; UUID-only logs; external security audit |
| Agricultural diagnostic misidentification | Medium | High | Confidence threshold; mandatory KVK escalation; liability disclaimer; not a replacement for expert |
| Celery/Redis queue overload at scale | Medium | High | Auto-scaling; load testing to 10x expected load before each phase launch |

---

## Dependencies

| Dependency | Type | Owner | Risk |
|------------|------|-------|------|
| Bhashini API access (MeitY) | External API | Govt. of India | Medium — requires registration, has rate limits |
| Meta WABA Verification | External process | Meta | Medium — 2–4 week review process; start Week 1 |
| West Bengal scheme documents (official) | Content | State Govt. | Low — publicly available; scraper + manual ingestion |
| EfficientNet training dataset (crop diseases) | Data | ML team | Medium — PlantVillage available; WB-specific extension needed |
| NGO Partner (pilot user recruitment) | Partnership | Product | High — recruit 2 NGO partners by Week 6 |
| Partner bank validation (PDF acceptance) | Partnership | Business Dev | Medium — 1 bank partnership needed by Week 14 |
| West Bengal SHG & SE Dept. MoU | Partnership | Executive | Low for MVP; required for Scale phase |

---

## Definition of Done (Per Phase)

**Phase 0 Done:** Bot responds to Bengali voice and text messages in production with < 10s latency. Monitoring is live. CI/CD is automated.

**Phase 1 Done:** 200 pilot users have made at least 1 ledger entry. At least 1 bank loan application has used a Kotha-Khata PDF. Zero RAG hallucinations confirmed in 200-query audit.

**Phase 2 Done:** All 8 features are in production. 5,000 MAU. NGO dashboard live. First external press coverage.

**Phase 3 Done:** 50,000 MAU. Government partnership formalized. Market predictor demonstrably influences user product decisions (measured by follow-up survey).
