"""
Originally: "A good first task for a new intern: read this test, then add
3-4 more cases covering things this simple regex-based verifier *doesn't*
catch yet (e.g. a number that's grounded but attached to the wrong scheme
name — see docs/research/agent_frameworks.md's note on "citation-shaped
hallucinations" for what a stronger version of this check should look for)."

Day 4-5 update: that gap is now closed in services/rag_service/grounding_verifier.py
(per-chunk grounding + scheme-name matching, see the module docstring there
for the "before/after" explanation). The tests below cover the original
behaviour plus the new wrong-scheme case and a few adjacent edge cases.
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


# ─── New cases (Day 4-5, Option A) ──────────────────────────────────────

def test_right_amount_wrong_scheme_is_caught():
    """
    Citation-shaped hallucination: ₹2500 is a real figure present in the
    retrieved context, but it belongs to JAAGO's chunk, not Lakshmir
    Bhandar's. The pre-fix verifier concatenated all chunks before
    searching, so this slipped through as "grounded" even though no
    Lakshmir Bhandar chunk actually supports ₹2500.
    """
    chunks = [
        {"scheme_name": "Lakshmir Bhandar", "chunk_bengali": "লক্ষ্মীর ভান্ডারে প্রতি মাসে ₹1000 দেওয়া হয়।"},
        {"scheme_name": "JAAGO", "chunk_bengali": "জাগো প্রকল্পে বছরে ₹2500 সহায়তা দেওয়া হয়।"},
    ]
    answer = "লক্ষ্মীর ভান্ডার থেকে আপনি প্রতি মাসে ₹2500 পাবেন।"
    result = verify_grounding(answer, chunks)
    assert result["all_grounded"] is False
    assert "₹2500" in result["ungrounded"]


def test_right_amount_right_scheme_passes():
    """Same two chunks, but the answer correctly attributes ₹2500 to JAAGO."""
    chunks = [
        {"scheme_name": "Lakshmir Bhandar", "chunk_bengali": "লক্ষ্মীর ভান্ডারে প্রতি মাসে ₹1000 দেওয়া হয়।"},
        {"scheme_name": "JAAGO", "chunk_bengali": "জাগো প্রকল্পে বছরে ₹2500 সহায়তা দেওয়া হয়।"},
    ]
    answer = "জাগো প্রকল্প থেকে আপনি বছরে ₹2500 পাবেন।"
    result = verify_grounding(answer, chunks)
    assert result["all_grounded"] is True
    assert result["ungrounded"] == []


def test_unattributed_amount_still_falls_back_to_any_chunk():
    """
    If the answer doesn't name a scheme near the figure at all, we can't
    know which scheme it's claiming, so we keep the old (lenient) behaviour:
    grounded if found in *any* retrieved chunk. This keeps the verifier from
    becoming so strict that short, scheme-less answers always fail.
    """
    chunks = [
        {"scheme_name": "Lakshmir Bhandar", "chunk_bengali": "প্রতি মাসে ₹1000 দেওয়া হয়।"},
    ]
    answer = "আপনি প্রতি মাসে ₹1000 পাবেন।"
    result = verify_grounding(answer, chunks)
    assert result["all_grounded"] is True


def test_two_correct_assertions_for_two_different_schemes_in_one_answer():
    """
    A multi-scheme comparison answer should ground each figure against its
    own scheme independently, not just "somewhere in the combined context."
    """
    chunks = [
        {"scheme_name": "Lakshmir Bhandar", "chunk_bengali": "লক্ষ্মীর ভান্ডারে প্রতি মাসে ₹1000 দেওয়া হয়।"},
        {"scheme_name": "JAAGO", "chunk_bengali": "জাগো প্রকল্পে বছরে ₹2500 সহায়তা দেওয়া হয়।"},
    ]
    answer = "লক্ষ্মীর ভান্ডার দেয় ₹1000 প্রতি মাসে, আর জাগো দেয় ₹2500 বছরে।"
    result = verify_grounding(answer, chunks)
    assert result["all_grounded"] is True


def test_swapped_amounts_across_two_schemes_is_caught():
    """The hard case: both amounts are real, retrieved figures — just swapped."""
    chunks = [
        {"scheme_name": "Lakshmir Bhandar", "chunk_bengali": "লক্ষ্মীর ভান্ডারে প্রতি মাসে ₹1000 দেওয়া হয়।"},
        {"scheme_name": "JAAGO", "chunk_bengali": "জাগো প্রকল্পে বছরে ₹2500 সহায়তা দেওয়া হয়।"},
    ]
    answer = "লক্ষ্মীর ভান্ডার দেয় ₹2500 প্রতি মাসে, আর জাগো দেয় ₹1000 বছরে।"
    result = verify_grounding(answer, chunks)
    assert result["all_grounded"] is False
    assert set(result["ungrounded"]) == {"₹2500", "₹1000"}
