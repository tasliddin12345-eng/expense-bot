from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from keyboards import MAIN_MENU

router = Router()

HELP_TEXT = (
    "📖 <b>Buyruqlar ro'yxati:</b>\n\n"
    "➕ <b>Xarajat qo'shish</b> — yangi xarajat kiritish\n"
    "💰 <b>Daromad qo'shish</b> — yangi daromad kiritish\n"
    "📊 <b>Bugungi hisobot</b> yoki /today — bugungi kirim-chiqimlar\n"
    "📅 <b>Oylik hisobot</b> yoki /month — shu oy bo'yicha to'liq hisobot\n"
    "🗑 <b>Oxirgisini o'chirish</b> yoki /delete — oxirgi yozuvni o'chirish\n\n"
    "⚡️ <b>Tez kiritish:</b> shunchaki \"25000 ovqat\" yoki \"taksi 15000\" deb yozing — "
    "bot avtomatik xarajat sifatida qo'shadi.\n\n"
    "/limit 500000 — oylik xarajat limitini belgilash\n"
    "/export — joriy oy yozuvlarini CSV qilib olish\n"
    "/help — shu xabarni qayta ko'rish"
)

WELCOME_TEXT = (
    "👋 Salom! Men — shaxsiy moliya yordamchingizman.\n\n"
    "Har kuni xarajat va daromadlaringizni menga yozib boring, men esa kunlik va oylik "
    "hisobotlar tayyorlab beraman.\n\n"
    "Quyidagi menyudan foydalaning yoki shunchaki \"15000 taksi\" kabi yozib yuboring 👇"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=MAIN_MENU)


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, reply_markup=MAIN_MENU)


@router.message(F.text == "⬅️ Bekor qilish")
async def cancel_action(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=MAIN_MENU)
