from __future__ import annotations

from datetime import date

GREGORIAN_MONTHS_BENGALI = {
    1: "জানুয়ারি", 2: "ফেব্রুয়ারি", 3: "মার্চ", 4: "এপ্রিল", 5: "মে", 6: "জুন",
    7: "জুলাই", 8: "আগস্ট", 9: "সেপ্টেম্বর", 10: "অক্টোবর", 11: "নভেম্বর", 12: "ডিসেম্বর",
}

BANGLA_MONTHS = [
    "বৈশাখ", "জ্যৈষ্ঠ", "আষাঢ়", "শ্রাবণ", "ভাদ্র", "আশ্বিন",
    "কার্তিক", "অগ্রহায়ণ", "পৌষ", "মাঘ", "ফাল্গুন", "চৈত্র",
]

_BANGLA_ERA_OFFSET = 593
_POYLA_BOISHAKH_MONTH = 4
_POYLA_BOISHAKH_DAY = 14


def gregorian_to_bangla_approx(g_date: date) -> tuple[str, int, int]:
    year = g_date.year
    this_years_new_year = date(year, _POYLA_BOISHAKH_MONTH, _POYLA_BOISHAKH_DAY)

    if g_date < this_years_new_year:
        new_year = date(year - 1, _POYLA_BOISHAKH_MONTH, _POYLA_BOISHAKH_DAY)
        bangla_year = year - 1 - _BANGLA_ERA_OFFSET
    else:
        new_year = this_years_new_year
        bangla_year = year - _BANGLA_ERA_OFFSET

    day_offset = (g_date - new_year).days  

    next_new_year = date(new_year.year + 1, _POYLA_BOISHAKH_MONTH, _POYLA_BOISHAKH_DAY)
    total_days_this_bangla_year = (next_new_year - new_year).days

    month_lengths = [31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 30, 30]
    month_lengths[-1] = total_days_this_bangla_year - sum(month_lengths[:-1])

    remaining = day_offset
    for idx, length in enumerate(month_lengths):
        if remaining < length:
            return BANGLA_MONTHS[idx], remaining + 1, bangla_year
        remaining -= length

    return BANGLA_MONTHS[-1], month_lengths[-1], bangla_year


def format_bangla_calendar_label(g_date: date) -> str:
    month_name, _day, bangla_year = gregorian_to_bangla_approx(g_date)
    bangla_year_digits = _to_bengali_digits(bangla_year)
    return f"{month_name} {bangla_year_digits} (আনুমানিক)"


_BENGALI_DIGIT_MAP = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def _to_bengali_digits(value: int) -> str:
    return str(value).translate(_BENGALI_DIGIT_MAP)
