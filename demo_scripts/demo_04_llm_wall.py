"""
Demo 4 - The Wall: shows exactly where an API key becomes necessary
Run from repo root: python demo_scripts/demo_04_llm_wall.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.orchestrator.model_router import route_completion, TaskCriticality

SAMPLE_VOICE_TRANSCRIPT = "আজ ৩০০ টাকা পাপড় বিক্রি করেছি, ১০০ টাকা মশলা কিনেছি"

EXTRACTION_SYSTEM = (
    "তুমি বাংলা আর্থিক তথ্য নিষ্কাশনকারী। নিচের বাংলা টেক্সট থেকে\n"
    "লেনদেন বের করো এবং শুধুমাত্র এই JSON ফরম্যাটে ফেরত দাও, অন্য কিছু লিখো না:\n\n"
    '{"transactions": [{"type": "INCOME"|"EXPENSE", "amount_inr": <number>,\n'
    ' "item_bengali": "...", "quantity": <number|null>, "unit": "...|null"}],\n'
    ' "confidence": <0.0-1.0>}'
)


async def main():
    print("Transcript:", SAMPLE_VOICE_TRANSCRIPT)
    print("Extracting structured ledger entries...")

    try:
        result = await route_completion(
            system=EXTRACTION_SYSTEM,
            prompt=SAMPLE_VOICE_TRANSCRIPT,
            criticality=TaskCriticality.ROUTINE,
            confidence_floor=0.80,
        )
        print("Success. Model used:", result["model_used"])
        print("Result:", result["text"])
    except Exception as exc:
        print("Failed:", type(exc).__name__, "-", exc)
        print("This step needs an OpenAI API key. Everything else in the")
        print("pipeline (confirmation flow, DB write, PDF report) is already built.")


if __name__ == "__main__":
    asyncio.run(main())
