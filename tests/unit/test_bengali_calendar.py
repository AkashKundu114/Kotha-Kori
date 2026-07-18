import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared.i18n.bengali_calendar import (
    gregorian_to_bangla_approx,
    format_bangla_calendar_label,
    BANGLA_MONTHS,
    GREGORIAN_MONTHS_BENGALI,
)


def test_gregorian_months_dict_has_all_twelve():
    assert len(GREGORIAN_MONTHS_BENGALI) == 12
    assert GREGORIAN_MONTHS_BENGALI[1] == "জানুয়ারি"
    assert GREGORIAN_MONTHS_BENGALI[12] == "ডিসেম্বর"


def test_bangla_months_list_has_twelve_entries():
    assert len(BANGLA_MONTHS) == 12
    assert BANGLA_MONTHS[0] == "বৈশাখ"
    assert BANGLA_MONTHS[-1] == "চৈত্র"


def test_new_year_boundary_transitions_correctly():
    day_before = gregorian_to_bangla_approx(date(2026, 4, 13))
    new_year_day = gregorian_to_bangla_approx(date(2026, 4, 14))
    assert day_before[0] == "চৈত্র"
    assert new_year_day[0] == "বৈশাখ"
    assert new_year_day[1] == 1
    assert new_year_day[2] == day_before[2] + 1


def test_result_is_always_structurally_valid_across_a_four_year_span_including_a_leap_year():
    d = date(2025, 1, 1)
    end = date(2028, 12, 31)
    while d <= end:
        month_name, day, bangla_year = gregorian_to_bangla_approx(d)
        assert month_name in BANGLA_MONTHS
        assert 1 <= day <= 31
        assert bangla_year > 1400
        d += timedelta(days=1)


def test_bangla_year_matches_well_known_public_mapping():



    _, _, bangla_year = gregorian_to_bangla_approx(date(2026, 7, 12))
    assert bangla_year == 1433


def test_format_bangla_calendar_label_includes_approximation_marker():
    label = format_bangla_calendar_label(date(2026, 7, 12))
    assert "আনুমানিক" in label
    assert any(month in label for month in BANGLA_MONTHS)


def test_leap_year_day_does_not_crash():

    result = gregorian_to_bangla_approx(date(2028, 2, 29))
    assert result[0] in BANGLA_MONTHS
