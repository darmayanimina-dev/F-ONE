"""
calculations.py
Modul mesin kalkulasi dan validasi MATCH / MISMATCH untuk sistem F-ONE.
"""
from typing import List, Dict, Any, Tuple


def calculate_daily_match(
    jlh_valid: int,
    order_nda: int,
    order_lokal: int,
    acc_haji: int,
    acc_emas: int,
    acc_cash: int
) -> Dict[str, Any]:
    """
    Menghitung rekonsiliasi harian:
    Jumlah Valid harus sama dengan: Order NDA + Order Lokal + ACC Haji + ACC Emas + ACC Cash.
    """
    total_order_hari = order_nda + order_lokal + acc_haji + acc_emas + acc_cash
    selisih = jlh_valid - total_order_hari
    is_match = (selisih == 0)

    return {
        "total_order_hari": total_order_hari,
        "selisih": selisih,
        "is_match": is_match,
        "status_text": "MATCH" if is_match else f"MISMATCH: {selisih}",
        "badge_color": "green" if is_match else "red"
    }


def compute_cumulative_records(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Menghitung running total akumulatif berurutan dari tanggal 1 sampai akhir bulan:
    - Tot Order NDA
    - Tot Vld
    - Akumulasi Lokal, Haji, Emas, Cash
    - Menghitung status match harian & akumulatif
    """
    sorted_records = sorted(records, key=lambda r: r.get("day_num", 0))

    cum_nda = 0
    cum_vld = 0
    cum_lokal = 0
    cum_haji = 0
    cum_emas = 0
    cum_cash = 0

    processed = []
    has_mismatch_any_day = False
    mismatch_days = []

    for r in sorted_records:
        rec = dict(r)
        day_num = rec.get("day_num", 0)
        is_sun = bool(rec.get("is_sunday", 0))
        is_hol = bool(rec.get("is_holiday", 0))

        jlh_valid = int(rec.get("jlh_valid") or 0)
        order_nda = int(rec.get("order_nda") or 0)
        order_lokal = int(rec.get("jlh_order_lokal") or 0)
        acc_haji = int(rec.get("acc_haji") or 0)
        acc_emas = int(rec.get("acc_emas") or 0)
        acc_cash = int(rec.get("acc_cash") or 0)

        # Update akumulasi
        cum_nda += order_nda
        cum_vld += jlh_valid
        cum_lokal += order_lokal
        cum_haji += acc_haji
        cum_emas += acc_emas
        cum_cash += acc_cash

        rec["tot_order_nda"] = cum_nda
        rec["tot_vld"] = cum_vld

        # Validasi harian
        daily_res = calculate_daily_match(
            jlh_valid=jlh_valid,
            order_nda=order_nda,
            order_lokal=order_lokal,
            acc_haji=acc_haji,
            acc_emas=acc_emas,
            acc_cash=acc_cash
        )
        rec["daily_order_sum"] = daily_res["total_order_hari"]
        rec["daily_diff"] = daily_res["selisih"]
        rec["is_daily_match"] = daily_res["is_match"]
        rec["daily_status"] = daily_res["status_text"]

        # Akumulatif check
        cum_total_orders = cum_nda + cum_lokal + cum_haji + cum_emas + cum_cash
        cum_diff = cum_vld - cum_total_orders
        rec["cum_diff"] = cum_diff

        if not daily_res["is_match"] and not (is_sun or is_hol and jlh_valid == 0 and daily_res["total_order_hari"] == 0):
            has_mismatch_any_day = True
            mismatch_days.append(day_num)

        processed.append(rec)

    total_semua_order = cum_nda + cum_lokal + cum_haji + cum_emas + cum_cash
    selisih_bulanan = cum_vld - total_semua_order
    is_monthly_match = (selisih_bulanan == 0 and not has_mismatch_any_day)

    summary = {
        "total_valid_bulan": cum_vld,
        "total_order_nda": cum_nda,
        "total_order_lokal": cum_lokal,
        "total_acc_haji": cum_haji,
        "total_acc_emas": cum_emas,
        "total_acc_cash": cum_cash,
        "total_semua_order": total_semua_order,
        "selisih_bulanan": selisih_bulanan,
        "is_monthly_match": is_monthly_match,
        "has_mismatch_any_day": has_mismatch_any_day,
        "mismatch_days": mismatch_days,
        "status_text": "MATCH" if is_monthly_match else f"MISMATCH: Selisih {abs(selisih_bulanan)}",
        "jumlah_hari_terisi": len([r for r in processed if not r.get("is_sunday") and not r.get("is_holiday")])
    }

    return processed, summary
