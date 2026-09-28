# 💰 Xarajat Hisobchi — Telegram Bot

Kunlik xarajat va daromadlaringizni hisobga oluvchi Telegram bot. Python (aiogram 3.x) va SQLite asosida yozilgan.

## 📦 Imkoniyatlar

- ➕ Xarajat / 💰 Daromad qo'shish (kategoriya tanlash orqali)
- ⚡️ Tez kiritish: shunchaki `"25000 ovqat"` yoki `"taksi 15000"` deb yozing
- 📊 Bugungi hisobot (`/today`)
- 📅 Oylik hisobot — kategoriyalar bo'yicha taqsimot, kunlik o'rtacha (`/month`)
- 🎯 Oylik xarajat limiti va ogohlantirishlar (`/limit 500000`)
- 🗑 Oxirgi yozuvni o'chirish (`/delete`)
- 📎 Oylik yozuvlarni CSV qilib eksport qilish (`/export`)

## ⚙️ O'rnatish

1. **Repository'ni yuklab oling / fayllarni papkaga joylashtiring.**

2. **Virtual muhit yarating (tavsiya etiladi):**
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```

3. **Kutubxonalarni o'rnating:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Bot tokenini sozlang:**
   - `.env.example` faylidan nusxa oling:
     ```bash
     cp .env.example .env
     ```
   - `.env` faylini oching va `BOT_TOKEN` qiymatiga [@BotFather](https://t.me/BotFather) dan olingan tokenni yozing:
     ```
     BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstuVWXyz
     ```

## ▶️ Ishga tushirish

```bash
python bot.py
```

Bot ishga tushgach, Telegram'da botingizga `/start` yuboring.

## 🗂 Loyiha strukturasi

```
expense_bot/
├── bot.py               # Asosiy ishga tushirish fayli
├── database.py          # SQLite bilan ishlash funksiyalari
├── keyboards.py         # Reply klaviaturalar
├── utils.py              # Summa parser, formatlash, kategoriya aniqlash
├── states.py             # FSM holatlari
├── handlers/
│   ├── __init__.py       # Barcha routerlarni birlashtiradi
│   ├── start.py          # /start, /help
│   ├── transaction.py    # Xarajat/daromad qo'shish + tez kiritish
│   ├── reports.py        # /today, /month hisobotlar
│   └── settings.py       # /limit, /delete, /export
├── requirements.txt
├── .env.example
└── README.md
```

Ma'lumotlar `finance.db` nomli SQLite faylida saqlanadi — bot birinchi marta ishga tushganda avtomatik yaratiladi.

## 📝 Eslatma

- Barcha summalarni "ming" (`k`) yoki "million" (`kk`) qisqartmalari bilan ham kiritish mumkin: `15k` → 15 000, `2kk` → 2 000 000.
- Har bir foydalanuvchining ma'lumotlari faqat o'ziga ko'rinadi (Telegram user ID orqali ajratiladi).
