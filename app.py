import streamlit as st                  # Library utama untuk membuat tampilan Web App (UI)
import fitz  # PyMuPDF                  # Library khusus untuk membuka dan membaca teks dari file PDF
import nltk                             # Natural Language Toolkit: Otak kecerdasan buatan untuk bahasa
from nltk.corpus import stopwords       # Mengambil daftar "kata sampah" (seperti: dan, yang, di) untuk dibuang
from nltk.tokenize import word_tokenize # Alat untuk memotong kalimat panjang menjadi kata-kata (token)
import pandas as pd                     # Library untuk membuat tabel data yang rapi (seperti Excel)
import networkx as nx                   # Library matematika untuk menghitung hubungan antar titik (Graph)
from pyvis.network import Network       # Library untuk visualisasi Graph yang bisa digerakkan (Interaktif)
import tempfile                         # Library untuk membuat file sementara (karena PyMuPDF butuh file fisik)
import re                               # Regex: Alat pencari pola teks (misal: hapus semua angka)
import streamlit.components.v1 as components # Alat agar HTML hasil graph bisa muncul di Streamlit
import os                               # Library untuk perintah sistem (seperti hapus file temp)

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
# Mengatur judul tab browser dan layout agar melebar (wide)
st.set_page_config(page_title="Analisis Paper PDF Di Upload", layout="wide") 

# ==========================================
# 2. FUNGSI DOWNLOAD RESOURCE BAHASA
# ==========================================
# @st.cache_resource agar download hanya dilakukan sekali saat pertama run
@st.cache_resource
def download_nltk_data():
    # Daftar paket bahasa yang wajib ada
    resources = ['punkt', 'stopwords', 'punkt_tab']
    for res in resources:
        try:
            # Cek apakah paket sudah ada di folder komputer?
            nltk.data.find(f'tokenizers/{res}')
        except LookupError:
            # Jika tidak ada, download diam-diam (quiet=True)
            nltk.download(res, quiet=True)
    try:
        # Cek ganda khusus untuk stopwords
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)

# ==========================================
# 3. FUNGSI MEMBACA PDF
# ==========================================
def extract_text_from_pdf(uploaded_file):
    # Membuat file sementara (temporary) karena PyMuPDF tidak bisa baca langsung dari RAM
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue()) # Salin isi PDF ke file temp
        tmp_path = tmp_file.name # Simpan alamat file temp tersebut
    
    doc = fitz.open(tmp_path) # Buka file PDF dari alamat temp
    text = ""                 # Siapkan wadah teks kosong
    for page in doc:          # Loop per halaman
        text += page.get_text() # Ambil teks dan gabungkan
    
    doc.close()               # Tutup file PDF
    os.remove(tmp_path)       # HAPUS file temp biar hardisk tidak penuh sampah
    return text               # Kembalikan teks bersih

# ==========================================
# 4. FUNGSI BERSIH-BERSIH TEKS
# ==========================================
def process_text(text):
    text = re.sub(r'\d+', '', text)        # Hapus semua angka (0-9)
    text = re.sub(r'[^\w\s]', '', text)    # Hapus tanda baca (bukan huruf/spasi)
    text = text.lower()                    # Ubah semua jadi huruf kecil
    
    try:
        words = word_tokenize(text)        # Coba potong kata pakai NLTK
    except:
        words = text.split()               # Jika error, potong pakai spasi biasa
    
    try:
        stop_words = set(stopwords.words('indonesian')) # Ambil kata sambung B.Indo
    except:
        stop_words = set()                 # Jika gagal, pakai set kosong
        
    # Daftar kata sampah tambahan buatan sendiri
    custom_stopwords = [
        'dan', 'yang', 'di', 'ke', 'dari', 'ini', 'itu', 'pada', 'untuk', 'dengan', 'adalah', 
        'sebagai', 'juga', 'karena', 'oleh', 'dalam', 'akan', 'dapat', 'tersebut', 'saya', 'kita',
        'kami', 'anda', 'ia', 'dia', 'mereka', 'apa', 'siapa', 'bagaimana', 'mengapa', 'kapan',
        'dimana', 'kenapa', 'bisa', 'ada', 'tidak', 'ya', 'hal', 'maka', 'atau', 'jika', 'saat',
        'serta', 'setelah', 'sebelum', 'lalu', 'sedangkan', 'meskipun', 'sehingga', 'namun',
        'bagi', 'antara', 'selama', 'setiap', 'suatu', 'sudah', 'telah', 'agar', 'pun',
        'gambar', 'tabel', 'penelitian', 'metode', 'data', 'hasil', 'analisis', 'pembahasan',
        'kesimpulan', 'saran', 'daftar', 'pustaka', 'universitas', 'jurusan', 'fakultas',
        'skripsi', 'tesis', 'disertasi', 'jurnal', 'paper', 'makalah', 'bab', 'halaman',
        'berdasarkan', 'menggunakan', 'dilakukan', 'merupakan', 'terhadap', 'adanya', 
        'menunjukkan', 'terdiri', 'mengenai', 'dijelaskan', 'penerapan', 'penggunaan', 
        'perancangan', 'pengujian', 'implementasi', 'sistem', 'aplikasi', 'program', 'proses',
        'studi', 'kasus', 'abstract', 'abstrak', 'keyword', 'kata', 'kunci', 'latar', 'belakang'
    ]
    stop_words.update(custom_stopwords) # Gabungkan stopwords bawaan + custom
    
    # Filter terakhir: Hanya ambil jika Huruf, Bukan Stopword, dan Panjang > 2
    filtered_words = [word for word in words if word.isalpha() and word not in stop_words and len(word) > 2]
    return filtered_words

# ==========================================
# 5. FUNGSI MEMBUAT GRAPH
# ==========================================
def build_graph(words, window_size=2):
    co_occurrences = {} # Kamus untuk mencatat pasangan kata
    
    # Loop dari kata pertama sampai hampir akhir
    for i in range(len(words) - window_size):
        target = words[i] # Kata pusat
        context = words[i+1 : i+1+window_size] # Kata-kata tetangga di kanannya
        
        for neighbor in context:
            if target == neighbor: continue # Skip jika katanya sama
            
            # Urutkan pasangan agar (A, B) dianggap sama dengan (B, A)
            pair = tuple(sorted((target, neighbor))) 
            
            # Hitung frekuensi
            if pair in co_occurrences:
                co_occurrences[pair] += 1
            else:
                co_occurrences[pair] = 1
                
    G = nx.Graph() # Buat wadah Graph kosong
    
    # Masukkan data pasangan kata sebagai Garis (Edge) ke dalam Graph
    for (u, v), weight in co_occurrences.items():
        G.add_edge(u, v, weight=weight)
    return G

# ==========================================
# 6. PROGRAM UTAMA (MAIN)
# ==========================================
def main():
    download_nltk_data() # Jalankan download data bahasa
    
    # --- SETUP MEMORI (SESSION STATE) ---
    
    # 1. Wadah Data ('paper_data'):
    # Disini kita simpan data Paper A, Paper B secara terpisah (Dictionary)
    if 'paper_data' not in st.session_state:
        st.session_state.paper_data = {}
        
    # 2. Penunjuk File Aktif ('active_file_key'):
    # Variabel ini mencatat "File apa yang sedang dilihat user sekarang?"
    # Ini kunci fitur Auto-Switch.
    if 'active_file_key' not in st.session_state:
        st.session_state.active_file_key = None

    # Judul Aplikasi
    st.title("Analisis Paper PDF Di Uploadr")
    st.markdown("Upload file baru -> Tampilan akan otomatis pindah ke file tersebut.")

    # --- SIDEBAR (PANEL KIRI) ---
    with st.sidebar:
        st.header("1. Upload & Settings")
        
        # Tombol Upload (Bisa banyak file sekaligus)
        uploaded_files = st.file_uploader(
            "Upload PDF Disini (Bisa Banyak)", 
            type="pdf", 
            accept_multiple_files=True
        )
        
        st.divider()
        window_size = st.slider("Jarak Hubungan Kata", 1, 5, 2)
        st.info("Setiap file diproses di laci terpisah.")

    # --- LOGIKA PROSES DATA ---
    if uploaded_files:
        # Loop: Cek satu per satu file yang ada di uploader
        for uploaded_file in uploaded_files:
            file_name = uploaded_file.name # Ambil nama file
            
            # [LOGIKA EFISIENSI]
            # Cek: Apakah file ini SUDAH ADA di memori 'paper_data'?
            # Jika BELUM ADA, berarti ini file BARU -> Proses!
            if file_name not in st.session_state.paper_data:
                
                with st.spinner(f"Sedang membedah {file_name}..."):
                    # Proses 1: Baca PDF
                    raw_text = extract_text_from_pdf(uploaded_file)
                    # Proses 2: Bersihkan Teks
                    words = process_text(raw_text)
                    
                    if len(words) > 5: # Validasi panjang teks
                        # Proses 3: Bikin Graph
                        G = build_graph(words, window_size)
                        
                        if len(G.nodes) > 0:
                            # Proses 4: Hitung Ranking (PageRank)
                            pr = nx.pagerank(G, alpha=0.85)
                            
                            # Proses 5: Bikin Tabel Statistik
                            df = pd.DataFrame(list(pr.items()), columns=['Kata', 'PageRank'])
                            df = df.sort_values(by='PageRank', ascending=False).reset_index(drop=True)
                            df.insert(0, 'ID', range(1, 1 + len(df))) # Tambah kolom ID
                            
                            # [LOGIKA PENYIMPANAN TERPISAH]
                            # Simpan hasil ke laci khusus milik file ini
                            st.session_state.paper_data[file_name] = {
                                'graph': G,
                                'pagerank': pr,
                                'df': df,
                                'count': len(words)
                            }
                            
                            # [LOGIKA AUTO-SWITCH]
                            # Karena ini file baru, kita paksa variabel 'active_file_key'
                            # menjadi nama file ini. Nanti menu dropdown akan ikut berubah.
                            st.session_state.active_file_key = file_name
                            
                        else:
                            st.warning(f"File {file_name} kurang relasi kata.")
                    else:
                        st.warning(f"File {file_name} teksnya kosong/pendek.")

        # --- LOGIKA NAVIGASI & TAMPILAN ---
        
        # Ambil daftar file yang datanya sudah siap
        processed_files = list(st.session_state.paper_data.keys())
        
        if processed_files:
            st.sidebar.divider()
            st.sidebar.header("2. Pilih File")
            
            # Penjaga: Jika file aktif terhapus, pindah ke file pertama yang ada
            if st.session_state.active_file_key not in processed_files:
                st.session_state.active_file_key = processed_files[0]

            # [MENU DROPDOWN NAVIGASI]
            # Parameter key='active_file_key' mengikat menu ini dengan variabel Auto-Switch tadi.
            # Jadi kalau variabel berubah, menu ini berubah. Kalau menu diklik, variabel berubah.
            selected_file = st.sidebar.selectbox(
                "Tampilkan Analisis Paper:",
                options=processed_files,
                key='active_file_key' 
            )
            
            # --- RENDER HASIL VISUALISASI ---
            if selected_file:
                # Ambil data HANYA dari laci file yang dipilih
                data = st.session_state.paper_data[selected_file]
                
                # Bongkar datanya
                G = data['graph']
                pr = data['pagerank']
                df = data['df']
                word_count = data['count']

                # Judul File
                st.subheader(f"📄 Analisis File: {selected_file}")
                st.success(f"Kata bersih: {word_count} | Node Graph: {len(G.nodes())}")

                # Bagi Layar: Kiri (Graph), Kanan (Tabel)
                col_graph, col_stats = st.columns([3, 2])

                # --- VISUALISASI GRAPH (KIRI) ---
                with col_graph:
                    st.subheader("🕸️ Relasi Kata (Network)")
                    pos = nx.spring_layout(G, k=0.5, seed=42) # Hitung posisi titik
                    
                    # Konfigurasi PyVis
                    net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black")
                    net.from_nx(G)

                    # Percantik Node
                    for node in net.nodes:
                        word = node['id']
                        node['x'] = pos[word][0] * 1000 # Set posisi X
                        node['y'] = pos[word][1] * 1000 # Set posisi Y
                        node['physics'] = False         # Matikan gerak (biar stabil)
                        
                        score = pr.get(word, 0.01)
                        node['size'] = score * 1000     # Ukuran berdasarkan ranking
                        # Tulisan saat mouse diarahkan ke titik
                        node['title'] = f"Kata: {word}\nRank: {df[df['Kata']==word].index[0]+1}\nSkor: {score:.4f}"

                    net.toggle_physics(False)

                    try:
                        # Simpan ke HTML sementara lalu baca lagi
                        path_html = "graph.html"
                        net.save_graph(path_html)
                        with open(path_html, 'r', encoding='utf-8') as f:
                            html_source = f.read()
                        # Tampilkan HTML di Streamlit
                        components.html(html_source, height=620)
                    except Exception as e:
                        st.error(f"Error visualisasi: {e}")

                # --- VISUALISASI STATISTIK (KANAN) ---
                with col_stats:
                    st.subheader("📊 Ranking Kata")
                    st.caption("Top 20 Kata Paling Penting")
                    
                    # Grafik Batang
                    top_df = df.head(20)
                    st.bar_chart(top_df.set_index('Kata')['PageRank'])
                    
                    st.divider()
                    st.subheader("📋 Tabel Data")
                    # Tabel Lengkap
                    st.dataframe(df, use_container_width=True, height=300, hide_index=True)
        else:
            st.info("Belum ada file yang berhasil diproses.")

    else:
        # --- RESET JIKA TOMBOL HAPUS (X) DITEKAN ---
        st.session_state.paper_data = {}       # Hapus semua data
        st.session_state.active_file_key = None # Reset pilihan file
        st.info("Silakan upload file PDF di sidebar.")

if __name__ == "__main__":
    main()
