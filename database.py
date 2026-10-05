import os
import shutil
import sqlite3
from datetime import datetime, date
from contextlib import contextmanager

# Railway'da DB_PATH=/data/hisob.db (Volume) bo'lsa, ma'lumotlar yangilanishda o'chmaydi.
DB_NAME = os.getenv("DB_PATH", "finance.db")
_SEED_DB = "finance.db"


def _prepare_db_file():
    folder = os.path.dirname(DB_NAME)
    if folder:
        os.makedirs(folder, exist_ok=True)
    # Volume'dagi baza hali yo'q bo'lsa, repozitoriyadagi eski finance.db ni nusxalaymiz
    if DB_NAME != _SEED_DB and not os.path.exists(DB_NAME) and os.path.exists(_SEED_DB):
        shutil.copy(_SEED_DB, DB_NAME)


_prepare_db_file()


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                monthly_limit REAL DEFAULT 0,
                limit_80_notified_month TEXT,
                limit_100_notified_month TEXT
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_date ON transactions(user_id, created_at)")

        # Yangi ustun: hisobot boshlanish sanasi (eski bazaga ham xavfsiz qo'shiladi)
        cols = [r["name"] for r in cur.execute("PRAGMA table_info(user_settings)").fetchall()]
        if "period_day" not in cols:
            cur.execute("ALTER TABLE user_settings ADD COLUMN period_day INTEGER DEFAULT 1")


def add_transaction(user_id: int, type_: str, category: str, amount: float, note: str = ""):
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO transactions (user_id, type, category, amount, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, type_, category, amount, note, created_at),
        )
        return cur.lastrowid


def get_today_transactions(user_id: int):
    today_str = date.today().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM transactions WHERE user_id = ? AND created_at LIKE ? ORDER BY created_at ASC",
            (user_id, f"{today_str}%"),
        )
        return cur.fetchall()


def get_month_transactions(user_id: int, year: int = None, month: int = None):
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    month_str = f"{year:04d}-{month:02d}"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM transactions WHERE user_id = ? AND created_at LIKE ? ORDER BY created_at ASC",
            (user_id, f"{month_str}%"),
        )
        return cur.fetchall()


def get_transactions_between(user_id: int, start: date, end: date):
    """start dan end gacha (end kirmaydi) bo'lgan yozuvlar."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM transactions WHERE user_id = ? AND created_at >= ? AND created_at < ? "
            "ORDER BY created_at ASC",
            (user_id, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")),
        )
        return cur.fetchall()


def get_today_totals(user_id: int):
    rows = get_today_transactions(user_id)
    income = sum(r["amount"] for r in rows if r["type"] == "income")
    expense = sum(r["amount"] for r in rows if r["type"] == "expense")
    return income, expense


def get_month_totals(user_id: int):
    rows = get_month_transactions(user_id)
    income = sum(r["amount"] for r in rows if r["type"] == "income")
    expense = sum(r["amount"] for r in rows if r["type"] == "expense")
    return income, expense


def get_last_transaction(user_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
        return cur.fetchone()


def delete_transaction(transaction_id: int, user_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM transactions WHERE id = ? AND user_id = ?",
            (transaction_id, user_id),
        )
        return cur.rowcount > 0


def set_monthly_limit(user_id: int, amount: float):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO user_settings (user_id, monthly_limit) VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET monthly_limit = excluded.monthly_limit""",
            (user_id, amount),
        )


def get_monthly_limit(user_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT monthly_limit FROM user_settings WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return row["monthly_limit"] if row else 0


def get_period_day(user_id: int) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT period_day FROM user_settings WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if row and row["period_day"]:
            return int(row["period_day"])
        return 1


def set_period_day(user_id: int, day: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO user_settings (user_id, period_day) VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET period_day = excluded.period_day""",
            (user_id, day),
        )


def get_limit_notification_flags(user_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT limit_80_notified_month, limit_100_notified_month FROM user_settings WHERE user_id = ?",
            (user_id,),
        )
        row = cur.fetchone()
        if row:
            return row["limit_80_notified_month"], row["limit_100_notified_month"]
        return None, None


def set_limit_notification_flag(user_id: int, level: str, month_str: str):
    column = "limit_80_notified_month" if level == "80" else "limit_100_notified_month"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""INSERT INTO user_settings (user_id, {column}) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET {column} = excluded.{column}""",
            (user_id, month_str),
        )


def get_total_users_count():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(DISTINCT user_id) FROM transactions")
        return cur.fetchone()[0]
