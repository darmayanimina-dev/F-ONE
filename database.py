"""
database.py
Layer penyimpanan SQLite lokal untuk F-ONE.
Mendukung multi-periode (Tahun & Bulan), riwayat, catatan harian & bulanan, serta flag status.
"""
import sqlite3
import calendar
import datetime
from typing import List, Dict, Any, Optional

DB_FILE = "fone_database.db"

MONTH_NAMES_ID = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}


def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS periods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                UNIQUE(year, month)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_id INTEGER NOT NULL,
                date_str TEXT NOT NULL UNIQUE,
                day_num INTEGER NOT NULL,
                is_sunday INTEGER DEFAULT 0,
                is_holiday INTEGER DEFAULT 0,
                holiday_name TEXT DEFAULT '',
                jlh_valid INTEGER DEFAULT 0,
                order_nda INTEGER DEFAULT 0,
                jlh_order_lokal INTEGER DEFAULT 0,
                acc_haji INTEGER DEFAULT 0,
                acc_emas INTEGER DEFAULT 0,
                acc_cash INTEGER DEFAULT 0,
                catatan TEXT DEFAULT '',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (period_id) REFERENCES periods (id) ON DELETE CASCADE
            )
        """)
        conn.commit()


def get_or_create_period(year: int, month: int) -> Dict[str, Any]:
    """Mengambil periode atau membuatnya jika belum ada"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM periods WHERE year = ? AND month = ?", (year, month))
        row = cursor.fetchone()
        if row:
            period = dict(row)
        else:
            now = datetime.datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO periods (year, month, status, notes, created_at, updated_at)
                VALUES (?, ?, 'ACTIVE', '', ?, ?)
            """, (year, month, now, now))
            conn.commit()
            period_id = cursor.lastrowid
            cursor.execute("SELECT * FROM periods WHERE id = ?", (period_id,))
            period = dict(cursor.fetchone())

    # Pastikan hari-hari dalam bulan tersebut sudah terinisialisasi
    ensure_month_days(period["id"], year, month)
    return period


def ensure_month_days(period_id: int, year: int, month: int):
    """
    Mengisi hari 1 s.d akhir bulan secara otomatis jika belum ada di database.
    Hari Minggu otomatis ditandai (is_sunday = 1).
    """
    _, num_days = calendar.monthrange(year, month)
    with get_db() as conn:
        cursor = conn.cursor()
        for day in range(1, num_days + 1):
            date_obj = datetime.date(year, month, day)
            date_str = date_obj.strftime("%Y-%m-%d")
            is_sunday = 1 if date_obj.weekday() == 6 else 0  # 6 is Sunday in Python

            cursor.execute("""
                INSERT OR IGNORE INTO daily_records 
                (period_id, date_str, day_num, is_sunday, is_holiday, holiday_name, jlh_valid, order_nda, jlh_order_lokal, acc_haji, acc_emas, acc_cash, catatan)
                VALUES (?, ?, ?, ?, 0, '', 0, 0, 0, 0, 0, 0, '')
            """, (period_id, date_str, day, is_sunday))
        conn.commit()


def list_all_years() -> List[int]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT year FROM periods ORDER BY year DESC")
        return [row[0] for row in cursor.fetchall()]


def list_periods_by_year(year: int) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM periods WHERE year = ? ORDER BY month DESC", (year,))
        return [dict(row) for row in cursor.fetchall()]


def get_period_by_id(period_id: int) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM periods WHERE id = ?", (period_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_period_status(period_id: int, status: str):
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.datetime.now().isoformat()
        completed_at = now if status == 'COMPLETED' else None
        cursor.execute("""
            UPDATE periods 
            SET status = ?, completed_at = ?, updated_at = ?
            WHERE id = ?
        """, (status, completed_at, now, period_id))
        conn.commit()


def update_period_notes(period_id: int, notes: str):
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.datetime.now().isoformat()
        cursor.execute("""
            UPDATE periods 
            SET notes = ?, updated_at = ?
            WHERE id = ?
        """, (notes, now, period_id))
        conn.commit()


def get_daily_records_by_period(period_id: int) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM daily_records WHERE period_id = ? ORDER BY day_num ASC", (period_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_daily_record_by_date(date_str: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM daily_records WHERE date_str = ?", (date_str,))
        row = cursor.fetchone()
        return dict(row) if row else None


def upsert_daily_record(
    period_id: int,
    date_str: str,
    day_num: int,
    is_sunday: bool,
    is_holiday: bool,
    holiday_name: str,
    jlh_valid: int,
    order_nda: int,
    jlh_order_lokal: int,
    acc_haji: int,
    acc_emas: int,
    acc_cash: int,
    catatan: str = ""
):
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO daily_records (
                period_id, date_str, day_num, is_sunday, is_holiday, holiday_name,
                jlh_valid, order_nda, jlh_order_lokal, acc_haji, acc_emas, acc_cash, catatan, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date_str) DO UPDATE SET
                is_sunday = excluded.is_sunday,
                is_holiday = excluded.is_holiday,
                holiday_name = excluded.holiday_name,
                jlh_valid = excluded.jlh_valid,
                order_nda = excluded.order_nda,
                jlh_order_lokal = excluded.jlh_order_lokal,
                acc_haji = excluded.acc_haji,
                acc_emas = excluded.acc_emas,
                acc_cash = excluded.acc_cash,
                catatan = excluded.catatan,
                updated_at = excluded.updated_at
        """, (
            period_id, date_str, day_num,
            1 if is_sunday else 0,
            1 if is_holiday else 0,
            holiday_name,
            jlh_valid, order_nda, jlh_order_lokal, acc_haji, acc_emas, acc_cash,
            catatan, now
        ))
        conn.commit()
