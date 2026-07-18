from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Festival:
    slug: str
    name_bengali: str
    name_english: str
    month_hint: list[int]
    demand_categories: list[str] = field(default_factory=list)
    demand_note_bengali: str = ""


@dataclass
class SeasonalPricePattern:
    season_bengali: str
    months: list[int]
    weather_note_bengali: str
    price_effects: list[str]


@dataclass
class DistrictMela:
    slug: str
    name_bengali: str
    name_english: str
    district: str
    month_hint: list[int]
    demand_categories: list[str] = field(default_factory=list)
    demand_note_bengali: str = ""


FESTIVALS: list[Festival] = [
    Festival("poila_boishakh", "পয়লা বৈশাখ", "Bengali New Year", [4], ["food", "handicraft", "textile"], "নতুন বছরের কেনাকাটা ও মিষ্টির চাহিদা বাড়ে।"),
    Festival("rath_yatra", "রথযাত্রা", "Rath Yatra", [6, 7], ["food", "handicraft"], "মেলার সামগ্রী ও খাবারের চাহিদা বাড়ে।"),
    Festival("saraswati_puja", "সরস্বতী পূজা", "Saraswati Puja", [1, 2], ["food", "handicraft"], "ফল, মিষ্টি ও পূজার সামগ্রীর চাহিদা বাড়ে।"),
    Festival("durga_puja", "দুর্গা পূজা", "Durga Puja", [9, 10], ["textile", "food", "handicraft"], "শাড়ি, নতুন পোশাক, মিষ্টি ও উপহারের চাহিদা বাড়ে।"),
    Festival("kali_puja", "কালী পূজা / দীপাবলি", "Kali Puja / Diwali", [10, 11], ["food", "handicraft"], "মোমবাতি, প্রদীপ ও মিষ্টির চাহিদা বাড়ে।"),
    Festival("jagadhatri_puja", "জগদ্ধাত্রী পূজা", "Jagadhatri Puja", [11], ["food", "handicraft"], "স্থানীয়ভাবে চাহিদা বাড়ে।"),
    Festival("nabanna", "নবান্ন", "Nabanna", [11, 12], ["food"], "নতুন চালের পিঠা ও মিষ্টির চাহিদা বাড়ে।"),
    Festival("poush_mela", "পৌষ মেলা", "Poush Mela", [12], ["handicraft", "food"], "হস্তশিল্প ও পিঠার চাহিদা বাড়ে।"),
    Festival("christmas", "বড়দিন", "Christmas", [12], ["food", "handicraft"], "কেক ও উপহারের চাহিদা বাড়ে।"),
    Festival("eid_ul_fitr", "ঈদ-উল-ফিতর", "Eid ul-Fitr", [3, 4, 5], ["food", "textile"], "নতুন পোশাক ও মিষ্টির চাহিদা বাড়ে।"),
    Festival("eid_ul_adha", "ঈদ-উল-আযহা / বকরি ঈদ", "Eid ul-Adha", [6, 7, 8], ["food"], "খাবারের চাহিদা বাড়ে।"),
]

SEASONAL_PATTERNS: list[SeasonalPricePattern] = [
    SeasonalPricePattern("গ্রীষ্ম", [4, 5, 6], "তীব্র গরমে পচনশীল পণ্য দ্রুত নষ্ট হয়।", ["তাজা শাকসবজির সরবরাহ কমে দাম বাড়তে পারে", "আম ও লিচুর সরবরাহ বাড়ে", "শুকনো পণ্যের বিক্রি স্থিতিশীল থাকে"]),
    SeasonalPricePattern("বর্ষা", [7, 8, 9], "ভারী বৃষ্টিতে যাতায়াত ও ফসল তোলা ব্যাহত হতে পারে।", ["শাকসবজির দাম ওঠানামা করে", "ঘরে বসে করা সেলাই বা হস্তশিল্পের সময় বাড়ে"]),
    SeasonalPricePattern("শরৎ-হেমন্ত", [10, 11], "পূজার মরসুমে কেনাকাটা বাড়ে।", ["টেক্সটাইল ও হস্তশিল্পের চাহিদা বাড়ে", "নতুন ধান ওঠে"]),
    SeasonalPricePattern("শীত", [12, 1, 2], "শুকনো ঠান্ডা আবহাওয়া সবজি চাষে সহায়ক।", ["শীতকালীন সবজির সরবরাহ বাড়ে", "পিঠা-পুলি ও মধুর চাহিদা বাড়ে"]),
    SeasonalPricePattern("বসন্ত", [3], "শুষ্ক ও উষ্ণ আবহাওয়া শুরু হয়।", ["হালকা সুতির কাপড়ের চাহিদা বাড়তে শুরু করে"]),
]

DISTRICT_MELAS: list[DistrictMela] = [
    DistrictMela("gangasagar_mela", "গঙ্গাসাগর মেলা", "Gangasagar Mela", "South 24 Parganas", [1], ["food", "handicraft"], "তীর্থযাত্রীর ভিড়ে খাবার ও ধর্মীয় সামগ্রীর চাহিদা বাড়ে।"),
    DistrictMela("joydev_kenduli_mela", "জয়দেব কেন্দুলি মেলা", "Joydev Kenduli Mela", "Birbhum", [1], ["handicraft", "food"], "বাউল মেলা ঘিরে হস্তশিল্প ও খাবারের চাহিদা বাড়ে।"),
    DistrictMela("bishnupur_mela", "বিষ্ণুপুর মেলা", "Bishnupur Mela", "Bankura", [12], ["handicraft"], "টেরাকোটা ও হস্তশিল্পের চাহিদা বাড়ে।"),
    DistrictMela("rash_mela", "রাস মেলা", "Rash Mela", "Cooch Behar", [11, 12], ["handicraft", "food"], "মাসব্যাপী মেলায় হস্তশিল্প ও খাবারের চাহিদা বাড়ে।"),
    DistrictMela("tusu_mela", "টুসু মেলা", "Tusu Mela", "Purulia", [12, 1], ["handicraft", "food"], "টুসু পরব ঘিরে হস্তশিল্প ও খাবারের চাহিদা বাড়ে।"),
]


def get_context_for_agents(month: int, block: str | None = None, district: str | None = None) -> dict:
    upcoming_festivals = [festival for festival in FESTIVALS if month in festival.month_hint]
    season = next((item for item in SEASONAL_PATTERNS if month in item.months), None)
    upcoming_melas: list[DistrictMela] = []
    if district:
        normalized = district.strip().lower()
        upcoming_melas = [
            mela
            for mela in DISTRICT_MELAS
            if month in mela.month_hint and (mela.district.lower() in normalized or normalized in mela.district.lower())
        ]
    return {
        "month": month,
        "block": block,
        "upcoming_festivals": [
            {"slug": festival.slug, "name_bengali": festival.name_bengali, "demand_categories": festival.demand_categories, "note": festival.demand_note_bengali}
            for festival in upcoming_festivals
        ],
        "upcoming_district_melas": [
            {"slug": mela.slug, "name_bengali": mela.name_bengali, "district": mela.district, "demand_categories": mela.demand_categories, "note": mela.demand_note_bengali}
            for mela in upcoming_melas
        ],
        "season": None if season is None else {"name": season.season_bengali, "weather_note": season.weather_note_bengali, "price_effects": season.price_effects},
    }
