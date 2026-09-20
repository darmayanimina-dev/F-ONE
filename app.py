"""
app.py
Aplikasi F-ONE (Fidusia Order & Numbering Efficiency)
Desain Minimalis, Bersih, dan Sangat Mudah Digunakan untuk CADM:
- Tampilan tenang & lapang (tanpa elemen berlebihan).
- Status rekonsiliasi ringkas: Total Valid vs Total Order.
- Buku besar rapi dengan tombol Edit langsung di setiap baris.
- Tanpa data bawaan (data 100% bersih, siap diisi sendiri).
"""
import datetime
import calendar
import io
import textwrap
import pandas as pd
import streamlit as st

from database import (
    init_db,
    get_or_create_period,
    list_all_years,
    list_periods_by_year,
    get_period_by_id,
    get_daily_records_by_period,
    get_daily_record_by_date,
    upsert_daily_record,
    update_period_status,
    update_period_notes,
    MONTH_NAMES_ID
)
from calculations import compute_cumulative_records, calculate_daily_match
from pdf_generator import generate_f_one_pdf

# Helper HTML render bersih tanpa risiko markdown code block
def render_html(html_str: str):
    lines = [line.strip() for line in html_str.strip().splitlines() if line.strip()]
    st.markdown("".join(lines), unsafe_allow_html=True)


# 1. Konfigurasi Halaman Minimalis
st.set_page_config(
    page_title="F-ONE | Rekap Fidusia",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Inisialisasi Database Bersih (Tanpa Data Sampel)
init_db()

# 2. Styling Minimalis & Ramah Aksesibilitas
render_html("""
<style>
    /* Tipografi Bersih & Elegan */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        color: #1E293B !important;
        font-size: 16px !important;
    }

    /* Top Bar Minimalis */
    .mini-topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 0;
        border-bottom: 2px solid #E2E8F0;
        margin-bottom: 1.25rem;
    }
    .brand-title {
        font-size: 1.75rem;
        font-weight: 800;
        color: #1E3A8A;
        letter-spacing: -0.5px;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }
    .brand-tag {
        font-size: 0.9rem;
        color: #64748B;
        font-weight: 500;
        margin-left: 8px;
    }

    /* Bar Ringkasan Minimalis */
    .summary-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #FFFFFF;
        border: 1.5px solid #E2E8F0;
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        flex-wrap: wrap;
        gap: 12px;
    }
    .summary-stat {
        display: flex;
        align-items: baseline;
        gap: 10px;
    }
    .stat-label {
        font-size: 0.95rem;
        color: #64748B;
        font-weight: 600;
    }
    .stat-number {
        font-size: 1.8rem;
        font-weight: 800;
        color: #0F172A;
    }
    .pill-match {
        background-color: #DCFCE7;
        color: #15803D;
        border: 1.5px solid #86EFAC;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 1.05rem;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .pill-mismatch {
        background-color: #FEE2E2;
        color: #B91C1C;
        border: 1.5px solid #FCA5A5;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 1.05rem;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }

    /* Tabel Minimalis */
    .table-container {
        border: 1.5px solid #CBD5E1;
        border-radius: 12px;
        overflow: hidden;
        background: white;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
    }
    table.mini-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 1rem;
    }
    table.mini-table th {
        background-color: #1E3A8A;
        color: white;
        font-weight: 700;
        padding: 10px 8px;
        text-align: center;
        font-size: 0.9rem;
        border: 1px solid #2563EB;
        white-space: pre-line;
    }
    table.mini-table td {
        padding: 8px 6px;
        text-align: center;
        border: 1px solid #E2E8F0;
        font-weight: 500;
    }
    tr.row-sun {
        background-color: #EFF6FF !important; /* Biru lembut */
        color: #1E40AF !important;
        font-weight: 600;
    }
    tr.row-hol {
        background-color: #FEF9C3 !important; /* Kuning lembut */
        color: #854D0E !important;
        font-weight: 600;
    }
    tr.row-tot {
        background-color: #F1F5F9 !important;
        font-weight: 800 !important;
        font-size: 1.05rem !important;
        border-top: 2px solid #0F172A !important;
    }
    .badge-ok {
        color: #15803D;
        font-weight: 700;
        font-size: 0.85rem;
    }
    .badge-err {
        color: #B91C1C;
        font-weight: 700;
        font-size: 0.85rem;
    }

    /* Tombol Utama Minimalis */
    div.stButton > button {
        border-radius: 10px !important;
        font-weight: 700 !important;
        padding: 0.6rem 1.2rem !important;
        min-height: 48px !important;
    }
</style>
""")


# 3. Navigasi Periode Aktif
today = datetime.date.today()
current_year = today.year
current_month = today.month

if "selected_year" not in st.session_state:
    st.session_state["selected_year"] = current_year
if "selected_month" not in st.session_state:
    st.session_state["selected_month"] = current_month
if "dialog_target_date" not in st.session_state:
    st.session_state["dialog_target_date"] = None

# Ambil periode yang dipilih (kosong tanpa data dummy)
active_period = get_or_create_period(st.session_state["selected_year"], st.session_state["selected_month"])
records = get_daily_records_by_period(active_period["id"])
processed_records, summary = compute_cumulative_records(records)


# 4. Modal Dialog Input / Edit (@st.dialog)
@st.dialog("📝 Input / Edit Order")
def dialog_input_order(default_date_str: str = None):
    p_yr = st.session_state["selected_year"]
    p_mo = st.session_state["selected_month"]
    _, num_days = calendar.monthrange(p_yr, p_mo)

    if default_date_str:
        try:
            curr_date = datetime.datetime.strptime(default_date_str, "%Y-%m-%d").date()
        except Exception:
            curr_date = datetime.date(p_yr, p_mo, 1)
    else:
        if p_yr == today.year and p_mo == today.month:
            curr_date = today
        else:
            curr_date = datetime.date(p_yr, p_mo, 1)

    st.caption(f"Periode: **{MONTH_NAMES_ID[p_mo]} {p_yr}**")

    tgl_selected = st.date_input(
        "Tanggal:",
        value=curr_date,
        min_value=datetime.date(p_yr, p_mo, 1),
        max_value=datetime.date(p_yr, p_mo, num_days),
        format="DD/MM/YYYY"
    )

    tgl_str = tgl_selected.strftime("%Y-%m-%d")
    existing_rec = get_daily_record_by_date(tgl_str) or {}
    day_num = tgl_selected.day
    is_sunday_auto = (tgl_selected.weekday() == 6)

    c_opt1, c_opt2 = st.columns(2)
    with c_opt1:
        is_holiday = st.checkbox("🚩 Tanggal Merah / Libur", value=bool(existing_rec.get("is_holiday", 0)))
    with c_opt2:
        is_sunday = st.checkbox("🏖️ Hari Minggu", value=bool(existing_rec.get("is_sunday", 1 if is_sunday_auto else 0)))

    holiday_name = ""
    if is_holiday:
        holiday_name = st.text_input("Keterangan Libur:", value=existing_rec.get("holiday_name", ""))

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        order_nda = st.number_input("Order NDA (Notadana):", min_value=0, value=int(existing_rec.get("order_nda", 0)), step=1)
        order_lokal = st.number_input("Notaris Lokal (PT/CV):", min_value=0, value=int(existing_rec.get("jlh_order_lokal", 0)), step=1)
        acc_cash = st.number_input("ACC Cash:", min_value=0, value=int(existing_rec.get("acc_cash", 0)), step=1)

    with c2:
        acc_haji = st.number_input("ACC Haji:", min_value=0, value=int(existing_rec.get("acc_haji", 0)), step=1)
        acc_emas = st.number_input("ACC Emas:", min_value=0, value=int(existing_rec.get("acc_emas", 0)), step=1)

    sum_orders = order_nda + order_lokal + acc_haji + acc_emas + acc_cash
    def_vld = int(existing_rec.get("jlh_valid", sum_orders if sum_orders > 0 else 0))

    st.divider()
    cv1, cv2 = st.columns([1.2, 1])
    with cv1:
        jlh_valid = st.number_input("Jumlah Valid (Total Valid Hari Ini):", min_value=0, value=def_vld, step=1)

    diff = jlh_valid - sum_orders
    with cv2:
        if diff == 0:
            render_html(f"""
            <div style='background: #DCFCE7; border: 2px solid #86EFAC; color: #166534; padding: 10px; border-radius: 8px; text-align: center; margin-top: 20px;'>
                <b style='font-size: 1.1rem;'>🟢 MATCH</b><br/>
                <span style='font-size: 0.85rem;'>Valid = Order ({sum_orders})</span>
            </div>
            """)
        else:
            render_html(f"""
            <div style='background: #FEE2E2; border: 2px solid #FCA5A5; color: #991B1B; padding: 10px; border-radius: 8px; text-align: center; margin-top: 20px;'>
                <b style='font-size: 1.1rem;'>🔴 MISMATCH</b><br/>
                <span style='font-size: 0.85rem;'>Selisih: {abs(diff)}</span>
            </div>
            """)

    catatan = st.text_input("Catatan (Opsional):", value=existing_rec.get("catatan", ""))

    st.write("")
    b1, b2 = st.columns(2)
    with b1:
        if st.button("💾 Simpan", type="primary", use_container_width=True):
            upsert_daily_record(
                period_id=active_period["id"],
                date_str=tgl_str,
                day_num=day_num,
                is_sunday=is_sunday,
                is_holiday=is_holiday,
                holiday_name=holiday_name,
                jlh_valid=jlh_valid,
                order_nda=order_nda,
                jlh_order_lokal=order_lokal,
                acc_haji=acc_haji,
                acc_emas=acc_emas,
                acc_cash=acc_cash,
                catatan=catatan
            )
            st.success("Tersimpan!")
            st.rerun()
    with b2:
        if st.button("Batal", use_container_width=True):
            st.rerun()


# 5. Top Bar Minimalis
nama_bulan = MONTH_NAMES_ID[st.session_state["selected_month"]]
p_title = f"{nama_bulan} {st.session_state['selected_year']}"

col_brand, col_pilih = st.columns([3, 2])
with col_brand:
    render_html(f"""
    <div class="mini-topbar">
        <div>
            <span class="brand-title">⚖️ F-ONE</span>
            <span class="brand-tag">Rekap Order Fidusia &bull; {p_title}</span>
        </div>
    </div>
    """)

with col_pilih:
    p_c1, p_c2 = st.columns(2)
    with p_c1:
        yrs = list_all_years()
        if current_year not in yrs:
            yrs.insert(0, current_year)
        sel_y = st.selectbox("Tahun", options=yrs, index=yrs.index(st.session_state["selected_year"]) if st.session_state["selected_year"] in yrs else 0, label_visibility="collapsed")
        if sel_y != st.session_state["selected_year"]:
            st.session_state["selected_year"] = sel_y
            st.rerun()
    with p_c2:
        sel_m = st.selectbox("Bulan", options=list(range(1, 13)), index=st.session_state["selected_month"] - 1, format_func=lambda m: MONTH_NAMES_ID[m], label_visibility="collapsed")
        if sel_m != st.session_state["selected_month"]:
            st.session_state["selected_month"] = sel_m
            st.rerun()


# 6. Bar Ringkasan Minimalis (Status Match & Total Utama)
status_pill = (
    f'<div class="pill-match">🟢 MATCH (Pas)</div>'
    if summary["is_monthly_match"]
    else f'<div class="pill-mismatch">🔴 MISMATCH (Selisih {abs(summary["selisih_bulanan"])})</div>'
)

render_html(f"""
<div class="summary-bar">
    <div class="summary-stat">
        <span class="stat-label">Total Valid:</span>
        <span class="stat-number" style="color: #1D4ED8;">{summary['total_valid_bulan']}</span>
    </div>
    <div class="summary-stat">
        <span class="stat-label">Total Order (NDA + Lokal + ACC):</span>
        <span class="stat-number" style="color: #0F766E;">{summary['total_semua_order']}</span>
    </div>
    <div>
        {status_pill}
    </div>
</div>
""")


# 7. Action Bar Sederhana
btn_c1, btn_c2, btn_c3, btn_c4 = st.columns([2.5, 1.5, 1.5, 2.5])
with btn_c1:
    if st.button("➕ Catat Order Hari Ini", type="primary", use_container_width=True):
        dialog_input_order()

with btn_c2:
    pdf_bytes = generate_f_one_pdf(active_period, processed_records, summary)
    st.download_button(
        label="📄 Unduh PDF",
        data=pdf_bytes,
        file_name=f"F-ONE_{nama_bulan}_{st.session_state['selected_year']}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

with btn_c3:
    # Excel Download
    x_buf = io.BytesIO()
    x_rows = []
    for r in processed_records:
        day_num = r.get("day_num", 0)
        is_sun = bool(r.get("is_sunday", 0))
        is_hol = bool(r.get("is_holiday", 0))
        hol_name = r.get("holiday_name", "")
        catatan = r.get("catatan", "")
        
        status_keterangan = "MINGGU" if is_sun else (hol_name if is_hol else ("MATCH" if r.get("is_daily_match", True) else f"MISMATCH ({r.get('daily_diff', 0)})"))
        if catatan:
            status_keterangan += f" - {catatan}"

        x_rows.append({
            "Tgl": f"{day_num}/{active_period['month']}",
            "Jlh Valid": r.get("jlh_valid", 0) if (r.get("jlh_valid", 0) > 0 or not (is_sun or is_hol)) else "-",
            "Order NDA": r.get("order_nda", 0) if (r.get("order_nda", 0) > 0 or not (is_sun or is_hol)) else "-",
            "Tot NDA": r.get("tot_order_nda", 0),
            "Tot Valid": r.get("tot_vld", 0),
            "Lokal": r.get("jlh_order_lokal", 0) if r.get("jlh_order_lokal", 0) > 0 else "-",
            "ACC Haji": r.get("acc_haji", 0) if r.get("acc_haji", 0) > 0 else "-",
            "ACC Emas": r.get("acc_emas", 0) if r.get("acc_emas", 0) > 0 else "-",
            "ACC Cash": r.get("acc_cash", 0) if r.get("acc_cash", 0) > 0 else "-",
            "Status": status_keterangan
        })
    x_rows.append({
        "Tgl": "TOTAL",
        "Jlh Valid": summary['total_valid_bulan'],
        "Order NDA": summary['total_order_nda'],
        "Tot NDA": summary['total_order_nda'],
        "Tot Valid": summary['total_valid_bulan'],
        "Lokal": summary['total_order_lokal'],
        "ACC Haji": summary['total_acc_haji'],
        "ACC Emas": summary['total_acc_emas'],
        "ACC Cash": summary['total_acc_cash'],
        "Status": summary['status_text']
    })
    with pd.ExcelWriter(x_buf, engine='openpyxl') as writer:
        pd.DataFrame(x_rows).to_excel(writer, index=False, sheet_name=f"{nama_bulan}_{active_period['year']}")
    
    st.download_button(
        label="📊 Excel",
        data=x_buf.getvalue(),
        file_name=f"F-ONE_{nama_bulan}_{st.session_state['selected_year']}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

with btn_c4:
    if active_period["status"] == "ACTIVE":
        if st.button("✓ Selesaikan Periode", use_container_width=True):
            update_period_status(active_period["id"], "COMPLETED")
            st.success("Periode ditandai selesai.")
            st.rerun()
    else:
        if st.button("🔓 Buka Kembali Periode", use_container_width=True):
            update_period_status(active_period["id"], "ACTIVE")
            st.rerun()


# 8. Tabel Buku Besar Bersih & Interaktif
st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)

mo = active_period["month"]
table_html_rows = []

for idx, r in enumerate(processed_records):
    day_num = r.get("day_num", 0)
    tgl_disp = f"{day_num}/{mo}"
    is_sun = bool(r.get("is_sunday", 0))
    is_hol = bool(r.get("is_holiday", 0))
    hol_name = r.get("holiday_name", "")
    catatan = r.get("catatan", "")

    jlh_vld = r.get("jlh_valid", 0)
    order_nda = r.get("order_nda", 0)
    tot_nda = r.get("tot_order_nda", 0)
    tot_vld = r.get("tot_vld", 0)
    lokal = r.get("jlh_order_lokal", 0)
    haji = r.get("acc_haji", 0)
    emas = r.get("acc_emas", 0)
    cash = r.get("acc_cash", 0)
    is_match = r.get("is_daily_match", True)
    daily_diff = r.get("daily_diff", 0)

    # Styling baris
    if is_sun:
        r_cls = "row-sun"
        st_txt = "<i>Minggu</i>"
    elif is_hol:
        r_cls = "row-hol"
        st_txt = f"<b>{hol_name if hol_name else 'Libur'}</b>"
    else:
        r_cls = ""
        has_entry = (jlh_vld > 0 or order_nda > 0 or lokal > 0 or haji > 0 or emas > 0 or cash > 0)
        if has_entry:
            st_txt = "<span class='badge-ok'>✓ MATCH</span>" if is_match else f"<span class='badge-err'>⚠ SELISIH {daily_diff}</span>"
        else:
            st_txt = "<span style='color:#94A3B8;'>-</span>"
        if catatan:
            st_txt += f" <small style='color:#64748B;'>({catatan})</small>"

    v_disp = str(jlh_vld) if jlh_vld > 0 else "-"
    n_disp = str(order_nda) if order_nda > 0 else "-"
    tn_disp = str(tot_nda) if tot_nda > 0 else "-"
    tv_disp = str(tot_vld) if tot_vld > 0 else "-"
    l_disp = str(lokal) if lokal > 0 else "-"
    h_disp = str(haji) if haji > 0 else "-"
    e_disp = str(emas) if emas > 0 else "-"
    c_disp = str(cash) if cash > 0 else "-"

    table_html_rows.append(
        f'<tr class="{r_cls}">'
        f'<td style="font-weight:700;">{tgl_disp}</td>'
        f'<td>{v_disp}</td>'
        f'<td>{n_disp}</td>'
        f'<td style="color:#0F766E; font-weight:600;">{tn_disp}</td>'
        f'<td style="color:#1D4ED8; font-weight:700;">{tv_disp}</td>'
        f'<td>{l_disp}</td>'
        f'<td>{h_disp}</td>'
        f'<td>{e_disp}</td>'
        f'<td>{c_disp}</td>'
        f'<td style="text-align: left; padding-left: 10px;">{st_txt}</td>'
        f'</tr>'
    )

# Baris Total
total_row = (
    f'<tr class="row-tot">'
    f'<td>TOTAL</td>'
    f'<td>{summary["total_valid_bulan"]}</td>'
    f'<td>{summary["total_order_nda"]}</td>'
    f'<td>{summary["total_order_nda"]}</td>'
    f'<td>{summary["total_valid_bulan"]}</td>'
    f'<td>{summary["total_order_lokal"]}</td>'
    f'<td>{summary["total_acc_haji"]}</td>'
    f'<td>{summary["total_acc_emas"]}</td>'
    f'<td>{summary["total_acc_cash"]}</td>'
    f'<td style="text-align: left; padding-left: 10px; font-weight: 800;">{summary["status_text"]}</td>'
    f'</tr>'
)
table_html_rows.append(total_row)

final_table = (
    '<div class="table-container">'
    '<table class="mini-table">'
    '<thead>'
    '<tr>'
    '<th style="width: 70px;">Tgl<br/>Vld</th>'
    '<th style="width: 70px;">Jlh<br/>Vld</th>'
    '<th style="width: 75px;">Order<br/>NDA</th>'
    '<th style="width: 85px;">Tot NDA</th>'
    '<th style="width: 80px;">Tot Vld</th>'
    '<th style="width: 75px;">Lokal</th>'
    '<th style="width: 65px;">Haji</th>'
    '<th style="width: 65px;">Emas</th>'
    '<th style="width: 65px;">Cash</th>'
    '<th>Status &amp; Keterangan</th>'
    '</tr>'
    '</thead>'
    '<tbody>'
    + "".join(table_html_rows) +
    '</tbody>'
    '</table>'
    '</div>'
)
render_html(final_table)


# 9. Edit Tanggal Tertentu (Sederhana di Bawah Tabel)
st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
with st.expander("✏️ Edit Tanggal Tertentu"):
    col_e1, col_e2 = st.columns([3, 2])
    with col_e1:
        edit_opts = [f"Tanggal {r['day_num']} ({r['day_num']}/{mo})" for r in processed_records]
        pick_day = st.selectbox("Pilih tanggal yang ingin diubah:", options=range(len(edit_opts)), format_func=lambda i: edit_opts[i])
    with col_e2:
        st.write("")
        st.write("")
        if st.button("Buka Form Edit", use_container_width=True):
            dialog_input_order(processed_records[pick_day]["date_str"])


# 10. Catatan & Riwayat Ringkas
c_not, c_his = st.columns([1, 1])

with c_not:
    with st.expander("📝 Catatan Buku Besar (Pending Order)"):
        n_text = st.text_area("Catatan:", value=active_period.get("notes", ""), height=100, placeholder="Contoh: pending order, nama debitur...")
        if st.button("Simpan Catatan"):
            update_period_notes(active_period["id"], n_text)
            st.success("Catatan tersimpan!")
            st.rerun()

with c_his:
    with st.expander("📁 Riwayat Periode Lampau"):
        all_yrs = list_all_years()
        for y in all_yrs:
            pers = list_periods_by_year(y)
            for p in pers:
                if p["id"] != active_period["id"]:
                    p_name = MONTH_NAMES_ID.get(p["month"], str(p["month"]))
                    c_h1, c_h2 = st.columns([3, 1])
                    with c_h1:
                        st.write(f"**{p_name} {y}** ({'Selesai' if p['status'] == 'COMPLETED' else 'Aktif'})")
                    with c_h2:
                        if st.button("Buka", key=f"hist_{p['id']}"):
                            st.session_state["selected_year"] = y
                            st.session_state["selected_month"] = p["month"]
                            st.rerun()


# 11. Panduan Sederhana CADM
with st.expander("💡 Cara Pakai (Panduan Singkat CADM)"):
    st.markdown("""
    1. **Input Order Baru:** Klik tombol biru **`➕ Catat Order Hari Ini`** di bagian atas.
    2. **Masukkan Angka:** Isi order Notadana, Notaris Lokal, ACC, dan Jumlah Valid hari itu.
    3. **Cek Status:** Jika kotak bertuliskan **🟢 MATCH**, klik Simpan! Buku besar otomatis bertambah tanpa kalkulator.
    4. **Jika Ada Salah Input:** Buka kotak **`✏️ Edit Tanggal Tertentu`**, pilih tanggalnya, dan ubah angkanya. F-ONE otomatis menghitung ulang seluruh tanggal berikutnya.
    5. **Unduh Laporan:** Klik **`📄 Unduh PDF`** untuk mencetak laporan resmi.
    """)
