from __future__ import annotations

from datetime import date

# --- Gregorian months, Bengali script (already used across the codebase for
# bank-submittable PDF reports and ledger confirmations — moved here from
# services/pdf_service/generator.py and
# services/orchestrator/nodes/ledger_report_node.py, which previously
# duplicated this exact dict). This stays the PRIMARY/authoritative date
# representation everywhere — banks and government offices work off the
# Gregorian calendar, and nothing here changes that. ---
GREGORIAN_MONTHS_BENGALI = {
    1: "জানুয়ারি", 2: "ফেব্রুয়ারি", 3: "মার্চ", 4: "এপ্রিল", 5: "মে", 6: "জুন",
    7: "জুলাই", 8: "আগস্ট", 9: "সেপ্টেম্বর", 10: "অক্টোবর", 11: "নভেম্বর", 12: "ডিসেম্বর",
}

# --- The actual Bengali (Bangla / Bangabda) calendar — a SECONDARY, "local
# flavor" display alongside the Gregorian date, not a replacement for it.
# Many rural West Bengal SHG members think and speak in these month names
# day to day, even though formal paperwork uses the Gregorian calendar. ---
BANGLA_MONTHS = [
    "বৈশাখ", "জ্যৈষ্ঠ", "আষাঢ়", "শ্রাবণ", "ভাদ্র", "আশ্বিন",
    "কার্তিক", "অগ্রহায়ণ", "পৌষ", "মাঘ", "ফাল্গুন", "চৈত্র",
]

_BANGLA_ERA_OFFSET = 593  # Bangabda epoch offset from the Gregorian year
_POYLA_BOISHAKH_MONTH = 4
_POYLA_BOISHAKH_DAY = 14


def gregorian_to_bangla_approx(g_date: date) -> tuple[str, int, int]:
    """Converts a Gregorian date to an approximate (month_name, day, year)
    in the Bangla calendar.

    OPEN VERIFICATION ITEM, in the same spirit as this repo's other
    "best-effort, not verified against an authoritative live source" flags
    (Sarvam Vision's scope, Flux Pro's API shape): this uses a FIXED Poyla
    Boishakh (Bangla New Year) of Gregorian April 14 every year, matching
    the widely-used 1987 calendar reform convention. Traditional West
    Bengal panjikas (almanacs) are not uniformly fixed this way — different
    publishers can place the new year on April 14 or 15 depending on the
    year, based on older Surya Siddhanta-based calculations, and can
    disagree with each other and with this approximation by up to a day.
    Month lengths here are internally consistent (every day of the
    Gregorian year maps to exactly one Bangla calendar day, with the final
    month absorbing any leap-year drift) but the exact month-boundary date
    may differ by a day from a specific printed panjika.

    This is intentionally used ONLY as a secondary, clearly-labeled
    "traditional/approximate" reference in this codebase (PDF reports,
    confirmation messages) — the Gregorian date remains the authoritative
    one everywhere, including anything submitted to a bank or government
    office. Do not use this for any legal, scheme-eligibility, or
    date-sensitive financial calculation.
    """
    year = g_date.year
    this_years_new_year = date(year, _POYLA_BOISHAKH_MONTH, _POYLA_BOISHAKH_DAY)

    if g_date < this_years_new_year:
        new_year = date(year - 1, _POYLA_BOISHAKH_MONTH, _POYLA_BOISHAKH_DAY)
        bangla_year = year - 1 - _BANGLA_ERA_OFFSET
    else:
        new_year = this_years_new_year
        bangla_year = year - _BANGLA_ERA_OFFSET

    day_offset = (g_date - new_year).days  # 0-indexed day within the Bangla year

    next_new_year = date(new_year.year + 1, _POYLA_BOISHAKH_MONTH, _POYLA_BOISHAKH_DAY)
    total_days_this_bangla_year = (next_new_year - new_year).days

    month_lengths = [31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 30, 30]
    month_lengths[-1] = total_days_this_bangla_year - sum(month_lengths[:-1])

    remaining = day_offset
    for idx, length in enumerate(month_lengths):
        if remaining < length:
            return BANGLA_MONTHS[idx], remaining + 1, bangla_year
        remaining -= length

    # Should be unreachable given the total_days_this_bangla_year balancing
    # above, but never raise out of a display-only helper — degrade to the
    # last valid day of the last month rather than crash a PDF/report node.
    return BANGLA_MONTHS[-1], month_lengths[-1], bangla_year


def format_bangla_calendar_label(g_date: date) -> str:
    """e.g. 'শ্রাবণ ১৪৩৩ (আনুমানিক)' — the '(আনুমানিক)' = 'approximate' suffix
    is intentional and should not be dropped; see the verification note in
    gregorian_to_bangla_approx above."""
    month_name, _day, bangla_year = gregorian_to_bangla_approx(g_date)
    bangla_year_digits = _to_bengali_digits(bangla_year)
    return f"{month_name} {bangla_year_digits} (আনুমানিক)"


_BENGALI_DIGIT_MAP = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def _to_bengali_digits(value: int) -> str:
    return str(value).translate(_BENGALI_DIGIT_MAP)
