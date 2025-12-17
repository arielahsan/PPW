# =========================================================
# IMPORT LIBRARY
# =========================================================

import streamlit as st                  # Framework utama untuk membangun Web App berbasis Python
import fitz  # PyMuPDF                  # Library untuk membaca dan mengekstrak teks dari file PDF
import nltk                             # Natural Language Toolkit untuk pemrosesan bahasa alami
from nltk.corpus import stopwords       # Mengambil daftar stopwords (kata umum yang dibuang)
from nltk.tokenize import word_tokenize # Tokenisasi: memecah teks menjadi kata
import pandas as pd                     # Mengelola data tabel (mirip Excel)
import networkx as nx                   # Membuat dan menganalisis Graph (jaringan kata)
from pyvis.network import Network       # Visualisasi graph interaktif berbasis HTML
import tempfile                         # Membuat file sementara
import re                               # Regex untuk pembersihan teks
import streamlit.components.v1 as components # Menampilkan HTML ke Streamlit
import os                               # Operasi sistem (hapus file, path, dll)

# =========================================================
# 1. KONFIGURASI HALAMAN STREAMLIT
# =========================================================

# Mengatur judul tab browser dan layout agar lebar
st.set_page_config(
    page_title="Analisis Relasi Kata PDF",
    layout="wide"
)

# =========================================================
# 2. CSS TAMBAHAN (HANYA UNTUK TAMPILAN)
# =========================================================

# CSS ini TIDAK mempengaruhi fungsi, hanya visual
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
# 3. DOWNLOAD RESOURCE NLTK (SEKALI SAJA)
# =========================================================

# Cache agar download tidak berulang saat app reload
@st.cache_resource
def download_nltk_data():
    """
    Fungsi untuk memastikan resource NLTK tersedia:
    - punkt       : tokenizer
    - stopwords   : kata umum
    """
    resources = ['punkt', 'stopwords', 'punkt_tab']
    for res in resources:
        try:
            nltk.data.find(f'tokenizers/{res}')
        except LookupError:
            nltk.download(res, quiet=True)

    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)

# =========================================================
# 4. EKSTRAK TEKS DARI PDF
# =========================================================

def extract_text_from_pdf(uploaded_file):
    """
    Membaca file PDF dan mengembalikan teks mentah.
    Menggunakan file sementara karena PyMuPDF
    tidak bisa membaca langsung dari memory.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    doc = fitz.open(tmp_path)
    text = ""
    for page in doc:
        text += page.get_text()

    doc.close()
    os.remove(tmp_path)
    return text

# =========================================================
# 5. PEMBERSIHAN & TOKENISASI TEKS
# =========================================================

def process_text(text):
    """
    Membersihkan teks:
    - Hapus angka
    - Hapus tanda baca
    - Lowercase
    - Tokenisasi
    - Hapus stopwords
    """
    text = re.sub(r'\d+', '', text)
    text = re.sub(r'[^\w\s]', '', text)
    text = text.lower()

    try:
        words = word_tokenize(text)
    except:
        words = text.split()

    try:
        stop_words = set(stopwords.words('indonesian'))
    except:
        stop_words = set()

    # Stopwords tambahan khusus dokumen akademik
    custom_stopwords = [
        'dan','yang','di','ke','dari','ini','itu','pada','untuk','dengan',
        'adalah','sebagai','juga','karena','oleh','dalam','akan','dapat',
        'penelitian','data','hasil','analisis','kesimpulan','metode',
        'jurnal','paper','bab','tabel','gambar','abstrak','keyword'
    ]

    stop_words.update(custom_stopwords)

    # Filter akhir
    filtered_words = [
        word for word in words
        if word.isalpha() and word not in stop_words and len(word) > 2
    ]

    return filtered_words

# =========================================================
# 6. MEMBANGUN GRAPH RELASI KATA
# =========================================================

def build_graph(words, window_size=2):
    """
    Membentuk graph berdasarkan kemunculan
    kata yang berdekatan (co-occurrence).
    """
    co_occurrences = {}

    for i in range(len(words) - window_size):
        target = words[i]
        context = words[i+1:i+1+window_size]

        for neighbor in context:
            if target == neighbor:
                continue

            pair = tuple(sorted((target, neighbor)))
            co_occurrences[pair] = co_occurrences.get(pair, 0) + 1

    G = nx.Graph()
    for (u, v), weight in co_occurrences.items():
        G.add_edge(u, v, weight=weight)

    return G

# =========================================================
# 7. PROGRAM UTAMA
# =========================================================

def main():
    download_nltk_data()

    # Session state untuk menyimpan data tiap file
    if 'paper_data' not in st.session_state:
        st.session_state.paper_data = {}

    if 'active_file_key' not in st.session_state:
        st.session_state.active_file_key = None

    # ================== HEADER ==================
    st.markdown("<div class='main-title'>📄 Analisis Relasi Kata Dokumen PDF</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Visualisasi jaringan kata menggunakan NLP & PageRank</div>", unsafe_allow_html=True)

    # ================== SIDEBAR ==================
    with st.sidebar:
        st.header("⚙️ Kontrol Aplikasi")
        uploaded_files = st.file_uploader(
            "Upload File PDF",
            type="pdf",
            accept_multiple_files=True
        )
        window_size = st.slider("Jarak Relasi Kata", 1, 5, 2)
        st.caption("Multiple upload diperbolehkan")

    # ================== PROSES DATA ==================
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_name = uploaded_file.name

            if file_name not in st.session_state.paper_data:
                with st.spinner(f"Memproses {file_name}..."):
                    raw_text = extract_text_from_pdf(uploaded_file)
                    words = process_text(raw_text)

                    if len(words) > 5:
                        G = build_graph(words, window_size)
                        pr = nx.pagerank(G, alpha=0.85)

                        df = pd.DataFrame(pr.items(), columns=['Kata', 'PageRank'])
                        df = df.sort_values('PageRank', ascending=False).reset_index(drop=True)

                        st.session_state.paper_data[file_name] = {
                            'graph': G,
                            'pagerank': pr,
                            'df': df,
                            'count': len(words)
                        }

                        st.session_state.active_file_key = file_name

        # ================== PILIH FILE ==================
        processed_files = list(st.session_state.paper_data.keys())

        selected_file = st.sidebar.selectbox(
            "Pilih Dokumen",
            processed_files,
            key='active_file_key'
        )

        data = st.session_state.paper_data[selected_file]
        G = data['graph']
        df = data['df']
        pr = data['pagerank']

        # ================== HASIL ==================
        st.markdown("<div class='section-box'>", unsafe_allow_html=True)
        st.subheader(f"📘 Dokumen Aktif: {selected_file}")
        st.success(f"Jumlah kata bersih: {data['count']} | Node graph: {len(G.nodes())}")
        st.markdown("</div>", unsafe_allow_html=True)

        col1, col2 = st.columns([3, 2])

        with col1:
            st.subheader("🕸️ Visualisasi Jaringan Kata")
            net = Network(height="600px", width="100%")
            net.from_nx(G)

            net.save_graph("graph.html")
            with open("graph.html", "r", encoding="utf-8") as f:
                components.html(f.read(), height=620)

        with col2:
            st.subheader("📊 Ranking Kata (PageRank)")
            st.bar_chart(df.head(20).set_index("Kata"))
            st.dataframe(df, use_container_width=True)

    else:
        st.info("Silakan upload file PDF melalui sidebar.")

# =========================================================
# 8. ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()
