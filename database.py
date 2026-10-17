"""
database.py
Layer penyimpanan data F-ONE dengan dukungan Dual-Backend:
1. Turso Cloud (LibSQL) - Penyimpanan permanen di cloud (bebas sleep / restart Streamlit).
2. SQLite Lokal (fone_database.db) - Fallback otomatis jika berjalan offline atau tanpa konfigurasi cloud.
"""
import sqlite3
import calendar
import datetime
import os
import json
import urllib.request
from typing import List, Dict, Any, Optional, Tuple, Iterable

DB_FILE = "fone_database.db"

MONTH_NAMES_ID = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}


# --- Turso Cloud Client Implementation ---

def get_turso_config() -> Tuple[Optional[str], Optional[str]]:
    """Mendapatkan konfigurasi Turso dari Streamlit Secrets, secrets.toml lokal, atau Environment Variables"""
    url = None
    token = None
    
    # 1. Coba baca dari streamlit.secrets jika sedang berjalan di Streamlit
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            url = st.secrets.get("TURSO_DATABASE_URL")
            token = st.secrets.get("TURSO_AUTH_TOKEN")
    except Exception:
        pass

    # 2. Coba baca dari file .streamlit/secrets.toml lokal jika belum dapat
    if not url or not token:
        try:
            secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
            if os.path.exists(secrets_path):
                try:
                    import tomllib
                    with open(secrets_path, "rb") as f:
                        data = tomllib.load(f)
                        url = url or data.get("TURSO_DATABASE_URL")
                        token = token or data.get("TURSO_AUTH_TOKEN")
                except ImportError:
                    pass
        except Exception:
            pass

    # 3. Coba baca dari environment variables
    if not url:
        url = os.environ.get("TURSO_DATABASE_URL")
    if not token:
        token = os.environ.get("TURSO_AUTH_TOKEN")

    if url and url.startswith("libsql://"):
        host = url[len("libsql://"):]
        url = f"https://{host}/v2/pipeline"
    elif url and url.startswith("https://") and not url.endswith("/v2/pipeline"):
        url = url.rstrip("/") + "/v2/pipeline"

    return url, token


def is_using_turso() -> bool:
    """Memeriksa apakah database terhubung ke Turso Cloud"""
    url, token = get_turso_config()
    return bool(url and token)


def get_active_storage_mode() -> str:
    """Mengembalikan label database yang sedang aktif"""
    return "Turso Cloud" if is_using_turso() else "SQLite Lokal"


class TursoRow(dict):
    """Wrapper baris Turso agar kompatibel dengan sqlite3.Row (bisa diakses via key maupun index)"""
    def __init__(self, cols: List[str], values: List[Any]):
        super().__init__(zip(cols, values))
        self._values = list(values)

    def __getitem__(self, item: Any) -> Any:
        if isinstance(item, int):
            return self._values[item]
        return super().__getitem__(item)


def _to_turso_arg(v: Any) -> Dict[str, Any]:
    if v is None:
        return {"type": "null"}
    elif isinstance(v, bool):
        return {"type": "integer", "value": "1" if v else "0"}
    elif isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    elif isinstance(v, float):
        return {"type": "float", "value": v}
    else:
        return {"type": "text", "value": str(v)}


def _from_turso_val(c: Any) -> Any:
    if not isinstance(c, dict):
        return c
    t = c.get("type")
    v = c.get("value")
    if t == "null":
        return None
    elif t == "integer":
        return int(v)
    elif t == "float":
        return float(v)
    elif t == "text":
        return str(v)
    return v


def _exec_turso_pipeline(requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    url, token = get_turso_config()
    if not url or not token:
        raise ValueError("Turso credentials tidak ditemukan.")

    payload = {"requests": requests + [{"type": "close"}]}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        for idx, r in enumerate(res.get("results", [])):
            if r.get("type") == "error":
                raise Exception(f"Turso Error (langkah {idx}): {r.get('error', {}).get('message', 'Unknown')}")
        return res.get("results", [])


def _turso_query(sql: str, params: Optional[Iterable[Any]] = None) -> List[TursoRow]:
    stmt: Dict[str, Any] = {"sql": sql}
    if params:
        stmt["args"] = [_to_turso_arg(p) for p in params]
    results = _exec_turso_pipeline([{"type": "execute", "stmt": stmt}])
    res = results[0]["response"]["result"]
    cols = [c["name"] for c in res["cols"]]
    return [TursoRow(cols, [_from_turso_val(c) for c in row]) for row in res["rows"]]


def _turso_query_one(sql: str, params: Optional[Iterable[Any]] = None) -> Optional[TursoRow]:
    rows = _turso_query(sql, params)
    return rows[0] if rows else None


def _turso_execute(sql: str, params: Optional[Iterable[Any]] = None) -> Optional[int]:
    stmt: Dict[str, Any] = {"sql": sql}
    if params:
        stmt["args"] = [_to_turso_arg(p) for p in params]
    results = _exec_turso_pipeline([{"type": "execute", "stmt": stmt}])
    res = results[0]["response"]["result"]
    return res.get("last_insert_rowid")


def _turso_execute_batch(stmts: List[Tuple[str, Optional[Iterable[Any]]]]):
    requests = []
    for sql, params in stmts:
        stmt: Dict[str, Any] = {"sql": sql}
        if params:
            stmt["args"] = [_to_turso_arg(p) for p in params]
        requests.append({"type": "execute", "stmt": stmt})
    _exec_turso_pipeline(requests)


# --- SQLite Local Helper ---

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# --- Main Application Database Functions ---

def init_db():
    """Inisialisasi tabel di database (Turso Cloud atau SQLite lokal)"""
    schema_stmts = [
        """
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
        """,
        """
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
        """,
        """
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
        """
    ]

    if is_using_turso():
        _turso_execute_batch([(sql, None) for sql in schema_stmts])
    else:
        with get_db() as conn:
            cursor = conn.cursor()
            for sql in schema_stmts:
                cursor.execute(sql)
            conn.commit()


def reset_change_history(period_id: Optional[int] = None):
    """Mereset/menghapus catatan riwayat perubahan"""
    if is_using_turso():
        if period_id:
            _turso_execute("DELETE FROM change_history WHERE period_id = ?", (period_id,))
        else:
            _turso_execute("DELETE FROM change_history")
    else:
        with get_db() as conn:
            cursor = conn.cursor()
            if period_id:
                cursor.execute("DELETE FROM change_history WHERE period_id = ?", (period_id,))
            else:
                cursor.execute("DELETE FROM change_history")
            conn.commit()


def get_or_create_period(year: int, month: int) -> Dict[str, Any]:
    """Mengambil periode atau membuatnya jika belum ada"""
    if is_using_turso():
        row = _turso_query_one("SELECT * FROM periods WHERE year = ? AND month = ?", (year, month))
        if row:
            period = dict(row)
        else:
            now = datetime.datetime.now().isoformat()
            period_id = _turso_execute("""
                INSERT INTO periods (year, month, status, notes, created_at, updated_at)
                VALUES (?, ?, 'ACTIVE', '', ?, ?)
            """, (year, month, now, now))
            row = _turso_query_one("SELECT * FROM periods WHERE id = ?", (period_id,))
            period = dict(row) if row else {"id": period_id, "year": year, "month": month, "status": "ACTIVE", "notes": ""}
    else:
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
    stmts = []
    for day in range(1, num_days + 1):
        date_obj = datetime.date(year, month, day)
        date_str = date_obj.strftime("%Y-%m-%d")
        is_sunday = 1 if date_obj.weekday() == 6 else 0
        sql = """
            INSERT OR IGNORE INTO daily_records 
            (period_id, date_str, day_num, is_sunday, is_holiday, holiday_name, jlh_valid, order_nda, jlh_order_lokal, acc_haji, acc_emas, acc_cash, catatan)
            VALUES (?, ?, ?, ?, 0, '', 0, 0, 0, 0, 0, 0, '')
        """
        stmts.append((sql, (period_id, date_str, day, is_sunday)))

    if is_using_turso():
        _turso_execute_batch(stmts)
    else:
        with get_db() as conn:
            cursor = conn.cursor()
            for sql, params in stmts:
                cursor.execute(sql, params)
            conn.commit()


def list_all_years() -> List[int]:
    if is_using_turso():
        rows = _turso_query("SELECT DISTINCT year FROM periods ORDER BY year DESC")
        return [row[0] for row in rows]
    else:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT year FROM periods ORDER BY year DESC")
            return [row[0] for row in cursor.fetchall()]


def list_periods_by_year(year: int) -> List[Dict[str, Any]]:
    if is_using_turso():
        rows = _turso_query("SELECT * FROM periods WHERE year = ? ORDER BY month DESC", (year,))
        return [dict(row) for row in rows]
    else:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM periods WHERE year = ? ORDER BY month DESC", (year,))
            return [dict(row) for row in cursor.fetchall()]


def get_period_by_id(period_id: int) -> Optional[Dict[str, Any]]:
    if is_using_turso():
        row = _turso_query_one("SELECT * FROM periods WHERE id = ?", (period_id,))
        return dict(row) if row else None
    else:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM periods WHERE id = ?", (period_id,))
            row = cursor.fetchone()
            return dict(row) if row else None


def update_period_status(period_id: int, status: str):
    now = datetime.datetime.now().isoformat()
    completed_at = now if status == 'COMPLETED' else None
    sql = """
        UPDATE periods 
        SET status = ?, completed_at = ?, updated_at = ?
        WHERE id = ?
    """
    params = (status, completed_at, now, period_id)
    if is_using_turso():
        _turso_execute(sql, params)
    else:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()


def update_period_notes(period_id: int, notes: str):
    now = datetime.datetime.now().isoformat()
    sql = """
        UPDATE periods 
        SET notes = ?, updated_at = ?
        WHERE id = ?
    """
    params = (notes, now, period_id)
    if is_using_turso():
        _turso_execute(sql, params)
    else:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()


def get_daily_records_by_period(period_id: int) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM daily_records WHERE period_id = ? ORDER BY day_num ASC"
    if is_using_turso():
        rows = _turso_query(sql, (period_id,))
        return [dict(row) for row in rows]
    else:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (period_id,))
            return [dict(row) for row in cursor.fetchall()]


def get_daily_record_by_date(date_str: str) -> Optional[Dict[str, Any]]:
    sql = "SELECT * FROM daily_records WHERE date_str = ?"
    if is_using_turso():
        row = _turso_query_one(sql, (date_str,))
        return dict(row) if row else None
    else:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (date_str,))
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
    now = datetime.datetime.now().isoformat()

    # Ambil data lama sebelum diupdate untuk mencatat riwayat perubahan
    old_row = get_daily_record_by_date(date_str)
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

    upsert_sql = """
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
    """
    upsert_params = (
        period_id, date_str, day_num,
        1 if is_sunday else 0,
        1 if is_holiday else 0,
        holiday_name,
        jlh_valid, order_nda, jlh_order_lokal, acc_haji, acc_emas, acc_cash,
        catatan, now
    )

    history_sql = None
    history_params = None

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

        history_sql = """
            INSERT INTO change_history (
                period_id, date_str, day_num, action_type,
                old_valid, new_valid, old_nda, new_nda,
                old_lokal, new_lokal, old_haji, new_haji,
                old_emas, new_emas, old_cash, new_cash,
                catatan_perubahan, changed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        history_params = (
            period_id, date_str, day_num, action_type,
            old_vld, jlh_valid, old_n, order_nda,
            old_lok, jlh_order_lokal, old_haj, acc_haji,
            old_em, acc_emas, old_csh, acc_cash,
            catatan_str, now
        )

    if is_using_turso():
        stmts = [(upsert_sql, upsert_params)]
        if history_sql and history_params:
            stmts.append((history_sql, history_params))
        _turso_execute_batch(stmts)
    else:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(upsert_sql, upsert_params)
            if history_sql and history_params:
                cursor.execute(history_sql, history_params)
            conn.commit()


def get_change_history(period_id: Optional[int] = None, limit: int = 200) -> List[Dict[str, Any]]:
    """Mengambil riwayat audit perubahan data transaksi"""
    if is_using_turso():
        if period_id:
            sql = """
                SELECT h.*, p.year, p.month 
                FROM change_history h
                JOIN periods p ON h.period_id = p.id
                WHERE h.period_id = ?
                ORDER BY h.id DESC
                LIMIT ?
            """
            rows = _turso_query(sql, (period_id, limit))
        else:
            sql = """
                SELECT h.*, p.year, p.month 
                FROM change_history h
                JOIN periods p ON h.period_id = p.id
                ORDER BY h.id DESC
                LIMIT ?
            """
            rows = _turso_query(sql, (limit,))
        return [dict(row) for row in rows]
    else:
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
    if is_using_turso():
        periods = [dict(r) for r in _turso_query("SELECT * FROM periods ORDER BY year DESC, month DESC")]
        active_records = [dict(r) for r in _turso_query("SELECT * FROM daily_records WHERE jlh_valid > 0 ORDER BY date_str DESC")]
        history = [dict(r) for r in _turso_query("""
            SELECT h.*, p.year, p.month 
            FROM change_history h
            JOIN periods p ON h.period_id = p.id
            ORDER BY h.id DESC
        """)]
    else:
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
