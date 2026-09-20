"""
pdf_generator.py
Modul pembuatan laporan PDF resmi untuk Rekapitulasi Order Fidusia F-ONE.
Menampilkan format tabel menyerupai buku besar fisik CADM lengkap dengan
highlight warna hari Minggu, Hari Libur Nasional, kotak ringkasan, dan tanda tangan.
"""
import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from database import MONTH_NAMES_ID


def generate_f_one_pdf(period: dict, processed_records: list, summary: dict) -> bytes:
    """
    Menghasilkan file PDF dalam bentuk bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#1E3A8A'),
        alignment=1  # Center
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#475569'),
        alignment=1  # Center
    )

    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        alignment=1
    )

    cell_bold_style = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        alignment=1
    )

    cell_left_style = ParagraphStyle(
        'TableCellLeft',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        alignment=0
    )

    elements = []

    # 1. Header & Title
    month_name = MONTH_NAMES_ID.get(period["month"], f"Bulan {period['month']}")
    year = period["year"]
    status_str = "SELESAI (COMPLETED)" if period.get("status") == "COMPLETED" else "SEDANG BERJALAN (ACTIVE)"

    elements.append(Paragraph("F-ONE — FIDUSIA ORDER &amp; NUMBERING EFFICIENCY", title_style))
    elements.append(Paragraph(f"REKAPITULASI ORDER FIDUSIA — PERIODE: {month_name.upper()} {year}", subtitle_style))
    elements.append(Paragraph(
        f"Status Dokumen: <b>{status_str}</b> | Rekonsiliasi: <b>{summary['status_text']}</b>",
        subtitle_style
    ))
    elements.append(Spacer(1, 0.4 * cm))

    # 2. Main Ledger Table
    # Columns:
    # 0: Tgl Vld
    # 1: Jlh Vld
    # 2: Order NDA
    # 3: Tot Order NDA
    # 4: Tot Vld
    # 5: Jlh Order Lokal
    # 6: ACC Haji
    # 7: ACC Emas
    # 8: ACC Cash
    # 9: Status / Keterangan
    headers = [
        "Tgl\nVld",
        "Jlh\nVld",
        "Order\nNDA",
        "Tot Order\nNDA",
        "Tot\nVld",
        "Jlh Order\nLokal",
        "ACC\nHaji",
        "ACC\nEmas",
        "ACC\nCash",
        "Status / Keterangan"
    ]

    table_data = [[Paragraph(f"<b>{h}</b>", cell_bold_style) for h in headers]]

    # Row styles list
    row_styles = []

    for idx, r in enumerate(processed_records):
        row_num = idx + 1  # 1-indexed (0 is header)
        day_num = r.get("day_num", 0)
        is_sun = bool(r.get("is_sunday", 0))
        is_hol = bool(r.get("is_holiday", 0))
        hol_name = r.get("holiday_name", "")
        catatan = r.get("catatan", "")

        tgl_display = f"{day_num}/{period['month']}"

        if is_sun:
            ket = "HARI MINGGU"
            row_data = [
                Paragraph(f"<b>{tgl_display}</b>", cell_bold_style),
                "-", "-", "-", "-", "-", "-", "-", "-",
                Paragraph(f"<i>{ket}</i>", cell_style)
            ]
            row_styles.append(('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor('#DBEAFE')))  # Soft Blue
        elif is_hol:
            ket = hol_name if hol_name else "LIBUR NASIONAL"
            row_data = [
                Paragraph(f"<b>{tgl_display}</b>", cell_bold_style),
                "-", "-", "-", "-", "-", "-", "-", "-",
                Paragraph(f"<b>{ket}</b>", cell_style)
            ]
            row_styles.append(('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor('#FEF08A')))  # Soft Yellow
        else:
            jlh_vld = r.get("jlh_valid", 0)
            order_nda = r.get("order_nda", 0)
            tot_nda = r.get("tot_order_nda", 0)
            tot_vld = r.get("tot_vld", 0)
            lokal = r.get("jlh_order_lokal", 0)
            haji = r.get("acc_haji", 0)
            emas = r.get("acc_emas", 0)
            cash = r.get("acc_cash", 0)
            is_match = r.get("is_daily_match", True)

            status_icon = "MATCH" if is_match else f"MISMATCH ({r.get('daily_diff', 0)})"
            if catatan:
                ket_text = f"{status_icon} | {catatan}"
            else:
                ket_text = status_icon

            # Alternate row background
            bg_color = colors.HexColor('#FFFFFF') if idx % 2 == 0 else colors.HexColor('#F8FAFC')
            row_styles.append(('BACKGROUND', (0, row_num), (-1, row_num), bg_color))

            row_data = [
                Paragraph(tgl_display, cell_style),
                str(jlh_vld) if jlh_vld > 0 else "-",
                str(order_nda) if order_nda > 0 else "-",
                str(tot_nda),
                str(tot_vld),
                str(lokal) if lokal > 0 else "-",
                str(haji) if haji > 0 else "-",
                str(emas) if emas > 0 else "-",
                str(cash) if cash > 0 else "-",
                Paragraph(ket_text, cell_left_style if catatan else cell_style)
            ]

        table_data.append(row_data)

    # Total Row
    total_row_num = len(table_data)
    total_row = [
        Paragraph("<b>TOTAL</b>", cell_bold_style),
        Paragraph(f"<b>{summary['total_valid_bulan']}</b>", cell_bold_style),
        Paragraph(f"<b>{summary['total_order_nda']}</b>", cell_bold_style),
        Paragraph(f"<b>{summary['total_order_nda']}</b>", cell_bold_style),
        Paragraph(f"<b>{summary['total_valid_bulan']}</b>", cell_bold_style),
        Paragraph(f"<b>{summary['total_order_lokal']}</b>", cell_bold_style),
        Paragraph(f"<b>{summary['total_acc_haji']}</b>", cell_bold_style),
        Paragraph(f"<b>{summary['total_acc_emas']}</b>", cell_bold_style),
        Paragraph(f"<b>{summary['total_acc_cash']}</b>", cell_bold_style),
        Paragraph(f"<b>{summary['status_text']}</b>", cell_bold_style)
    ]
    table_data.append(total_row)
    row_styles.append(('BACKGROUND', (0, total_row_num), (-1, total_row_num), colors.HexColor('#E2E8F0')))

    # Table Column Widths (A4 Landscape usable width is ~26.7 cm)
    col_widths = [
        1.6 * cm,  # Tgl Vld
        1.6 * cm,  # Jlh Vld
        1.8 * cm,  # Order NDA
        2.2 * cm,  # Tot Order NDA
        2.0 * cm,  # Tot Vld
        2.2 * cm,  # Jlh Order Lokal
        1.7 * cm,  # ACC Haji
        1.7 * cm,  # ACC Emas
        1.7 * cm,  # ACC Cash
        8.2 * cm   # Status / Keterangan
    ]

    base_table_style = [
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
    ] + row_styles

    ledger_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    ledger_table.setStyle(TableStyle(base_table_style))
    elements.append(ledger_table)
    elements.append(Spacer(1, 0.4 * cm))

    # 3. Footer Recap & Notes Section
    recap_summary_text = (
        f"<b>REKONSILIASI AKHIR BULAN:</b><br/>"
        f"• Total Order Notadana (NDA): <b>{summary['total_order_nda']}</b><br/>"
        f"• Total Order Notaris Lokal: <b>{summary['total_order_lokal']}</b><br/>"
        f"• Total Order ACC Haji: <b>{summary['total_acc_haji']}</b><br/>"
        f"• Total Order ACC Emas: <b>{summary['total_acc_emas']}</b><br/>"
        f"• Total Order ACC Cash: <b>{summary['total_acc_cash']}</b><br/>"
        f"• <b>Total Seluruh Order: {summary['total_semua_order']}</b><br/>"
        f"• <b>Total Valid (Buku Besar): {summary['total_valid_bulan']}</b><br/>"
        f"• Status: <b>{summary['status_text']}</b>"
    )

    notes_text = period.get("notes", "").replace("\n", "<br/>")
    if not notes_text:
        notes_text = "<i>Tidak ada catatan khusus untuk periode ini.</i>"

    footer_table_data = [
        [
            Paragraph("<b>RINGKASAN TOTAL ORDER</b>", cell_bold_style),
            Paragraph("<b>CATATAN / PENDING ORDER CADM</b>", cell_bold_style),
            Paragraph("<b>TANDA TANGAN &amp; PENGESAHAN</b>", cell_bold_style)
        ],
        [
            Paragraph(recap_summary_text, cell_left_style),
            Paragraph(notes_text, cell_left_style),
            Paragraph(
                "<br/>Dibuat Oleh,<br/><br/><br/><br/><b>( CADM )</b><br/>Central Administration",
                cell_style
            )
        ]
    ]

    footer_table = Table(footer_table_data, colWidths=[8.0 * cm, 10.0 * cm, 6.7 * cm])
    footer_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))

    elements.append(KeepTogether([footer_table]))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
