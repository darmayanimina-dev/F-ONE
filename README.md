# ⚖️ F-ONE — Fidusia Order & Numbering Efficiency
> *One Input, One Record, Zero Miscalculation.*

Aplikasi web rekapitulasi order fidusia harian yang dirancang khusus untuk CADM:
- **Ramah Lansia & Aksesibilitas Tinggi**: Tipografi besar, kontras jelas, dan modal popup ramah smartphone/HP.
- **Buku Besar Digital**: Kolom dan tanda visual meniru buku fisik asli CADM (Hari Minggu biru, Hari Libur kuning).
- **Perhitungan Otomatis & Nol Salah Hitung**: Akumulasi bulanan terhitung otomatis tanpa perlu kalkulator manual.
- **Validasi Real-Time**: Status 🟢 **MATCH** / 🔴 **MISMATCH** harian dan bulanan.
- **Ekspor Dokumen**: Cetak rekapitulasi PDF resmi A4 Landscape dengan tanda tangan CADM serta ekspor Microsoft Excel (`.xlsx`).

---

## 🚀 Menjalankan Secara Lokal

1. Clone repositori:
   ```bash
   git clone https://github.com/darmayanimina-dev/F-ONE.git
   cd F-ONE
   ```

2. Pasang pustaka dependensi:
   ```bash
   pip install -r requirements.txt
   ```

3. Jalankan aplikasi Streamlit:
   ```bash
   streamlit run app.py
   ```

---

## 🗄️ Format & Struktur Database SQLite (`fone_database.db`)

Seluruh data transaksi, periode bulanan, dan jejak riwayat audit tersimpan secara lokal dan terstruktur dalam 3 tabel utama:

### 1. Tabel `periods` (Daftar Periode Rekap)
| Kolom | Tipe Data | Keterangan |
| :--- | :--- | :--- |
| `id` | `INTEGER PRIMARY KEY` | ID unik periode |
| `year` | `INTEGER` | Tahun periode (misal: 2026) |
| `month` | `INTEGER` | Bulan periode (1 s.d 12) |
| `status` | `TEXT` | Status periode (`ACTIVE` / `COMPLETED`) |
| `notes` | `TEXT` | Catatan buku besar / memo CADM |
| `created_at` | `TIMESTAMP` | Waktu pembuatan periode |
| `updated_at` | `TIMESTAMP` | Waktu pembaruan terakhir |
| `completed_at` | `TIMESTAMP` | Waktu status diselesaikan |

### 2. Tabel `daily_records` (Transaksi Harian CADM)
| Kolom | Tipe Data | Keterangan |
| :--- | :--- | :--- |
| `id` | `INTEGER PRIMARY KEY` | ID unik catatan transaksi |
| `period_id` | `INTEGER` | Foreign key ke tabel `periods` |
| `date_str` | `TEXT UNIQUE` | Tanggal transaksi (`YYYY-MM-DD`) |
| `day_num` | `INTEGER` | Angka hari/tanggal (1 s.d 31) |
| `is_sunday` | `INTEGER` | Flag hari Minggu (0 / 1) |
| `is_holiday` | `INTEGER` | Flag tanggal merah / libur (0 / 1) |
| `holiday_name` | `TEXT` | Nama hari libur nasional |
| `jlh_valid` | `INTEGER` | Total berkas valid harian |
| `order_nda` | `INTEGER` | Jumlah order Nota Dana (Otomatis: Valid dikurangi lainnya) |
| `jlh_order_lokal` | `INTEGER` | Jumlah order Notaris Lokal |
| `acc_haji` | `INTEGER` | Jumlah ACC Porsi Haji |
| `acc_emas` | `INTEGER` | Jumlah ACC Pembiayaan Emas |
| `acc_cash` | `INTEGER` | Jumlah ACC Cash / Tunai |
| `catatan` | `TEXT` | Catatan transaksi debitur / berkas khusus |
| `updated_at` | `TIMESTAMP` | Waktu pencatatan / pembaruan |

### 3. Tabel `change_history` (Riwayat Perubahan)
| Kolom | Tipe Data | Keterangan |
| :--- | :--- | :--- |
| `id` | `INTEGER PRIMARY KEY` | ID log riwayat |
| `period_id` | `INTEGER` | Foreign key ke tabel `periods` |
| `date_str` | `TEXT` | Tanggal transaksi yang diubah |
| `day_num` | `INTEGER` | Hari transaksi yang diubah |
| `action_type` | `TEXT` | Jenis aksi (`INPUT_AWAL`, `INPUT`, `UPDATE`) |
| `old_valid` | `INTEGER` | Nilai Total Valid sebelum perubahan |
| `new_valid` | `INTEGER` | Nilai Total Valid sesudah perubahan |
| `old_nda` | `INTEGER` | Nilai Order NDA sebelum perubahan |
| `new_nda` | `INTEGER` | Nilai Order NDA sesudah perubahan |
| `old_lokal` | `INTEGER` | Nilai Notaris Lokal sebelum perubahan |
| `new_lokal` | `INTEGER` | Nilai Notaris Lokal sesudah perubahan |
| `old_haji` | `INTEGER` | Nilai ACC Haji sebelum perubahan |
| `new_haji` | `INTEGER` | Nilai ACC Haji sesudah perubahan |
| `old_emas` | `INTEGER` | Nilai ACC Emas sebelum perubahan |
| `new_emas` | `INTEGER` | Nilai ACC Emas sesudah perubahan |
| `old_cash` | `INTEGER` | Nilai ACC Cash sebelum perubahan |
| `new_cash` | `INTEGER` | Nilai ACC Cash sesudah perubahan |
| `catatan_perubahan` | `TEXT` | Ringkasan diff perubahan kolom angka & memo |
| `changed_at` | `TIMESTAMP` | Waktu presisi dilakukannya perubahan |

