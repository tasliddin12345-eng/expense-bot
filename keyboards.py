from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from utils import EXPENSE_CATEGORIES, INCOME_CATEGORIES

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Xarajat qo'shish"), KeyboardButton(text="💰 Daromad qo'shish")],
        [KeyboardButton(text="📊 Bugungi hisobot"), KeyboardButton(text="📅 Oylik hisobot")],
        [KeyboardButton(text="🗑 Oxirgisini o'chirish")],
    ],
    resize_keyboard=True,
)


def categories_keyboard(is_income: bool = False) -> ReplyKeyboardMarkup:
    categories = list(INCOME_CATEGORIES.keys()) if is_income else list(EXPENSE_CATEGORIES.keys())
    rows = []
    row = []
    for i, cat in enumerate(categories, start=1):
        row.append(KeyboardButton(text=cat))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([KeyboardButton(text="⬅️ Bekor qilish")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


SKIP_NOTE_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➡️ O'tkazib yuborish")],
        [KeyboardButton(text="⬅️ Bekor qilish")],
    ],
    resize_keyboard=True,
)

CANCEL_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="⬅️ Bekor qilish")]],
    resize_keyboard=True,
)

CONFIRM_DELETE_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Ha, o'chirish"), KeyboardButton(text="❌ Yo'q, bekor qilish")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

REMOVE_KEYBOARD = ReplyKeyboardRemove()
