import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from services.orchestrator.nodes.ledger_node import _looks_code_mixed


def test_pure_bengali_not_flagged():
    assert _looks_code_mixed("আজ তিনশো টাকা পাপড় বিক্রি করেছি") is False


def test_pure_english_is_flagged():
    assert _looks_code_mixed("today I sold 300 taka papad") is True


def test_banglish_code_mixed_is_flagged():
    assert _looks_code_mixed("500 taka bikri hoise aaj papad theke") is True


def test_too_short_text_not_flagged():
    assert _looks_code_mixed("ok") is False


def test_mostly_bengali_with_one_english_word_not_flagged():
    assert _looks_code_mixed("আজ papad বিক্রি করেছি তিনশো টাকায়") is False
