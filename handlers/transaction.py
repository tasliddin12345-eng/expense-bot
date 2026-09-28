from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

import database as db
from states import TransactionForm
from keyboards import (
    MAIN_MENU,
    categories_keyboard,
    SKIP_NOTE_KEYBOARD,
    CANCEL_KEYBOARD,
)
from utils import (
    parse_amount,
    format_amount,
    detect_category,
    extract_amount_and_category,
    EXPENSE_CATEGORIES,
    INCOME_CATEGORIES,
)

router = Router()

ALL_EXPENSE_CATS = set(EXPENSE_CATEGORIES.keys())
ALL_INCOME_CATS = set(INCOME_CATEGORIES.keys())

# Keywords that strongly suggest the quick-entry message is income, not expense
INCOME_HINT_KEYWORDS = [
    "ish haqi", "oylik", "maosh", "keldi", "tushdi", "frilans", "frilanс",
    "sovga", "sovg'a", "hadya", "topdim", "daromad",
]


# ---------- Starting the flow ----------

@router.message(F.text == "➕ Xarajat qo'shish")
async def start_expense(message: Message, state: FSMContext):
    await state.clear()
    await state.update_data(type="expense")
    await state.set_state(TransactionForm.choosing_category)
    await message.answer("Kategoriyani tanlang:", reply_markup=categories_keyboard(is_income=False))


@router.message(F.text == "💰 Daromad qo'shish")
async def start_income(message: Message, state: FSMContext):
    await state.clear()
    await state.update_data(type="income")
    await state.set_state(TransactionForm.choosing_category)
    await message.answer("Kategoriyani tanlang:", reply_markup=categories_keyboard(is_income=True))


# ---------- Category selection ----------

@router.message(TransactionForm.choosing_category)
async def choose_category(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    data = await state.get_data()
    is_income = data.get("type") == "income"
    valid_cats = ALL_INCOME_CATS if is_income else ALL_EXPENSE_CATS

    if text not in valid_cats:
        await message.answer(
            "Iltimos, quyidagi tugmalardan birini tanlang 👇",
            reply_markup=categories_keyboard(is_income=is_income),
        )
        return

    await state.update_data(category=text)
    await state.set_state(TransactionForm.entering_amount)
    await message.answer(
        "Summani kiriting (masalan: 25000, 15k yoki 2kk):",
        reply_markup=CANCEL_KEYBOARD,
    )


# ---------- Amount entry ----------

@router.message(TransactionForm.entering_amount)
async def enter_amount(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    amount = parse_amount(text)

    if amount is None:
        await message.answer(
            "❗️ Summani to'g'ri kiriting (faqat musbat son). Masalan: 25000, 15k, 2kk",
            reply_markup=CANCEL_KEYBOARD,
        )
        return

    await state.update_data(amount=amount)
    await state.set_state(TransactionForm.entering_note)
    await message.answer(
        "Izoh qo'shmoqchimisiz? (ixtiyoriy)",
        reply_markup=SKIP_NOTE_KEYBOARD,
    )


# ---------- Note entry ----------

@router.message(TransactionForm.entering_note)
async def enter_note(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    note = "" if text == "➡️ O'tkazib yuborish" else text

    data = await state.get_data()
    await finalize_transaction(
        message=message,
        state=state,
        user_id=message.from_user.id,
        type_=data["type"],
        category=data["category"],
        amount=data["amount"],
        note=note,
    )


# ---------- Shared finalize logic ----------

async def finalize_transaction(message: Message, state: FSMContext, user_id: int, type_: str, category: str, amount: float, note: str):
    try:
        db.add_transaction(user_id, type_, category, amount, note)
    except Exception:
        await state.clear()
        await message.answer(
            "❌ Xatolik yuz berdi, yozuvni saqlab bo'lmadi. Qaytadan urinib ko'ring.",
            reply_markup=MAIN_MENU,
        )
        return

    await state.clear()

    income_today, expense_today = db.get_today_totals(user_id)
    label = "Xarajat" if type_ == "expense" else "Daromad"
    today_total = expense_today if type_ == "expense" else income_today

    note_part = f" ({note})" if note else ""
    text = (
        f"✅ {label} qo'shildi: {category} — {format_amount(amount)}{note_part}\n"
        f"Bugungi jami {label.lower()}: {format_amount(today_total)}"
    )
    await message.answer(text, reply_markup=MAIN_MENU)

    if type_ == "expense":
        await check_limit_and_notify(message, user_id)


async def check_limit_and_notify(message: Message, user_id: int):
    limit = db.get_monthly_limit(user_id)
    if not limit or limit <= 0:
        return

    from datetime import datetime
    month_str = datetime.now().strftime("%Y-%m")
    _, month_expense = db.get_month_totals(user_id)
    ratio = month_expense / limit

    notified_80, notified_100 = db.get_limit_notification_flags(user_id)

    if ratio >= 1.0 and notified_100 != month_str:
        db.set_limit_notification_flag(user_id, "100", month_str)
        await message.answer(
            f"🚨 Diqqat! Oylik xarajat limitingiz ({format_amount(limit)}) to'liq sarflandi.\n"
            f"Joriy oy xarajati: {format_amount(month_expense)}"
        )
    elif ratio >= 0.8 and notified_80 != month_str:
        db.set_limit_notification_flag(user_id, "80", month_str)
        await message.answer(
            f"⚠️ Diqqat! Oylik xarajat limitingizning 80% i sarflandi.\n"
            f"Limit: {format_amount(limit)} | Sarflandi: {format_amount(month_expense)}"
        )


# ---------- Quick entry: free text like "25000 ovqat" or "taksi 15000" ----------

def looks_like_income(text: str) -> bool:
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in INCOME_HINT_KEYWORDS)


@router.message(F.text.regexp(r"\d"))
async def quick_entry(message: Message, state: FSMContext):
    # Only handle free text when user is not in the middle of another flow
    current_state = await state.get_state()
    if current_state is not None:
        return

    text = message.text.strip()
    is_income = looks_like_income(text)
    amount, category = extract_amount_and_category(text, is_income=is_income)

    if amount is None:
        return  # not a recognizable quick-entry message, ignore silently

    type_ = "income" if is_income else "expense"
    user_id = message.from_user.id

    await finalize_transaction(
        message=message,
        state=state,
        user_id=user_id,
        type_=type_,
        category=category,
        amount=amount,
        note="",
    )
