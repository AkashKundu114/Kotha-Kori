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

def test_right_amount_wrong_scheme_is_caught():

    chunks = [
        {"scheme_name": "Lakshmir Bhandar", "chunk_bengali": "লক্ষ্মীর ভান্ডারে প্রতি মাসে ₹1000 দেওয়া হয়।"},
        {"scheme_name": "JAAGO", "chunk_bengali": "জাগো প্রকল্পে বছরে ₹2500 সহায়তা দেওয়া হয়।"},
    ]
    answer = "লক্ষ্মীর ভান্ডার থেকে আপনি প্রতি মাসে ₹2500 পাবেন।"
    result = verify_grounding(answer, chunks)
    assert result["all_grounded"] is False
    assert "₹2500" in result["ungrounded"]

def test_right_amount_right_scheme_passes():

    chunks = [
        {"scheme_name": "Lakshmir Bhandar", "chunk_bengali": "লক্ষ্মীর ভান্ডারে প্রতি মাসে ₹1000 দেওয়া হয়।"},
        {"scheme_name": "JAAGO", "chunk_bengali": "জাগো প্রকল্পে বছরে ₹2500 সহায়তা দেওয়া হয়।"},
    ]
    answer = "জাগো প্রকল্প থেকে আপনি বছরে ₹2500 পাবেন।"
    result = verify_grounding(answer, chunks)
    assert result["all_grounded"] is True
    assert result["ungrounded"] == []

def test_unattributed_amount_still_falls_back_to_any_chunk():

    chunks = [
        {"scheme_name": "Lakshmir Bhandar", "chunk_bengali": "প্রতি মাসে ₹1000 দেওয়া হয়।"},
    ]
    answer = "আপনি প্রতি মাসে ₹1000 পাবেন।"
    result = verify_grounding(answer, chunks)
    assert result["all_grounded"] is True

def test_two_correct_assertions_for_two_different_schemes_in_one_answer():

    chunks = [
        {"scheme_name": "Lakshmir Bhandar", "chunk_bengali": "লক্ষ্মীর ভান্ডারে প্রতি মাসে ₹1000 দেওয়া হয়।"},
        {"scheme_name": "JAAGO", "chunk_bengali": "জাগো প্রকল্পে বছরে ₹2500 সহায়তা দেওয়া হয়।"},
    ]
    answer = "লক্ষ্মীর ভান্ডার দেয় ₹1000 প্রতি মাসে, আর জাগো দেয় ₹2500 বছরে।"
    result = verify_grounding(answer, chunks)
    assert result["all_grounded"] is True

def test_swapped_amounts_across_two_schemes_is_caught():

    chunks = [
        {"scheme_name": "Lakshmir Bhandar", "chunk_bengali": "লক্ষ্মীর ভান্ডারে প্রতি মাসে ₹1000 দেওয়া হয়।"},
        {"scheme_name": "JAAGO", "chunk_bengali": "জাগো প্রকল্পে বছরে ₹2500 সহায়তা দেওয়া হয়।"},
    ]
    answer = "লক্ষ্মীর ভান্ডার দেয় ₹2500 প্রতি মাসে, আর জাগো দেয় ₹1000 বছরে।"
    result = verify_grounding(answer, chunks)
    assert result["all_grounded"] is False
    assert set(result["ungrounded"]) == {"₹2500", "₹1000"}

def test_word_form_amount_is_caught_when_not_grounded():
    chunks = [{"chunk_bengali": "লক্ষ্মীর ভান্ডারে প্রতি মাসে ₹1000 দেওয়া হয়।"}]
    answer = "লক্ষ্মীর ভান্ডার থেকে আপনি এক হাজার টাকা পাবেন।"
    result = verify_grounding(answer, chunks)
    assert result["all_grounded"] is False
    assert "এক হাজার টাকা" in result["ungrounded"]
