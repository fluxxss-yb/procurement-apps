import base64
from datetime import date
import io
import os
import fitz  # PyMuPDF
from fpdf import FPDF
from github import Github
import pandas as pd
from PIL import Image
import streamlit as st

# --- KONFIGURASI GITHUB ---
# Ambil kredensial dari Streamlit Secrets
GITHUB_TOKEN = st.secrets.get('GITHUB_TOKEN', '')
REPO_NAME = st.secrets.get(
    'REPO_NAME', ''
)  # Contoh: "username_anda/procurement-apps"
BRANCH = st.secrets.get('BRANCH', 'main')

DB_FILE = 'database.csv'
SHOPPING_FILE = 'shopping_list_draft.csv'
COLS = ['BRAND NAME', 'ITEM NAME', 'TYPE', 'SPECS']


# --- FUNGSI UTAMA GITHUB API ---
def update_file_to_github(file_path, content_str, commit_message):
  """Fungsi pembantu untuk meng-update/commit file langsung ke repository GitHub."""
  if not GITHUB_TOKEN or not REPO_NAME:
    st.warning(
        '⚠️ Token GitHub atau Repo Name belum dikonfigurasi di Streamlit'
        ' Secrets. Perubahan hanya disimpan secara lokal.'
    )
    return False

  try:
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)

    try:
      # Ambil metadata file jika sudah ada di GitHub
      contents = repo.get_contents(file_path, ref=BRANCH)
      repo.update_file(
          path=file_path,
          message=commit_message,
          content=content_str,
          sha=contents.sha,
          branch=BRANCH,
      )
    except Exception:
      # Jika file belum ada di GitHub, buat file baru
      repo.create_file(
          path=file_path,
          message=f'Create {file_path}',
          content=content_str,
          branch=BRANCH,
      )
    return True
  except Exception as e:
    st.error(f'❌ Gagal memperbarui file {file_path} di GitHub: {e}')
    return False


# --- 1. DEFINISIKAN CLASS PDF ---
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
st.set_page_config(page_title='Material System & Procurement', layout='wide')


# --- FUNGSI DAFTAR BELANJA ---
def load_shopping_list():
  if os.path.exists(SHOPPING_FILE):
    try:
      return pd.read_csv(
          SHOPPING_FILE,
          sep=None,
          engine='python',
          on_bad_lines='skip',
          quotechar='"',
          escapechar='\\',
      ).to_dict('records')
    except Exception:
      return []
  return []


def save_shopping_list(list_data):
  # 1. Simpan ke lokal/server
  df_temp = pd.DataFrame(list_data)
  df_temp.to_csv(SHOPPING_FILE, index=False)

  # 2. Sync otomatis langsung ke repository GitHub
  csv_content = df_temp.to_csv(index=False)
  update_file_to_github(
      SHOPPING_FILE,
      csv_content,
      'Update shopping_list_draft.csv via Streamlit App',
  )


# --- FUNGSI DATABASE MASTER ---
def load_data():
  if os.path.exists(DB_FILE):
    try:
      df = pd.read_csv(
          DB_FILE,
          sep=None,
          engine='python',
          dtype=str,
          quotechar='"',
          on_bad_lines='skip',
      )
      df.columns = df.columns.astype(str).str.strip()

      if 'BRAND NAME' in df.columns:
        df = df[df['BRAND NAME'].astype(str).str.strip() != 'Pilih Item']

      for col in COLS:
        if col not in df.columns:
          df[col] = ''
        else:
          df[col] = df[col].fillna('').astype(str).str.strip()

      return df[COLS].reset_index(drop=True)
    except Exception as e:
      st.error(f'Gagal membaca database: {e}')
      return pd.DataFrame(columns=COLS)
  return pd.DataFrame(columns=COLS)


def save_data(df):
  try:
    df_to_save = df[COLS].copy()
    for col in COLS:
      df_to_save[col] = df_to_save[col].astype(str).str.strip()

    # 1. Simpan ke lokal
    df_to_save.to_csv(DB_FILE, index=False, sep=',')

    # 2. Sync otomatis langsung ke repository GitHub
    csv_content = df_to_save.to_csv(index=False, sep=',')
    update_file_to_github(
        DB_FILE, csv_content, 'Update database.csv via Streamlit App'
    )
    return True
  except Exception as e:
    st.error(f'Gagal menyimpan database: {e}')
    return False


# Inisialisasi Session States
if 'data' not in st.session_state:
  st.session_state['data'] = load_data()
if 'shopping_list' not in st.session_state:
  st.session_state['shopping_list'] = load_shopping_list()


# --- FUNGSI GENERATE PDF ---
def generate_pdf(
    daftar_belanja,
    format_kertas='A4',
    client='',
    project='',
    doc_no='',
    dvs='',
):
  pdf = PDF(orientation='L', format=format_kertas)
  pdf.add_page()

  pdf.set_font('Arial', '', 10)
  pdf.cell(30, 7, 'Nama Client', 0, 0)
  pdf.cell(5, 7, ':', 0, 0)
  pdf.cell(60, 7, str(client), 0, 0)

  pdf.cell(40, 7, 'Nomor PO', 0, 0)
  pdf.cell(5, 7, ':', 0, 0)
  pdf.cell(0, 7, str(doc_no), 0, 1)

  pdf.cell(30, 7, 'Divisi', 0, 0)
  pdf.cell(5, 7, ':', 0, 0)
  pdf.cell(60, 7, str(dvs), 0, 0)

  pdf.cell(40, 7, 'Nama Proyek', 0, 0)
  pdf.cell(5, 7, ':', 0, 0)
  pdf.cell(0, 7, str(project), 0, 1)

  pdf.ln(5)

  usable_width = pdf.w - (pdf.l_margin * 2)

  ratios = {
      'no': 0.05,
      'item': 0.12,
      'brand': 0.10,
      'type': 0.20,
      'specs': 0.23,
      'qty': 0.05,
      'unit': 0.05,
      'date': 0.10,
      'rem': 0.10,
  }

  w_no = usable_width * ratios['no']
  w_item = usable_width * ratios['item']
  w_brand = usable_width * ratios['brand']
  w_type = usable_width * ratios['type']
  w_specs = usable_width * ratios['specs']
  w_qty = usable_width * ratios['qty']
  w_unit = usable_width * ratios['unit']
  w_date = usable_width * ratios['date']
  w_rem = usable_width * ratios['rem']

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

  pdf.set_font('Arial', '', 9)

  def trim_text(text, width, font_size):
    max_chars = int(width / (font_size * 0.18))
    text_str = str(text)
    return (
        (text_str[: max_chars - 3] + '..')
        if len(text_str) > max_chars
        else text_str
    )

  for i, item in enumerate(daftar_belanja, 1):
    h = 8
    pdf.cell(w_no, h, str(i), 1, 0, 'C')
    pdf.cell(w_item, h, trim_text(item.get('Item Name', ''), w_item, 9), 1, 0, 'C')
    pdf.cell(
        w_brand, h, trim_text(item.get('Brand Name', ''), w_brand, 9), 1, 0, 'C'
    )
    pdf.cell(w_type, h, trim_text(item.get('Type', ''), w_type, 9), 1, 0, 'C')
    pdf.cell(w_specs, h, trim_text(item.get('Specs', ''), w_specs, 9), 1, 0, 'C')
    pdf.cell(w_qty, h, str(item.get('Qty', 1)), 1, 0, 'C')
    pdf.cell(w_unit, h, str(item.get('Unit', '')), 1, 0, 'C')
    pdf.cell(w_date, h, str(item.get('Due Date', '')), 1, 0, 'C')
    pdf.cell(w_rem, h, trim_text(item.get('Remarks', ''), w_rem, 9), 1, 1, 'C')

  return bytes(pdf.output())


def display_pdf_preview(pdf_bytes):
  try:
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=150)
    img_data = pix.tobytes('png')
    st.image(img_data, caption='Pratinjau Dokumen', use_container_width=True)
  except Exception as e:
    st.error(f'Gagal menampilkan preview: {e}')


st.title('📦 Sistem Database & Pengadaan')

# --- NAVIGASI ---
if 'menu' not in st.session_state:
  st.session_state['menu'] = 'View Database'


def set_menu(target):
  st.session_state['menu'] = target


st.sidebar.header('🧭 Navigasi Menu')
st.sidebar.button(
    '📊 View Database',
    on_click=set_menu,
    args=('View Database',),
    use_container_width=True,
)
st.sidebar.button(
    '➕ Input Master Data',
    on_click=set_menu,
    args=('Input Master Data',),
    use_container_width=True,
)
st.sidebar.button(
    '📥 Import Data',
    on_click=set_menu,
    args=('Import Data',),
    use_container_width=True,
)
st.sidebar.button(
    '📝 Buat Daftar Belanja',
    on_click=set_menu,
    args=('Buat Daftar Belanja',),
    use_container_width=True,
)

menu = st.session_state['menu']

st.sidebar.divider()
st.sidebar.info(f'Menu Aktif: **{menu}**')

# --- MENU: BUAT DAFTAR BELANJA ---
if menu == 'Buat Daftar Belanja':
  st.subheader('📝 Form Pembuatan FPPB')
  df = st.session_state['data']

  if df.empty:
    st.warning('Database kosong.')
  else:
    with st.expander('➕ Tambah Barang ke Daftar', expanded=True):
      col1, col2, col3 = st.columns(3)
      with col1:
        b_list = sorted(df['BRAND NAME'].dropna().unique().astype(str))
        sel_brand = st.selectbox('Pilih Brand', b_list)
      with col2:
        filtered_df_brand = df[df['BRAND NAME'] == sel_brand]
        i_list = sorted(
            filtered_df_brand['ITEM NAME'].dropna().unique().astype(str)
        )
        sel_item = st.selectbox('Pilih Nama Barang', i_list)
      with col3:
        filtered_df_item = filtered_df_brand[
            filtered_df_brand['ITEM NAME'] == sel_item
        ]
        t_list = sorted(
            filtered_df_item['TYPE'].dropna().unique().astype(str)
        )
        sel_type = st.selectbox('Pilih Type', t_list)

      res = df[
          (df['BRAND NAME'] == sel_brand)
          & (df['ITEM NAME'] == sel_item)
          & (df['TYPE'] == sel_type)
      ]

      if not res.empty:
        st.info(f"**Spesifikasi:** {res['SPECS'].values[0]}")

      st.divider()

      c_qty, c_unit, c_date, c_rem = st.columns([1, 1, 2, 3])
      with c_qty:
        qty = st.number_input('Jumlah', min_value=1, value=1)
      with c_unit:
        unit = st.selectbox('Satuan', ['pcs', 'lot', 'set', 'unit', 'mtr'])
      with c_date:
        d_date = st.date_input('Due Date', date.today())
      with c_rem:
        remarks = st.text_input(
            'Remarks / Keterangan', placeholder='Contoh: Untuk Proyek A'
        )

      if st.button('Tambah ke Daftar Belanja'):
        row_data = df[
            (df['BRAND NAME'] == sel_brand)
            & (df['ITEM NAME'] == sel_item)
            & (df['TYPE'] == sel_type)
        ]

        current_specs = (
            row_data['SPECS'].values[0] if not row_data.empty else ''
        )

        new_entry = {
            'Brand Name': sel_brand,
            'Item Name': sel_item,
            'Type': sel_type,
            'Specs': current_specs,
            'Qty': qty,
            'Unit': unit,
            'Due Date': str(d_date),
            'Remarks': remarks,
        }
        st.session_state['shopping_list'].append(new_entry)
        save_shopping_list(st.session_state['shopping_list'])
        st.success('Barang berhasil ditambahkan dan disimpan ke GitHub!')
        st.rerun()

    if st.session_state['shopping_list']:
      st.divider()

      st.subheader('🏢 Informasi Header Dokumen')
      col_c, col_p, col_n, col_d = st.columns(4)
      with col_c:
        client_input = st.text_input(
            'Nama Client', placeholder='Contoh: PT. Maju Jaya'
        )
      with col_p:
        project_input = st.text_input(
            'Nama Proyek', placeholder='Contoh: Maintenance Robot A'
        )
      with col_n:
        doc_input = st.text_input('Nomor PO', placeholder='Contoh: PR/2024/001')
      with col_d:
        dvs_input = st.text_input('Divisi', placeholder='Masukkan nama divisi')

      tab1, tab2 = st.tabs(['📊 Kelola Daftar', '📄 Preview PDF'])

      with tab1:
        st.subheader('🛒 Keranjang Belanja')

        h_col = st.columns(
            [0.5, 2, 2, 2.5, 2.5, 0.5, 0.5, 1.5, 1.5, 0.75, 0.75]
        )
        h_col[0].write('**No**')
        h_col[1].write('**Item Name**')
        h_col[2].write('**Brand Name**')
        h_col[3].write('**Type**')
        h_col[4].write('**Specs**')
        h_col[5].write('**Qty**')
        h_col[6].write('**Unit**')
        h_col[7].write('**Due Date**')
        h_col[8].write('**Remarks**')
        h_col[9].write('**Aksi**')

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

          with col[9]:
            if st.button('🗑️', key=f'del_{idx}'):
              st.session_state['shopping_list'].pop(idx)
              save_shopping_list(st.session_state['shopping_list'])
              st.rerun()

          with col[10]:
            with st.popover('📝'):
              st.write(f'Edit Item {idx+1}')
              edit_qty = st.number_input(
                  'Qty', value=int(item['Qty']), key=f'eqty_{idx}'
              )

              units_option = ['pcs', 'lot', 'set', 'unit', 'mtr']
              unit_idx = (
                  units_option.index(item['Unit'])
                  if item['Unit'] in units_option
                  else 0
              )
              edit_unit = st.selectbox(
                  'Unit', units_option, index=unit_idx, key=f'eunit_{idx}'
              )

              edit_date = st.date_input('Due Date', key=f'edate_{idx}')
              edit_rem = st.text_input(
                  'Remarks', value=str(item['Remarks']), key=f'erem_{idx}'
              )

              if st.button('Update', key=f'upd_{idx}'):
                st.session_state['shopping_list'][idx]['Qty'] = edit_qty
                st.session_state['shopping_list'][idx]['Unit'] = edit_unit
                st.session_state['shopping_list'][idx]['Due Date'] = str(
                    edit_date
                )
                st.session_state['shopping_list'][idx]['Remarks'] = edit_rem
                save_shopping_list(st.session_state['shopping_list'])
                st.success('Terupdate!')
                st.rerun()

        if st.button('🗑️ Kosongkan Semua Daftar', type='secondary'):
          st.session_state['shopping_list'] = []
          save_shopping_list([])
          st.rerun()

      with tab2:
        st.subheader('🖼️ Preview Dokumen')

        paper_size = st.selectbox(
            'Pilih Ukuran Kertas:', ['A4', 'A3', 'Letter', 'Legal']
        )

        pdf_data = generate_pdf(
            st.session_state['shopping_list'],
            format_kertas=paper_size,
            client=client_input,
            project=project_input,
            doc_no=doc_input,
            dvs=dvs_input,
        )

        display_pdf_preview(pdf_data)

        st.download_button(
            label='📥 Download PDF',
            data=pdf_data,
            file_name=f"Daftar_{doc_input if doc_input else 'FPPB'}.pdf",
            mime='application/pdf',
        )
    else:
      st.info('Belum ada barang di daftar belanja.')

# --- MENU: INPUT MASTER DATA ---
elif menu == 'Input Master Data':
  st.subheader('Input Manual Master Data')
  df = st.session_state['data']

  with st.form('input_form', clear_on_submit=True):
    new_brand = st.text_input('Nama Brand')
    new_item = st.text_input('Nama Item')
    new_type = st.text_input('Type / Model')
    new_specs = st.text_area('Spesifikasi')

    submit_button = st.form_submit_button('Simpan ke Database')

    if submit_button:
      if new_brand and new_item and new_type:
        is_duplicate = (
            (df['BRAND NAME'].astype(str) == new_brand.strip())
            & (df['ITEM NAME'].astype(str) == new_item.strip())
            & (df['TYPE'].astype(str) == new_type.strip())
        ).any()

        if is_duplicate:
          st.error(
              f"❌ Data Gagal Disimpan! Tipe '{new_type}' untuk Brand"
              f" '{new_brand}' sudah ada di database."
          )
        else:
          new_row = {
              'BRAND NAME': new_brand.strip(),
              'ITEM NAME': new_item.strip(),
              'TYPE': new_type.strip(),
              'SPECS': new_specs.strip(),
          }

          st.session_state['data'] = pd.concat(
              [st.session_state['data'], pd.DataFrame([new_row])],
              ignore_index=True,
          )
          save_data(st.session_state['data'])
          st.success(
              f'Data {new_type} berhasil disimpan & di-sync ke GitHub!'
          )
          st.rerun()
      else:
        st.error('Mohon isi Brand, Item, dan Type!')

  if not df.empty:
    st.subheader('Pencarian Material')
    col1, col2, col3 = st.columns(3)

    with col1:
      brand_list = sorted(df['BRAND NAME'].dropna().unique())
      selected_brand = st.selectbox('Pilih Brand', brand_list)

    with col2:
      filtered_item = (
          df[df['BRAND NAME'] == selected_brand]['ITEM NAME'].dropna().unique()
      )
      selected_item = st.selectbox('Pilih Item Name', sorted(filtered_item))

    with col3:
      filtered_type = (
          df[
              (df['BRAND NAME'] == selected_brand)
              & (df['ITEM NAME'] == selected_item)
          ]['TYPE']
          .dropna()
          .unique()
      )
      selected_type = st.selectbox('Pilih Type', sorted(filtered_type))

    res = df[
        (df['BRAND NAME'] == selected_brand)
        & (df['ITEM NAME'] == selected_item)
        & (df['TYPE'] == selected_type)
    ]

    if not res.empty:
      st.info(f"**Spesifikasi:** {res['SPECS'].values[0]}")

    st.divider()
    st.subheader('Seluruh Database')
    st.dataframe(df, use_container_width=True)
  else:
    st.info('Database kosong. Silakan Input Manual atau Import data.')

# --- MENU: IMPORT DATA ---
elif menu == 'Import Data':
  st.subheader('Import Database dari File')
  uploaded_file = st.file_uploader('Unggah File', type=['xlsx', 'csv'])

  if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
      new_df = pd.read_csv(
          uploaded_file,
          sep=None,
          engine='python',
          dtype=str,
          on_bad_lines='skip',
          quotechar='"',
      )
    else:
      new_df = pd.read_excel(uploaded_file, dtype=str)

    new_df.columns = new_df.columns.astype(str).str.strip()

    if all(col in new_df.columns for col in COLS):
      if st.button('Gabungkan ke Database'):
        combined_df = pd.concat(
            [st.session_state['data'], new_df[COLS]], ignore_index=True
        )

        for col in COLS:
          combined_df[col] = combined_df[col].fillna('').astype(str).str.strip()

        combined_df = combined_df.drop_duplicates()

        st.session_state['data'] = combined_df
        save_data(combined_df)
        st.success('Data berhasil digabungkan dan diperbarui di GitHub!')
        st.rerun()
    else:
      st.error(
          f'Format file tidak valid. Pastikan ada kolom: {", ".join(COLS)}'
      )

# --- MENU: VIEW DATABASE ---
elif menu == 'View Database':
  st.subheader('Manajemen Database Barang')

  df = load_data()
  st.session_state['data'] = df

  if not df.empty:
    st.write(f'Total Data Terbaca: **{len(df)}** item')
    st.dataframe(df, use_container_width=True)
    st.divider()

    df_temp = df.copy()
    df_temp['select_label'] = (
        df_temp['BRAND NAME'].astype(str)
        + ' | '
        + df_temp['ITEM NAME'].astype(str)
        + ' ('
        + df_temp['TYPE'].astype(str)
        + ')'
    )

    st.subheader('📝 Ubah / 🗑️ Hapus Data')
    selected_item = st.selectbox(
        'Pilih data yang akan dikelola:', df_temp['select_label'].unique()
    )

    idx = df_temp[df_temp['select_label'] == selected_item].index[0]
    data_lama = df.iloc[idx]

    if st.button('🗑️ Hapus Baris Ini', type='secondary'):
      df_updated = df.drop(idx).reset_index(drop=True)
      st.session_state['data'] = df_updated
      if save_data(df_updated):
        st.success('Data berhasil dihapus dari GitHub!')
        st.rerun()

    st.divider()

    st.subheader(f"Edit Data: {data_lama['TYPE']}")
    with st.form('form_edit', clear_on_submit=False):
      edit_brand = st.text_input(
          'Ubah Brand', value=str(data_lama['BRAND NAME'])
      )
      edit_item = st.text_input(
          'Ubah Nama Item', value=str(data_lama['ITEM NAME'])
      )
      edit_type = st.text_input('Ubah Type', value=str(data_lama['TYPE']))
      edit_specs = st.text_area(
          'Ubah Spesifikasi', value=str(data_lama['SPECS'])
      )

      save_edit = st.form_submit_button('💾 Simpan Perubahan')

      if save_edit:
        is_duplicate = (
            (df.index != idx)
            & (df['BRAND NAME'] == edit_brand.strip())
            & (df['ITEM NAME'] == edit_item.strip())
            & (df['TYPE'] == edit_type.strip())
        ).any()

        if is_duplicate:
          st.error(
              '❌ Perubahan gagal! Kombinasi Brand, Item, dan Type tersebut'
              ' sudah ada di data lain.'
          )
        else:
          df.at[idx, 'BRAND NAME'] = edit_brand.strip()
          df.at[idx, 'ITEM NAME'] = edit_item.strip()
          df.at[idx, 'TYPE'] = edit_type.strip()
          df.at[idx, 'SPECS'] = edit_specs.strip()

          st.session_state['data'] = df
          if save_data(df):
            st.success('✅ Data berhasil diperbarui di GitHub!')
            st.rerun()
  else:
    st.info('Database kosong.')
