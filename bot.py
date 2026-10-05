"""Hisobchi bot: aiogram 3 + SQLite.
O'rnatish:  pip install aiogram
Ishga tushirish:  BOT_TOKEN=123:ABC python bot.py
"""
import asyncio
import os
import sqlite3
from datetime import date, datetime, timedelta

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandObject
from aiogram.types import (BotCommand, CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

TOKEN = os.getenv("BOT_TOKEN", "")
db = sqlite3.connect(os.getenv("DB_PATH", "hisob.db"))
db.executescript("""
CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, period_day INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS records(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, kind TEXT,
  amount REAL, note TEXT, created TEXT);
""")
dp = Dispatcher()


# ---------- yordamchi funksiyalar ----------
def money(x):
    return f"{x:,.0f}".replace(",", " ")


def get_day(uid):
    db.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (uid,))
    return db.execute("SELECT period_day FROM users WHERE user_id=?", (uid,)).fetchone()[0]


def add_months(d, n):
    y, m = divmod(d.year * 12 + d.month - 1 + n, 12)
    return date(y, m + 1, d.day)  # kun 1..28 bo'lgani uchun xavfsiz


def period(day, offset=0):
    """offset=0 joriy davr, -1 o'tgan davr, -2 undan oldingi ..."""
    t = date.today()
    start = date(t.year, t.month, day) if t.day >= day else add_months(date(t.year, t.month, day), -1)
    start = add_months(start, offset)
    return start, add_months(start, 1)  # oxiri kiritilmaydi


def totals(uid, start, end):
    rows = db.execute(
        "SELECT kind, COALESCE(SUM(amount),0) FROM records "
        "WHERE user_id=? AND created>=? AND created<? GROUP BY kind",
        (uid, start.isoformat(), end.isoformat())).fetchall()
    d = dict(rows)
    return d.get("daromat", 0), d.get("xarajat", 0)


def report_text(uid, offset):
    start, end = period(get_day(uid), offset)
    inc, exp = totals(uid, start, end)
    last = end - timedelta(days=1)
    return (f"📊 Hisobot: {start:%d.%m.%Y} - {last:%d.%m.%Y}\n\n"
            f"💰 Daromad: {money(inc)}\n💸 Xarajat: {money(exp)}\n"
            f"🧮 Balans: {money(inc - exp)}")


def report_kb(offset):
    row = [InlineKeyboardButton(text="◀ Oldingi oy", callback_data=f"rep:{offset - 1}")]
    if offset < 0:
        row.append(InlineKeyboardButton(text="Keyingi oy ▶", callback_data=f"rep:{offset + 1}"))
    return InlineKeyboardMarkup(inline_keyboard=[row])


async def add_record(m: Message, command: CommandObject, kind):
    parts = (command.args or "").split(maxsplit=1)
    try:
        amount = float(parts[0].replace(",", "."))
        assert amount > 0
    except Exception:
        return await m.answer(f"Summani yozing. Masalan:\n/{kind} 50000 izoh")
    note = parts[1] if len(parts) > 1 else ""
    get_day(m.from_user.id)
    db.execute("INSERT INTO records(user_id,kind,amount,note,created) VALUES(?,?,?,?,?)",
               (m.from_user.id, kind, amount, note, date.today().isoformat()))
    db.commit()
    await m.answer(f"✅ Qo'shildi: {money(amount)} {note}")


# ---------- buyruqlar ----------
@dp.message(Command("start"))
async def start(m: Message):
    get_day(m.from_user.id)
    db.commit()
    await m.answer("Assalomu alaykum! 💰 Daromad va xarajatlaringizni yuritaman.\n"
                   "Buyruqlar ro'yxati: /yordam")


@dp.message(Command("daromat"))
async def income(m: Message, command: CommandObject):
    await add_record(m, command, "daromat")


@dp.message(Command("xarajat"))
async def expense(m: Message, command: CommandObject):
    await add_record(m, command, "xarajat")


@dp.message(Command("balans"))
async def balance(m: Message):
    start_, end = period(get_day(m.from_user.id))
    inc, exp = totals(m.from_user.id, start_, end)
    await m.answer(f"🧮 Joriy davr balansi: {money(inc - exp)}\n"
                   f"({start_:%d.%m} dan {(end - timedelta(days=1)):%d.%m} gacha)")


@dp.message(Command("hisobot"))
async def hisobot(m: Message):
    await m.answer(report_text(m.from_user.id, 0), reply_markup=report_kb(0))


@dp.callback_query(lambda c: c.data and c.data.startswith("rep:"))
async def report_nav(c: CallbackQuery):
    offset = min(int(c.data.split(":")[1]), 0)
    await c.message.edit_text(report_text(c.from_user.id, offset), reply_markup=report_kb(offset))
    await c.answer()


@dp.message(Command("kun"))
async def set_day(m: Message, command: CommandObject):
    try:
        d = int(command.args)
        assert 1 <= d <= 28
    except Exception:
        return await m.answer("Hisobot qaysi kundan boshlansin? 1 dan 28 gacha son yozing.\nMasalan: /kun 15")
    get_day(m.from_user.id)
    db.execute("UPDATE users SET period_day=? WHERE user_id=?", (d, m.from_user.id))
    db.commit()
    await m.answer(f"✅ Endi oylik hisobot har oyning {d}-sanasidan boshlanadi.")


@dp.message(Command("tarix"))
async def history(m: Message):
    rows = db.execute("SELECT id,kind,amount,note,created FROM records WHERE user_id=? "
                      "ORDER BY id DESC LIMIT 10", (m.from_user.id,)).fetchall()
    if not rows:
        return await m.answer("Hozircha yozuv yo'q.")
    lines = [f"#{i} {'💰' if k == 'daromat' else '💸'} {money(a)} {n} ({d})" for i, k, a, n, d in rows]
    await m.answer("So'nggi yozuvlar:\n" + "\n".join(lines) + "\n\nO'chirish: /ochirish <raqam>")


@dp.message(Command("ochirish"))
async def delete(m: Message, command: CommandObject):
    try:
        rid = int((command.args or "").lstrip("#"))
    except ValueError:
        return await m.answer("Yozuv raqamini kiriting. Masalan: /ochirish 12")
    cur = db.execute("DELETE FROM records WHERE id=? AND user_id=?", (rid, m.from_user.id))
    db.commit()
    await m.answer("🗑 O'chirildi." if cur.rowcount else "Bunday yozuv topilmadi.")


@dp.message(Command("yordam"))
async def help_(m: Message):
    await m.answer(
        "/daromat 50000 maosh - daromad qo'shish\n"
        "/xarajat 20000 non - xarajat qo'shish\n"
        "/balans - joriy balans\n"
        "/hisobot - oylik hisobot (◀ ▶ tugmalari bilan oldingi oylarni ko'ring)\n"
        "/kun 15 - hisobot har oyning 15-sanasidan boshlansin\n"
        "/tarix - so'nggi yozuvlar\n"
        "/ochirish 12 - yozuvni o'chirish")


async def main():
    bot = Bot(TOKEN)
    await bot.set_my_commands([
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="daromat", description="Daromad qo'shish"),
        BotCommand(command="xarajat", description="Xarajat qo'shish"),
        BotCommand(command="balans", description="Joriy balansni ko'rish"),
        BotCommand(command="hisobot", description="Oylik hisobot"),
        BotCommand(command="kun", description="Hisobot boshlanish sanasi"),
        BotCommand(command="tarix", description="So'nggi yozuvlar"),
        BotCommand(command="ochirish", description="Yozuvni o'chirish"),
        BotCommand(command="yordam", description="Yordam"),
    ])
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
