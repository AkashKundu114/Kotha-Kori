"""
Demo 1 - Grounding Verifier
No API key needed.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.rag_service.grounding_verifier import verify_grounding


def show(title, answer, chunks):
    print(title)
    print("Answer:", answer)
    result = verify_grounding(answer, chunks)
    print("All grounded:", result["all_grounded"])
    if result["ungrounded"]:
        print("Flagged as ungrounded:", result["ungrounded"])
    print()


chunks = [
    {"scheme_name": "Lakshmir Bhandar", "chunk_bengali": "লক্ষ্মীর ভান্ডারে প্রতি মাসে ₹1000 দেওয়া হয়।"},
    {"scheme_name": "JAAGO", "chunk_bengali": "জাগো প্রকল্পে বছরে ₹2500 সহায়তা দেওয়া হয়।"},
]

show(
    "Case 1: Correct answer",
    "লক্ষ্মীর ভান্ডার থেকে আপনি প্রতি মাসে ₹1000 পাবেন।",
    chunks,
)

show(
    "Case 2: Right number, wrong scheme (the bug this fix catches)",
    "লক্ষ্মীর ভান্ডার থেকে আপনি প্রতি মাসে ₹2500 পাবেন।",
    chunks,
)

show(
    "Case 3: Hallucinated amount written as words instead of digits",
    "লক্ষ্মীর ভান্ডার থেকে আপনি এক হাজার টাকা পাবেন।",
    [{"scheme_name": "Lakshmir Bhandar", "chunk_bengali": "লক্ষ্মীর ভান্ডারে প্রতি মাসে ₹1000 দেওয়া হয়।"}],
)
