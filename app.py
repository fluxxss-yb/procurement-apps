import fitz  # Ini adalah PyMuPDF, tambahkan di bagian paling atas kode
import io
from PIL import Image
import base64
import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from datetime import date

# --- 1. DEFINISIKAN CLASS PDF TERLEBIH DAHULU ---
# Class ini harus ada di atas sebelum digunakan oleh fungsi manapun
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'FORM PENGAJUAN PEMBELIAN BARANG', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Halaman {self.page_no()}', 0, 0, 'C')

# Konfigurasi Halaman
st.set_page_config(page_title="Material System & Procurement", layout="wide")   

DB_FILE = 'database.csv'
SHOPPING_FILE = 'shopping_list_draft.csv'

# Fungsi untuk memuat daftar belanja dari file
def load_shopping_list():
    if os.path.exists(SHOPPING_FILE):
        return pd.read_csv(SHOPPING_FILE).to_dict('records')
    return []

# Fungsi untuk menyimpan daftar belanja ke file
def save_shopping_list(list_data):
    df_temp = pd.DataFrame(list_data)
    df_temp.to_csv(SHOPPING_FILE, index=False)

def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['BRAND NAME', 'ITEM NAME', 'TYPE', 'SPECS'])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

# Inisialisasi Session States
if 'data' not in st.session_state:
    st.session_state['data'] = load_data()
if 'shopping_list' not in st.session_state:
    st.session_state['shopping_list'] = load_shopping_list()

# --- FUNGSI GENERATE PDF ---
def generate_pdf(daftar_belanja, format_kertas='A4', client="", project="", doc_no="", dvs=""):
    # Inisialisasi PDF dengan format pilihan user
    pdf = PDF(orientation='L', format=format_kertas)
    pdf.add_page()

    # --- BAGIAN HEADER DINAMIS (DIBAWAH JUDUL) ---
    pdf.set_font('Arial', '', 10)
    # Membuat grid sederhana untuk informasi client & proyek
    # Kolom kiri
    pdf.cell(30, 7, "Nama Client", 0, 0)
    pdf.cell(5, 7, ":", 0, 0)
    pdf.cell(60, 7, client, 0, 0)
    
    # Kolom kanan (Nomor PO)
    pdf.cell(40, 7, "Nomor PO", 0, 0)
    pdf.cell(5, 7, ":", 0, 0)
    pdf.cell(0, 7, doc_no, 0, 1)
    
    # Baris Divisi
    pdf.cell(30, 7, "Divisi", 0, 0)
    pdf.cell(5, 7, ":", 0, 0)
    pdf.cell(60, 7, dvs, 0, 0)

    # Baris Proyek
    pdf.cell(40, 7, "Nama Proyek", 0, 0)
    pdf.cell(5, 7, ":", 0, 0)
    pdf.cell(0, 7, project, 0, 1)
    
    pdf.ln(5) # Spasi sebelum tabel
    
    # Hitung lebar total yang bisa digunakan (Lebar kertas - margin kiri & kanan)
    # pdf.w adalah lebar total kertas, pdf.l_margin adalah margin kiri
    usable_width = pdf.w - (pdf.l_margin * 2)
    
    # Tentukan rasio lebar kolom (total harus 1.0 atau 100%)
    # Contoh: No (5%), Item (25%), Type (20%), Qty (10%), Unit (10%), Date (15%), Remarks (15%)
    ratios = {
        'no': 0.05,
        'item': 0.12,
        'brand': 0.10,
        'type': 0.20,
        'specs': 0.23,
        'qty': 0.05,
        'unit': 0.05,
        'date': 0.10,
        'rem': 0.10
    }

    # Hitung lebar kolom sesungguhnya dalam mm
    w_no = usable_width * ratios['no']
    w_item = usable_width * ratios['item']
    w_brand = usable_width * ratios['brand']
    w_type = usable_width * ratios['type']
    w_specs = usable_width * ratios['specs']
    w_qty = usable_width * ratios['qty']
    w_unit = usable_width * ratios['unit']
    w_date = usable_width * ratios['date']
    w_rem = usable_width * ratios['rem']

    # --- HEADER TABEL ---
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font('Arial', 'B', 10)
    
    pdf.cell(w_no, 10, 'No', 1, 0, 'C', 1)
    pdf.cell(w_item, 10, 'Item', 1, 0, 'C', 1)
    pdf.cell(w_brand, 10, 'Brand', 1, 0, 'C', 1)
    pdf.cell(w_type, 10, 'Type', 1, 0, 'C', 1)
    pdf.cell(w_specs, 10, 'Specs', 1, 0, 'C', 1)
    pdf.cell(w_qty, 10, 'Qty', 1, 0, 'C', 1)
    pdf.cell(w_unit, 10, 'Unit', 1, 0, 'C', 1)
    pdf.cell(w_date, 10, 'Due Date', 1, 0, 'C', 1)
    pdf.cell(w_rem, 10, 'Remarks', 1, 1, 'C', 1)

    # --- ISI TABEL ---
    pdf.set_font('Arial', '', 9)
    for i, item in enumerate(daftar_belanja, 1):
        h = 8
        pdf.cell(w_no, h, str(i), 1, 0, 'C')
        
        # Fungsi pembatas teks otomatis agar tidak overflow
        def trim_text(text, width, font_size):
            # Logika sederhana: perkiraan lebar karakter (font size * 0.5)
            max_chars = int(width / (font_size * 0.18)) 
            return (text[:max_chars-3] + '..') if len(text) > max_chars else text

        pdf.cell(w_item, h, trim_text(item['Item Name'], w_item, 9), 1, 0, 'C')
        pdf.cell(w_brand, h, trim_text(item['Brand Name'], w_brand, 9), 1, 0, 'C')
        pdf.cell(w_type, h, trim_text(item['Type'], w_type, 9), 1, 0, 'C')
        pdf.cell(w_specs, h, trim_text(str(item['Specs']), w_specs, 9), 1, 0, 'C')
        pdf.cell(w_qty, h, str(item['Qty']), 1, 0, 'C')
        pdf.cell(w_unit, h, str(item['Unit']), 1, 0, 'C')
        pdf.cell(w_date, h, str(item['Due Date']), 1, 0, 'C')
        pdf.cell(w_rem, h, trim_text(str(item['Remarks']), w_rem, 9), 1, 1, 'C')

    return pdf.output(dest='S').encode('latin-1')

def display_pdf_preview(pdf_bytes):
    try:
        # 1. Buka data PDF dari memori (bytes)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        # 2. Ambil halaman pertama (index 0)
        page = doc.load_page(0)

        # 3. Render halaman PDF menjadi gambar (Pixmap)
        # dpi=150 membuat gambar cukup tajam untuk dibaca di layar
        pix = page.get_pixmap(dpi=150)

        # 4. Konversi pixmap ke format PNG yang dipahami Streamlit
        img_data = pix.tobytes("png")

        # 5. Tampilkan sebagai gambar biasa di Streamlit
        st.image(img_data, caption="Pratinjau Dokumen", use_container_width=True)

    except Exception as e:
        st.error(f"Gagal menampilkan preview: {e}")

st.title("📦 Sistem Database & Pengadaan")

# --- NAVIGASI ---
# Inisialisasi state menu jika belum ada
if 'menu' not in st.session_state:
    st.session_state['menu'] = "View Database"

# Fungsi pembantu untuk mengubah state menu
def set_menu(target):
    st.session_state['menu'] = target

# --- NAVIGASI MENGGUNAKAN BUTTON ---
st.sidebar.header("🧭 Navigasi Menu")

# Buat tombol-tombol navigasi
st.sidebar.button("📊 View Database", on_click=set_menu, args=("View Database",), use_container_width=True)
st.sidebar.button("➕ Input Master Data", on_click=set_menu, args=("Input Master Data",), use_container_width=True)
st.sidebar.button("📥 Import Data", on_click=set_menu, args=("Import Data",), use_container_width=True)
st.sidebar.button("📝 Buat Daftar Belanja", on_click=set_menu, args=("Buat Daftar Belanja",), use_container_width=True)

# Gunakan session_state['menu'] sebagai pengganti variabel 'menu' yang lama
menu = st.session_state['menu']

st.sidebar.divider()
st.sidebar.info(f"Menu Aktif: **{menu}**")

# --- MENU: BUAT DAFTAR BELANJA (FITUR BARU) ---
if menu == "Buat Daftar Belanja":
    st.subheader("📝 Form Pembuatan FPPB")
    df = st.session_state['data']
    
    if df.empty:
        st.warning("Database kosong.")
    else:
        # Bagian Input Barang (Sama seperti sebelumnya)
        with st.expander("➕ Tambah Barang ke Daftar", expanded=True):
            # ... (Logika selectbox Brand, Item, Type, Qty, dll)
            # Pastikan tombol "Tambah ke Daftar Belanja" sudah ada di sini
            col1, col2, col3, = st.columns(3)
            with col1:
                b_list = sorted(df['BRAND NAME'].dropna().unique().astype(str))
                sel_brand = st.selectbox("Pilih Brand", b_list)
            with col2:
                filtered_df_brand = df[df['BRAND NAME'] == sel_brand]
                i_list = sorted(filtered_df_brand['ITEM NAME'].dropna().unique().astype(str))
                sel_item = st.selectbox("Pilih Nama Barang", i_list)
            with col3:
                filtered_df_item = filtered_df_brand[filtered_df_brand['ITEM NAME'] == sel_item]
                t_list = sorted(filtered_df_item['TYPE'].dropna().unique().astype(str))
                sel_type = st.selectbox("Pilih Type", t_list)
            
            res = df[(df['BRAND NAME'] == sel_brand) & 
            (df['ITEM NAME'] == sel_item) & 
            (df['TYPE'] == sel_type)]
        
            if not res.empty:
                st.info(f"**Spesifikasi:** {res['SPECS'].values[0]}")
            
            st.divider()
            
            c_qty, c_unit, c_date, c_rem = st.columns([1, 1, 2, 3])
            with c_qty:
                qty = st.number_input("Jumlah", min_value=1, value=1)
            with c_unit:
                unit = st.selectbox("Satuan", ["pcs", "lot", "set", "unit", "mtr"])
            with c_date:
                d_date = st.date_input("Due Date", date.today())
            with c_rem:
                remarks = st.text_input("Remarks / Keterangan", placeholder="Contoh: Untuk Proyek A")

            if st.button("Tambah ke Daftar Belanja"):
                # 1. Ambil data spesifikasi dari database berdasarkan Type yang dipilih
                # Pastikan nama kolom di df sudah di-upper() jika Anda mengikuti saran sebelumnya
                row_data = df[(df['BRAND NAME'] == sel_brand) & 
                            (df['ITEM NAME'] == sel_item) & 
                            (df['TYPE'] == sel_type)]
                
                # Ambil nilai specs, jika kosong beri string kosong
                current_specs = row_data['SPECS'].values[0] if not row_data.empty else ""

                new_entry = {
                    "Brand Name": sel_brand,
                    "Item Name": sel_item,
                    "Type": sel_type,
                    "Specs": current_specs,
                    "Qty": qty,
                    "Unit": unit,
                    "Due Date": d_date,
                    "Remarks": remarks
                }
                st.session_state['shopping_list'].append(new_entry)
                save_shopping_list(st.session_state['shopping_list']) # <--- SIMPAN KE FILE
                st.success("Barang ditambahkan!")
                st.rerun()
            pass

        # --- FITUR PREVIEW ---
        if st.session_state['shopping_list']:
            st.divider()

            # --- INPUT HEADER DOKUMEN ---
            st.subheader("🏢 Informasi Header Dokumen")
            col_c, col_p, col_n, col_d = st.columns(4)
            with col_c:
                client_input = st.text_input("Nama Client", placeholder="Contoh: PT. Maju Jaya")
            with col_p:
                project_input = st.text_input("Nama Proyek", placeholder="Contoh: Maintenance Robot A")
            with col_n:
                doc_input = st.text_input("Nomor PO", placeholder="Contoh: PR/2024/001")
            with col_d:
                dvs_input = st.text_input("Divisi", placeholder="Masukkan nama divisi")
            
            # Membuat Tab untuk memisahkan Tabel Data dan Preview PDF
            tab1, tab2 = st.tabs(["📊 Kelola Daftar", "📄 Preview PDF"])
            
            with tab1:
                st.subheader("🛒 Keranjang Belanja")
                
                # Header Tabel Manual
                h_col = st.columns([0.5, 2, 2, 2.5, 2.5, 0.5, 0.5, 1.5, 1.5, 0.75, 0.75])
                h_col[0].write("**No**")            #0.5
                h_col[1].write("**Item Name**")     #2
                h_col[2].write("**Brand Name**")    #2
                h_col[3].write("**Type**")          #2.5
                h_col[4].write("**Specs**")         #2.5
                h_col[5].write("**Qty**")           #0.5
                h_col[6].write("**Unit**")          #0.5
                h_col[7].write("**Due Date**")      #1.5
                h_col[8].write("**Remarks**")       #1.5
                h_col[9].write("**Aksi**")          #1

                # Iterasi melalui daftar belanja
                # Kita gunakan list(enumerate) agar bisa menghapus berdasarkan index
                for idx, item in enumerate(st.session_state['shopping_list']):
                    col = st.columns([0.5, 2, 2, 2.5, 2.5, 0.5, 0.5, 1.5, 1.5, 0.75, 0.75])
                    
                    col[0].write(idx + 1)
                    col[1].write(item['Item Name'])
                    col[2].write(item['Brand Name'])
                    col[3].write(item['Type'])
                    col[4].write(item['Specs'])
                    col[5].write(item['Qty'])
                    col[6].write(item['Unit'])
                    col[7].write(str(item['Due Date']))
                    col[8].write(item['Remarks'])

                    # Tombol Aksi (Edit & Hapus) dalam satu kolom menggunakan Popover atau Expander
                    with col[9]:
                        # Fitur Hapus Per Baris
                        if st.button("🗑️", key=f"del_{idx}"):
                            st.session_state['shopping_list'].pop(idx)
                            save_shopping_list(st.session_state['shopping_list'])
                            st.rerun()
                        
                    with col[10]:    
                        # Fitur Edit Per Baris menggunakan Popover (Tombol kecil yang membuka jendela)
                        with st.popover("📝"):
                            st.write(f"Edit Item {idx+1}")
                            edit_qty = st.number_input("Qty", value=item['Qty'], key=f"eqty_{idx}")
                            edit_unit = st.selectbox("Unit", ["pcs", "lot", "set", "unit", "mtr"], 
                                                     index=["pcs", "lot", "set", "unit", "mtr"].index(item['Unit']), 
                                                     key=f"eunit_{idx}")
                            edit_date = st.date_input("Due Date", value=item['Due Date'], key=f"edate_{idx}")
                            edit_rem = st.text_input("Remarks", value=item['Remarks'], key=f"erem_{idx}")
                            
                            if st.button("Update", key=f"upd_{idx}"):
                                st.session_state['shopping_list'][idx]['Qty'] = edit_qty
                                st.session_state['shopping_list'][idx]['Unit'] = edit_unit
                                st.session_state['shopping_list'][idx]['Due Date'] = edit_date
                                st.session_state['shopping_list'][idx]['Remarks'] = edit_rem
                                save_shopping_list(st.session_state['shopping_list']) # <--- SIMPAN KE FILE
                                st.success("Terupdate!")
                                st.rerun()

                if st.button("🗑️ Kosongkan Semua Daftar", type="secondary"):
                    st.session_state['shopping_list'] = []
                    os.remove(SHOPPING_FILE)
                    st.rerun()

            with tab2:
                st.subheader("🖼️ Preview Dokumen")
                
                # Tambahkan opsi ukuran kertas
                paper_size = st.selectbox("Pilih Ukuran Kertas:", ["A4", "A3", "Letter", "Legal"])

                # Masukkan variabel input tadi ke dalam fungsi generate_pdf
                pdf_data = generate_pdf(
                    st.session_state['shopping_list'], 
                    format_kertas=paper_size,
                    client=client_input,
                    project=project_input,
                    doc_no=doc_input,
                    dvs=dvs_input
                )

                # Tampilkan Preview
                display_pdf_preview(pdf_data)
                
                # Generate PDF berdasarkan ukuran yang dipilih
                pdf_data = generate_pdf(st.session_state['shopping_list'], format_kertas=paper_size)
                
                
                st.download_button(
                    label="📥 Download PDF",
                    data=pdf_data,
                    file_name=f"Daftar_{doc_input}.pdf",
                    mime="application/pdf"
                )
        else:
            st.info("Belum ada barang di daftar belanja.")

# --- MENU LAINNYA (Sesuai kode sebelumnya) ---
elif menu == "Input Master Data":
    st.subheader("Input Manual Master Data")
    df = st.session_state['data']

    with st.form("input_form", clear_on_submit=True):
        new_brand = st.text_input("Nama Brand")
        new_item = st.text_input("Nama Item")
        new_type = st.text_input("Type / Model")
        new_specs = st.text_area("Spesifikasi")
        
        submit_button = st.form_submit_button("Simpan ke Database")
        
        if submit_button:
            if new_brand and new_item and new_type:
                # --- LOGIKA PENCEGAHAN DUPLIKAT ---
                # Cek apakah kombinasi 3 kolom ini sudah ada
                is_duplicate = ((df['BRAND NAME'].astype(str) == new_brand) & 
                                (df['ITEM NAME'].astype(str) == new_item) & 
                                (df['TYPE'].astype(str) == new_type)).any()
                
                if is_duplicate:
                    st.error(f"❌ Data Gagal Disimpan! Tipe '{new_type}' untuk Brand '{new_brand}' sudah ada di database.")
                # Buat baris baru
                else:
                    new_row = {
                        'BRAND NAME': new_brand.strip(),
                        'ITEM NAME': new_item.strip(),
                        'TYPE': new_type.strip(),
                        'SPECS': new_specs.strip()
                    }
                
                    # Tambahkan ke session state dan simpan ke file
                    st.session_state['data'] = pd.concat([st.session_state['data'], pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state['data'])
                    st.success(f"Data {new_type} berhasil disimpan!")
                    st.rerun()
            else:
                st.error("Mohon isi Brand, Item, dan Type!")

    
    if not df.empty:
        st.subheader("Pencarian Material")
        col1, col2, col3 = st.columns(3)

        with col1:
            brand_list = sorted(df['BRAND NAME'].unique())
            selected_brand = st.selectbox("Pilih Brand", brand_list)

        with col2:
            filtered_item = df[df['BRAND NAME'] == selected_brand]['ITEM NAME'].unique()
            selected_item = st.selectbox("Pilih Item Name", sorted(filtered_item))

        with col3:
            filtered_type = df[(df['BRAND NAME'] == selected_brand) & 
                            (df['ITEM NAME'] == selected_item)]['TYPE'].unique()
            selected_type = st.selectbox("Pilih Type", sorted(filtered_type))
        # Tampilkan Specs
        res = df[(df['BRAND NAME'] == selected_brand) & 
                (df['ITEM NAME'] == selected_item) & 
                (df['TYPE'] == selected_type)]
        
        if not res.empty:
            st.info(f"**Spesifikasi:** {res['SPECS'].values[0]}")
        
        st.divider()
        st.subheader("Seluruh Database")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Database kosong. Silakan Input Manual atau Import data.")


elif menu == "Import Data":
    st.subheader("Import Database dari File")
    uploaded_file = st.file_uploader("Unggah File", type=["xlsx", "csv"])
    
    if uploaded_file:
        if uploaded_file.name.endswith('.csv'):
            new_df = pd.read_csv(uploaded_file)
        else:
            new_df = pd.read_excel(uploaded_file)
        
        # Bersihkan nama kolom
        new_df.columns = new_df.columns.str.strip()
        
        if st.button("Gabungkan ke Database"):
            # Gabungkan data lama dengan data baru yang di-import
            combined_df = pd.concat([st.session_state['data'], new_df], ignore_index=True)
            # Hapus duplikat jika perlu
            combined_df = combined_df.drop_duplicates()
            
            st.session_state['data'] = combined_df
            save_data(combined_df)
            st.success("Data berhasil digabungkan dan disimpan!")
    pass


# --- UPDATE PADA MENU: VIEW DATABASE (TAMBAH FITUR HAPUS) ---
elif menu == "View Database":
    st.subheader("Manajemen Database Barang")
    df = st.session_state['data']
    
    if not df.empty:
        # Tampilkan tabel utama
        st.dataframe(df, use_container_width=True)
        
        st.divider()
        
        # --- BAGIAN EDIT & HAPUS ---
        col_action1, col_action2 = st.columns(2)
        
        # Buat label unik untuk pencarian
        df['select_label'] = df['BRAND NAME'] + " | " + df['ITEM NAME'] + " (" + df['TYPE'] + ")"
        
        with col_action1:
            st.subheader("📝 Ubah / 🗑️ Hapus Data")
            selected_item = st.selectbox("Pilih data yang akan dikelola:", df['select_label'].unique())
            
            # Ambil data spesifik berdasarkan pilihan
            idx = df[df['select_label'] == selected_item].index[0]
            data_lama = df.iloc[idx]

        # Tombol aksi (Hapus tetap ada)
        if st.button("🗑️ Hapus Baris Ini", type="secondary"):
            df_updated = df.drop(idx).drop(columns=['select_label'])
            st.session_state['data'] = df_updated
            if save_data(df_updated):
                st.success("Data berhasil dihapus!")
                st.rerun()

        st.divider()

        # --- FORM EDIT DATA ---
        st.subheader(f"Edit Data: {data_lama['TYPE']}")
        with st.form("form_edit", clear_on_submit=False):
            # Form ini otomatis terisi dengan data_lama (value=...)
            edit_brand = st.text_input("Ubah Brand", value=str(data_lama['BRAND NAME']))
            edit_item = st.text_input("Ubah Nama Item", value=str(data_lama['ITEM NAME']))
            edit_type = st.text_input("Ubah Type", value=str(data_lama['TYPE']))
            edit_specs = st.text_area("Ubah Spesifikasi", value=str(data_lama['SPECS']))
            
            save_edit = st.form_submit_button("💾 Simpan Perubahan")
            
            if save_edit:
                # Validasi Duplikat (Kecuali jika tidak mengubah brand/item/type)
                # Cek apakah kombinasi baru sudah ada di baris LAIN
                is_duplicate = ((df.index != idx) & 
                                (df['BRAND NAME'] == edit_brand.strip()) & 
                                (df['ITEM NAME'] == edit_item.strip()) & 
                                (df['TYPE'] == edit_type.strip())).any()
                
                if is_duplicate:
                    st.error("❌ Perubahan gagal! Kombinasi Brand, Item, dan Type tersebut sudah ada di data lain.")
                else:
                    # Update DataFrame pada index yang tepat
                    df.at[idx, 'BRAND NAME'] = edit_brand.strip()
                    df.at[idx, 'ITEM NAME'] = edit_item.strip()
                    df.at[idx, 'TYPE'] = edit_type.strip()
                    df.at[idx, 'SPECS'] = edit_specs.strip()
                    
                    # Hapus kolom pembantu sebelum simpan
                    df_final = df.drop(columns=['select_label'])
                    
                    st.session_state['data'] = df_final
                    if save_data(df_final):
                        st.success("✅ Data berhasil diperbarui!")
                        st.rerun()
    else:
        st.info("Database kosong.")
