import re
from datetime import datetime

MONTHS_UZ = [
    "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
    "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr",
]

EXPENSE_CATEGORIES = {
    "🍔 Ovqat": ["ovqat", "ovqatlanish", "tushlik", "nonushta", "kechki", "osh", "fastfud", "kafe", "restoran"],
    "🚕 Yo'l-kira": ["taksi", "yol", "yo'l", "kira", "avtobus", "metro", "benzin", "yoliga", "transport"],
    "🛒 Bozorlik": ["bozor", "bozorlik", "market", "do'kon", "dokon", "oziq-ovqat", "supermarket"],
    "🏠 Kommunal": ["kommunal", "svet", "gaz", "suv", "internet", "ijara", "kvartira", "elektr"],
    "👕 Kiyim": ["kiyim", "poyabzal", "oyoq kiyim", "kurtka", "shim", "koylak"],
    "🎉 Ko'ngilochar": ["kino", "konsert", "o'yin", "oyin", "dam olish", "sayohat", "kafe", "restoran"],
    "📦 Boshqa": [],
}

INCOME_CATEGORIES = {
    "💼 Ish haqi": ["ish haqi", "oylik", "maosh", "ishdan"],
    "💻 Frilanс": ["frilans", "frilanс", "loyiha", "buyurtma", "freelance"],
    "🎁 Sovg'a": ["sovga", "sovg'a", "hadya"],
    "📦 Boshqa": [],
}


def parse_amount(text: str):
    """
    Parse an amount string like '25000', '15k', '2kk', '1.5k', '2 mln'
    into a float. Returns None if parsing fails or amount is not positive.
    """
    if not text:
        return None
    text = text.strip().lower().replace(",", ".")
    text = text.replace(" ", "")

    # 2kk / 2 mln / 2million -> millions
    match = re.match(r"^(\d+(?:\.\d+)?)(kk|mln|million|m)$", text)
    if match:
        value = float(match.group(1)) * 1_000_000
        return value if value > 0 else None

    # 15k / 15ming -> thousands
    match = re.match(r"^(\d+(?:\.\d+)?)(k|ming)$", text)
    if match:
        value = float(match.group(1)) * 1_000
        return value if value > 0 else None

    # plain number
    match = re.match(r"^(\d+(?:\.\d+)?)$", text)
    if match:
        value = float(match.group(1))
        return value if value > 0 else None

    return None


def extract_amount_and_category(text: str, is_income: bool = False):
    """
    Try to extract an amount and a category from a free-text quick-entry message,
    e.g. '25000 ovqat' or 'taksi 15000'.
    Returns (amount, category) or (None, None) if no amount found.
    """
    words = text.strip().lower().split()
    amount = None
    remaining_words = []

    for word in words:
        if amount is None:
            parsed = parse_amount(word)
            if parsed is not None:
                amount = parsed
                continue
        remaining_words.append(word)

    if amount is None:
        return None, None

    remaining_text = " ".join(remaining_words)
    categories = INCOME_CATEGORIES if is_income else EXPENSE_CATEGORIES
    category = detect_category(remaining_text, categories)
    return amount, category


def detect_category(text: str, categories: dict):
    text = text.lower()
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in text:
                return category
    return "📦 Boshqa"


def format_amount(amount: float) -> str:
    """Format a number as '1 250 000 so'm'."""
    amount_int = int(round(amount))
    formatted = f"{amount_int:,}".replace(",", " ")
    return f"{formatted} so'm"


def format_date_uz(dt: datetime = None) -> str:
    dt = dt or datetime.now()
    return f"{dt.day} {MONTHS_UZ[dt.month - 1]} {dt.year}"


def format_datetime_short(dt_str: str) -> str:
    """Convert '2026-09-27 14:30:00' -> '14:30'."""
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%H:%M")
    except ValueError:
        return dt_str
