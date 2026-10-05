from datetime import datetime, date, timedelta
from collections import defaultdict

from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

import database as db
from keyboards import MAIN_MENU
from utils import format_amount, format_datetime_short, format_date_uz

router = Router()


def build_today_report(user_id: int) -> str:
    rows = db.get_today_transactions(user_id)
    today_str = format_date_uz(datetime.now())

    if not rows:
        return f"📊 <b>Bugungi hisobot ({today_str})</b>\n\nBugun hali yozuv kiritilmagan."

    lines = [f"📊 <b>Bugungi hisobot ({today_str})</b>\n"]
    income_total = 0
    expense_total = 0

    for row in rows:
        time_str = format_datetime_short(row["created_at"])
        sign = "+" if row["type"] == "income" else "−"
        note_part = f" ({row['note']})" if row["note"] else ""
        lines.append(f"{time_str} | {row['category']} | {sign}{format_amount(row['amount'])}{note_part}")
        if row["type"] == "income":
            income_total += row["amount"]
        else:
            expense_total += row["amount"]

    lines.append("")
    lines.append(f"💰 Jami daromad: {format_amount(income_total)}")
    lines.append(f"💸 Jami xarajat: {format_amount(expense_total)}")
    lines.append(f"📈 Sof farq: {format_amount(income_total - expense_total)}")

    return "\n".join(lines)


# ---------- oylik hisobot: tanlangan sanadan keyingi oyning shu sanasigacha ----------
def add_months(d: date, n: int) -> date:
    y, m = divmod(d.year * 12 + d.month - 1 + n, 12)
    return date(y, m + 1, d.day)  # kun 1..28 bo'lgani uchun xavfsiz


def get_period(day: int, offset: int = 0):
    """offset=0 joriy davr, -1 o'tgan davr, -2 undan oldingi ...
    Qaytaradi: (boshlanish, tugash). Tugash sanasi kirmaydi."""
    today = date.today()
    start = date(today.year, today.month, day)
    if today.day < day:
        start = add_months(start, -1)
    start = add_months(start, offset)
    return start, add_months(start, 1)


def build_month_report(user_id: int, offset: int = 0) -> str:
    day = db.get_period_day(user_id)
    start, end = get_period(day, offset)
    last_day = end - timedelta(days=1)
    label = f"{start:%d.%m.%Y} - {last_day:%d.%m.%Y}"
    footer = "\n\nℹ️ Hisobot boshlanish sanasini o'zgartirish: <code>/kun 10</code>"

    rows = db.get_transactions_between(user_id, start, end)

    if not rows:
        return f"📅 <b>Oylik hisobot ({label})</b>\n\nBu davrda yozuv kiritilmagan." + footer

    income_total = 0
    expense_total = 0
    expense_by_category = defaultdict(float)

    for row in rows:
        if row["type"] == "income":
            income_total += row["amount"]
        else:
            expense_total += row["amount"]
            expense_by_category[row["category"]] += row["amount"]

    lines = [f"📅 <b>Oylik hisobot ({label})</b>\n"]
    lines.append(f"💰 Jami daromad: {format_amount(income_total)}")
    lines.append(f"💸 Jami xarajat: {format_amount(expense_total)}")
    lines.append(f"📈 Sof qoldiq: {format_amount(income_total - expense_total)}")

    if expense_total > 0:
        lines.append("\n📂 <b>Kategoriyalar bo'yicha xarajat:</b>")
        sorted_cats = sorted(expense_by_category.items(), key=lambda x: x[1], reverse=True)
        for category, amount in sorted_cats:
            percent = (amount / expense_total) * 100
            lines.append(f"{category}: {format_amount(amount)} ({percent:.1f}%)")

    # Kunlik o'rtacha: joriy davrda bugungi kungacha, o'tgan davrda to'liq davr bo'yicha
    days_passed = (min(date.today(), last_day) - start).days + 1
    avg_daily = expense_total / days_passed if days_passed > 0 else 0
    lines.append(f"\n📆 Kunlik o'rtacha xarajat: {format_amount(avg_daily)}")

    limit = db.get_monthly_limit(user_id)
    if limit and limit > 0:
        remaining = limit - expense_total
        lines.append(f"\n🎯 Oylik limit: {format_amount(limit)}")
        if remaining >= 0:
            lines.append(f"✅ Qoldiq: {format_amount(remaining)}")
        else:
            lines.append(f"🚨 Limitdan {format_amount(abs(remaining))} ga oshib ketdingiz!")

    return "\n".join(lines) + footer


def month_keyboard(offset: int) -> InlineKeyboardMarkup:
    row = [InlineKeyboardButton(text="◀ Oldingi oy", callback_data=f"mrep:{offset - 1}")]
    if offset < 0:
        row.append(InlineKeyboardButton(text="Keyingi oy ▶", callback_data=f"mrep:{offset + 1}"))
    return InlineKeyboardMarkup(inline_keyboard=[row])


@router.message(Command("today"))
@router.message(F.text == "📊 Bugungi hisobot")
async def today_report(message: Message):
    text = build_today_report(message.from_user.id)
    await message.answer(text, reply_markup=MAIN_MENU)


@router.message(Command("month"))
@router.message(F.text == "📅 Oylik hisobot")
async def month_report(message: Message):
    text = build_month_report(message.from_user.id, 0)
    await message.answer(text, reply_markup=month_keyboard(0))


@router.callback_query(F.data.startswith("mrep:"))
async def month_report_nav(call: CallbackQuery):
    offset = min(int(call.data.split(":")[1]), 0)
    text = build_month_report(call.from_user.id, offset)
    await call.message.edit_text(text, reply_markup=month_keyboard(offset))
    await call.answer()


@router.message(Command("kun"))
async def set_period_day(message: Message, command: CommandObject):
    user_id = message.from_user.id
    current = db.get_period_day(user_id)
    try:
        day = int((command.args or "").strip())
        if not 1 <= day <= 28:
            raise ValueError
    except ValueError:
        await message.answer(
            f"Hisobot hozir har oyning <b>{current}</b>-sanasidan boshlanadi.\n\n"
            "O'zgartirish uchun 1 dan 28 gacha son yozing.\n"
            "Masalan: <code>/kun 10</code>",
            reply_markup=MAIN_MENU,
        )
        return

    db.set_period_day(user_id, day)
    await message.answer(
        f"✅ Endi oylik hisobot har oyning <b>{day}</b>-sanasidan keyingi oyning "
        f"{day}-sanasigacha hisoblanadi.\n\n📅 Oylik hisobot tugmasini bosib ko'ring.",
        reply_markup=MAIN_MENU,
    )
