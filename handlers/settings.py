import csv
import io
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, BufferedInputFile
from aiogram.fsm.context import FSMContext

import database as db
from states import DeleteForm
from keyboards import MAIN_MENU, CONFIRM_DELETE_KEYBOARD
from utils import parse_amount, format_amount, format_datetime_short

router = Router()


# ---------- /limit ----------

@router.message(Command("limit"))
async def cmd_limit(message: Message, command: CommandObject):
    if not command.args:
        current = db.get_monthly_limit(message.from_user.id)
        current_text = format_amount(current) if current else "belgilanmagan"
        await message.answer(
            f"Joriy oylik limit: {current_text}\n\n"
            f"Limit belgilash uchun: <code>/limit 500000</code>",
            reply_markup=MAIN_MENU,
        )
        return

    amount = parse_amount(command.args.strip())
    if amount is None:
        await message.answer(
            "❗️ Iltimos, to'g'ri son kiriting. Masalan: /limit 500000",
            reply_markup=MAIN_MENU,
        )
        return

    db.set_monthly_limit(message.from_user.id, amount)
    await message.answer(
        f"✅ Oylik xarajat limiti {format_amount(amount)} qilib belgilandi.\n"
        f"Limitning 80% va 100% iga yetganda sizga ogohlantirish yuboraman.",
        reply_markup=MAIN_MENU,
    )


# ---------- /delete ----------

@router.message(Command("delete"))
@router.message(F.text == "🗑 Oxirgisini o'chirish")
async def cmd_delete(message: Message, state: FSMContext):
    last = db.get_last_transaction(message.from_user.id)
    if not last:
        await message.answer("O'chirish uchun yozuvlar topilmadi.", reply_markup=MAIN_MENU)
        return

    label = "Xarajat" if last["type"] == "expense" else "Daromad"
    note_part = f" ({last['note']})" if last["note"] else ""
    time_str = format_datetime_short(last["created_at"])

    await state.update_data(delete_id=last["id"])
    await state.set_state(DeleteForm.confirming)
    await message.answer(
        f"Oxirgi yozuv:\n\n"
        f"{label}: {last['category']} — {format_amount(last['amount'])}{note_part}\n"
        f"Vaqti: {time_str}\n\n"
        f"Shu yozuvni o'chirishni tasdiqlaysizmi?",
        reply_markup=CONFIRM_DELETE_KEYBOARD,
    )


@router.message(DeleteForm.confirming, F.text == "✅ Ha, o'chirish")
async def confirm_delete(message: Message, state: FSMContext):
    data = await state.get_data()
    delete_id = data.get("delete_id")
    await state.clear()

    if delete_id and db.delete_transaction(delete_id, message.from_user.id):
        await message.answer("🗑 Yozuv o'chirildi.", reply_markup=MAIN_MENU)
    else:
        await message.answer("❌ Yozuvni o'chirib bo'lmadi.", reply_markup=MAIN_MENU)


@router.message(DeleteForm.confirming, F.text == "❌ Yo'q, bekor qilish")
async def cancel_delete(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=MAIN_MENU)


@router.message(DeleteForm.confirming)
async def invalid_delete_response(message: Message):
    await message.answer(
        "Iltimos, tugmalardan birini tanlang 👇",
        reply_markup=CONFIRM_DELETE_KEYBOARD,
    )


# ---------- /export ----------

@router.message(Command("export"))
async def cmd_export(message: Message):
    user_id = message.from_user.id
    rows = db.get_month_transactions(user_id)

    if not rows:
        await message.answer("Bu oyda eksport qilish uchun yozuvlar yo'q.", reply_markup=MAIN_MENU)
        return

    try:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["Sana", "Turi", "Kategoriya", "Summa", "Izoh"])
        for row in rows:
            type_label = "Daromad" if row["type"] == "income" else "Xarajat"
            writer.writerow([row["created_at"], type_label, row["category"], row["amount"], row["note"] or ""])

        file_bytes = buffer.getvalue().encode("utf-8-sig")
        file_name = f"xarajatlar_{datetime.now().strftime('%Y_%m')}.csv"
        document = BufferedInputFile(file_bytes, filename=file_name)

        await message.answer_document(document, caption="📎 Joriy oy yozuvlari CSV formatida.")
    except Exception:
        await message.answer("❌ Faylni tayyorlashda xatolik yuz berdi.", reply_markup=MAIN_MENU)
