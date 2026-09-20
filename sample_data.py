"""
sample_data.py
Memasukkan data riil dari buku besar manual CADM (Agustus 2026)
sebagai data awal agar CADM langsung familiar dan bisa mencocokkan dengan buku fisik.
"""
from database import get_or_create_period, upsert_daily_record, update_period_notes, update_period_status, init_db


def seed_sample_data():
    init_db()

    # Periode Agustus 2026 (Sesuai Buku Besar Fisik CADM)
    aug_period = get_or_create_period(2026, 8)
    period_id = aug_period["id"]

    # Data transaksi Agustus 2026
    # day, jlh_vld, nda, lokal, haji, emas, cash, is_hol, hol_name, cat
    aug_data = [
        (1, 10, 9, 1, 0, 0, 0, False, "", ""),
        (2, 0, 0, 0, 0, 0, 0, False, "", ""),  # Minggu
        (3, 11, 11, 0, 0, 0, 0, False, "", ""),
        (4, 16, 16, 0, 0, 0, 0, False, "", ""),
        (5, 10, 10, 0, 0, 0, 0, False, "", ""),
        (6, 17, 16, 1, 0, 0, 0, False, "", ""),
        (7, 22, 20, 2, 0, 0, 0, False, "", ""),
        (8, 7, 7, 0, 0, 0, 0, False, "", ""),
        (9, 0, 0, 0, 0, 0, 0, False, "", ""),  # Minggu
        (10, 17, 17, 0, 0, 0, 0, False, "", ""),
        (11, 13, 13, 0, 0, 0, 0, False, "", ""),
        (12, 12, 11, 1, 0, 0, 0, False, "", ""),
        (13, 23, 23, 0, 0, 0, 0, False, "", ""),
        (14, 10, 9, 1, 0, 0, 0, False, "", ""),
        (15, 10, 10, 0, 0, 0, 0, False, "", ""),
        (16, 0, 0, 0, 0, 0, 0, False, "", ""),  # Minggu
        (17, 0, 0, 0, 0, 0, 0, True, "17 Agustus (HUT RI)", "Libur Nasional HUT RI"),
        (18, 8, 8, 0, 0, 0, 0, False, "", ""),
        (19, 22, 21, 1, 0, 0, 0, False, "", ""),
        (20, 14, 14, 0, 0, 0, 0, False, "", ""),
        (21, 14, 13, 0, 1, 0, 0, False, "", ""),
        (22, 10, 8, 1, 1, 0, 0, False, "", ""),
        (23, 0, 0, 0, 0, 0, 0, False, "", ""),  # Minggu
        (24, 17, 17, 0, 0, 0, 0, False, "", ""),
        (25, 0, 0, 0, 0, 0, 0, True, "Maulid Nabi Muhammad SAW", "Libur Nasional Maulid Nabi"),
        (26, 14, 13, 0, 0, 0, 1, False, "", ""),
        (27, 14, 14, 0, 0, 0, 0, False, "", "Catatan: Rokiah 27/8"),
        (28, 11, 9, 0, 1, 0, 1, False, "", ""),
        (29, 9, 8, 1, 0, 0, 0, False, "", ""),
        (30, 0, 0, 0, 0, 0, 0, False, "", ""),  # Minggu
        (31, 15, 15, 0, 0, 0, 0, False, "", ""),
    ]

    sundays = {2, 9, 16, 23, 30}

    for day, jlh_vld, nda, lokal, haji, emas, cash, is_hol, hol_name, cat in aug_data:
        date_str = f"2026-08-{day:02d}"
        is_sun = day in sundays
        upsert_daily_record(
            period_id=period_id,
            date_str=date_str,
            day_num=day,
            is_sunday=is_sun,
            is_holiday=is_hol,
            holiday_name=hol_name,
            jlh_valid=jlh_vld,
            order_nda=nda,
            jlh_order_lokal=lokal,
            acc_haji=haji,
            acc_emas=emas,
            acc_cash=cash,
            catatan=cat
        )

    # Catatan buku besar Agustus persis seperti di foto CADM
    notes_august = (
        "Rekap Manual CADM:\n"
        "NDA: 312\n"
        "Lokal: 9\n"
        "Cash: 2\n"
        "Haji: 3\n"
        "Total Order: 326\n"
        "Total Valid: 326 (✓ MATCH)\n\n"
        "yg blm:\n"
        "- Rokiah 27/8 Royo\n"
        "- 8 29/8\n"
        "- 15 31/8\n"
        "Total 23"
    )
    update_period_notes(period_id, notes_august)
    update_period_status(period_id, "COMPLETED")

    # Siapkan juga Periode Aktif September 2026
    sep_period = get_or_create_period(2026, 9)
    # Masukkan beberapa contoh data hari awal September agar terlihat aktif dan hidup
    sep_id = sep_period["id"]
    upsert_daily_record(sep_id, "2026-09-01", 1, False, False, "", 15, 14, 1, 0, 0, 0, "Awal bulan lancar")
    upsert_daily_record(sep_id, "2026-09-02", 2, False, False, "", 18, 17, 0, 1, 0, 0, "")
    upsert_daily_record(sep_id, "2026-09-03", 3, False, False, "", 20, 18, 1, 0, 0, 1, "")


if __name__ == "__main__":
    seed_sample_data()
    print("Sample data seeded successfully!")
