"""
app.py
Aplikasi F-ONE (Fidusia Order & Numbering Efficiency)
Tata Letak CMS Minimalis & Profesional:
- Menu Navigasi Samping (Sidebar CMS) untuk Navigasi Periode, Riwayat, dan Dokumen.
- Tombol [✏️ Edit] langsung di setiap baris tabel buku besar (In-Line Row Action).
- Status rekonsiliasi ringkas: Total Valid vs Total Order (🟢 MATCH / 🔴 MISMATCH).
- 100% Bersih tanpa dummy data.
"""
import datetime
import calendar
import io
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

# Helper fungsi render HTML bebas bug indentasi
def render_html(html_str: str):
    lines = [line.strip() for line in html_str.strip().splitlines() if line.strip()]
    st.markdown("".join(lines), unsafe_allow_html=True)


# 1. Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="F-ONE | CMS Rekap Fidusia CADM",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inisialisasi Database
init_db()

# 2. Styling CMS Minimalis & Aksesibilitas
render_html("""
<style>
    /* Tipografi Utama */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        color: #0F172A !important;
        font-size: 16px !important;
    }

    /* Sidebar CMS Styling */
    section[data-testid="stSidebar"] {
        background-color: #F8FAFC !important;
        border-right: 1.5px solid #E2E8F0 !important;
    }
    .cms-brand {
        padding: 0.5rem 0 1rem 0;
        border-bottom: 2px solid #E2E8F0;
        margin-bottom: 1rem;
    }
    .cms-brand-title {
        font-size: 1.6rem;
        font-weight: 800;
        color: #1E3A8A;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .cms-brand-desc {
        font-size: 0.85rem;
        color: #64748B;
        font-weight: 500;
        margin-top: 4px;
    }
    .sidebar-section-title {
        font-size: 0.82rem;
        font-weight: 800;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.7px;
        margin: 1.25rem 0 0.5rem 0;
    }

    /* Top Summary Bar */
    .summary-strip {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #FFFFFF;
        border: 1.5px solid #CBD5E1;
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.03);
        flex-wrap: wrap;
        gap: 14px;
    }
    .stat-item {
        display: flex;
        align-items: baseline;
        gap: 8px;
    }
    .stat-label {
        font-size: 0.95rem;
        color: #475569;
        font-weight: 600;
    }
    .stat-val {
        font-size: 2rem;
        font-weight: 800;
        color: #0F172A;
    }
    .pill-match {
        background-color: #DCFCE7;
        color: #15803D;
        border: 1.5px solid #86EFAC;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 800;
        font-size: 1.1rem;
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
        font-weight: 800;
        font-size: 1.1rem;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }

    /* Tabel CMS & Action Button */
    .cms-table-wrapper {
        border: 1.5px solid #CBD5E1;
        border-radius: 12px;
        overflow-x: auto;
        background: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }
    table.cms-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 1rem;
    }
    table.cms-table th {
        background-color: #1E3A8A;
        color: white;
        font-weight: 700;
        padding: 11px 8px;
        text-align: center;
        font-size: 0.9rem;
        border: 1px solid #2563EB;
        white-space: pre-line;
    }
    table.cms-table td {
        padding: 9px 8px;
        text-align: center;
        border: 1px solid #E2E8F0;
        font-weight: 500;
    }
    tr.row-sun {
        background-color: #EFF6FF !important; /* Biru lembut hari Minggu */
        color: #1E40AF !important;
        font-weight: 600;
    }
    tr.row-hol {
        background-color: #FEF9C3 !important; /* Kuning lembut libur nasional */
        color: #854D0E !important;
        font-weight: 600;
    }
    tr.row-tot {
        background-color: #F1F5F9 !important;
        font-weight: 800 !important;
        font-size: 1.1rem !important;
        border-top: 2.5px solid #0F172A !important;
    }
    .badge-ok {
        color: #15803D;
        font-weight: 700;
        font-size: 0.9rem;
    }
    .badge-err {
        color: #B91C1C;
        font-weight: 700;
        font-size: 0.9rem;
    }

    /* Baris Tabel & Klik Edit */
    tr.row-clickable {
        cursor: pointer;
        transition: background-color 0.15s ease;
    }
    tr.row-clickable:hover {
        background-color: #F8FAFC !important;
    }
    tr.row-sun.row-clickable:hover {
        background-color: #E0E7FF !important;
    }
    tr.row-hol.row-clickable:hover {
        background-color: #FEF08A !important;
    }
    .tgl-badge-link {
        display: inline-block;
        min-width: 28px;
        padding: 2px 6px;
        border-radius: 6px;
        background-color: #F1F5F9;
        color: #1E3A8A !important;
        font-weight: 800;
        text-decoration: none !important;
        border: 1px solid #CBD5E1;
        transition: all 0.15s ease;
    }
    .tgl-badge-link:hover {
        background-color: #1E3A8A;
        color: white !important;
        border-color: #1E3A8A;
    }

    /* Tombol Edit Langsung di Baris Tabel */
    .action-edit-btn {
        display: inline-block;
        background-color: #EFF6FF;
        color: #1D4ED8 !important;
        border: 1.5px solid #93C5FD;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 700;
        text-decoration: none !important;
        transition: all 0.15s ease-in-out;
    }
    .action-edit-btn:hover {
        background-color: #1D4ED8;
        color: white !important;
        border-color: #1D4ED8;
    }

    /* Tombol Utama */
    div.stButton > button {
        border-radius: 10px !important;
        font-weight: 700 !important;
        padding: 0.65rem 1.25rem !important;
        min-height: 48px !important;
    }
</style>
""")


# 3. State Management Navigasi
today = datetime.date.today()
current_year = today.year
current_month = today.month

if "selected_year" not in st.session_state:
    st.session_state["selected_year"] = current_year
if "selected_month" not in st.session_state:
    st.session_state["selected_month"] = current_month
if "dialog_target_date" not in st.session_state:
    st.session_state["dialog_target_date"] = None


# Deteksi query param ?edit=YYYY-MM-DD jika user klik tombol [✏️ Edit] langsung di tabel
query_target_edit = None
if "edit" in st.query_params:
    query_target_edit = st.query_params["edit"]
    # Bersihkan query params agar tidak terus menerus terbuka saat refresh
    del st.query_params["edit"]


# Ambil data periode aktif
active_period = get_or_create_period(st.session_state["selected_year"], st.session_state["selected_month"])
records = get_daily_records_by_period(active_period["id"])
processed_records, summary = compute_cumulative_records(records)
nama_bulan = MONTH_NAMES_ID[st.session_state["selected_month"]]
p_title = f"{nama_bulan} {st.session_state['selected_year']}"


# 4. Modal Dialog Input / Edit Order (@st.dialog)
@st.dialog("📝 Input / Edit Rekap Order Fidusia")
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

    render_html(f"""
    <div style='background: #EFF6FF; border: 1.5px solid #3B82F6; padding: 10px 14px; border-radius: 8px; margin-bottom: 12px;'>
        <b style='color: #1E3A8A; font-size: 1.05rem;'>📅 Periode: {MONTH_NAMES_ID[p_mo]} {p_yr}</b>
    </div>
    """)

    tgl_selected = st.date_input(
        "Pilih Tanggal Transaksi:",
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
        order_nda = st.number_input("Order Notadana (NDA):", min_value=0, value=int(existing_rec.get("order_nda", 0)), step=1)
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
        jlh_valid = st.number_input("Jumlah Valid (Total Valid):", min_value=0, value=def_vld, step=1)

    diff = jlh_valid - sum_orders
    with cv2:
        if diff == 0:
            render_html(f"""
            <div style='background: #DCFCE7; border: 2px solid #86EFAC; color: #166534; padding: 10px; border-radius: 8px; text-align: center; margin-top: 20px;'>
                <b style='font-size: 1.1rem;'>🟢 MATCH (Pas)</b><br/>
                <span style='font-size: 0.85rem;'>Valid = Total Order ({sum_orders})</span>
            </div>
            """)
        else:
            render_html(f"""
            <div style='background: #FEE2E2; border: 2px solid #FCA5A5; color: #991B1B; padding: 10px; border-radius: 8px; text-align: center; margin-top: 20px;'>
                <b style='font-size: 1.1rem;'>🔴 MISMATCH</b><br/>
                <span style='font-size: 0.85rem;'>Selisih: {abs(diff)}</span>
            </div>
            """)

    catatan = st.text_input("Catatan Tambahan (Opsional):", value=existing_rec.get("catatan", ""))

    st.write("")
    b1, b2 = st.columns(2)
    with b1:
        if st.button("💾 Simpan Data", type="primary", use_container_width=True):
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
            st.success("Berhasil disimpan!")
            st.rerun()
    with b2:
        if st.button("Batal", use_container_width=True):
            st.rerun()


# Jika terdeteksi klik edit dari baris tabel, langsung buka dialog
if query_target_edit:
    dialog_input_order(query_target_edit)


# 5. CMS SIDEBAR (Menu Navigasi Samping)
with st.sidebar:
    render_html("""
    <div class="cms-brand">
        <div class="cms-brand-title">⚖️ F-ONE</div>
        <div class="cms-brand-desc">Fidusia Order &amp; Numbering Efficiency</div>
    </div>
    """)

    st.markdown('<div class="sidebar-section-title">📅 Periode Aktif</div>', unsafe_allow_html=True)
    status_tag = "🟢 SELESAI" if active_period["status"] == "COMPLETED" else "🔵 AKTIF"
    render_html(f"""
    <div style="background: white; border: 1.5px solid #CBD5E1; border-radius: 8px; padding: 10px 12px; margin-bottom: 10px;">
        <div style="font-size: 1.15rem; font-weight: 800; color: #1E3A8A;">{p_title}</div>
        <div style="font-size: 0.85rem; font-weight: 700; margin-top: 2px;">Status: {status_tag}</div>
    </div>
    """)

    # Tombol kembali ke bulan berjalan jika sedang membuka bulan lampau
    is_running_now = (st.session_state["selected_year"] == current_year and st.session_state["selected_month"] == current_month)
    if not is_running_now:
        if st.button(f"📍 Buka Bulan Ini ({MONTH_NAMES_ID[current_month]})", use_container_width=True):
            st.session_state["selected_year"] = current_year
            st.session_state["selected_month"] = current_month
            st.rerun()

    st.markdown('<div class="sidebar-section-title">📁 Riwayat Periode (CMS)</div>', unsafe_allow_html=True)
    
    # Pilih Tahun
    all_yrs = list_all_years()
    if current_year not in all_yrs:
        all_yrs.insert(0, current_year)
    
    sel_yr = st.selectbox("Pilih Tahun", options=all_yrs, index=all_yrs.index(st.session_state["selected_year"]) if st.session_state["selected_year"] in all_yrs else 0, key="side_yr")
    if sel_yr != st.session_state["selected_year"]:
        st.session_state["selected_year"] = sel_yr
        st.rerun()

    # Daftar Bulan dalam Tahun Tersebut
    periods_in_yr = list_periods_by_year(sel_yr)
    for p in periods_in_yr:
        m_name = MONTH_NAMES_ID.get(p["month"], f"Bulan {p['month']}")
        is_selected = (p["month"] == st.session_state["selected_month"] and p["year"] == st.session_state["selected_year"])
        p_stat_badge = "✓ Selesai" if p["status"] == "COMPLETED" else "Aktif"
        
        btn_label = f"{'👉 ' if is_selected else ''}{m_name} ({p_stat_badge})"
        if st.button(btn_label, key=f"nav_p_{p['id']}", use_container_width=True, type="primary" if is_selected else "secondary"):
            st.session_state["selected_year"] = p["year"]
            st.session_state["selected_month"] = p["month"]
            st.rerun()

    st.markdown('<div class="sidebar-section-title">📄 Ekspor &amp; Dokumen</div>', unsafe_allow_html=True)
    pdf_data = generate_f_one_pdf(active_period, processed_records, summary)
    st.download_button(
        label="📄 Unduh Rekap PDF",
        data=pdf_data,
        file_name=f"F-ONE_Rekap_{nama_bulan}_{st.session_state['selected_year']}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

    # Excel Download
    x_buf = io.BytesIO()
    x_rows = []
    for r in processed_records:
        day_num = r.get("day_num", 0)
        is_sun = bool(r.get("is_sunday", 0))
        is_hol = bool(r.get("is_holiday", 0))
        x_rows.append({
            "Tanggal": day_num,
            "Jumlah Valid": r.get("jlh_valid", 0) if (r.get("jlh_valid", 0) > 0 or not (is_sun or is_hol)) else "-",
            "Order Notadana": r.get("order_nda", 0) if (r.get("order_nda", 0) > 0 or not (is_sun or is_hol)) else "-",
            "Order Lokal": r.get("jlh_order_lokal", 0) if r.get("jlh_order_lokal", 0) > 0 else "-",
            "ACC Haji": r.get("acc_haji", 0) if r.get("acc_haji", 0) > 0 else "-",
            "ACC Emas": r.get("acc_emas", 0) if r.get("acc_emas", 0) > 0 else "-",
            "ACC Cash": r.get("acc_cash", 0) if r.get("acc_cash", 0) > 0 else "-",
        })
    x_rows.append({
        "Tanggal": "TOTAL",
        "Jumlah Valid": summary['total_valid_bulan'],
        "Order Notadana": summary['total_order_nda'],
        "Order Lokal": summary['total_order_lokal'],
        "ACC Haji": summary['total_acc_haji'],
        "ACC Emas": summary['total_acc_emas'],
        "ACC Cash": summary['total_acc_cash'],
    })
    with pd.ExcelWriter(x_buf, engine='openpyxl') as writer:
        pd.DataFrame(x_rows).to_excel(writer, index=False, sheet_name=f"{nama_bulan}_{active_period['year']}")
    st.download_button(
        label="📊 Unduh Excel (.xlsx)",
        data=x_buf.getvalue(),
        file_name=f"F-ONE_Rekap_{nama_bulan}_{st.session_state['selected_year']}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    st.markdown('<div class="sidebar-section-title">⚙️ Status Periode</div>', unsafe_allow_html=True)
    if active_period["status"] == "ACTIVE":
        if st.button("✓ Selesaikan Periode Ini", use_container_width=True):
            update_period_status(active_period["id"], "COMPLETED")
            st.success("Ditandai selesai.")
            st.rerun()
    else:
        if st.button("🔓 Buka Kembali Periode", use_container_width=True):
            update_period_status(active_period["id"], "ACTIVE")
            st.rerun()


# 6. KONTEN UTAMA CMS DASHBOARD

# Header & Aksi Cepat
main_head_col, main_act_col = st.columns([3.5, 2])
with main_head_col:
    render_html(f"""
    <div style="margin-bottom: 8px;">
        <h2 style="margin: 0; font-size: 1.85rem; font-weight: 800; color: #1E3A8A;">
            📖 Buku Besar: {p_title}
        </h2>
        <div style="font-size: 0.95rem; color: #64748B; margin-top: 2px;">
            Rekapitulasi order harian &bull; Klik <b>[✏️ Edit]</b> langsung di baris tanggal untuk mengisi / mengubah angka.
        </div>
    </div>
    """)

with main_act_col:
    st.write("")
    if st.button("➕ Catat Order Hari Ini", type="primary", use_container_width=True):
        dialog_input_order()


# Bar Ringkasan Minimalis
status_chip = (
    f'<div class="pill-match">🟢 MATCH (Pas)</div>'
    if summary["is_monthly_match"]
    else f'<div class="pill-mismatch">🔴 MISMATCH (Selisih {abs(summary["selisih_bulanan"])})</div>'
)

render_html(f"""
<div class="summary-strip">
    <div class="stat-item">
        <span class="stat-label">Total Valid:</span>
        <span class="stat-val" style="color: #1D4ED8;">{summary['total_valid_bulan']}</span>
    </div>
    <div class="stat-item">
        <span class="stat-label">Total Order (Semua):</span>
        <span class="stat-val" style="color: #0F766E;">{summary['total_semua_order']}</span>
    </div>
    <div>
        {status_chip}
    </div>
</div>
""")


# 7. TABEL BUKU BESAR (7 KOLOM SESUAI BUKU FISIK CADM)
mo = active_period["month"]
table_html_rows = []

for idx, r in enumerate(processed_records):
    day_num = r.get("day_num", 0)
    date_str = r.get("date_str", "")
    is_sun = bool(r.get("is_sunday", 0))
    is_hol = bool(r.get("is_holiday", 0))
    hol_name = r.get("holiday_name", "")
    catatan = r.get("catatan", "")

    jlh_vld = r.get("jlh_valid", 0)
    order_nda = r.get("order_nda", 0)
    lokal = r.get("jlh_order_lokal", 0)
    haji = r.get("acc_haji", 0)
    emas = r.get("acc_emas", 0)
    cash = r.get("acc_cash", 0)

    # Styling baris & keterangan tooltip
    if is_sun:
        r_cls = "row-sun"
        tip_text = "Hari Minggu (Klik untuk edit)"
    elif is_hol:
        r_cls = "row-hol"
        tip_text = f"{hol_name if hol_name else 'Libur Nasional'} (Klik untuk edit)"
    else:
        r_cls = ""
        tip_text = f"Klik untuk edit tanggal {day_num}"
        if catatan:
            tip_text += f" - Catatan: {catatan}"

    v_disp = str(jlh_vld) if jlh_vld > 0 else "-"
    n_disp = str(order_nda) if order_nda > 0 else "-"
    l_disp = str(lokal) if lokal > 0 else "-"
    h_disp = str(haji) if haji > 0 else "-"
    e_disp = str(emas) if emas > 0 else "-"
    c_disp = str(cash) if cash > 0 else "-"

    # Angka tanggal saja
    tgl_cell = f'<span style="font-weight:800; font-size:1.05rem; color:#1E3A8A;">{day_num}</span>'
    
    # Tombol [✏️ Edit] jelas dan mudah diklik
    action_html = f'<a href="?edit={date_str}" target="_self" class="action-edit-btn">✏️ Edit</a>'

    table_html_rows.append(
        f'<tr class="{r_cls}">'
        f'<td>{tgl_cell}</td>'
        f'<td>{v_disp}</td>'
        f'<td>{n_disp}</td>'
        f'<td>{l_disp}</td>'
        f'<td>{h_disp}</td>'
        f'<td>{e_disp}</td>'
        f'<td>{c_disp}</td>'
        f'<td>{action_html}</td>'
        f'</tr>'
    )

# Baris Total Akumulatif
total_row = (
    f'<tr class="row-tot">'
    f'<td>TOTAL</td>'
    f'<td>{summary["total_valid_bulan"]}</td>'
    f'<td>{summary["total_order_nda"]}</td>'
    f'<td>{summary["total_order_lokal"]}</td>'
    f'<td>{summary["total_acc_haji"]}</td>'
    f'<td>{summary["total_acc_emas"]}</td>'
    f'<td>{summary["total_acc_cash"]}</td>'
    f'<td>-</td>'
    f'</tr>'
)
table_html_rows.append(total_row)

final_table = (
    '<div class="cms-table-wrapper">'
    '<table class="cms-table">'
    '<thead>'
    '<tr>'
    '<th style="width: 75px;">Tanggal</th>'
    '<th>Jumlah<br/>Valid</th>'
    '<th>Order<br/>Notadana</th>'
    '<th>Order<br/>Lokal</th>'
    '<th>ACC<br/>Haji</th>'
    '<th>ACC<br/>Emas</th>'
    '<th>ACC<br/>Cash</th>'
    '<th style="width: 85px;">Aksi</th>'
    '</tr>'
    '</thead>'
    '<tbody>'
    + "".join(table_html_rows) +
    '</tbody>'
    '</table>'
    '</div>'
)
render_html(final_table)


# 8. Catatan Buku Besar (Collapsible / Mengembang di Bawah)
st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
with st.expander("📝 Catatan Buku Besar (Pending Order)"):
    n_text = st.text_area(
        "Tulis catatan pending order atau memo khusus di sini:",
        value=active_period.get("notes", ""),
        height=110,
        placeholder="Contoh: pending order, nama debitur..."
    )
    if st.button("Simpan Catatan"):
        update_period_notes(active_period["id"], n_text)
        st.success("Catatan tersimpan!")
        st.rerun()
