from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CropSeason:
    slug: str
    name_bengali: str
    name_english: str
    main_districts: list[str]
    sowing_months: list[int]
    harvest_months: list[int]
    note_bengali: str
    source_note: str = ""


CROP_CALENDAR: list[CropSeason] = [
    CropSeason(
        "aman_paddy",
        "আমন ধান",
        "Aman paddy",
        ["Nadia", "Bardhaman", "Birbhum", "Hooghly"],
        [6, 7, 8],
        [11, 12],
        "নভেম্বর-ডিসেম্বরে কাটা হয়, তখন চালের সরবরাহ বাড়ে এবং দাম তুলনামূলক কম থাকতে পারে।",
    ),
    CropSeason(
        "boro_paddy",
        "বোরো ধান",
        "Boro paddy",
        ["Bardhaman", "Birbhum"],
        [11, 12, 1],
        [4, 5],
        "এপ্রিল-মে মাসে কাটা হয়, গ্রীষ্মের আগে চালের সরবরাহ বাড়ে।",
    ),
    CropSeason(
        "aus_paddy",
        "আউশ ধান",
        "Aus paddy",
        ["Nadia", "Murshidabad"],
        [4, 5],
        [7, 8],
        "বর্ষার আগে বোনা, বর্ষার মধ্যে কাটা হয়।",
    ),
    CropSeason(
        "jute",
        "পাট",
        "Jute",
        ["Nadia", "Murshidabad", "North 24 Parganas"],
        [3, 4],
        [7, 8, 9],
        "বর্ষায় কাটা ও জাগ দেওয়া হয়, তারপর পাটের সরবরাহ বাড়ে।",
    ),
    CropSeason(
        "potato",
        "আলু",
        "Potato",
        ["Hooghly", "Bardhaman", "Paschim Medinipur"],
        [10, 11],
        [1, 2, 3],
        "জানুয়ারি-মার্চে তোলা হয়, তখন কাঁচামাল হিসেবে আলু কেনা সস্তা হতে পারে।",
    ),
    CropSeason(
        "mustard",
        "সরিষা",
        "Mustard",
        ["Bankura", "Purulia", "Murshidabad"],
        [10, 11],
        [2, 3],
        "ফেব্রুয়ারি-মার্চে ফসল ওঠে, তখন সরিষার তেলের কাঁচামাল সস্তা হতে পারে।",
    ),
]


def crops_at_harvest(month: int) -> list[CropSeason]:
    return [crop for crop in CROP_CALENDAR if month in crop.harvest_months]


def crops_being_sown(month: int) -> list[CropSeason]:
    return [crop for crop in CROP_CALENDAR if month in crop.sowing_months]


def find_crop(slug: str) -> CropSeason | None:
    return next((crop for crop in CROP_CALENDAR if crop.slug == slug), None)


def crops_for_district(district: str) -> list[CropSeason]:
    if not district:
        return []
    normalized = district.strip().lower()
    return [
        crop
        for crop in CROP_CALENDAR
        if any(normalized in item.lower() or item.lower() in normalized for item in crop.main_districts)
    ]
