import sqlite3
from datetime import datetime, date
from contextlib import contextmanager

DB_NAME = "finance.db"


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
