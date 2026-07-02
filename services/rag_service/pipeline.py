import json

import httpx
from sqlalchemy import text

from shared.config.settings import get_settings

ANTI_HALLUCINATION_SYSTEM = (
    "তুমি পশ্চিমবঙ্গের স্বনির্ভর গোষ্ঠীর মহিলাদের সরকারি প্রকল্প সহায়ক।\n\n"
    "কঠোর নিয়ম:\n"
    "1. শুধুমাত্র নিচে দেওয়া CONTEXT থেকে উত্তর দাও।\n"
    "2. Context-এ উত্তর না থাকলে: \"এ বিষয়ে নিশ্চিত তথ্য নেই। পঞ্চায়েত অফিসে জিজ্ঞেস করুন।\"\n"
    "3. টাকার পরিমাণ, যোগ্যতার শর্ত বা তারিখ কখনো অনুমান করো না।\n"
    "4. সহজ কথ্য বাংলায় উত্তর দাও। ছোট ছোট বাক্য।\n"
    "5. প্রতিটি তথ্যের সাথে কোন প্রকল্পের নথি থেকে নেওয়া তা উল্লেখ করো।"
)

async def get_embedding(text_input: str) -> list[float]:
    s = get_settings()
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{s.ollama_base_url}/api/embeddings",
            json={"model": s.ollama_embedding_model, "prompt": text_input},
        )
        return r.json()["embedding"]

def _reciprocal_rank_fusion(vector_rows: list, fts_rows: list, k: int = 60, top_n: int = 5) -> list[dict]:

    scores: dict[str, float] = {}
    rows_by_id: dict[str, dict] = {}

    for rank, row in enumerate(vector_rows):
        scores[row.id] = scores.get(row.id, 0.0) + 1.0 / (k + rank + 1)
        rows_by_id[row.id] = dict(row._mapping)

    for rank, row in enumerate(fts_rows):
        scores[row.id] = scores.get(row.id, 0.0) + 1.0 / (k + rank + 1)
        rows_by_id.setdefault(row.id, dict(row._mapping))

    ranked_ids = sorted(scores, key=scores.get, reverse=True)[:top_n]
    return [rows_by_id[i] for i in ranked_ids]

async def query_scheme_rag(query: str, user_context: dict, scheme_filter: list[str] | None = None) -> dict:
    from shared.db.session import get_db_session

    embedding = await get_embedding(query)
    emb_str = f"[{','.join(str(x) for x in embedding)}]"
    scheme_clause = ""
    params: dict = {"q": query}
    if scheme_filter:
        scheme_clause = "AND sd.scheme_name = ANY(:schemes)"
        params["schemes"] = scheme_filter

    async with get_db_session() as db:
        vector_rows = (
            await db.execute(
                text(
                    f"\n"
                    f"                SELECT sc.id, sc.chunk_text, sc.chunk_bengali, sd.scheme_name,\n"
                    f"                       1 - (sc.embedding <=> '{emb_str}'::vector) AS similarity\n"
                    f"                FROM scheme_chunks sc\n"
                    f"                JOIN scheme_documents sd ON sc.document_id = sd.id\n"
                    f"                WHERE sd.is_active = true {scheme_clause}\n"
                    f"                ORDER BY sc.embedding <=> '{emb_str}'::vector\n"
                    f"                LIMIT 10\n"
                    f"            "
                ),
                params,
            )
        ).fetchall()

        fts_rows = (
            await db.execute(
                text(
                    f"\n"
                    f"                SELECT sc.id, sc.chunk_text, sc.chunk_bengali, sd.scheme_name,\n"
                    f"                       ts_rank(sc.chunk_bengali_tsv, plainto_tsquery('simple', :q)) AS rank\n"
                    f"                FROM scheme_chunks sc\n"
                    f"                JOIN scheme_documents sd ON sc.document_id = sd.id\n"
                    f"                WHERE sd.is_active = true {scheme_clause}\n"
                    f"                  AND sc.chunk_bengali_tsv @@ plainto_tsquery('simple', :q)\n"
                    f"                ORDER BY rank DESC\n"
                    f"                LIMIT 10\n"
                    f"            "
                ),
                params,
            )
        ).fetchall()

    merged = _reciprocal_rank_fusion(vector_rows, fts_rows)

    if not merged:
        fallback = "এ বিষয়ে নিশ্চিত তথ্য নেই। পঞ্চায়েত অফিসে জিজ্ঞেস করুন।"
        return {"answer_bengali": fallback, "citations_full": []}

    context = "\n\n---\n\n".join(f"[{c['scheme_name']}]\n{c.get('chunk_bengali') or c['chunk_text']}" for c in merged)

    answer = await _generate(context, query, user_context)
    return {"answer_bengali": answer, "citations_full": merged}

async def _generate(context: str, query: str, user_context: dict) -> str:

    from services.orchestrator.model_router import route_completion, TaskCriticality

    prompt = (
        f"CONTEXT:\n{context}\n\n"
        f"USER DETAILS: {json.dumps(user_context, ensure_ascii=False)}\n"
        f"USER QUESTION: {query}\n\n"
        "Answer in simple Bengali based ONLY on the context above."
    )

    result = await route_completion(
        system=ANTI_HALLUCINATION_SYSTEM, prompt=prompt, criticality=TaskCriticality.SAFETY_CRITICAL
    )
    return result["text"]
