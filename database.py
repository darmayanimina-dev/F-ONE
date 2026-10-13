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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS change_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_id INTEGER NOT NULL,
                date_str TEXT NOT NULL,
                day_num INTEGER NOT NULL,
                action_type TEXT NOT NULL DEFAULT 'UPDATE',
                old_valid INTEGER DEFAULT 0,
                new_valid INTEGER DEFAULT 0,
                old_nda INTEGER DEFAULT 0,
                new_nda INTEGER DEFAULT 0,
                old_lokal INTEGER DEFAULT 0,
                new_lokal INTEGER DEFAULT 0,
                old_haji INTEGER DEFAULT 0,
                new_haji INTEGER DEFAULT 0,
                old_emas INTEGER DEFAULT 0,
                new_emas INTEGER DEFAULT 0,
                old_cash INTEGER DEFAULT 0,
                new_cash INTEGER DEFAULT 0,
                catatan_perubahan TEXT DEFAULT '',
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (period_id) REFERENCES periods (id) ON DELETE CASCADE
            )
        """)

        # Otomatis catat riwayat awal jika tabel history masih kosong
        cursor.execute("SELECT COUNT(*) FROM change_history")
        if cursor.fetchone()[0] == 0:
            cursor.execute("SELECT * FROM daily_records WHERE jlh_valid > 0 ORDER BY period_id ASC, day_num ASC")
            for r in cursor.fetchall():
                now_str = r["updated_at"] or datetime.datetime.now().isoformat()
                cursor.execute("""
                    INSERT INTO change_history (
                        period_id, date_str, day_num, action_type,
                        old_valid, new_valid, old_nda, new_nda,
                        old_lokal, new_lokal, old_haji, new_haji,
                        old_emas, new_emas, old_cash, new_cash,
                        catatan_perubahan, changed_at
                    ) VALUES (?, ?, ?, 'INPUT_AWAL', 0, ?, 0, ?, 0, ?, 0, ?, 0, ?, 0, ?, ?, ?)
                """, (
                    r["period_id"], r["date_str"], r["day_num"],
                    r["jlh_valid"], r["order_nda"], r["jlh_order_lokal"],
                    r["acc_haji"], r["acc_emas"], r["acc_cash"],
                    f"Pencatatan Buku Besar CADM (Tgl {r['day_num']})",
                    now_str
                ))
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

        # Ambil data lama sebelum diupdate untuk mencatat riwayat perubahan
        cursor.execute("SELECT * FROM daily_records WHERE date_str = ?", (date_str,))
        old_row = cursor.fetchone()
        old_vld = old_row["jlh_valid"] if old_row else 0
        old_n = old_row["order_nda"] if old_row else 0
        old_lok = old_row["jlh_order_lokal"] if old_row else 0
        old_haj = old_row["acc_haji"] if old_row else 0
        old_em = old_row["acc_emas"] if old_row else 0
        old_csh = old_row["acc_cash"] if old_row else 0
        old_cat = old_row["catatan"] if old_row else ""

        has_changed = (
            old_vld != jlh_valid or
            old_n != order_nda or
            old_lok != jlh_order_lokal or
            old_haj != acc_haji or
            old_em != acc_emas or
            old_csh != acc_cash or
            old_cat != catatan
        )

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

        # Catat ke change_history jika terjadi perubahan nilai numerik atau pengisian data
        if has_changed and (jlh_valid > 0 or old_vld > 0):
            action_type = "UPDATE" if (old_row and old_vld > 0) else "INPUT"
            desc_changes = []
            if old_vld != jlh_valid:
                desc_changes.append(f"Valid: {old_vld}➔{jlh_valid}")
            if old_n != order_nda:
                desc_changes.append(f"NDA: {old_n}➔{order_nda}")
            if old_lok != jlh_order_lokal:
                desc_changes.append(f"Lokal: {old_lok}➔{jlh_order_lokal}")
            if old_haj != acc_haji:
                desc_changes.append(f"Haji: {old_haj}➔{acc_haji}")
            if old_em != acc_emas:
                desc_changes.append(f"Emas: {old_em}➔{acc_emas}")
            if old_csh != acc_cash:
                desc_changes.append(f"Cash: {old_csh}➔{acc_cash}")
            catatan_str = ", ".join(desc_changes) if desc_changes else "Pembaruan Catatan"
            if catatan and catatan != old_cat:
                catatan_str += f" | Memo: {catatan}"

            cursor.execute("""
                INSERT INTO change_history (
                    period_id, date_str, day_num, action_type,
                    old_valid, new_valid, old_nda, new_nda,
                    old_lokal, new_lokal, old_haji, new_haji,
                    old_emas, new_emas, old_cash, new_cash,
                    catatan_perubahan, changed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                period_id, date_str, day_num, action_type,
                old_vld, jlh_valid, old_n, order_nda,
                old_lok, jlh_order_lokal, old_haj, acc_haji,
                old_em, acc_emas, old_csh, acc_cash,
                catatan_str, now
            ))

        conn.commit()


def get_change_history(period_id: Optional[int] = None, limit: int = 200) -> List[Dict[str, Any]]:
    """Mengambil riwayat audit perubahan data transaksi"""
    with get_db() as conn:
        cursor = conn.cursor()
        if period_id:
            cursor.execute("""
                SELECT h.*, p.year, p.month 
                FROM change_history h
                JOIN periods p ON h.period_id = p.id
                WHERE h.period_id = ?
                ORDER BY h.id DESC
                LIMIT ?
            """, (period_id, limit))
        else:
            cursor.execute("""
                SELECT h.*, p.year, p.month 
                FROM change_history h
                JOIN periods p ON h.period_id = p.id
                ORDER BY h.id DESC
                LIMIT ?
            """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


def get_database_tables_data() -> Dict[str, List[Dict[str, Any]]]:
    """Mengambil seluruh data mentah dari tabel-tabel database untuk dibaca dalam bentuk tabel"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM periods ORDER BY year DESC, month DESC")
        periods = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT * FROM daily_records WHERE jlh_valid > 0 ORDER BY date_str DESC")
        active_records = [dict(row) for row in cursor.fetchall()]

        cursor.execute("""
            SELECT h.*, p.year, p.month 
            FROM change_history h
            JOIN periods p ON h.period_id = p.id
            ORDER BY h.id DESC
        """)
        history = [dict(row) for row in cursor.fetchall()]

        return {
            "periods": periods,
            "daily_records": active_records,
            "change_history": history
        }

