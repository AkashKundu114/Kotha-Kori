from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

RAW_DIR = Path("data/schemes/raw")
MANIFEST_PATH = RAW_DIR / "manifest.json"
CHUNK_CHARS = 800
CHUNK_OVERLAP_CHARS = 100


def _load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        print(f"No manifest found at {MANIFEST_PATH}.")
        print("Add manifest.json with scheme_name, optional scheme_code, document_type, source_url, and source_language.")
        sys.exit(1)
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _extract_pdf_text(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        print("pypdf is not installed. Run: pip install -r requirements.txt")
        sys.exit(1)
    reader = PdfReader(str(pdf_path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()


def _chunk_text(text: str, chunk_chars: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_chars, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = end - overlap
    return chunks


async def _seed_one_pdf(pdf_path: Path, meta: dict) -> dict:
    from sqlalchemy import text as sql_text
    from services.rag_service.pipeline import get_embedding
    from shared.db.session import get_db_session

    full_text = _extract_pdf_text(pdf_path)
    chunks = _chunk_text(full_text)
    if not chunks:
        return {"file": pdf_path.name, "status": "no_extractable_text", "chunks": 0}

    async with get_db_session() as db:
        doc_id_row = (
            await db.execute(
                sql_text(
                    """
                    INSERT INTO scheme_documents
                      (scheme_name, scheme_code, document_type, content_english,
                       source_url, source_file, last_verified_at, is_active)
                    VALUES (:scheme_name, :scheme_code, :document_type, :content_english,
                            :source_url, :source_file, NOW(), TRUE)
                    RETURNING id
                    """
                ),
                {
                    "scheme_name": meta["scheme_name"],
                    "scheme_code": meta.get("scheme_code"),
                    "document_type": meta.get("document_type"),
                    "content_english": full_text[:5000],
                    "source_url": meta.get("source_url"),
                    "source_file": pdf_path.name,
                },
            )
        ).fetchone()
        document_id = doc_id_row[0]

        for idx, chunk in enumerate(chunks):
            embedding = await get_embedding(chunk)
            emb_str = f"[{','.join(str(value) for value in embedding)}]"
            await db.execute(
                sql_text(
                    """
                    INSERT INTO scheme_chunks (document_id, chunk_text, chunk_bengali, embedding, chunk_index)
                    VALUES (:document_id, :chunk_text, :chunk_bengali, :embedding, :chunk_index)
                    """
                ),
                {
                    "document_id": str(document_id),
                    "chunk_text": chunk,
                    "chunk_bengali": chunk if meta.get("source_language") == "bengali" else None,
                    "embedding": emb_str,
                    "chunk_index": idx,
                },
            )
        await db.commit()

    return {"file": pdf_path.name, "status": "seeded", "chunks": len(chunks), "scheme_name": meta["scheme_name"]}


async def main() -> None:
    manifest = _load_manifest()
    pdfs = sorted(RAW_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {RAW_DIR}.")
        return

    results = []
    for pdf_path in pdfs:
        meta = manifest.get(pdf_path.name)
        if not meta or "scheme_name" not in meta:
            print(f"Skipping {pdf_path.name}: missing manifest entry or scheme_name.")
            results.append({"file": pdf_path.name, "status": "skipped_bad_manifest", "chunks": 0})
            continue
        print(f"Processing {pdf_path.name} ({meta['scheme_name']})...")
        try:
            result = await _seed_one_pdf(pdf_path, meta)
        except Exception as exc:
            print(f"Failed on {pdf_path.name}: {exc}")
            result = {"file": pdf_path.name, "status": f"error: {exc}", "chunks": 0}
        results.append(result)

    print("SEEDING SUMMARY")
    total_chunks = 0
    for result in results:
        print(f"{result['file']}: {result['status']} ({result['chunks']} chunks)")
        total_chunks += result["chunks"]
    print(f"Total chunks written: {total_chunks}")


if __name__ == "__main__":
    asyncio.run(main())
