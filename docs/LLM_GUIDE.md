# Kotha-Kori (কথা-কড়ি): Zero-Cost LLM Architecture Guide
## Replacing Every Paid API with Self-Hosted + Fine-Tuned Models

---

## The Core Insight

Paid API costs at scale are catastrophic for a social-impact project:

| Component | Paid API | Cost at 150k msg/day | Zero-Cost Alternative | Daily Cost |
|-----------|----------|---------------------|----------------------|------------|
| LLM (NLU, RAG, Extraction) | Claude claude-sonnet-4-6 | ~₹35,000/day | Qwen2.5-7B (Ollama, self-hosted) | ₹0 |
| STT | Bhashini / paid API | ~₹8,000/day | fine-tuned Whisper (self-hosted) | ₹0 |
| Vision | GPT-4o | ~₹12,000/day | Qwen2-VL-7B (self-hosted) | ₹0 |
| Embeddings | OpenAI | ~₹2,000/day | nomic-embed-text (Ollama local) | ₹0 |
| **TOTAL** | | **~₹57,000/day** | **GPU server** | **~₹800/day** |

> At 150k messages/day: paid APIs = ₹57,000/day (~$680). Self-hosted GPU server = ₹800/day (~$10).
> Annual saving: **~₹2.07 crore**.

The only recurring cost becomes the GPU server rental — a fixed cost that doesn't scale with usage.

---

## The Complete Zero-Cost Stack

### Component 1: LLM — Qwen2.5-7B-Instruct (Fine-Tuned)

**Why Qwen2.5-7B:**
- Best-in-class Bengali language understanding among open models
- 7B parameters fits in 8GB VRAM (4-bit quantized via QLoRA)
- Instruction-following quality rivals GPT-3.5 on structured tasks
- Apache 2.0 license (commercial use allowed)
- Outperforms LLaMA 3.1-8B on non-English languages (MMLU multilingual benchmarks)

**What we fine-tune it for:**
```
Task 1: Bengali Financial NER
  Input:  "আজ ১৫ প্যাকেট পাপড় ৩০০ টাকায় বিক্রি, ১০০ টাকা মশলা কিনেছি"
  Output: {"transactions": [{"type": "INCOME", "amount": 300, ...}, ...]}

Task 2: Scheme Eligibility Reasoning  
  Input:  [Context chunks] + User's attributes
  Output: Bengali eligibility verdict + document checklist

Task 3: Meeting Minutes Extraction
  Input:  "আজ ৮ জন হাজির। প্রত্যেকে ৫০ টাকা দিয়েছেন। সিতাকে ৫০০ টাকা ঋণ।"
  Output: Structured meeting record JSON

Task 4: Dialectal Bengali Instruction Following
  Input:  Rural dialect voice transcript
  Output: Standard Bengali structured response

Task 5: Strict Anti-Hallucination Behaviour
  Fine-tune to output EXACTLY: "এ বিষয়ে নিশ্চিত তথ্য নেই।" when context is absent
```

**Fine-tuning method: QLoRA (Quantized Low-Rank Adaptation)**
```
Base model:     Qwen2.5-7B-Instruct (4-bit quantized)
LoRA rank:      16  (adds only ~8M trainable parameters)
Training data:  10,000 Bengali SHG domain examples (JSONL)
Hardware:       1x RTX 3090 (24GB VRAM) — RunPod ~₹1,700 one-time
Training time:  ~4 hours
Output:         GGUF Q4_K_M file (~4.3GB) → loaded by Ollama
Cost:           ₹1,700 one-time + ₹0 per inference forever
```

**How to build the fine-tuning dataset:**
```
Sources (all free):
1. Translate English SHG financial Q&A → Bengali (50% of dataset)
   Use: Helsinki-NLP/opus-mt-en-bn (free translation model)
   
2. Generate synthetic Bengali ledger entries using:
   gpt-4o-mini (one-time batch, ~₹1,500 for 5,000 examples)
   
3. Real pilot data (collect from 200 pilot users with consent)
   Week 6-18 pilot generates 5,000+ real Bengali voice transcripts
   
4. West Bengal government scheme documents (parse + reformat as Q&A)
   Script: scripts/generate_scheme_qa.py
```

**Serving via Ollama:**
```bash
# After fine-tuning:
ollama create kotha-khata-qwen -f ml/llm-finetune/Modelfile

# Test:
ollama run kotha-khata-qwen "আজ ৩০০ টাকা পাপড় বিক্রি করেছি"
# Expected: {"transactions": [{"type": "INCOME", "amount_inr": 300, "item": "papad"}]}
```

---

### Component 2: STT — Fine-Tuned Whisper Large v3

**Why Whisper:**
- OpenAI Whisper is open-source (MIT license)
- `faster-whisper` (CTranslate2 backend) runs 4x faster than original
- Bengali support built-in; fine-tuning adds rural dialect vocabulary
- Bhashini is kept as FALLBACK ONLY (free government API)

**Fine-tuning dataset for rural Bengali:**
```
Source 1: Mozilla Common Voice Bengali — 300+ hours (free, CC0)
  URL: https://commonvoice.mozilla.org/en/datasets
  
Source 2: FLEURS Bengali — 12 hours (Google, Apache 2.0)
  URL: huggingface.co/datasets/google/fleurs (bn_in split)
  
Source 3: IndicSUPERB Bengali — 40 hours (AI4Bharat, MIT)
  URL: huggingface.co/datasets/ai4bharat/IndicSUPERB
  
Source 4: Domain augmentation (you create):
  - Record SHG domain sentences via TTS (Bhashini TTS, free)
  - Sentences: financial amounts, product names, scheme names
  - Add noise augmentation (background sounds, low bitrate simulation)
  
Total: ~400h dataset — achieves ≥92% WER on rural Bengali
Fine-tuning time: ~8 hours on 1x RTX 3090
One-time cost: ~₹3,000 on RunPod
```

**Runtime: faster-whisper (not standard Whisper)**
```python
# 4x faster inference, same accuracy
from faster_whisper import WhisperModel
model = WhisperModel("./models/bengali-large-v3", device="cuda", compute_type="float16")
# Average RTF (real-time factor): 0.15x — a 30s audio transcribed in ~4.5s
```

---

### Component 3: Vision — Qwen2-VL-7B

**Why Qwen2-VL:**
- State-of-the-art open vision-language model (beats LLaVA-1.6 significantly)
- Bengali text generation after image analysis
- Handles: product recognition, crop disease identification, text in images
- 7B parameters, fits in 8GB VRAM at 4-bit

**Two vision tasks:**

**Task A: Catalog Creator**
```
No fine-tuning needed. Qwen2-VL-7B base model already:
- Identifies product type from photo
- Generates Bengali description
- Suggests price range (prompt-engineered from pricing table)

Prompt template:
"এই ছবিতে কী পণ্য দেখছ? পণ্যের বৈশিষ্ট্য বাংলায় বলো এবং
 একটা আকর্ষণীয় বিক্রির বার্তা লেখো। দাম: ₹X-₹Y।"
```

**Task B: Agri-Diagnostic**
```
Option A (recommended): EfficientNet-B4 fine-tuned classifier
  - Faster, lighter, more accurate on specific disease set
  - 15MB model vs 14GB vision model
  - Fine-tune on PlantVillage (54,306 images, 38 classes, free)
  - Add: West Bengal KVK disease photos (request via RTI or partnership)

Option B: Qwen2-VL-7B with vision prompt
  - Use for rare/unusual cases not in classifier training set
  - Fallback when EfficientNet confidence < 0.6
```

**How Qwen2-VL serves via Ollama:**
```bash
ollama pull qwen2-vl:7b-q4_K_M

# In Python:
response = httpx.post("http://ollama:11434/api/generate", json={
    "model": "qwen2-vl:7b-q4_K_M",
    "prompt": "এই পণ্যটি কী? বাংলায় বিক্রির বার্তা লেখো।",
    "images": [base64_image],  # Ollama supports base64 images
    "stream": False
})
```

---

### Component 4: Embeddings — nomic-embed-text (via Ollama)

**Why nomic-embed-text:**
- 768-dimensional embeddings (vs 1536 for OpenAI, half the storage)
- Multilingual support including Bengali
- Free, local, Apache 2.0
- Performance within 5% of OpenAI text-embedding-3-small on multilingual tasks
- Available via `ollama pull nomic-embed-text`

```python
# Usage — identical interface, zero cost
async def embed(text: str) -> list[float]:
    r = await httpx.post("http://ollama:11434/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": text})
    return r.json()["embedding"]  # 768-dim vector
```

**Note on pgvector:** Update schema to `vector(768)` instead of `vector(1536)`.

---

### Component 5: TTS (Optional) — Coqui TTS / Bhashini TTS

For voice responses (users who request audio output):

**Option A: Bhashini TTS (Free government API)**
```
- Free for Indian language TTS
- Bengali male + female voices available
- Latency: ~1-2 seconds
- Keep this for TTS — it's free and high quality
```

**Option B: Coqui TTS (Self-hosted)**
```
- Open source, MIT license
- Bengali VITS model available
- Run on CPU (TTS is not compute-heavy)
- docker run ghcr.io/coqui-ai/tts --model_name tts_models/bn/custom/vits
```

---

## Hardware Sizing Guide

### Minimum: Single GPU Server (Development / Small Pilot)

```
GPU:    RTX 3090 (24GB VRAM)
CPU:    8-core (Intel i7 or AMD Ryzen 7)
RAM:    32GB DDR4
Storage: 500GB NVMe SSD

VRAM allocation:
  Whisper large-v3 (faster-whisper):  ~3GB
  Qwen2.5-7B Q4_K_M (Ollama):        ~5GB
  Qwen2-VL-7B Q4_K_M (Ollama):       ~5GB  ← load on demand
  EfficientNet-B4:                    ~0.5GB
  nomic-embed-text (Ollama):          ~0.5GB
  Buffer:                             ~10GB
  TOTAL:                              ~24GB ✓

Capacity: ~3,000-5,000 messages/day
Cloud option: RunPod RTX 3090 — ~₹37/hour → ₹888/day
```

### Recommended: Two GPU Server (5,000-50,000 users)

```
GPU 1 (STT + EfficientNet):   RTX 3090 or A10G (24GB)
GPU 2 (LLM + Vision):         RTX 4090 or A100 (24GB/40GB)

OR: single A100 80GB (runs everything + headroom)

Cloud options:
  RunPod A100 80GB:  ~₹110/hour → ₹2,640/day
  Lambda Labs A100:  ~₹75/hour → ₹1,800/day
  Vast.ai (spot):    ~₹40-60/hour → ₹960-1,440/day

Capacity: 50,000-100,000 messages/day
```

### Production: Dedicated Server (100,000+ users)

```
Buy or lease: 4x A100 80GB NVMe server
Hosting: Yotta Data Centre (Mumbai) or CtrlS (Hyderabad)
Monthly: ~₹2-3 lakhs (vs ₹1.5+ crore on APIs)
```

---

## Model Quality vs. API Quality

Realistic assessment for this domain:

| Task | Paid API Accuracy | Fine-Tuned Open Model | Gap | Acceptable? |
|------|------------------|----------------------|-----|-------------|
| Bengali STT (rural) | ~94% (Bhashini) | ~92% (fine-tuned Whisper) | 2% | ✅ Yes |
| Financial NER | ~95% (Claude) | ~88-91% (fine-tuned Qwen) | 5-7% | ✅ Yes* |
| RAG scheme Q&A | ~97% (Claude) | ~88-92% (fine-tuned Qwen) | 7% | ✅ Yes* |
| Vision (product) | ~95% (GPT-4o) | ~85% (Qwen2-VL) | 10% | ✅ Yes |
| Agri diagnostic | ~88% (GPT-4o) | ~85% (EfficientNet) | 3% | ✅ Yes |

*The gap closes significantly with fine-tuning. Fine-tuned 7B on domain data often beats general 70B on that specific domain.

The remaining gap is mitigated by:
- Asking users to confirm before saving (ledger confirmation step)
- Fallback prompt: "একটু পরিষ্কার হলো না, আবার বলুন?"
- Scheme RAG has strict hallucination guard regardless of model

---

## Fine-Tuning Dataset Creation (Practical Steps)

### Step 1: Scheme Q&A Dataset (500 examples)
```python
# scripts/generate_scheme_qa.py
# Parse scheme PDFs → extract eligibility rules → generate Q&A pairs
# Cost: ₹0 (rule-based generation from official documents)
```

### Step 2: Financial NER Dataset (3,000 examples)
```python
# ml/llm-finetune/data/generate_ner_data.py
# Template: "X taka Y bikri" → generate 3,000 variations
# Amounts: 50-50,000 range, Bengali number words included
# Products: 50 common SHG product names in Bengali
# Cost: ₹0 (programmatic generation)
```

### Step 3: Meeting Minutes Dataset (500 examples)
```python
# Synthesize: X members, Y savings, Z loans in varied Bengali phrasing
# Cost: ₹0 (programmatic generation)
```

### Step 4: Real Data (from pilot)
```
During the 4-week pilot with 200 users:
- Collect (with consent): anonymized voice transcripts + correct extractions
- Human review: 2 Bengali-speaking volunteers review 1,000 samples
- This data is most valuable — real dialectal Bengali in domain context
- Feed back into fine-tuning cycle after pilot
```

---

## Deployment: Ollama in Production

```yaml
# docker-compose.yml (already included in project)
ollama:
  image: ollama/ollama:latest
  volumes:
    - ollama_models:/root/.ollama   # Models persist across restarts
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

```bash
# First-time model setup (run once):
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama create kotha-khata-qwen -f /app/ml/llm-finetune/Modelfile
docker compose exec ollama ollama create kotha-khata-vision -f /app/ml/vision-finetune/Modelfile

# Verify:
docker compose exec ollama ollama list
# NAME                         ID              SIZE   MODIFIED
# kotha-khata-qwen:latest      abc123...       4.3 GB  ...
# kotha-khata-vision:latest    def456...       4.8 GB  ...
# nomic-embed-text:latest      ghi789...       274 MB  ...
```

---

## Phased Migration Plan (API → Self-Hosted)

```
MVP Launch (Week 18):
  STT:        Bhashini (free API) + Whisper CPU fallback
  LLM:        Claude API (paid) — acceptable for 200 pilot users (~₹500/day)
  Vision:     GPT-4o (paid) — used rarely, acceptable
  Embeddings: OpenAI (paid) — small cost at low volume

Post-Pilot (Week 22-26):
  ← Fine-tune Whisper on pilot audio data
  ← Fine-tune Qwen on pilot extraction data
  STT:        Switch to self-hosted fine-tuned Whisper
  LLM:        Switch to self-hosted Qwen2.5-7B
  Embeddings: Switch to nomic-embed-text via Ollama

Growth Phase (Week 30+):
  Vision:     Switch to self-hosted Qwen2-VL + EfficientNet
  TOTAL API COST: ₹0/day (only GPU server cost)
```

This phased approach means you launch fast with paid APIs while building data,
then migrate to zero-cost as you validate quality with real users.
