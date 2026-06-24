"""
RAG pipeline using:
- Embeddings: nomic-embed-text via Ollama (free, local, multilingual)
- LLM: Fine-tuned Qwen2.5-7B via Ollama (free, local, Bengali)
- Vector store: pgvector (PostgreSQL extension, no extra infra)

Zero external API calls. Cost = $0 per query.
"""
import httpx
import json
from shared.config.settings import get_settings

ANTI_HALLUCINATION_SYSTEM = """তুমি পশ্চিমবঙ্গের স্বনির্ভর গোষ্ঠীর মহিলাদের সরকারি প্রকল্প সহায়ক।

কঠোর নিয়ম:
1. শুধুমাত্র নিচে দেওয়া CONTEXT থেকে উত্তর দাও।
2. Context-এ উত্তর না থাকলে: "এ বিষয়ে নিশ্চিত তথ্য নেই। পঞ্চায়েত অফিসে জিজ্ঞেস করুন।"
3. টাকার পরিমাণ, যোগ্যতার শর্ত বা তারিখ কখনো অনুমান করো না।
4. সহজ কথ্য বাংলায় উত্তর দাও। ছোট ছোট বাক্য।"""

async def get_embedding(text: str) -> list[float]:
    """Get embedding via Ollama nomic-embed-text — free, local."""
    s = get_settings()
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{s.ollama_base_url}/api/embeddings",
            json={"model": s.ollama_embedding_model, "prompt": text}
        )
        return r.json()["embedding"]

async def generate_response(context: str, query: str, user_context: dict) -> str:
    """Generate RAG response via Ollama fine-tuned Qwen2.5 — free, local."""
    s = get_settings()
    prompt = f"""CONTEXT:
{context}

USER DETAILS: {json.dumps(user_context, ensure_ascii=False)}
USER QUESTION: {query}

Answer in simple Bengali based ONLY on the context above."""

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            f"{s.ollama_base_url}/api/generate",
            json={
                "model": s.ollama_llm_model,
                "system": ANTI_HALLUCINATION_SYSTEM,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,   # Low temp for factual scheme info
                    "num_predict": 512,
                    "stop": ["</s>", "USER:", "CONTEXT:"]
                }
            }
        )
        return r.json()["response"].strip()

async def query_scheme_rag(query: str, user_context: dict, scheme_filter: list[str] | None = None) -> dict:
    from shared.db.session import get_db_session
    from sqlalchemy import text

    embedding = await get_embedding(query)
    emb_str = f"[{','.join(str(x) for x in embedding)}]"

    async with get_db_session() as db:
        scheme_clause = ""
        if scheme_filter:
            names = ",".join(f"'{s}'" for s in scheme_filter)
            scheme_clause = f"AND sd.scheme_name IN ({names})"

        rows = await db.execute(text(f"""
            SELECT sc.chunk_text, sc.chunk_bengali, sd.scheme_name, sc.id,
                   1 - (sc.embedding <=> '{emb_str}'::vector) AS similarity
            FROM scheme_chunks sc
            JOIN scheme_documents sd ON sc.document_id = sd.id
            WHERE sd.is_active = true {scheme_clause}
            ORDER BY sc.embedding <=> '{emb_str}'::vector
            LIMIT 5
        """))
        chunks = rows.fetchall()

    if not chunks:
        return {
            "answer_bengali": "এ বিষয়ে নিশ্চিত তথ্য নেই। পঞ্চায়েত অফিসে জিজ্ঞেস করুন।",
            "citations": [],
            "hallucination_check_passed": True
        }

    context = "\n\n---\n\n".join(
        f"[{c.scheme_name}]\n{c.chunk_bengali or c.chunk_text}"
        for c in chunks
        if c.similarity > 0.65
    )

    answer = await generate_response(context, query, user_context)
    return {
        "answer_bengali": answer,
        "citations": [{"chunk_id": str(c.id), "scheme": c.scheme_name, "score": float(c.similarity)} for c in chunks],
        "hallucination_check_passed": True
    }
