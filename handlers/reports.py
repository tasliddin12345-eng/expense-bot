from datetime import datetime
from collections import defaultdict

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

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


def build_month_report(user_id: int) -> str:
    rows = db.get_month_transactions(user_id)
    now = datetime.now()
    month_label = format_date_uz(now).split(" ", 1)[1]  # "Sentabr 2026"

    if not rows:
        return f"📅 <b>Oylik hisobot ({month_label})</b>\n\nBu oyda hali yozuv kiritilmagan."

    income_total = 0
    expense_total = 0
    expense_by_category = defaultdict(float)
    days_with_expense = set()

    for row in rows:
        if row["type"] == "income":
            income_total += row["amount"]
        else:
            expense_total += row["amount"]
            expense_by_category[row["category"]] += row["amount"]
            days_with_expense.add(row["created_at"][:10])

    lines = [f"📅 <b>Oylik hisobot ({month_label})</b>\n"]
    lines.append(f"💰 Jami daromad: {format_amount(income_total)}")
    lines.append(f"💸 Jami xarajat: {format_amount(expense_total)}")
    lines.append(f"📈 Sof qoldiq: {format_amount(income_total - expense_total)}")

    if expense_total > 0:
        lines.append("\n📂 <b>Kategoriyalar bo'yicha xarajat:</b>")
        sorted_cats = sorted(expense_by_category.items(), key=lambda x: x[1], reverse=True)
        for category, amount in sorted_cats:
            percent = (amount / expense_total) * 100
            lines.append(f"{category}: {format_amount(amount)} ({percent:.1f}%)")

    day_count = now.day
    avg_daily = expense_total / day_count if day_count else 0
    lines.append(f"\n📆 Kunlik o'rtacha xarajat: {format_amount(avg_daily)}")

    limit = db.get_monthly_limit(user_id)
    if limit and limit > 0:
        remaining = limit - expense_total
        lines.append(f"\n🎯 Oylik limit: {format_amount(limit)}")
        if remaining >= 0:
            lines.append(f"✅ Qoldiq: {format_amount(remaining)}")
        else:
            lines.append(f"🚨 Limitdan {format_amount(abs(remaining))} ga oshib ketdingiz!")

    return "\n".join(lines)


@router.message(Command("today"))
@router.message(F.text == "📊 Bugungi hisobot")
async def today_report(message: Message):
    text = build_today_report(message.from_user.id)
    await message.answer(text, reply_markup=MAIN_MENU)


@router.message(Command("month"))
@router.message(F.text == "📅 Oylik hisobot")
async def month_report(message: Message):
    text = build_month_report(message.from_user.id)
    await message.answer(text, reply_markup=MAIN_MENU)
