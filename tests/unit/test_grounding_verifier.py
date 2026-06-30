"""
A good first task for a new intern: read this test, then add 3-4 more
cases covering things this simple regex-based verifier *doesn't* catch yet
(e.g. a number that's grounded but attached to the wrong scheme name —
see docs/research/agent_frameworks.md's note on "citation-shaped
hallucinations" for what a stronger version of this check should look for).
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from services.rag_service.grounding_verifier import verify_grounding


def test_grounded_amount_passes():
    chunks = [{"chunk_bengali": "লক্ষ্মীর ভান্ডারে প্রতি মাসে ₹1000 দেওয়া হয়।"}]
    answer = "আপনি প্রতি মাসে ₹1000 পাবেন।"
    result = verify_grounding(answer, chunks)
    assert result["all_grounded"] is True
    assert result["ungrounded"] == []


def test_fabricated_amount_is_caught():
    chunks = [{"chunk_bengali": "লক্ষ্মীর ভান্ডারে প্রতি মাসে ₹1000 দেওয়া হয়।"}]
    # Model hallucinated a different amount than what's in the retrieved chunk.
    answer = "আপনি প্রতি মাসে ₹2500 পাবেন।"
    result = verify_grounding(answer, chunks)
    assert result["all_grounded"] is False
    assert "₹2500" in result["ungrounded"]


def test_no_chunks_means_no_assertions_can_be_grounded():
    answer = "আপনি প্রতি মাসে ₹1000 পাবেন।"
    result = verify_grounding(answer, retrieved_chunks=[])
    assert result["all_grounded"] is False


def test_answer_with_no_numeric_claims_passes_trivially():
    chunks = [{"chunk_bengali": "এই প্রকল্পের জন্য পঞ্চায়েত অফিসে যোগাযোগ করুন।"}]
    answer = "পঞ্চায়েত অফিসে যোগাযোগ করুন।"
    result = verify_grounding(answer, chunks)
    assert result["all_grounded"] is True
    assert result["assertions"] == []
