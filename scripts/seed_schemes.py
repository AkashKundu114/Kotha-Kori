"""
Ingests government scheme PDFs into RAG vector store.
Usage: python scripts/seed_schemes.py
"""
# Implementation: parse PDFs from data/schemes/raw/
# Chunk into 512-token segments
# Embed with nomic-embed-text
# Store in scheme_chunks table with pgvector
print("Seed schemes script — implement with PDF parsing + Ollama embeddings")
