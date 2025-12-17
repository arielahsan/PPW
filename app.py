# =========================================================
# IMPORT LIBRARY
# =========================================================

import streamlit as st                  # Framework utama untuk membuat Web App interaktif
import fitz                             # PyMuPDF: membaca dan mengekstrak teks dari PDF
import nltk                             # Library NLP (Natural Language Processing)
from nltk.corpus import stopwords       # Mengambil daftar stopwords (kata umum)
from nltk.tokenize import word_tokenize # Memecah teks menjadi kata (tokenisasi)
import pandas as pd                     # Mengelola data tabel (seperti Excel)
import networkx as nx                   # Membuat graph dan menghitung PageRank
from pyvis.network import Network       # Visualisasi graph berbasis HTML (interaktif)
import tempfile                         # Membuat file PDF sementara
import re                               # Regex untuk membersihkan teks
import streamlit.components.v1 as components # Menampilkan HTML ke Streamlit
import os                               # Operasi sistem (hapus file sementara)

# =========================================================
# 1. KONFIGURASI HALAMAN STREAMLIT
# =========================================================

st.set_page_config(
    page_title="Analisis Relasi Kata PDF",  # Judul tab browser
    layout="wide"                           # Layout lebar (kanan–kiri)
)

# =========================================================
# 2. CSS TAMBAHAN (HANYA UNTUK TAMPILAN)
# =========================================================

# CSS ini hanya mengatur tampilan, TIDAK mempengaruhi algoritma
st.markdown("""
<style>
.main-title {
    font-size: 36px;
    font-weight: bold;
    color: #1f77b4;
}
.sub-title {
    font-size: 18px;
    color: #555;
    margin-bottom: 20px;
}
.section-box {
    padding: 15px;
    border-radius: 10px;
    background-color: #f8f9fa;
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. DOWNLOAD RESOURCE NLTK (DIJALANKAN SEKALI SAJA)
# =========================================================

@st.cache_resource                     # Cache agar tidak download berulang
def download_nltk_data():
    resources = ['punkt', 'stopwords', 'punkt_tab']  # Resource NLTK yang dibutuhkan
    for res in resources:
        try:
            nltk.data.find(f'tokenizers/{res}')       # Cek apakah sudah ada
        except LookupError:
            nltk.download(res, quiet=True)            # Download jika belum ada

    try:
        nltk.data.find('corpora/stopwords')           # Cek stopwords
    except LookupError:
        nltk.download('stopwords', quiet=True)        # Download stopwords

# =========================================================
# 4. FUNGSI MEMBACA DAN MENGAMBIL TEKS DARI PDF
# =========================================================

def extract_text_from_pdf(uploaded_file):
    # Membuat file PDF sementara karena PyMuPDF butuh file fisik
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getvalue())            # Salin isi PDF
        tmp_path = tmp.name                            # Simpan path file sementara

    doc = fitz.open(tmp_path)                          # Buka PDF dengan PyMuPDF
    text = ""                                          # Variabel penampung teks

    for page in doc:                                   # Loop setiap halaman PDF
        text += page.get_text()                        # Ambil teks per halaman

    doc.close()                                        # Tutup dokumen PDF
    os.remove(tmp_path)                                # Hapus file sementara
    return text                                        # Kembalikan teks mentah

# =========================================================
# 5. PEMBERSIHAN DAN TOKENISASI TEKS
# =========================================================

def process_text(text):
    text = re.sub(r'\d+', '', text)                    # Hapus semua angka
    text = re.sub(r'[^\w\s]', '', text)                # Hapus tanda baca
    text = text.lower()                                # Ubah ke huruf kecil

    try:
        words = word_tokenize(text)                    # Tokenisasi dengan NLTK
    except:
        words = text.split()                           # Cadangan jika error

    try:
        stop_words = set(stopwords.words('indonesian'))# Stopwords Bahasa Indonesia
    except:
        stop_words = set()                             # Jika gagal, kosongkan

    # Stopwords tambahan khusus dokumen ilmiah
    custom_stopwords = [
        'dan','yang','di','ke','dari','ini','itu','pada','untuk','dengan',
        'adalah','sebagai','juga','karena','oleh','dalam','akan','dapat',
        'penelitian','data','hasil','analisis','kesimpulan','metode',
        'jurnal','paper','bab','tabel','gambar','abstrak','keyword'
    ]

    stop_words.update(custom_stopwords)                # Gabungkan stopwords

    # Ambil hanya kata:
    # - huruf saja
    # - bukan stopwords
    # - panjang > 2 karakter
    filtered_words = [
        w for w in words
        if w.isalpha() and w not in stop_words and len(w) > 2
    ]

    return filtered_words                              # Kembalikan kata bersih

# =========================================================
# 6. MEMBANGUN GRAPH RELASI KATA (CO-OCCURRENCE)
# =========================================================

def build_graph(words, window_size=2):
    co_occurrences = {}                                # Menyimpan pasangan kata

    for i in range(len(words) - window_size):
        target = words[i]                              # Kata utama
        context = words[i+1:i+1+window_size]           # Kata di sekitarnya

        for neighbor in context:
            if target == neighbor:                     # Lewati jika sama
                continue
            pair = tuple(sorted((target, neighbor)))   # Urutkan pasangan
            co_occurrences[pair] = co_occurrences.get(pair, 0) + 1

    G = nx.Graph()                                     # Buat graph kosong

    for (u, v), w in co_occurrences.items():
        G.add_edge(u, v, weight=w)                     # Tambah edge ke graph

    return G                                           # Kembalikan graph

# =========================================================
# 7. PROGRAM UTAMA STREAMLIT
# =========================================================

def main():
    download_nltk_data()                               # Pastikan NLTK siap

    # Session state untuk menyimpan hasil tiap file PDF
    if 'paper_data' not in st.session_state:
        st.session_state.paper_data = {}

    if 'active_file_key' not in st.session_state:
        st.session_state.active_file_key = None

    # ---------- JUDUL ----------
    st.markdown("<div class='main-title'>📄 Analisis Relasi Kata Dokumen PDF</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Visualisasi graph statis berbasis NLP & PageRank</div>", unsafe_allow_html=True)

    # ---------- SIDEBAR ----------
    with st.sidebar:
        st.header("⚙️ Kontrol Aplikasi")
        uploaded_files = st.file_uploader(
            "Upload File PDF",                         # Tombol upload
            type="pdf",
            accept_multiple_files=True                 # Bisa upload banyak PDF
        )
        window_size = st.slider(
            "Jarak Relasi Kata", 1, 5, 2               # Parameter window co-occurrence
        )

    # ---------- PROSES FILE ----------
    if uploaded_files:
        for uploaded_file in uploaded_files:
            fname = uploaded_file.name                 # Nama file PDF

            if fname not in st.session_state.paper_data:
                with st.spinner(f"Memproses {fname}..."):
                    raw_text = extract_text_from_pdf(uploaded_file)  # Baca PDF
                    words = process_text(raw_text)                   # Bersihkan teks

                    if len(words) > 5:
                        G = build_graph(words, window_size)          # Bangun graph
                        pr = nx.pagerank(G, alpha=0.85)              # Hitung PageRank

                        df = pd.DataFrame(
                            pr.items(), columns=['Kata', 'PageRank']
                        ).sort_values('PageRank', ascending=False)

                        st.session_state.paper_data[fname] = {
                            'graph': G,
                            'pagerank': pr,
                            'df': df,
                            'count': len(words)
                        }

                        st.session_state.active_file_key = fname

        files = list(st.session_state.paper_data.keys())
        selected_file = st.sidebar.selectbox(
            "Pilih Dokumen", files, key='active_file_key'
        )

        data = st.session_state.paper_data[selected_file]
        G = data['graph']
        df = data['df']
        pr = data['pagerank']

        # ---------- INFORMASI ----------
        st.markdown("<div class='section-box'>", unsafe_allow_html=True)
        st.subheader(f"📘 Dokumen Aktif: {selected_file}")
        st.success(f"Kata bersih: {data['count']} | Node graph: {len(G.nodes())}")
        st.markdown("</div>", unsafe_allow_html=True)

        col_graph, col_table = st.columns([3, 2])

        # =================================================
        # VISUALISASI GRAPH (STATIS / TIDAK BERGERAK)
        # =================================================
        with col_graph:
            st.subheader("🕸️ Visualisasi Jaringan Kata (Statis)")

            pos = nx.spring_layout(G, seed=42)          # Hitung posisi node sekali

            net = Network(
                height="600px",
                width="100%",
                bgcolor="#ffffff",
                font_color="black"
            )

            net.from_nx(G)                              # Masukkan graph NetworkX

            for node in net.nodes:
                word = node["id"]
                node["x"] = pos[word][0] * 1000         # Posisi X statis
                node["y"] = pos[word][1] * 1000         # Posisi Y statis
                node["physics"] = False                 # Matikan gerak
                node["fixed"] = True                    # Kunci posisi

                score = pr.get(word, 0.01)
                node["size"] = score * 1000             # Ukuran node
                node["title"] = f"Kata: {word}<br>PageRank: {score:.4f}"

            net.toggle_physics(False)                   # Pastikan graph statis

            net.save_graph("graph.html")                # Simpan HTML
            with open("graph.html", "r", encoding="utf-8") as f:
                components.html(f.read(), height=620)   # Tampilkan ke Streamlit

        # ---------- TABEL ----------
        with col_table:
            st.subheader("📊 Ranking Kata (PageRank)")
            st.bar_chart(df.head(20).set_index("Kata")) # Grafik batang
            st.dataframe(df, use_container_width=True)  # Tabel lengkap

    else:
        st.info("Silakan upload file PDF melalui sidebar.")

# =========================================================
# ENTRY POINT PROGRAM
# =========================================================

if __name__ == "__main__":
    main()                                             # Jalankan aplikasi